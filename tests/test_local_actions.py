import hashlib
from pathlib import Path
import tempfile
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from typer.testing import CliRunner

from kurt.core import local_actions as local


class LocalActionTests(unittest.TestCase):
    def test_native_action_allowlist_excludes_scripts_and_sending(self):
        for action in ['send_mail', 'run_script', 'delete_message']:
            with self.subTest(action=action), self.assertRaises(ValueError):
                local._native_action(action)

    def test_mail_permission_failure_is_not_misreported_as_no_accounts(self):
        class Delegate:
            @classmethod
            def alloc(cls): return cls()
            def init(self): return self
        class Mail:
            def setTimeout_(self, timeout): pass
            def setDelegate_(self, delegate): self.delegate = delegate
            def accounts(self):
                self.delegate.last_error = 'Not authorized'
                return SimpleNamespace(count=lambda: 0)
        mail = Mail()
        bridge = SimpleNamespace(SBApplication=SimpleNamespace(applicationWithBundleIdentifier_=lambda bundle: mail))
        with patch.object(local, '_DELEGATE_CLASS', Delegate), \
             patch.dict(sys.modules, {'ScriptingBridge': bridge, 'Foundation': SimpleNamespace(NSObject=object)}):
            with self.assertRaisesRegex(RuntimeError, 'Not authorized'):
                local._native_action('check_mail')

    def test_stopped_music_selects_one_available_local_track_without_querying_invalid_current_track(self):
        class Delegate:
            @classmethod
            def alloc(cls): return cls()
            def init(self): return self
        with tempfile.TemporaryDirectory() as root:
            media = Path(root) / 'synthetic.mp3'
            media.write_bytes(b'fixture')
            track = SimpleNamespace(location=lambda: SimpleNamespace(path=lambda: str(media)))
            library = SimpleNamespace(tracks=lambda: SimpleNamespace(count=lambda: 1), fileTracks=lambda: [track])
            class Music:
                state = 'kPSS'
                played = None
                def setTimeout_(self, timeout): pass
                def setDelegate_(self, delegate): self.delegate = delegate
                def libraryPlaylists(self): return SimpleNamespace(objectAtIndex_=lambda index: library)
                def playerState(self): return int.from_bytes(self.state.encode(), 'big')
                def play_once_(self, candidate, once): self.played = candidate; self.state = 'kPSP'
            music = Music()
            bridge = SimpleNamespace(SBApplication=SimpleNamespace(applicationWithBundleIdentifier_=lambda bundle: music))
            with patch.object(local, '_DELEGATE_CLASS', Delegate), \
                 patch.dict(sys.modules, {'ScriptingBridge': bridge, 'Foundation': SimpleNamespace(NSObject=object)}):
                result = local._native_action('play_music')
            self.assertEqual(result['player_state'], 'playing')
            self.assertIs(music.played, track)

    def test_common_requests_route_to_actual_actions(self):
        cases = {'buksan mo nga yung Calculator': 'open_app', 'open Notes': 'open_app',
                 'check my email': 'check_mail', 'i-check mo ang email ko': 'check_mail',
                 'play music': 'play_music', 'magpatugtog ka ng musika': 'play_music',
                 'pause music': 'pause_music', 'i-download mo ito': 'download'}
        with patch.object(local, 'installed_apps', return_value={'calculator': 'Calculator', 'notes': 'Notes'}):
            for prompt, action in cases.items():
                with self.subTest(prompt=prompt):
                    self.assertEqual(local.parse_local_request(prompt).action, action)

    def test_compound_tasks_and_explanations_are_not_consumed(self):
        with patch.object(local, 'installed_apps', return_value={'notes': 'Notes'}):
            for prompt in ['how do I open Notes?', 'do not play music', 'open Notes and delete my notes',
                           'check my email and send a reply', 'read my email', 'play music and turn volume to maximum']:
                with self.subTest(prompt=prompt):
                    self.assertIsNone(local.parse_local_request(prompt))

    def test_no_mail_account_is_not_claimed_as_an_empty_inbox(self):
        with patch.object(local, 'mail_status', return_value={'accounts': 0, 'unread': 0}):
            result = local.execute_local_request(local.LocalRequest('check_mail'))
        self.assertEqual(result['status'], 'needs_setup')

    def test_play_requires_playing_state_not_merely_an_open_app(self):
        for returned in ['paused', 'stopped', 'no_tracks']:
            with self.subTest(returned=returned), patch.object(local, '_native_action', return_value={'player_state': returned, 'library_tracks': 0 if returned == 'no_tracks' else 1}):
                result = local.execute_local_request(local.LocalRequest('play_music'))
                self.assertNotEqual(result['status'], 'completed')

    def test_download_saves_exact_bytes_and_hash(self):
        payload = b'synthetic-download'
        client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=payload)))
        with tempfile.TemporaryDirectory() as root, patch.object(local.httpx, 'Client', return_value=client):
            target = Path(root) / 'test.txt'
            result = local.download_file('https://example.test/test.txt', str(target))
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(result['sha256'], hashlib.sha256(payload).hexdigest())

    def test_download_refuses_overwrite_before_request(self):
        with tempfile.TemporaryDirectory() as root, patch.object(local.httpx, 'Client') as client:
            target = Path(root) / 'existing.txt'
            target.write_text('user data')
            with self.assertRaises(FileExistsError):
                local.download_file('https://example.test/file', str(target))
            self.assertEqual(target.read_text(), 'user data')
            client.assert_not_called()

    def test_oversize_stream_leaves_no_partial_output(self):
        client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=httpx.ByteStream(b'12345'))))
        with tempfile.TemporaryDirectory() as root, patch.object(local.httpx, 'Client', return_value=client):
            with self.assertRaises(ValueError):
                local.download_file('https://example.test/file', str(Path(root) / 'file.txt'), max_bytes=3)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_missing_download_source_requests_input_without_network(self):
        with patch.object(local.httpx, 'Client') as client:
            result = local.execute_local_request(local.LocalRequest('download'))
        self.assertEqual(result['status'], 'needs_input')
        client.assert_not_called()

    def test_chat_opens_named_app_without_model_or_memory_route(self):
        from kurt import main
        with patch.object(main, 'load_env'), patch.object(main, 'ModelRouter', side_effect=AssertionError('No model needed')), \
             patch.object(local, 'installed_apps', return_value={'notes': 'Notes'}), \
             patch.object(local, 'desktop_action', return_value={'status': 'completed'}) as action:
            result = CliRunner().invoke(main.app, ['chat', '--no-memory'], input='open Notes\nexit\n')
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('Nabuksan at na-verify ang Notes', result.output)
        action.assert_called_once_with('open_app', app='Notes')


if __name__ == '__main__':
    unittest.main()
