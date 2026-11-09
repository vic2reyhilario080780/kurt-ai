"""Explicit local Codex delegation with native permissions and JSONL results.

Codex enforces its own OS sandbox. We do not nest an outer Seatbelt sandbox or
silently disable Codex's sandbox when nesting/platform policy fails.
"""
import json
import os
import re
from pathlib import Path
import shutil

from kurt.utils.process import run_bounded
from kurt.utils.security import child_env, redact, require_public_file


def executable():
    local=Path(__file__).resolve().parents[2]/'node_modules/.bin/codex'
    return str(local) if local.is_file() and os.access(local,os.X_OK) else shutil.which('codex')


def _toml(value):
    if isinstance(value,dict):return '{'+', '.join(json.dumps(k)+' = '+_toml(v) for k,v in value.items())+'}'
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,int):return str(value)
    return json.dumps(value)


def permission_args(mode):
    if mode not in ('read-only','workspace-write'):
        raise ValueError('Codex mode must be read-only or workspace-write')
    scope={'.':'write' if mode=='workspace-write' else 'read'}
    for pattern in ('**/.env*','**/*.env','**/*.key','**/*.pem','**/*.kurt-token','**/credentials.json','**/credentials','**/auth.json','**/.credentials.json','**/.npmrc','**/.netrc','**/mcp_connections.json','**/control.db','**/.kurt/**','**/.kurt-saas/**','**/.codex/**','**/.claude/**','**/.aws/**','**/.openclaw-kurt/**'):
        scope[pattern]='deny'
    fs={':root':'deny',':minimal':'read',':workspace_roots':scope,'glob_scan_max_depth':8}
    for name in ('.kurt','.kurt-saas','.aws','.ssh','.gnupg','.config','.claude','.gemini','.codex','.openclaw','Library/Keychains'):
        fs[str(Path.home()/name)]='deny'
    # Homebrew and local Node runtimes are outside Codex's minimal system roots.
    for runtime in (Path('/opt/homebrew'), Path.home()/'.nvm/versions/node'):
        if runtime.is_dir():fs[str(runtime)]='read'
    profile={'extends' :':workspace' if mode=='workspace-write' else ':read-only','filesystem':fs,'network':{'enabled':False}}
    settings={'default_permissions':'kurt-coding','permissions.kurt-coding':profile,'approval_policy':'never',
              'shell_environment_policy.inherit':'none','mcp_servers':{}}
    args=[]
    for key,value in settings.items():args += ['-c',key+'='+_toml(value)]
    return args


def codex_status():
    binary=executable()
    if not binary:return {'installed':False,'ready':False,'hint':'Install Codex CLI and run codex login.'}
    env=child_env(allow=('OPENAI_API_KEY','CODEX_HOME'))
    result=run_bounded([binary,'login','status'],env=env,cwd=str(Path.cwd()),timeout=15,max_output=8192)
    return {'installed':True,'ready':result['status']=='completed','executable':binary,
            'status':result['status'],'details':redact(result['stdout']+result['stderr'])}


def run_codex(task, *, cwd='.', mode='read-only', timeout=180):
    if not isinstance(task,str) or not task.strip() or len(task.encode())>32768:
        raise ValueError('Codex task must be nonempty text, at most 32 KiB')
    if type(timeout) is not int or not 1<=timeout<=600:
        raise ValueError('Codex timeout must be 1 to 600 seconds')
    root=Path(cwd).expanduser().resolve()
    if not root.is_dir():raise ValueError('Workspace must exist')
    require_public_file(root)
    # Legacy project sandbox settings override named permission profiles in
    # Codex. Refuse such a configuration instead of quietly losing deny rules.
    for parent in (root, *root.parents):
        config=parent/'.codex/config.toml'
        if config.is_file() and parent != Path.home():
            content=config.read_text(encoding='utf-8')
            if re.search(r'(?m)^\s*(?:["\']?sandbox_mode["\']?\s*=|\[sandbox_workspace_write\])',content):
                raise ValueError('Legacy project sandbox settings must be migrated to permission profiles before Codex delegation')
    policy=permission_args(mode)
    binary=executable()
    if not binary:return {'status':'missing','hint':'Install Codex CLI and run codex login.','changes_verified':False}
    command=[binary,'exec','--ignore-user-config','--ignore-rules','--ephemeral','--json','--color','never',
             '--cd',str(root),*policy,'-']
    # Only Codex's own auth mechanism is available, never all Kurt provider keys.
    result=run_bounded(command,env=child_env(allow=('OPENAI_API_KEY','CODEX_HOME')),cwd=str(root),
                       timeout=timeout,input_text=redact(task),max_output=1024*1024)
    messages,events,changed=[],[],[]
    completed,failed=False,False
    for line in result.pop('stdout').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if not isinstance(event,dict):continue
        kind=event.get('type')
        if kind=='turn.completed':completed=True
        if kind in ('error','turn.failed'):failed=True
        item=event.get('item',{})
        if kind=='item.completed' and isinstance(item,dict):
            if item.get('type')=='agent_message' and isinstance(item.get('text'),str):messages.append(item['text'])
            if item.get('type')=='file_change' and item.get('status')=='completed':
                for change in item.get('changes',[]):
                    if not isinstance(change,dict) or not isinstance(change.get('path'),str):continue
                    path=(root/change['path']).resolve()
                    if path==root or root in path.parents:
                        changed.append(str(path.relative_to(root)))
        if len(events)<50:events.append({'type':kind,'item_type':item.get('type') if isinstance(item,dict) else None,
                                       'exit_code':item.get('exit_code') if isinstance(item,dict) else None})
    if result['status']=='completed' and (failed or not completed or not messages):result['status']='failed'
    result.update({'backend':'codex','mode':mode,'workspace':str(root),'final_text':'\n'.join(messages)[-16384:],
                   'reported_files_changed':sorted(set(changed)),'events':events,'changes_verified':False,
                   'hint':'Inspect the diff and check results. A timeout/output limit can leave partial edits; do not retry automatically.'})
    return redact(result)
