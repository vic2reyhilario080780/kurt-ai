import asyncio
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import httpx

from kurt.models import providers, additional, catalog
from kurt.core import persona, command_palette as picker
from kurt.core.router import ModelRouter


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.env = root / '.env'
        for context in (patch.object(providers, 'credential_path', return_value=self.env),
                        patch.object(persona, 'KURT_DIR', root), patch.object(persona, 'PERSONA_PATH', root/'persona.json'),
                        patch.dict(os.environ, {}, clear=True)):
            context.start(); self.addCleanup(context.stop)

    def test_private_save_preserves_other_keys_and_refreshes_aliases(self):
        self.env.write_text("# original\nOTHER_KEY='leave-me-alone'\nLITERAL='${KEEP_LITERAL}'\nGOOGLE_AI_KEY='old'\n")
        os.environ['GEMINI_API_KEY'] = 'stale-shell-key'
        providers.save_provider_key('google', 'new-synthetic-google-token')
        self.assertEqual(providers.provider_key('google'), 'new-synthetic-google-token')
        self.assertNotIn('GEMINI_API_KEY', os.environ)
        from dotenv import dotenv_values
        data = dotenv_values(self.env, interpolate=False)
        self.assertEqual(data['OTHER_KEY'], 'leave-me-alone')
        self.assertEqual(data['LITERAL'], '${KEEP_LITERAL}')
        self.assertEqual(stat.S_IMODE(self.env.stat().st_mode), 0o600)
        self.assertNotIn('old', self.env.read_text())

    def test_bad_or_cancelled_key_never_changes_environment_or_file(self):
        self.env.write_text('OTHER=value\n')
        for value in ('', 'YOUR_API_KEY', 'token with spaces', 'token\nINJECT=yes', 'x'*4097):
            with self.subTest(value_length=len(value)), self.assertRaises(ValueError):
                providers.save_provider_key('together', value)
        with patch('rich.prompt.Prompt.ask', return_value=''):
            self.assertIn('Cancelled', providers.request_provider_key('together'))
        self.assertEqual(self.env.read_text(), 'OTHER=value\n')
        self.assertNotIn('TOGETHER_API_KEY', os.environ)

    def test_masked_prompt_has_no_key_in_status_and_saved_file_wins(self):
        secret = 'synthetic-private-provider-token'
        with patch('rich.prompt.Prompt.ask', return_value=secret) as prompt:
            status = providers.request_provider_key('huggingface')
        self.assertTrue(prompt.call_args.kwargs['password'])
        self.assertNotIn(secret, status)
        os.environ['HF_TOKEN'] = 'stale-shell-token'
        self.assertEqual(providers.provider_key('huggingface'), secret)

    def test_byok_and_wallet_are_explicit_separate_choices(self):
        providers.save_provider_key('openrouter', 'synthetic-openrouter-key')
        self.assertFalse(providers.uses_byok('openrouter'))
        providers.confirm_byok('openrouter')
        self.assertTrue(providers.uses_byok('openrouter'))
        providers.confirm_wallet('openrouter')
        self.assertFalse(providers.uses_byok('openrouter'))
        with self.assertRaises(ValueError):
            providers.confirm_wallet('together')
        self.assertTrue(providers.uses_byok('together'))


class OptionalCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.real_client = httpx.Client
        for context in (patch.object(additional, 'CACHE_DIR', self.root), patch.object(additional, '_memory', {}),
                        patch.object(providers, 'credential_path', return_value=self.root/'.env')):
            context.start(); self.addCleanup(context.stop)

    def client(self, handler):
        return lambda **kw: self.real_client(transport=httpx.MockTransport(handler), **kw)

    def test_dedup_uses_exact_identity_and_explicit_hf_metadata_not_name_guessing(self):
        primary = [{'id': 'vendor/primary', 'hugging_face_id': 'Lab/Model-v1'}]
        models = [{'id': 'Lab/Model-v1'}, {'id': 'Lab/Model-v2'}, {'id': 'Lab/Model-v1-Turbo'}]
        visible, excluded = additional.without_primary_duplicates('huggingface', models, primary, [])
        self.assertEqual([m['id'] for m in excluded], ['Lab/Model-v1'])
        self.assertEqual(len(visible), 2)
        visible, excluded = additional.without_primary_duplicates('fireworks',
            [{'id': 'accounts/fireworks/models/alias', 'huggingFaceUrl': 'https://huggingface.co/Lab/Model-v1'}], primary, [])
        self.assertFalse(visible); self.assertEqual(len(excluded), 1)

    def test_missing_key_does_not_fake_catalog_or_send_other_credentials(self):
        with patch.object(additional, 'provider_key', return_value=''), patch.object(additional.httpx, 'Client') as client:
            result = additional.fetch_catalog('wavespeed')
        self.assertIn('API key', result['error'])
        client.assert_not_called()

    def test_fireworks_all_pages_and_normalized_chat_contract(self):
        calls = []
        def handler(req):
            calls.append(req)
            second = bool(req.url.params.get('pageToken'))
            return httpx.Response(200, json={'models': [{'name': 'accounts/fireworks/models/'+('two' if second else 'one'),
                'supportsServerless': True, 'baseModelDetails': {'modelType': 'llm'}}],
                'nextPageToken': '' if second else 'page2', 'totalSize': 2})
        with patch.object(additional, 'provider_key', return_value='synthetic-fireworks-key'), \
             patch.object(additional.httpx, 'Client', self.client(handler)):
            result = additional.fetch_catalog('fireworks')
        self.assertTrue(result['complete']); self.assertEqual(len(result['models']), 2)
        self.assertEqual(catalog.default_roles('fireworks', result['models'][0]), ['chat'])
        self.assertTrue(all(r.headers['Authorization']=='Bearer synthetic-fireworks-key' for r in calls))

    def test_replicate_load_more_and_untrusted_continuation_retains_previous_data(self):
        calls = []
        def handler(req):
            cursor = req.url.params.get('cursor')
            calls.append(cursor)
            return httpx.Response(200, json={'results': [{'owner': 'owner', 'name': cursor or 'one'}],
                'next': 'https://api.replicate.com/v1/models?cursor=two' if not cursor else None})
        with patch.object(additional, 'provider_key', return_value='synthetic'), \
             patch.object(additional.httpx, 'Client', self.client(handler)):
            first = additional.fetch_catalog('replicate', page_budget=1)
            self.assertFalse(first['complete'])
            second = additional.fetch_catalog('replicate', more=True)
        self.assertTrue(second['complete']); self.assertEqual(len(second['models']), 2)
        bad = lambda req: httpx.Response(200, json={'results': [], 'next': 'https://evil.example/steal?cursor=two'})
        with patch.object(additional, 'provider_key', return_value='synthetic'), \
             patch.object(additional.httpx, 'Client', self.client(bad)):
            failed = additional.fetch_catalog('replicate', refresh=True)
        self.assertEqual(failed['models'], second['models'])
        self.assertIn('error', failed)
        self.assertEqual(len(calls), 2)

    def test_wave_catalog_only_enables_implemented_prompt_contracts(self):
        def model(required):
            return additional.normalize('wavespeed', {'model_id': 'vendor/model', 'type': 'text-to-image',
                'api_schema': {'api_schemas': [{'type': 'model_run', 'method': 'POST', 'request_schema': {
                    'properties': {'prompt': {'type': 'string'}, 'image': {'type': 'string'}}, 'required': required}}]}})
        self.assertEqual(catalog.default_roles('wavespeed', model(['prompt'])), ['image'])
        self.assertEqual(catalog.default_roles('wavespeed', model(['prompt', 'image'])), [])


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_new_chat_endpoints_use_only_own_key_and_skip_wallet(self):
        for provider in ('huggingface', 'together', 'fireworks', 'novita'):
            seen = []
            def handler(req):
                seen.append(req)
                return httpx.Response(200, text='data: '+json.dumps({'choices':[{'delta':{'content':'OK'}}]})+'\n\ndata: [DONE]\n\n')
            router = ModelRouter()
            router.byok_keys = {provider: 'synthetic-'+provider}
            with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler))):
                text = ''.join([c async for c in router.route(provider, 'vendor/model', [{'role':'user','content':'test'}])])
            self.assertEqual(text, 'OK')
            self.assertEqual(str(seen[0].url), providers.PROVIDERS[provider]['chat_url'])
            self.assertEqual(seen[0].headers['Authorization'], 'Bearer synthetic-'+provider)
        with patch('kurt.billing.client.active', return_value=True), patch('kurt.billing.client.WalletTransport') as wallet:
            async with ModelRouter()._http_client(provider='together'):
                pass
        wallet.assert_not_called()

    async def test_missing_byok_key_cannot_silently_use_openrouter(self):
        router = ModelRouter(); router.byok_keys = {'together': ''}; router.openrouter_key = 'synthetic-openrouter'
        with self.assertRaisesRegex(RuntimeError, 'Missing API key'):
            async for _ in router.route('together', 'model', [{'role':'user','content':'test'}]):
                pass

    async def test_wavespeed_polls_job_without_replaying_submission_or_using_supplied_poll_url(self):
        requests = []
        def handler(req):
            requests.append(req)
            if req.method == 'POST':
                return httpx.Response(200, json={'code':200,'data':{'id':'job_1','status':'processing','urls':{'get':'https://evil.example'}}})
            return httpx.Response(200, json={'data':{'id':'job_1','status':'completed','outputs':['https://cdn.wavespeed.ai/test.png']}})
        from kurt.models.media_providers import generate_wavespeed
        router=ModelRouter();router.byok_keys={'wavespeed':'synthetic-wave-key'}
        contract={'id':'vendor/model','category':'text-to-image','prompt_compatible':True}
        with patch('kurt.models.media_providers.find_cached_model',return_value=contract), \
             patch('kurt.models.media_providers.asyncio.sleep'), \
             patch.object(router,'_http_client',return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler))):
            result=''.join([c async for c in generate_wavespeed(router,'vendor/model','synthetic','image')])
        self.assertEqual(result,'https://cdn.wavespeed.ai/test.png')
        self.assertEqual([r.method for r in requests],['POST','GET'])
        self.assertEqual(str(requests[1].url),'https://api.wavespeed.ai/api/v3/predictions/job_1/result')


