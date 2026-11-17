"""Actual installed CLIs against a local protocol fixture; no paid endpoint/key."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

from kurt.core import deepseek_adapter as adapter, cli_orchestrator as cli
from kurt.utils.security import child_env
from kurt.utils.workspace import workspace


def verify():
    requests, state = [], {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['content-length'])))
            requests.append({'model': body.get('model'), 'thinking': body.get('thinking'),
                             'key_matches': self.headers.get('authorization') == 'Bearer fixture-only',
                             'tool_reply_present': any(m.get('role') == 'tool' for m in body['messages'])})
            if not requests[-1]['tool_reply_present']:
                tool = 'read_file' if state['scenario'] == 'read' else 'run_shell'
                arguments = {'path': 'notes.txt'} if tool == 'read_file' else {'command': 'printf changed > notes.txt'}
                message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'fixture-call', 'type': 'function', 'function': {'name': tool, 'arguments': json.dumps(arguments)}}]}
            elif state['name'] == 'deepseek-cli':
                message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'fixture-finish', 'type': 'function', 'function': {'name': 'finish', 'arguments': json.dumps({'summary': 'DEEPSEEK_FIXTURE_OK'})}}]}
            else:
                message = {'role': 'assistant', 'content': 'DEEPSEEK_FIXTURE_OK'}
            data = json.dumps({'id': 'fixture', 'object': 'chat.completion', 'created': 0, 'model': adapter.MODEL,
                'choices': [{'index': 0, 'message': message, 'finish_reason': 'tool_calls' if message.get('tool_calls') else 'stop'}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode()
            self.send_response(200); self.send_header('content-type', 'application/json'); self.send_header('content-length', str(len(data))); self.end_headers(); self.wfile.write(data)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix='kurt-deepseek-fixture-') as folder, workspace(folder):
            root = Path(folder); note = root/'notes.txt'; note.write_text('original')
            def env(binary):
                return child_env(extra={'DEEPSEEK_API_KEY': 'fixture-only', 'DEEPSEEK_BASE_URL': f'http://127.0.0.1:{server.server_port}/v1',
                                        'DEEPSEEK_MODEL': adapter.MODEL, 'TAVILY_API_KEY': 'not-configured'})
            for name in adapter.TOOLS:
                for scenario in ('read', 'blocked-write'):
                    state.update(name=name, scenario=scenario)
                    start = len(requests)
                    with patch.object(cli, '_ai_cli_env', side_effect=env):
                        result = adapter.run_deepseek(name, 'Run the synthetic fixture task only.')
                    checks = {'cli': name, 'scenario': scenario, 'status': result['status'],
                              'expected_reply': result.get('final_text') == 'DEEPSEEK_FIXTURE_OK',
                              'request_count': len(requests)-start, 'project_file_unchanged': note.read_text() == 'original',
                              'error': result.get('stderr', '')[-1000:] if result['status'] != 'completed' else ''}
                    results.append(checks)
        return {'results': results, 'requests': requests, 'paid_endpoint_used': False,
                'passed': all(r['status'] == 'completed' and r['expected_reply'] and r['request_count'] == 2 and r['project_file_unchanged'] for r in results)}
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    result = verify()
    if args.output: Path(args.output).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
