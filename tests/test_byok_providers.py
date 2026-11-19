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
                        patch.object(providers, 'credential_path', return_value=self.root/'.env'),
                        patch.object(persona, 'KURT_DIR', self.root),
                        patch.object(persona, 'PERSONA_PATH', self.root/'persona.json')):
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

    def test_hf_inference_and_full_hub_are_separate_paginated_searchable_browse_catalogs(self):
        seen_params = []
        def handler(req):
            seen_params.append(dict(req.url.params))
            if req.url.params.get('search'):
                return httpx.Response(200, json=[
                    {'id': 'Qwen/Qwen3-0.6B', 'pipeline_tag': 'text-generation', 'downloads': 16000000, 'likes': 1900, 'library_name': 'transformers'}
                ])
            cursor = req.url.params.get('cursor')
            is_inf = req.url.params.get('inference_provider') == 'all'
            prefix = 'inf' if is_inf else 'hub'
            headers = {}
            if not cursor:
                q = 'inference_provider=all&' if is_inf else ''
                headers['link'] = f'<https://huggingface.co/api/models?{q}limit=100&cursor=page2>; rel="next"'
            return httpx.Response(200, headers=headers, json=[
                {'id': f'org/{prefix}-{cursor or "p1"}', 'pipeline_tag': 'text-to-image' if is_inf else 'sentence-similarity',
                 'downloads': 5000, 'likes': 42}
            ])
        with patch.object(additional, 'provider_key', return_value=''), \
             patch.object(additional.httpx, 'Client', self.client(handler)):
            inf_p1 = additional.fetch_catalog('huggingface_inference', page_budget=1)
            self.assertFalse(inf_p1['complete'])
            self.assertEqual(inf_p1['next'], 'page2')
            inf_p2 = additional.fetch_catalog('huggingface_inference', more=True, page_budget=1)
            self.assertTrue(inf_p2['complete'])
            self.assertEqual(len(inf_p2['models']), 2)
            hub_p1 = additional.fetch_catalog('huggingface_hub', page_budget=1)
            self.assertFalse(hub_p1['complete'])
            self.assertEqual(hub_p1['models'][0]['id'], 'org/hub-p1')
            # Live search merges results without discarding existing models
            sr = additional.search_hub_catalog('huggingface_inference', 'qwen')
            self.assertEqual(sr['matched'], 1)
            self.assertEqual(sr['total_loaded'], 3)
        self.assertEqual(seen_params[0].get('inference_provider'), 'all')
        self.assertNotIn('inference_provider', seen_params[2])
        self.assertEqual(seen_params[3].get('search'), 'qwen')
        self.assertEqual(seen_params[3].get('inference_provider'), 'all')
        self.assertEqual(catalog.category('huggingface_inference', inf_p1['models'][0]), 'text-to-image')
        self.assertEqual(catalog.category_label('huggingface_inference', 'text-to-image'), 'Text → Image')
        self.assertEqual(catalog.default_roles('huggingface_inference', inf_p1['models'][0]), [])
        self.assertEqual(catalog.default_roles('huggingface_hub', hub_p1['models'][0]), [])
        # Untrusted Link continuation host must fail closed and retain cached models
        bad_link = lambda req: httpx.Response(200, headers={'link': '<https://evil.example/api/models?cursor=bad>; rel="next"'}, json=[{'id': 'org/x'}])
        with patch.object(additional, 'provider_key', return_value=''), \
             patch.object(additional.httpx, 'Client', self.client(bad_link)):
            failed = additional.fetch_catalog('huggingface_hub', refresh=True)
        self.assertEqual(failed['models'], hub_p1['models'])
        self.assertIn('unavailable', failed['error'])
        # Picker lists all three HF catalogs separately and links to exact model pages
        with patch.object(picker, '_openrouter_models', return_value=[]), patch.object(picker, '_fal_models', return_value=[]):
            root_targets = [r.get('target') for r in picker._catalog_root_items('')]
            self.assertIn('catalog_provider:huggingface', root_targets)
            self.assertIn('catalog_provider:huggingface_inference', root_targets)
            self.assertIn('catalog_provider:huggingface_hub', root_targets)
            search_rows = picker._catalog_provider_items('huggingface_hub', 'qwen')
            self.assertTrue(any(r.get('kind') == 'provider_search' and r.get('query') == 'qwen' for r in search_rows))
            detail_rows = picker._catalog_model_items('huggingface_inference', 'Qwen/Qwen3-0.6B')
            self.assertTrue(any(r.get('url') == 'https://huggingface.co/Qwen/Qwen3-0.6B' for r in detail_rows))
            self.assertTrue(any('Downloads: 16,000,000' in r.get('label', '') for r in detail_rows))
        # Setup wizard must not duplicate HF_TOKEN
        self.assertNotIn('huggingface_inference', providers.NEW_BYOK_PROVIDERS)
        self.assertNotIn('huggingface_hub', providers.NEW_BYOK_PROVIDERS)
        self.assertTrue(providers.uses_byok('huggingface_inference'))
        self.assertTrue(providers.uses_byok('huggingface_hub'))

    def test_replicate_live_search_github_link_and_private_json_config_flow(self):
        def handler(req):
            self.assertEqual(str(req.url.copy_with(query=None)), 'https://api.replicate.com/v1/search')
            self.assertEqual(req.url.params.get('query'), 'flux')
            return httpx.Response(200, json={'models': [
                {'model': {'owner': 'black-forest-labs', 'name': 'flux-schnell', 'run_count': 12345,
                           'github_url': 'https://github.com/black-forest-labs/flux'}}
            ]})
        with patch.object(additional, 'provider_key', return_value='synthetic-rep'), \
             patch.object(additional.httpx, 'Client', self.client(handler)):
            res = additional.search_catalog('replicate', 'flux')
        self.assertEqual(res['matched'], 1)
        self.assertEqual(res['error'], '')
        with patch.object(picker, '_openrouter_models', return_value=[]), patch.object(picker, '_fal_models', return_value=[]):
            srows = picker._catalog_provider_items('replicate', 'flux')
            self.assertTrue(any(r.get('kind') == 'provider_search' and r.get('provider') == 'replicate' for r in srows))
            detail = picker._catalog_model_items('replicate', 'black-forest-labs/flux-schnell')
            self.assertTrue(any(r.get('url') == 'https://github.com/black-forest-labs/flux' for r in detail))
            self.assertTrue(any(r.get('url') == 'https://replicate.com/black-forest-labs/flux-schnell' for r in detail))
            self.assertTrue(any(r.get('kind') == 'model_json_config' for r in detail))
        # Private JSON config save (inline + .json file + invalid rejection + delete)
        saved = providers.save_model_json_config('replicate', 'black-forest-labs/flux-schnell',
            json.dumps({'repo': 'https://github.com/black-forest-labs/flux', 'env': {'TOKEN': 'synthetic-secret-token'}}))
        self.assertEqual(saved['kind'], 'model_config')
        cfg_path = providers.model_config_path()
        self.assertEqual(stat.S_IMODE(cfg_path.stat().st_mode), 0o600)
        self.assertEqual(providers.get_model_config('replicate', 'black-forest-labs/flux-schnell')['config']['repo'],
                         'https://github.com/black-forest-labs/flux')
        cfg_file = self.root / 'repo_cfg.json'
        cfg_file.write_text(json.dumps({'repo': 'https://github.com/org/custom', 'branch': 'main'}))
        saved_file = providers.save_model_json_config('huggingface_hub', 'org/custom', str(cfg_file))
        self.assertEqual(saved_file['kind'], 'model_config')
        self.assertEqual(providers.get_model_config('huggingface_hub', 'org/custom')['config']['branch'], 'main')
        with self.assertRaises(ValueError):
            providers.save_model_json_config('replicate', 'black-forest-labs/flux-schnell', '{broken json')
        self.assertTrue(providers.delete_model_config('replicate', 'black-forest-labs/flux-schnell'))
        self.assertIsNone(providers.get_model_config('replicate', 'black-forest-labs/flux-schnell'))
        # mcpServers JSON imports into MCP registry without running anything
        mcp_reg = self.root / 'mcp_registry.json'
        with patch('kurt.core.mcp_client.KURT_DIR', self.root), \
             patch('kurt.core.mcp_client.MCP_REGISTRY_PATH', mcp_reg):
            mcp_saved = providers.save_model_json_config('huggingface_hub', 'org/mcp-repo',
                json.dumps({'mcpServers': {'demo-repo': {'command': 'npx', 'args': ['-y', 'demo-pkg']}}}))
            self.assertEqual(mcp_saved['kind'], 'mcp')
            self.assertEqual(mcp_saved['names'], ['demo-repo'])
            self.assertTrue(mcp_reg.is_file())

    def test_hf_inference_mapping_exposes_live_chat_and_image_roles_and_rejects_unimplemented_tasks(self):
        seen_expand = []
        def handler(req):
            seen_expand.append(req.url.params.get_list('expand[]'))
            return httpx.Response(200, json=[
                {'id': 'Qwen/Qwen3-14B', 'pipeline_tag': 'text-generation', 'downloads': 13000000,
                 'inferenceProviderMapping': [
                     {'provider': 'deepinfra', 'providerId': 'Qwen/Qwen3-14B', 'status': 'live', 'task': 'conversational', 'type': 'single-model'}
                 ]},
                {'id': 'black-forest-labs/FLUX.1-dev', 'pipeline_tag': 'text-to-image', 'downloads': 430000,
                 'inferenceProviderMapping': [
                     {'provider': 'wavespeed', 'providerId': 'wavespeed-ai/flux-dev', 'status': 'live', 'task': 'text-to-image', 'type': 'single-model'},
                     {'provider': 'fal-ai', 'providerId': 'fal-ai/flux/dev', 'status': 'live', 'task': 'text-to-image', 'type': 'single-model'},
                     {'provider': 'deepinfra', 'providerId': 'black-forest-labs/FLUX-1-dev', 'status': 'error', 'task': 'text-to-image', 'type': 'single-model'},
                 ]},
                {'id': 'Wan-AI/Wan2.2-T2V-A14B-Diffusers', 'pipeline_tag': 'text-to-video', 'downloads': 192000,
                 'inferenceProviderMapping': [
                     {'provider': 'fal-ai', 'providerId': 'fal-ai/wan/v2.2-a14b/text-to-video', 'status': 'live', 'task': 'text-to-video', 'type': 'single-model'}
                 ]},
                {'id': 'org/lora-only', 'pipeline_tag': 'text-to-image',
                 'inferenceProviderMapping': [
                     {'provider': 'fal-ai', 'providerId': 'fal-ai/flux-lora', 'status': 'live', 'task': 'text-to-image', 'type': 'lora', 'adapterWeightsPath': 'w.safetensors'}
                 ]},
                {'id': 'sentence-transformers/all-MiniLM-L6-v2', 'pipeline_tag': 'sentence-similarity',
                 'inferenceProviderMapping': [
                     {'provider': 'hf-inference', 'providerId': 'sentence-transformers/all-MiniLM-L6-v2', 'status': 'live', 'task': 'sentence-similarity', 'type': 'single-model'}
                 ]},
            ])
        with patch.object(additional, 'provider_key', return_value=''), \
             patch.object(additional.httpx, 'Client', self.client(handler)):
            res = additional.fetch_catalog('huggingface_inference', page_budget=1)
        self.assertIn('inferenceProviderMapping', seen_expand[0])
        by_id = {m['id']: m for m in res['models']}
        self.assertEqual(catalog.default_roles('huggingface_inference', by_id['Qwen/Qwen3-14B']), ['chat'])
        self.assertEqual(catalog.default_roles('huggingface_inference', by_id['black-forest-labs/FLUX.1-dev']), ['image'])
        self.assertEqual(catalog.hf_inference_route(by_id['black-forest-labs/FLUX.1-dev'], 'image')['provider'], 'fal-ai')
        self.assertEqual(catalog.default_roles('huggingface_inference', by_id['Wan-AI/Wan2.2-T2V-A14B-Diffusers']), ['video'])
        self.assertEqual(catalog.hf_inference_route(by_id['Wan-AI/Wan2.2-T2V-A14B-Diffusers'], 'video')['provider'], 'fal-ai')
        self.assertEqual(catalog.default_roles('huggingface_inference', by_id['org/lora-only']), [])
        self.assertEqual(catalog.default_roles('huggingface_inference', by_id['sentence-transformers/all-MiniLM-L6-v2']), [])
        with patch.object(picker, '_openrouter_models', return_value=[]), patch.object(picker, '_fal_models', return_value=[]):
            chat_detail = picker._catalog_model_items('huggingface_inference', 'Qwen/Qwen3-14B')
            img_detail = picker._catalog_model_items('huggingface_inference', 'black-forest-labs/FLUX.1-dev')
            vid_detail = picker._catalog_model_items('huggingface_inference', 'Wan-AI/Wan2.2-T2V-A14B-Diffusers')
            self.assertTrue(any(r.get('value') == '/model default Qwen/Qwen3-14B huggingface_inference' for r in chat_detail))
            self.assertTrue(any(r.get('value') == '/image-model black-forest-labs/FLUX.1-dev huggingface_inference' for r in img_detail))
            self.assertTrue(any(r.get('value') == '/video-model Wan-AI/Wan2.2-T2V-A14B-Diffusers huggingface_inference' for r in vid_detail))
            self.assertTrue(any('Live HF Inference:' in r.get('label', '') for r in img_detail))
        from kurt.core import execution_preferences as prefs
        with patch.object(persona, 'KURT_DIR', self.root), patch.object(persona, 'PERSONA_PATH', self.root/'persona.json'):
            self.assertEqual(prefs.save_default_model('Qwen/Qwen3-14B', 'huggingface_inference'), 'Qwen/Qwen3-14B|huggingface_inference')
            self.assertEqual(prefs.save_default_media('image', 'black-forest-labs/FLUX.1-dev', 'huggingface_inference'),
                             'black-forest-labs/FLUX.1-dev|huggingface_inference')
            self.assertEqual(prefs.save_default_media('video', 'Wan-AI/Wan2.2-T2V-A14B-Diffusers', 'huggingface_inference'),
                             'Wan-AI/Wan2.2-T2V-A14B-Diffusers|huggingface_inference')
            with self.assertRaises(ValueError):
                prefs.save_default_media('video', 'black-forest-labs/FLUX.1-dev', 'huggingface_inference')

    def test_hf_full_hub_supports_live_inference_custom_json_endpoint_and_local_ollama_gguf(self):
        def handler(req):
            return httpx.Response(200, json=[
                {'id': 'org/live-hub-chat', 'pipeline_tag': 'text-generation', 'downloads': 5000,
                 'inferenceProviderMapping': [
                     {'provider': 'deepinfra', 'providerId': 'org/live-hub-chat', 'status': 'live', 'task': 'conversational', 'type': 'single-model'}
                 ]},
                {'id': 'org/raw-weights', 'pipeline_tag': 'text-generation', 'downloads': 100, 'inferenceProviderMapping': []},
                {'id': 'unsloth/Qwen3.8-27B-GGUF', 'downloads': 7100000, 'tags': ['gguf', 'conversational', 'imatrix'], 'inferenceProviderMapping': []},
                {'id': 'audio-cpp/audio.cpp-gguf', 'pipeline_tag': 'text-to-speech', 'library_name': 'audio.cpp',
                 'tags': ['audio.cpp', 'gguf', 'text-to-speech'], 'inferenceProviderMapping': []},
            ])
        with patch.object(additional, 'provider_key', return_value=''), \
             patch.object(additional.httpx, 'Client', self.client(handler)):
            res = additional.fetch_catalog('huggingface_hub', page_budget=1)
        by_id = {m['id']: m for m in res['models']}
        # Option A: live HF Inference auto-detected inside 3M Full Hub
        self.assertEqual(catalog.default_roles('huggingface_hub', by_id['org/live-hub-chat']), ['chat'])
        # Raw weights start browse-only
        self.assertEqual(catalog.default_roles('huggingface_hub', by_id['org/raw-weights']), [])
        # Option C: chat GGUF detected; audio TTS GGUF excluded
        self.assertTrue(by_id['unsloth/Qwen3.8-27B-GGUF'].get('ollama_gguf'))
        self.assertFalse(by_id['audio-cpp/audio.cpp-gguf'].get('ollama_gguf'))
        with patch.object(picker, '_openrouter_models', return_value=[]), patch.object(picker, '_fal_models', return_value=[]):
            gguf_rows = picker._catalog_model_rows('huggingface_hub', [by_id['unsloth/Qwen3.8-27B-GGUF']], '')
            self.assertIn('local Ollama GGUF', gguf_rows[0]['label'])
            gguf_detail = picker._catalog_model_items('huggingface_hub', 'unsloth/Qwen3.8-27B-GGUF')
            self.assertTrue(any(r.get('value') == '/model default hf.co/unsloth/Qwen3.8-27B-GGUF ollama' for r in gguf_detail))
        # Option B: cleartext remote HTTP rejected; HTTPS and local loopback accepted
        providers.save_model_json_config('huggingface_hub', 'org/raw-weights',
            json.dumps({'base_url': 'http://remote.example/v1', 'api_key': 'synthetic-leaked'}))
        self.assertIsNone(providers.custom_endpoint_config('huggingface_hub', 'org/raw-weights'))
        self.assertEqual(catalog.default_roles('huggingface_hub', by_id['org/raw-weights']), [])
        providers.save_model_json_config('huggingface_hub', 'org/raw-weights',
            json.dumps({'base_url': 'https://my-ep.endpoints.huggingface.cloud/v1', 'api_key': 'synthetic-ep-key', 'roles': ['chat', 'image']}))
        self.assertEqual(catalog.default_roles('huggingface_hub', by_id['org/raw-weights']), ['chat', 'image'])
        with patch.object(picker, '_openrouter_models', return_value=[]), patch.object(picker, '_fal_models', return_value=[]):
            raw_detail = picker._catalog_model_items('huggingface_hub', 'org/raw-weights')
            self.assertTrue(any('Custom endpoint ready:' in r.get('label', '') for r in raw_detail))
            self.assertTrue(any(r.get('value') == '/model default org/raw-weights huggingface_hub' for r in raw_detail))
            self.assertTrue(any(r.get('value') == '/image-model org/raw-weights huggingface_hub' for r in raw_detail))
            auth_rows = picker._provider_auth_items('huggingface_hub', '/model default org/raw-weights huggingface_hub')
            self.assertTrue(any(r.get('kind') == 'leaf' and 'custom JSON endpoint' in r.get('label', '') for r in auth_rows))
        from kurt.core import execution_preferences as prefs
        with patch.object(persona, 'KURT_DIR', self.root), patch.object(persona, 'PERSONA_PATH', self.root/'persona.json'):
            self.assertEqual(prefs.save_default_media('image', 'org/raw-weights', 'huggingface_hub'), 'org/raw-weights|huggingface_hub')


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for context in (patch.object(providers, 'credential_path', return_value=root/'.env'),
                        patch.object(persona, 'KURT_DIR', root),
                        patch.object(persona, 'PERSONA_PATH', root/'persona.json')):
            context.start(); self.addCleanup(context.stop)

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

    async def test_non_streaming_chat_and_provider_named_empty_error(self):
        def ok_handler(req):
            return httpx.Response(200, json={'choices': [{'message': {'content': 'NON_STREAM_OK'}}]})
        for provider in ('huggingface', 'together', 'fireworks', 'novita', 'google'):
            router = ModelRouter()
            router.byok_keys = {provider: 'synthetic-' + provider} if provider != 'google' else {}
            router.google_key = 'synthetic-google'
            with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(ok_handler))):
                text = ''.join([c async for c in router.route(provider, 'vendor/model', [{'role': 'user', 'content': 'hi'}], stream=False)])
            self.assertEqual(text, 'NON_STREAM_OK')
        def empty_handler(req):
            return httpx.Response(200, text='data: [DONE]\n\n')
        router = ModelRouter()
        router.byok_keys = {'huggingface': 'synthetic-hf'}
        with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(empty_handler))):
            with self.assertRaisesRegex(RuntimeError, 'Hugging Face.*returned no content'):
                async for _ in router.route('huggingface', 'vendor/model', [{'role': 'user', 'content': 'hi'}], stream=True):
                    pass

    async def test_huggingface_inference_chat_and_image_routing_url_and_bytes(self):
        import base64, io
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (4, 4), color=(10, 20, 30)).save(buf, format='PNG')
        png_bytes = buf.getvalue()
        # 1. Chat routing via router.huggingface.co skips wallet
        seen_chat = []
        def chat_handler(req):
            seen_chat.append(req)
            return httpx.Response(200, json={'choices': [{'message': {'content': 'HF_INF_CHAT_OK'}}]})
        router = ModelRouter()
        router.byok_keys['huggingface_inference'] = 'synthetic-hf-inf'
        with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(chat_handler))):
            out = ''.join([c async for c in router.route('huggingface_inference', 'Qwen/Qwen3-14B', [{'role': 'user', 'content': 'hi'}], stream=False)])
        self.assertEqual(out, 'HF_INF_CHAT_OK')
        self.assertEqual(str(seen_chat[0].url), 'https://router.huggingface.co/v1/chat/completions')
        self.assertEqual(seen_chat[0].headers['Authorization'], 'Bearer synthetic-hf-inf')
        with patch('kurt.billing.client.active', return_value=True), patch('kurt.billing.client.WalletTransport') as wallet:
            async with ModelRouter()._http_client(provider='huggingface_inference'):
                pass
        wallet.assert_not_called()
        # 2. Image routing: fal-ai CDN URL
        fal_model = {'id': 'black-forest-labs/FLUX.1-dev', 'category': 'text-to-image',
                     'inference_providers': [{'provider': 'fal-ai', 'provider_id': 'fal-ai/flux/dev', 'task': 'text-to-image', 'status': 'live'}]}
        fal_reqs = []
        def fal_handler(req):
            fal_reqs.append(req)
            return httpx.Response(200, json={'images': [{'url': 'https://v3.fal.media/files/test.png'}]})
        with patch('kurt.models.media_providers.find_cached_model', return_value=fal_model), \
             patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(fal_handler))):
            fal_out = ''.join([c async for c in router.route('huggingface_inference', 'black-forest-labs/FLUX.1-dev',
                                                             [{'role': 'user', 'content': 'cat'}], media_kind='image')])
        self.assertEqual(fal_out, 'https://v3.fal.media/files/test.png')
        self.assertEqual(str(fal_reqs[0].url), 'https://router.huggingface.co/fal-ai/fal-ai/flux/dev')
        # 3. Image routing: hf-inference raw PNG bytes + local receipt verification
        out_dir = Path(self.temp.name) / 'out'
        hf_model = {'id': 'org/hf-img', 'category': 'text-to-image',
                    'inference_providers': [{'provider': 'hf-inference', 'provider_id': 'org/hf-img', 'task': 'text-to-image', 'status': 'live'}]}
        from kurt.core import media_artifacts
        holder = {}
        tok = media_artifacts.LOCAL_ARTIFACT_HOLDER.set(holder)
        try:
            with patch('kurt.models.media_providers.find_cached_model', return_value=hf_model), \
                 patch.object(media_artifacts, 'OUTPUT_DIR', out_dir), \
                 patch.object(router, '_http_client', return_value=httpx.AsyncClient(
                     transport=httpx.MockTransport(lambda req: httpx.Response(200, content=png_bytes, headers={'content-type': 'image/png'})))):
                saved_path = ''.join([c async for c in router.route('huggingface_inference', 'org/hf-img',
                                                                    [{'role': 'user', 'content': 'dog'}], media_kind='image')])
        finally:
            media_artifacts.LOCAL_ARTIFACT_HOLDER.reset(tok)
        self.assertTrue(Path(saved_path).is_file())
        self.assertTrue(holder['receipt']['file_verified'])
        self.assertEqual(holder['receipt']['path'], saved_path)
        self.assertTrue(Path(saved_path + '.json').is_file())
        # 4. Image routing: together base64 PNG
        tog_model = {'id': 'org/tog-img', 'category': 'text-to-image',
                     'inference_providers': [{'provider': 'together', 'provider_id': 'org/tog-img', 'task': 'text-to-image', 'status': 'live'}]}
        b64_payload = {'data': [{'b64_json': base64.b64encode(png_bytes).decode('ascii')}]}
        with patch('kurt.models.media_providers.find_cached_model', return_value=tog_model), \
             patch.object(media_artifacts, 'OUTPUT_DIR', out_dir), \
             patch.object(router, '_http_client', return_value=httpx.AsyncClient(
                 transport=httpx.MockTransport(lambda req: httpx.Response(200, json=b64_payload)))):
            tog_path = ''.join([c async for c in router.route('huggingface_inference', 'org/tog-img',
                                                              [{'role': 'user', 'content': 'bird'}], media_kind='image')])
        self.assertTrue(Path(tog_path).is_file())
        # 5. Image routing: wavespeed via HF router polls fixed origin only
        ws_model = {'id': 'org/ws-img', 'category': 'text-to-image',
                    'inference_providers': [{'provider': 'wavespeed', 'provider_id': 'wavespeed-ai/flux-dev', 'task': 'text-to-image', 'status': 'live'}]}
        ws_reqs = []
        def ws_handler(req):
            ws_reqs.append(req)
            if req.method == 'POST':
                return httpx.Response(200, json={'code': 200, 'data': {'id': 'job_7', 'status': 'processing', 'urls': {'get': 'https://evil.example/steal'}}})
            return httpx.Response(200, json={'data': {'id': 'job_7', 'status': 'completed', 'outputs': ['https://cdn.wavespeed.ai/ok.png']}})
        with patch('kurt.models.media_providers.find_cached_model', return_value=ws_model), \
             patch('kurt.models.media_providers.asyncio.sleep'), \
             patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(ws_handler))):
            ws_out = ''.join([c async for c in router.route('huggingface_inference', 'org/ws-img',
                                                            [{'role': 'user', 'content': 'moon'}], media_kind='image')])
        self.assertEqual(ws_out, 'https://cdn.wavespeed.ai/ok.png')
        self.assertEqual([r.method for r in ws_reqs], ['POST', 'GET'])
        self.assertEqual(str(ws_reqs[1].url), 'https://router.huggingface.co/wavespeed/api/v3/predictions/job_7/result')
        # 6. Video routing: fal-ai queue polling pinned to router.huggingface.co/fal-ai
        vid_model = {'id': 'Wan-AI/Wan2.2-T2V-A14B-Diffusers', 'category': 'text-to-video',
                     'inference_providers': [{'provider': 'fal-ai', 'provider_id': 'fal-ai/wan/v2.2-a14b/text-to-video',
                                              'task': 'text-to-video', 'status': 'live'}]}
        vid_reqs = []
        def vid_handler(req):
            vid_reqs.append(req)
            if req.method == 'POST':
                return httpx.Response(200, json={'request_id': 'req_9', 'status': 'IN_QUEUE',
                                                 'response_url': 'https://evil.example/fal-ai/wan/requests/req_9'})
            if str(req.url).endswith('/status?_subdomain=queue'):
                return httpx.Response(200, json={'status': 'COMPLETED'})
            return httpx.Response(200, json={'video': {'url': 'https://v3.fal.media/files/clip.mp4'}})
        with patch('kurt.models.media_providers.find_cached_model', return_value=vid_model), \
             patch('kurt.models.media_providers.asyncio.sleep'), \
             patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(vid_handler))):
            vid_out = ''.join([c async for c in router.route('huggingface_inference', 'Wan-AI/Wan2.2-T2V-A14B-Diffusers',
                                                             [{'role': 'user', 'content': 'ocean waves'}], media_kind='video')])
        self.assertEqual(vid_out, 'https://v3.fal.media/files/clip.mp4')
        self.assertEqual([r.method for r in vid_reqs], ['POST', 'GET', 'GET'])
        self.assertEqual(str(vid_reqs[0].url), 'https://router.huggingface.co/fal-ai/fal-ai/wan/v2.2-a14b/text-to-video?_subdomain=queue')
        self.assertEqual(str(vid_reqs[1].url), 'https://router.huggingface.co/fal-ai/fal-ai/wan/requests/req_9/status?_subdomain=queue')
        self.assertEqual(str(vid_reqs[2].url), 'https://router.huggingface.co/fal-ai/fal-ai/wan/requests/req_9?_subdomain=queue')
        # 7. Music is rejected cleanly on huggingface_inference
        with self.assertRaises(ValueError):
            async for _ in router.route('huggingface_inference', 'org/ws-img', [{'role': 'user', 'content': 'song'}], media_kind='music'):
                pass

    def test_generate_media_tool_verifies_hf_inference_local_bytes(self):
        import io
        from PIL import Image
        from kurt.core import media_artifacts
        from kurt.core.assistant_tools import invoke_assistant
        buf = io.BytesIO()
        Image.new('RGB', (4, 4), color=(15, 25, 35)).save(buf, format='PNG')
        png_bytes = buf.getvalue()
        out_dir = Path(self.temp.name) / 'tool_out'
        hf_model = {'id': 'org/hf-img', 'category': 'text-to-image',
                    'inference_providers': [{'provider': 'hf-inference', 'provider_id': 'org/hf-img', 'task': 'text-to-image', 'status': 'live'}]}
        with patch('kurt.core.execution_preferences.media_target', return_value={'model': 'org/hf-img', 'provider': 'huggingface_inference'}), \
             patch('kurt.models.media_providers.find_cached_model', return_value=hf_model), \
             patch.object(media_artifacts, 'OUTPUT_DIR', out_dir), \
             patch.object(providers, 'provider_key', side_effect=lambda p: 'synthetic-hf-inf' if p in ('huggingface', 'huggingface_inference') else ''), \
             patch.object(ModelRouter, '_http_client', return_value=httpx.AsyncClient(
                 transport=httpx.MockTransport(lambda req: httpx.Response(200, content=png_bytes, headers={'content-type': 'image/png'})))):
            tool_res = invoke_assistant('generate_media', {'kind': 'image', 'prompt': 'sunset'})
        self.assertEqual(tool_res['status'], 'completed')
        self.assertTrue(tool_res['file_verified'])
        self.assertTrue(Path(tool_res['path']).is_file())
        self.assertEqual(tool_res['provider'], 'huggingface_inference')

    async def test_custom_json_endpoint_chat_image_and_local_ollama_gguf_routing(self):
        import io
        from PIL import Image
        from kurt.core import media_artifacts
        buf = io.BytesIO()
        Image.new('RGB', (4, 4), color=(50, 60, 70)).save(buf, format='PNG')
        png_bytes = buf.getvalue()
        # Option B: custom endpoint chat + image (loopback HTTP allowed, skips wallet)
        providers.save_model_json_config('huggingface_hub', 'org/custom-3m',
            json.dumps({'base_url': 'http://127.0.0.1:8000', 'api_key': 'synthetic-local-key', 'model': 'org/custom-3m', 'roles': ['chat', 'image']}))
        seen = []
        def custom_handler(req):
            seen.append(req)
            if str(req.url).endswith('/v1/chat/completions'):
                return httpx.Response(200, json={'choices': [{'message': {'content': 'CUSTOM_EP_OK'}}]})
            return httpx.Response(200, content=png_bytes, headers={'content-type': 'image/png'})
        router = ModelRouter()
        with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(custom_handler))):
            chat_out = ''.join([c async for c in router.route('huggingface_hub', 'org/custom-3m', [{'role': 'user', 'content': 'hi'}], stream=False)])
        self.assertEqual(chat_out, 'CUSTOM_EP_OK')
        self.assertEqual(str(seen[0].url), 'http://127.0.0.1:8000/v1/chat/completions')
        self.assertEqual(seen[0].headers['Authorization'], 'Bearer synthetic-local-key')
        out_dir = Path(self.temp.name) / 'custom_img_out'
        with patch.object(media_artifacts, 'OUTPUT_DIR', out_dir), \
             patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(custom_handler))):
            img_path = ''.join([c async for c in router.route('huggingface_hub', 'org/custom-3m', [{'role': 'user', 'content': 'tree'}], media_kind='image')])
        self.assertTrue(Path(img_path).is_file())
        self.assertEqual(str(seen[1].url), 'http://127.0.0.1:8000/v1/images/generations')
        # Option C: local Ollama GGUF skips wallet and gives clear pull hint on 404
        with patch('kurt.billing.client.active', return_value=True), patch('kurt.billing.client.WalletTransport') as wallet:
            async with router._http_client(provider='ollama'):
                pass
            async with router._http_client(provider='custom_endpoint'):
                pass
        wallet.assert_not_called()
        def ollama_ok(req):
            return httpx.Response(200, text=json.dumps({'message': {'content': 'GGUF_LOCAL_OK'}, 'done': True}) + '\n')
        with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(ollama_ok))):
            ol_out = ''.join([c async for c in router.route('ollama', 'hf.co/unsloth/Qwen3.8-27B-GGUF', [{'role': 'user', 'content': 'hi'}])])
        self.assertEqual(ol_out, 'GGUF_LOCAL_OK')
        with patch.object(router, '_http_client', return_value=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(404, text='not found')))):
            with self.assertRaisesRegex(RuntimeError, 'ollama pull hf.co/unsloth/Qwen3.8-27B-GGUF'):
                async for _ in router.route('ollama', 'hf.co/unsloth/Qwen3.8-27B-GGUF', [{'role': 'user', 'content': 'hi'}]):
                    pass


class KeyPickerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for context in (patch.object(providers, 'credential_path', return_value=root/'.env'),
                        patch.object(persona, 'KURT_DIR', root),
                        patch.object(persona, 'PERSONA_PATH', root/'persona.json')):
            context.start(); self.addCleanup(context.stop)

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
             patch.object(additional,'invalidate') as invalidate_cache, \
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
                invalidate_cache.assert_called_once_with('together')
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
                    task.cancel()
                    try:await task
                    except asyncio.CancelledError:pass

    async def test_json_config_input_in_picker_saves_privately_and_clears_buffer(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        from urllib.parse import quote
        real_session = picker.PromptSession
        model_row = {'id': 'org/repo-model', 'name': 'org/repo-model', 'category': 'text-generation',
                     'github_url': 'https://github.com/org/repo-model'}
        saved_calls = []
        def fake_save(provider, mid, raw):
            saved_calls.append((provider, mid, raw))
            return {'kind': 'model_config', 'key': f'{provider}:{mid}', 'message': 'JSON config saved privately.'}
        with create_pipe_input() as pipe, \
             patch.object(picker, '_catalog_models', return_value=[model_row]), \
             patch.object(providers, 'get_model_config', return_value=None), \
             patch.object(providers, 'provider_key', return_value=''), \
             patch.object(providers, 'save_model_json_config', side_effect=fake_save), \
             patch.object(picker, 'PromptSession', lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
            session, state = picker._build_session()
            state.is_open = True
            state.view = 'catalog_model:huggingface_hub:' + quote('org/repo-model', safe='')
            task = asyncio.create_task(session.prompt_async(default='/'))
            try:
                await asyncio.sleep(.05)
                rows = picker._current_items(state, '')
                state.index = next(i for i, r in enumerate(rows) if r.get('kind') == 'model_json_config')
                pipe.send_text('\r'); await asyncio.sleep(.05)
                self.assertEqual(state.view, 'model_json_input:huggingface_hub:' + quote('org/repo-model', safe=''))
                self.assertTrue(getattr(session.app, '_kurt_secret_input', False))
                payload = '{"repo":"https://github.com/org/repo-model"}'
                pipe.send_text(payload + '\r'); await asyncio.sleep(.05)
                self.assertEqual(saved_calls, [('huggingface_hub', 'org/repo-model', payload)])
                self.assertFalse(getattr(session.app, '_kurt_secret_input', False))
                self.assertEqual(session.default_buffer.text, '/')
                session.default_buffer.undo()
                self.assertNotIn('github.com/org/repo-model', session.default_buffer.text)
                self.assertIn('saved privately', state.notice)
            finally:
                if not task.done():
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass

    async def test_left_right_page_navigation_and_auto_load_more_for_large_catalogs(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        real_session = picker.PromptSession
        loaded = [{'id': f'org/model-{i:03d}', 'name': f'org/model-{i:03d}', 'category': 'text-generation'} for i in range(25)]
        remote = {'next': 'cursor2'}
        more_calls = []
        def fake_fetch(provider, more=False, **kw):
            more_calls.append((provider, more))
            if more and remote['next']:
                loaded.extend({'id': f'org/model-{i:03d}', 'name': f'org/model-{i:03d}', 'category': 'text-generation'} for i in range(25, 45))
                remote['next'] = None
            return {'models': list(loaded), 'next': remote['next'], 'complete': remote['next'] is None, 'error': ''}
        with create_pipe_input() as pipe, \
             patch.object(picker, '_catalog_models', side_effect=lambda p: list(loaded)), \
             patch.object(additional, 'peek_catalog', side_effect=lambda p: {'models': list(loaded), 'next': remote['next']}), \
             patch.object(additional, 'fetch_catalog', side_effect=fake_fetch), \
             patch.object(picker, 'PromptSession', lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
            session, state = picker._build_session()
            state.is_open = True
            state.view = 'catalog_list:huggingface_hub:*'
            state.index = 1
            task = asyncio.create_task(session.prompt_async(default='/'))
            try:
                await asyncio.sleep(.05)
                rendered = ''.join(text for _, text in picker._render(state, '/'))
                self.assertIn('Page 1/3+', rendered)
                # Right arrow flips page 1 -> page 2 -> page 3
                pipe.send_text('\x1b[C'); await asyncio.sleep(.05)
                self.assertEqual(state.index, picker.WINDOW)
                pipe.send_text('\x1b[C'); await asyncio.sleep(.05)
                self.assertEqual(state.index, picker.WINDOW * 2)
                self.assertEqual(more_calls, [])
                # Right arrow on last loaded page auto-fetches next batch and flips to page 4
                pipe.send_text('\x1b[C'); await asyncio.sleep(.05)
                self.assertEqual(more_calls, [('huggingface_hub', True)])
                self.assertEqual(state.index, picker.WINDOW * 3)
                # Left arrow flips back to page 3, then page 2, then page 1 (skipping info row 0)
                pipe.send_text('\x1b[D'); await asyncio.sleep(.05)
                self.assertEqual(state.index, picker.WINDOW * 2)
                pipe.send_text('\x1b[D'); await asyncio.sleep(.05)
                self.assertEqual(state.index, picker.WINDOW)
                pipe.send_text('\x1b[D'); await asyncio.sleep(.05)
                self.assertEqual(state.index, 1)
            finally:
                if not task.done():
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass


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
