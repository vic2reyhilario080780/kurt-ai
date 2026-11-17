import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core.cli_orchestrator import _ai_cli_env, run_ai_cli
from kurt.utils import env_loader


class VibeSharedKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'.env'
        context = patch.object(env_loader, 'ENV_PATH', self.path)
        context.start(); self.addCleanup(context.stop)

    def test_setup_wins_over_shell_and_key_rotation_is_immediate(self):
        self.path.write_text('MISTRAL_API_KEY=synthetic-setup-one\n')
        with patch.dict(os.environ, {'MISTRAL_API_KEY': 'synthetic-stale', 'OPENAI_API_KEY': 'other'}, clear=True):
            first = _ai_cli_env('/test/vibe')
            self.path.write_text('MISTRAL_API_KEY=synthetic-setup-two\n')
            second = _ai_cli_env('/test/vibe')
            self.assertEqual(os.environ['MISTRAL_API_KEY'], 'synthetic-stale')
        self.assertEqual(first['MISTRAL_API_KEY'], 'synthetic-setup-one')
        self.assertEqual(second['MISTRAL_API_KEY'], 'synthetic-setup-two')
        self.assertNotIn('OPENAI_API_KEY', second)

    def test_missing_or_blank_setup_does_not_use_shell_or_start_cli(self):
        for content in [None, 'MISTRAL_API_KEY=   \n']:
            if content is not None: self.path.write_text(content)
            with patch.dict(os.environ, {'MISTRAL_API_KEY': 'synthetic-shell'}), \
                 patch('kurt.utils.process.run_bounded') as run:
                self.assertNotIn('MISTRAL_API_KEY', _ai_cli_env('/test/vibe'))
                with self.assertRaisesRegex(ValueError, 'Kurt /setup'):
                    run_ai_cli('/test/vibe', ['-p', 'Hello'])
                run.assert_not_called()

    def test_version_probe_does_not_need_setup(self):
        with patch('kurt.utils.process.run_bounded', return_value={'status': 'completed'}) as run:
            run_ai_cli('/test/vibe', ['--version'])
        run.assert_called_once()

    def test_vibe_failure_does_not_misdiagnose_model_permission_as_bad_key(self):
        from kurt.core.execution_preferences import cli_failure_detail
        message = cli_failure_detail('vibe', {'status': 'failed', 'exit_code': 1,
            'stderr': 'Invalid API key. Please check your API key and try again.'})
        self.assertIn('403', message)
        self.assertIn('mistral-medium-3.5', message)
        self.assertIn('model access', message)

    def test_only_exact_read_only_search_tools_are_preapproved(self):
        import json
        with patch.dict(os.environ, {'VIBE_TOOLS': '{"bash":{"permission":"always"}}'}):
            env = _ai_cli_env('/test/vibe')
        self.assertEqual(json.loads(env['VIBE_TOOLS']), {
            'connector_web_search_news_search': {'permission': 'always'},
            'connector_web_search_web_search': {'permission': 'always'},
        })
        self.assertNotIn('VIBE_BYPASS_TOOL_PERMISSIONS', env)

    def test_tool_approval_error_does_not_show_unrelated_api_key_hint(self):
        from kurt.core.execution_preferences import cli_failure_detail
        message = cli_failure_detail('vibe', {'status': 'failed', 'exit_code': 3,
            'stderr': 'Tool call denied: connector_web_search.news_search (needs approval)\nStopped: turn_limit'})
        self.assertIn('headless cannot approve', message)
        self.assertNotIn('403', message)
        self.assertNotIn('authentication', message)

    def test_setup_key_reaches_actual_adapter_environment(self):
        self.path.write_text('MISTRAL_API_KEY=synthetic-shared\n')
        with patch('kurt.utils.process.run_bounded', return_value={'status': 'completed'}) as run:
            run_ai_cli('/test/vibe', ['-p', 'Hello'])
        self.assertEqual(run.call_args.kwargs['env']['MISTRAL_API_KEY'], 'synthetic-shared')


if __name__ == '__main__': unittest.main()
