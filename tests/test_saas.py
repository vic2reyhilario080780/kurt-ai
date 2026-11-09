"""Hosted boundaries: synthetic tenants/tokens/provider keys, no live services."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

from kurt.saas.app import App
from kurt.saas.protocol import MAX_BODY, decode, native_request
from kurt.saas.runner import IsolatedRunner, WorkerUnavailable
from kurt.saas.store import Denied, Store

CAPABILITY = 'kurt-skill--shopee-orders--gross_sales--describe'
IMAGE = 'registry.example/kurt-worker@sha256:' + 'a'*64


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name)
        self.a,self.token=self.store.grant('starter')

    def test_token_is_hashed_and_files_private(self):
        self.assertNotIn(self.token.encode(),self.store.path.read_bytes())
        self.assertEqual(self.store.path.stat().st_mode&0o777,0o600)
        self.assertEqual(self.store.root.stat().st_mode&0o777,0o700)

    def test_revocation_and_expiration(self):
        self.store.revoke(self.a)
        with self.assertRaises(Denied): self.store.identity(self.token)
        _,token=self.store.grant('starter',tenant=self.a)
        with self.store.db() as db: db.execute('UPDATE tokens SET expires=0')
        with self.assertRaises(Denied): self.store.identity(token)

    def test_quotas_are_per_tenant(self):
        with patch.dict('kurt.saas.store.PLANS',{'starter':{'daily':2,'minute':10,'concurrent':1}}):
            for _ in range(2):
                tenant,lease=self.store.reserve(self.token,'chat');self.store.finish(tenant,lease,'completed')
            with self.assertRaises(Denied) as denied: self.store.reserve(self.token,'chat')
            self.assertEqual(denied.exception.code,'quota_exceeded')
            other,token=self.store.grant('starter')
            tenant,lease=self.store.reserve(token,'chat')
            self.assertEqual(tenant,other); self.store.finish(tenant,lease,'completed')

    def test_parallel_reservations_cannot_bypass_concurrency(self):
        def attempt(_):
            try: return self.store.reserve(self.token,'native')
            except Denied: return None
        with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(attempt,range(8)))
        self.assertEqual(len([r for r in results if r]),1)

    def test_other_tenant_cannot_finish_a_lease(self):
        b,_=self.store.grant('starter')
        tenant,lease=self.store.reserve(self.token,'chat')
        self.store.finish(b,lease,'completed')
        with self.assertRaises(Denied): self.store.reserve(self.token,'chat')
        self.store.finish(tenant,lease,'completed')
        self.store.reserve(self.token,'chat')

    def test_subscription_expiration_blocks_work(self):
        with self.store.db() as db: db.execute('UPDATE tenants SET active_until=0')
        with self.assertRaises(Denied) as denied: self.store.reserve(self.token,'chat')
        self.assertEqual(denied.exception.status,403)


class FakeGateway:
    async def chat(self,messages): return {'content':messages[-1]['content']}


class APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name)
        self.a,self.token=self.store.grant('starter')
        self.b,self.other=self.store.grant('pro')
        self.app=App(self.store,FakeGateway())
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://test')
        self.addAsyncCleanup(self.client.aclose)

    def auth(self,token=None): return {'Authorization':'Bearer '+(token or self.token)}

    async def test_authentication_and_no_cross_tenant_selector(self):
        self.assertEqual((await self.client.get('/v1/me')).status_code,401)
        a=await self.client.get('/v1/me',headers={**self.auth(),'X-Tenant-ID':self.b})
        b=await self.client.get('/v1/me',headers=self.auth(self.other))
        self.assertEqual(a.json()['tenant']['id'],self.a)
        self.assertEqual(b.json()['tenant']['id'],self.b)
        self.assertNotIn(self.other,a.text)

    async def test_client_cannot_upgrade_plan_or_choose_tenant(self):
        response=await self.client.post('/v1/chat',headers=self.auth(),json={'tenant':self.b,'plan':'pro','messages':[{'role':'user','content':'hi'}]})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.store.identity(self.token)['plan'],'starter')

    async def test_https_and_no_url_token(self):
        response=await self.client.get('http://test/v1/me',headers=self.auth())
        self.assertEqual(response.status_code,400)
        response=await self.client.get('/v1/me?token='+self.token)
        self.assertEqual(response.status_code,400)
        self.assertNotIn(self.token,response.text)

    async def test_no_cors_or_caching(self):
        response=await self.client.get('/v1/me',headers={**self.auth(),'Origin':'https://evil.test'})
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertNotIn('access-control-allow-origin',response.headers)

    async def test_shell_desktop_paths_and_model_overrides_rejected(self):
        for value in ({'cmd':'cat ~/.kurt/.env'},{'capability_id':CAPABILITY,'input_path':'/etc/passwd'},
                      {'messages':[{'role':'user','content':'hi'}],'model':'evil','tools':[]}):
            response=await self.client.post('/v1/native/run' if 'messages' not in value else '/v1/chat',headers=self.auth(),json=value)
            self.assertEqual(response.status_code,400)

    async def test_native_unavailable_has_no_host_fallback(self):
        response=await self.client.post('/v1/native/run',headers=self.auth(),json={'capability_id':CAPABILITY,'rows':[{'x':1}]})
        self.assertEqual(response.status_code,503)

    async def test_duplicate_json_and_nonfinite_numbers_rejected(self):
        for content in ('{"messages":[],"messages":[]}', '{"messages":NaN}'):
            response=await self.client.post('/v1/chat',headers={**self.auth(),'Content-Type':'application/json'},content=content)
            self.assertEqual(response.status_code,400)

    async def test_body_and_messages_bounded(self):
        response=await self.client.post('/v1/chat',headers={**self.auth(),'Content-Type':'application/json','Content-Length':str(MAX_BODY+1)},content='{}')
        self.assertEqual(response.status_code,413)
        response=await self.client.post('/v1/chat',headers=self.auth(),json={'messages':[{'role':'user','content':'x'*32769}]})
        self.assertEqual(response.status_code,400)

    async def test_tokens_redacted_and_prompts_not_persisted(self):
        prompt='PRIVATE CUSTOMER DATA '+self.token
        response=await self.client.post('/v1/chat',headers=self.auth(),json={'messages':[{'role':'user','content':prompt}]})
        self.assertEqual(response.status_code,200)
        self.assertNotIn(self.token,response.text)
        self.assertNotIn(b'PRIVATE CUSTOMER DATA',self.store.path.read_bytes())
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT status FROM audit').fetchone()[0],'completed')

    async def test_errors_do_not_echo_credentials(self):
        class Broken:
            async def chat(self,messages): raise RuntimeError('secret-key-and-private-prompt')
        self.app.gateway=Broken()
        response=await self.client.post('/v1/chat',headers=self.auth(),json={'messages':[{'role':'user','content':'hi'}]})
        self.assertEqual(response.status_code,500)
        self.assertNotIn('secret-key',response.text)
        with self.store.db() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM leases').fetchone()[0],0)

    async def test_disconnection_does_not_release_running_job(self):
        started,release=asyncio.Event(),asyncio.Event()
        class Slow:
            async def chat(self,messages):
                started.set(); await release.wait(); return {'content':'ok'}
        self.app.gateway=Slow()
        request=asyncio.create_task(self.client.post('/v1/chat',headers=self.auth(),json={'messages':[{'role':'user','content':'hi'}]}))
        await started.wait(); request.cancel()
        with self.assertRaises(asyncio.CancelledError): await request
        with self.assertRaises(Denied): self.store.reserve(self.token,'chat')
        release.set()
        for _ in range(10): await asyncio.sleep(0)
        tenant,lease=self.store.reserve(self.token,'chat');self.store.finish(tenant,lease,'completed')

    async def test_provider_key_only_in_auth_header(self):
        from kurt.saas.gateway import GroqGateway
        secret='server-key-synthetic-123456789'
        seen=[]
        def upstream(request):
            seen.append(request)
            return httpx.Response(200,json={'choices':[{'message':{'content':secret}}]})
        original=httpx.AsyncClient
        def provider_client(**kwargs): return original(transport=httpx.MockTransport(upstream),**kwargs)
        self.app.gateway=GroqGateway(secret)
        with patch('kurt.saas.gateway.httpx.AsyncClient',side_effect=provider_client):
            response=await self.client.post('/v1/chat',headers=self.auth(),json={'messages':[{'role':'user','content':secret}]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(seen[0].headers['Authorization'],'Bearer '+secret)
        self.assertNotIn(secret,seen[0].content.decode())
        self.assertNotIn(secret,response.text)
        payload=json.loads(seen[0].content)
        self.assertEqual(payload['max_tokens'],1024)
        self.assertNotIn('tools',payload)


class RunnerTests(unittest.TestCase):
    def test_image_must_be_digest_pinned(self):
        for image in ('image:latest','image; cat /etc/passwd',''):
            with self.assertRaises(ValueError): IsolatedRunner(image)

    def test_no_mounts_secrets_host_network_or_custom_entrypoint(self):
        runner=IsolatedRunner(IMAGE)
        args=runner.create_args('kurt-job-fixed')
        for flag in ('--runtime=runsc','--network=none','--read-only','--cap-drop=ALL','--user=10001:10001','--pull=never','--memory=256m','--pids-limit=64'):
            self.assertIn(flag,args)
        self.assertFalse(any(arg.startswith(('--volume','--mount','--privileged','--publish')) for arg in args))
        self.assertNotIn('GROQ_API_KEY',str(args))
        self.assertEqual(args[-3:], [IMAGE,'-m','kurt.saas.worker'])

    def test_unsupported_host_fails_closed(self):
        with patch('kurt.saas.runner.platform.system',return_value='Darwin'):
            with self.assertRaises(WorkerUnavailable): IsolatedRunner(IMAGE).run({'capability_id':CAPABILITY,'rows':[{'x':1}]})

    def test_missing_runtime_or_resource_controllers_fail_closed(self):
        runner=IsolatedRunner(IMAGE)
        data={'Runtimes':{'runsc':{'path':'runsc'}},'OSType':'linux','CgroupVersion':'2','SecurityOptions':['name=rootless'],'MemoryLimit':True,'CpuCfsQuota':True,'PidsLimit':True}
        for broken in ({**data,'Runtimes':{}},{**data,'SecurityOptions':[]},{**data,'MemoryLimit':False},{**data,'CgroupVersion':'1'}):
            with patch('kurt.saas.runner.platform.system',return_value='Linux'),patch('kurt.saas.runner.shutil.which',return_value='/usr/bin/docker'),patch.object(runner,'_control',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(broken))):
                with self.assertRaises(WorkerUnavailable):runner.preflight('/tmp')

    def test_timeout_removes_container(self):
        runner=IsolatedRunner(IMAGE)
        with patch.object(runner,'preflight'),patch.object(runner,'_control',return_value=SimpleNamespace(returncode=0)) as control,patch.object(runner,'_attached',side_effect=WorkerUnavailable('deadline')):
            with self.assertRaises(WorkerUnavailable):runner.run({'capability_id':CAPABILITY,'rows':[{'x':1}]})
        self.assertEqual(control.call_args.args[1][:2],['rm','--force'])

    def test_worker_executes_real_native_recipe_without_site_packages(self):
        from kurt.capabilities.runtime import domain_pack
        from kurt.capabilities.engine import sample_rows
        rows=sample_rows(domain_pack('shopee-orders')['profile'])
        with tempfile.TemporaryDirectory() as home:
            response=subprocess.run([sys.executable,'-S','-m','kurt.saas.worker'],input=json.dumps({'capability_id':CAPABILITY,'rows':rows}),capture_output=True,text=True,timeout=15,
                                    env={'PATH':os.defpath,'HOME':home,'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
        self.assertEqual(response.returncode,0,response.stderr)
        result=json.loads(response.stdout)
        self.assertEqual(result['id'],CAPABILITY)
        self.assertNotIn('error',result)


if __name__=='__main__':unittest.main()
