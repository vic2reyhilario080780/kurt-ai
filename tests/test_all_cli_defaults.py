import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core import execution_preferences as prefs, persona, cli_readiness as readiness, command_palette
from kurt.core.cli_tools import CLIResult
from kurt.core.codex_adapter import run_codex
from kurt.core.cli_orchestrator import _ai_cli_env, handle_slash
from kurt.utils.execution import sandbox_profile


class AllCLIDefaultTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for k, v in [('KURT_DIR', self.root), ('PERSONA_PATH', self.root/'persona.json')]:
            p = patch.object(persona, k, v); p.start(); self.addCleanup(p.stop)
        p = patch.object(readiness, 'KURT_DIR', self.root); p.start(); self.addCleanup(p.stop)

    def test_all_supported_choices_persist_without_erasing_saved_chat_model(self):
        prefs.save_default_model('mistral-small-latest', 'mistral')
        for name in prefs.DEFAULT_CLIS:
            with self.subTest(name=name):
                result = handle_slash('/cli default '+name, 's', 'auto', None)
                self.assertEqual(result.cli_override, name)
                self.assertEqual(prefs.ExecutionSession.load().cli, name)
                self.assertEqual(persona.load_persona()['default_model'], 'mistral-small-latest|mistral')

    def test_each_headless_cli_has_correct_protocol_and_final_text(self):
        messages = [{'role': 'user', 'content': 'Reply OK'}]
        for name, payload in [('claude', json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'OK'})),
                              ('gemini', json.dumps({'response': 'OK', 'stats': {}})), ('vibe', 'OK')]:
            with self.subTest(name=name), patch('kurt.core.cli_orchestrator._resolve_cmd', return_value='/test/'+name), \
                 patch('kurt.core.cli_orchestrator.run_ai_cli', return_value={'status': 'completed', 'stdout': payload}) as run:
                self.assertEqual(prefs.run_default_cli(name, messages), 'OK')
            args = run.call_args.args[1]
            self.assertEqual(args[0], '--print' if name == 'claude' else '-p')
            if name != 'vibe': self.assertEqual(args[-2:], ['--output-format', 'json'])
            self.assertNotIn('--yolo', args)

    def test_codex_can_start_outside_git_without_relaxing_sandbox(self):
        events = '\n'.join(json.dumps(e) for e in [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'OK'}}, {'type': 'turn.completed'}])
        with patch('kurt.core.codex_adapter.executable', return_value='/test/codex'), \
             patch('kurt.core.codex_adapter.run_bounded', return_value={'status': 'completed', 'stdout': events, 'stderr': '', 'exit_code': 0}) as run:
            result = run_codex('Reply OK', cwd=self.root)
        self.assertEqual(result['status'], 'completed')
        argv = run.call_args.args[0]
        self.assertIn('--skip-git-repo-check', argv)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', argv)
        self.assertTrue(any('network' in x and 'false' in x for x in argv))

    def test_openclaw_payload_and_final_envelopes_and_empty_ack(self):
        for data in [{'result': {'payloads': [{'text': 'OK'}]}}, {'ok': True, 'final': 'OK', 'payloads': []}]:
            with patch('kurt.core.cli_tools.delegate_desktop_cli', return_value=CLIResult('openclaw', 'completed', data=data)):
                self.assertEqual(prefs.run_default_cli('openclaw', [{'role': 'user', 'content': 'hello'}]), 'OK')
        with patch('kurt.core.cli_tools.delegate_desktop_cli', return_value=CLIResult('openclaw', 'completed', stdout='{"ok":true}', data={'ok': True, 'status': 'queued'})) as run:
            with self.assertRaisesRegex(RuntimeError, 'no verified text'):
                prefs.run_default_cli('openclaw', [{'role': 'user', 'content': 'hello'}])
        run.assert_called_once()

    def test_zero_exit_error_and_empty_reply_are_not_success(self):
        for name, data in [('claude', {'is_error': True, 'subtype': 'error_max_turns', 'result': 'turn limit'}),
                           ('gemini', {'error': {'code': 503, 'message': 'provider busy'}}), ('gemini', {'response': ''})]:
            with self.subTest(name=name), self.assertRaises(RuntimeError) as err:
                prefs.cli_reply(name, {'status': 'completed', 'stdout': json.dumps(data), 'exit_code': 0})
            self.assertNotIsInstance(err.exception, prefs.CLIQuotaExhausted)
        with self.assertRaises(RuntimeError): prefs.cli_reply('vibe', {'stdout': ''})

    def test_sdk_json_error_is_readable_without_changing_quota_policy(self):
        nested = json.dumps({'error': {'code': 503, 'message': 'This model is currently experiencing high demand.'}})
        stderr = 'Retrying... _ApiError: '+json.dumps({'error': {'code': 503, 'message': nested}})+'\nlong stack trace'
        result = {'status': 'timed_out', 'exit_code': -9, 'stdout': '', 'stderr': stderr}
        detail = prefs.cli_failure_detail('gemini', result)
        self.assertIn('Provider error 503', detail)
        self.assertIn('high demand', detail)
        self.assertNotIn('long stack trace', detail)
        self.assertFalse(prefs.cli_quota_exhausted(result))

    def test_private_helper_paths_are_not_given_to_other_clis(self):
        with patch.dict(os.environ, {'PATH': str(Path.home()/'.codex/private/bin')+os.pathsep+'/usr/bin'}, clear=True):
            env = _ai_cli_env('/test/gemini')
        self.assertNotIn('.codex', env['PATH'])
        self.assertIn('/usr/bin', env['PATH'])
        self.assertFalse(env['PATH'].endswith(os.pathsep))

    def test_missing_cli_cannot_be_selected_from_picker(self):
        with patch('kurt.core.cli_orchestrator._cmd_exists', return_value=False):
            rows = command_palette._cli_default_items('')
        self.assertEqual([r['value'] for r in rows if r['kind'] == 'leaf'], ['/cli default auto'])

    def test_probe_all_never_submits_model_requests(self):
        with patch.object(readiness, 'probe_default_cli', side_effect=lambda n: {'cli': n}) as probe, \
             patch('kurt.core.execution_preferences.run_default_cli') as live:
            result = handle_slash('/cli probe all', 's', 'auto', None)
        self.assertEqual(len(json.loads(result.output)), len(prefs.DEFAULT_CLIS) - 1)
        self.assertEqual(probe.call_count, len(prefs.DEFAULT_CLIS) - 1)
        live.assert_not_called()
        self.assertFalse(persona.PERSONA_PATH.exists())

    def test_probe_caches_health_and_surfaces_only_recent_failures(self):
        results = [
            {'cli': 'codex', 'installed': True, 'executable_check': 'completed'},
            {'cli': 'gemini', 'installed': True, 'executable_check': 'failed'},
        ]
        with patch.object(readiness, 'probe_default_cli', side_effect=lambda n: next(r for r in results if r['cli'] == n)):
            readiness.probe_clis('codex')
            readiness.probe_clis('gemini')
        self.assertEqual(readiness.cached_unhealthy_clis(), ['gemini'])
        # A stale entry (older than the surfacing window) must not be reported.
        cache = readiness._load_health_cache()
        cache['gemini']['checked_at'] -= readiness.HEALTH_CACHE_MAX_AGE + 1
        (self.root / 'cli_health.json').write_text(json.dumps(cache))
        self.assertEqual(readiness.cached_unhealthy_clis(), [])

    def test_health_cache_survives_corrupt_file(self):
        (self.root / 'cli_health.json').write_text('not json')
        self.assertEqual(readiness.cached_unhealthy_clis(), [])

    def test_live_test_does_not_change_default_or_switch_backend_on_error(self):
        prefs.save_default_cli('vibe'); before = persona.PERSONA_PATH.read_text()
        with patch('kurt.core.execution_preferences.run_default_cli', side_effect=RuntimeError('Gemini HTTP 503')), patch('kurt.utils.env_loader.load_env'):
            result = readiness.test_default_cli('gemini')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('503', result['error'])
        self.assertEqual(persona.PERSONA_PATH.read_text(), before)


if __name__ == '__main__': unittest.main()
