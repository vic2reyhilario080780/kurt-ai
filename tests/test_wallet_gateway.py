import asyncio
from decimal import Decimal
import json
import tempfile
import time
import unittest
import httpx

from kurt.billing import WalletError
from kurt.billing.ledger import Wallet
from kurt.billing.gateway import Gateway
from kurt.billing.costs import receipt
from kurt.billing.app import BillingApp


class WalletGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.wallet=Wallet(self.tmp.name);self.tenant,self.token=self.wallet.grant('pro')
        self.other,self.other_token=self.wallet.grant('pro')
        self.wallet.manual_credit(self.tenant,'100','fund','Fixture only')
        self.calls=[];self.reply=None
        def handler(request):
            self.calls.append(request)
            if self.reply:return self.reply(request)
            return httpx.Response(200,json={'id':'gen-'+str(len(self.calls)),'choices':[{'message':{'content':'OK'}}],
                'usage':{'prompt_tokens':10,'completion_tokens':2,'cost':0.012345678901}})
        self.config={'currency':'USD','markup_percent':0,'providers':{p:{'models':['fixture/model'],'reserve_usd':'1'} for p in ('openrouter','mistral','openai','deepseek','google','anthropic','fal','replicate','groq')}}
        self.gateway=Gateway(self.wallet,self.config,{p:'server-only-'+p for p in self.config['providers']},transport=httpx.MockTransport(handler))
        self.app=BillingApp(self.wallet,self.gateway)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://wallet.example')
        self.addAsyncCleanup(self.client.aclose)

    def headers(self,key='one',token=None):return {'Authorization':'Bearer '+(token or self.token),'X-Kurt-Request-ID':key}
    async def post(self,key='one',provider='openrouter',path='/api/v1/chat/completions',payload=None,token=None):
        return await self.client.post('/wallet/proxy/'+provider+path,headers=self.headers(key,token),json=payload or {'model':'fixture/model','messages':[{'role':'user','content':'Hi'}]})

    async def test_reported_cost_is_exact_zero_markup_and_vendor_key_stays_server_side(self):
        response=await self.post()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.calls[0].headers['authorization'],'Bearer server-only-openrouter')
        self.assertNotIn(self.token,repr(self.calls[0].headers))
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'99.987654321099')
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'0')
        self.assertNotIn('server-only',response.text)
        self.assertEqual(len(self.wallet.history(self.tenant)['entries']),2)

    async def test_zero_reported_cost_is_free_not_default_estimate(self):
        self.reply=lambda request:httpx.Response(200,json={'id':'free','choices':[{'message':{'content':'OK'}}],'usage':{'cost':0}})
        response=await self.post()
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'100')
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'0')

    async def test_stream_terminal_usage_settled_before_complete_response(self):
        self.reply=lambda request:httpx.Response(200,headers={'content-type':'text/event-stream'},text='data: {"id":"gen-stream","choices":[{"delta":{"content":"Hi"}}]}\n\ndata: {"id":"gen-stream","choices":[],"usage":{"cost":0.02,"prompt_tokens":5,"completion_tokens":1}}\n\ndata: [DONE]\n\n')
        response=await self.post(payload={'model':'fixture/model','messages':[{'role':'user','content':'Hi'}],'stream':True})
        self.assertEqual(response.status_code,200)
        self.assertIn('[DONE]',response.text)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'99.98')
        self.assertEqual(response.headers['x-kurt-wallet-state'],'settled')

    async def test_missing_cost_is_pending_not_fake_charge_or_refund(self):
        response=await self.post(provider='mistral',path='/v1/chat/completions')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['x-kurt-wallet-state'],'pending')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'100')
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'1')

    async def test_insufficient_balance_model_and_callback_rejected_before_dispatch(self):
        for kwargs in ({'token':self.other_token},{'payload':{'model':'unapproved'}},{'payload':{'model':'fixture/model','webhook':'https://private.example'}}):
            response=await self.post(**kwargs)
            self.assertIn(response.status_code,(400,402,403))
        self.assertEqual(self.calls,[])

    async def test_duplicate_request_fails_without_second_paid_call(self):
        first=await self.post();second=await self.post()
        self.assertEqual(first.status_code,200)
        self.assertEqual(second.status_code,409)
        self.assertEqual(len(self.calls),1)

    async def test_scoped_cli_retry_fingerprint_and_provider_isolation(self):
        response=await self.client.post('/wallet/sessions',headers=self.headers(),json={'cli':'vibe'})
        self.assertEqual(response.status_code,200,response.text)
        token=response.json()['token']
        first=await self.post(provider='mistral',path='/v1/chat/completions',token=token)
        retry=await self.post(key='another-id',provider='mistral',path='/v1/chat/completions',token=token)
        wrong=await self.post(key='other-provider',token=token)
        self.assertEqual(first.status_code,200)
        self.assertEqual(retry.status_code,409)
        self.assertEqual(wrong.status_code,403)
        self.assertEqual((await self.client.get('/wallet/status',headers=self.headers(token=token))).status_code,403)
        self.assertEqual(len(self.calls),1)

    async def test_timeout_and_500_keep_hold_and_sanitize_errors(self):
        def timeout(request):raise httpx.ReadTimeout('ambiguous',request=request)
        self.reply=timeout
        response=await self.post()
        self.assertEqual(response.status_code,503)
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'1')
        self.reply=lambda request:httpx.Response(500,json={'error':{'message':'server-only-openrouter'}})
        response=await self.post(key='second')
        self.assertEqual(response.status_code,500)
        self.assertNotIn('server-only-openrouter',response.text)
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'2')

    async def test_interrupted_stream_keeps_generation_id_and_hold_for_reconciliation(self):
        class Broken(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'data: {"id":"gen-broken","choices":[{"delta":{"content":"partial"}}]}\n\n'
                raise httpx.ReadError('connection interrupted')
        self.reply=lambda request:httpx.Response(200,headers={'content-type':'text/event-stream','x-request-id':'header-broken'},stream=Broken())
        response=await self.post()
        self.assertEqual(response.status_code,503)
        row=self.wallet.history(self.tenant)['requests'][0]
        self.assertEqual(row['provider_id'],'gen-broken')
        self.assertEqual(row['status'],'pending')
        self.assertIsNone(row['cost_usd'])
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'1')

    async def test_auth_or_payment_rejection_before_inference_releases_hold(self):
        self.reply=lambda request:httpx.Response(402,json={'error':{'code':'insufficient_balance','message':'Insufficient Balance'}})
        response=await self.post()
        self.assertEqual(response.status_code,402)
        self.assertEqual(self.wallet.summary(self.tenant)['available_usd'],'100')

    async def test_redirect_cannot_send_server_key_elsewhere(self):
        self.reply=lambda request:httpx.Response(307,headers={'location':'https://attacker.example'})
        response=await self.post()
        self.assertEqual(response.status_code,502)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'1')

    async def test_fal_billing_receipt_request_and_endpoint_match_before_settlement(self):
        def handler(request):
            if request.url.host=='api.fal.ai':
                self.assertEqual(request.url.params['request_id'],'fal-job')
                self.assertEqual(request.headers['authorization'],'Key server-only-fal')
                return httpx.Response(200,json={'billing_events':[{'request_id':'fal-job','endpoint_id':'fixture/model','cost_estimate_nano_usd':25000000}]})
            return httpx.Response(200,headers={'x-fal-request-id':'fal-job'},json={'images':[{'url':'https://v3.fal.media/file.png'}]})
        self.reply=handler
        response=await self.post(provider='fal',path='/fixture/model',payload={'prompt':'A blue bird'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'99.975')
        self.assertEqual(response.headers['x-kurt-wallet-state'],'settled')

    async def test_delayed_fal_bill_does_not_prevent_artifact_output(self):
        def handler(request):
            if request.url.host=='api.fal.ai':return httpx.Response(403,json={'error':'billing permission absent'})
            return httpx.Response(200,headers={'x-fal-request-id':'fal-delayed'},json={'video':{'url':'https://v3.fal.media/file.mp4'}})
        self.reply=handler
        response=await self.post(provider='fal',path='/fixture/model',payload={'prompt':'A blue bird'})
        self.assertEqual(response.status_code,200)
        self.assertIn('file.mp4',response.text)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'100')
        self.assertEqual(response.headers['x-kurt-wallet-state'],'pending')

    async def test_replicate_polling_is_owned_by_requesting_tenant(self):
        def handler(request):
            if request.method=='GET' and '/models/' in request.url.path:
                return httpx.Response(200,json={'latest_version':{'id':'version-hash'}})
            return httpx.Response(200,json={'id':'prediction-1','status':'succeeded','output':['https://replicate.delivery/file.mp4']})
        self.reply=handler
        self.config['providers']['replicate']['models']=['owner/model']
        response=await self.client.get('/wallet/proxy/replicate/v1/models/owner/model',headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)
        response=await self.post(provider='replicate',path='/v1/predictions',payload={'version':'version-hash','input':{'prompt':'Hi'}})
        self.assertEqual(response.status_code,200,response.text)
        other=await self.client.get('/wallet/proxy/replicate/v1/predictions/prediction-1',headers=self.headers(token=self.other_token))
        self.assertEqual(other.status_code,404)
        mine=await self.client.get('/wallet/proxy/replicate/v1/predictions/prediction-1',headers=self.headers())
        self.assertEqual(mine.status_code,200)

    async def test_public_manual_credit_endpoints_do_not_exist(self):
        for path in ('/wallet/credit','/wallet/settle','/wallet/admin'):
            self.assertEqual((await self.client.post(path,headers=self.headers(),json={'amount':'1000'})).status_code,404)

    async def test_key_echoes_in_response_headers_are_never_returned_or_stored(self):
        self.reply=lambda request:httpx.Response(200,headers={'x-request-id':'server-only-openrouter'},
            json={'id':'server-only-openrouter','usage':{'cost':0}})
        response=await self.post()
        self.assertEqual(response.status_code,200)
        self.assertNotIn('server-only-openrouter',response.text)
        self.assertNotIn('x-request-id',response.headers)
        self.assertNotIn('server-only-openrouter',json.dumps(self.wallet.history(self.tenant)))

    async def test_estimated_token_rates_are_not_allowed_to_be_debited_as_actual_cost(self):
        config={'providers':{'openai':{'models':['*'],'reserve_usd':'1','rates_per_million_usd':{'input_tokens':'1'}}}}
        with self.assertRaisesRegex(ValueError,'Estimated-rate settlement is disabled'):
            Gateway(self.wallet,config,{'openai':'fixture'})

    async def test_claude_beta_query_is_allowed_without_arbitrary_query_forwarding(self):
        response=await self.post(provider='anthropic',path='/v1/messages?beta=true')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.calls[0].url.query,b'beta=true')

    async def test_gateway_rejects_nonzero_markup_and_unsafe_path(self):
        with self.assertRaises(ValueError):Gateway(self.wallet,{**self.config,'markup_percent':1},{})
        response=await self.client.post('/wallet/proxy/openrouter/api/v1/chat/completions?key=private',headers=self.headers(),json={'model':'fixture/model'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.calls,[])


class UsageTests(unittest.TestCase):
    def test_anthropic_stream_merge_and_cache_categories_not_double_counted(self):
        raw=b'data: {"type":"message_start","message":{"id":"msg-1","usage":{"input_tokens":10,"cache_read_input_tokens":5,"cache_creation_input_tokens":2}}}\n\ndata: {"type":"message_delta","usage":{"output_tokens":3}}\n\n'
        value=receipt(raw,'text/event-stream','anthropic')
        self.assertEqual(value['usage'],{'input_tokens':10,'output_tokens':3,'cached_tokens':5,'cache_write_tokens':2})

    def test_cache_tokens_output_reasoning_not_charged_twice(self):
        usage=receipt(b'{"usage":{"prompt_tokens":10,"completion_tokens":4,"prompt_tokens_details":{"cached_tokens":2},"completion_tokens_details":{"reasoning_tokens":3}}}', 'application/json','openai')['usage']
        self.assertEqual(usage['output_tokens'],4)
        self.assertEqual(usage['cached_tokens'],2)

    def test_zero_cost_missing_cost_and_google_thinking_are_distinct(self):
        self.assertEqual(receipt(b'{"usage":{"cost":0}}','application/json','openrouter')['cost_units'],0)
        self.assertIsNone(receipt(b'{"usage":{"prompt_tokens":1}}','application/json','openrouter')['cost_units'])
        usage=receipt(b'{"usageMetadata":{"promptTokenCount":5,"candidatesTokenCount":2,"thoughtsTokenCount":3,"cachedContentTokenCount":1}}','application/json','google')['usage']
        self.assertEqual(usage['output_tokens'],5)
