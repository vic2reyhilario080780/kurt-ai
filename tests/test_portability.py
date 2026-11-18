import json
import io
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bootstrap
from kurt.core import device, persona


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for key,value in [('KURT_DIR',self.root),('PERSONA_PATH',self.root/'persona.json')]:
            p = patch.object(persona,key,value); p.start(); self.addCleanup(p.stop)

    def test_install_plan_uses_per_os_virtual_environment_without_implicit_models_or_npm(self):
        for system,suffix in [('Windows','Scripts/python.exe'),('Darwin','bin/python'),('Linux','bin/python')]:
            with self.subTest(system=system):
                plan = bootstrap.installation_plan(self.root,system,['web','media'])
                self.assertTrue(plan['python'].replace('\\','/').endswith(suffix))
                self.assertFalse(plan['global_python_install'])
                self.assertFalse(plan['downloads_local_models'])
                self.assertFalse(plan['cli_tools'])
                self.assertTrue(all(command[0] == plan['python'] for command in plan['commands']))

    def test_browser_download_is_explicit_and_installs_required_extra(self):
        plain = bootstrap.installation_plan(self.root,'Linux',[])
        self.assertFalse(any('playwright' in c for c in plain['commands']))
        browser = bootstrap.installation_plan(self.root,'Linux',[],browser=True)
        self.assertIn('web',browser['features'])
        self.assertTrue(any(c[2:] == ['playwright','install','chromium'] for c in browser['commands']))
        with self.assertRaises(ValueError):bootstrap.installation_plan(self.root,'Unknown',[])
        with self.assertRaises(ValueError):bootstrap.installation_plan(self.root,'Linux',['offline'])

    def test_dry_run_never_creates_environment_or_starts_process(self):
        args = type('Args',(),{'features':'web','cli_tools':False,'browser':False,'dry_run':True})()
        with patch.object(bootstrap,'ROOT',self.root),patch.object(bootstrap.subprocess,'run') as run, \
             patch('builtins.print'):
            bootstrap.install(args)
        run.assert_not_called(); self.assertFalse((self.root/'.venv').exists())

    def test_export_import_preserves_preferences_and_leaves_machine_secrets_and_paths_untouched(self):
        persona.save_persona({'user_name':'Daddy Tito','kurt_name':'Bhe','default_model':'mistral-small-latest|mistral',
                             'default_cli':'auto','default_image_model':'fal-ai/nano-banana|fal',
                             'wallet_token_file':'/old/private.kurt-token','wallet_enabled':True,
                             'active_projects':['/Users/old/project'],'API_KEY':'synthetic-secret'})
        target = self.root/'transfer.json'
        result = device.export_settings(target)
        self.assertFalse(result['credentials_included'])
        exported = target.read_text()
        for value in ('synthetic-secret','/old/private','/Users/old/project','wallet_enabled','API_KEY'):
            self.assertNotIn(value,exported)
        persona.save_persona({'user_name':'New','wallet_token_file':'C:/new/device.kurt-token',
                             'wallet_enabled':False,'active_projects':['C:/project']})
        device.import_settings(target)
        saved = persona.load_persona()
        self.assertEqual(saved['user_name'],'Daddy Tito')
        self.assertEqual(saved['default_image_model'],'fal-ai/nano-banana|fal')
        self.assertEqual(saved['wallet_token_file'],'C:/new/device.kurt-token')
        self.assertFalse(saved['wallet_enabled'])
        self.assertEqual(saved['active_projects'],['C:/project'])

    def test_unavailable_cli_falls_back_with_visible_warning(self):
        persona.save_persona({'default_cli':'copilot'})
        target = self.root/'transfer.json'; device.export_settings(target)
        with patch('kurt.core.cli_orchestrator._cmd_exists',return_value=False):
            result = device.import_settings(target)
        self.assertTrue(result['warnings'])
        self.assertEqual(persona.load_persona()['default_cli'],'auto')

    def test_untrusted_settings_rejected_before_writing(self):
        persona.save_persona({'user_name':'Unchanged'})
        target = self.root/'bad.json'
        for settings in [{'wallet_enabled':True},{'compact_mode':'yes'},{'default_cli':'shell'},
                         {'speech_provider':'unknown'},{'speech_vocabulary':['ok',123]},
                         {'user_name':['invalid']},{'default_model':'bad|unsupported'}]:
            target.write_text(json.dumps({'format':'kurt-portable-settings','version':1,'settings':settings}))
            with self.subTest(settings=settings),self.assertRaises(ValueError):device.import_settings(target)
            self.assertEqual(persona.load_persona()['user_name'],'Unchanged')
        target.write_text('{"format":"kurt-portable-settings","version":1,"settings":{"user_name":"a","user_name":"b"}}')
        with self.assertRaisesRegex(ValueError,'Duplicate'):device.import_settings(target)

    def test_oversize_and_overwrite_exports_rejected(self):
        target = self.root/'transfer.json'; target.write_text('existing')
        with self.assertRaises(ValueError):device.export_settings(target)
        self.assertEqual(target.read_text(),'existing')
        target.write_bytes(b' '*(device.MAX_SETTINGS+1))
        with self.assertRaises(ValueError):device.import_settings(target)

    def test_status_reports_platform_limits_without_inference_or_desktop_imports(self):
        for system in ('Windows','Darwin','Linux'):
            with self.subTest(system=system),patch.object(device.platform,'system',return_value=system), \
                 patch('kurt.core.cli_orchestrator._cmd_exists',return_value=False):
                status = device.device_status()
            self.assertEqual(status['os'],system)
            self.assertFalse(status['credentials_tested'])
            self.assertFalse(status['model_requests_submitted'])
            if system != 'Darwin':self.assertIn('unavailable',status['features']['read_only_cli_adapters'])

    def test_device_commands_are_registered_without_entering_chat(self):
        from typer.testing import CliRunner
        from kurt.main import app
        result = CliRunner().invoke(app,['device','status'])
        self.assertEqual(result.exit_code,0,result.output)
        self.assertIn('"model_requests_submitted": false',result.output)

    def test_windows_picker_and_commands_block_mac_only_adapters(self):
        from kurt.core import command_palette, cli_orchestrator, execution_preferences
        with patch('platform.system',return_value='Windows'), \
             patch.object(cli_orchestrator,'_cmd_exists',return_value=True):
            rows = command_palette._cli_default_items('copilot')
            result = cli_orchestrator.handle_slash('/cli default copilot','s','auto',None)
            with self.assertRaises(ValueError):execution_preferences.save_default_cli('deepseek')
        self.assertEqual(rows[0]['kind'],'info')
        self.assertIsNone(result.cli_override)
        self.assertIn('macOS',result.output)

    def test_windows_npm_launcher_keeps_prompt_literal_without_shell(self):
        from kurt.utils.execution import windows_cli_argv
        folder = self.root/'node_modules'; package = folder/'@google/gemini-cli'
        package.mkdir(parents=True); (package/'entry.js').write_text('// fixture')
        (package/'package.json').write_text(json.dumps({'bin':{'gemini':'entry.js'}}))
        shim = folder/'.bin/gemini.cmd'
        with patch('kurt.utils.execution.shutil.which',return_value='/node.exe'):
            result = windows_cli_argv([str(shim),'-p','hello & echo SHOULD_NOT_RUN'])
        self.assertEqual(result,['/node.exe',str((package/'entry.js').resolve()),'-p','hello & echo SHOULD_NOT_RUN'])
        with self.assertRaises(RuntimeError):windows_cli_argv([str(folder/'.bin/unknown.cmd')])
        (package/'package.json').write_text(json.dumps({'bin':{'gemini':'../../escape.js'}}))
        with self.assertRaises(RuntimeError):windows_cli_argv([str(shim)])

    def test_windows_resolution_prefers_cmd_over_unix_shell_shim(self):
        from kurt.core import cli_orchestrator
        for name in ('gemini','gemini.cmd'):
            path=self.root/name;path.write_text('fixture');path.chmod(0o755)
        with patch.object(cli_orchestrator,'NODE_BIN',self.root),patch.object(sys,'platform','win32'):
            self.assertEqual(cli_orchestrator._resolve_cmd('gemini'),str(self.root/'gemini.cmd'))

    def test_threaded_pipe_reader_handles_stdout_stderr_and_limits(self):
        from kurt.utils.process import _threaded_output
        for code,limit,expected in [('import sys; print("OUT"); print("ERR",file=sys.stderr)',8192,'completed'),
                ('import time; time.sleep(10)',8192,'timed_out'),('print("x"*20000)',1000,'output_limit')]:
            process = subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                status,out,err = _threaded_output(process,.5 if expected=='timed_out' else 10,limit)
                self.assertEqual(status,expected)
                self.assertLessEqual(len(out)+len(err),limit)
                if expected=='completed':self.assertIn(b'OUT',out);self.assertIn(b'ERR',err)
            finally:
                if process.poll() is None:process.kill()
                process.wait(timeout=5);process.stdout.close();process.stderr.close()

    def test_bounded_runner_completes_and_cleans_up_timeouts_on_current_os(self):
        from kurt.utils.process import run_bounded
        env = dict(os.environ)
        good = run_bounded([sys.executable,'-c','import sys; print(sys.stdin.read()); print("ERR",file=sys.stderr)'],
                           env=env,cwd=str(self.root),input_text='PORTABLE',timeout=10)
        self.assertEqual(good['status'],'completed');self.assertIn('PORTABLE',good['stdout'])
        self.assertIn('ERR',good['stderr'])
        limited = run_bounded([sys.executable,'-c','import time; time.sleep(30)'],env=env,cwd=str(self.root),timeout=.5)
        self.assertEqual(limited['status'],'timed_out');self.assertIsNotNone(limited['exit_code'])

    def test_windows_cp1252_output_is_reconfigured_before_unicode_rendering(self):
        from kurt.utils import terminal
        raw=io.BytesIO();stream=io.TextIOWrapper(raw,encoding='cp1252')
        with patch.object(terminal.sys,'platform','win32'),patch.object(terminal.sys,'stdout',stream), \
             patch.object(terminal.sys,'stderr',stream):
            terminal.configure_windows_output()
            stream.write('\U0001f916 Kurt');stream.flush()
        self.assertEqual(raw.getvalue(),'\U0001f916 Kurt'.encode())
        stream.close()

    def test_non_windows_output_encoding_is_preserved(self):
        from kurt.utils import terminal
        raw=io.BytesIO();stream=io.TextIOWrapper(raw,encoding='latin-1')
        with patch.object(terminal.sys,'platform','linux'),patch.object(terminal.sys,'stdout',stream):
            terminal.configure_windows_output()
        self.assertEqual(stream.encoding,'latin-1');stream.close()
