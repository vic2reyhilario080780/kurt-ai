"""Credential boundaries for logs, model context, local files and child processes.

Redaction is defense in depth, not a sandbox. Arbitrary same-user programs can
still read credentials from disk or capture a screen containing a secret.
"""

from functools import lru_cache
import base64
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote, quote_plus


MASK = "[REDACTED]"
_REGISTERED = set()
_SECRET_NAME = re.compile(r"(?:api.?key|access.?key|private.?key|secret|password|passwd|credential|authorization|(?:access|refresh|auth|bot|bearer|session).?token|(?:^|_)token$|cookie|database_url|connection_string)", re.I)
_PLACEHOLDER = re.compile(r"(?:\$\{|\{[\w.-]+\}|your[_ -]|placeholder|example|dummy|REDACTED|^<.*>$)", re.I)
_TOKEN = re.compile(r"\b(?:sk-(?:proj-|ant-|or-v1-)?[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[A-Z0-9]{16})\b")
_QUOTED = re.compile(r'''(?<![A-Za-z0-9_.-])(?P<prefix>["']?(?:[A-Za-z0-9_.-]{0,128}(?:api[_-]?key|token|secret|password|authorization|credential)[A-Za-z0-9_.-]{0,128})["']?\s*[:=]\s*)(?P<quote>["'])(?P<value>[^\n]*?)(?P=quote)''', re.I)
_ENV_LINE = re.compile(r"(?m)^(?P<prefix>\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)(?P<value>[^\s\"'\n]+)")
_QUERY = re.compile(r"([?&](?:api[_-]?key|key|token|access_token|refresh_token|auth|secret|password)=)[^&#\s\"']+", re.I)


def secret_name(name):
    return bool(_SECRET_NAME.search(str(name))) or str(name).upper().endswith("_KEY")


def register_secrets(values):
    for value in values:
        if isinstance(value, str) and len(value) >= 8 and not _PLACEHOLDER.search(value):
            _REGISTERED.add(value)
            if value.lower().startswith(("bearer ", "key ", "token ")):
                _REGISTERED.add(value.split(None, 1)[1])


@lru_cache(maxsize=16)
def _file_secrets(path, stamp):
    try:
        p = Path(path)
        if p.name == ".env" or p.name.startswith(".env."):
            from dotenv import dotenv_values
            return tuple(v for k, v in dotenv_values(p).items() if secret_name(k) and v)
        data = json.loads(p.read_text())
        values = []
        for config in data.values():
            if not isinstance(config, dict):
                continue
            values.extend(v for k, v in config.get("env", {}).items() if secret_name(k))
            values.extend(v for k, v in config.get("headers", {}).items() if k.lower() not in ("accept", "content-type", "user-agent"))
        return tuple(values)
    except (OSError, ValueError, TypeError, AttributeError):
        return ()


def secret_values():
    values = {v for k, v in os.environ.items() if secret_name(k)} | _REGISTERED
    for path in (Path.home() / ".kurt/.env", Path.cwd() / ".env", Path.home() / ".kurt/mcp_connections.json"):
        try:
            values.update(_file_secrets(str(path), path.stat().st_mtime_ns))
        except OSError:
            pass
    result = set()
    for value in values:
        if not isinstance(value, str) or len(value) < 8 or _PLACEHOLDER.search(value):
            continue
        result.add(value)
        if value.lower().startswith(("bearer ", "key ", "token ")):
            result.add(value.split(None, 1)[1])
    return result


def _redact_text(text):
    values = set()
    for value in secret_values():
        values.update((value, quote(value, safe=""), quote_plus(value), json.dumps(value)[1:-1],
                       base64.b64encode(value.encode()).decode()))
    for value in sorted(values, key=len, reverse=True):
        text = text.replace(value, MASK)
    text = _TOKEN.sub(lambda m: m[0] if _PLACEHOLDER.search(m[0]) else MASK, text)
    text = _QUERY.sub(lambda m: m[1] + MASK, text)
    text = re.sub(r"(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", text)
    def quoted(match):
        value = match["value"]
        # Keep references and instructional placeholders usable in code snippets.
        if not value or _PLACEHOLDER.search(value):
            return match[0]
        return match["prefix"] + match["quote"] + MASK + match["quote"]
    text = _QUOTED.sub(quoted, text)
    text = _ENV_LINE.sub(lambda m: m["prefix"] + MASK if secret_name(m["name"]) and not _PLACEHOLDER.search(m["value"]) else m[0], text)
    return text


def redact(value):
    """Return a sanitized copy. Never use this for actual auth headers/config saves."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact(v) for v in value)
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if secret_name(key) and isinstance(item, str) and item and not _PLACEHOLDER.search(item):
                result[key] = MASK
            elif str(key).lower() == "headers" and isinstance(item, dict):
                result[key] = {k: MASK if k.lower() not in ("accept", "content-type", "user-agent") and isinstance(v, str) and v and not _PLACEHOLDER.search(v) else redact(v) for k, v in item.items()}
            else:
                result[key] = redact(item)
        return result
    return value


def sensitive_path(path):
    p = Path(path).expanduser()
    names = (p.name.lower(), p.resolve().name.lower())
    for name in names:
        if (name.startswith(".env") or name.endswith(".env")) and not name.endswith((".example", ".sample", ".template")):
            return True
        if name in {".npmrc", ".pypirc", ".netrc", ".git-credentials", "credentials", "credentials.json",
                    "secrets.json", "secrets.yaml", "secrets.yml", "auth.json", ".credentials.json", "auth-profiles.json", "mcp_connections.json", "memory.db", "control.db",
                    "id_rsa", "id_ed25519", "id_ecdsa"} or name.endswith((".pem", ".key", ".p12", ".pfx", ".tfstate", ".kurt-token")):
            return True
    return any(part.lower() in {".kurt", ".codex", ".claude", ".gemini", ".openclaw", ".aws", ".ssh", ".gnupg", ".openclaw-kurt", ".kurt-saas"} for part in p.resolve().parts)


def require_public_file(path):
    if sensitive_path(path):
        raise ValueError("Credential/private state files are excluded from AI file tools. Use configured-status checks instead.")


_BASE_ENV = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TMP", "TEMP", "TERM", "COLORTERM",
             "NO_COLOR", "LANG", "LANGUAGE", "TZ", "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY",
             "SYSTEMROOT", "SystemRoot", "COMSPEC", "ComSpec", "PATHEXT", "WINDIR", "APPDATA", "LOCALAPPDATA"}


def child_env(allow=(), extra=None, source=None):
    """Only base OS variables plus explicitly allowed credentials reach a child."""
    source = os.environ if source is None else source
    allowed = _BASE_ENV | set(allow)
    result = {k: v for k, v in source.items() if k in allowed or k.startswith("LC_")}
    if extra:
        result.update(extra)  # MCP's explicit per-server env is an intentional grant.
    return result


def write_private_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".private-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def require_secure_endpoint(url):
    """Remote credentials require TLS; HTTP is allowed for literal loopback only."""
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1"))
        if not valid or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise ValueError
        parsed.port  # Reject invalid port syntax before making any request.
    except (ValueError, TypeError):
        raise ValueError("Use an HTTPS endpoint without URL userinfo; plain HTTP is allowed only on literal loopback hosts.") from None
