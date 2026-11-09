"""Reproducible authoring of explicit domain/metric/operation specializations.

The pack contains 10,000 recipes per kind, not 30,000 unrelated algorithms.
All use a reviewed shared engine. Prompts and plans are saved in the pack;
runtime discovery does not fabricate instructions or download third-party code.
"""

import gzip
import hashlib
import json
from pathlib import Path

from .engine import METHODS
from .profiles import profiles

PACK_DIR = Path(__file__).parents[1] / "data" / "native_pack"
KINDS = ("skill", "agent", "plugin")


def capability_id(kind, domain, metric, method):
    return f"kurt-{kind}--{domain}--{metric}--{method}"


def skill_instructions(profile, metric, method):
    title, procedure = METHODS[method]
    plugin_id = capability_id("plugin", profile["id"], metric, method)
    return f"""You are Kurt's {profile['title']} specialist for {title.lower()} of {metric}.
Your concrete task is to transform the user's supplied records into a traceable report using
the native plugin {plugin_id}. This is a local data workflow. It does not access an app,
trade, publish, contact customers, change inventory, or update a remote system.

INPUT CONTRACT: accept a UTF-8 CSV with headers or a JSON array of record objects.
The measurement column is {metric}. The entity column is {profile['entity']}; the
group column is {profile['group']}; the time column is {profile['date']}. Require the
group column for group comparisons and the time column for temporal operations.
Use the user's actual export, not invented example values. If the file or relevant column
is unavailable, identify the missing input and stop the calculation. Numeric values must be
finite, with magnitude from 1e-100 to 1e100 or zero. Plain numeric strings from CSV are accepted.
Do not strip currency symbols, silently convert units, impute blanks, coerce booleans,
or drop inconvenient records. Ask the user to make ambiguous units or schemas explicit.

PROCEDURE: {procedure} Use run_native with capability_id set to {plugin_id}
and input_path set to the user's file. Alternatively use `kurt library run {plugin_id}
--input FILE`. Read the returned measurement name, input row count, result and notes.
If validation fails, report the specific input problem; do not manufacture an answer.
An entity identifier may recur across observations. Preserve source row numbers and review
repeated identifiers before removing any observations. Inputs remain unchanged.

OUTPUT: identify the dataset as {profile['title']}, state the measured field {metric},
give the operation and observed sample size, then present the computed findings. Clearly
separate numeric evidence from tentative explanations. Totals of rates, scores or ratios
are not business totals; disclose this whenever the selected metric has those semantics.
Observed associations do not establish causes, improvements, forecasts or statistical
significance. Explain missing periods, zero denominators and insufficient samples exactly
as the engine reports them. Do not claim a live {profile['title']} connection or fresh data.
Only write a separate output file when the user requests one. Conclude with specific data
questions supported by the result, rather than automatic business or financial decisions.
"""


def definition(kind, profile, metric, method):
    label, procedure = METHODS[method]
    domain = profile["id"]
    identity = capability_id(kind, domain, metric, method)
    plugin_id = capability_id("plugin", domain, metric, method)
    quality_id = capability_id("plugin", domain, metric, "quality")
    contract = {"format": ["csv", "json-records"], "metric": metric,
                "entity": profile["entity"], "group": profile["group"], "date": profile["date"],
                "required_columns": [metric, profile["entity"]] +
                    ([profile["group"]] if method == "group" else []) +
                    ([profile["date"]] if method in ("trend", "changes") else [])}
    base = {"id": identity, "name": f"{profile['title']}: {metric} / {label}",
            "kind": kind, "domain": domain, "metric": metric, "method": method,
            "description": f"{procedure} Dataset: {profile['title']}; field: {metric}.",
            "version": "1.0.0", "author": "Kurt native library", "builtin": True,
            "requirements": {"network": False, "api_keys": [], "packages": []},
            "input_contract": contract, "entrypoint": "kurt.capabilities.runtime:run_capability",
            "verification": "local_fixture", "enabled": True}
    if kind == "plugin":
        base.update({"handler": "kurt.capabilities.engine:analyze", "operation": method,
                     "capabilities": [method], "output": "descriptive JSON report",
                     "procedure": procedure})
    elif kind == "skill":
        base.update({"system_prompt": skill_instructions(profile, metric, method),
                     "plugin": plugin_id, "tools": ["run_native"]})
    else:
        steps = [{"id": "audit", "plugin": quality_id}]
        if method != "quality":
            steps.append({"id": "analysis", "plugin": plugin_id})
        base.update({"steps": steps, "tools": ["run_native"], "model": "inherit",
                     "agent_mode": "deterministic_workflow",
                     "stop_on": "invalid measurements or missing required inputs",
                     "system_prompt": skill_instructions(profile, metric, method) +
                     "\nAGENT PLAN: audit the selected measurement first. Preserve the audit output. "
                     "Stop calculation if a measurement or entity is missing/invalid. Repeated "
                     "entities are review notes and do not automatically block a run. Execute "
                     "the analysis step only after the audit passes. Keep both step reports "
                     "in the final result, include source row counts, and state completion "
                     "only after every required step returns a valid result. This agent follows "
                     "a declared plan; it does not claim autonomous LLM reasoning."})
    return base


def write_pack(destination=PACK_DIR):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    # An explicit 100-contract edition; remaining authored profiles can be added
    # in a later edition without silently inflating this edition's counts.
    selected = profiles()[:100]
    index = []
    files = {}
    for profile in selected:
        items = [definition(kind, profile, metric, method)
                 for kind in KINDS for metric in profile["metrics"] for method in METHODS]
        filename = profile["id"] + ".json.gz"
        content = json.dumps({"profile": profile, "items": items}, ensure_ascii=False, separators=(",", ":")).encode()
        packed = gzip.compress(content, mtime=0)
        (destination / filename).write_bytes(packed)
        files[filename] = hashlib.sha256(packed).hexdigest()
        index.extend({k: item[k] for k in ("id", "kind", "domain", "metric", "method", "name", "description")}
                     for item in items)
    manifest = {"format_version": 1, "edition": "kurt-native-data-1", "author": "Kurt native library",
                "counts": {kind: sum(e["kind"] == kind for e in index) for kind in KINDS},
                "domains": len(selected), "metric_contracts": sum(len(p["metrics"]) for p in selected),
                "operations": list(METHODS), "files": files,
                "scope": "Local numeric CSV/JSON data workflows. Domain specializations share ten algorithms.",
                "limitations": ["Not 30,000 distinct algorithms", "No external app connectivity",
                                "LLM reasoning quality is not verified by deterministic fixture tests",
                                "Skills require a model to interpret natural-language instructions; local run uses their bound plugin"],
                "index": index}
    (destination / "manifest.json.gz").write_bytes(gzip.compress(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))
    return manifest


if __name__ == "__main__":
    manifest = write_pack()
    print(json.dumps({k: manifest[k] for k in ("counts", "domains", "metric_contracts", "operations")}, indent=2))
