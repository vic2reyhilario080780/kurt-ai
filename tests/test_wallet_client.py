from contextlib import ExitStack
import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from typer.testing import CliRunner

from kurt.billing import WalletError
from kurt.billing.client import CLI_CONTEXT,WalletTransport,Client,active,cli_environment,codex_arguments,read_token
from kurt.billing.commands import initialize
from kurt.billing.gateway import CLI_PROVIDERS
from kurt.core import persona
from kurt.core.cli_orchestrator import _ai_cli_env


class WalletClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for key,value in [('KURT_DIR',self.root),('PERSONA_PATH',self.root/'persona.json')]:
            p=patch.object(persona,key,value);p.start();self.addCleanup(p.stop)

    def context(self,name):
        root=self.root/name;root.mkdir(exist_ok=True)
        return {'url':'https://wallet.example','token':'kurt_cli_'+'c'*43,'provider':CLI_PROVIDERS[name],
                'cli':name,'root':root,'profile':{'provider':CLI_PROVIDERS[name]}}

    def test_every_cli_receives_only_scoped_wallet_credentials(self):
        actual={'ANTHROPIC_API_KEY':'real-a','MISTRAL_API_KEY':'real-m','DEEPSEEK_API_KEY':'real-d','OPENAI_API_KEY':'real-o',
                'GOOGLE_API_KEY':'real-g','GITHUB_TOKEN':'real-gh','KURT_WALLET_TOKEN':'kurt_live_'+'OWNER'*9,'PATH':'/usr/bin','HOME':str(Path.home()),'KURT_WALLET_MODE':'1'}
        for name in CLI_PROVIDERS:
            with self.subTest(name=name),patch.dict(os.environ,actual,clear=True):
                context=self.context(name);reset=CLI_CONTEXT.set(context)
                try:env=_ai_cli_env('/installed/'+name)
                finally:CLI_CONTEXT.reset(reset)
            text=json.dumps(env)
            for key,value in actual.items():
                if key.endswith(('KEY','TOKEN')):self.assertNotIn(value,text)
            self.assertNotIn('KURT_WALLET_TOKEN',env)
            self.assertEqual(env['KURT_SESSION_TOKEN'],context['token'])
            self.assertEqual(env['HOME'],str(context['root']))
            if name in ('deepseek','deepseek-cli'):self.assertEqual(env['DEEPSEEK_BASE_URL'],'https://wallet.example/wallet/proxy/deepseek')
            if name=='vibe':self.assertIn('/wallet/proxy/mistral',env['VIBE_PROVIDERS'])
            if name=='gemini':self.assertIn('/wallet/proxy/google',env['GOOGLE_GEMINI_BASE_URL'])
            if name=='openclaw':
                config=Path(env['OPENCLAW_CONFIG_PATH']).read_text()
                self.assertIn('/wallet/proxy/groq',config);self.assertNotIn('real-',config)

    def test_gemini_keeps_existing_trust_decisions_without_automatic_trust_bypass(self):
        original=self.root/'original-home';source=original/'.gemini';source.mkdir(parents=True)
        policy={'/approved/project':'TRUST_FOLDER','/untrusted/project':'DO_NOT_TRUST'}
        (source/'trustedFolders.json').write_text(json.dumps(policy))
        context=self.context('gemini');reset=CLI_CONTEXT.set(context)
        try:
            with patch('pathlib.Path.home',return_value=original):env=cli_environment('gemini',{'PATH':'/usr/bin'})
        finally:CLI_CONTEXT.reset(reset)
        copied=json.loads((context['root']/'.gemini/trustedFolders.json').read_text())
        self.assertEqual(copied,policy)
        self.assertNotIn('GEMINI_CLI_TRUST_WORKSPACE',env)
        settings=json.loads((context['root']/'.gemini/settings.json').read_text())
        self.assertEqual(settings['security']['auth']['selectedType'],'gemini-api-key')

    def test_codex_wallet_arguments_keep_permission_policy_and_force_gateway(self):
        context=self.context('codex');reset=CLI_CONTEXT.set(context)
        try:args=codex_arguments()
        finally:CLI_CONTEXT.reset(reset)
        joined=' '.join(args)
        self.assertIn('/wallet/proxy/openai/v1',joined)
        self.assertIn('request_max_retries',joined)
        self.assertIn('KURT_SESSION_TOKEN',joined)
        self.assertNotIn('dangerously',joined)

    def test_private_token_file_and_zero_balance_initialization(self):
        root=self.root/'new-wallet';result=initialize(root)
        token=read_token(root/'owner.kurt-token')
        self.assertTrue(token.startswith('kurt_live_'))
        self.assertNotIn(token,json.dumps(result))
        self.assertEqual(result['balance_usd'],'0');self.assertFalse(result['payments_enabled'])
        self.assertEqual((root/'owner.kurt-token').stat().st_mode&0o777,0o600)
        with self.assertRaises(ValueError):initialize(root)
        (root/'owner.kurt-token').chmod(0o644)
        with self.assertRaises(ValueError):read_token(root/'owner.kurt-token')

    def test_explicit_environment_and_saved_mode_do_not_silently_fallback(self):
        persona.save_persona({'wallet_enabled':True})
        with patch.dict(os.environ,{},clear=True):self.assertTrue(active())
        with patch.dict(os.environ,{'KURT_WALLET_MODE':'0'},clear=True):self.assertFalse(active())
        with patch.dict(os.environ,{'KURT_WALLET_MODE':'invalid'},clear=True),self.assertRaises(WalletError):active()

    def test_ephemeral_and_owner_wallet_tokens_are_redacted_in_cli_errors(self):
        from kurt.utils.security import redact
        for prefix in ('kurt_live_','kurt_cli_'):
            token=prefix+'aB9_'*11
            self.assertNotIn(token,redact('Provider error: '+token))

    def test_connect_is_verified_before_saving_wallet_mode(self):
        from kurt.billing.commands import connect
        result=initialize(self.root/'wallet')
        with patch.object(Client,'request',return_value={'currency':'USD','balance_usd':'0','markup_percent':0}):
            connect('https://wallet.example',result['token_file'])
        settings=persona.load_persona()
        self.assertTrue(settings['wallet_enabled'])
        self.assertEqual(settings['wallet_url'],'https://wallet.example')
        self.assertNotIn(read_token(result['token_file']),json.dumps(settings))

    def test_wallet_native_search_does_not_charge_unmetered_paid_search_keys(self):
        from kurt.core.web_browse import search_web
        with patch('kurt.billing.client.active',return_value=True), \
             patch('requests.get') as get,patch('requests.post') as post, \
             patch('kurt.core.web_browse._ddg_scrape',return_value=[{'title':'fixture','url':'https://example.org','snippet':'fixture'}]), \
             patch('kurt.core.web_browse._google_news_rss',return_value=[]):
            result=search_web('fixture query')
        self.assertTrue(result.success);get.assert_not_called();post.assert_not_called()

    def test_cloud_vision_sdk_uses_wallet_instead_of_bypassing_billing(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        from kurt.core.vision import describe_screen_claude
        factory=Mock();factory.return_value.messages.create.return_value=SimpleNamespace(content=[SimpleNamespace(text='fixture image')])
        wallet=Client('https://wallet.example','kurt_live_'+'a'*43)
        with patch.dict(sys.modules,{'anthropic':SimpleNamespace(Anthropic=factory)}), \
             patch.dict(os.environ,{'KURT_ALLOW_CLOUD_VISION':'1'}), \
             patch('kurt.billing.client.active',return_value=True),patch('kurt.billing.client.from_env',return_value=wallet):
            result=describe_screen_claude('fixture-image')
        self.assertTrue(result.success)
        self.assertEqual(factory.call_args.kwargs['base_url'],'https://wallet.example/wallet/proxy/anthropic')
        self.assertEqual(factory.call_args.kwargs['max_retries'],0)
        self.assertEqual(factory.call_args.kwargs['api_key'],wallet._token)

    def test_wallet_cli_has_no_payment_success_without_processor(self):
        from kurt.main import app
        result=CliRunner().invoke(app,['wallet','--help'])
        self.assertEqual(result.exit_code,0,result.output)
        self.assertIn('topup',result.output);self.assertIn('settle',result.output)


class WalletTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_vendor_request_is_rewritten_without_provider_key(self):
        calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json={'ok':True})
        wallet=Client('https://wallet.example','kurt_live_'+'a'*43)
        async with httpx.AsyncClient(transport=WalletTransport(wallet,httpx.MockTransport(handler))) as client:
            response=await client.post('https://api.mistral.ai/v1/chat/completions',headers={'Authorization':'Bearer REAL_VENDOR_SECRET'},json={'model':'m','messages':[]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(calls[0].url.host,'wallet.example')
        self.assertEqual(calls[0].url.path,'/wallet/proxy/mistral/v1/chat/completions')
        self.assertEqual(calls[0].headers['authorization'],'Bearer '+wallet._token)
        self.assertNotIn('REAL_VENDOR_SECRET',str(calls[0].headers))
        self.assertIn('x-kurt-request-id',calls[0].headers)

    async def test_wallet_failure_raises_no_replay_error_instead_of_retrying_provider(self):
        count=[]
        def handler(request):count.append(request);return httpx.Response(402,json={'error':{'code':'insufficient_wallet_balance'}})
        wallet=Client('https://wallet.example','kurt_live_'+'a'*43)
        async with httpx.AsyncClient(transport=WalletTransport(wallet,httpx.MockTransport(handler))) as client:
            with self.assertRaises(WalletError) as error:await client.post('https://api.deepseek.com/chat/completions',json={'model':'deepseek-flash'})
        self.assertTrue(error.exception.no_replay);self.assertEqual(len(count),1)

    async def test_unknown_origin_fails_closed(self):
        wallet=Client('https://wallet.example','kurt_live_'+'a'*43)
        async with httpx.AsyncClient(transport=WalletTransport(wallet)) as client:
            with self.assertRaises(WalletError):await client.post('https://other.example/steal')
