"""Verify installed CLI attachment bytes against a local HTTP fixture, no AI calls."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==')


def verify():
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            images = [m for m in data['messages'] if m.get('images')]
            received.append({'path': self.path, 'model': data['model'], 'image_count': len(images),
                             'bytes_match': bool(images) and base64.b64decode(images[0]['images'][0]) == PNG})
            body = json.dumps({'message': {'content': 'KURT_IMAGE_RECEIVED'}, 'done': True}).encode()+b'\n'
            self.send_response(200); self.send_header('Content-Type', 'application/x-ndjson'); self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='kurt-attachment-') as folder:
            image = Path(folder)/'Photos Library.photoslibrary/resources/derivatives/C/picture.png'
            image.parent.mkdir(parents=True); image.write_bytes(PNG)
            env = os.environ.copy(); env['OLLAMA_HOST'] = f'http://127.0.0.1:{server.server_port}'
            result = subprocess.run([shutil.which('kurt') or 'kurt', 'chat', '--no-memory', '--model', 'fixture-vision|ollama'],
                                    input=f"'{image}'\nexit\n", env=env, text=True, capture_output=True, timeout=30)
            checks = {'process_exited': result.returncode == 0, 'attachment_indicator': 'Attached image:' in result.stdout,
                      'image_response': 'KURT_IMAGE_RECEIVED' in result.stdout,
                      'not_unknown_command': 'Unknown command' not in result.stdout,
                      'exact_image_bytes_delivered': len(received) == 1 and received[0]['bytes_match']}
            return {'passed': all(checks.values()), 'checks': checks, 'requests': received,
                    'scope': 'Real installed CLI and local HTTP protocol fixture; no model inference, private photo upload or paid API call'}
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = verify(); args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
