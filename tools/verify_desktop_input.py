"""Opt-in mouse/keyboard/scroll verification through actual natural-language chat."""
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
import uuid

from kurt.core.desktop_actions import observe, desktop_action
from kurt.utils.security import redact


def verify(browser, model='auto', direct=False, timeout=240):
    root = Path(tempfile.mkdtemp(prefix='kurt-input-'))
    token = 'INPUT_' + uuid.uuid4().hex[:8]
    title = 'Kurt Input ' + token
    page = root / 'input.html'
    page.write_text('''<!doctype html><meta charset="utf-8"><title>TITLE</title>
<style>body{font:22px system-ui;height:4000px;padding:50px}section{position:fixed;top:20px;background:white;padding:30px}input,button{font:22px system-ui;padding:12px;margin:12px}output{display:block}</style>
<section><h1>Desktop input verification</h1>
<input aria-label="Test message"><button aria-label="Hover target">Hover target</button>
<output aria-live="polite">Waiting</output></section>
<script>let entered='',hovered=false,scrolled=false,hoverY=0;
function show(){document.querySelector('output').textContent='KEYBOARD:'+entered+' HOVER:'+hovered+' SCROLL:'+scrolled;document.title='TITLE '+(entered==='TOKEN'&&hovered&&scrolled?'INPUT_OK':'WAITING')}
document.querySelector('input').onkeydown=e=>{if(e.key==='Enter'){entered=e.target.value;show()}};
document.querySelector('button').onmouseenter=()=>{if(entered==='TOKEN'){hovered=true;hoverY=scrollY;scrolled=false;show()}};
onscroll=()=>{if(hovered){scrolled=scrollY>hoverY;show()}};</script>'''.replace('TITLE', title).replace('TOKEN', token))
    prompt = (f'Open {browser} at {page.as_uri()}. Fill "Test message" with "{token}". '
              'Press Return on the keyboard to submit it. Move the mouse onto "Hover target" without clicking. '
              'Scroll down in this browser window. Verify the page title says INPUT_OK and report the observed result. '
              'Do all steps yourself using desktop_action, and only interact with this local test page.')
    if direct:
        trace = []
        for action, options in [('open_url', {'url': page.as_uri()}),
                                ('fill', {'element': 'Test message', 'text': token}),
                                ('press', {'key': 'Return'}), ('move', {'element': 'Hover target'}),
                                ('scroll', {'direction': 'down', 'amount': 4})]:
            result = desktop_action(action, app=browser, **options)
            observation = result.get('observation', {})
            trace.append({**{k: v for k, v in result.items() if k != 'observation'},
                          'window_title': observation.get('window_title'),
                          'page_result': [e.get('value') for e in observation.get('elements', [])
                                          if str(e.get('label', '')).startswith('KEYBOARD:')]})
        final = observe(browser)
        return {'browser': browser, 'passed': 'INPUT_OK' in (final.get('window_title') or ''),
                'window_title': final.get('window_title'), 'trace': trace, 'fixture': str(page), 'mode': 'direct tools'}
    command = ['/opt/homebrew/bin/kurt', 'chat', '--no-memory']
    if model != 'auto':
        command += ['--model', model]
    process = subprocess.Popen(command,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    captured = bytearray()
    observed = {}
    error = None
    tool_count = 0
    status_count = 0
    try:
        process.stdin.write((prompt + '\n').encode())
        process.stdin.flush()
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while captured.decode(errors='replace').count('You ›') < 2:
                if time.monotonic() > deadline:
                    raise TimeoutError(f'Chat did not finish within {timeout} seconds')
                for ready, _ in selector.select(.25):
                    chunk = os.read(ready.fileobj.fileno(), 8192)
                    if chunk:
                        captured.extend(chunk)
                        count = captured.decode(errors='replace').count('🔧 desktop_action')
                        if count != tool_count:
                            tool_count = count
                            print(f'{browser}: {tool_count} desktop tool calls', flush=True)
                        statuses = [line for line in captured.decode(errors='replace').splitlines()
                                    if line.startswith(('Desktop ', 'Tool '))]
                        for status in statuses[status_count:]:
                            print(status, flush=True)
                        status_count = len(statuses)
                if process.poll() is not None:
                    break
        observed = observe(browser)
    except (OSError, TimeoutError) as exc:
        error = str(exc)
    finally:
        if process.poll() is None:
            try:
                process.communicate(b'exit\n', timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
    passed = observed.get('status') == 'completed' and title in (observed.get('window_title') or '') and 'INPUT_OK' in (observed.get('window_title') or '')
    return {'browser': browser, 'passed': passed, 'window_title': observed.get('window_title'),
            'error': error, 'transcript': redact(captured.decode(errors='replace')), 'fixture': str(page)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--browser', default='Safari')
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', default='auto')
    parser.add_argument('--direct', action='store_true', help='Check the tools without an AI planner')
    parser.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to control the browser with real mouse/keyboard input and AI requests.')
    result = verify(args.browser, args.model, args.direct, args.timeout)
    Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('browser', 'passed', 'window_title')}))
    raise SystemExit(0 if result['passed'] else 1)
