import asyncio
import base64
import io
import json
import os
import shlex
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import httpx
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput
from rich.console import Console
from typer.testing import CliRunner

from kurt.core import attachments as attach, command_palette as palette, persona
from kurt.core.cli_orchestrator import handle_slash
from kurt.core.router import ModelRouter
from kurt.capabilities.bridge import NativeToolRouter

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==')


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root/'Photos Library.photoslibrary/resources/derivatives/C/photo.png'
        self.path.parent.mkdir(parents=True); self.path.write_bytes(PNG)

    def test_quotes_spaces_drag_escapes_and_file_url(self):
        for text in [str(self.path), "'"+str(self.path)+"'", '"'+str(self.path)+'"', str(self.path).replace(' ', '\\ '), self.path.as_uri()]:
            with self.subTest(text=text):
                parsed = attach.parse_image_input(text)
                self.assertEqual(parsed.paths, [self.path])
                self.assertEqual(parsed.text, '')

    def test_question_and_multiple_quoted_images(self):
        other = self.root/'another.jpeg'
        parsed = attach.parse_image_input(f"Ano ang nasa '{self.path}' at '{other}'?")
        self.assertEqual(parsed.paths, [self.path, other])
        self.assertIn('Ano ang nasa', parsed.text)
        apostrophe = self.root/"Photo's picture.png"
        self.assertEqual(attach.parse_image_input(shlex.quote(str(apostrophe))).paths, [apostrophe])

    def test_plain_path_with_following_question_and_exact_user_shape(self):
        parsed = attach.parse_image_input(str(self.path)+' ano ang nasa larawan?')
        self.assertEqual(parsed.paths, [self.path])
        self.assertEqual(parsed.text, 'ano ang nasa larawan?')
        example = "'/Users/vic2rey/Pictures/Photos Library.photoslibrary/resources/derivatives/C/CA8F5CE4-B4E2-4933-8B6C-ED994F7B8BA1_1_105_c.jpeg'"
        self.assertEqual(len(attach.parse_image_input(example).paths), 1)

    def test_filesystem_paths_are_not_commands_but_help_still_is(self):
        self.assertFalse(handle_slash(str(self.path), 'test', 'auto', None).handled)
        self.assertTrue(handle_slash('/help', 'test', 'auto', None).handled)
        self.assertFalse(attach.parse_image_input('https://example.org/image.png').paths)

    def test_mime_comes_from_bytes_and_provider_formats_are_correct(self):
        loaded = attach.load_images([self.path])
        content = attach.image_content('Describe this', loaded)
        self.assertEqual(base64.b64decode(content[1]['image_url']['url'].split(',', 1)[1]), PNG)
        messages = [{'role': 'user', 'content': content}]
        self.assertEqual(attach.redact_messages(messages), messages)
        claude = attach.provider_image_messages(messages, 'anthropic')
        self.assertEqual(claude[0]['content'][1]['source']['media_type'], 'image/png')
        ollama = attach.provider_image_messages(messages, 'ollama')
        self.assertEqual(ollama[0]['content'], 'Describe this')
        self.assertEqual(base64.b64decode(ollama[0]['images'][0]), PNG)
        self.assertEqual(attach._mime(b'\xff\xd8\xff\xe0image'), 'image/jpeg')

    def test_invalid_data_large_files_and_private_symlinks_are_rejected(self):
        bad = self.root/'bad.png'; bad.write_text('not an image')
        with self.assertRaises(ValueError): attach.load_images([bad])
        with patch.object(attach, 'MAX_IMAGE_BYTES', 10), self.assertRaises(ValueError): attach.load_images([self.path])
        private = self.root/'.ssh'; private.mkdir()
        target = private/'photo.png'; target.write_bytes(PNG)
        link = self.root/'link.png'; link.symlink_to(target)
        with self.assertRaises(ValueError): attach.load_images([link])
        with self.assertRaises(ValueError): attach.parse_image_input('file://remote-host/a.png')

    def test_main_sends_image_bytes_but_saves_only_text_marker(self):
        from kurt import main
        received, saved = [], []
        async def response(**kwargs):
            received.extend(kwargs['messages'])
            return 'A small image.'
        with patch.object(persona, 'KURT_DIR', self.root), patch.object(persona, 'PERSONA_PATH', self.root/'settings.json'), \
             patch.object(main, 'console', Console(file=io.StringIO())), patch.object(main, 'load_env'), \
             patch.object(main, 'init_db'), patch.object(main, 'get_history', return_value=[]), \
             patch('kurt.core.memory.get_history', return_value=[]), \
             patch.object(main, 'save_message', side_effect=lambda *args: saved.append(args)), \
             patch.object(main, 'stream_response', side_effect=response), patch('kurt.persona.KurtPersona') as kp:
            persona.save_persona({'default_model': 'mistral-small-latest|mistral'})
            kp.return_value.build.return_value = {'system_prompt': 'test', 'temperature': .5}
            result = CliRunner().invoke(main.app, ['chat'], input=f"'{self.path}'\nexit\n")
        self.assertEqual(result.exit_code, 0, result.output)
        user = next(m for m in received if m['role'] == 'user')
        self.assertIsInstance(user['content'], list)
        self.assertIn('data:image/png;base64,', user['content'][1]['image_url']['url'])
        self.assertNotIn('data:image', json.dumps(saved))
        self.assertIn('photo.png', json.dumps(saved))

    def test_followup_keeps_latest_image_in_ram_and_clear_removes_it(self):
        from kurt import main
        calls = []
        async def response(**kwargs):
            calls.append(kwargs['messages'])
            return 'Image context acknowledged.'
        with patch.object(persona, 'KURT_DIR', self.root), patch.object(persona, 'PERSONA_PATH', self.root/'settings.json'), \
             patch.object(main, 'console', Console(file=io.StringIO())), patch.object(main, 'load_env'), \
             patch.object(main, 'stream_response', side_effect=response), patch('kurt.persona.KurtPersona') as kp:
            persona.save_persona({'default_model': 'vision-test|mistral', 'default_cli': 'auto'})
            kp.return_value.build.return_value = {'system_prompt': 'test', 'temperature': .5}
            result = CliRunner().invoke(main.app, ['chat', '--no-memory'],
                input=f"'{self.path}'\nAnimate that picture\nclear\nHello\nexit\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(calls), 3)
        self.assertIn('data:image/png;base64,', json.dumps(calls[1]))
        self.assertNotIn('data:image/png;base64,', json.dumps(calls[2]))

    def test_native_tool_router_accepts_multimodal_user_content(self):
        class Planner:
            supports_native_tools = True
            async def route(self, **kwargs): yield 'Image received.'
        messages = [{'role': 'user', 'content': attach.image_content('Describe', attach.load_images([self.path]))}]
        async def collect():
            return ''.join([s async for s in NativeToolRouter(Planner()).route('test', 'test', messages)])
        self.assertEqual(asyncio.run(collect()), 'Image received.')

    def test_provider_http_payload_really_contains_image_data(self):
        real_client = httpx.AsyncClient
        messages = [{'role': 'user', 'content': attach.image_content('Describe', attach.load_images([self.path]))}]
        for provider, key in [('mistral', 'MISTRAL_API_KEY'), ('anthropic', 'ANTHROPIC_API_KEY'), ('ollama', '')]:
            sent = []
            def handler(request):
                sent.append(json.loads(request.content))
                if provider == 'anthropic': payload = 'data: '+json.dumps({'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'seen'}})+'\n\n'
                elif provider == 'ollama': payload = json.dumps({'message': {'content': 'seen'}, 'done': True})+'\n'
                else: payload = 'data: '+json.dumps({'choices': [{'delta': {'content': 'seen'}}]})+'\n\ndata: [DONE]\n\n'
                return httpx.Response(200, text=payload)
            async def collect():
                return ''.join([s async for s in ModelRouter().route(provider, 'vision-test', messages)])
            with self.subTest(provider=provider), patch.dict(os.environ, {key: 'synthetic-key'} if key else {}, clear=True), \
                 patch('kurt.core.router.httpx.AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
                self.assertEqual(asyncio.run(collect()), 'seen')
            self.assertIn(base64.b64encode(PNG).decode(), json.dumps(sent[0]))


class AttachmentKeyboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_path_is_submitted_without_getting_stuck_in_picker(self):
        real_session = palette.PromptSession
        for text in ['/Users/name/Photos Library.photoslibrary/pic.jpeg', "'/Users/name/Photos Library.photoslibrary/pic.jpeg'", '/picture.jpeg']:
            with self.subTest(text=text), create_pipe_input() as pipe, patch.object(palette.engine, 'PromptSession', lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
                session, state = palette._build_session()
                task = asyncio.create_task(session.prompt_async())
                await asyncio.sleep(.03)
                pipe.send_text(text+'\r')
                self.assertEqual(await asyncio.wait_for(task, 2), text)
                self.assertFalse(state.is_open)


if __name__ == '__main__': unittest.main()
