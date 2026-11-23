"""Small ASGI API for all clients. No desktop imports or shared chat history.

Billing/SSO, distributed queues and production provisioning are intentionally
not simulated. The operator-owned Store provides the entitlement boundary.
"""
import asyncio
import json
import os
from pathlib import Path
import uuid

from . import iap, iap_apple, iap_google, iap_huawei
from .auth import hash_password, valid_email, valid_password, verify_password
from .gateway import GroqGateway, ProviderUnavailable
from .protocol import MAX_BODY, MAX_OUTPUT, chat_request, decode, native_request, scrub
from .runner import IsolatedRunner, WorkerUnavailable
from .store import Denied, Store

IAP_ERRORS = (iap.IAPVerificationError, iap_apple.IAPVerificationError, iap_google.IAPVerificationError, iap_huawei.IAPVerificationError)

SESSION_COOKIE = "kurt_session"
SESSION_DAYS = 30


class App:
    def __init__(self, store, gateway=None, runner=None, require_https=True, allowed_origin=None, iap_config=None):
        self.store, self.gateway, self.runner = store, gateway, runner
        self.require_https = require_https
        # Explicit single origin only (never "*") — required for
        # Access-Control-Allow-Credentials with cookie-based web sessions.
        self.allowed_origin = allowed_origin
        # {"apple": {"trusted_root_der": bytes}, "google": {"service_account": dict, "package_name": str},
        #  "huawei": {"client_id": str, "client_secret": str}} — each key present only when that
        # provider is configured; see create_app()'s env vars and kurt/saas/iap_*.py.
        self.iap_config = iap_config or {}
        self._jobs = set()

    async def _read_json(self, receive, headers):
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
        return decode(raw)

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
        set_cookie = None
        cors_headers = []
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
                origin = headers.get(b"origin", b"").decode("ascii")
                if self.allowed_origin and origin == self.allowed_origin:
                    cors_headers = [
                        (b"access-control-allow-origin", origin.encode()),
                        (b"access-control-allow-credentials", b"true"),
                        (b"vary", b"Origin"),
                    ]
                if method == "OPTIONS":
                    # Preflight only makes sense for an origin we actually
                    # allow; otherwise behave like any other unknown route.
                    if not cors_headers:
                        raise Denied(404, "not_found")
                    cors_headers.append((b"access-control-allow-methods", b"GET, POST, OPTIONS"))
                    cors_headers.append((b"access-control-allow-headers", b"authorization, content-type"))
                    status, result = 204, None
                elif path == "/v1/signup" and method == "POST":
                    data = await self._read_json(receive, headers)
                    if not {"email", "password"} <= set(data) <= {"email", "password", "client"} \
                            or data.get("client", "cookie") not in ("cookie", "bearer") \
                            or not valid_email(data["email"]) or not valid_password(data["password"]):
                        raise Denied(400, "invalid_signup")
                    self.store.check_rate_limit("signup:" + _client_ip(scope), 3600, 20)
                    tenant = self.store.create_account(data["email"], hash_password(data["password"]))
                    token = self.store.issue_token(tenant, SESSION_DAYS)
                    set_cookie, status, result = _issue_session(self.store, token, data.get("client", "cookie"))
                elif path == "/v1/login" and method == "POST":
                    data = await self._read_json(receive, headers)
                    if not {"email", "password"} <= set(data) <= {"email", "password", "client"} \
                            or data.get("client", "cookie") not in ("cookie", "bearer"):
                        raise Denied(400, "invalid_login")
                    self.store.check_rate_limit("login:" + _client_ip(scope), 300, 30)
                    account = self.store.account_by_email(data["email"]) if valid_email(data["email"]) else None
                    if account is None or not verify_password(data["password"], account["password_hash"]):
                        raise Denied(401, "invalid_credentials")
                    token = self.store.issue_token(account["tenant"], SESSION_DAYS)
                    set_cookie, status, result = _issue_session(self.store, token, data.get("client", "cookie"))
                elif path == "/v1/logout" and method == "POST":
                    existing = _extract_token(headers)
                    if existing:
                        self.store.revoke_token(existing)
                    set_cookie = _session_cookie("", 0)
                    status, result = 200, {"status": "logged_out"}
                else:
                    token = _extract_token(headers)
                    if not token:
                        raise Denied(401, "invalid_token")
                    # Authenticate before reading a potentially large body.
                    identity = self.store.identity(token)
                    if path == "/v1/me" and method == "GET":
                        status, result = 200, {"tenant":identity}
                    elif path in ("/v1/chat", "/v1/native/run") and method == "POST":
                        data = await self._read_json(receive, headers)
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

                    elif path.startswith("/v1/iap/") and method == "POST":
                        provider = path[len("/v1/iap/"):]
                        if provider not in ("apple", "google", "huawei"):
                            raise Denied(404, "not_found")
                        config = self.iap_config.get(provider)
                        if config is None:
                            raise Denied(503, "capability_unavailable")
                        data = await self._read_json(receive, headers)
                        product_id = await _verify_iap_purchase(provider, config, data)
                        plan, days = iap.plan_for_product(product_id)
                        self.store.grant(plan, days, tenant=identity["id"])
                        status, result = 200, {"tenant": self.store.identity(token)}

                    else:
                        raise Denied(404, "not_found")
        except Denied as exc:
            status, result = exc.status, {"error":exc.code}
        except IAP_ERRORS as exc:
            status, result = 402, {"error": "purchase_not_verified", "detail": str(exc)}
        except (ValueError, UnicodeError, RecursionError, TypeError):
            status, result = 400, {"error":"invalid_request"}
        except asyncio.TimeoutError:
            status, result = 408, {"error":"request_timeout"}
        except (WorkerUnavailable, ProviderUnavailable):
            status, result = 503, {"error":"execution_unavailable"}
        except Exception:
            # Never include exception messages, payloads or provider headers.
            status, result = 500, {"error":"internal_error"}
        if status == 204:
            encoded = b""
        else:
            encoded = json.dumps(result, allow_nan=False).encode()
            if len(encoded) > MAX_OUTPUT:
                status, encoded = 502, b'{"error":"response_too_large"}'
        response_headers = [
            (b"content-type",b"application/json"), (b"cache-control",b"no-store"),
            (b"x-content-type-options",b"nosniff"), (b"x-request-id",request_id.encode()),
            (b"content-length",str(len(encoded)).encode())]
        response_headers.extend(cors_headers)
        if set_cookie is not None:
            response_headers.append((b"set-cookie", set_cookie))
        await send({"type":"http.response.start", "status":status, "headers":response_headers})
        await send({"type":"http.response.body", "body":encoded})


