import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from rich.console import Console
from typer.testing import CliRunner

from kurt.core import persona, execution_preferences as prefs, command_palette as palette
from kurt.core.cli_orchestrator import handle_slash
from kurt.core.assistant_tools import invoke_assistant
from kurt.core.agent_loop import execute_tool
from kurt.capabilities.bridge import NativeToolRouter


class MediaRoutingTests(unittest.TestCase):
    def setUp(self):
        finalizer = patch('kurt.core.media_artifacts.finalize_artifact', side_effect=lambda url, kind: {'output': url, 'path': '/tmp/verified-media', 'file_verified': True})
        finalizer.start(); self.addCleanup(finalizer.stop)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        for key, value in [('KURT_DIR', Path(self.tmp.name)), ('PERSONA_PATH', Path(self.tmp.name)/'persona.json')]:
            context = patch.object(persona, key, value); context.start(); self.addCleanup(context.stop)

    def select(self, kind, query):
        with patch.object(palette, '_fal_models', return_value=[]):
            row = next(r for r in palette._media_model_items(kind, query) if r.get('kind') == 'leaf' and query in r['label'])
        result = handle_slash(row['value'], 'test', 'auto', None)
        self.assertIn('saved', result.output)

    def test_picker_save_banner_and_real_http_adapter_use_same_exact_models(self):
        from kurt.main import _kurt_welcome_banner
        self.select('image', 'Nano Banana 2.1'); self.select('video', 'Kling 3.0 Standard')
        targets = {'image': 'google/nano-banana-2.1', 'video': 'fal-ai/kling-video/v3/standard/text-to-video'}
        output = io.StringIO()
        Console(file=output, width=160).print(_kurt_welcome_banner('Kurt', 'test', {'primary': 'cyan'}, 'Boss', 'auto', None, 's', defaults=persona.load_persona()))
        for target in targets.values(): self.assertIn(target, output.getvalue())
        real_client = httpx.AsyncClient
        requests = []
        def handler(request):
            requests.append(request)
            self.assertEqual(request.headers['authorization'], 'Key synthetic-media-key')
            self.assertEqual(json.loads(request.content), {'prompt': 'A blue bird'})
            return httpx.Response(200, json={'video': {'url': 'https://example.org/result.mp4'}} if 'kling' in request.url.path else {'images': [{'url': 'https://example.org/result.png'}]})
        with patch.dict(os.environ, {'FAL_API_KEY': 'synthetic-media-key'}, clear=True), \
             patch('kurt.core.router.httpx.AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
            for kind, target in targets.items():
                result = invoke_assistant('generate_media', {'kind': kind, 'prompt': 'A blue bird'})
                self.assertEqual(result['model'], target)
                self.assertEqual(str(requests[-1].url), 'https://fal.run/'+target)
        self.assertEqual(len(requests), 2)

    def test_wrong_role_selection_cannot_overwrite_saved_default(self):
        self.select('image', 'Nano Banana')
        before = persona.PERSONA_PATH.read_text()
        with self.assertRaises(ValueError):
            prefs.save_default_media('image', 'fal-ai/kling-video/v3/standard/text-to-video', 'fal')
        self.assertEqual(persona.PERSONA_PATH.read_text(), before)

    def test_manual_wrong_role_saved_state_blocks_before_request(self):
        persona.save_persona({'default_video_model': 'fal-ai/nano-banana|fal'})
        with patch('kurt.core.router.ModelRouter') as router, self.assertRaises(ValueError):
            invoke_assistant('generate_media', {'kind': 'video', 'prompt': 'bird'})
        router.assert_not_called()

    def test_generic_model_tool_cannot_bypass_media_defaults(self):
        with patch('kurt.core.agent_loop._collect_model_response') as call:
            result = execute_tool('call_model', {'provider': 'fal', 'model': 'other/model', 'prompt': 'bird'})
        self.assertIn('generate_media', result)
        call.assert_not_called()

    def test_empty_generation_prompt_never_reaches_provider(self):
        with patch('kurt.core.router.ModelRouter') as router, self.assertRaises(ValueError):
            invoke_assistant('generate_media', {'kind': 'image', 'prompt': '   '})
        router.assert_not_called()

    def test_explicit_media_command_works_even_with_selected_cli(self):
        prefs.save_default_cli('vibe')
        self.select('video', 'Kling 3.0 Standard')
        with patch('kurt.core.media_generation.generate_selected_media', return_value={'status': 'provider_result', 'output': 'https://example.org/clip.mp4'}) as generate:
            result = handle_slash('/video A blue bird', 'test', 'auto', None, current_cli='vibe')
        generate.assert_called_once_with('video', 'A blue bird')
        self.assertTrue(result.feed_to_ai)
        self.assertEqual(persona.load_persona()['default_cli'], 'vibe')

    def test_dry_run_does_not_submit_a_generation(self):
        from kurt import main
        self.select('video', 'Kling 3.0 Standard')
        with patch('kurt.core.media_generation.generate_selected_media') as generate, patch('kurt.utils.env_loader.load_env'):
            result = CliRunner().invoke(main.app, ['generate', 'video', '--dry-run'])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('fal-ai/kling-video/v3/standard/text-to-video', result.output)
        generate.assert_not_called()

    def test_provider_failure_does_not_switch_or_repeat_models(self):
        self.select('image', 'Nano Banana')
        requests = []
        real_client = httpx.AsyncClient
        def handler(request):
            requests.append(request)
            return httpx.Response(503, json={'detail': 'busy'})
        with patch.dict(os.environ, {'FAL_API_KEY': 'synthetic'}, clear=True), \
             patch('kurt.core.router.httpx.AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
            result = invoke_assistant('generate_media', {'kind': 'image', 'prompt': 'bird'})
        self.assertEqual(result['status'], 'unverified')
        self.assertFalse(result['retry_safe'])
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), 'https://fal.run/fal-ai/nano-banana')

    def test_chat_pinned_model_can_still_use_selected_image_generator(self):
        self.select('image', 'Nano Banana')
        calls = iter([
            {'tool': 'set_task_goal', 'params': {'objective': 'Generate a bird image', 'goal_type': 'workflow', 'target_app': ''}},
            {'tool': 'generate_media', 'params': {'kind': 'image', 'prompt': 'A blue bird'}}, None])
        class Planner:
            supports_native_tools = True
            strict_selection = True
            async def route(self, **kwargs):
                names = {t['function']['name'] for t in kwargs['native_tools']}
                assert 'generate_media' in names and 'call_model' not in names
                call = next(calls)
                yield 'Done' if call is None else '```tool\n'+json.dumps(call)+'\n```'
        requests = []
        real_client = httpx.AsyncClient
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={'images': [{'url': 'https://example.org/bird.png'}]})
        async def run():
            return ''.join([c async for c in NativeToolRouter(Planner()).route('mistral', 'mistral-small-latest', [{'role': 'user', 'content': 'Gawan mo ako ng larawan ng blue bird.'}])])
        with patch.dict(os.environ, {'FAL_API_KEY': 'synthetic'}, clear=True), \
             patch('kurt.core.router.httpx.AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
            self.assertIn('Na-download at na-check', asyncio.run(run()))
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), 'https://fal.run/fal-ai/nano-banana')


if __name__ == '__main__': unittest.main()
