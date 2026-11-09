"""On-demand discovery and execution for native skills, plugins and agents."""

from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path

from .authoring import PACK_DIR
from .engine import analyze, load_rows, sample_rows

STATE_PATH = Path.home() / ".kurt" / "native_capabilities.json"


def enabled(identity):
    if not STATE_PATH.exists():
        return True
    state = json.loads(STATE_PATH.read_text())
    if not isinstance(state, dict) or any(not isinstance(v, bool) for v in state.values()):
        raise ValueError("Invalid native capability settings.")
    return state.get(identity, True)


def set_enabled(identity, value):
    get_capability(identity)
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    if not isinstance(state, dict):
        raise ValueError("Invalid native capability settings.")
    state[identity] = bool(value)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    import os
    fd, temporary = tempfile.mkstemp(dir=STATE_PATH.parent, prefix=".native-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream)
        os.replace(temporary, STATE_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _require_enabled(identity):
    if not enabled(identity):
        raise ValueError(f"Native capability is disabled: {identity}")


@lru_cache(maxsize=1)
def manifest():
    with gzip.open(PACK_DIR / "manifest.json.gz", "rt") as stream:
        return json.load(stream)


@lru_cache(maxsize=8)
def domain_pack(domain):
    if domain not in {e["domain"] for e in manifest()["index"]}:
        raise ValueError("Unknown native dataset contract.")
    filename = domain + ".json.gz"
    raw = (PACK_DIR / filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest()["files"].get(filename):
        raise ValueError("Native pack integrity check failed.")
    return json.loads(gzip.decompress(raw))


def get_capability(identity):
    parts = identity.split("--")
    if len(parts) != 4 or parts[0] not in ("kurt-skill", "kurt-agent", "kurt-plugin"):
        raise ValueError("Unknown native capability ID. Use kurt library search.")
    pack = domain_pack(parts[1])
    item = next((e for e in pack["items"] if e["id"] == identity), None)
    if item is None:
        raise ValueError("Unknown native capability ID. Use kurt library search.")
    # Return a copy so callers cannot mutate cached definitions.
    result = json.loads(json.dumps(item))
    result["enabled"] = enabled(identity)
    return result


def search(query="", kind=None, limit=20):
    if kind and kind not in ("skill", "agent", "plugin"):
        raise ValueError("Kind must be skill, agent or plugin.")
    if not isinstance(limit, int) or limit < 1 or limit > 30_000:
        raise ValueError("Search limit must be between 1 and 30,000.")
    words = query.casefold().split()
    output = []
    for entry in manifest()["index"]:
        if kind and entry["kind"] != kind:
            continue
        if all(w in (entry["id"] + " " + entry["name"] + " " + entry["description"]).casefold() for w in words):
            output.append(dict(entry))
            if len(output) >= limit:
                break
    return output


def run_capability(identity, rows=None, input_path=None):
    item = get_capability(identity)
    _require_enabled(identity)
    if input_path is not None and rows is not None:
        raise ValueError("Provide either records or an input file, not both.")
    if input_path is not None:
        rows = load_rows(input_path)
    pack = domain_pack(item["domain"])
    profile = pack["profile"]
    if item["kind"] == "agent":
        reports = []
        for step in item["steps"]:
            plugin = get_capability(step["plugin"])
            try:
                _require_enabled(plugin["id"])
                report = analyze(rows, profile, plugin["metric"], plugin["method"])
            except ValueError as exc:
                return {"id": identity, "kind": "agent", "status": "blocked_input", "steps": reports,
                        "reason": str(exc), "failed_step": step["id"]}
            reports.append({"step": step["id"], "plugin": plugin["id"], "report": report})
            if step["id"] == "audit" and item["method"] != "quality":
                blocking = [i for i in report["result"]["issues"] if i["issue"] != "repeated_entity"]
                if blocking:
                    return {"id": identity, "kind": "agent", "status": "blocked_input", "steps": reports,
                            "reason": "Audit found missing or invalid measurements/entities; no analysis was run."}
        return {"id": identity, "kind": "agent", "status": "completed", "steps": reports,
                "execution": "deterministic declared plan; no LLM inference"}
    if item["kind"] == "skill":
        _require_enabled(item["plugin"])
    result = analyze(rows, profile, item["metric"], item["method"])
    return {"id": identity, "kind": item["kind"], "status": "completed", "report": result,
            "execution": "bound native plugin" if item["kind"] == "skill" else "native operation"}


def example(identity):
    item = get_capability(identity)
    return sample_rows(domain_pack(item["domain"])["profile"])


def verify_library():
    """Exercise every recipe and check operation-specific known fixture facts.

    This proves wiring and deterministic behavior, not subjective AI quality.
    """
    counts = {"skill": 0, "agent": 0, "plugin": 0}
    errors = []
    seen = set()
    for entry in manifest()["index"]:
        identity = entry["id"]
        try:
            if identity in seen:
                raise ValueError("Duplicate ID")
            seen.add(identity)
            item = get_capability(identity)
            if item["entrypoint"] != "kurt.capabilities.runtime:run_capability":
                raise ValueError("Invalid entrypoint")
            if item["kind"] in ("skill", "agent") and len(item.get("system_prompt", "").split()) < 200:
                raise ValueError("Missing substantive instructions")
            if item["kind"] == "skill":
                if get_capability(item["plugin"])["kind"] != "plugin":
                    raise ValueError("Invalid bound plugin")
            result = run_capability(identity, rows=example(identity))
            if result["status"] != "completed":
                raise ValueError("Fixture did not complete")
            report = result["steps"][-1]["report"] if item["kind"] == "agent" else result["report"]
            _check_fixture(report)
            json.dumps(result, allow_nan=False)
            counts[item["kind"]] += 1
        except Exception as exc:
            errors.append({"id": identity, "error": str(exc)})
    return {"counts": counts, "total_executed": sum(counts.values()), "errors": errors,
            "manifest_sha256": hashlib.sha256((PACK_DIR / "manifest.json.gz").read_bytes()).hexdigest(),
            "coverage": "All entries: local fixture execution, references, prompt length, output facts and serialization. No model/API calls.",
            "scope": manifest()["scope"]}


def _check_fixture(report):
    method, result = report["method"], report["result"]
    def check(condition):
        if not condition:
            raise ValueError("Computed output differs from independently specified fixture facts.")

    if report["input_rows"] != 8:
        raise ValueError("Wrong fixture row count")
    if method == "describe":
        check(result["sum"] == 1160 and result["mean"] == 145 and result["median"] == 25)
    elif method == "quality":
        check(result["issue_count"] == 0)
    elif method == "group":
        check([r["sum"] for r in result] == [90, 1070])
    elif method == "trend":
        check(len(result) == 8 and result[-1]["change"] == 950)
    elif method == "rank":
        check(result[0]["entity"] == "record-8" and result[-1]["value"] == 0)
    elif method == "outliers":
        check([r["value"] for r in result["flagged"]] == [1000])
    elif method == "histogram":
        check([r["count"] for r in result] == [7, 0, 0, 0, 1])
    elif method == "contribution":
        check(result["total"] == 1160 and abs(sum(r["share_percent"] for r in result["records"]) - 100) < 1e-10)
    elif method == "normalize":
        check(result[0]["min_max"] == 0 and result[-1]["min_max"] == 1)
    elif method == "changes":
        check(result[1]["percent_change"] is None and result[-1]["change"] == 950)
