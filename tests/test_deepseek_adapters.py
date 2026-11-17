import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core import deepseek_adapter as adapter, persona, execution_preferences as prefs
from kurt.core import cli_orchestrator as cli, command_palette, cli_readiness
from kurt.utils import env_loader
from kurt.utils.execution import sandbox_profile


class DeepSeekAdaptersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = self.root/'setup.env'
        self.env.write_text('DEEPSEEK_API_KEY=synthetic-setup\nTAVILY_API_KEY=synthetic-search\n')
        for obj, key, value in [(env_loader, 'ENV_PATH', self.env), (persona, 'KURT_DIR', self.root),
                                (persona, 'PERSONA_PATH', self.root/'persona.json')]:
            context = patch.object(obj, key, value); context.start(); self.addCleanup(context.stop)

    def test_both_cli_choices_persist_and_are_named_in_picker(self):
        with patch.object(cli, '_cmd_exists', return_value=True):
            rows = command_palette._cli_default_items('deepseek')
        self.assertEqual(len(rows), 2)
        self.assertTrue(any('Agent (Python)' in r['label'] for r in rows))
        self.assertTrue(any('Terminal CLI (Node)' in r['label'] for r in rows))
        for name in adapter.TOOLS:
            prefs.save_default_cli(name)
            self.assertEqual(prefs.ExecutionSession.load().cli, name)

    def test_cli_and_agent_exact_commands_win_over_new_substring_matches(self):
        for command in ('cli', 'deepseek', 'deepseek-cli'):
            self.assertEqual(command_palette._flat_commands(command)[0], '/'+command)

    def test_shared_setup_overrides_shell_and_filters_other_keys(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'stale', 'GITHUB_TOKEN': 'private', 'MISTRAL_API_KEY': 'private', 'DEEPSEEK_BASE_URL': 'https://untrusted.example'}, clear=True):
            for name in adapter.TOOLS:
                env = cli._ai_cli_env('/test/'+name)
                self.assertEqual(env['DEEPSEEK_API_KEY'], 'synthetic-setup')
                self.assertEqual(env['DEEPSEEK_BASE_URL'], 'https://api.deepseek.com')
                self.assertEqual(env['DEEPSEEK_MODEL'], 'deepseek-flash')
                self.assertNotIn('GITHUB_TOKEN', env)
                self.assertNotIn('MISTRAL_API_KEY', env)
                self.assertEqual('TAVILY_API_KEY' in env, name == 'deepseek')

    def test_missing_setup_never_uses_cli_embedded_key_or_starts_inference(self):
        self.env.write_text('')
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'stale'}), \
             patch.object(cli, '_resolve_cmd', return_value='/test/deepseek-cli'), \
             patch.object(adapter, 'run_bounded') as run:
            with self.assertRaisesRegex(ValueError, 'Kurt /setup'):
                adapter.run_deepseek('deepseek-cli', 'Hello')
        run.assert_not_called()

    def test_terminal_cli_uses_stdin_no_autoapproval_and_isolates_home(self):
        with patch.object(cli, '_resolve_cmd', return_value='/test/deepseek-cli'), \
             patch.object(adapter, 'service_argv', side_effect=lambda argv, service, **kw: argv) as sandbox, \
             patch.object(adapter, 'run_bounded', return_value={'status': 'completed', 'stdout': '\x1b[1mDeepSeek Terminal CLI\x1b[0m v1.3.0 (non-interactive mode)\nHello\n', 'stderr': '', 'exit_code': 0}) as run:
            result = adapter.run_deepseek('deepseek-cli', 'user task')
        self.assertEqual(result['final_text'], 'Hello')
        self.assertEqual(run.call_args.kwargs['input_text'], 'user task')
        self.assertNotIn('--yes', run.call_args.args[0])
        self.assertNotEqual(run.call_args.kwargs['env']['HOME'], str(Path.home()))
        self.assertTrue(sandbox.call_args.kwargs['write_paths'])

    def test_step_limit_with_zero_exit_is_not_success(self):
        for output in ['banner\nmax steps (8) reached\n', 'banner\n⏺ run_shell(command)\nno final summary\n', 'banner\n']:
            with patch.object(cli, '_resolve_cmd', return_value='/test/deepseek-cli'), \
                 patch.object(adapter, 'service_argv', side_effect=lambda argv, service, **kw: argv), \
                 patch.object(adapter, 'run_bounded', return_value={'status': 'completed', 'stdout': output, 'stderr': '', 'exit_code': 0}):
                self.assertEqual(adapter.run_deepseek('deepseek-cli', 'Hello')['status'], 'failed')

    def test_agent_uses_package_worker_not_automatic_test_cli_followups(self):
        executable = self.root/'deepseek'; executable.write_text('#!/usr/bin/python3\n')
        with patch.object(cli, '_resolve_cmd', return_value=str(executable)), \
             patch.object(adapter, 'service_argv', side_effect=lambda argv, service, **kw: argv), \
             patch.object(adapter, 'run_bounded', return_value={'status': 'completed', 'stdout': json.dumps({'status': 'completed', 'final_text': 'Agent ready'}), 'stderr': '', 'exit_code': 0}) as run:
            result = adapter.run_deepseek('deepseek', 'Hello')
        self.assertEqual(result['final_text'], 'Agent ready')
        self.assertTrue(run.call_args.args[0][1].endswith('deepseek_worker.py'))
        self.assertEqual(run.call_args.kwargs['input_text'], 'Hello')

    def test_timeout_is_not_retried_and_echoed_keys_are_redacted(self):
        with patch.object(cli, '_resolve_cmd', return_value='/test/deepseek-cli'), \
             patch.object(adapter, 'service_argv', side_effect=lambda argv, service, **kw: argv), \
             patch.object(adapter, 'run_bounded', return_value={'status': 'timed_out', 'stdout': '', 'stderr': 'synthetic-setup', 'exit_code': -9}) as run:
            result = adapter.run_deepseek('deepseek-cli', 'Hello')
        self.assertEqual(result['status'], 'timed_out')
        self.assertNotIn('synthetic-setup', result['stderr'])
        run.assert_called_once()

    def test_agent_provider_error_metadata_is_preserved_without_key_echo(self):
        executable = self.root/'deepseek'; executable.write_text('#!/usr/bin/python3\n')
        with patch.object(cli, '_resolve_cmd', return_value=str(executable)), \
             patch.object(adapter, 'service_argv', side_effect=lambda argv, service, **kw: argv), \
             patch.object(adapter, 'run_bounded', return_value={'status': 'failed', 'stdout': json.dumps({'status': 'failed', 'reason': 'Insufficient Balance', 'provider_http_status': 402}), 'stderr': '', 'exit_code': 1}):
            result = adapter.run_deepseek('deepseek', 'Hello')
        self.assertEqual(result['provider_http_status'], 402)
        self.assertIn('Insufficient Balance', result['stderr'])

    def test_explicit_shortcuts_and_delegation_preserve_selected_default(self):
        from kurt.core.agent_loop import execute_tool
        from kurt.capabilities.bridge import function_schemas
        prefs.save_default_cli('vibe')
        for name in adapter.TOOLS:
            with patch.object(prefs, 'run_default_cli', return_value='Agent result') as run:
                result = cli.handle_slash('/'+name+' Inspect this project', 's', 'auto', None)
                self.assertEqual(result.output, 'Agent result')
                self.assertTrue(result.feed_to_ai)
                run.assert_called_once_with(name, [{'role': 'user', 'content': 'Inspect this project'}])
            with patch.object(prefs, 'run_default_cli', return_value='Delegate result'):
                self.assertEqual(execute_tool('delegate_cli', {'tool': name, 'prompt': 'Inspect'}), 'Delegate result')
        self.assertEqual(prefs.ExecutionSession.load().cli, 'vibe')
        schema = next(t['function']['parameters'] for t in function_schemas(False) if t['function']['name'] == 'delegate_cli')
        self.assertTrue(set(adapter.TOOLS).issubset(schema['properties']['tool']['enum']))

    def test_sandbox_only_allows_runtime_directory_writes_and_protects_vault(self):
        profile = sandbox_profile(service='deepseek-cli', write_paths=[self.root])
        self.assertIn('(deny file-write*)', profile)
        self.assertIn('(subpath '+json.dumps(str(self.root.resolve()))+')', profile)
        self.assertIn(str(Path.home()/'.kurt'), profile)
        self.assertIn('(deny appleevent-send)', profile)

    def test_default_execution_and_readiness_use_adapters(self):
        result = {'status': 'completed', 'final_text': 'OK', 'stdout': '0.6.6', 'exit_code': 0}
        for name in adapter.TOOLS:
            with patch.object(cli, '_resolve_cmd', return_value='/test/'+name), patch.object(adapter, 'run_deepseek', return_value=result) as run:
                self.assertEqual(prefs.run_default_cli(name, [{'role': 'user', 'content': 'Hello'}]), 'OK')
                probe = cli_readiness.probe_default_cli(name)
                self.assertEqual(probe['executable_check'], 'completed')
                self.assertTrue(run.call_args.kwargs['probe'])


if __name__ == '__main__': unittest.main()
