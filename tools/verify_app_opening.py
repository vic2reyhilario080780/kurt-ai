"""Opt-in app opening checks through installed Kurt chat, with fresh foreground observations."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

from verify_local_actions import start_chat, finish_chat


def verify():
    rows = []
    cases = [('buksan mo yung app na Calculator', 'Calculator'),
             ('mag open ka ng TextEdit', 'TextEdit'),
             ('buksan mo ang Notes sa imac ko', 'Notes'),
             ('open the Calculator app', 'Calculator'),
             ('paki bukas ng TextEdit', 'TextEdit'),
             ('buksan mo ang Notes', 'Notes')]
    process = None
    try:
        for prompt, expected in cases:
            print(f'Testing: {prompt}', flush=True)
            if process is None:
                process, transcript = start_chat(prompt)
            else:
                process.stdin.write((prompt + '\n').encode())
                process.stdin.flush()
                output = bytearray()
                deadline = time.monotonic() + 45
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while 'You ›' not in output.decode(errors='replace'):
                        if time.monotonic() > deadline or process.poll() is not None:
                            raise RuntimeError('Persistent chat did not finish the app-opening request.')
                        for key, _ in selector.select(.25):
                            output.extend(os.read(key.fileobj.fileno(), 8192))
                transcript = output.decode(errors='replace')
            observed = subprocess.run([sys.executable, __file__, '--observe'],
                                      capture_output=True, text=True, timeout=15, check=True)
            foreground = json.loads(observed.stdout)
            passed = foreground.get('app') == expected and f'Nabuksan at na-verify ang {expected}' in transcript
            rows.append({'prompt': prompt, 'expected_app': expected, 'foreground': foreground,
                         'passed': passed, 'transcript': transcript})
            print(f'{expected}: {"passed" if passed else "FAILED"}', flush=True)
    finally:
        if process is not None:
            finish_chat(process)
    return {'tested_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'One persistent installed kurt chat with invalid AI model; independent fresh-process foreground observation after each app switch; no screen/AX inspection.',
            'passed': all(row['passed'] for row in rows), 'results': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--observe', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.observe:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        print(json.dumps({'app': str(app.localizedName()), 'pid': int(app.processIdentifier())} if app else {}))
    else:
        if not args.live or not args.output:
            parser.error('Use --live --output REPORT.json to open/focus Calculator, TextEdit and Notes.')
        report = verify()
        Path(args.output).write_text(json.dumps(report, indent=2))
        raise SystemExit(0 if report['passed'] else 1)
