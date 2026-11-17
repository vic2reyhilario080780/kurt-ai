"""Personal/hosted wallet ASGI service. No desktop actions or public admin credits."""
import asyncio
import json
import os
from pathlib import Path

from . import WalletError
from .ledger import Wallet
from .gateway import Gateway, MAX_BODY, MAX_REPLY, decode, CLI_PROVIDERS, KEY_VARS
from .payments import Payments


class BillingApp:
    def __init__(self,wallet,gateway,payments=None,*,require_https=True):
        self.wallet,self.gateway,self.payments=wallet,gateway,payments
        self.require_https=require_https
        self.jobs=set()

    async def __call__(self,scope,receive,send):
        if scope['type']=='lifespan':
            while True:
                event=await receive()
                if event['type']=='lifespan.startup': await send({'type':'lifespan.startup.complete'})
                elif event['type']=='lifespan.shutdown':
                    if self.jobs: await asyncio.gather(*self.jobs,return_exceptions=True)
                    await send({'type':'lifespan.shutdown.complete'}); return
            return
        if scope['type']!='http': return
        status,body,headers=500,b'{"error":"internal_error"}',{}
        try:
            if self.require_https and scope.get('scheme')!='https': raise WalletError('https_required',400)
            incoming={}
            for key,value in scope.get('headers',[]):
                name=key.decode('ascii').lower()
                if name in incoming: raise WalletError('duplicate_header',400)
                incoming[name]=value.decode('latin1')
            if int(incoming.get('content-length','0'))>MAX_BODY: raise WalletError('request_too_large',413)
            path,method=scope.get('path',''),scope.get('method','')
            async def read_body():
                raw=bytearray()
                while True:
                    item=await receive()
                    if item['type']!='http.request': raise WalletError('request_disconnected',400)
                    raw.extend(item.get('body',b''))
                    if len(raw)>MAX_BODY: raise WalletError('request_too_large',413)
                    if not item.get('more_body'): return bytes(raw)
            if path=='/wallet/payments/stripe' and method=='POST':
                if not self.payments: raise WalletError('payment_processor_not_configured',503)
                if scope.get('query_string'): raise WalletError('query_not_allowed',400)
                raw=await asyncio.wait_for(read_body(),10)
                if len(raw)>512*1024: raise WalletError('webhook_too_large',413)
                result=self.payments.event(raw,incoming.get('stripe-signature',''))
                status,body=200,json.dumps(result).encode()
            else:
                auth=incoming.get('authorization','')
                token=auth[7:] if auth.startswith('Bearer ') else incoming.get('x-api-key') or incoming.get('x-goog-api-key') or ''
                identity=self.wallet.auth(token)
                query=scope.get('query_string',b'').decode('ascii')
                if path.startswith('/wallet/proxy/'):
                    route=path[len('/wallet/proxy/'):].split('/',1)
                    if len(route)!=2: raise WalletError('path_not_allowed',404)
                    raw=await asyncio.wait_for(read_body(),15) if method=='POST' else b''
                    async def execute():
                        return await self.gateway.forward(identity,route[0],method,'/'+route[1],raw,incoming,query)
                    task=asyncio.create_task(execute()); self.jobs.add(task)
                    task.add_done_callback(self.jobs.discard)
                    task.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
                    status,body,headers,_=await asyncio.shield(task)
                else:
                    if query: raise WalletError('query_not_allowed',400)
                    if identity['scope']!='owner': raise WalletError('owner_token_required',403)
                    if path=='/wallet/status' and method=='GET':
                        result=self.wallet.summary(identity['tenant'])
                        result['payments_enabled']=bool(self.payments and self.payments.enabled)
                    elif path=='/wallet/history' and method=='GET': result=self.wallet.history(identity['tenant'])
                    elif path=='/wallet/catalog' and method=='GET': result=self.gateway.catalog()
                    elif path in ('/wallet/sessions','/wallet/topups','/wallet/reconcile') and method=='POST':
                        if not incoming.get('content-type','').startswith('application/json'): raise WalletError('json_required',415)
                        data=decode(await asyncio.wait_for(read_body(),10))
                        if path=='/wallet/sessions':
                            if set(data)!={'cli'} or data['cli'] not in CLI_PROVIDERS: raise WalletError('invalid_cli',400)
                            profile=self.gateway.profiles().get(data['cli'])
                            if not profile or not self.gateway._keys.get(profile['provider']): raise WalletError('provider_not_configured',503)
                            budget=str(self.gateway.config.get('cli_session_budget_usd','5'))
                            session=self.wallet.session(token,profile['provider'],data['cli'],budget=budget)
                            result={'token':session,'provider':profile['provider'],'profile':profile,'expires_in':300,'budget_usd':budget}
                        elif path=='/wallet/topups':
                            if set(data)!={'amount_cents'}: raise WalletError('invalid_topup',400)
                            if not self.payments: raise WalletError('payment_processor_not_configured',503)
                            result=await self.payments.checkout(identity['tenant'],data['amount_cents'])
                        else:
                            if set(data)!={'request_id'}: raise WalletError('invalid_reconciliation',400)
                            row=self.wallet.request(identity['tenant'],data['request_id'])
                            if row['provider']=='fal' and row['status']!='settled':
                                await self.gateway.reconcile_fal(identity['tenant'],row['id'])
                            if row['provider']=='openrouter' and row['status']!='settled':
                                await self.gateway.reconcile_openrouter(identity['tenant'],row['id'])
                            result={'request':self.wallet.request(identity['tenant'],row['id'])}
                    else: raise WalletError('not_found',404)
                    status,body=200,json.dumps(result,allow_nan=False).encode()
        except WalletError as exc:
            status,body=exc.status,json.dumps({'error':{'type':'kurt_wallet_error','code':exc.code,'message':str(exc)}}).encode()
        except (ValueError,TypeError,UnicodeError,RecursionError):
            status,body=400,b'{"error":{"code":"invalid_request","message":"Invalid wallet request."}}'
        except asyncio.TimeoutError:
            status,body=408,b'{"error":{"code":"request_timeout","message":"No automatic retry. Check wallet history."}}'
        except Exception:
            status,body=503,b'{"error":{"code":"upstream_outcome_unverified","message":"Check wallet history before retrying. No task was replayed."}}'
        response_headers={'content-type':'application/json','cache-control':'no-store','x-content-type-options':'nosniff',**headers}
        response_headers['content-length']=str(len(body))
        await send({'type':'http.response.start','status':status,'headers':[(k.encode(),v.encode()) for k,v in response_headers.items()]})
        await send({'type':'http.response.body','body':body})


def create_app():
    root=os.environ.get('KURT_WALLET_STATE_DIR','')
    config_path=os.environ.get('KURT_WALLET_CONFIG','')
    if not root or not Path(root).is_absolute() or not config_path or not Path(config_path).is_absolute():
        raise RuntimeError('Set absolute KURT_WALLET_STATE_DIR and KURT_WALLET_CONFIG.')
    config=json.loads(Path(config_path).read_text())
    keys={provider:os.environ.get('KURT_WALLET_'+name,'') for provider,name in KEY_VARS.items()}
    keys['fal_billing']=os.environ.get('KURT_WALLET_FAL_BILLING_KEY','')
    wallet=Wallet(root); gateway=Gateway(wallet,config,keys)
    payments=Payments(wallet,os.environ.get('KURT_WALLET_STRIPE_KEY',''),os.environ.get('KURT_WALLET_STRIPE_WEBHOOK_SECRET',''),
        live=os.environ.get('KURT_WALLET_STRIPE_LIVE')=='1',return_url=config.get('payment_return_url',''))
    return BillingApp(wallet,gateway,payments,require_https=os.environ.get('KURT_WALLET_LOCAL_HTTP')!='1')
