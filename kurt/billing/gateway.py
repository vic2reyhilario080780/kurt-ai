"""Allowlisted provider origins. The client never chooses a URL or upstream key."""
import hashlib
import json
import re
import time
from decimal import Decimal
from email.parser import BytesParser
from email.policy import default as email_policy

import httpx
from . import WalletError
from .costs import receipt
from .ledger import units, usd

ORIGINS = {
    'openrouter':'https://openrouter.ai', 'openai':'https://api.openai.com',
    'mistral':'https://api.mistral.ai', 'deepseek':'https://api.deepseek.com',
    'groq':'https://api.groq.com', 'anthropic':'https://api.anthropic.com',
    'google':'https://generativelanguage.googleapis.com', 'fal':'https://fal.run',
    'replicate':'https://api.replicate.com',
}
KEY_VARS = {'openrouter':'OPENROUTER_API_KEY','openai':'OPENAI_API_KEY','mistral':'MISTRAL_API_KEY',
            'deepseek':'DEEPSEEK_API_KEY','groq':'GROQ_API_KEY','anthropic':'ANTHROPIC_API_KEY',
            'google':'GOOGLE_AI_KEY','fal':'FAL_API_KEY','replicate':'REPLICATE_API_TOKEN'}
CLI_PROVIDERS = {'codex':'openai','claude':'anthropic','gemini':'google','openclaw':'groq',
                 'vibe':'mistral','deepseek':'deepseek','deepseek-cli':'deepseek'}
MAX_BODY = 24*1024*1024
MAX_REPLY = 64*1024*1024


