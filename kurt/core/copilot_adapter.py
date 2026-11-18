"""Bounded, read-only GitHub Copilot CLI delegation; no automatic replay."""
import json
from pathlib import Path
import tempfile

from kurt.utils.execution import service_argv
from kurt.utils.process import run_bounded
from kurt.utils.security import redact
from kurt.utils.workspace import current_workspace


def final_reply(output):
    """Require a completed JSONL session, rather than accepting partial text."""
    messages = []
    completed = False
    for line in output.splitlines():
        event = json.loads(line)
        if not isinstance(event, dict): raise ValueError('Invalid Copilot event.')
        kind, data = event.get('type'), event.get('data', {})
        if not isinstance(data, dict): raise ValueError('Invalid Copilot event data.')
        if kind in ('session.error', 'error'):
            raise ValueError(str(data.get('message') or data.get('error') or 'Copilot session failed.'))
        if kind == 'assistant.message':
            if not data.get('toolRequests') and isinstance(data.get('content'), str):
                messages.append(data['content'])
        if kind == 'tool.execution_complete' and data.get('success') is False:
            raise ValueError('Copilot tool request failed or was denied; completion is unverified.')
        if kind == 'result':
            if event.get('exitCode') != 0: raise ValueError('Copilot session did not complete successfully.')
            completed = True
    if not completed or not messages or not messages[-1].strip():
        raise ValueError('Copilot returned no completed final answer; completion is unverified.')
    return messages[-1].strip()


def run_copilot(prompt=None, *, probe=False):
    from kurt.billing.client import active, CLI_CONTEXT, cli_session
    if active() and not probe and CLI_CONTEXT.get() is None:
        with cli_session('copilot'):
            return run_copilot(prompt, probe=probe)
    from kurt.core.cli_orchestrator import _resolve_cmd, _ai_cli_env
    binary = _resolve_cmd('copilot')
    env = _ai_cli_env(binary)
    if not probe and (not isinstance(prompt, str) or not prompt.strip()):
        raise ValueError('Provide a nonempty Copilot task.')
    with tempfile.TemporaryDirectory(prefix='kurt-copilot-') as folder:
        root = Path(folder).resolve()
        env.update({'COPILOT_AUTO_UPDATE':'false', 'NO_COLOR':'1', 'TERM':'dumb'})
        # Keep the existing account usable in direct mode. All generated logs
        # and CLI session state are restricted to its own home and runtime.
        home = Path(env.get('COPILOT_HOME', str(Path.home()/'.copilot'))).resolve()
        writable = [root, home, Path(env.get('HOME', str(Path.home())))/'Library/Caches/copilot']
        context = CLI_CONTEXT.get()
        if context is not None: writable.append(context['root'])
        if probe:
            argv = [binary, '--version']
        else:
            argv = [binary, '-p', prompt, '--output-format', 'json', '--no-auto-update',
                    '--no-ask-user', '--no-custom-instructions', '--no-bash-env',
                    '--disable-client-telemetry', '--sync-session=off', '--disable-builtin-mcps',
                    '--disable-mcp-server=computer-use', '--available-tools=view,glob,grep',
                    '--allow-tool=read', '--deny-tool=shell', '--deny-tool=write',
                    '--log-dir', str(root/'logs'), '--stream', 'off']
        result = run_bounded(service_argv(argv, 'copilot', write_paths=writable), env=env,
                             cwd=str(current_workspace()), timeout=30 if probe else 120,
                             max_output=65536)
        for field in ('stdout', 'stderr'):
            value = result.get(field, '')
            for key in ('COPILOT_PROVIDER_API_KEY', 'COPILOT_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'):
                if env.get(key): value = value.replace(env[key], '[REDACTED]')
            result[field] = redact(value)
        result.update({'tool':'copilot', 'filesystem_read_only':True})
        if probe: return result
        if result['status'] == 'completed':
            try: result['final_text'] = redact(final_reply(result['stdout']))
            except (ValueError, TypeError) as exc:
                result.update({'status':'failed', 'stderr':redact(str(exc))})
        if result['status'] != 'completed':
            result['stderr'] += ('\nCopilot: check /cli probe copilot. For GitHub login run '
                'node_modules/.bin/copilot login; in wallet mode check /wallet catalog and credits. '
                'Only file viewing/search is enabled in this headless adapter. Kurt did not replay the task.')
        return result
