"""Desktop wallet client and short-lived, provider-scoped CLI credentials."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
import uuid

import httpx
from kurt.utils.security import child_env, require_secure_endpoint
from . import WalletError
from .gateway import ORIGINS, CLI_PROVIDERS, MAX_REPLY

CLI_CONTEXT = ContextVar('kurt_wallet_cli',default=None)


def active():
    mode=os.environ.get('KURT_WALLET_MODE')
    if mode is not None:
        if mode not in ('0','1'): raise WalletError('invalid_wallet_mode',503)
        return mode=='1'
    from kurt.core.persona import load_persona
    return load_persona().get('wallet_enabled') is True


def read_token(path):
    import stat
    fd=os.open(Path(path).expanduser(),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode&0o077 or info.st_size>4096 or (hasattr(os,'getuid') and info.st_uid!=os.getuid()):
            raise ValueError('Wallet token must be a private owner-owned regular file.')
        token=os.read(fd,4096).decode().strip()
        if not token.startswith('kurt_live_'): raise ValueError('Invalid wallet owner token file.')
        return token
    finally: os.close(fd)


class Client:
    def __init__(self,url,token):
        require_secure_endpoint(url)
        parsed=urlsplit(url)
        if parsed.path not in ('','/') or parsed.query: raise ValueError('Wallet URL must be an origin.')
        if not isinstance(token,str) or not token.startswith('kurt_live_'): raise ValueError('A Kurt owner device token is required.')
        self.url,self._token=url.rstrip('/'),token

    def request(self,path,payload=None):
        allowed={'/wallet/status','/wallet/history','/wallet/catalog','/wallet/topups','/wallet/sessions','/wallet/reconcile'}
        if path not in allowed: raise ValueError('Unknown wallet route.')
        with httpx.Client(timeout=30,follow_redirects=False,trust_env=False) as client:
            response=client.request('POST' if payload is not None else 'GET',self.url+path,
                json=payload,headers={'Authorization':'Bearer '+self._token})
            if response.status_code!=200:
                try: code=response.json()['error']['code']
                except (ValueError,KeyError,TypeError): code='wallet_unavailable'
                raise WalletError(code,response.status_code)
            if len(response.content)>1024*1024: raise WalletError('wallet_response_too_large',502)
            return response.json()


def from_env():
    try:
        from kurt.core.persona import load_persona
        settings=load_persona()
        url=os.environ.get('KURT_WALLET_URL') or settings.get('wallet_url','')
        token=os.environ.get('KURT_WALLET_TOKEN','')
        token_file=os.environ.get('KURT_WALLET_TOKEN_FILE') or settings.get('wallet_token_file')
        if not token and token_file: token=read_token(token_file)
        return Client(url,token)
    except ValueError: raise WalletError('configure_wallet_url_and_device_token',503) from None


class WalletTransport(httpx.AsyncBaseTransport):
    """Replaces upstream credentials before any native HTTP request leaves Kurt."""
    def __init__(self,client=None,transport=None):
        self.client=client or from_env()
        self.transport=transport

    async def handle_async_request(self,request):
        origin=str(request.url.copy_with(path='/',query=None)).rstrip('/')
        provider=next((p for p,value in ORIGINS.items() if value==origin),None)
        if not provider:
            # Free on-device Ollama is independent of the paid wallet.
            if request.url.host in ('localhost','127.0.0.1') and request.url.port==11434 and request.url.path=='/api/chat':
                transport=httpx.AsyncHTTPTransport()
                try:
                    response=await transport.handle_async_request(request)
                    data=await response.aread()
                    return httpx.Response(response.status_code,headers=response.headers,content=data,request=request)
                finally: await transport.aclose()
            raise WalletError('provider_origin_not_supported',403)
        raw=await request.aread()
        headers={k:v for k,v in request.headers.items() if k.lower() in ('content-type','accept','anthropic-version','anthropic-beta')}
        headers.update({'Authorization':'Bearer '+self.client._token,'X-Kurt-Request-ID':str(uuid.uuid4())})
        path='/wallet/proxy/'+provider+request.url.path
        if request.url.query: path+='?'+request.url.query.decode('ascii')
        try:
            async with httpx.AsyncClient(timeout=620,follow_redirects=False,trust_env=False,transport=self.transport) as client:
                async with client.stream(request.method,self.client.url+path,headers=headers,content=raw) as response:
                    data=bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data)>MAX_REPLY: raise WalletError('wallet_response_too_large',502)
                    status=response.status_code; reply_headers=dict(response.headers)
            if status>=400:
                try: code=json.loads(data)['error']['code']
                except (ValueError,KeyError,TypeError): code='provider_http_'+str(status)
                raise WalletError(code,status)
            return httpx.Response(status,headers=reply_headers,content=bytes(data),request=request)
        except WalletError: raise
        except Exception: raise WalletError('outcome_unverified_check_history',503) from None


@contextmanager
def cli_session(name):
    if not active() or CLI_CONTEXT.get() is not None:
        yield CLI_CONTEXT.get(); return
    if name not in CLI_PROVIDERS: raise WalletError('cli_not_supported',403)
    client=from_env(); result=client.request('/wallet/sessions',{'cli':name})
    token=result.get('token',''); profile=result.get('profile',{})
    if not token.startswith('kurt_cli_') or result.get('provider')!=CLI_PROVIDERS[name]: raise WalletError('invalid_session_response',503)
    with tempfile.TemporaryDirectory(prefix='kurt-wallet-cli-') as folder:
        context={'url':client.url,'token':token,'provider':result['provider'],'profile':profile,'root':Path(folder).resolve(),'cli':name}
        reset=CLI_CONTEXT.set(context)
        try: yield context
        finally: CLI_CONTEXT.reset(reset)


def cli_environment(name,base):
    context=CLI_CONTEXT.get()
    if context is None:
        return None
    if name!=context['cli']: raise WalletError('nested_cli_requires_separate_session',403)
    root=context['root']; url=context['url']+'/wallet/proxy/'+context['provider']; token=context['token']
    # Start from OS variables only, dropping every actual vendor/GitHub key and
    # inherited OAuth/config overrides. The owner token never reaches a child.
    env=child_env(source=base)
    env.update({'HOME':str(root),'NO_COLOR':'1','KURT_SESSION_TOKEN':token,'CI':'1'})
    model=context['profile'].get('model')
    if name in ('deepseek','deepseek-cli'):
        env.update({'DEEPSEEK_API_KEY':token,'DEEPSEEK_BASE_URL':url,'DEEPSEEK_MODEL':model or 'deepseek-flash',
                    'TAVILY_API_KEY':'not-configured'})
    elif name=='claude':
        env.update({'ANTHROPIC_API_KEY':token,'ANTHROPIC_BASE_URL':url,'CLAUDE_CONFIG_DIR':str(root/'.claude'),
                    'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1','DISABLE_TELEMETRY':'1','DISABLE_ERROR_REPORTING':'1'})
    elif name=='gemini':
        env.update({'GEMINI_API_KEY':token,'GOOGLE_GEMINI_BASE_URL':url,'GEMINI_CLI_HOME':str(root)})
        config=root/'.gemini'; config.mkdir(exist_ok=True)
        (config/'settings.json').write_text(json.dumps({'security':{'auth':{'selectedType':'gemini-api-key'}},'telemetry':{'enabled':False}}))
        if base.get('GEMINI_CLI_TRUST_WORKSPACE') in ('true','false'):
            env['GEMINI_CLI_TRUST_WORKSPACE']=base['GEMINI_CLI_TRUST_WORKSPACE']
        # Preserve existing trust decisions, not OAuth/API credential files.
        policy=Path.home()/'.gemini/trustedFolders.json'
        try:
            if policy.is_file() and policy.stat().st_size<=65536:
                values=json.loads(policy.read_text())
                if isinstance(values,dict) and all(isinstance(k,str) and Path(k).is_absolute() and v in ('TRUST_FOLDER','TRUST_PARENT','DO_NOT_TRUST') for k,v in values.items()):
                    (config/'trustedFolders.json').write_text(json.dumps(values))
        except (OSError,ValueError):
            pass
    elif name=='vibe':
        env.update({'MISTRAL_API_KEY':token,
            'VIBE_PROVIDERS':json.dumps([{'name':'mistral','api_base':url+'/v1','api_key_env_var':'MISTRAL_API_KEY','backend':'mistral'}]),
            'VIBE_VIBE_BASE_URL':url,'VIBE_CONSOLE_BASE_URL':url,'VIBE_VIBE_CODE_SESSIONS_BASE_URL':url,
            'VIBE_OTEL_ENABLED':'false'})
        # Remote connector/tool calls may have separate billable contracts. Do
        # not silently route them around this gateway with other credentials.
        env['VIBE_TOOLS']=json.dumps({'connector_web_search_news_search':{'permission':'never'},
                                    'connector_web_search_web_search':{'permission':'never'}})
    elif name=='codex':
        home=root/'.codex'; home.mkdir(exist_ok=True)
        env.update({'CODEX_HOME':str(home),'OPENAI_API_KEY':token})
    elif name=='openclaw':
        model=model or 'openai/gpt-oss-20b'
        state=root/'openclaw'; state.mkdir(exist_ok=True)
        config=root/'openclaw.json'
        config.write_text(json.dumps({'gateway':{'mode':'local'},'agents':{'defaults':{
            'workspace':str(root/'workspace'),'model':{'primary':'kurt-wallet/'+model}}},
            'models':{'mode':'replace','providers':{'kurt-wallet':{'baseUrl':url+'/openai/v1','apiKey':token,
                'api':'openai-completions','models':[{'id':model,'name':'Kurt Wallet '+model,'contextWindow':131072,'maxTokens':8192}]}}}}))
        env.update({'OPENCLAW_CONFIG_PATH':str(config),'OPENCLAW_STATE_DIR':str(state)})
    return env


def codex_arguments():
    context=CLI_CONTEXT.get()
    if context is None: return []
    from kurt.core.codex_adapter import _toml
    provider={'name':'Kurt Wallet','base_url':context['url']+'/wallet/proxy/openai/v1',
              'env_key':'KURT_SESSION_TOKEN','wire_api':'responses','request_max_retries':0,'stream_max_retries':0}
    args=['-c','model_provider="kurt-wallet"','-c','model_providers.kurt-wallet='+_toml(provider)]
    if context['profile'].get('model'): args+=['-c','model='+_toml(context['profile']['model'])]
    return args