def decode(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('Duplicate JSON field.')
            result[key]=value
        return result
    def constant(_): raise ValueError('Non-finite JSON number.')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    if not isinstance(value,dict): raise ValueError('Expected JSON object.')
    return value


class Gateway:
    def __init__(self,wallet,config,keys,*,transport=None):
        if config.get('currency','USD')!='USD' or config.get('markup_percent',0)!=0:
            raise ValueError('This wallet supports USD with exactly zero markup.')
        self.wallet,self.config,self._keys,self.transport=wallet,config,dict(keys),transport
        self.providers=config.get('providers',{})
        if set(self.providers)-ORIGINS.keys(): raise ValueError('Unsupported provider.')
        for provider,spec in self.providers.items():
            if not isinstance(spec,dict) or not isinstance(spec.get('models'),list) or not spec['models']:
                raise ValueError('An explicit model allowlist is required.')
            if units(str(spec.get('reserve_usd','0')))<=0: raise ValueError('A positive cost reservation is required.')
            if spec.get('rates_per_million_usd'):
                raise ValueError('Estimated-rate settlement is disabled: use provider receipts or verified invoice reconciliation.')

    def profiles(self):
        profiles={name:{'provider':provider} for name,provider in CLI_PROVIDERS.items() if provider in self.providers}
        for name,spec in self.config.get('cli_profiles',{}).items():
            if name not in CLI_PROVIDERS or spec.get('provider')!=CLI_PROVIDERS[name]:
                raise ValueError('CLI profiles cannot silently switch provider.')
            profiles[name]=dict(spec)
        return profiles

    def catalog(self):
        return {'currency':'USD','markup_percent':0,'cli_profiles':self.profiles(),
                'providers':{p:{'models':s['models'],'reservation_usd':str(s['reserve_usd']),
                    'key_configured':bool(self._keys.get(p)),
                    'settlement':'provider_receipt' if p in ('openrouter','fal') else 'pending_verified_reconciliation'}
                    for p,s in self.providers.items()}}

    def _model(self,provider,model):
        spec=self.providers.get(provider)
        if not spec or not self._keys.get(provider): raise WalletError('provider_not_configured',503)
        if not isinstance(model,str) or not model or len(model)>200 or not re.fullmatch(r'[A-Za-z0-9_./:@+-]+',model) or '..' in model:
            raise WalletError('invalid_model',400)
        if '*' not in spec['models'] and model not in spec['models']: raise WalletError('model_not_allowed',403)
        return spec

    def _route(self,identity,provider,method,path,payload):
        if provider not in ORIGINS or provider not in self.providers or not self._keys.get(provider):
            raise WalletError('provider_not_configured',503)
        if identity['provider'] and provider!=identity['provider']: raise WalletError('session_provider_mismatch',403)
        if not path.startswith('/') or '..' in path or '%' in path or '\\' in path or '?' in path or '#' in path or '//' in path:
            raise WalletError('path_not_allowed',400)
        # Local acknowledgement only: telemetry must never receive a Kurt token.
        if provider=='mistral' and method=='POST' and path=='/v1/datalake/events': return None,False,None
        if method=='GET':
            if provider=='replicate' and re.fullmatch(r'/v1/predictions/[A-Za-z0-9_-]+',path):
                item=self.wallet.resource(identity['tenant'],provider,path.rsplit('/',1)[1])
                return self.wallet.request(identity['tenant'],item['request_id'])['model'],False,item['request_id']
            if re.fullmatch(r'/(?:api/v1/|openai/v1/|v1/|v1beta/)?models(?:/[A-Za-z0-9_./:@+-]+)?',path):
                if '/models/' in path: self._model(provider,path.split('/models/',1)[1])
                return None,False,None
            if provider=='mistral' and path=='/v1/connectors/bootstrap': return None,False,None
            raise WalletError('path_not_allowed',403)
        if method!='POST': raise WalletError('method_not_allowed',405)
        if provider=='fal':
            model=path[1:]
        elif provider=='replicate':
            if path=='/v1/predictions':
                version=payload.get('version')
                # Only a server-known model version can be submitted through the
                # generic API; the native router first fetches its model metadata.
                item=self.wallet.resource(identity['tenant'],'replicate-version',str(version))
                model=item['request_id']
            else:
                match=re.fullmatch(r'/v1/models/([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+)/predictions',path)
                if not match: raise WalletError('path_not_allowed',403)
                model=match[1]
            if set(payload)-{'input','version'}: raise WalletError('unsupported_prediction_options',400)
        elif provider=='google' and re.fullmatch(r'/v1(?:beta)?/models/[^/]+:(?:generateContent|streamGenerateContent|countTokens)',path):
            model=path.split('/models/',1)[1].split(':',1)[0]
            if path.endswith(':countTokens'): return model,False,None
        else:
            allowed={'/v1/chat/completions','/chat/completions','/api/v1/chat/completions','/openai/v1/chat/completions',
                     '/v1/responses','/responses','/api/v1/responses','/v1/messages','/v1/messages/count_tokens',
                     '/v1beta/openai/chat/completions','/openai/v1/audio/transcriptions'}
            if path not in allowed: raise WalletError('path_not_allowed',403)
            model=payload.get('model')
            if path.endswith('/count_tokens'): return model,False,None
        self._model(provider,model)
        return model,True,None

    def _headers(self,provider,content_type,incoming):
        key=self._keys[provider]
        headers={'Content-Type':content_type,'Accept':incoming.get('accept','application/json')}
        if provider=='anthropic':
            headers.update({'x-api-key':key,'anthropic-version':incoming.get('anthropic-version','2023-06-01')})
            if incoming.get('anthropic-beta'): headers['anthropic-beta']=incoming['anthropic-beta'][:1000]
        elif provider=='google': headers['x-goog-api-key']=key
        else: headers['Authorization']=('Key ' if provider=='fal' else 'Bearer ')+key
        if provider=='replicate': headers['Prefer']='wait=60'
        return headers

    async def forward(self,identity,provider,method,path,raw,headers,query=''):
        if len(raw)>MAX_BODY: raise WalletError('request_too_large',413)
        if query and not ((provider=='google' and query=='alt=sse') or (provider=='anthropic' and query=='beta=true')):
            raise WalletError('query_not_allowed',400)
        content_type=headers.get('content-type','application/json')
        multipart=content_type.startswith('multipart/form-data')
        if raw and multipart:
            if provider!='groq' or path!='/openai/v1/audio/transcriptions': raise WalletError('multipart_not_allowed',415)
            message=BytesParser(policy=email_policy).parsebytes(('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
            fields=[p.get_payload(decode=True).decode() for p in message.iter_parts() if p.get_param('name',header='content-disposition')=='model']
            if len(fields)!=1: raise WalletError('invalid_transcription_model',400)
            payload={'model':fields[0]}
        elif raw:
            if not content_type.startswith('application/json'): raise WalletError('json_required',415)
            payload=decode(raw)
        else: payload={}
        if any(name in payload for name in ('api_key','apiKey','authorization','base_url','tenant','provider_url','webhook','webhook_events_filter')):
            raise WalletError('client_credentials_or_callbacks_not_allowed',400)
        model,billable,parent=self._route(identity,provider,method,path,payload)
        if provider=='mistral' and path=='/v1/datalake/events': return 204,b'',{},None
        if model: spec=self._model(provider,model)
        else: spec=self.providers[provider]
        request=None
        if billable:
            if not multipart and provider not in ('fal','replicate'):
                limit=spec.get('max_output_tokens',8192)
                if type(limit) is not int or not 1<=limit<=65536: raise WalletError('invalid_server_output_limit',503)
                if provider=='google' and ':generate' in path or provider=='google' and ':streamGenerate' in path:
                    config=payload.setdefault('generationConfig',{})
                    if not isinstance(config,dict): raise WalletError('invalid_generation_config',400)
                    requested=config.get('maxOutputTokens',limit)
                    if type(requested) is not int or not 1<=requested<=2**31: raise WalletError('invalid_output_limit',400)
                    config['maxOutputTokens']=min(requested,limit)
                else:
                    field='max_output_tokens' if path.endswith('/responses') else 'max_completion_tokens' if 'max_completion_tokens' in payload else 'max_tokens'
                    requested=payload.get(field,limit)
                    if type(requested) is not int or not 1<=requested<=2**31: raise WalletError('invalid_output_limit',400)
                    payload[field]=min(requested,limit)
                raw=json.dumps(payload,allow_nan=False,separators=(',',':')).encode()
            fingerprint=hashlib.sha256(provider.encode()+method.encode()+path.encode()+raw).hexdigest()
            dedupe=fingerprint if identity['scope']!='owner' else headers.get('x-kurt-request-id','')
            if not dedupe: raise WalletError('request_id_required',400)
            request=self.wallet.reserve_money(identity,provider,model,str(spec['reserve_usd']),dedupe,fingerprint)
            self.wallet.submitted(identity['tenant'],request)
        output=bytearray();forwarded={};status=None
        try:
            async with httpx.AsyncClient(timeout=610,follow_redirects=False,trust_env=False,transport=self.transport) as client:
                async with client.stream(method,ORIGINS[provider]+path+('?' + query if query else ''),
                    headers=self._headers(provider,content_type,headers),content=raw or None) as response:
                    status=response.status_code
                    forwarded={k:v for k,v in response.headers.items() if k.lower() in ('content-type','retry-after','x-fal-request-id','x-request-id','request-id')}
                    forwarded={k:v for k,v in forwarded.items() if not any(secret and secret in v for secret in self._keys.values())}
                    early_id=forwarded.get('x-fal-request-id') or forwarded.get('x-request-id') or forwarded.get('request-id')
                    if request and early_id and len(early_id)<=200:
                        self.wallet.record(identity['tenant'],request,provider_id=early_id,http_status=status,pending=False)
                    async for chunk in response.aiter_bytes():
                        output.extend(chunk)
                        if len(output)>MAX_REPLY: raise WalletError('provider_response_too_large',502)
                    body=bytes(output)
            if status in (301,302,303,307,308): raise WalletError('provider_redirect_refused',502)
            # Strip known secrets even from provider errors/echoes. Only opaque
            # generated media bytes (not accepted here) would need another policy.
            for secret in self._keys.values():
                if secret:
                    body=body.replace(secret.encode(),b'[REDACTED]')
                    forwarded={name:value for name,value in forwarded.items() if secret not in value}
            if provider=='replicate' and method=='GET' and '/models/' in path and status==200:
                data=json.loads(body); version=(data.get('latest_version') or {}).get('id')
                if version:
                    self._model(provider,path.split('/models/',1)[1])
                    self.wallet.add_resource(identity['tenant'],'replicate-version',version,path.split('/models/',1)[1])
            if parent and provider=='replicate' and status==200:
                data=json.loads(body)
                compute=(data.get('metrics') or {}).get('predict_time')
                extra={'compute_seconds':str(compute)} if isinstance(compute,(int,float)) and not isinstance(compute,bool) else {}
                self.wallet.record(identity['tenant'],parent,usage=extra,http_status=status)
            if request:
                parsed={'usage':{},'provider_id':None,'cost_units':None}
                try: parsed=receipt(body,forwarded.get('content-type',''),provider)
                except (ValueError,TypeError,KeyError): pass
                if parsed['provider_id'] and '[REDACTED]' in parsed['provider_id']: parsed['provider_id']=None
                parsed['provider_id']=parsed['provider_id'] or forwarded.get('x-fal-request-id') or forwarded.get('x-request-id') or forwarded.get('request-id')
                self.wallet.record(identity['tenant'],request,provider_id=parsed['provider_id'],usage=parsed['usage'],http_status=status)
                if provider=='replicate' and parsed['provider_id']:
                    self.wallet.add_resource(identity['tenant'],provider,parsed['provider_id'],request)
                if parsed['cost_units'] is not None:
                    self.wallet.settle(identity['tenant'],request,usd(parsed['cost_units']),basis='provider_receipt',evidence=provider+':'+(parsed['provider_id'] or request))
                elif status in (401,402) and not parsed['provider_id']:
                    self.wallet.settle(identity['tenant'],request,'0',basis='rejected_before_inference',evidence=f'upstream-http-{status}:'+request)
                if provider=='fal' and parsed['provider_id']:
                    try: await self.reconcile_fal(identity['tenant'],request)
                    except Exception: pass  # The output still exists; the hold stays pending.
            forwarded['cache-control']='no-store'
            if request:
                forwarded['x-kurt-wallet-request-id']=request
                forwarded['x-kurt-wallet-state']=self.wallet.request(identity['tenant'],request)['status']
            return status,body,forwarded,request
        except BaseException:
            if request:
                # Preserve an already received generation ID across a broken
                # stream, without assuming a partial usage figure is the bill.
                try:
                    prefix=bytes(output)
                    for secret in self._keys.values():
                        if secret: prefix=prefix.replace(secret.encode(),b'[REDACTED]')
                    partial=receipt(prefix,forwarded.get('content-type',''),provider)
                    known=partial.get('provider_id')
                    if known and '[REDACTED]' not in known:
                        self.wallet.record(identity['tenant'],request,provider_id=known,usage=partial['usage'],http_status=status)
                except Exception:
                    pass
                self.wallet.pending(identity['tenant'],request)
            raise

    async def reconcile_fal(self,tenant,request):
        row=self.wallet.request(tenant,request)
        if row['provider']!='fal' or not row['provider_id']: raise WalletError('missing_fal_request_id')
        key=self._keys.get('fal_billing') or self._keys.get('fal')
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,trust_env=False,transport=self.transport) as client:
            response=await client.get('https://api.fal.ai/v1/models/billing-events',
                params={'request_id':row['provider_id'],'endpoint_id':row['model'],'limit':50},headers={'Authorization':'Key '+key})
            response.raise_for_status(); data=json.loads(response.content,parse_float=Decimal)
        events=[item for item in data.get('billing_events',[]) if item.get('request_id')==row['provider_id'] and item.get('endpoint_id')==row['model']]
        if len(events)!=1: return False
        nano=events[0].get('cost_estimate_nano_usd')
        if type(nano) is not int or nano<0: return False
        return self.wallet.settle(tenant,request,str(Decimal(nano)/10**9),basis='fal_billed_event',evidence='fal:'+row['provider_id'])

    async def reconcile_openrouter(self,tenant,request):
        row=self.wallet.request(tenant,request)
        if row['provider']!='openrouter' or not row['provider_id']: raise WalletError('missing_generation_id')
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,trust_env=False,transport=self.transport) as client:
            response=await client.get('https://openrouter.ai/api/v1/generation',params={'id':row['provider_id']},
                headers={'Authorization':'Bearer '+self._keys['openrouter']})
            response.raise_for_status(); data=json.loads(response.content,parse_float=Decimal).get('data',{})
        if data.get('id')!=row['provider_id'] or data.get('total_cost') is None: return False
        value=units(str(data['total_cost']))
        return self.wallet.settle(tenant,request,usd(value),basis='openrouter_generation_receipt',evidence='openrouter:'+row['provider_id'])
