import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

import httpx

from kurt.core import command_palette as picker
from kurt.models import catalog, fal, openrouter


class CatalogTests(unittest.TestCase):
    def test_every_endpoint_occurs_in_exactly_one_category(self):
        source = [{'id': f'owner/model-{i}', 'category': ['text-to-image', 'image-to-image',
                  'image-to-video', 'text-to-video', 'training', 'new-future-task', None][i % 7]}
                  for i in range(1356)]
        with patch.object(picker.items, '_fal_models', return_value=source):
            groups = catalog.groups('fal', source)
            self.assertEqual(sum(map(len, groups.values())), 1356)
            all_rows = picker._catalog_provider_items('fal', '', '*')
            self.assertEqual(sum(r['kind'] == 'open' for r in all_rows), 1356)
            ids = []
            for cat in groups:
                rows = picker._catalog_provider_items('fal', '', cat)
                ids.extend(unquote(r['target'].split(':', 2)[-1]) for r in rows if r['kind'] == 'open')
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(set(ids), {m['id'] for m in source})
            self.assertIn('1,356', picker._catalog_link('fal')['label'])

    def test_openrouter_full_catalog_retains_non_chat_models_and_unknown_metadata(self):
        source = [{'id': f'lab/text-{i}', 'architecture': {'output_modalities': ['text']}} for i in range(461)]
        source += [{'id': f'lab/media-{i}', 'architecture': {'output_modalities': ['text', 'image']}} for i in range(18)]
        source += [{'id': 'lab/unknown'}]
        with patch.object(picker.items, '_openrouter_models', return_value=source):
            rows = picker._catalog_provider_items('openrouter', '', '*')
            self.assertEqual(sum(r['kind'] == 'open' for r in rows), 480)
            self.assertEqual(sum(map(len, catalog.groups('openrouter', source).values())), 480)
            self.assertTrue(any('lab/media-17' in r['label'] for r in rows))
            self.assertTrue(any('lab/unknown' in r['label'] for r in rows))
            detail = picker._catalog_model_items('openrouter', 'lab/media-17')
            self.assertFalse(any(r['kind'] == 'leaf' for r in detail))
            self.assertTrue(any(r['kind'] == 'browser' for r in detail))

    def test_deduplication_is_exact_id_only_and_preserves_versions(self):
        source = [{'id': 'lab/model-v1'}, {'id': 'lab/model-v2'}, {'id': 'lab/model-v1'}]
        self.assertEqual(len(catalog.unique_models(source)), 2)
        with patch.object(picker.items, '_openrouter_models', return_value=source):
            self.assertIn('2 models', picker._catalog_link('openrouter')['label'])

    def test_search_finds_non_default_workflows_and_details_are_browse_only(self):
        models = [{'id': 'lab/rare-edit', 'category': 'image-to-image'},
                  {'id': 'lab/training', 'category': 'training'}]
        with patch.object(picker.items, '_fal_models', return_value=models), patch.object(picker.items, '_openrouter_models', return_value=[]):
            rows = picker._catalog_root_items('rare-edit')
            self.assertEqual(len(rows), 1)
            state = picker._PaletteState(view=rows[0]['target'])
            detail = picker._current_items(state, '')
            self.assertFalse(any(r['kind'] == 'leaf' for r in detail))
            self.assertTrue(any(r.get('kind') == 'model_json_config' and
                                r.get('provider') == 'fal' and r.get('mid') == 'lab/rare-edit'
                                for r in detail))

    def test_model_details_use_existing_commands_and_settings_hide_session_action(self):
        model = {'id': 'lab/chat', 'architecture': {'output_modalities': ['text']}}
        with patch.object(picker.items, '_openrouter_models', return_value=[model]):
            rows = picker._catalog_model_items('openrouter', model['id'], settings_only=True)
        self.assertEqual([r['value'] for r in rows if r['kind'] == 'leaf'], ['/model default lab/chat openrouter'])
        self.assertEqual(catalog.default_roles('fal', {'id': 'lab/edit', 'category': 'image-to-image'}), [])
        self.assertEqual(catalog.default_roles('fal', {'id': 'lab/image', 'category': 'text-to-image'}), ['image'])

    def test_menus_link_to_complete_catalog_without_changing_compatible_defaults(self):
        with patch.object(picker.items, '_openrouter_models', return_value=[]), patch.object(picker.items, '_fal_models', return_value=[]):
            self.assertEqual(picker.OPEN_TARGETS['/models'], 'model_catalog')
            for rows, provider in ((picker._model_items(''), 'openrouter'),
                                   (picker._default_model_items(''), 'openrouter'),
                                   (picker._media_model_items('image', ''), 'fal'),
                                   (picker._media_model_items('video', ''), 'fal')):
                self.assertTrue(any(r.get('target') == 'catalog_provider:' + provider for r in rows))


class CatalogFetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.client = httpx.Client

    def client_for(self, handler):
        return lambda **kwargs: self.client(transport=httpx.MockTransport(handler), **kwargs)

    def test_fal_fetches_all_pages_and_checks_total(self):
        pages = []
        def handler(req):
            page = int(req.url.params['page'])
            pages.append(page)
            return httpx.Response(200, json={'page': page, 'pages': 3, 'total': 3,
                                             'items': [{'id': f'model-{page}'}]})
        with patch.object(fal, 'CACHE_DIR', self.root), patch.dict(os.environ, {'FAL_API_KEY': 'synthetic'}), \
             patch.object(fal.httpx, 'Client', self.client_for(handler)):
            models = fal.fetch_models(False)
        self.assertEqual(pages, [1, 2, 3])
        self.assertEqual(len(models), 3)
        self.assertEqual(json.loads((self.root/'models.json').read_text()), models)

    def test_partial_unauthorized_or_duplicate_pages_cannot_replace_complete_cache(self):
        previous = [{'id': 'previous-complete-model'}]
        for problem in ('unauthorized', 'duplicate', 'changed-total'):
            (self.root/'models.json').write_text(json.dumps(previous))
            def handler(req):
                page = int(req.url.params['page'])
                if page == 2 and problem == 'unauthorized':
                    return httpx.Response(401, json={'error': 'invalid key'})
                return httpx.Response(200, json={'page': page, 'pages': 2,
                    'total': 3 if page == 2 and problem == 'changed-total' else 2,
                    'items': [{'id': 'same' if problem == 'duplicate' else f'model-{page}'}]})
            with self.subTest(problem=problem), patch.object(fal, 'CACHE_DIR', self.root), \
                 patch.dict(os.environ, {'FAL_API_KEY': 'synthetic'}), \
                 patch.object(fal.httpx, 'Client', self.client_for(handler)), \
                 patch.object(fal.console, 'print'):
                self.assertEqual(fal.fetch_models(False), previous)
                self.assertEqual(json.loads((self.root/'models.json').read_text()), previous)

    def test_openrouter_http_error_preserves_cache_and_corrupt_cache_can_recover(self):
        previous = [{'id': 'previous'}]
        path = self.root/'models.json'
        path.write_text(json.dumps(previous))
        with patch.object(openrouter, 'CACHE_DIR', self.root), patch.object(openrouter.console, 'print'), \
             patch.object(openrouter.httpx, 'Client', self.client_for(lambda req: httpx.Response(503))):
            self.assertEqual(openrouter.fetch_models(False), previous)
            self.assertEqual(json.loads(path.read_text()), previous)
        path.write_text('broken json')
        with patch.object(openrouter, 'CACHE_DIR', self.root), \
             patch.object(openrouter.httpx, 'Client', self.client_for(lambda req: httpx.Response(200, json={'data': [{'id': 'new'}]}))):
            self.assertEqual(openrouter.fetch_models(), [{'id': 'new'}])


class CatalogInteractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_browse_unsupported_model_then_save_supported_default(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        real_session = picker.PromptSession
        models = [{'id': 'lab/edit', 'category': 'image-to-image'}, {'id': 'lab/image', 'category': 'text-to-image'}]
        with create_pipe_input() as pipe, patch.object(picker.items, '_fal_models', return_value=models), \
             patch.object(picker.engine, 'refresh_model_catalogs', return_value='Catalogs loaded: fal.ai 2.') as refresh, \
             patch('kurt.models.providers.provider_key', return_value='synthetic-key'), \
             patch('kurt.models.providers.confirm_byok') as confirm, \
             patch.object(picker.engine, 'PromptSession', lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
            session, state = picker._build_session()
            state.is_open, state.settings_only = True, True
            state.view = 'catalog_provider:fal'
            state.index = next(i for i, r in enumerate(picker._current_items(state, '')) if r['kind'] == 'catalog_refresh')
            task = asyncio.create_task(session.prompt_async(default='/'))
            try:
                await asyncio.sleep(.05)
                pipe.send_text('\r')
                await asyncio.sleep(.05)
                refresh.assert_called_once()
                self.assertFalse(task.done())
                self.assertIn('Catalogs loaded', state.notice)
                state.view = 'catalog_list:fal:*'
                state.index = 1  # first actual model after the count header
                pipe.send_text('\r')
                await asyncio.sleep(.05)
                self.assertEqual(state.view, 'catalog_model:fal:lab%2Fedit')
                self.assertFalse(task.done())
                self.assertFalse(any(r['kind'] == 'leaf' for r in picker._current_items(state, '')))
                pipe.send_text('\x1b')
                await asyncio.sleep(.55)
                self.assertEqual(state.view, 'catalog_list:fal:*')
                state.index = 2
                pipe.send_text('\r')
                await asyncio.sleep(.05)
                state.index = next(i for i, r in enumerate(picker._current_items(state, '')) if r['kind'] == 'leaf')
                pipe.send_text('\r')
                await asyncio.sleep(.05)
                self.assertTrue(state.view.startswith('model_setup:fal:'))
                state.index = next(i for i, r in enumerate(picker._current_items(state, '')) if r.get('billing') == 'byok')
                pipe.send_text('\r')
                self.assertEqual(await asyncio.wait_for(task, 2), '/image-model lab/image fal')
                confirm.assert_called_once_with('fal')
            finally:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
