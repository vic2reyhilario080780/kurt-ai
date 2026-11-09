"""OS enforcement tests; use synthetic files, never real credential contents."""
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from kurt.utils.execution import restricted_run

@unittest.skipUnless(platform.system() == 'Darwin', 'macOS sandbox integration')
class ExecutionSecurityTests(unittest.TestCase):
    def run_python(self, code, **kw):
        return restricted_run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15, **kw)

    def test_normal_code_runs(self):
        result = self.run_python('print(6 * 7)')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '42')

    def test_credentials_and_symlink_read_denied(self):
        with tempfile.TemporaryDirectory() as root:
            secret = Path(root)/'.env.production'; secret.write_text('synthetic-only')
            link = Path(root)/'public.txt'; link.symlink_to(secret)
            for path in (secret, link):
                result = self.run_python('from pathlib import Path; print(Path('+repr(str(path))+').read_text())')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('synthetic-only', result.stdout)

    def test_network_denied(self):
        result = self.run_python('import socket; socket.create_connection(("127.0.0.1", 9), timeout=1)')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Operation not permitted', result.stderr)

    def test_descendant_cannot_escape(self):
        with tempfile.TemporaryDirectory() as root:
            secret=Path(root)/'.env'; secret.write_text('synthetic-only')
            result=restricted_run('/bin/cat '+str(secret), shell=True, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('synthetic-only', result.stdout)

    def test_keychain_access_denied(self):
        result=restricted_run(['/usr/bin/security','find-generic-password','-s','KURT-SYNTHETIC-MISSING'], capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)

    def test_service_cannot_read_kurt_vault(self):
        import subprocess
        from kurt.utils.execution import service_argv
        from kurt.utils.security import child_env
        with tempfile.TemporaryDirectory() as root:
            vault=Path(root)/'.kurt'; vault.mkdir()
            secret=vault/'custom-name.txt'; secret.write_text('synthetic-only')
            with patch('kurt.utils.execution.Path.home', return_value=Path(root)):
                argv=service_argv(['/bin/cat',str(secret)],'mcp')
            result=subprocess.run(argv,env=child_env(),capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('synthetic-only',result.stdout)

class WindowsGuardTests(unittest.TestCase):
    """This runner has no real Windows host, so platform.system() is patched
    to exercise the lexical guard's control flow. It verifies the guard's
    logic, not kernel-level enforcement — see the module docstring on
    execution.py: unlike macOS Seatbelt, this can be defeated by a command
    that builds a sensitive path indirectly at runtime. Re-verify on an
    actual Windows host before trusting this as equivalent to the Mac path."""

    def test_benign_shell_command_passes_through(self):
        from kurt.utils import execution
        with patch('kurt.utils.execution.platform.system', return_value='Windows'):
            argv = execution.restricted_argv('echo hi', shell=True)
        self.assertEqual(argv, ['cmd', '/c', 'echo hi'])

    def test_benign_argv_passes_through(self):
        from kurt.utils import execution
        with patch('kurt.utils.execution.platform.system', return_value='Windows'):
            argv = execution.restricted_argv(['python', 'script.py'], shell=False)
        self.assertEqual(argv, ['python', 'script.py'])

    def test_protected_directory_reference_refused(self):
        from kurt.utils import execution
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            with patch('kurt.utils.execution.Path.home', return_value=home), \
                 patch('kurt.utils.execution.platform.system', return_value='Windows'):
                variants = (
                    f'{home}\\.ssh\\id_rsa',
                    f'{home}/.SSH/id_rsa',
                    str(home / '.aws' / 'credentials'),
                )
                for variant in variants:
                    with self.subTest(variant=variant):
                        with self.assertRaises(RuntimeError):
                            execution.restricted_argv(f'type {variant}', shell=True)

    def test_credential_filename_anywhere_refused(self):
        from kurt.utils import execution
        with patch('kurt.utils.execution.platform.system', return_value='Windows'):
            with self.assertRaises(RuntimeError):
                execution.restricted_argv('cat somewhere\\credentials.json', shell=True)

    def test_service_argv_also_guarded(self):
        from kurt.utils import execution
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            with patch('kurt.utils.execution.Path.home', return_value=home), \
                 patch('kurt.utils.execution.platform.system', return_value='Windows'):
                safe = execution.service_argv(['claude', '--print', 'hi'], 'claude')
                self.assertEqual(safe, ['claude', '--print', 'hi'])
                with self.assertRaises(RuntimeError):
                    execution.service_argv(['claude', '--print', str(home / '.aws' / 'credentials')], 'claude')

    def test_restricted_run_builds_windows_argv_and_env(self):
        from kurt.utils import execution
        captured = {}

        def fake_run(argv, **kwargs):
            captured['argv'] = argv
            captured['kwargs'] = kwargs
            return SimpleNamespace(returncode=0, stdout='ok', stderr='')

        with patch('kurt.utils.execution.platform.system', return_value='Windows'), \
             patch('kurt.utils.execution.subprocess.run', side_effect=fake_run):
            result = execution.restricted_run('echo hi', shell=True)
        self.assertEqual(captured['argv'], ['cmd', '/c', 'echo hi'])
        self.assertEqual(result.returncode, 0)
        self.assertIn('creationflags', captured['kwargs'])


class PolicyTests(unittest.TestCase):
    def test_unsupported_host_fails_closed(self):
        with patch('kurt.utils.execution.platform.system', return_value='Other'):
            with self.assertRaises(RuntimeError): restricted_run(['true'])

    def test_cloud_vision_default_off(self):
        from kurt.core.vision import describe_screen_claude
        with patch.dict(os.environ, {}, clear=True):
            result=describe_screen_claude('synthetic-image')
        self.assertFalse(result.success)
        self.assertIn('disabled', result.error)

    def test_background_cannot_use_cloud_even_when_opted_in(self):
        from kurt.core.vision import smart_vision
        with patch('kurt.core.vision._ollama_available', return_value=False), patch('kurt.core.vision.describe_screen_claude', side_effect=AssertionError('must not send screenshot')):
            result=smart_vision('synthetic-image','describe',allow_cloud=False)
        self.assertFalse(result.success)

    def test_remote_mcp_requires_tls(self):
        from kurt.utils.security import require_secure_endpoint
        for url in ('http://example.org/mcp', 'https://user:pass@example.org/mcp', 'file:///tmp/mcp', 'http://localhost.evil.test/mcp'):
            with self.subTest(url=url), self.assertRaises(ValueError): require_secure_endpoint(url)
        for url in ('https://example.org/mcp', 'http://127.0.0.1:9999/mcp', 'http://localhost/mcp', 'http://[::1]:9999/mcp'):
            require_secure_endpoint(url)

    def test_trusted_cli_metacharacters_never_enter_shell(self):
        from kurt.core.cli_orchestrator import _run_shell
        from types import SimpleNamespace
        with patch('kurt.core.cli_orchestrator.subprocess.run', return_value=SimpleNamespace(returncode=0,stdout='ok',stderr='')) as run:
            _run_shell('gh', 'status; echo unsafe')
        self.assertFalse(run.call_args.kwargs['shell'])
        self.assertEqual(run.call_args.args[0][-4:], ['gh', 'status;', 'echo', 'unsafe'])

    def test_cron_never_embeds_prompt_or_name(self):
        from kurt.core.scheduler import install_cron
        from types import SimpleNamespace
        task={'id':'task-001','name':'injected\n* * * * * evil','prompt':"unsafe ' ; echo secret",'cron':'0 9 * * *'}
        with tempfile.TemporaryDirectory() as root, patch('kurt.core.scheduler.KURT_DIR',Path(root)), patch('kurt.core.scheduler.subprocess.run', return_value=SimpleNamespace(returncode=0,stdout='',stderr='')) as run:
            install_cron(task)
        text=run.call_args.kwargs['input']
        self.assertIn('kurt schedule run task-001',text)
        self.assertNotIn(task['prompt'],text)
        self.assertNotIn(task['name'],text)
        for invalid in ('* * * * *\nevil','* * * * *; echo bad'):
            with self.assertRaises(ValueError): install_cron({**task,'cron':invalid})

    def test_background_events_do_not_contain_image_bytes(self):
        from kurt.core.screen_watcher import ScreenWatcher
        watcher=ScreenWatcher(use_vision=False)
        events=[]; watcher.on_event(events.append)
        watcher._on_screen_changed('synthetic-private-image',1.0)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0].screenshot_b64,'')
        self.assertNotIn('synthetic-private-image',repr(watcher._event_history))
