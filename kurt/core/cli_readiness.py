"""Explicit CLI diagnostics: installed/version checks are separate from model tests."""
from kurt.core.execution_preferences import DEFAULT_CLIS
from kurt.utils.security import child_env, redact
from kurt.utils.process import run_bounded
from kurt.utils.workspace import current_workspace


def probe_default_cli(name):
    if name not in DEFAULT_CLIS or name == 'auto':
        raise ValueError('Choose codex, claude, gemini, openclaw or vibe.')
    from kurt.core.cli_orchestrator import _resolve_cmd, run_ai_cli
    from kurt.core import codex_adapter, cli_tools
    binary = None
    try:
        if name == 'codex':
            binary = codex_adapter.executable()
            if not binary: raise FileNotFoundError('Codex CLI not installed.')
            result = run_bounded([binary, '--version'], env=child_env(), cwd=str(current_workspace()), timeout=20, max_output=8192)
        elif name == 'openclaw':
            binary = cli_tools.resolve_cli(name)
            if not binary: raise FileNotFoundError('OpenClaw CLI not installed.')
            from dataclasses import asdict
            result = asdict(cli_tools.run_cli(name, ['--version'], timeout=20))
        else:
            binary = _resolve_cmd(name)
            result = run_ai_cli(binary, ['--version'])
        return {'cli': name, 'installed': True, 'executable': binary,
                'executable_check': result['status'], 'version': redact(result.get('stdout', '')).strip()[:300],
                'exit_code': result.get('exit_code'),
                'error': redact(result.get('stderr', ''))[-1200:] if result['status'] != 'completed' else '',
                'warnings': redact(result.get('stderr', ''))[-1200:] if result['status'] == 'completed' else '',
                'authentication': 'Not tested by this version-only probe; no paid model request submitted.'}
    except (OSError, ValueError, RuntimeError) as exc:
        return {'cli': name, 'installed': bool(binary), 'executable_check': 'failed', 'error': redact(str(exc))}


def test_default_cli(name):
    if name not in DEFAULT_CLIS or name == 'auto': raise ValueError('Choose a supported CLI name.')
    from kurt.utils.env_loader import load_env
    load_env()
    from kurt.core.execution_preferences import run_default_cli
    marker = 'KURT_'+name.upper()+'_READY'
    try:
        answer = run_default_cli(name, [{'role': 'system', 'content': 'Read-only CLI connection test. Do not use tools, change files or delegate.'},
                                        {'role': 'user', 'content': 'Reply exactly '+marker+'. Do not use tools.'}])
        matched = answer.strip() == marker
        return {'cli': name, 'status': 'verified' if matched else 'unverified_reply', 'expected_reply': matched,
                'model_request_submitted': True, 'note': 'Verified for this request only; login, credits and provider availability can change.'}
    except Exception as exc:
        return {'cli': name, 'status': 'failed', 'error': redact(str(exc))[-2400:],
                'note': 'No alternate CLI or model was selected; the task was not replayed.'}


def probe_clis(target='all'):
    names = [n for n in DEFAULT_CLIS if n != 'auto'] if target == 'all' else [target]
    return [probe_default_cli(n) for n in names]


def register_commands(group):
    import json
    import typer
    @group.command('probe')
    def probe(target: str = typer.Argument('all')):
        """Check AI CLI executables/versions; no model inference or paid request."""
        try: result = probe_clis(target)
        except ValueError as exc: raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2))
    @group.command('test')
    def test(target: str):
        """Run one minimal read-only model response test; may consume provider credits."""
        try: result = test_default_cli(target)
        except ValueError as exc: raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2))
        if result['status'] != 'verified': raise typer.Exit(1)
