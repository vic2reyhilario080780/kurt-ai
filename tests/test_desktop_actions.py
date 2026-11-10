import asyncio
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx

from kurt.core.cli_tools import CLIResult
from kurt.core.desktop_actions import desktop_action, ensure_chromium_accessibility
from kurt.capabilities.bridge import NativeToolRouter


def observation(value="", duplicate=False, focus="Test message"):
    field = {"id": "input-1", "role": "textField", "label": "Test message",
             "value": value, "is_actionable": True, "is_value_settable": True}
    return CLIResult("peekaboo", "completed", data={"success": True,
        "target_receipt": {"window_id": 42}, "data": {
            "snapshot_id": "fresh", "window_title": "Test", "ui_elements": [field, dict(field)] if duplicate else [field],
            "focused_element": {"role": "AXTextField", "title": focus}}})


class DesktopActionTests(unittest.TestCase):
    def test_rejected_identical_desktop_call_is_not_repeated_with_new_call_id(self):
        class Router:
            calls = 0
            async def route(self, **kwargs):
                self.calls += 1
                yield json.dumps({'tool': 'desktop_action', 'call_id': str(self.calls),
                                  'params': {'action': 'fill', 'app': 'Safari'}})
        async def run():
            return ''.join([s async for s in NativeToolRouter(Router()).route('test', 'test',
                [{'role': 'user', 'content': 'Open Safari and fill the input.'}])])
        with patch('kurt.capabilities.bridge.invoke_native', side_effect=ValueError('Missing element')) as invoke:
            result = asyncio.run(run())
        self.assertIn('same rejected tool request', result)
        self.assertEqual(invoke.call_count, 1)

    def test_keyboard_scroll_and_pointer_are_window_pinned_and_never_replayed(self):
        for action, options in [('press', {'key': 'Return'}),
                                ('scroll', {'direction': 'down', 'amount': 4}),
                                ('move', {'element': 'Test message'})]:
            with self.subTest(action=action):
                responses = [observation(), CLIResult('peekaboo', 'failed', stderr='indeterminate'), observation()]
                with patch('kurt.core.desktop_actions.run_cli', side_effect=responses) as run:
                    result = desktop_action(action, app='Safari', window_id=42, **options)
                self.assertEqual(run.call_count, 3)
                args = run.call_args_list[1].args[1]
                self.assertEqual(args[0], action)
                self.assertIn('--snapshot', args)
                self.assertIn('--window-id', args)
                self.assertIn('42', args)
                self.assertEqual(result['status'], 'observed_after_action')
                self.assertEqual(result['dispatch_status'], 'failed')

    def test_invalid_keys_scroll_and_dialogs_cannot_dispatch(self):
        for options in [{'action': 'press', 'key': '--help'}, {'action': 'press', 'key': 'Return Tab'},
                        {'action': 'scroll', 'direction': 'down', 'amount': True},
                        {'action': 'scroll', 'direction': 'down', 'amount': 21}]:
            with self.subTest(options=options), patch('kurt.core.desktop_actions.run_cli') as run:
                with self.assertRaises(ValueError):
                    desktop_action(**options)
                run.assert_not_called()
        dialog = observation()
        dialog.data['data']['is_dialog'] = True
        with patch('kurt.core.desktop_actions.run_cli', return_value=dialog) as run:
            result = desktop_action('press', key='Return')
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(run.call_count, 1)

    def test_open_url_selects_the_matching_page_instead_of_the_profile_picker(self):
        picker = observation()
        page = observation()
        page.data['target_receipt']['window_id'] = 43
        page.data['data']['ui_elements'] = [{'id': 'address', 'role': 'textField',
            'label': 'Address and search bar', 'value': 'file:///private/tmp/requested.html'}]
        inventory = CLIResult('peekaboo', 'completed', data={'data': {'windows': [
            {'window_id': 42}, {'window_id': 43, 'observation_capability': 'combined_eligible'}]}})
        responses = [CLIResult('peekaboo', 'completed'), picker, inventory, page,
                     CLIResult('peekaboo', 'completed'), page]
        with patch('kurt.core.desktop_actions.run_cli', side_effect=responses) as run:
            result = desktop_action('open_url', app='Safari', url='file:///tmp/requested.html')
        focus = next(c.args[1] for c in run.call_args_list if c.args[1][:2] == ['window', 'focus'])
        self.assertIn('43', focus)
        self.assertEqual(result['observation']['window_id'], 43)
        self.assertTrue(result['url_verified'])
        self.assertEqual(result['status'], 'completed')

    def test_open_app_without_url_explicitly_focuses_and_verifies_the_exact_window(self):
        responses = [CLIResult('peekaboo', 'completed'), observation(),
                     CLIResult('peekaboo', 'completed'), observation()]
        with patch('kurt.core.desktop_actions.run_cli', side_effect=responses) as run:
            result = desktop_action('open_app', app='Safari')
        launch = run.call_args_list[0].args[1]
        focus = run.call_args_list[2].args[1]
        self.assertNotIn('--open', launch)
        self.assertEqual(focus[:2], ['window', 'focus'])
        self.assertIn('--verify', focus)
        self.assertIn('42', focus)
        self.assertTrue(result['focus_verified'])
        self.assertEqual(result['status'], 'completed')

    def test_existing_window_without_successful_focus_is_not_reported_as_opened(self):
        responses = [CLIResult('peekaboo', 'completed'), observation(),
                     CLIResult('peekaboo', 'failed', stderr='Could not focus target'), observation()]
        with patch('kurt.core.desktop_actions.run_cli', side_effect=responses) as run:
            result = desktop_action('open_app', app='Safari')
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['focus_verified'])
        self.assertEqual(run.call_count, 4)  # no mutation retry

    def test_chromium_observation_and_mutations_use_the_same_local_provider(self):
        for browser in ('Google Chrome', 'Microsoft Edge'):
            with self.subTest(browser=browser):
                responses = [observation(), CLIResult('peekaboo', 'completed'), observation(),
                             CLIResult('peekaboo', 'completed'), observation('test')]
                with patch('kurt.core.desktop_actions.run_cli', side_effect=responses) as run, \
                     patch('kurt.core.desktop_actions.ensure_chromium_accessibility', return_value={'status': 'enabled'}):
                    result = desktop_action('fill', app=browser, element='Test message', text='test')
                self.assertEqual(result['status'], 'verified')
                for call in run.call_args_list:
                    self.assertIn('--no-remote', call.args[1])
                    self.assertIn(browser, call.args[1])

    def test_chromium_activation_uses_readback_when_set_reports_an_error(self):
        target = SimpleNamespace(bundleIdentifier=lambda: 'com.google.Chrome',
                                 localizedName=lambda: 'Google Chrome', processIdentifier=lambda: 42)
        workspace = SimpleNamespace(sharedWorkspace=lambda: SimpleNamespace(runningApplications=lambda: [target]))
        ax = SimpleNamespace(AXUIElementCreateApplication=MagicMock(return_value='exact-process'),
                             AXUIElementCopyAttributeValue=MagicMock(side_effect=[(0, False), (0, True)]),
                             AXUIElementSetAttributeValue=MagicMock(return_value=-25208))
        with patch('kurt.core.desktop_actions.sys.platform', 'darwin'), \
             patch.dict('sys.modules', {'ApplicationServices': ax, 'AppKit': SimpleNamespace(NSWorkspace=workspace)}):
            result = ensure_chromium_accessibility('Google Chrome')
        self.assertEqual(result['status'], 'enabled')
        ax.AXUIElementCreateApplication.assert_called_once_with(42)
        ax.AXUIElementSetAttributeValue.assert_called_once_with('exact-process', 'AXEnhancedUserInterface', True)

    def test_chromium_activation_does_not_claim_success_without_readback(self):
        target = SimpleNamespace(bundleIdentifier=lambda: 'com.microsoft.edgemac',
                                 localizedName=lambda: 'Microsoft Edge', processIdentifier=lambda: 42)
        workspace = SimpleNamespace(sharedWorkspace=lambda: SimpleNamespace(runningApplications=lambda: [target]))
        ax = SimpleNamespace(AXUIElementCreateApplication=lambda pid: 'exact-process',
                             AXUIElementCopyAttributeValue=MagicMock(side_effect=[(0, False), (-25211, None)]),
                             AXUIElementSetAttributeValue=MagicMock(return_value=0))
        with patch('kurt.core.desktop_actions.sys.platform', 'darwin'), \
             patch.dict('sys.modules', {'ApplicationServices': ax, 'AppKit': SimpleNamespace(NSWorkspace=workspace)}):
            result = ensure_chromium_accessibility('Microsoft Edge')
        self.assertEqual(result['status'], 'unavailable')

    def test_chat_does_not_swallow_multistep_desktop_request_with_open_app_shortcut(self):
        from typer.testing import CliRunner
        from kurt import main
        from kurt.core.orchestrator import TaskType
        prompt = 'Buksan mo ang Safari at ilagay ang code sa Test message, pindutin ang Verify control.'
        optional_modules = {
            'kurt.core.wake_word': SimpleNamespace(check_dependencies=lambda: {}, start_listening=lambda **kw: None),
            'kurt.core.screen_watcher': SimpleNamespace(KURTProactive=MagicMock()),
        }
        with patch.dict('sys.modules', optional_modules), \
             patch.object(main, 'load_env'), patch.object(main, 'init_db'), \
             patch.object(main, 'get_history', return_value=[]), patch.object(main, 'save_message'), \
             patch('kurt.core.memory.get_history', return_value=[]), \
             patch.object(main, 'close_browser_session'), \
             patch.object(main.console, 'input', side_effect=[prompt, 'exit']), \
             patch.object(main, 'stream_response', new_callable=AsyncMock) as stream, \
             patch('kurt.core.intent.detect_intent') as detect:
            result = CliRunner().invoke(main.app, ['chat'])
        self.assertEqual(result.exit_code, 0, f'{result.output}\n{result.exception!r}')
        detect.assert_not_called()
        stream.assert_awaited_once()
        self.assertEqual(stream.call_args.kwargs['analysis'].task_type, TaskType.CHAT)
        self.assertEqual(stream.call_args.kwargs['messages'][-1]['content'], prompt)

    def test_indeterminate_typing_is_read_back_and_never_repeated(self):
        calls = []
        responses = [observation(), CLIResult("peekaboo", "completed"), observation(),
                     CLIResult("peekaboo", "failed", data={"effect": "unverifiable"}), observation("literal; $(no-shell)")]
        def run(tool, args, timeout):
            calls.append(args)
            return responses.pop(0)
        with patch('kurt.core.desktop_actions.run_cli', side_effect=run):
            result = desktop_action("fill", element="Test message", text="literal; $(no-shell)", window_id=42)
        self.assertEqual(result["status"], "verified")
        typed = [args for args in calls if args[0] == "type"]
        self.assertEqual(len(typed), 1)
        self.assertEqual(typed[0][1:3], ["--text", "literal; $(no-shell)"])
        self.assertIn("42", typed[0])

    def test_ambiguous_target_performs_no_mutation(self):
        with patch('kurt.core.desktop_actions.run_cli', return_value=observation(duplicate=True)) as run:
            result = desktop_action("fill", element="Test message", text="test")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[1][0], "see")

    def test_wrong_focus_sends_no_text(self):
        with patch('kurt.core.desktop_actions.run_cli', side_effect=[observation(), CLIResult("peekaboo", "completed"), observation(focus="Other input")]) as run:
            result = desktop_action("fill", element="Test message", text="test")
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(any(call.args[1][0] == "type" for call in run.call_args_list))

    def test_newlines_cannot_submit_a_form_implicitly(self):
        with patch('kurt.core.desktop_actions.run_cli', return_value=observation()) as run:
            with self.assertRaises(ValueError):
                desktop_action("fill", element="Test message", text="test\n")
        self.assertEqual(run.call_count, 1)

    def test_literal_backslash_escape_is_not_a_return_key(self):
        text = r'literal\ntext'
        responses = [observation(), CLIResult("peekaboo", "completed"), observation(),
                     CLIResult("peekaboo", "completed"), observation(text)]
        with patch('kurt.core.desktop_actions.run_cli', side_effect=responses) as run:
            result = desktop_action("fill", element="Test message", text=text)
        self.assertEqual(result['status'], 'verified')
        typed = next(call.args[1] for call in run.call_args_list if call.args[1][0] == 'type')
        self.assertEqual(typed[2], r'literal\\ntext')

    def test_rate_limit_fallback_retries_only_the_pending_model_decision(self):
        class Router:
            calls = []
            async def route(self, **kwargs):
                self.calls.append(kwargs["model"])
                if len(self.calls) == 1:
                    raise httpx.HTTPStatusError('limited', request=httpx.Request('POST', 'https://example.test'),
                        response=httpx.Response(429, headers={'retry-after': '40'}))
                yield 'ready'
        router = Router()
        async def run():
            return ''.join([s async for s in NativeToolRouter(router)._chunks(
                'groq', 'primary', [], {}, rate_limit_fallback='alternate')])
        with patch('kurt.capabilities.bridge.asyncio.sleep') as sleep:
            self.assertEqual(asyncio.run(run()), 'ready')
        self.assertEqual(router.calls, ['primary', 'alternate'])
        sleep.assert_not_called()

    def test_desktop_context_retains_user_constraints_and_recent_complete_pairs(self):
        class Router:
            supports_native_tools = True
            calls = []
            async def route(self, **kwargs):
                self.calls.append(json.loads(json.dumps(kwargs)))
                yield json.dumps({"tool": "desktop_action", "params": {"action": "observe"}}) if len(self.calls) < 5 else 'done'
        router = Router()
        messages = [{"role": "user", "content": "Open Safari; do not touch other apps."}]
        async def run():
            return ''.join([s async for s in NativeToolRouter(router).route('test', 'test', messages)])
        with patch('kurt.capabilities.bridge.invoke_native', return_value={"status": "completed"}):
            self.assertEqual(asyncio.run(run()), 'done')
        final = router.calls[-1]
        self.assertEqual(len(final['messages']), 7)  # prompt, ledger, user, two paired exchanges
        self.assertIn('Desktop execution history', final['messages'][1]['content'])
        self.assertEqual(final['messages'][1]['content'].count('"action": "observe"'), 4)
        self.assertIn('do not touch other apps', final['messages'][2]['content'])
        names = {s['function']['name'] for s in final['native_tools']}
        self.assertTrue({'press_key', 'list_apps', 'open_application', 'search_web'} <= names)


if __name__ == '__main__':
    unittest.main()
