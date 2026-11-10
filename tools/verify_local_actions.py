"""Opt-in real chat tests: native apps, unread Mail counts, Music and download."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import threading
import time

from kurt.core.cli_tools import run_cli
from kurt.core.local_actions import mail_status, music_status, _native_action
from kurt.utils.security import redact


def start_chat(prompt):
    process = subprocess.Popen([shutil.which('kurt'), 'chat', '--no-memory', '--model', 'offline/local-smoke'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process.stdin.write((prompt + '\n').encode())
    process.stdin.flush()
    output = bytearray()
    deadline = time.monotonic() + 90
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while output.decode(errors='replace').count('You ›') < 2:
            if time.monotonic() > deadline:
                process.kill()
                process.communicate()
                raise RuntimeError('Chat timed out before returning to its input prompt.')
            for key, _ in selector.select(.25):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if chunk:
                    output.extend(chunk)
            if process.poll() is not None:
                break
    return process, redact(output.decode(errors='replace'))


def finish_chat(process):
    if process.poll() is None:
        process.stdin.write(b'exit\n')
        process.stdin.flush()
    output, _ = process.communicate(timeout=15)
    return redact(output.decode(errors='replace'))


def verify():
    root = Path(tempfile.mkdtemp(prefix='kurt-local-actions-'))
    payload = b'KURT_SYNTHETIC_DOWNLOAD_OK\n'
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/sample.txt':
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rows = []
    try:
        for prompt, app in [('buksan mo nga yung Calculator', 'Calculator'), ('Can you open TextEdit?', 'TextEdit')]:
            print(f'Testing chat: {prompt}', flush=True)
            process, transcript = start_chat(prompt)
            observation = run_cli('peekaboo', ['see', '--app', app, '--json'], timeout=30)
            for _ in range(2):
                if observation.status == 'completed' and (observation.data or {}).get('target_receipt', {}).get('window_id'):
                    break
                time.sleep(.2)
                observation = run_cli('peekaboo', ['see', '--app', app, '--json'], timeout=30)
            data = (observation.data or {}).get('data') or {}
            verified = (f'Nabuksan at na-verify ang {app}' in transcript and observation.status == 'completed'
                        and bool((observation.data or {}).get('target_receipt', {}).get('window_id')))
            transcript += finish_chat(process)
            rows.append({'kind': 'open_app', 'app': app, 'prompt': prompt,
                         'status': 'passed' if verified else 'failed', 'window': data.get('window_title'), 'transcript': transcript})
            print(f'{app}: {rows[-1]["status"]}', flush=True)

        prompt = 'i-check mo ang email ko'
        print(f'Testing chat: {prompt}', flush=True)
        process, transcript = start_chat(prompt)
        mail = mail_status()
        passed = mail['accounts'] > 0 and f'{mail["unread"]} unread email' in transcript
        transcript += finish_chat(process)
        rows.append({'kind': 'check_mail', 'prompt': prompt, 'status': 'passed' if passed else 'failed',
                     'verification': 'Read-only account/unread counts; no message bodies read or read flags changed.',
                     'observed': mail, 'transcript': transcript})
        print(f'Mail: {rows[-1]["status"]}', flush=True)

        initial = music_status()
        try:
            prompt = 'magpatugtog ka ng musika'
            print(f'Testing chat: {prompt}', flush=True)
            process, transcript = start_chat(prompt)
            music = music_status()
            passed = music['player_state'] == 'playing' and 'na-verify ang player state' in transcript
            transcript += finish_chat(process)
            rows.append({'kind': 'play_music', 'prompt': prompt, 'status': 'passed' if passed else 'failed',
                         'observed_state': music['player_state'], 'transcript': transcript})
            print(f'Music: {rows[-1]["status"]}', flush=True)
        finally:
            # A playback test should not leave music playing if it was inactive.
            if initial['player_state'] != 'playing':
                _native_action('pause_music')

        target = root / 'downloaded.txt'
        url = f'http://127.0.0.1:{server.server_port}/sample.txt'
        prompt = f'i-download mo ang {url} sa "{target}"'
        print('Testing chat: explicit download URL and destination', flush=True)
        process, transcript = start_chat(prompt)
        content = target.read_bytes() if target.exists() else b''
        passed = content == payload and 'Na-download at na-verify' in transcript
        transcript += finish_chat(process)
        rows.append({'kind': 'download', 'prompt': prompt, 'status': 'passed' if passed else 'failed',
                     'file': str(target), 'sha256': hashlib.sha256(content).hexdigest(), 'transcript': transcript})
        print(f'Download: {rows[-1]["status"]}', flush=True)

        process, transcript = start_chat(prompt)
        unchanged = target.read_bytes() == payload
        refused = 'already exists' in transcript
        transcript += finish_chat(process)
        rows.append({'kind': 'download_no_overwrite', 'status': 'passed' if unchanged and refused else 'failed',
                     'transcript': transcript})
        process, transcript = start_chat('i-download mo ito')
        clarified = 'Ibigay ang direct HTTP(S) download link' in transcript
        transcript += finish_chat(process)
        rows.append({'kind': 'download_missing_source', 'status': 'passed' if clarified else 'failed', 'transcript': transcript})
    finally:
        server.shutdown()
        server.server_close()
    return {'tested_at': datetime.now(timezone.utc).isoformat(),
            'entrypoint': 'installed kurt chat --no-memory --model offline/local-smoke',
            'status': 'passed' if all(row['status'] == 'passed' for row in rows) else 'failed',
            'scope': 'Calculator/TextEdit; Apple Mail unread counts; existing Music playback; synthetic local HTTP download.',
            'results': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to open native apps, read Mail counts, briefly play Music and download a synthetic file.')
    report = verify()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'passed' else 1)
