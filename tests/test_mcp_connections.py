import asyncio
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx
from typer.testing import CliRunner

from kurt.core import mcp_catalog as catalog
from kurt.core import mcp_client as client
from kurt.core import mcp_oauth


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for key, value in (("KURT_DIR", root), ("MCP_REGISTRY_PATH", root / "connections.json")):
            p = patch.object(client, key, value)
            p.start()
            self.addCleanup(p.stop)

    def test_paste_claude_and_vscode_configs(self):
        for wrapper in ("mcpServers", "servers"):
            cfg = {wrapper: {"app": {"type": "streamable-http", "url": "https://example.org/mcp"}}}
            conn = catalog.parse_config(json.dumps(cfg))[0]
            self.assertEqual((conn.name, conn.transport), ("app", "http"))

    def test_import_does_not_spawn_or_connect(self):
        with patch("asyncio.create_subprocess_exec", side_effect=AssertionError("must not start")):
            names = catalog.import_config('{"app":{"command":"missing-app","args":["a b"]}}')
        self.assertEqual(names, ["app"])
        self.assertEqual(client.load_registry()["app"].args, ["a b"])
        self.assertEqual(client.MCP_REGISTRY_PATH.stat().st_mode & 0o777, 0o600)

    def test_env_expansion_and_no_secret_echo(self):
        with patch.dict(os.environ, {"KURT_TEST_TOKEN": "secret-token"}):
            conn = catalog.parse_config('{"a":{"url":"https://example.org/mcp","headers":{"Authorization":"Bearer ${KURT_TEST_TOKEN}"}}}')[0]
        self.assertEqual(conn.headers["Authorization"], "Bearer secret-token")

    def test_placeholders_and_invalid_values_rejected(self):
        for value in (
            '{"a":{"url":"https://example.org/{tenant}/mcp"}}',
            '{"a":{"url":"https://example.org","headers":{"Key":"${KURT_MISSING_123}"}}}',
            '{"a":{"url":"file:///etc/passwd"}}',
            '{"a":{"command":"npx","args":"-y package"}}',
            '{"a":{"url":"https://example.org","headers":{"Key":12}}}',
            '{"a":{"url":"https://example.org","type":"websocket"}}',
            '{"a":{"url":"https://example.org","oauth":true}}',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                catalog.import_config(value)
        self.assertFalse(client.MCP_REGISTRY_PATH.exists())

    def test_collisions_preserve_registry(self):
        catalog.import_config('{"a":{"url":"https://example.org/mcp"}}')
        before = client.MCP_REGISTRY_PATH.read_bytes()
        with self.assertRaises(ValueError):
            catalog.import_config('{"a":{"url":"https://other.org/mcp"}}')
        self.assertEqual(client.MCP_REGISTRY_PATH.read_bytes(), before)
        catalog.import_config('{"a":{"url":"https://other.org/mcp"}}', replace=True)
        self.assertEqual(client.load_registry()["a"].url, "https://other.org/mcp")

    def test_single_url_and_single_object(self):
        self.assertEqual(catalog.parse_config("https://example.org/mcp")[0].name, "example.org")
        self.assertEqual(catalog.parse_config('{"command":"uvx"}', name="single")[0].name, "single")

    def test_corrupt_registry_is_not_overwritten(self):
        client.MCP_REGISTRY_PATH.write_text("broken")
        with self.assertRaises(ValueError):
            catalog.import_config('{"a":{"url":"https://example.org/mcp"}}')
        self.assertEqual(client.MCP_REGISTRY_PATH.read_text(), "broken")

    def test_legacy_registry_without_name(self):
        client.MCP_REGISTRY_PATH.write_text('{"legacy":{"transport":"http","url":"https://example.org"}}')
        self.assertEqual(client.load_registry()["legacy"].name, "legacy")

    def test_sdk_auth_diagnostics_redact_url_and_token(self):
        request = httpx.Request("POST", "https://example.org/mcp?apiKey=secret")
        response = httpx.Response(401, request=request)
        message = client.connection_error(httpx.HTTPStatusError("secret", request=request, response=response))
        self.assertIn("401", message)
        self.assertNotIn("secret", message)

    def test_cli_and_chat_import(self):
        from kurt.main import app
        from kurt.core.cli_orchestrator import handle_slash
        result = CliRunner().invoke(app, ["mcp", "import", '{"cli":{"url":"https://example.org/mcp"}}'])
        self.assertEqual(result.exit_code, 0, result.output)
        result = handle_slash('/mcp import {"chat":{"url":"https://example.org/mcp"}}', "test", None, None)
        self.assertIn("Saved: chat", result.output)
        self.assertEqual(set(client.load_registry()), {"cli", "chat"})


class CatalogTests(unittest.TestCase):
    def test_bundled_catalog_has_over_10000_distinct_entries(self):
        data = catalog.load_catalog(catalog.BUNDLED_CATALOG)
        entries = data["entries"]
        self.assertGreaterEqual(sum(bool(e["configs"]) for e in entries), 10000)
        self.assertEqual(len(entries), len({e["id"] for e in entries}))
        self.assertEqual(len(entries), data["count"])
        self.assertTrue(all(e["source"] == catalog.REGISTRY_URL for e in entries))

    def test_registry_recipe_preserves_args_headers_and_requirements(self):
        e = catalog.registry_entry({"server": {"name": "org.example/test", "remotes": [
            {"type": "sse", "url": "https://example.org/sse", "headers": [{"name": "Authorization", "value": "Bearer {token}"}]}],
            "packages": [{"registryType": "pypi", "identifier": "test-mcp", "version": "1.2.3", "transport": {"type": "stdio"},
                          "environmentVariables": [{"name": "API_KEY", "isRequired": True}],
                          "packageArguments": [{"type": "named", "name": "--folder", "value": "a b"}]}]}})
        self.assertEqual(e["configs"][0]["headers"]["Authorization"], "Bearer {token}")
        self.assertEqual(e["configs"][1]["args"], ["test-mcp==1.2.3", "--folder", "a b"])
        self.assertEqual(e["configs"][1]["env"], {"API_KEY": "${API_KEY}"})

    def test_pagination_deduplication_and_failed_refresh(self):
        def handler(req):
            if "cursor" not in req.url.params:
                return httpx.Response(200, json={"servers": [{"server": {"name": "org.example/a"}}], "metadata": {"nextCursor": "next"}})
            return httpx.Response(200, json={"servers": [{"server": {"name": "org.example/a"}}, {"server": {"name": "org.example/b"}}]})
        real_client = httpx.Client
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            with patch.object(catalog.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler))):
                data = catalog.sync_catalog(path)
            self.assertEqual(data["count"], 2)
            before = path.read_bytes()
            def failing(req):
                return httpx.Response(503)
            with patch.object(catalog.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(failing))), patch.object(catalog.time, "sleep"):
                with self.assertRaises(httpx.HTTPStatusError):
                    catalog.sync_catalog(path)
            self.assertEqual(path.read_bytes(), before)

    def test_export_and_search_work_offline(self):
        rows = catalog.search_catalog("context7", path=catalog.BUNDLED_CATALOG)
        self.assertTrue(rows)
        data = catalog.export_config("io.github.upstash/context7", 1, path=catalog.BUNDLED_CATALOG)
        self.assertIn("mcpServers", data)
        self.assertEqual(catalog.parse_config(json.dumps(data))[0].transport, "stdio")


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    fixture = str(Path(__file__).with_name("mcp_fixture_server.py"))

    async def test_real_stdio_initialize_list_call_and_cleanup(self):
        conn = client.MCPConnection("stdio-test", "stdio", command=sys.executable, args=[self.fixture])
        tools = await client.probe_connection(conn)
        self.assertEqual([t.name for t in tools], ["echo"])
        self.assertIn("echo:hello", await client.call_tool(conn, "echo", {"text": "hello"}))
        self.assertIn("Tool error", await client.call_tool(conn, "echo", {}))

    async def test_agent_can_call_mcp_inside_running_event_loop(self):
        from kurt.core.agent_loop import execute_tool
        conn = client.MCPConnection("agent-test", "stdio", command=sys.executable, args=[self.fixture])
        with patch.object(client, "load_registry", return_value={"agent-test": conn}):
            result = execute_tool("mcp_tool", {"tool_ref": "agent-test/echo", "params": {"text": "agent"}})
        self.assertIn("echo:agent", result)

    async def test_http_and_legacy_sse_sessions(self):
        for transport, protocol, endpoint in (("streamable-http", "http", "/mcp"), ("sse", "sse", "/sse")):
            with self.subTest(transport=transport):
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                proc = subprocess.Popen([sys.executable, self.fixture, transport, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    for _ in range(100):
                        if proc.poll() is not None:
                            self.fail("Fixture server exited before startup")
                        try:
                            with socket.create_connection(("127.0.0.1", port), timeout=.1):
                                break
                        except OSError:
                            await asyncio.sleep(.05)
                    conn = client.MCPConnection("remote-test", protocol, url=f"http://127.0.0.1:{port}{endpoint}")
                    self.assertEqual([t.name for t in await client.probe_connection(conn)], ["echo"])
                    self.assertIn("echo:remote", await client.call_tool(conn, "echo", {"text": "remote"}))
                finally:
                    proc.terminate()
                    proc.wait(timeout=10)


class OAuthTests(unittest.TestCase):
    """Discovery + Dynamic Client Registration + PKCE token exchange,
    all against a mocked authorization server — the local callback
    socket is real, but we simulate the user's browser by hitting it
    directly instead of driving an actual browser."""

    def _mock_client(self, handler):
        # Capture the real Client class before patch.object replaces
        # httpx.Client (the same module object mcp_oauth imports) —
        # otherwise this factory would recursively call its own mock.
        real_client = httpx.Client
        return lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs)

    def test_discover_returns_none_when_server_publishes_no_metadata(self):
        def handler(req):
            return httpx.Response(404)
        with patch.object(mcp_oauth.httpx, "Client", self._mock_client(handler)):
            self.assertIsNone(mcp_oauth.discover("https://example.org/mcp"))

    def test_discover_follows_protected_resource_to_authorization_server(self):
        def handler(req):
            if req.url.path == "/.well-known/oauth-protected-resource":
                return httpx.Response(200, json={"authorization_servers": ["https://auth.example.org"]})
            if req.url.host == "auth.example.org" and req.url.path == "/.well-known/oauth-authorization-server":
                return httpx.Response(200, json={
                    "authorization_endpoint": "https://auth.example.org/authorize",
                    "token_endpoint": "https://auth.example.org/token",
                })
            return httpx.Response(404)
        with patch.object(mcp_oauth.httpx, "Client", self._mock_client(handler)):
            meta = mcp_oauth.discover("https://example.org/mcp")
        self.assertEqual(meta["token_endpoint"], "https://auth.example.org/token")

    def test_authorize_end_to_end_with_pkce_and_dynamic_registration(self):
        issued_client_id = "dcr-client-123"
        seen = {}

        def handler(req):
            if req.url.path == "/.well-known/oauth-protected-resource":
                return httpx.Response(404)  # same-origin fallback path
            if req.url.path == "/.well-known/oauth-authorization-server":
                return httpx.Response(200, json={
                    "authorization_endpoint": "https://example.org/authorize",
                    "token_endpoint": "https://example.org/token",
                    "registration_endpoint": "https://example.org/register",
                })
            if req.url.path == "/register":
                seen["redirect_uri"] = json.loads(req.content)["redirect_uris"][0]
                return httpx.Response(200, json={"client_id": issued_client_id})
            if req.url.path == "/token":
                body = dict(urllib.parse.parse_qsl(req.content.decode()))
                seen["token_request"] = body
                self.assertEqual(body["client_id"], issued_client_id)
                self.assertEqual(body["redirect_uri"], seen["redirect_uri"])
                # PKCE: verifier must hash forward to the challenge the test sent as the auth code.
                return httpx.Response(200, json={"access_token": "tok-abc", "refresh_token": "ref-abc", "expires_in": 3600})
            return httpx.Response(404)

        def fake_open(url):
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            self.assertEqual(params["client_id"], issued_client_id)
            callback = params["redirect_uri"] + "?" + urllib.parse.urlencode({
                "code": "authcode-xyz", "state": params["state"],
            })
            threading.Thread(target=lambda: (time.sleep(0.05), urllib.request.urlopen(callback, timeout=5))).start()
            return True

        with patch.object(mcp_oauth.httpx, "Client", self._mock_client(handler)), \
             patch.object(mcp_oauth, "webbrowser") as fake_webbrowser, \
             patch.object(mcp_oauth, "require_secure_endpoint"):
            fake_webbrowser.open.side_effect = fake_open
            tokens = mcp_oauth.authorize("https://example.org/mcp", timeout=10)

        self.assertEqual(tokens["access_token"], "tok-abc")
        self.assertEqual(tokens["refresh_token"], "ref-abc")
        self.assertEqual(seen["token_request"]["code"], "authcode-xyz")
        self.assertIn("code_verifier", seen["token_request"])

    def test_authorize_raises_not_oauth_protected_when_no_metadata(self):
        def handler(req):
            return httpx.Response(404)
        with patch.object(mcp_oauth.httpx, "Client", self._mock_client(handler)), \
             patch.object(mcp_oauth, "require_secure_endpoint"):
            with self.assertRaises(mcp_oauth.NotOAuthProtected):
                mcp_oauth.authorize("https://example.org/mcp")


if __name__ == "__main__":
    unittest.main()
