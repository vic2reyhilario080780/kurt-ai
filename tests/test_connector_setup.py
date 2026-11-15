"""Connector browsing must stay read-only; connection claims need receipts."""

import asyncio
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from kurt.core import command_palette as palette
from kurt.core import connector_pages as pages
from kurt.core import mcp_client as client
from kurt.core import mcp_commands as commands
from kurt.core import mcp_oauth
from kurt.hub import composio


class ConnectorSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for obj, name, value in (
            (client, "KURT_DIR", Path(tmp.name)),
            (client, "MCP_REGISTRY_PATH", Path(tmp.name) / "connections.json"),
            (composio, "KURT_DIR", Path(tmp.name)),
        ):
            context = patch.object(obj, name, value)
            context.start()
            self.addCleanup(context.stop)

    def test_publisher_website_and_repository_both_survive(self):
        entry = {"website": "https://app.example/setup", "repository": "https://github.com/org/server"}
        self.assertEqual(set(pages.entry_pages(entry).values()), set(entry.values()))
        self.assertEqual(pages.entry_pages({}), {})

    def test_browser_failure_retains_manual_link_and_rejects_non_web_links(self):
        with patch.object(pages.webbrowser, "open", return_value=False) as browser:
            self.assertIn("https://example.org", pages.open_page("https://example.org"))
            pages.open_page("file:///tmp/example")
            pages.open_page("https://user:secret@example.org")
        self.assertEqual(browser.call_count, 1)

    def test_all_directories_have_setup_menus_without_connecting(self):
        for provider, ref in (("composio", "gmail"), ("zapier", "shopify"), ("n8n", "slack")):
            with self.subTest(provider=provider), patch.object(pages.webbrowser, "open") as browser:
                items = palette._connector_detail_items(provider, ref, "")
                self.assertTrue(any(i["kind"] == "browser" for i in items))
                self.assertTrue(any(i["kind"] == "leaf" for i in items))
                browser.assert_not_called()
                self.assertEqual(client.load_registry(), {})

    def test_mcp_list_contains_platforms_and_does_not_hide_same_short_names(self):
        entries = [{"id": "org/github", "description": "", "configs": []}]
        with patch.object(palette, "_catalog_entries", return_value=entries):
            items = palette._mcp_items("")
        targets = {i.get("target") for i in items}
        self.assertTrue({"connectors", "zapier", "n8n", "connector:mcp:org/github"} <= targets)

    def test_recipe_choices_and_links_available_even_without_recipe(self):
        entry = {"id": "org/app", "configs": [{"type": "http"}, {"type": "stdio", "command": "uvx"}],
                 "website": "https://example.org", "repository": "https://github.com/org/app"}
        with patch.object(palette, "_catalog_entries", return_value=[entry]):
            items = palette._connector_detail_items("mcp", "org/app", "")
            self.assertTrue(any(i.get("value") == "/mcp authorize org/app --variant 1" for i in items))
            entry["configs"] = []
            items = palette._connector_detail_items("mcp", "org/app", "")
            self.assertEqual(sum(i["kind"] == "browser" for i in items), 2)
            self.assertFalse(any(i["kind"] == "leaf" for i in items))

    def test_embedded_credentials_url_variables_and_argument_variables_are_filled(self):
        recipe = {"type": "http", "url": "https://{tenant}.example/mcp",
                  "headers": {"authorization": "Bearer ${TOKEN}", "X-Key": "${KEY}"},
                  "args": ["--key=${KEY}", "${FOLDER}"], "env": {"ACTUAL_KEY": "${KEY}"}}
        self.assertEqual(set(commands._recipe_missing_fields(recipe)), {"tenant", "TOKEN", "KEY", "FOLDER"})
        filled = commands._fill_recipe(recipe, {"tenant": "test", "TOKEN": "abc", "KEY": "key", "FOLDER": "/tmp"})
        self.assertEqual(filled["headers"], {"authorization": "Bearer abc", "X-Key": "key"})
        self.assertEqual(filled["env"], {"ACTUAL_KEY": "key"})
        self.assertEqual(filled["args"], ["--key=key", "/tmp"])
        self.assertEqual(commands._recipe_missing_fields(filled), [])

    def test_env_credentials_skip_oauth_and_keep_catalog_namespace(self):
        entry = {"id": "org/app", "configs": [{"type": "http", "url": "https://example.org/mcp",
                 "headers": {"Authorization": "Bearer ${TEST_CONNECT_TOKEN}"}}]}
        probe = AsyncMock(return_value=[])
        with patch.object(commands.catalog, "load_catalog", return_value={"entries": [entry]}), \
             patch.dict(os.environ, {"TEST_CONNECT_TOKEN": "sample-token"}), \
             patch.object(mcp_oauth, "authorize") as oauth, patch.object(client, "probe_connection", probe), \
             redirect_stdout(io.StringIO()):
            commands.connect_entry("org/app")
        oauth.assert_not_called()
        self.assertEqual(client.load_registry()["org/app"].headers["Authorization"], "Bearer sample-token")

    def test_cancel_never_saves_or_probes(self):
        with patch.object(commands.sys.stdin, "isatty", return_value=True), \
             patch.object(commands, "_show_setup_pages"), \
             patch.object(mcp_oauth, "authorize", side_effect=mcp_oauth.NotOAuthProtected()), \
             patch("rich.prompt.Prompt.ask", side_effect=KeyboardInterrupt), \
             patch.object(client, "probe_connection", AsyncMock()) as probe, \
             redirect_stdout(io.StringIO()), patch.dict(client.PRESETS["github"].headers, {"Authorization": ""}):
            commands.connect_entry("github")
        self.assertEqual(client.load_registry(), {})
        probe.assert_not_called()

    def test_platform_endpoint_is_tested_and_url_not_echoed(self):
        url = "https://example.org/secret-connection/mcp"
        output = io.StringIO()
        with patch.object(commands.sys.stdin, "isatty", return_value=True), \
             patch.object(commands, "_show_setup_pages"), \
             patch("rich.prompt.Prompt.ask", side_effect=[url, "my-token"]), \
             patch.object(client, "probe_connection", AsyncMock(return_value=[])) as probe, redirect_stdout(output):
            commands.connect_platform("zapier")
        probe.assert_awaited_once()
        self.assertNotIn(url, output.getvalue())
        self.assertEqual(client.load_registry()["zapier"].url, url)

    def test_failed_probe_does_not_claim_connected(self):
        output = io.StringIO()
        with patch.object(client, "probe_connection", AsyncMock(side_effect=RuntimeError("bad auth"))), redirect_stdout(output):
            commands._save_and_report(client.MCPConnection(name="test", transport="http", url="https://example.org"), "test")
        self.assertIn("test call failed", output.getvalue())
        self.assertNotIn("Connected:", output.getvalue())

    def test_namespaced_catalog_tool_can_be_called(self):
        client.add_connection(client.MCPConnection(name="org/app", transport="http", url="https://example.org"))
        with patch.object(client, "call_tool", AsyncMock(return_value="ok")) as call:
            self.assertEqual(asyncio.run(client.execute_mcp_tool("org/app/search", {})), "ok")
        self.assertEqual(call.call_args.args[1], "search")

    def test_composio_without_redirect_does_not_claim_pending_account_active(self):
        real_client = httpx.Client
        def handler(req):
            if req.url.path.endswith("auth_configs"):
                if req.method == "GET":
                    return httpx.Response(200, json={"items": []})
                return httpx.Response(200, json={"auth_config": {"id": "ac_test"}})
            return httpx.Response(200, json={"id": "ca_test", "status": "INITIATED"})
        output = io.StringIO()
        with patch.object(composio, "get_composio_key", return_value="test"), \
             patch.object(composio.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)), \
             redirect_stdout(output):
            composio.composio_connect("notion", open_browser=False)
        self.assertIn("not connected yet", output.getvalue())
        self.assertNotIn("✅", output.getvalue())

    def test_composio_reuses_custom_config_and_uses_hosted_link(self):
        real_client = httpx.Client
        requests = []
        def handler(req):
            requests.append(req)
            if req.url.path.endswith("auth_configs"):
                return httpx.Response(200, json={"items": [{"id": "ac_custom", "toolkit": {"slug": "notion"},
                                                            "auth_scheme": "API_KEY", "status": "ENABLED"}]})
            if req.url.path.endswith("/link"):
                self.assertEqual(json.loads(req.content), {"auth_config_id": "ac_custom", "user_id": "default"})
                return httpx.Response(201, json={"connected_account_id": "ca_new", "redirect_url": "https://connect.composio.dev/link/test"})
            self.fail(f"Unexpected request: {req.url.path}")
        with patch.object(composio, "get_composio_key", return_value="test"), \
             patch.object(composio.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)), \
             patch.object(composio, "_poll_connection", return_value="ACTIVE") as poll, \
             patch.object(composio.webbrowser, "open") as browser, redirect_stdout(io.StringIO()):
            composio.composio_connect("notion")
        self.assertEqual(len(requests), 2)
        browser.assert_called_once_with("https://connect.composio.dev/link/test")
        self.assertEqual(poll.call_args.args[2], "ca_new")


class PickerInteractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_website_keeps_picker_open_then_connect_submits_actual_command(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        real_session = palette.PromptSession
        with create_pipe_input() as pipe:
            with patch.object(palette, "PromptSession", lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
                session, state = palette._build_session()
            state.is_open = True
            state.view = "connector:composio:gmail"
            items = palette._current_items(state, "")
            state.index = next(i for i, item in enumerate(items) if item["kind"] == "browser")
            with patch.object(pages.webbrowser, "open", return_value=True) as browser:
                task = asyncio.create_task(session.prompt_async(default="/"))
                try:
                    await asyncio.sleep(0.05)
                    pipe.send_text("\r")
                    await asyncio.sleep(0.05)
                    browser.assert_called_once()
                    self.assertFalse(task.done())
                    self.assertTrue(state.is_open)
                    self.assertIn("return here", state.notice)
                    state.index = 0
                    pipe.send_text("\r")
                    result = await asyncio.wait_for(task, timeout=2)
                    self.assertEqual(result, "/connect gmail")
                    self.assertEqual(session.default_buffer.text, "/connect gmail")
                finally:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass


if __name__ == "__main__":
    unittest.main()
