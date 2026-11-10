"""Opt-in browser-opening smoke test through the installed Kurt chat command."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import sys
import os
import selectors
import time

from kurt.core.browser_intent import default_browser
from kurt.core.cli_tools import run_cli
from kurt.core.desktop_actions import observation_flags
from kurt.utils.security import redact


def verify():
    executable = shutil.which('kurt')
    if not executable:
        raise RuntimeError('The installed kurt entrypoint is required for this test.')
    default = default_browser()
    if not default:
        raise RuntimeError('Cannot resolve the macOS default browser.')
    root = Path(tempfile.mkdtemp(prefix='kurt-chat-browser-'))
    cases = [
        ('magbukas ka ng browser', default, False),
        ('Can you open a browser?', default, False),
        ('buksan mo nga yung Chrome', 'Google Chrome', False),
        ('please open Microsoft Edge', 'Microsoft Edge', False),
        ('paki open naman ng Safari', 'Safari', False),
    ]
    for browser, wording in [
        ('Google Chrome', 'Kurt, buksan mo nga yung Chrome sa {url}'),
        ('Microsoft Edge', 'Could you please open the Microsoft Edge browser to {url}'),
        ('Safari', 'magbukas ka ng Safari at pumunta sa {url}'),
    ]:
        title = 'Kurt Chat Browser ' + uuid.uuid4().hex[:8]
        page = root / (title.replace(' ', '-') + '.html')
        page.write_text(f'<!doctype html><title>{title}</title><h1>{title}</h1>Local chat-mode browser test.')
        cases.append((wording.format(url=page.as_uri()), browser, title))
    results = []
    for index, (prompt, browser, title) in enumerate(cases):
        print(f'Testing actual chat: {prompt}', flush=True)
        # Keep the real chat alive at its next input prompt while observing the
        # desktop. Exiting the GUI-launched process first can restore Code focus.
        process = subprocess.Popen([executable, 'chat', '--no-memory', '--model', 'offline/browser-smoke'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.stdin.write((prompt + '\n').encode())
        process.stdin.flush()
        captured = bytearray()
        deadline = time.monotonic() + 90
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while captured.decode(errors='replace').count('You ›') < 2:
                if time.monotonic() >= deadline:
                    process.kill()
                    raise RuntimeError('Kurt chat did not return to its input prompt within 90 seconds.')
                for key, _ in selector.select(0.25):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        break
                    captured.extend(chunk)
                if process.poll() is not None:
                    break
        transcript = redact(captured.decode(errors='replace'))
        screenshot = root / f'result-{index}.png'
        target = []
        if title:
            inventory = run_cli('peekaboo', ['window', 'list', '--app', browser, '--json',
                                            *(['--no-remote'] if browser != 'Safari' else [])], timeout=30)
            windows = ((inventory.data or {}).get('data') or {}).get('windows', [])
            matches = [w for w in windows if title in w.get('window_title', '') and w.get('window_id')]
            if len(matches) == 1:
                target = ['--window-id', str(matches[0]['window_id'])]
        receipt = run_cli('peekaboo', ['see', '--app', browser, *target, '--path', str(screenshot),
                                     '--json', *observation_flags(browser)], timeout=30)
        payload = receipt.data or {}
        observed = payload.get('data') or {}
        window_id = (payload.get('target_receipt') or {}).get('window_id')
        # NSWorkspace's singleton caches activation notifications while this
        # parent is blocked in subprocess.run. Query from a fresh process.
        active = subprocess.run([sys.executable, '-c',
            'from AppKit import NSWorkspace; print(NSWorkspace.sharedWorkspace().frontmostApplication().localizedName())'],
            capture_output=True, text=True, timeout=10)
        foreground = active.stdout.strip()
        passed = (process.poll() is None and f'Nabuksan at na-verify ang {browser}' in transcript
                  and receipt.status == 'completed' and bool(window_id) and foreground == browser
                  and (not title or title in (observed.get('window_title') or '')))
        if process.poll() is None:
            process.stdin.write(b'exit\n')
            process.stdin.flush()
        remaining, _ = process.communicate(timeout=15)
        transcript += redact(remaining.decode(errors='replace'))
        results.append({'prompt': prompt, 'browser': browser, 'status': 'passed' if passed else 'failed',
                        'cli_exit_code': process.returncode, 'observed_window': observed.get('window_title'),
                        'window_id': window_id, 'foreground_app': foreground, 'screenshot': str(screenshot),
                        'transcript': transcript})
        print(f'{browser}: {results[-1]["status"]}', flush=True)
    return {'tested_at': datetime.now(timezone.utc).isoformat(), 'entrypoint': executable,
            'mode': 'actual installed kurt chat --no-memory with a deliberately invalid model selection',
            'verification': 'Independent window, foreground app, and unique page title checks; no model replies mocked.',
            'status': 'passed' if all(r['status'] == 'passed' for r in results) else 'failed', 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to open and focus installed browsers through real Kurt chat.')
    report = verify()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'passed' else 1)
