import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import httpx

from kurt.hub import composio


def _mock_client_factory(handler):
    real_client = httpx.Client
    return lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)


class ComposioConnectErrorHandlingTests(unittest.TestCase):
    """composio_connect() must tell apart two very different /auth_configs
    failures: KURT's own API key being bad vs. the toolkit itself having no
    Composio-managed OAuth app (Composio's docs name PostHog, Tavily, and
    Perplexity as real examples of the latter)."""

    def test_api_key_error_shows_key_message_and_does_not_open_dashboard(self):
        def handler(req):
            return httpx.Response(401, json={"error": {
                "message": "Invalid API key: ck_**EO91", "code": 902,
                "slug": "Auth_Unauthorized", "suggested_fix": "Please check you are using a valid API key.",
            }})

        buf = io.StringIO()
        with patch.object(composio, "get_composio_key", return_value="ck_test"), \
             patch.object(composio.httpx, "Client", _mock_client_factory(handler)), \
             patch.object(composio, "webbrowser") as fake_browser, \
             redirect_stdout(buf):
            composio.composio_connect("spotify")

        self.assertIn("Invalid API key", buf.getvalue())
        self.assertNotIn("OAuth app", buf.getvalue())
        fake_browser.open.assert_not_called()

    def test_missing_managed_auth_explains_custom_oauth_and_opens_dashboard(self):
        def handler(req):
            return httpx.Response(400, json={"error": {
                "message": "No managed OAuth app available for toolkit spotify",
                "code": 400, "slug": "Toolkit_NoManagedAuth",
            }})

        buf = io.StringIO()
        with patch.object(composio, "get_composio_key", return_value="ck_test"), \
             patch.object(composio.httpx, "Client", _mock_client_factory(handler)), \
             patch.object(composio, "webbrowser") as fake_browser, \
             redirect_stdout(buf):
            composio.composio_connect("spotify")

        output = buf.getvalue()
        self.assertIn("needs its own OAuth app", output)
        self.assertIn("Client ID", output)
        self.assertIn("backend.composio.dev/api/v3/toolkits/auth/callback", output)
        fake_browser.open.assert_called_with("https://dashboard.composio.dev/")


if __name__ == "__main__":
    unittest.main()
