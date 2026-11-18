"""Real wallet HTTP service + installed CLIs, synthetic upstreams/credits only."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import threading
import time
from unittest.mock import patch
import uuid

import httpx
import uvicorn
from kurt.billing.app import BillingApp
from kurt.billing.gateway import Gateway,ORIGINS
from kurt.billing.commands import default_config
from kurt.billing.ledger import Wallet
from kurt.core import persona
from kurt.core.cli_readiness import test_default_cli
from kurt.core.router import ModelRouter
from kurt.utils import env_loader
from kurt.utils.workspace import workspace


def sse(items):
    return '\n\n'.join('event: '+item.get('type','message')+'\ndata: '+json.dumps(item) for item in items)+'\n\n'


def verify(names, *, copilot_read=False):
    upstream=[]
    client_requests=[]
    def handler(request):
        provider=next((p for p,url in ORIGINS.items() if request.url.host==httpx.URL(url).host),None)
        path=request.url.path
        if request.url.host=='api.fal.ai': provider='fal'
        auth=request.headers.get('authorization') or request.headers.get('x-api-key') or request.headers.get('x-goog-api-key') or ''
        match=auth in ('Bearer fixture-server-'+str(provider),'Key fixture-server-'+str(provider),'fixture-server-'+str(provider))
        upstream.append({'provider':provider or ('fal_billing' if request.url.host=='api.fal.ai' else 'unknown'),
                         'path':path,'method':request.method,'server_key_matches':match})
        if request.url.host=='api.fal.ai':
            return httpx.Response(200,json={'billing_events':[{'request_id':request.url.params['request_id'],'endpoint_id':request.url.params['endpoint_id'],'cost_estimate_nano_usd':1000000}]})
        body=json.loads(request.content) if request.content else {}
        text=json.dumps(body)
        markers=re.findall(r'KURT_[A-Z_-]+_READY',text)
        marker=markers[0] if markers else 'KURT_NATIVE_READY'
        model=body.get('model') or ('mistral-vibe-cli-latest' if provider=='mistral' else 'fixture/model')
        identity='fixture-'+uuid.uuid4().hex
        if copilot_read and provider=='openrouter' and marker=='KURT_COPILOT_READY':
            tool_results=[m for m in body.get('messages',[]) if m.get('role')=='tool']
            if not tool_results:
                call={'id':'fixture_read','type':'function','function':{'name':'view',
                      'arguments':json.dumps({'path':str(root/'read-fixture.txt')})}}
                if not body.get('stream'):
                    return httpx.Response(200,json={'id':identity,'object':'chat.completion','created':0,'model':model,
                        'choices':[{'index':0,'message':{'role':'assistant','content':None,'tool_calls':[call]},'finish_reason':'tool_calls'}],
                        'usage':{'prompt_tokens':1,'completion_tokens':2,'total_tokens':3,'cost':0.000001}})
                chunk={'id':identity,'object':'chat.completion.chunk','created':0,'model':model,
                       'choices':[{'index':0,'delta':{'role':'assistant','tool_calls':[{'index':0,**call}]},'finish_reason':'tool_calls'}],
                       'usage':{'prompt_tokens':1,'completion_tokens':2,'total_tokens':3,'cost':0.000001}}
                return httpx.Response(200,headers={'content-type':'text/event-stream'},
                    text='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
            upstream[-1]['tool_roundtrip_verified']='COPILOT_READ_FIXTURE' in json.dumps(tool_results)
            if not upstream[-1]['tool_roundtrip_verified']:
                return httpx.Response(400,json={'error':{'message':'Fixture tool read not verified'}})
        if request.method=='GET':
            if '/models/' in path:
                return httpx.Response(200,json={'id':path.split('/models/',1)[1],'object':'model','owned_by':'fixture','created':0,
                    'capabilities':{'completion_chat':True,'function_calling':True,'vision':True},'max_context_length':131072,
                    'latest_version':{'id':'fixture-version'}})
            if path.endswith('/models'):
                return httpx.Response(200,json={'object':'list','data':[]})
            if path.endswith('/connectors/bootstrap'):return httpx.Response(200,json={'connectors':[],'groups':[],'data':[]})
            if '/predictions/' in path:return httpx.Response(200,json={'id':path.rsplit('/',1)[1],'status':'succeeded','output':['https://replicate.delivery/fixture.mp4']})
            return httpx.Response(404,json={'error':'fixture_metadata_not_supported'})
        if provider=='fal':return httpx.Response(200,headers={'x-fal-request-id':identity},json={'images':[{'url':'https://v3.fal.media/fixture.png'}]})
        if provider=='replicate':return httpx.Response(200,json={'id':identity,'status':'succeeded','output':['https://replicate.delivery/fixture.mp4']})
        if path.endswith(':countTokens'):return httpx.Response(200,json={'totalTokens':1})
        if path.endswith('/count_tokens'):return httpx.Response(200,json={'input_tokens':1})
        if provider=='google' and ':streamGenerateContent' in path:
            value={'candidates':[{'index':0,'content':{'role':'model','parts':[{'text':marker}]},'finishReason':'STOP'}],
                   'usageMetadata':{'promptTokenCount':1,'candidatesTokenCount':2,'totalTokenCount':3},'modelVersion':model}
            return httpx.Response(200,headers={'content-type':'text/event-stream'},text='data: '+json.dumps(value)+'\n\n')
        if provider=='google' and ':generateContent' in path:
            return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':marker}]},'finishReason':'STOP'}],
                'usageMetadata':{'promptTokenCount':1,'candidatesTokenCount':2,'totalTokenCount':3}})
        if provider=='anthropic' and path.endswith('/messages'):
            message={'id':identity,'type':'message','role':'assistant','model':model,'content':[{'type':'text','text':marker}],
                     'stop_reason':'end_turn','stop_sequence':None,'usage':{'input_tokens':1,'output_tokens':2}}
            if not body.get('stream'):return httpx.Response(200,json=message)
            start={**message,'content':[],'stop_reason':None,'usage':{'input_tokens':1,'output_tokens':0}}
            items=[{'type':'message_start','message':start},{'type':'content_block_start','index':0,'content_block':{'type':'text','text':''}},
                   {'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':marker}},
                   {'type':'content_block_stop','index':0},{'type':'message_delta','delta':{'stop_reason':'end_turn','stop_sequence':None},'usage':{'output_tokens':2}},
                   {'type':'message_stop'}]
            return httpx.Response(200,headers={'content-type':'text/event-stream'},text=sse(items))
        if path.endswith('/responses'):
            item={'id':'msg_'+identity,'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':marker,'annotations':[]}]}
            response={'id':'resp_'+identity,'object':'response','created_at':int(time.time()),'status':'completed','model':model,'output':[item],
                      'usage':{'input_tokens':1,'output_tokens':2,'total_tokens':3}}
            if not body.get('stream'):return httpx.Response(200,json=response)
            items=[{'type':'response.created','response':{**response,'status':'in_progress','output':[]}},
                   {'type':'response.output_item.added','output_index':0,'item':{**item,'status':'in_progress','content':[]}},
                   {'type':'response.content_part.added','item_id':item['id'],'output_index':0,'content_index':0,'part':{'type':'output_text','text':'','annotations':[]}},
                   {'type':'response.output_text.delta','item_id':item['id'],'output_index':0,'content_index':0,'delta':marker},
                   {'type':'response.output_text.done','item_id':item['id'],'output_index':0,'content_index':0,'text':marker},
                   {'type':'response.output_item.done','output_index':0,'item':item},
                   {'type':'response.completed','response':response}]
            return httpx.Response(200,headers={'content-type':'text/event-stream'},text=sse(items))
        usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
        if provider=='openrouter':usage['cost']=0.000001
        if body.get('stream'):
            items=[{'id':identity,'object':'chat.completion.chunk','created':0,'model':model,
                    'choices':[{'index':0,'delta':{'role':'assistant','content':marker},'finish_reason':None}]},
                   {'id':identity,'object':'chat.completion.chunk','created':0,'model':model,
                    'choices':[{'index':0,'delta':{},'finish_reason':'stop'}],'usage':usage}]
            return httpx.Response(200,headers={'content-type':'text/event-stream'},text='\n\n'.join('data: '+json.dumps(item) for item in items)+'\n\ndata: [DONE]\n\n')
        return httpx.Response(200,json={'id':identity,'object':'chat.completion','created':0,'model':model,
            'choices':[{'index':0,'message':{'role':'assistant','content':marker},'finish_reason':'stop'}],'usage':usage})

    with tempfile.TemporaryDirectory(prefix='kurt-wallet-fixture-') as folder:
        root=Path(folder);state=root/'state';store=Wallet(state);tenant,token=store.grant('pro')
        if copilot_read: (root/'read-fixture.txt').write_text('COPILOT_READ_FIXTURE\n')
        store.manual_credit(tenant,'1000','fixture-only','Synthetic fixture credit, not a payment')
        config=default_config();config['cli_session_budget_usd']='50'
        gateway=Gateway(store,config,{p:'fixture-server-'+p for p in ORIGINS},transport=httpx.MockTransport(handler))
        billing_app=BillingApp(store,gateway,require_https=False)
        async def audited_app(scope,receive,send):
            if scope['type']=='http':
                from urllib.parse import parse_qs
                query=parse_qs(scope.get('query_string',b'').decode())
                client_requests.append({'path':scope.get('path'),'query_keys':list(query),
                    'beta_true':query.get('beta')==['true'],'method':scope.get('method')})
            return await billing_app(scope,receive,send)
        server=uvicorn.Server(uvicorn.Config(audited_app,log_level='error',access_log=False))
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        deadline=time.monotonic()+10
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.02)
        if not server.started:raise RuntimeError('Fixture wallet server failed to start.')
        results=[];native=[]
        env={'GEMINI_CLI_TRUST_WORKSPACE':'true','KURT_WALLET_MODE':'1','KURT_WALLET_URL':f'http://127.0.0.1:{port}','KURT_WALLET_TOKEN':token}
        try:
            with patch.dict(os.environ,env),patch.object(persona,'KURT_DIR',root),patch.object(persona,'PERSONA_PATH',root/'persona.json'),patch.object(env_loader,'ENV_PATH',root/'empty.env'),workspace(root):
                for provider in ORIGINS:
                    start=len(upstream)
                    async def ask():
                        return ''.join([piece async for piece in ModelRouter().route(provider,'owner/model' if provider=='replicate' else 'fixture/model',
                            [{'role':'user','content':'Reply exactly KURT_NATIVE_READY'}])])
                    try:
                        text=asyncio.run(ask())
                        native.append({'provider':provider,'passed':bool(text),'request_count':len(upstream)-start})
                    except Exception as exc:native.append({'provider':provider,'passed':False,'error':str(exc)[:500]})
                for name in names:
                    start=len(upstream)
                    print('Checking CLI '+name,flush=True)
                    result=test_default_cli(name)
                    results.append({**result,'provider_requests':len(upstream)-start})
        finally:
            server.should_exit=True;thread.join(timeout=10);sock.close()
        history=store.history(tenant,100)
        return {'native':native,'cli':results,'upstream':upstream,'client_requests':client_requests,'wallet':store.summary(tenant),
                'financial_entries':len(history['entries']),'payment_processor_used':False,'real_provider_credentials_used':False,
                'passed':all(r['passed'] for r in native) and all(r['status']=='verified' for r in results)
                    and (not copilot_read or any(r.get('tool_roundtrip_verified') for r in upstream))}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cli',nargs='*',default=['deepseek','deepseek-cli','vibe','claude','gemini','codex','openclaw','copilot']);parser.add_argument('--output');parser.add_argument('--copilot-read',action='store_true');args=parser.parse_args()
    report=verify(args.cli,copilot_read=args.copilot_read)
    if args.output:Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
