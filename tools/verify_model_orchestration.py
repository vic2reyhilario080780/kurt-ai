"""Opt-in live checks of Kurt's actual agent delegation tools."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import subprocess

from kurt.core.agent_loop import execute_tool
from kurt.core.cli_orchestrator import _cmd_exists, _resolve_cmd
from kurt.core.router import ModelRouter
from kurt.utils.env_loader import load_env
from kurt.utils.security import redact
from kurt.utils.workspace import workspace


def verify(names=None):
    load_env()
    router = ModelRouter()
    rows = []
    original = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='kurt-orchestration-') as folder:
        subprocess.run(['git', 'init', '-q', folder], check=True, capture_output=True)
        os.chdir(folder)
        try:
            with workspace(folder):
                for name in names or ('openrouter', 'fal', 'claude', 'gemini', 'codex'):
                    print(f'Testing {name} through Kurt...', flush=True)
                    marker = 'KURT_' + name.upper() + '_OK'
                    row = {'name': name, 'tested_at': datetime.now(timezone.utc).isoformat()}
                    try:
                        if name in ('openrouter', 'fal'):
                            row['configured'] = router._has_key(name)
                            if not row['configured']:
                                row['status'] = 'missing_key'
                                rows.append(row)
                                continue
                            row['tool'] = 'call_model'
                            row['model'] = 'openai/gpt-oss-120b' if name == 'openrouter' else 'fal-ai/flux/schnell'
                            prompt = f'Reply with exactly {marker}. No explanation.' if name == 'openrouter' else 'A plain blue circle on a white background. No text.'
                            output = execute_tool('call_model', {'provider': name, 'model': row['model'], 'prompt': prompt})
                            passed = output.strip() == marker if name == 'openrouter' else output.strip().startswith('https://')
                        else:
                            row['tool'] = 'delegate_cli'
                            row['installed'] = _cmd_exists(name)
                            row['executable'] = _resolve_cmd(name) if row['installed'] else None
                            if not row['installed']:
                                row['status'] = 'missing'
                                rows.append(row)
                                continue
                            previous_trust = os.environ.get('GEMINI_CLI_TRUST_WORKSPACE')
                            try:
                                if name == 'gemini':
                                    # Trust only this known, empty synthetic repository for
                                    # this child process. Do not alter saved trusted folders.
                                    os.environ['GEMINI_CLI_TRUST_WORKSPACE'] = 'true'
                                    row['workspace_trust'] = 'Disposable synthetic Git repository; process-scoped, no saved trust changes.'
                                output = execute_tool('delegate_cli', {'tool': name, 'prompt': f'Reply with exactly {marker}. Do not use tools, read files, or modify files.'})
                            finally:
                                if previous_trust is None:
                                    os.environ.pop('GEMINI_CLI_TRUST_WORKSPACE', None)
                                else:
                                    os.environ['GEMINI_CLI_TRUST_WORKSPACE'] = previous_trust
                            if name == 'codex':
                                value = json.loads(output)
                                passed = value.get('status') == 'completed' and value.get('final_text', '').strip() == marker
                            else:
                                passed = output.strip() == marker
                        row.update(status='passed' if passed else 'failed', output=redact(output)[:18000])
                    except Exception as exc:
                        row.update(status='failed', error=redact(str(exc)))
                    rows.append(row)
                    print(f'{name}: {row["status"]}', flush=True)
        finally:
            os.chdir(original)
    return {'tested_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'Individual live provider/CLI calls through real Kurt agent tools; not an autonomous five-service planning run.',
            'status': 'passed' if all(row['status'] == 'passed' for row in rows) else 'partial',
            'results': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--only', nargs='+', choices=['openrouter', 'fal', 'claude', 'gemini', 'codex'])
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to use configured provider credits, CLI quotas and one fal image generation.')
    report = verify(args.only)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
