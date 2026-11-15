"""Live, local-only web fetch + Playwright test; no AI/provider API calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from kurt.core.web_browse import BrowserSession, read_page

PAGE = b'''<!doctype html><title>Kurt Web Test</title><h1>Automation test</h1>
<input id="message" aria-label="Test message"><button id="apply">Apply</button>
<output id="result">Waiting</output><a href="/other">Other</a>
<script>document.querySelector('#apply').onclick=()=>{
document.querySelector('#result').textContent='WEB_OK:'+document.querySelector('#message').value;
document.title='WEB_OK';};</script>'''


def verify():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/start":
                self.send_response(302); self.send_header("Location", "/page"); self.end_headers(); return
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(PAGE)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/start"
    rows = []
    try:
        page = read_page(url)
        rows.append({"check": "live_http_fetch", "passed": page.success and page.title == "Kurt Web Test" and page.url.endswith("/page") and page.links[0]["url"].endswith("/other"), "title": page.title, "status": page.status_code})
        session = BrowserSession(headless=True, slow_mo=0)
        try:
            session.start()
            # Different caller threads exercise the actual ownership bug.
            with ThreadPoolExecutor(3) as callers:
                opened = callers.submit(session.go, url).result()
                typed = callers.submit(session.type, "#message", "KURT_WEB_VERIFIED").result()
                clicked = callers.submit(session.click, selector="#apply").result()
            observed = session.read()
            rows.append({"check": "live_playwright_multi_thread_workflow", "passed": opened.success and typed and clicked and observed.title == "WEB_OK" and "WEB_OK:KURT_WEB_VERIFIED" in observed.content, "title": observed.title, "backend": observed.backend, "controls": observed.controls})
        except Exception as exc:
            rows.append({"check": "live_playwright_multi_thread_workflow", "passed": False, "error": str(exc)})
        finally:
            session.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    return {"tested_at": datetime.now(timezone.utc).isoformat(), "scope": "Local HTTP server and real headless Chromium, no model calls", "passed": all(r["passed"] for r in rows), "results": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = verify()
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
