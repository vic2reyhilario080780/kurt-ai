"""Credential regression tests use synthetic secrets only."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.utils.security import redact, child_env, require_public_file, write_private_text

SECRET = 'synthetic-credential-987654321'

class SecurityTests(unittest.TestCase):
    def test_known_secret_and_encoded_variants(self):
        import base64
        from urllib.parse import quote
        with patch.dict(os.environ, {'TEST_API_KEY': SECRET}):
            for value in [SECRET, base64.b64encode(SECRET.encode()).decode(), quote(SECRET)]:
                self.assertNotIn(value, redact('output: ' + value))

    def test_structured_and_url_credentials(self):
        self.assertEqual(redact({'api_key': SECRET})['api_key'], '[REDACTED]')
        self.assertNotIn(SECRET, redact('https://example.test/?api_key=' + SECRET))
        self.assertEqual(redact('${GROQ_API_KEY}'), '${GROQ_API_KEY}')

    def test_child_environment_explicit_grants(self):
        source = {'PATH': '/bin', 'HOME': '/tmp', 'OPENAI_API_KEY': SECRET, 'OTHER_SECRET': SECRET}
        self.assertEqual(child_env(source=source), {'PATH': '/bin', 'HOME': '/tmp'})
        self.assertEqual(child_env(source=source, allow=('OPENAI_API_KEY',))['OPENAI_API_KEY'], SECRET)
        self.assertEqual(child_env(source=source, extra={'SERVER_TOKEN': SECRET})['SERVER_TOKEN'], SECRET)

    def test_private_paths_and_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root)/'.env.production'; target.write_text('secret')
            link = Path(root)/'report.csv'; link.symlink_to(target)
            for path in (target, link, Path(root)/'credentials.json'):
                with self.assertRaises(ValueError): require_public_file(path)
            require_public_file(Path(root)/'.env.example')

    def test_private_file_mode(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'config'; write_private_text(path, SECRET)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_memory_never_persists_known_secret(self):
        from kurt.core import memory
        with tempfile.TemporaryDirectory() as root, patch.object(memory, 'KURT_DIR', Path(root)), patch.object(memory, 'DB_PATH', Path(root)/'memory.db'), patch.dict(os.environ, {'TEST_API_KEY': SECRET}):
            memory.init_db(); memory.save_message('test', 'user', 'key: ' + SECRET)
            self.assertNotIn(SECRET, json.dumps(memory.get_history('test')))
            self.assertNotIn(SECRET.encode(), memory.DB_PATH.read_bytes())

    def test_provider_payload_redacted_auth_preserved(self):
        from kurt.core.router import ModelRouter
        from unittest.mock import AsyncMock, MagicMock
        response = MagicMock(); response.json.return_value = {'choices': [{'message': {'content': 'ok'}}]}
        async def lines():
            yield 'data: [DONE]'
        response.aiter_lines.side_effect = lines
        stream_context = MagicMock(); stream_context.__aenter__ = AsyncMock(return_value=response); stream_context.__aexit__ = AsyncMock(return_value=False)
        client = MagicMock(); client.stream.return_value = stream_context
        context = MagicMock(); context.__aenter__ = AsyncMock(return_value=client); context.__aexit__ = AsyncMock(return_value=False)
        async def request():
            router = ModelRouter()
            async for _ in router.call_openrouter('model', [{'role':'user','content':SECRET}], stream=False): pass
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': SECRET}), patch('kurt.core.router.httpx.AsyncClient', return_value=context):
            asyncio.run(request())
        kwargs = client.stream.call_args.kwargs
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer ' + SECRET)
        self.assertNotIn(SECRET, json.dumps(kwargs['json']['messages']))

    def test_peekaboo_does_not_inherit_provider_keys(self):
        from kurt.core.cli_tools import cli_env
        with patch.dict(os.environ, {'OPENAI_API_KEY': SECRET, 'REPLICATE_API_TOKEN': SECRET}):
            self.assertNotIn('OPENAI_API_KEY', cli_env('peekaboo'))
            self.assertNotIn('REPLICATE_API_TOKEN', cli_env('openclaw'))

    def test_dotenv_quotes_and_export_precedence(self):
        from kurt.utils import env_loader
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'.env'; path.write_text("TEST_API_KEY='stored-test-value'\nANOTHER_TEST_KEY='quoted-value'\n")
            with patch.object(env_loader, 'ENV_PATH', path), patch.dict(os.environ, {'TEST_API_KEY':'exported-test-value'}, clear=True):
                env_loader.load_env()
                self.assertEqual(os.environ['TEST_API_KEY'], 'exported-test-value')
                self.assertEqual(os.environ['ANOTHER_TEST_KEY'], 'quoted-value')

    def test_slash_agent_prompt_is_one_shell_argument(self):
        from kurt.core import cli_orchestrator
        # Validate quoting at the actual boundary by intercepting the shell call.
        with patch.object(cli_orchestrator, '_cmd_exists', return_value=True), patch.object(cli_orchestrator, '_resolve_cmd', return_value='claude'), patch.object(cli_orchestrator, '_run_shell', return_value='ok') as run:
            cli_orchestrator.handle_slash('/claude hello $(printenv) "quoted"', 'test', 'test-model', None)
        import shlex
        self.assertEqual(shlex.split(run.call_args.args[1]), ['--print', 'hello $(printenv) "quoted"'])
