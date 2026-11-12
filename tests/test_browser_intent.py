import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from kurt.core.browser_intent import BrowserRequest, parse_browser_request, execute_browser_request


class BrowserIntentTests(unittest.TestCase):
    def test_common_natural_language_opening_requests(self):
        cases = {
            'open browser': None,
            'Can you open a browser?': None,
            'magbukas ka ng browser': None,
            'buksan mo ang browser': None,
            'Kurt, buksan mo nga yung Chrome': 'Google Chrome',
            'please open Microsoft Edge': 'Microsoft Edge',
            'could you please open the Safari browser': 'Safari',
            'paki open naman ng browser': None,
            'pakibukas ang Safari': 'Safari',
            'open my web browser please': None,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                request = parse_browser_request(text)
                self.assertIsNotNone(request)
                self.assertEqual(request.app, expected)

    def test_complete_navigation_request_preserves_url(self):
        self.assertEqual(parse_browser_request('open Chrome to example.com'), BrowserRequest('Google Chrome', 'https://example.com'))
        self.assertEqual(parse_browser_request('buksan ang Edge at pumunta sa file:///tmp/test.html'), BrowserRequest('Microsoft Edge', 'file:///tmp/test.html'))

    def test_questions_negation_and_extra_tasks_are_not_consumed(self):
        for text in ['how do I open Chrome?', 'do not open Chrome', 'I opened Safari yesterday',
                     'open Chrome and type hello', 'open Chrome and delete history',
                     'open Safari to https://example.com and click Submit',
                     '"open Chrome" is an example', 'open Chrome to javascript:alert(1)']:
            with self.subTest(text=text):
                self.assertIsNone(parse_browser_request(text))

    def test_plain_browser_resolves_the_actual_default_without_requiring_a_url(self):
        observed = {'status': 'completed', 'observation': {'status': 'completed', 'window_id': 42}}
        with patch('kurt.core.browser_intent.default_browser', return_value='Microsoft Edge'), \
             patch('kurt.core.browser_intent.desktop_action', return_value=observed) as action:
            result = execute_browser_request(BrowserRequest(None))
        action.assert_called_once_with('open_app', app='Microsoft Edge', url=None)
        self.assertEqual(result['status'], 'completed')

    def test_dispatched_launch_without_observation_is_not_success(self):
        with patch('kurt.core.browser_intent.desktop_action', return_value={'status': 'completed', 'observation': {'status': 'failed'}}):
            result = execute_browser_request(BrowserRequest('Safari'))
        self.assertEqual(result['status'], 'failed')

    def test_quick_local_action_dispatches_literal_request_without_model_or_intent_fallback(self):
        # `_try_local_request` is the literal-command fast path shared by `kurt
        # voice` and (formerly) `kurt ask`/`kurt do` — it must resolve a plain
        # "open the browser" request without ever touching the AI model.
        from kurt import main
        with patch.object(main, 'ModelRouter', side_effect=AssertionError('AI must not be needed')), \
             patch('kurt.core.intent.detect_intent', side_effect=AssertionError('Must not misroute the app name')), \
             patch('kurt.core.browser_intent.default_browser', return_value='Safari'), \
             patch('kurt.core.browser_intent.desktop_action', return_value={
                 'status': 'completed', 'observation': {'status': 'completed', 'window_id': 42}}) as action:
            result = main._try_local_request('magbukas ka ng browser', 'test-session', no_memory=True)
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'completed')
        self.assertIn('Nabuksan at na-verify ang Safari', result['message'])
        self.assertEqual(action.call_count, 1)

    def test_quick_local_action_opens_without_provider_configuration_or_credits(self):
        from kurt import main
        with patch.object(main, 'check_setup', side_effect=AssertionError('No AI setup required')), \
             patch('kurt.core.browser_intent.desktop_action', return_value={
                 'status': 'completed', 'observation': {'status': 'completed', 'window_id': 42}}):
            result = main._try_local_request('buksan mo nga yung Chrome', 'test-session', no_memory=True)
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
