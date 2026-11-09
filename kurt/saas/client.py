"""Shared hosted API client for CLI, desktop and mobile adapters.

Clients carry a revocable Kurt device token, never a platform provider API key.
No automatic upload, local file execution or server-selected desktop action.
"""
import json
import os
from pathlib import Path
import httpx

from kurt.utils.security import require_secure_endpoint
from .protocol import MAX_BODY, MAX_OUTPUT, scrub


class CloudClient:
    def __init__(self, url, token):
        require_secure_endpoint(url)
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        if parsed.query or parsed.path not in ("", "/"):
            raise ValueError("Cloud URL must be an origin without a path or query")
        if not isinstance(token, str) or not token.startswith("kurt_live_"):
            raise ValueError("A Kurt device token is required")
        self.url, self._token = url.rstrip("/"), token

    def request(self, route, payload=None):
        if route not in ("/v1/me", "/v1/chat", "/v1/native/run"):
            raise ValueError("Unknown hosted route")
        raw = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
        if raw is not None and len(raw) > MAX_BODY:
            raise ValueError("Request too large")
        with httpx.Client(timeout=120, follow_redirects=False, trust_env=False) as client:
            with client.stream("POST" if payload is not None else "GET", self.url+route,
                    content=raw, headers={"Authorization":"Bearer "+self._token, "Content-Type":"application/json"}) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Hosted request failed (HTTP {response.status_code})")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_OUTPUT:
                        raise ValueError("Response too large")
        return scrub(json.loads(data), (self._token,))


def from_env():
    return CloudClient(os.environ.get("KURT_CLOUD_URL", ""), os.environ.get("KURT_CLOUD_TOKEN", ""))


def register_commands(app):
    import typer
    cloud = typer.Typer(help="Use a hosted Kurt subscription; provider keys stay on the server.")
    app.add_typer(cloud, name="cloud")

    def emit(callback):
        try:
            typer.echo(json.dumps(callback(), ensure_ascii=False))
        except (ValueError, RuntimeError, OSError, httpx.HTTPError):
            typer.echo("Cloud request failed. Check the endpoint, token, subscription and server availability.", err=True)
            raise typer.Exit(1)

    @cloud.command("status")
    def status():
        """Check your own subscription using KURT_CLOUD_URL and KURT_CLOUD_TOKEN."""
        emit(lambda: from_env().request("/v1/me"))

    @cloud.command("ask")
    def ask(prompt: str):
        """Send an explicit text request; no local tools or files are uploaded."""
        emit(lambda: from_env().request("/v1/chat", {"messages":[{"role":"user","content":prompt}]}))

    @cloud.command("run")
    def run(capability_id: str, input_path: Path = typer.Option(..., "--input")):
        """Explicitly upload CSV/JSON records for an isolated native recipe job."""
        def request():
            from kurt.capabilities.engine import load_rows
            return from_env().request("/v1/native/run", {"capability_id":capability_id,"rows":load_rows(input_path)})
        emit(request)
