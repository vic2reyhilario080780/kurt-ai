"""Bounded adapters for the user's installed DeepSeek Agent and Terminal CLI."""
import json
from pathlib import Path
import re
import tempfile

from kurt.utils.execution import service_argv
from kurt.utils.process import run_bounded
from kurt.utils.security import redact
from kurt.utils.workspace import current_workspace

TOOLS = ('deepseek', 'deepseek-cli')
MODEL = 'deepseek-flash'
BASE_URL = 'https://api.deepseek.com'


def _clean(text):
    return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text).strip()


def _python_for(binary):
    first = Path(binary).resolve().read_text().splitlines()[0]
    interpreter = first[2:].strip() if first.startswith('#!') else ''
    if not interpreter or ' ' in interpreter or not Path(interpreter).is_absolute() or not Path(interpreter).is_file() or not Path(interpreter).name.startswith('python'):
        raise ValueError('DeepSeek Agent requires its installed Python console entry point; unsupported executable format.')
    return interpreter


def run_deepseek(name, prompt=None, *, probe=False):
    if name not in TOOLS: raise ValueError('Choose deepseek or deepseek-cli.')
    from kurt.billing.client import active, CLI_CONTEXT, cli_session
    if active() and not probe and CLI_CONTEXT.get() is None:
        with cli_session(name):
            return run_deepseek(name, prompt, probe=probe)
    from kurt.core.cli_orchestrator import _resolve_cmd, _ai_cli_env
    binary = _resolve_cmd(name)
    env = _ai_cli_env(binary)
    if not probe and not env.get('DEEPSEEK_API_KEY'):
        raise ValueError('Configure DEEPSEEK_API_KEY in Kurt /setup first. No DeepSeek request was sent.')
    if not probe and (not isinstance(prompt, str) or not prompt.strip()):
        raise ValueError('Provide a nonempty task.')
    with tempfile.TemporaryDirectory(prefix='kurt-deepseek-') as folder:
        root = Path(folder).resolve()
        # No reuse or modification of either community CLI's stored credentials.
        env.update({'HOME': str(root), 'CI': '1', 'NO_COLOR': '1', 'TERM': 'dumb', 'PYTHONDONTWRITEBYTECODE': '1'})
        transcript = root/'transcript.jsonl'
        if probe:
            argv, input_text = [binary, '--version'], None
        elif name == 'deepseek':
            argv = [_python_for(binary), str(Path(__file__).with_name('deepseek_worker.py')), str(transcript)]
            input_text = prompt
        else:
            argv = [binary, '--cwd', str(current_workspace()), '--max-steps', '8']
            input_text = prompt
        result = run_bounded(service_argv(argv, name, write_paths=[root]), env=env,
            cwd=str(current_workspace()), timeout=20 if probe else 120,
            input_text=input_text, max_output=65536)
        # Prevent accidental echo of either granted credential in upstream logs.
        for key in ('stdout', 'stderr'):
            value = result.get(key, '')
            for variable in ('DEEPSEEK_API_KEY', 'TAVILY_API_KEY'):
                if env.get(variable): value = value.replace(env[variable], '[REDACTED]')
            result[key] = redact(_clean(value))
        result.update({'tool': name, 'model': MODEL, 'filesystem_read_only': True})
        if probe: return result
        if result['status'] != 'completed':
            if name == 'deepseek':
                try:
                    detail = json.loads(result['stdout'])
                    result['stderr'] += '\n' + str(detail.get('reason', 'Agent failed.'))
                    result['provider_http_status'] = detail.get('provider_http_status')
                except ValueError:
                    pass
            return result
        try:
            if name == 'deepseek':
                data = json.loads(result['stdout'])
                if data.get('status') != 'completed': raise ValueError('Agent did not complete.')
                text = data.get('final_text', '').strip()
            else:
                output = result['stdout']
                if re.search(r'^max steps \(\d+\) reached$', output, re.M):
                    raise ValueError('DeepSeek CLI reached the tool-step limit; no verified final response.')
                lines = output.splitlines()
                summaries = [line[1:].strip() for line in lines if line.startswith('✓')]
                if '⏺' in output and not summaries:
                    raise ValueError('DeepSeek CLI tool workflow has no final summary; completion is unverified.')
                text = summaries[-1] if summaries else '\n'.join(lines[1:]).strip()
            if not text: raise ValueError('No final answer was returned.')
            result['final_text'] = text
        except (ValueError, TypeError, AttributeError) as exc:
            result.update({'status': 'failed', 'stderr': str(exc)})
        return result