class KeyPickerTests(unittest.IsolatedAsyncioTestCase):
    async def test_key_input_and_website_keep_picker_open_then_confirm_uses_existing_dispatch(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        real_session=picker.PromptSession
        state_key={'saved':False}
        def input_key(provider, value):
            self.assertEqual(value,'synthetic-private-picker-token')
            state_key['saved']=True
        command='/model default vendor/unique together'
        from urllib.parse import quote
        with create_pipe_input() as pipe, \
             patch.object(providers,'provider_key',side_effect=lambda p:'synthetic-key' if state_key['saved'] else ''), \
             patch.object(providers,'save_provider_key',side_effect=input_key) as prompt, \
             patch.object(providers,'confirm_byok') as confirm, \
             patch('kurt.core.connector_pages.open_page',return_value='Browser opened; return here.') as browser, \
             patch.object(picker,'PromptSession',lambda **kw:real_session(input=pipe,output=DummyOutput(),**kw)):
            session,state=picker._build_session();state.is_open=True
            state.view='model_setup:together:'+quote(command,safe='')
            task=asyncio.create_task(session.prompt_async(default='/'))
            try:
                await asyncio.sleep(.05)
                self.assertFalse(any(r.get('billing')=='byok' for r in picker._current_items(state,'')))
                state.index=next(i for i,r in enumerate(picker._current_items(state,'')) if r['kind']=='browser')
                pipe.send_text('\r');await asyncio.sleep(.05)
                browser.assert_called_once();self.assertFalse(task.done())
                state.index=next(i for i,r in enumerate(picker._current_items(state,'')) if r['kind']=='provider_key')
                pipe.send_text('\r');await asyncio.sleep(.05)
                self.assertEqual(state.view,'provider_key_input:together')
                self.assertTrue(session.is_password())
                pipe.send_text('synthetic-private-picker-token\r');await asyncio.sleep(.05)
                prompt.assert_called_once_with('together','synthetic-private-picker-token');self.assertFalse(task.done())
                self.assertEqual(session.default_buffer.text,'/')
                session.default_buffer.undo()
                self.assertNotIn('synthetic-private-picker-token',session.default_buffer.text)
                session.default_buffer.text='/'
                state.index=next(i for i,r in enumerate(picker._current_items(state,'')) if r.get('billing')=='byok')
                pipe.send_text('\r')
                self.assertEqual(await asyncio.wait_for(task,2),command)
                confirm.assert_called_once_with('together')
            finally:
                if not task.done():
                    pipe.send_text('\x03')
                    try:await task
                    except BaseException:pass


class SecretVoiceTests(unittest.TestCase):
    def test_voice_event_cannot_capture_or_submit_api_key_draft(self):
        from types import SimpleNamespace
        from kurt.core.voice_input import VoiceInputBridge, VOICE_READY
        app=SimpleNamespace(_kurt_secret_input=True,is_done=False,
                            current_buffer=SimpleNamespace(text='synthetic-private-token'),exit=Mock(),invalidate=Mock())
        loop=Mock();loop.call_soon_threadsafe.side_effect=lambda callback:callback()
        bridge=VoiceInputBridge();bridge.bind(app,loop);bridge.submit('queued speech')
        app.exit.assert_not_called();self.assertEqual(bridge.take_draft(),'')
        app._kurt_secret_input=False;app.current_buffer.text='/'
        bridge.set_status('waiting')
        app.exit.assert_called_once_with(result=VOICE_READY)
        self.assertEqual(bridge.take_draft(),'/')
