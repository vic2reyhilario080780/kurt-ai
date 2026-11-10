"""Opt-in live natural-language desktop test through Kurt's actual ask CLI."""

import argparse
from datetime import datetime, timezone
from html import escape
import json
import plistlib
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

from kurt.core.cli_tools import run_cli
from kurt.core.desktop_actions import observation_flags
from kurt.utils.security import redact


def installed_browsers():
    """Discover installed top-level apps registered to handle web URLs."""
    browsers = []
    for folder in (Path('/Applications'), Path('/System/Applications'), Path.home() / 'Applications'):
        for app in sorted(folder.glob('*.app')):
            try:
                info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
                schemes = {scheme for item in info.get('CFBundleURLTypes', [])
                           for scheme in item.get('CFBundleURLSchemes', [])}
                if {'http', 'https'} & schemes:
                    browsers.append(app.stem)
            except (OSError, ValueError):
                continue
    return sorted(set(browsers))


def verify(input_label="Test message", button_label="Verify control", browser="Safari"):
    token = "KURT_AUTO_" + uuid.uuid4().hex[:8].upper()
    root = Path(tempfile.mkdtemp(prefix="kurt-autonomy-"))
    page = root / "control.html"
    page.write_text(('''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Kurt Autonomous Browser Test</title>
<style>body{font:24px system-ui;padding:60px;background:#edf5ff}input,button{font:24px system-ui;padding:16px;margin:12px}output{display:block;padding:20px}</style>
<h1>Kurt Autonomous Browser Test</h1><p>Local browser control test.</p>
<label>INPUT_LABEL <input aria-label="INPUT_LABEL"></label>
<button onclick="document.querySelector('output').textContent='AUTONOMOUS_OK: '+document.querySelector('input').value">BUTTON_LABEL</button>
<output aria-live="polite">Waiting for Kurt</output></html>''').replace('INPUT_LABEL', escape(input_label)).replace('BUTTON_LABEL', escape(button_label)), encoding="utf-8")
    prompt = (
        f'Kurt, buksan mo ang {browser} at pumunta sa {page.as_uri()}. '
        f'Ilagay ang "{token}" sa "{input_label}", pindutin ang "{button_label}", '
        'at i-check kung lumabas ang tamang AUTONOMOUS_OK result. '
        'Ikaw na ang gumawa sa desktop, huwag instructions lang. '
        f'Local test page lang ito; puwede mong i-focus ang {browser}. '
        'Huwag galawin ang ibang apps, accounts o files. '
        'Kapag may unverified action, tingnan muna ang kasalukuyang resulta bago umulit.'
    )
    try:
        process = subprocess.run(
            [sys.executable, "-m", "kurt.main", "ask", prompt, "--no-memory", "--verbose"],
            capture_output=True, text=True, timeout=240,
        )
        transcript = redact(process.stdout + process.stderr)
        exit_code = process.returncode
    except subprocess.TimeoutExpired as exc:
        transcript = redact((exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else exc.stdout or "")
        exit_code = None
    # Observe only after Kurt has finished. The verifier never performs the task.
    screenshot = root / "result.png"
    observation = run_cli("peekaboo", ["see", "--app", browser, "--path", str(screenshot), "--json", *observation_flags(browser)], timeout=30)
    data = (observation.data or {}).get("data") or {}
    values = [e.get("value") or e.get("label", "") for e in data.get("ui_elements", [])]
    expected = "AUTONOMOUS_OK: " + token
    verified = "Kurt Autonomous Browser Test" in (data.get("window_title") or "") and expected in values
    return {
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "browser": browser,
        "status": "passed" if verified and any(name in transcript for name in ("desktop_cli", "desktop_action")) else "failed",
        "entrypoint": "python -m kurt.main ask <natural-language request> --no-memory --verbose",
        "prompt": prompt, "cli_exit_code": exit_code,
        "expected_result": expected, "page_result_verified": verified,
        "observed_window": data.get("window_title"),
        "observed_result": [v for v in values if expected in v],
        "screenshot": str(screenshot),
        "transcript": transcript,
        "verification": "Independent read-only desktop observation; no task actions by verifier.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input-label", default="Test message")
    parser.add_argument("--button-label", default="Verify control")
    parser.add_argument("--browser", default="Safari")
    parser.add_argument("--all-installed", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to allow model requests and browser desktop actions.")
    if args.all_installed:
        browsers = installed_browsers()
        reports = []
        for browser in browsers:
            print(f'Testing {browser}...', flush=True)
            result = verify(args.input_label, args.button_label, browser)
            reports.append(result)
            print(f'{browser}: {result["status"]}', flush=True)
            if args.output:
                args.output.write_text(json.dumps({'status': 'running', 'installed_browsers': browsers, 'results': reports}, indent=2, ensure_ascii=False) + '\n')
        report = {'tested_at': datetime.now(timezone.utc).isoformat(), 'installed_browsers': browsers,
                  'status': 'passed' if reports and all(r['status'] == 'passed' for r in reports) else 'failed', 'results': reports}
    else:
        report = verify(args.input_label, args.button_label, args.browser)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "passed" else 1)
