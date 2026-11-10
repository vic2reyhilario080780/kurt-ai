"""Live implicit-goal and contextual follow-up checks through actual Kurt chat."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

from kurt.utils.security import redact


class TurnFailed(RuntimeError):
    def __init__(self, transcript):
        super().__init__('Semantic chat did not return to its input prompt.')
        self.transcript = transcript


def turn(process, prompt, first=False):
    process.stdin.write((prompt + '\n').encode())
    process.stdin.flush()
    captured = bytearray()
    deadline = time.monotonic() + 150
    lines_printed = 0
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while captured.decode(errors='replace').count('You ›') < (2 if first else 1):
            if time.monotonic() > deadline or process.poll() is not None:
                raise TurnFailed(redact(captured.decode(errors='replace')))
            for key, _ in selector.select(.25):
                captured.extend(os.read(key.fileobj.fileno(), 8192))
                lines = [line for line in captured.decode(errors='replace').splitlines()
                         if line.startswith(('Desktop ', 'Tool ')) or '🔧 ' in line]
                for line in lines[lines_printed:]:
                    print(line, flush=True)
                lines_printed = len(lines)
    return redact(captured.decode(errors='replace'))


def verify(model):
    process = subprocess.Popen(['/opt/homebrew/bin/kurt', 'chat', '--no-memory', '--model', model],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    cases = [
        ('May kukuwentahin akong simpleng arithmetic. Ihanda mo sa harap ko ang built-in na pang-compute ng iMac. App lang muna, wala pang ita-type.', 'Calculator', True),
        ('May susulatin akong plain text. Ihanda mo naman ang built-in plain-text editor dito sa Mac. App lang muna, huwag mag-save o gumawa ng file.', 'TextEdit', True),
        ('Balik tayo sa una mong inihanda para sa akin; iyon ulit ang gusto kong nasa harap.', 'Calculator', True),
        ('Tanong lang: ano ang pagkakaiba ng Notes at plain-text editor? Huwag kang gumalaw ng app para dito.', None, False),
    ]
    rows = []
    try:
        for i, (prompt, expected, mutate) in enumerate(cases):
            print(f'Case {i + 1}: {prompt}', flush=True)
            try:
                transcript = turn(process, prompt, first=i == 0)
            except TurnFailed as exc:
                rows.append({'prompt': prompt, 'passed': False, 'error': str(exc), 'transcript': exc.transcript})
                break
            observed = subprocess.run([sys.executable, str(Path(__file__).with_name('verify_app_opening.py')), '--observe'],
                capture_output=True, text=True, check=True, timeout=15)
            foreground = json.loads(observed.stdout)
            tools = [line.split('🔧 ', 1)[1].strip() for line in transcript.splitlines() if '🔧 ' in line]
            read_only = {'list_apps', 'observe_application', 'search_web', 'read_webpage',
                         'desktop_cli_status', 'search_native', 'inspect_native', 'inspect_native_input'}
            # Other apps/user focus can change while answering. For a question,
            # assert no mutation tool was used, not that OS focus never changed.
            other_actions = {'fill_field', 'click_element', 'press_key', 'move_pointer', 'scroll_window',
                             'open_browser_url', 'desktop_cli', 'desktop_action', 'download_url', 'generate_media'}
            passed = (foreground.get('app') == expected and 'Desktop open_application: completed' in transcript
                      and not other_actions.intersection(tools)) if mutate else set(tools) <= read_only
            rows.append({'prompt': prompt, 'expected_app': expected, 'tools': tools,
                         'foreground': foreground, 'passed': passed, 'transcript': transcript})
            print(json.dumps({'passed': passed, 'foreground': foreground, 'tools': tools}), flush=True)
    finally:
        try:
            process.communicate(b'exit\n', timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=10)
    return {'tested_at': datetime.now(timezone.utc).isoformat(), 'model': model,
            'scope': 'Actual installed chat, implicit goals without app names, follow-up using session context with disk memory off, and question-only non-action; fresh independent foreground observations.',
            'passed': all(row['passed'] for row in rows), 'results': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--model', default='openai/gpt-oss-120b')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to run model calls and open/focus Calculator and TextEdit.')
    report = verify(args.model)
    Path(args.output).write_text(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
