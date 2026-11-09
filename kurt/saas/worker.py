"""Fixed entrypoint in the approved offline image; no shell/MCP/desktop tools."""
import json
import sys
from .protocol import MAX_BODY, MAX_OUTPUT, decode, native_request, scrub


def process(raw):
    request = native_request(decode(raw))
    from kurt.capabilities.runtime import run_capability
    result = run_capability(request["capability_id"], rows=request["rows"])
    encoded = json.dumps(scrub(result), ensure_ascii=False, allow_nan=False).encode()
    if len(encoded) > MAX_OUTPUT:
        raise ValueError("Result exceeds output limit")
    return encoded


def main():
    import signal
    signal.alarm(65)  # Bounds an orphaned job if its supervisor crashes.
    try:
        encoded = process(sys.stdin.buffer.read(MAX_BODY + 1))
        sys.stdout.buffer.write(encoded)
    except Exception:
        # Dataset values and stack traces are not written to supervisor logs.
        sys.stdout.write('{"error":"native_request_failed"}')
        raise SystemExit(1)


if __name__ == "__main__":
    main()
