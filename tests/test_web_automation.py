import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import unittest
from unittest.mock import patch

import httpx

from kurt.core import web_browse as web
from kurt.capabilities.bridge import NativeToolRouter


class WebReaderTests(unittest.TestCase):
    def fetch(self, handler, url="https://example.org/start"):
        real = httpx.Client
        with patch.object(httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)):
            return web.read_page(url)

    def test_redirect_final_url_relative_links_and_hidden_script_removal(self):
        def handler(request):
            if request.url.path == "/start":
                return httpx.Response(302, headers={"location": "/folder/page"})
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  text='<title>Test</title><script>HIDDEN</script><p>Visible</p><a href="next">Next</a>')
        result = self.fetch(handler)
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.url, "https://example.org/folder/page")
        self.assertEqual(result.links[0]["url"], "https://example.org/folder/next")
        self.assertNotIn("HIDDEN", result.content)
        self.assertEqual(result.status_code, 200)

    def test_non_http_urls_never_reach_network(self):
        for url in ("file:///tmp/private", "ftp://example.org/file", "https://user:password@example.org"):
            with self.subTest(url=url):
                result = self.fetch(lambda req: self.fail("Unexpected network request"), url)
                self.assertFalse(result.success)

    def test_body_limit_and_text_truncation_are_distinct(self):
        with patch.object(web, "MAX_FETCH_BYTES", 100):
            result = self.fetch(lambda req: httpx.Response(200, headers={"content-type": "text/plain"}, text="x" * 101))
            self.assertFalse(result.success)
        result = self.fetch(lambda req: httpx.Response(200, headers={"content-type": "text/plain"}, text="x" * 9000))
        self.assertTrue(result.success)
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.content), 8000)

    def test_binary_data_and_http_errors_are_not_successful_pages(self):
        for response in (httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF"), httpx.Response(404)):
            result = self.fetch(lambda req: response)
            self.assertFalse(result.success)

    def test_free_search_respects_requested_result_count(self):
        rows = [{"title": str(i), "url": f"https://example.org/{i}"} for i in range(8)]
        with patch.object(web, "_brave_search", side_effect=RuntimeError), patch.object(web, "_serper_search", side_effect=RuntimeError), \
             patch.object(web, "_ddg_scrape", return_value=rows), patch.object(web, "_google_news_rss", return_value=[]):
            self.assertEqual(len(web.search_web("test", 2).results), 2)


class BrowserOwnerTests(unittest.TestCase):
    def test_legacy_desktop_mutation_cannot_skip_goal(self):
        class Planner:
            async def route(self, **kwargs):
                yield '```tool\n' + json.dumps({'tool': 'hotkey', 'params': {'keys': 'cmd+w'}}) + '\n```'
        with patch('kurt.capabilities.bridge.invoke_native') as invoke:
            async def collect():
                return [c async for c in NativeToolRouter(Planner(), max_tools=1).route('test', 'test', [{'role': 'user', 'content': 'inspect'}])]
            asyncio.run(collect())
        invoke.assert_not_called()

    def test_legacy_activation_uses_verified_open_application(self):
        replies = iter([
            {'tool': 'set_task_goal', 'params': {'goal_type': 'app_foreground', 'target_app': 'Calculator'}},
            {'tool': 'focus_window', 'params': {'app_name': 'Calculator'}},
        ])
        class Planner:
            async def route(self, **kwargs):
                yield '```tool\n' + json.dumps(next(replies)) + '\n```'
        def invoke(name, params, paths):
            if name == 'set_task_goal':
                return {'status': 'planned', **params}
            self.assertEqual((name, params), ('open_application', {'app': 'Calculator'}))
            return {'status': 'completed', 'app': 'Calculator', 'foreground_verified': True, 'pid': 123}
        with patch('kurt.capabilities.bridge.invoke_native', side_effect=invoke) as called:
            async def collect():
                return [c async for c in NativeToolRouter(Planner()).route('test', 'test', [{'role': 'user', 'content': 'open calculator'}])]
            asyncio.run(collect())
        self.assertEqual(called.call_count, 2)

    def test_browser_is_created_used_and_closed_on_one_thread(self):
        owners = []
        class FakeBrowser:
            def __init__(self, **kwargs): owners.append(threading.get_ident())
            def start(self): owners.append(threading.get_ident()); return True
            def read(self): owners.append(threading.get_ident()); return "observed"
            def close(self): owners.append(threading.get_ident())
        with patch.object(web, "KurtBrowser", FakeBrowser):
            session = web.BrowserSession()
            try:
                session.start()
                with ThreadPoolExecutor(3) as callers:
                    self.assertEqual(list(callers.map(lambda _: session.read(), range(6))), ["observed"] * 6)
            finally:
                session.close()
        self.assertEqual(len(set(owners)), 1)
        self.assertNotEqual(owners[0], threading.get_ident())

    def test_browser_mutations_require_a_declared_workflow_goal(self):
        class Planner:
            async def route(self, **kwargs):
                yield '```tool\n' + json.dumps({"tool": "browser_action", "params": {"action": "click", "selector": "#submit"}}) + '\n```'
        with patch("kurt.capabilities.bridge.invoke_native") as invoke:
            async def collect():
                return [c async for c in NativeToolRouter(Planner(), max_tools=1).route("test", "test", [{"role": "user", "content": "inspect page"}])]
            asyncio.run(collect())
        invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
