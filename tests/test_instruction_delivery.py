"""Synthetic instructions only: inspect the wire, never contact a provider."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from kurt.persona import KurtPersona
from kurt.core.router import ModelRouter
from kurt.capabilities.bridge import NativeToolRouter


class InstructionDeliveryTests(unittest.TestCase):
    def test_chat_entrypoint_forwards_persona_and_saved_model(self):
        import io
        from rich.console import Console
        from typer.testing import CliRunner
        from kurt import main
        from kurt.core import wake_word
        from kurt.core.execution_preferences import ExecutionSession
        prompt = (Path(__file__).parent / 'fixtures/technical/calculus_prompt.txt').read_text().strip()
        seen = []
        wire = []
        real_stream = main.stream_response
        router = ModelRouter()
        router.mistral_key = 'synthetic-not-a-credential'
        def transport(request):
            wire.append(json.loads(request.content))
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"fixture"}}]}\n\ndata: [DONE]\n\n')
        async def respond(**kwargs):
            seen.append(kwargs)
            return await real_stream(**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'system_instructions.md').write_text('SYNTHETIC_CHAT_RIGOR')
            with patch('kurt.persona.KurtPersona', return_value=KurtPersona(root)), \
                 patch.object(main, 'console', Console(file=io.StringIO())), \
                 patch.object(main, 'ModelRouter', return_value=router), \
                 patch.object(router, '_http_client', side_effect=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(transport))), \
                 patch('kurt.capabilities.bridge._chat_discovery_summary', return_value=''), \
                 patch.object(main, 'load_env'), patch.object(main, 'stream_response', side_effect=respond), \
                 patch.object(main, 'load_persona', return_value={}), \
                 patch('kurt.core.persona.load_persona', return_value={}), \
                 patch.object(ExecutionSession, 'load', return_value=ExecutionSession('mistral-small-latest|mistral', 'auto')), \
                 patch.object(wake_word, 'check_dependencies', return_value={}):
                result = CliRunner().invoke(main.app, ['chat', prompt, '--no-memory'], input='exit\n')
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(seen), 1)
        call = seen[0]
        self.assertTrue(any('SYNTHETIC_CHAT_RIGOR' in m['content'] for m in call['messages'] if m['role'] == 'system'))
        self.assertEqual(call['messages'][-1], {'role':'user','content':prompt})
        self.assertEqual(call['analysis'].provider, 'mistral')
        self.assertEqual(call['analysis'].model, 'mistral-small-latest')
        self.assertEqual(call['temperature'], .3)
        self.assertTrue(call['execution'].pinned)
        self.assertEqual(len(wire), 1)
        self.assertEqual(wire[0]['model'], 'mistral-small-latest')
        self.assertEqual(wire[0]['temperature'], .3)
        systems = [m['content'] for m in wire[0]['messages'] if m['role'] == 'system']
        self.assertTrue(any('SYNTHETIC_CHAT_RIGOR' in s for s in systems))
        self.assertTrue(any('KURT_NATIVE_TOOLS_V1' in s for s in systems))
        self.assertTrue(any('You are running as a CLI tool' in s for s in systems))
        self.assertEqual(wire[0]['messages'][-1], {'role':'user','content':prompt})

    def test_standalone_voice_delivers_custom_instructions_and_temperature(self):
        from kurt import main
        from kurt.core import wake_word
        from kurt.core.execution_preferences import ExecutionSession
        from unittest.mock import Mock
        seen = []
        async def respond(analysis, messages, *args, **kwargs):
            seen.append((messages, kwargs))
            return 'fixture'
        def start(callback, **kwargs):
            callback(SimpleNamespace(text='Explain this equation.'))
            return Mock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'system_instructions.md').write_text('SYNTHETIC_VOICE_RIGOR')
            with patch('kurt.persona.KurtPersona', return_value=KurtPersona(root)), \
                 patch.object(main, 'load_env'), patch.object(main, 'init_db'), \
                 patch.object(main, 'save_message'), patch.object(main, '_try_local_request', return_value=None), \
                 patch.object(main, 'stream_response', side_effect=respond), \
                 patch.object(ExecutionSession, 'load', return_value=ExecutionSession('mistral-small-latest|mistral', 'auto')), \
                 patch.object(wake_word, 'check_dependencies', return_value={'can_record':True, 'can_transcribe':True, 'can_detect_speech':True}), \
                 patch.object(wake_word, 'start_listening', side_effect=start), \
                 patch.object(wake_word, 'stop_listening'), patch.object(wake_word, 'speak'), \
                 patch.object(main.time, 'sleep', side_effect=KeyboardInterrupt):
                main.voice(model=None, speak=False, hotkey_only=True)
        self.assertEqual(len(seen), 1)
        messages, options = seen[0]
        self.assertIn('SYNTHETIC_VOICE_RIGOR', messages[0]['content'])
        self.assertEqual(options['temperature'], .2)
        self.assertNotIn('1-2 sentences max', str(messages))

    def test_custom_instructions_survive_auto_mode_and_mistral_transport(self):
        prompt = (Path(__file__).parent / 'fixtures/technical/calculus_prompt.txt').read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'persona.md').write_text('Neutral test assistant.')
            (root / 'memory.md').write_text('')
            (root / 'system_instructions.md').write_text('SYNTHETIC_RIGOR: justify convergence.')
            persona = KurtPersona(root)
            turn = persona.build(prompt, include_history=False)
            # "special functions" matches coding before the technical category.
            self.assertEqual(turn['mode'], 'coding')
            captured = []

            def transport(request):
                captured.append(json.loads(request.content))
                return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"fixture"}}]}\n\ndata: [DONE]\n\n')

            router = ModelRouter()
            router.mistral_key = 'synthetic-not-a-credential'
            router.strict_selection = True
            messages = [{'role': 'system', 'content': turn['system_prompt']},
                        {'role': 'user', 'content': prompt}]

            async def run():
                return ''.join([s async for s in NativeToolRouter(router).route(
                    'mistral', 'mistral-small-latest', messages, temperature=turn['temperature'])])

            with patch.object(router, '_http_client', side_effect=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(transport))), \
                 patch('kurt.capabilities.bridge._chat_discovery_summary', return_value=''):
                self.assertEqual(asyncio.run(run()), 'fixture')
            self.assertEqual(len(captured), 1)
            wire = captured[0]
            self.assertEqual(wire['model'], 'mistral-small-latest')
            self.assertEqual(wire['temperature'], .3)
            self.assertTrue(wire['stream'])
            self.assertIn('SYNTHETIC_RIGOR', '\n'.join(m['content'] for m in wire['messages'] if m['role'] == 'system'))
            self.assertEqual(wire['messages'][-1], {'role': 'user', 'content': prompt})

    def test_custom_instructions_apply_without_keywords_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'persona.md').write_text('PERSONA_SENTINEL')
            instructions = root / 'system_instructions.md'
            instructions.write_text('CUSTOM_V1')
            persona = KurtPersona(root)
            for mode in ('auto', 'casual', 'coding', 'business', 'technical'):
                with self.subTest(mode=mode):
                    system = persona.build('hello', mode=mode)['system_prompt']
                    self.assertIn('CUSTOM_V1', system)
                    self.assertIn('PERSONA_SENTINEL', system)
            instructions.write_text('CUSTOM_V2')
            self.assertIn('CUSTOM_V2', persona.build('hello')['system_prompt'])