def _client_ip(scope):
    client = scope.get("client")
    return client[0] if client else "unknown"


def _extract_token(headers):
    """Bearer header (CLI/mobile/desktop) or the kurt_session cookie (web) —
    one identity path either way, resolved the same way by Store.identity()."""
    auth = headers.get(b"authorization", b"").decode("ascii")
    if auth.startswith("Bearer "):
        return auth[7:]
    cookie_header = headers.get(b"cookie", b"").decode("ascii")
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name == SESSION_COOKIE and value:
            return value
    return ""


def _session_cookie(token, days):
    max_age = days * 86400 if token else 0
    return f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={max_age}".encode()


def _issue_session(store, token, client_mode):
    """cookie (default, web app): SameSite=Strict HttpOnly cookie, token never
    in the JSON body — the whole point of HttpOnly. bearer (extension/mobile):
    no cookie at all (SameSite=Strict cookies are never sent cross-site, which
    a chrome-extension:// origin always is) — the raw token goes in the body
    instead, for the caller to hold in its own storage (chrome.storage.local,
    OS keychain, ...) and send back as `Authorization: Bearer <token>`, same
    as the existing CLI/admin.py-issued tokens."""
    identity = store.identity(token)
    if client_mode == "bearer":
        return None, 200, {"tenant": identity, "token": token}
    return _session_cookie(token, SESSION_DAYS), 200, {"tenant": identity}


async def _verify_iap_purchase(provider, config, data):
    """Dispatch to the right store's verifier and return the verified
    product id. Raises one of IAP_ERRORS on any failure — the caller never
    grants a plan without a positively verified purchase."""
    if provider == "apple":
        if set(data) != {"signedTransaction"} or not isinstance(data["signedTransaction"], str):
            raise iap.IAPVerificationError("invalid_request")
        payload = iap_apple.verify_transaction(data["signedTransaction"], trusted_root_der=config["trusted_root_der"])
        return payload.get("productId")
    if provider == "google":
        if set(data) != {"productId", "purchaseToken"} or not all(isinstance(data[k], str) for k in data):
            raise iap.IAPVerificationError("invalid_request")
        item = await iap_google.verify_purchase(
            service_account=config["service_account"], package_name=config["package_name"],
            product_id=data["productId"], purchase_token=data["purchaseToken"],
        )
        return item.get("productId")
    if set(data) != {"productId", "purchaseToken"} or not all(isinstance(data[k], str) for k in data):
        raise iap.IAPVerificationError("invalid_request")
    purchase = await iap_huawei.verify_purchase(
        client_id=config["client_id"], client_secret=config["client_secret"],
        product_id=data["productId"], purchase_token=data["purchaseToken"],
    )
    return purchase.get("productId", data["productId"])


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
    # Explicit single web origin only — never a wildcard, since cookie-based
    # sessions require Access-Control-Allow-Credentials. Unset means no web
    # client (CLI/mobile/desktop Bearer-token usage is unaffected either way).
    allowed_origin = os.environ.get("KURT_SAAS_WEB_ORIGIN") or None
    if allowed_origin and allowed_origin.rstrip("/") != allowed_origin:
        raise RuntimeError("KURT_SAAS_WEB_ORIGIN must not have a trailing slash")
    iap_config = _load_iap_config()
    return App(Store(root), gateway, runner, require_https=require_https, allowed_origin=allowed_origin, iap_config=iap_config)


def _load_iap_config():
    """Each provider is configured independently and is absent (not a
    broken/partial entry) unless all of its required settings are present —
    see kurt/saas/iap_apple.py / iap_google.py / iap_huawei.py for what each
    value is used for and where to obtain the real one. None of these are
    fabricated or bundled by this project."""
    config = {}
    apple_root_path = os.environ.get("KURT_SAAS_APPLE_ROOT_CA_PATH")
    if apple_root_path:
        config["apple"] = {"trusted_root_der": Path(apple_root_path).read_bytes()}
    google_sa_path = os.environ.get("KURT_SAAS_GOOGLE_SERVICE_ACCOUNT_PATH")
    google_package = os.environ.get("KURT_SAAS_GOOGLE_PACKAGE_NAME")
    if google_sa_path and google_package:
        config["google"] = {
            "service_account": json.loads(Path(google_sa_path).read_text()),
            "package_name": google_package,
        }
    huawei_client_id = os.environ.get("KURT_SAAS_HUAWEI_CLIENT_ID")
    huawei_client_secret = os.environ.get("KURT_SAAS_HUAWEI_CLIENT_SECRET")
    if huawei_client_id and huawei_client_secret:
        config["huawei"] = {"client_id": huawei_client_id, "client_secret": huawei_client_secret}
    return config
