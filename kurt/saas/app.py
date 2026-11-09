"""Small ASGI API for all clients. No desktop imports or shared chat history.

Billing/SSO, distributed queues and production provisioning are intentionally
not simulated. The operator-owned Store provides the entitlement boundary.
"""
import asyncio
import json
import os
from pathlib import Path
import uuid

from .gateway import GroqGateway, ProviderUnavailable
from .protocol import MAX_BODY, MAX_OUTPUT, chat_request, decode, native_request, scrub
from .runner import IsolatedRunner, WorkerUnavailable
from .store import Denied, Store


class App:
    def __init__(self, store, gateway=None, runner=None, require_https=True):
        self.store, self.gateway, self.runner = store, gateway, runner
        self.require_https = require_https
        self._jobs = set()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    await send({"type":"lifespan.startup.complete"})
                elif event["type"] == "lifespan.shutdown":
                    await send({"type":"lifespan.shutdown.complete"}); return
            return
        if scope["type"] != "http":
            return
        request_id = str(uuid.uuid4())
        status, result = 500, {"error":"internal_error"}
        token = ""
        try:
            if scope.get("query_string"):
                raise Denied(400, "query_parameters_not_supported")
            path, method = scope.get("path"), scope.get("method")
            if path == "/health" and method == "GET":
                status, result = 200, {"status":"ok", "version":1}
            else:
                if self.require_https and scope.get("scheme") != "https":
                    raise Denied(400, "https_required")
                headers = {}
                for key,value in scope.get("headers", []):
                    key = key.lower()
                    if key in headers and key in (b"authorization", b"content-type", b"content-length"):
                        raise Denied(400, "duplicate_header")
                    headers[key] = value
                auth = headers.get(b"authorization", b"").decode("ascii")
                if not auth.startswith("Bearer "):
                    raise Denied(401, "invalid_token")
                token = auth[7:]
                # Authenticate before reading a potentially large body.
                identity = self.store.identity(token)
                if path == "/v1/me" and method == "GET":
                    status, result = 200, {"tenant":identity}
                elif path in ("/v1/chat", "/v1/native/run") and method == "POST":
                    if headers.get(b"content-type", b"").split(b";",1)[0].strip().lower() != b"application/json":
                        raise Denied(415, "json_required")
                    if int(headers.get(b"content-length", b"0")) > MAX_BODY:
                        raise Denied(413, "request_too_large")
                    raw = bytearray()
                    async def body():
                        while True:
                            message = await receive()
                            if message["type"] == "http.disconnect":
                                raise Denied(400, "request_disconnected")
                            if message["type"] != "http.request":
                                raise Denied(400, "invalid_request")
                            raw.extend(message.get("body", b""))
                            if len(raw) > MAX_BODY:
                                raise Denied(413, "request_too_large")
                            if not message.get("more_body", False):
                                return
                    await asyncio.wait_for(body(), 10)
                    data = decode(raw)
                    action = "chat" if path == "/v1/chat" else "native"
                    data = chat_request(data) if action == "chat" else native_request(data)
                    if (action == "chat" and self.gateway is None) or (action == "native" and self.runner is None):
                        raise Denied(503, "capability_unavailable")
                    tenant, lease = self.store.reserve(token, action)
                    async def execute():
                        outcome = "failed"
                        try:
                            if action == "chat":
                                response = await self.gateway.chat(scrub(data["messages"], (token,)))
                            else:
                                response = await asyncio.to_thread(self.runner.run, data)
                            outcome = "completed"
                            return {"request_id":lease, "result":scrub(response, (token,))}
                        finally:
                            self.store.finish(tenant, lease, outcome)
                    # A disconnected client cannot release its lease while the
                    # underlying native thread/container is still running.
                    task = asyncio.create_task(execute())
                    self._jobs.add(task)
                    task.add_done_callback(self._jobs.discard)
                    def consume_exception(done):
                        if not done.cancelled():
                            done.exception()
                    task.add_done_callback(consume_exception)
                    result = await asyncio.shield(task)
                    status = 200

                else:
                    raise Denied(404, "not_found")
        except Denied as exc:
            status, result = exc.status, {"error":exc.code}
        except (ValueError, UnicodeError, RecursionError, TypeError):
            status, result = 400, {"error":"invalid_request"}
        except asyncio.TimeoutError:
            status, result = 408, {"error":"request_timeout"}
        except (WorkerUnavailable, ProviderUnavailable):
            status, result = 503, {"error":"execution_unavailable"}
        except Exception:
            # Never include exception messages, payloads or provider headers.
            status, result = 500, {"error":"internal_error"}
        encoded = json.dumps(result, allow_nan=False).encode()
        if len(encoded) > MAX_OUTPUT:
            status, encoded = 502, b'{"error":"response_too_large"}'
        await send({"type":"http.response.start", "status":status, "headers":[
            (b"content-type",b"application/json"), (b"cache-control",b"no-store"),
            (b"x-content-type-options",b"nosniff"), (b"x-request-id",request_id.encode()),
            (b"content-length",str(len(encoded)).encode())]})
        await send({"type":"http.response.body", "body":encoded})


def create_app():
    """Uvicorn factory; reads server settings only, never ~/.kurt/.env.

    HTTPS is required by default — production puts this behind a TLS proxy
    (see deploy/saas/kurt-api.service's --proxy-headers). The only way off
    that default is the explicit KURT_SAAS_DEV_INSECURE_HTTP=1 opt-in below,
    for running a real local smoke test without a proxy in front. Never set
    it outside local development.
    """
    root = os.environ.get("KURT_SAAS_STATE_DIR")
    if not root or not Path(root).is_absolute():
        raise RuntimeError("Set an absolute KURT_SAAS_STATE_DIR for the server")
    gateway = None
    if os.environ.get("KURT_SAAS_GROQ_KEY"):
        gateway = GroqGateway(os.environ["KURT_SAAS_GROQ_KEY"], os.environ.get("KURT_SAAS_MODEL", "openai/gpt-oss-20b"))
    runner = None
    if os.environ.get("KURT_SAAS_WORKER_IMAGE"):
        runner = IsolatedRunner(os.environ["KURT_SAAS_WORKER_IMAGE"], os.environ.get("KURT_SAAS_DOCKER_SOCKET", "unix:///run/user/1000/docker.sock"))
    require_https = os.environ.get("KURT_SAAS_DEV_INSECURE_HTTP") != "1"
    if not require_https:
        import sys
        print("WARNING: KURT_SAAS_DEV_INSECURE_HTTP=1 — HTTPS enforcement is OFF. "
              "Local development only; never set this in production.", file=sys.stderr)
    return App(Store(root), gateway, runner, require_https=require_https)
