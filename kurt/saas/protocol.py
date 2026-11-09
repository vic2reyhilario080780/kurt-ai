"""Strict hosted request formats. No paths, commands, tools or tenant selectors."""
import json
import re

MAX_BODY = 512 * 1024
MAX_OUTPUT = 512 * 1024


def decode(raw):
    if len(raw) > MAX_BODY:
        raise ValueError("Request too large")
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError("Duplicate JSON field")
            obj[k] = v
        return obj
    def constant(_):
        raise ValueError("Non-finite JSON numbers are not allowed")
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError("An object is required")
    return value


def native_request(value):
    if set(value) != {"capability_id", "rows"}:
        raise ValueError("Expected capability_id and rows only")
    identity, rows = value["capability_id"], value["rows"]
    if not isinstance(identity, str) or len(identity) > 200 or not re.fullmatch(r"kurt-(?:skill|agent|plugin)--[a-z0-9-]+--[a-z0-9_-]+--[a-z0-9_-]+", identity):
        raise ValueError("Invalid native capability ID")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10_000:
        raise ValueError("Supply 1 to 10,000 records")
    if any(not isinstance(row, dict) or len(row) > 200 or any(not isinstance(k,str) for k in row) for row in rows):
        raise ValueError("Invalid records")
    return {"capability_id": identity, "rows": rows}


def chat_request(value):
    if set(value) != {"messages"} or not isinstance(value["messages"], list) or not 1 <= len(value["messages"]) <= 24:
        raise ValueError("Expected 1 to 24 messages only")
    total = 0
    for item in value["messages"]:
        if not isinstance(item, dict) or set(item) != {"role", "content"} or item["role"] not in ("user", "assistant") or not isinstance(item["content"], str):
            raise ValueError("Only text user/assistant messages are accepted")
        total += len(item["content"].encode())
    if total > 32768:
        raise ValueError("Message content exceeds 32 KiB")
    return value


def scrub(value, secrets=()):
    """Pure redaction: no reads from the desktop's home, env files or memory."""
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return re.sub(r"\b(?:sk-[\w-]{20,}|gsk_[\w-]{20,}|kurt_live_[\w-]{30,})\b", "[REDACTED]", value)
    if isinstance(value, list):
        return [scrub(item, secrets) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item, secrets) for key,item in value.items()}
    return value
