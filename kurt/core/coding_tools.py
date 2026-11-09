"""Coding tools with concrete verification results, scoped to the active repo."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from kurt.utils.execution import restricted_run, restricted_argv, service_argv
from kurt.utils.process import run_bounded
from kurt.utils.security import child_env
from kurt.utils.security import redact
from kurt.utils.workspace import current_workspace, workspace_path

CODING_TOOLS = [
    {'name':'project_skills','description':'Discover or read project SKILL.md workflows without executing their scripts.',
     'parameters':{'action':'optional string — list or read','skill':'optional string — skill ID returned by list'}},
    {'name':'git_inspect','description':'Inspect git status, diff or recent log without mutating the repository.',
     'parameters':{'action':'optional string — status, diff or log','staged':'optional boolean — staged diff only'}},
    {'name':'run_checks','description':'Run an exact test/build command argv in the active workspace. Returns actual exit code and bounded output.',
     'parameters':{'argv':'list of strings — executable and arguments, never a shell string','timeout':'optional integer — 1 to 120 seconds'}},
    {'name':'mcp_list_tools','description':'Discover tool names and schemas from one configured MCP server on demand.',
     'parameters':{'server':'string — configured server name'}},
    {'name':'codex_task','description':'Delegate a coding task to installed Codex CLI with explicit workspace permissions. Requires its own login.',
     'parameters':{'task':'string — coding or review task','mode':'optional string — read-only or workspace-write','timeout':'optional integer — 1 to 600 seconds'}},
]


def git_inspect(action='status', staged=False):
    if action not in ('status','diff','log') or not isinstance(staged,bool):
        raise ValueError('Expected status, diff or log')
    # macOS /usr/bin/git is an Xcode launcher that needs forbidden XPC services.
    # Use the actual installed Git executable without relaxing IPC restrictions.
    git = '/Library/Developer/CommandLineTools/usr/bin/git'
    if not Path(git).is_file():git='git'
    args = [git,'--no-pager' ,'-c','core.fsmonitor=false','-c','core.excludesFile=/dev/null','-c','core.hooksPath=/dev/null']
    if action == 'status': args += ['status','--short','--untracked-files=normal','--ignore-submodules=all']
    elif action == 'log': args += ['log','-5','--format=%h %s']
    else: args += ['diff','--no-ext-diff','--no-textconv','--ignore-submodules=all'] + (['--cached'] if staged else [])
    env=child_env(extra={'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
                         'GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'})
    result=run_bounded(service_argv(args,'git'),env=env,cwd=str(current_workspace()),timeout=30,max_output=128*1024)
    if result['status']=='completed':result['status']='passed'
    result['argv']=args
    return redact(result)


def run_checks(argv, timeout=60):
    if not isinstance(argv,list) or not argv or len(argv)>100 or any(not isinstance(a,str) or '\0' in a for a in argv):
        raise ValueError('A nonempty command argument array is required')
    if type(timeout) is not int or not 1<=timeout<=120:
        raise ValueError('Timeout must be 1 to 120 seconds')
    result=run_bounded(restricted_argv(argv), env=child_env(),cwd=str(current_workspace()),timeout=timeout,max_output=128*1024)
    result['argv']=redact(argv)
    if result['status']=='failed' and result['exit_code'] is not None and result['exit_code']<0:
        result['hint']='Process was terminated by a signal. Inspect sandbox/tool initialization; this does not prove the project or repository is missing.'
    if result['status']=='completed':result['status']='passed'
    return redact(result)


def project_skills(action='list', skill=None):
    if action not in ('list','read'):raise ValueError('Expected list or read')
    root=current_workspace()
    found={}
    for name in ('.agents/skills','.skills','skills'):
        try:folder=workspace_path(name)
        except ValueError:continue
        if not folder.is_dir():continue
        for path in folder.rglob('SKILL.md'):
            try:path=workspace_path(path)
            except ValueError:continue
            if len(found)>=100:break
            found[str(path.parent.relative_to(root))]=path
    if action=='list':return {'skills':sorted(found),'limit':100}
    if skill not in found:raise ValueError('Unknown project skill; list skills first')
    with found[skill].open('rb') as stream:raw=stream.read(16385)
    return {'skill':skill,'instructions':redact(raw[:16384].decode(errors='replace')),'truncated':len(raw)>16384}


def execute_coding_tool(name, params):
    if name=='project_skills':return project_skills(params.get('action','list'),params.get('skill'))
    if name=='git_inspect': return git_inspect(params.get('action','status'),params.get('staged',False))
    if name=='run_checks': return run_checks(params.get('argv'),params.get('timeout',60))
    if name=='codex_task':
        from kurt.core.codex_adapter import run_codex
        return run_codex(params.get('task',''),cwd=current_workspace(),mode=params.get('mode','read-only'),timeout=params.get('timeout',180))
    if name=='mcp_list_tools':
        from kurt.core.mcp_client import load_registry, list_tools
        from kurt.core.agent_loop import _run_coro_blocking
        name=params.get('server')
        conn=load_registry().get(name)
        if conn is None or not conn.enabled: raise ValueError('Unknown or disabled MCP server')
        tools=_run_coro_blocking(list_tools(conn))
        return {'server':name,'tools':[{'name':t.name,'description':redact(t.description),'schema':redact(t.input_schema)} for t in tools[:30]],'truncated':len(tools)>30}
    raise ValueError('Unknown coding tool')
