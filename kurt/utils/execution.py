"""Restricted runner for generated code and shell commands.

On macOS, Seatbelt enforces credential-file/IPC/network restrictions for the
process and its children. Unsupported hosts fail closed rather than silently
running generated code with full account access. Trusted service adapters have
separate, explicit credential grants and are not routed through this runner.
"""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from kurt.utils.workspace import current_workspace, active_workspace

from kurt.utils.security import child_env


def sandbox_profile(*, service=None, workspace=None):
    # Deny rules apply to descendants as well, including symlink-resolved reads.
    roots = [Path.home()/name for name in ('.kurt', '.kurt-saas', '.aws', '.ssh', '.gnupg', '.config', '.claude', '.codex', '.gemini', '.openclaw', '.kube', '.docker', '.azure', 'Library')]
    if service:
        # Service adapters keep only their own login/state directories usable.
        own = {"openclaw": ".openclaw", "claude": ".claude", "gemini": ".gemini"}.get(service)
        roots = [p for p in roots if p.name not in {own, "Library"}]
        if service != "claude":
            roots.append(Path.home()/"Library/Keychains")
        # claude is exempted: Claude Code's own OAuth/Pro login is stored in
        # the macOS Keychain, not a plain file under ~/.claude — blocking
        # Keychain reads broke /claude entirely ("Not logged in" even when
        # actually logged in). Verified via a direct before/after sandboxed
        # run: identical profile minus this one path fixes it, nothing else
        # needed. gemini/openclaw are untouched — no evidence they need this.
    if service != "openclaw":
        roots.append(Path(__file__).resolve().parents[2]/'.openclaw-kurt')
    filters = '\n'.join('(subpath ' + json.dumps(str(p.resolve())) + ')' for p in roots)
    names = r'(^|/)(\.env($|[./])|\.npmrc$|\.pypirc$|\.netrc$|\.git-credentials$|credentials(\.json)?$|secrets\.(json|yaml|yml)$|control\.db$|auth-profiles\.json$|id_(rsa|ed25519|ecdsa)($|\.)|[^/]+\.(pem|key|p12|pfx|tfstate|kurt-token|env)$)'
    if service == "openclaw":
        names = names.replace(r"auth-profiles\.json$|", "")
    # SBPL regex literals use ordinary backslashes, unlike Scheme string literals.
    restrictions = '' if service else '(deny network*)\n(deny appleevent-send)\n(deny mach-lookup)\n(deny process-info*)\n'
    if service == 'git':
        restrictions = '(deny network*)\n(deny appleevent-send)\n(deny file-write*)\n(allow file-write* (literal "/dev/null"))\n'
    if workspace is not None and not service:
        paths = {str(Path(workspace).resolve()), str(Path(tempfile.gettempdir()).resolve()), "/private/tmp", "/tmp"}
        restrictions += "(deny file-write*)\n(allow file-write* " + " ".join("(subpath " + json.dumps(p) + ")" for p in sorted(paths)) + ")\n"
    return '(version 1)\n(allow default)\n' + restrictions + '(deny file-read* file-write*\n' + filters + '\n(regex #"' + names + '"))\n'


def restricted_argv(command, *, shell=False, cwd=None):
    if platform.system() != 'Darwin' or not shutil.which('sandbox-exec'):
        raise RuntimeError('Generated code requires an OS sandbox; execution is disabled on this host.')
    if shell:
        if not isinstance(command, str): raise TypeError('A shell command must be a string.')
        argv=['/bin/sh','-c',command]
    else:
        if not isinstance(command,(list,tuple)) or not all(isinstance(a,str) for a in command):
            raise TypeError('An argument list is required.')
        argv=list(command)
    root=active_workspace() or Path(cwd or Path.cwd()).resolve()
    return ['/usr/bin/sandbox-exec','-p',sandbox_profile(workspace=root),*argv]


def restricted_run(command, *, shell=False, **kwargs):
    if 'env' in kwargs:
        raise ValueError('Restricted commands cannot supply a custom environment.')
    argv=restricted_argv(command,shell=shell,cwd=kwargs.get('cwd'))
    kwargs.setdefault('cwd',str(current_workspace()))
    kwargs['env']=child_env()
    kwargs.setdefault('start_new_session',True)
    return subprocess.run(argv,**kwargs)


def service_argv(argv, service):
    """Third-party tools get network access but cannot directly read Kurt's vault.

    Desktop/IPC capabilities remain trusted; this is not a separate OS identity.
    Explicit environment grants authenticate the intended service.
    """
    if platform.system() != 'Darwin' or not shutil.which('sandbox-exec'):
        raise RuntimeError('External service execution requires the supported OS sandbox on this host.')
    return ['/usr/bin/sandbox-exec', '-p', sandbox_profile(service=service), *argv]
