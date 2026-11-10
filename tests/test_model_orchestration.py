import json
import asyncio
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx

from kurt.core import cli_orchestrator as cli
from kurt.utils.workspace import workspace


class AIEnvironmentTests(unittest.TestCase):
    def test_google_key_alias_is_mapped_without_leaking_other_provider_keys(self):
        with patch.dict(os.environ, {'GOOGLE_AI_KEY': 'synthetic-google-value', 'OPENAI_API_KEY': 'synthetic-openai-value'}, clear=True):
            env = cli._ai_cli_env('gemini')
        self.assertEqual(env['GEMINI_API_KEY'], 'synthetic-google-value')
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('GOOGLE_AI_KEY', env)

    def test_explicit_gemini_key_is_not_replaced(self):
        with patch.dict(os.environ, {'GOOGLE_AI_KEY': 'alias', 'GEMINI_API_KEY': 'explicit'}, clear=True):
            self.assertEqual(cli._ai_cli_env('gemini')['GEMINI_API_KEY'], 'explicit')

    def test_claude_uses_existing_cli_login_without_overriding_it_with_api_billing(self):
        status = SimpleNamespace(returncode=0, stdout=json.dumps({'loggedIn': True, 'authMethod': 'claude.ai'}))
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'synthetic-anthropic-value'}, clear=True), \
             patch.object(cli.subprocess, 'run', return_value=status) as run:
            env = cli._ai_cli_env('claude')
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('ANTHROPIC_API_KEY', run.call_args.kwargs['env'])

    def test_explicit_claude_api_mode_preserves_api_auth(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'synthetic-value', 'KURT_CLAUDE_AUTH': 'api'}, clear=True), \
             patch.object(cli.subprocess, 'run') as run:
            env = cli._ai_cli_env('claude')
        self.assertEqual(env['ANTHROPIC_API_KEY'], 'synthetic-value')
        run.assert_not_called()

    def test_failed_cli_exit_with_stdout_is_not_reported_as_success(self):
        status = SimpleNamespace(returncode=7, stdout='task failed', stderr='')
        with tempfile.TemporaryDirectory() as root, workspace(root), \
             patch.object(cli.subprocess, 'run', return_value=status) as run:
            result = cli._run_shell('gh', 'status')
            self.assertEqual(Path(run.call_args.kwargs['cwd']), Path(root).resolve())
        self.assertTrue(result.startswith('❌ Error:'))
        self.assertIn('code 7', result)

    def test_ai_cli_execution_is_bounded_and_keeps_workspace_scope(self):
        result = {'status': 'timed_out', 'exit_code': -9, 'stdout': '', 'stderr': '', 'truncated': False}
        with tempfile.TemporaryDirectory() as root, workspace(root), \
             patch.object(cli, '_ai_cli_env', return_value={'PATH': '/bin'}), \
             patch('kurt.utils.process.run_bounded', return_value=result) as run:
            output = cli._run_shell('gemini', '-p "synthetic request"')
            self.assertEqual(Path(run.call_args.kwargs['cwd']), Path(root).resolve())
        self.assertEqual(run.call_args.kwargs['timeout'], 120)
        self.assertEqual(run.call_args.kwargs['max_output'], 65536)
        self.assertTrue(output.startswith('❌ Error:'))
        self.assertIn('timed_out', output)

    def test_fal_account_rejection_preserves_actionable_reason(self):
        from kurt.core.router import ModelRouter
        async def run():
            client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(403, json={'detail': 'User is locked. Reason: TOP_UP.'})))
            with patch('kurt.core.router.httpx.AsyncClient', return_value=client):
                with self.assertRaisesRegex(RuntimeError, 'fal.ai HTTP 403:.*TOP_UP'):
                    async for _ in ModelRouter().call_fal('synthetic image'):
                        pass
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
