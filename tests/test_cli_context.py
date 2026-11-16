import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core.execution_preferences import cli_prompt, cli_failure_detail
from kurt.core.cli_orchestrator import handle_slash
from kurt.persona import KurtPersona


class CLIContextTests(unittest.TestCase):
    def test_long_context_drops_old_turns_but_preserves_policy_and_latest_request(self):
        messages = [{'role': 'system', 'content': 'Never modify user files without authorization.'},
                    {'role': 'user', 'content': 'Earlier request'},
                    {'role': 'assistant', 'content': 'old answer '*10000},
                    {'role': 'user', 'content': 'Reply exactly CURRENT_REQUEST'}]
        original = json.dumps(messages)
        prompt = cli_prompt(messages)
        self.assertLessEqual(len(prompt.encode()), 30000)
        self.assertIn('CURRENT_REQUEST', prompt)
        self.assertIn(messages[0]['content'], prompt)
        self.assertNotIn('Earlier request', prompt)
        self.assertIn('omitted', prompt)
        self.assertEqual(json.dumps(messages), original)

    def test_latest_request_and_system_policy_are_never_truncated(self):
        for messages in ([{'role': 'user', 'content': 'latest '*10000}],
                         [{'role': 'system', 'content': 'policy '*10000}, {'role': 'user', 'content': 'hello'}]):
            with self.subTest(messages=len(messages)), self.assertRaisesRegex(ValueError, 'neither was truncated'):
                cli_prompt(messages)

    def test_cli_persona_does_not_repeat_history_inside_system_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            persona = KurtPersona(base_dir=Path(directory))
            persona.remember('OLD_UNIQUE_USER', 'OLD_UNIQUE_ANSWER')
            self.assertIn('OLD_UNIQUE_ANSWER', persona.build('hello')['system_prompt'])
            self.assertNotIn('OLD_UNIQUE_ANSWER', persona.build('hello', include_history=False)['system_prompt'])
            self.assertTrue(persona.history)

    def test_failure_reports_actionable_tail_and_partial_output(self):
        detail = cli_failure_detail('vibe', {'status': 'timed_out', 'exit_code': -9,
                                          'stderr': 'startup chatter '*1000+'ACTIONABLE_ERROR_END',
                                          'stdout': 'Partial answer'})
        self.assertIn('ACTIONABLE_ERROR_END', detail)
        self.assertIn('Partial answer', detail)
        self.assertIn('completion unverified', detail)
        self.assertIn('exit -9', detail)

    def test_vibe_probe_is_version_only(self):
        with patch('kurt.core.cli_orchestrator._resolve_cmd', return_value='/test/vibe'), \
             patch('kurt.core.cli_orchestrator.run_ai_cli', return_value={'status': 'completed', 'stdout': 'vibe 3.1.2', 'stderr': '', 'exit_code': 0}) as run:
            result = handle_slash('/cli probe vibe', 's', 'auto', None)
        run.assert_called_once_with('/test/vibe', ['--version'])
        self.assertEqual(json.loads(result.output)['executable_check'], 'completed')

    def test_explicit_image_command_returns_actual_receipt_not_json_binding_error(self):
        with patch('kurt.core.media_generation.generate_selected_media', return_value={'status': 'provider_result', 'output': 'https://example.org/image.png'}):
            result = handle_slash('/image A bird', 's', 'auto', None)
        self.assertEqual(json.loads(result.output)['status'], 'provider_result')


if __name__ == '__main__': unittest.main()
