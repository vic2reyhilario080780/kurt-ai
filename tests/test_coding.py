"""Coding harness tests run real tools on disposable repositories only."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from kurt.core.agent_loop import TOOLS, execute_tool, parse_tool_call, run_agent
from kurt.core.agent_schema import agent_function_schemas
from kurt.core.coding import run_coding_task
from kurt.core.coding_tools import run_checks
from kurt.core.codex_adapter import permission_args, run_codex
from kurt.utils.workspace import workspace


def call(name,**params):return '```tool\n'+json.dumps({'tool':name,'params':params})+'\n```'


class Replies:
    supports_native_tools=True
    def __init__(self,replies):self.replies=list(replies);self.options=[]
    async def route(self,**options):
        self.options.append(options)
        yield self.replies.pop(0)


class ContractTests(unittest.TestCase):
    def test_every_tool_has_a_provider_schema(self):
        schemas=agent_function_schemas(TOOLS)
        self.assertEqual({t['name'] for t in TOOLS},{t['function']['name'] for t in schemas})
        for item in schemas:
            params=item['function']['parameters']
            self.assertEqual(params['type'],'object')
            self.assertFalse(params['additionalProperties'])
        lookup={s['function']['name']:s['function']['parameters'] for s in schemas}
        self.assertEqual(lookup['multi_edit']['properties']['edits']['items']['type'],'object')
        self.assertEqual(lookup['run_checks']['properties']['argv']['type'],'array')

    def test_parser_handles_nested_objects_and_malformed_params(self):
        value=call('mcp_tool',tool_ref='test/tool',params={'deep':{'nested':[1,2]}})
        name,params=parse_tool_call(value)
        self.assertEqual(name,'mcp_tool');self.assertEqual(params['params']['deep']['nested'],[1,2])
        for text in ('[]','{"tool":"done","params":[]}','{"tool":"done","params":"bad"}'):
            self.assertEqual(parse_tool_call(text),(None,None))

    def test_mcp_discovery_is_on_demand(self):
        from kurt.core.agent_loop import _build_mcp_tools_prompt
        with patch('kurt.core.agent_loop.load_registry',return_value={'test':SimpleNamespace(enabled=True)}),patch('kurt.core.agent_loop.mcp_list_tools',side_effect=AssertionError('must not start server')):
            text=asyncio.run(_build_mcp_tools_prompt())
        self.assertIn('test',text)

    def test_file_tools_reject_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as root,tempfile.TemporaryDirectory() as other,workspace(root):
            target=Path(other)/'file.txt';target.write_text('private-other-project')
            (Path(root)/'link').symlink_to(target)
            for path in (str(target),'link'):
                result=execute_tool('read_file',{'path':path})
                self.assertIn('escapes',result)
                self.assertNotIn('private-other-project',result)

    def test_codex_permissions_are_not_bypassed(self):
        args=permission_args('workspace-write')
        self.assertIn('approval_policy="never"',args)
        self.assertTrue(any('".env' in arg or '**/.env' in arg for arg in args))
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',args)
        self.assertTrue(any('default_permissions' in arg for arg in args))
        with self.assertRaises(ValueError):permission_args('danger-full-access')

    def test_codex_events_required_for_success_and_prompt_uses_stdin(self):
        events='\n'.join(json.dumps(x) for x in [{'type':'item.completed','item':{'type':'agent_message','text':'done'}},{'type':'turn.completed'}])
        result={'status':'completed','stdout':events,'stderr':'','exit_code':0,'truncated':False}
        with tempfile.TemporaryDirectory() as root,patch('kurt.core.codex_adapter.executable',return_value='/bin/codex'),patch('kurt.core.codex_adapter.run_bounded',return_value=dict(result)) as run:
            report=run_codex('fix $(touch NOT_A_SHELL)',cwd=root)
        self.assertEqual(report['status'],'completed')
        argv=run.call_args.args[0]
        self.assertEqual(argv[-1],'-')
        self.assertNotIn('fix $(touch NOT_A_SHELL)',argv)
        self.assertEqual(run.call_args.kwargs['input_text'],'fix $(touch NOT_A_SHELL)')
        with tempfile.TemporaryDirectory() as root,patch('kurt.core.codex_adapter.executable',return_value='/bin/codex'),patch('kurt.core.codex_adapter.run_bounded',return_value={**result,'stdout':'not a completion'}):
            self.assertEqual(run_codex('fix',cwd=root)['status'],'failed')

    def test_failed_edit_is_not_reported_as_changed(self):
        with tempfile.TemporaryDirectory() as root,patch('kurt.core.agent_loop._build_mcp_tools_prompt',return_value=''):
            router=Replies([call('edit_file',path='missing.py',old_str='a',new_str='b'),call('done',summary='No edit applied')])
            result=asyncio.run(run_agent('inspect',SimpleNamespace(provider='groq',model='test'),router,cwd=root))
        self.assertEqual(result.files_changed,[])

    def test_loop_limit_reports_incomplete(self):
        with tempfile.TemporaryDirectory() as root,patch('kurt.core.agent_loop._build_mcp_tools_prompt',return_value=''):
            result=asyncio.run(run_agent('inspect',SimpleNamespace(provider='groq',model='test'),Replies([call('list_dir')]),cwd=root,max_steps=1))
        self.assertFalse(result.success)
        self.assertIn('Incomplete',result.final_summary)


class RealCodingToolsTests(unittest.TestCase):
    def test_read_edit_test_cycle_in_selected_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            (root/'calc.py').write_text('def add(a,b):\n    return a-b\n')
            (root/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass TestAdd(unittest.TestCase):\n def test_add(self): self.assertEqual(add(1,2),3)\n')
            subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
            router=Replies([call('read_file',path='calc.py'),call('edit_file',path='calc.py',old_str='return a-b',new_str='return a+b'),
                            call('run_checks',argv=[sys.executable,'-m','unittest','-q','test_calc']),call('done',summary='Fixed add and verified the real test')])
            with patch('kurt.core.agent_loop._build_mcp_tools_prompt',return_value=''):
                result=run_coding_task('Fix arithmetic',cwd=root,router=router)
            self.assertIn('return a+b',(root/'calc.py').read_text())
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['verification'],'passed')
            self.assertEqual(result['checks'][0]['exit_code'],0)
            self.assertEqual(result['git_before']['status'],'passed',result['git_before'])
            self.assertEqual(result['diff']['status'],'passed')
            self.assertIn('edit_file',{t['function']['name'] for t in router.options[0]['native_tools']})

    def test_output_limit_is_not_a_passing_check(self):
        with tempfile.TemporaryDirectory() as root,workspace(root):
            result=run_checks([sys.executable,'-c','print("x"*300000)'])
        self.assertEqual(result['status'],'output_limit')
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['stdout'])+len(result['stderr']),128*1024)

    def test_provider_keys_not_in_test_process(self):
        with tempfile.TemporaryDirectory() as root,workspace(root),patch.dict(os.environ,{'SYNTHETIC_API_KEY':'private-test-only'}):
            result=run_checks([sys.executable,'-c','import os; print(os.getenv("SYNTHETIC_API_KEY","ABSENT"))'])
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['stdout'].strip(),'ABSENT')

    @unittest.skipUnless(shutil.which('codex'),'Codex CLI not installed')
    def test_actual_codex_sandbox_profile_blocks_secret_reads(self):
        binary=shutil.which('codex')
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);secret=root/'.env';secret.write_text('synthetic-only')
            command=[binary,'sandbox','-P','kurt-coding','-C',str(root),*permission_args('workspace-write'),
                     sys.executable,'-c','from pathlib import Path; Path("allowed.txt").write_text("ok"); print(Path(".env").read_text())']
            result=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('synthetic-only',result.stdout)
            self.assertTrue((root/'allowed.txt').exists(),result.stderr)

    def test_project_skill_read_and_symlink_escape(self):
        from kurt.core.coding_tools import project_skills
        with tempfile.TemporaryDirectory() as root,tempfile.TemporaryDirectory() as outside,workspace(root):
            folder=Path(root)/'.agents/skills/review';folder.mkdir(parents=True)
            (folder/'SKILL.md').write_text('Inspect changed files and run relevant tests.')
            bad=Path(outside)/'SKILL.md';bad.write_text('outside-private-instructions')
            (folder.parent/'outside').symlink_to(Path(outside),target_is_directory=True)
            listing=project_skills()
            self.assertIn('.agents/skills/review',listing['skills'])
            self.assertNotIn('.agents/skills/outside',listing['skills'])
            self.assertIn('Inspect changed files',project_skills('read','.agents/skills/review')['instructions'])

    def test_generic_command_cannot_write_outside_workspace(self):
        import uuid
        target=Path(__file__).resolve().parent/('coding-guard-'+uuid.uuid4().hex)
        try:
            with tempfile.TemporaryDirectory() as root,workspace(root):
                result=run_checks([sys.executable,'-c','from pathlib import Path; Path('+repr(str(target))+').write_text("denied")'])
            self.assertEqual(result['status'],'failed')
            self.assertFalse(target.exists())
        finally:target.unlink(missing_ok=True)

    def test_legacy_codex_policy_is_not_silently_used(self):
        with tempfile.TemporaryDirectory() as root:
            config=Path(root)/'.codex';config.mkdir();(config/'config.toml').write_text('sandbox_mode = "danger-full-access"\n')
            with patch('kurt.core.codex_adapter.run_bounded',side_effect=AssertionError('must not run')):
                with self.assertRaises(ValueError):run_codex('fix',cwd=root)

    def test_agent_cannot_read_codex_oauth_state(self):
        with tempfile.TemporaryDirectory() as root,workspace(root):
            folder=Path(root)/'.codex';folder.mkdir()
            (folder/'auth.json').write_text('{"access_token":"synthetic-private-token"}')
            result=execute_tool('read_file',{'path':'.codex/auth.json'})
            self.assertNotIn('synthetic-private-token',result)
            self.assertIn('excluded',result)
