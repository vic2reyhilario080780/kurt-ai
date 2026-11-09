"""Restricted runner for generated code and shell commands.

On macOS, Seatbelt enforces credential-file/IPC/network restrictions for the
process and its children — kernel-level, so it cannot be bypassed by however
the child process ends up referencing a path.

Windows has no kernel primitive wired up yet that plays the same role (the
real equivalent, AppContainer sandboxing, needs direct Win32 API calls this
project doesn't have test coverage for). Instead, _windows_guard_violation()
does a lexical pre-flight scan of the command against the same protected-path
list: if it textually references a protected directory or credential-looking
filename, the command is refused before it ever runs. This is real
protection against the straightforward case, but it is strictly weaker than
Seatbelt — a command that builds a sensitive path indirectly (e.g. by
concatenating pieces at runtime inside a script Kurt launches) is not caught.
Treat it as a deterrent, not an equivalent guarantee.

Unsupported hosts (or any guard violation) fail closed rather than silently
running generated code with full account access. Trusted service adapters
have separate, explicit credential grants and are not routed through this
runner.
"""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
from kurt.utils.workspace import current_workspace, active_workspace

from kurt.utils.security import child_env


def _protected_paths(service=None):
    """Sensitive directories and credential-filename pattern, shared by the
    macOS Seatbelt profile and the Windows lexical guard."""
    roots = [Path.home()/name for name in ('.kurt', '.kurt-saas', '.aws', '.ssh', '.gnupg', '.config', '.claude', '.codex', '.gemini', '.openclaw', '.kube', '.docker', '.azure', 'Library')]
    if service:
        # Service adapters keep only their own login/state directories usable.
        own = {"openclaw": ".openclaw", "claude": ".claude", "gemini": ".gemini"}.get(service)
        roots = [p for p in roots if p.name not in {own, "Library"}]
    if service != "openclaw":
        roots.append(Path(__file__).resolve().parents[2]/'.openclaw-kurt')
    names = r'(^|/)(\.env($|[./])|\.npmrc$|\.pypirc$|\.netrc$|\.git-credentials$|credentials(\.json)?$|secrets\.(json|yaml|yml)$|control\.db$|auth-profiles\.json$|id_(rsa|ed25519|ecdsa)($|\.)|[^/]+\.(pem|key|p12|pfx|tfstate|kurt-token|env)$)'
    if service == "openclaw":
        names = names.replace(r"auth-profiles\.json$|", "")
    return roots, names


def sandbox_profile(*, service=None, workspace=None):
    # Deny rules apply to descendants as well, including symlink-resolved reads.
    roots, names = _protected_paths(service=service)
    if service and service != "claude":
        roots.append(Path.home()/"Library/Keychains")
        # claude is exempted: Claude Code's own OAuth/Pro login is stored in
        # the macOS Keychain, not a plain file under ~/.claude — blocking
        # Keychain reads broke /claude entirely ("Not logged in" even when
        # actually logged in). Verified via a direct before/after sandboxed
        # run: identical profile minus this one path fixes it, nothing else
        # needed. gemini/openclaw are untouched — no evidence they need this.
    filters = '\n'.join('(subpath ' + json.dumps(str(p.resolve())) + ')' for p in roots)
    # SBPL regex literals use ordinary backslashes, unlike Scheme string literals.
    restrictions = '' if service else '(deny network*)\n(deny appleevent-send)\n(deny mach-lookup)\n(deny process-info*)\n'
    if service == 'git':
        restrictions = '(deny network*)\n(deny appleevent-send)\n(deny file-write*)\n(allow file-write* (literal "/dev/null"))\n'
    if workspace is not None and not service:
        paths = {str(Path(workspace).resolve()), str(Path(tempfile.gettempdir()).resolve()), "/private/tmp", "/tmp"}
        restrictions += "(deny file-write*)\n(allow file-write* " + " ".join("(subpath " + json.dumps(p) + ")" for p in sorted(paths)) + ")\n"
    return '(version 1)\n(allow default)\n' + restrictions + '(deny file-read* file-write*\n' + filters + '\n(regex #"' + names + '"))\n'


def _windows_guard_violation(command, *, service=None):
    """Return a human-readable reason if `command` textually references a
    protected path or credential-looking filename, else None. See module
    docstring for why this is a lexical check rather than kernel enforcement."""
    text = command if isinstance(command, str) else ' '.join(command)
    text_norm = text.replace('\\', '/').lower()
    roots, names = _protected_paths(service=service)
    for p in roots:
        if str(p).replace('\\', '/').lower() in text_norm:
            return str(p)
    # names is written with '/' separators (shared with the macOS SBPL regex);
    # match against the backslash-normalized text so Windows-style paths count too.
    if re.search(names, text_norm):
        return 'a credential-looking filename'
    return None


def restricted_argv(command, *, shell=False, cwd=None):
    if shell:
        if not isinstance(command, str): raise TypeError('A shell command must be a string.')
    else:
        if not isinstance(command,(list,tuple)) or not all(isinstance(a,str) for a in command):
            raise TypeError('An argument list is required.')

    system = platform.system()
    if system == 'Darwin':
        if not shutil.which('sandbox-exec'):
            raise RuntimeError('Generated code requires an OS sandbox; execution is disabled on this host.')
        argv = ['/bin/sh','-c',command] if shell else list(command)
        root=active_workspace() or Path(cwd or Path.cwd()).resolve()
        return ['/usr/bin/sandbox-exec','-p',sandbox_profile(workspace=root),*argv]

    if system == 'Windows':
        violation = _windows_guard_violation(command)
        if violation:
            raise RuntimeError(f'Refused: command references a protected path ({violation}).')
        return ['cmd', '/c', command] if shell else list(command)

    raise RuntimeError('Generated code requires an OS sandbox; execution is disabled on this host.')


def restricted_run(command, *, shell=False, **kwargs):
    if 'env' in kwargs:
        raise ValueError('Restricted commands cannot supply a custom environment.')
    argv=restricted_argv(command,shell=shell,cwd=kwargs.get('cwd'))
    kwargs.setdefault('cwd',str(current_workspace()))
    kwargs['env']=child_env()
    if platform.system() == 'Windows':
        kwargs.setdefault('creationflags', getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
    else:
        kwargs.setdefault('start_new_session',True)
    return subprocess.run(argv,**kwargs)


def service_argv(argv, service):
    """Third-party tools get network access but cannot directly read Kurt's vault.

    Desktop/IPC capabilities remain trusted; this is not a separate OS identity.
    Explicit environment grants authenticate the intended service.
    """
    system = platform.system()
    if system == 'Darwin':
        if not shutil.which('sandbox-exec'):
            raise RuntimeError('External service execution requires the supported OS sandbox on this host.')
        return ['/usr/bin/sandbox-exec', '-p', sandbox_profile(service=service), *argv]

    if system == 'Windows':
        violation = _windows_guard_violation(argv, service=service)
        if violation:
            raise RuntimeError(f'Refused: command references a protected path ({violation}).')
        return list(argv)

    raise RuntimeError('External service execution requires the supported OS sandbox on this host.')
