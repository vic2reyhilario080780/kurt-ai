"""Generic MCP Authorization flow — OAuth 2.1 + PKCE + Dynamic Client
Registration (RFC 7591) against a remote MCP server's OWN authorization
server. This is how Claude's built-in MCP connectors sign in: no
middleman connector platform, no manually issued API keys — just
"open the login page, approve, done." Implements the discovery side of
the official MCP Authorization spec (RFC 9728 protected-resource
metadata + RFC 8414 authorization-server metadata).
"""

import base64
import hashlib
import http.server
import secrets
import time
import urllib.parse
import webbrowser

import httpx

from kurt.utils.security import require_secure_endpoint

CALLBACK_HOST = "127.0.0.1"


class NotOAuthProtected(Exception):
    """Raised when the target server publishes no OAuth metadata at all —
    it's either open, or gated behind a manually issued API key instead."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _origin(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _get_json(client: httpx.Client, url: str) -> dict | None:
    try:
        resp = client.get(url, timeout=10)
    except httpx.HTTPError:
        return None
    if resp.status_code >= 400:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def discover(server_url: str) -> dict | None:
    """Resolve the authorization-server metadata (authorization_endpoint,
    token_endpoint, registration_endpoint, ...) that protects `server_url`,
    following RFC 9728 (protected-resource metadata points at one or more
    issuers) with a same-origin RFC 8414 fallback for servers that skip the
    protected-resource indirection."""
    origin = _origin(server_url)
    with httpx.Client(follow_redirects=True) as client:
        resource_meta = _get_json(client, f"{origin}/.well-known/oauth-protected-resource")
        issuers = (resource_meta or {}).get("authorization_servers") or [origin]
        for issuer in issuers:
            issuer = issuer.rstrip("/")
            for suffix in ("/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"):
                meta = _get_json(client, issuer + suffix)
                if meta and meta.get("authorization_endpoint") and meta.get("token_endpoint"):
                    return meta
    return None


def _register_client(client: httpx.Client, meta: dict, redirect_uri: str) -> str | None:
    """Dynamic Client Registration — the piece that lets Kurt skip asking
    the user for their own OAuth app/client id, same as how a fresh Claude
    install needs no pre-registered client for a new MCP connector."""
    endpoint = meta.get("registration_endpoint")
    if not endpoint:
        return None
    resp = client.post(endpoint, json={
        "client_name": "KURT",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }, timeout=15)
    if resp.status_code >= 400:
        return None
    return resp.json().get("client_id")


class _CallbackServer(http.server.HTTPServer):
    result: dict | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.result = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><body>KURT is connected. You can close this tab.</body></html>")

    def log_message(self, *_args):
        pass  # keep the chat transcript clean — nothing secret, just noisy


def _await_callback(server: _CallbackServer, timeout: float) -> dict | None:
    server.timeout = 1  # poll in small slices so the overall deadline is honored
    deadline = time.monotonic() + timeout
    try:
        while server.result is None and time.monotonic() < deadline:
            server.handle_request()
        return server.result
    finally:
        server.server_close()


def authorize(server_url: str, timeout: float = 180) -> dict:
    """Run the full flow for one MCP server: discover -> register -> open
    the browser -> wait for the redirect -> exchange the code for tokens.

    Returns {"access_token", "refresh_token", "expires_at", "token_endpoint",
    "client_id"}. Raises NotOAuthProtected if the server has no OAuth
    metadata at all, or RuntimeError with a human-readable reason otherwise.
    """
    require_secure_endpoint(server_url)
    meta = discover(server_url)
    if not meta:
        raise NotOAuthProtected(server_url)

    # Bind the loopback callback server BEFORE building the authorization
    # URL/opening the browser — otherwise there's a window where the port
    # we picked is free but nothing is listening yet to catch the redirect.
    callback_server = _CallbackServer((CALLBACK_HOST, 0), _CallbackHandler)
    port = callback_server.server_address[1]
    redirect_uri = f"http://{CALLBACK_HOST}:{port}/callback"

    try:
        with httpx.Client(timeout=20) as client:
            client_id = _register_client(client, meta, redirect_uri)
            if not client_id:
                raise RuntimeError(
                    "server doesn't support open client registration — it likely needs "
                    "a manually issued API key instead"
                )

            verifier = _b64url(secrets.token_bytes(32))
            challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
            state = _b64url(secrets.token_bytes(16))
            scope = " ".join(meta.get("scopes_supported") or [])

            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
            if scope:
                params["scope"] = scope
            auth_url = meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(params)

            try:
                webbrowser.open(auth_url)
            except Exception:
                pass  # headless/no-display — caller still has auth_url to show

            result = _await_callback(callback_server, timeout)
            if result is None:
                raise RuntimeError("timed out waiting for you to finish authorizing in the browser")
            if result.get("state") != state:
                raise RuntimeError("authorization response failed the state check")
            if "error" in result:
                raise RuntimeError(f"authorization denied: {result.get('error_description', result['error'])}")
            code = result.get("code")
            if not code:
                raise RuntimeError("no authorization code returned")

            token_resp = client.post(meta["token_endpoint"], data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": verifier,
            })
            if token_resp.status_code >= 400:
                raise RuntimeError(f"token exchange failed: HTTP {token_resp.status_code}")
            tokens = token_resp.json()
    finally:
        # _await_callback already closes it on the success/timeout path;
        # this only matters if something above raised before that point.
        try:
            callback_server.server_close()
        except OSError:
            pass

    if not tokens.get("access_token"):
        raise RuntimeError("token endpoint returned no access_token")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "expires_at": time.time() + tokens["expires_in"] if tokens.get("expires_in") else None,
        "token_endpoint": meta["token_endpoint"],
        "client_id": client_id,
    }

