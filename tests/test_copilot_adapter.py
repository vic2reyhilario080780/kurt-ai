import json
import os
import platform
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core import copilot_adapter as adapter, persona, execution_preferences as prefs
from kurt.core import cli_orchestrator as cli, command_palette
from kurt.billing.client import CLI_CONTEXT, cli_environment
from kurt.utils.execution import sandbox_profile, service_argv


def events(*extra):
    return '\n'.join(json.dumps(e) for e in (
        {'type':'assistant.message','data':{'content':'READY'}}, *extra,
        {'type':'result','exitCode':0}))


class CopilotAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for obj, key, value in [(persona,'KURT_DIR',self.root), (persona,'PERSONA_PATH',self.root/'persona.json')]:
            p = patch.object(obj,key,value); p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ,{'KURT_WALLET_MODE':'0'}); p.start(); self.addCleanup(p.stop)

    def test_picker_default_and_slash_dispatch(self):
        with patch.object(cli,'_cmd_exists',return_value=True):
            rows = command_palette._cli_default_items('copilot')
        self.assertEqual(rows[0]['value'],'/cli default copilot')
        prefs.save_default_cli('copilot')
        self.assertEqual(prefs.ExecutionSession.load().cli,'copilot')
        with patch.object(adapter,'run_copilot',return_value={'status':'completed','final_text':'READY'}) as run:
            result = cli.handle_slash('/copilot review this','s','auto',None)
        self.assertEqual(result.output,'READY'); run.assert_called_once()
        self.assertIn('review this',run.call_args.args[0])

    def test_final_event_required_and_partial_errors_not_success(self):
        self.assertEqual(adapter.final_reply(events()),'READY')
        cases = [json.dumps({'type':'assistant.message','data':{'content':'partial'}}),
                 events({'type':'session.error','data':{'message':'authentication failed'}}),
                 events({'type':'tool.execution_complete','data':{'success':False}}),
                 events().replace('"exitCode": 0','"exitCode": 1'),
                 json.dumps({'type':'result','exitCode':0}), 'not-json']
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError): adapter.final_reply(case)

    def test_tool_planning_text_is_not_final_answer(self):
        output = '\n'.join(json.dumps(e) for e in [
            {'type':'assistant.message','data':{'content':'I will inspect','toolRequests':[{'name':'view'}]}},
            {'type':'result','exitCode':0}])
        with self.assertRaises(ValueError):adapter.final_reply(output)

    def test_adapter_limits_tools_and_never_enables_blanket_permissions(self):
        with patch.object(cli,'_resolve_cmd',return_value='/test/copilot'), \
             patch.object(adapter,'service_argv',side_effect=lambda a,s,**kw:a) as sandbox, \
             patch.object(adapter,'run_bounded',return_value={'status':'completed','exit_code':0,'stdout':events(),'stderr':''}) as run:
            result = adapter.run_copilot('Review only')
        self.assertEqual(result['final_text'],'READY')
        argv = run.call_args.args[0]
        self.assertIn('--available-tools=view,glob,grep',argv)
        self.assertIn('--deny-tool=write',argv); self.assertIn('--deny-tool=shell',argv)
        self.assertNotIn('--allow-all-tools',argv); self.assertNotIn('--trust-folder',argv)
        self.assertTrue(sandbox.call_args.kwargs['write_paths'])
        self.assertEqual(run.call_args.kwargs['timeout'],120)

    def test_timeout_no_replay_and_token_echo_is_redacted(self):
        with patch.object(cli,'_resolve_cmd',return_value='/test/copilot'), \
             patch.dict(os.environ,{'COPILOT_GITHUB_TOKEN':'synthetic-copilot-secret'}), \
             patch.object(adapter,'service_argv',side_effect=lambda a,s,**kw:a), \
             patch.object(adapter,'run_bounded',return_value={'status':'timed_out','stdout':'','stderr':'synthetic-copilot-secret','exit_code':-9}) as run:
            result = adapter.run_copilot('Review only')
        self.assertEqual(result['status'],'timed_out')
        self.assertNotIn('synthetic-copilot-secret',result['stderr']);run.assert_called_once()

    def test_wallet_forces_scoped_provider_and_never_personal_login(self):
        context = {'cli':'copilot','root':self.root,'url':'https://wallet.example','provider':'openrouter',
                   'token':'kurt_cli_fixture','profile':{'model':'fixture/model'}}
        reset = CLI_CONTEXT.set(context)
        try:
            env = cli_environment('copilot',{'GH_TOKEN':'private','COPILOT_PROVIDER_BASE_URL':'https://other.example','PATH':'/usr/bin'})
            profile = sandbox_profile(service='copilot',write_paths=[self.root])
        finally: CLI_CONTEXT.reset(reset)
        self.assertEqual(env['COPILOT_PROVIDER_BASE_URL'],'https://wallet.example/wallet/proxy/openrouter/api/v1')
        self.assertEqual(env['COPILOT_PROVIDER_API_KEY'],'kurt_cli_fixture')
        self.assertEqual(env['COPILOT_MODEL'],'fixture/model')
        self.assertEqual(env['COPILOT_OFFLINE'],'true')
        self.assertNotIn('GH_TOKEN',env);self.assertNotIn('GITHUB_TOKEN',env)
        self.assertIn(str(Path.home()/'.copilot'),profile)
        self.assertIn(str(Path.home()/'Library/Keychains'),profile)

    def test_direct_environment_drops_inherited_provider_and_approval_overrides(self):
        with patch.dict(os.environ,{'COPILOT_PROVIDER_BASE_URL':'https://other.example',
                'COPILOT_PROVIDER_API_KEY':'private','COPILOT_ALLOW_ALL':'true',
                'COPILOT_GITHUB_TOKEN':'copilot-token','OPENAI_API_KEY':'unrelated'},clear=True):
            env = cli._ai_cli_env('/test/copilot')
        self.assertEqual(env['COPILOT_GITHUB_TOKEN'],'copilot-token')
        for key in ('COPILOT_PROVIDER_BASE_URL','COPILOT_PROVIDER_API_KEY','COPILOT_ALLOW_ALL','OPENAI_API_KEY'):
            self.assertNotIn(key,env)

    def test_copilot_credentials_protected_from_other_services(self):
        self.assertIn(str(Path.home()/'.copilot'),sandbox_profile(service='gemini'))
        self.assertNotIn('(subpath '+json.dumps(str(Path.home()/'.copilot'))+')',sandbox_profile(service='copilot'))

    @unittest.skipUnless(platform.system() == 'Darwin', 'Requires macOS Seatbelt')
    def test_kernel_blocks_project_write_even_if_child_ignores_tool_permissions(self):
        runtime = self.root/'runtime'; runtime.mkdir()
        target = self.root/'project.txt'
        code = 'from pathlib import Path; Path('+repr(str(target))+').write_text("unauthorized")'
        result = subprocess.run(service_argv([sys.executable,'-c',code],'copilot',write_paths=[runtime]),
                                capture_output=True,text=True,timeout=15)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Operation not permitted',result.stderr)
        self.assertFalse(target.exists())
