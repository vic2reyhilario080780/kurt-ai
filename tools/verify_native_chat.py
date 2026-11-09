"""Opt-in real model smoke test using only synthetic data (no account mutations)."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import httpx

from kurt.capabilities.bridge import NativeToolRouter
from kurt.capabilities.runtime import example
from kurt.core.router import ModelRouter
from kurt.utils.env_loader import load_env


async def verify(model="openai/gpt-oss-120b"):
    load_env()
    router = ModelRouter()
    if not router._has_key("groq"):
        raise RuntimeError("A configured Groq key is required for this smoke test.")
    with tempfile.TemporaryDirectory(prefix="kurt-native-live-") as directory:
        data = Path(directory) / "orders.json"
        data.write_text(json.dumps(example("kurt-plugin--shopee-orders--gross_sales--describe")))
        messages = [{"role": "user", "content": (
            f'Kurt, analyze mo ang gross_sales ng Shopee orders sa "{data}". '
            'Inspect the input, find the native descriptive-statistics workflow, inspect its contract, '
            'then actually run it and summarize the computed total and row count. '
            'This is synthetic test data; do not use live apps or invent measurements.'
        )}]
        tools = []
        bridge = NativeToolRouter(router, on_tool=tools.append)
        try:
            answer = ''.join([part async for part in bridge.route("groq", model, messages)])
        except httpx.HTTPStatusError as exc:
            return {"tested_at": datetime.now(timezone.utc).isoformat(), "provider": "groq", "model": model,
                    "status": "unavailable", "http_status": exc.response.status_code,
                    "retry_after": exc.response.headers.get("retry-after"), "tools": tools,
                    "data": "synthetic fixture only", "external_app_actions": False}
        reports = []
        for message in messages:
            if message.get("role") == "user" and message["content"].startswith("NATIVE TOOL RESULT ("):
                value = json.loads(message["content"].split("\n", 1)[1])
                if isinstance(value, dict) and value.get("status") == "completed":
                    reports.append(value["steps"][-1]["report"] if value["kind"] == "agent" else value["report"])
        passed = "run_native" in tools and any(r["input_rows"] == 8 and isinstance(r["result"], dict) and r["result"].get("sum") == 1160 for r in reports)
        return {"tested_at": datetime.now(timezone.utc).isoformat(), "provider": "groq", "model": model,
                "status": "passed" if passed else "failed", "tools": tools, "expected_rows": 8, "expected_sum": 1160,
                "answer": answer, "data": "synthetic fixture only", "external_app_actions": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow requests to the configured Groq model")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to opt into real model API calls.")
    report = asyncio.run(verify(args.model))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] != "passed":
        raise SystemExit(1)
