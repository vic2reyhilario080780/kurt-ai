"""Observed desktop actions: one model decision, local targeting and readback."""

from urllib.parse import urlsplit, unquote
from pathlib import Path
import sys
import time
import re

from kurt.core.cli_tools import run_cli


def desktop_host_flags(app):
    # The bridge normalizes Chromium AX titles differently from its window
    # context and rejects its own evidence. Caller-local execution keeps both
    # receipts and actions on one provider, with normal permission validation.
    chromium = {'chrome', 'google chrome', 'com.google.chrome', 'chromium', 'org.chromium.chromium',
                'edge', 'microsoft edge', 'com.microsoft.edgemac', 'brave', 'brave browser',
                'com.brave.browser', 'opera', 'com.operasoftware.opera', 'vivaldi',
                'com.vivaldi.vivaldi', 'arc', 'company.thebrowser.browser'}
    return ["--no-remote"] if app.casefold() in chromium else []


def ensure_chromium_accessibility(app):
    """Activate the running browser's AX tree, never OS permission prompts."""
    if not desktop_host_flags(app) or sys.platform != 'darwin':
        return {"status": "not_required"}
    try:
        import ApplicationServices as AX
        from AppKit import NSWorkspace
    except ImportError:
        return {"status": "unavailable", "reason": "Install kurt-ai[desktop] for Chromium accessibility activation."}
    aliases = {'chrome': 'com.google.chrome', 'google chrome': 'com.google.chrome',
               'edge': 'com.microsoft.edgemac', 'microsoft edge': 'com.microsoft.edgemac'}
    identity = app.casefold()
    bundle = aliases.get(identity, identity)
    matches = [candidate for candidate in NSWorkspace.sharedWorkspace().runningApplications()
               if str(candidate.bundleIdentifier()).casefold() == bundle
               or str(candidate.localizedName()).casefold() == identity]
    if len(matches) != 1:
        return {"status": "unavailable", "reason": "Exactly one running browser process is required."}
    target = AX.AXUIElementCreateApplication(matches[0].processIdentifier())
    error, enabled = AX.AXUIElementCopyAttributeValue(target, 'AXEnhancedUserInterface', None)
    if error == 0 and enabled is True:
        return {"status": "enabled"}
    status = AX.AXUIElementSetAttributeValue(target, 'AXEnhancedUserInterface', True)
    # Chromium can return an AX error while applying the change. Read back the
    # attribute rather than treating either the return code or dispatch as proof.
    error, enabled = AX.AXUIElementCopyAttributeValue(target, 'AXEnhancedUserInterface', None)
    return {"status": "enabled" if error == 0 and enabled is True else "unavailable",
            "set_code": int(status), "read_code": int(error)}


def observation_flags(app):
    flags = desktop_host_flags(app)
    return [*flags, '--fresh', '--depth', '50', '--max-elements', '500', '--max-children', '100'] if flags else []


def observe(app, window_id=None):
    accessibility = ensure_chromium_accessibility(app)
    args = ["see", "--app", app, "--json", *observation_flags(app)]
    if window_id is not None:
        args += ["--window-id", str(window_id)]
    result = run_cli("peekaboo", args, timeout=30)
    payload = result.data or {}
    data = payload.get("data") or {}
    receipt = payload.get("target_receipt") or {}
    elements = data.get("ui_elements", [])
    return {
        "status": result.status, "app": app,
        "window_id": receipt.get("window_id"), "window_title": data.get("window_title"),
        "snapshot_id": data.get("snapshot_id"), "is_dialog": data.get("is_dialog", False),
        "elements": [{k: e[k] for k in ("id", "role", "label", "value", "is_actionable", "is_value_settable") if k in e}
                     for e in elements if e.get("is_actionable") or e.get("value")],
        "error": payload.get("error") or result.stderr,
        "accessibility": accessibility,
    }


def _matches_browser_url(observation, url):
    expected = urlsplit(url)
    for element in observation.get('elements', []):
        label = element.get('label', '').casefold()
        if element.get('role') != 'textField' or label not in {'address and search bar', 'smart search field', 'search or enter website name'}:
            continue
        value = str(element.get('value', '')).strip()
        if expected.scheme == 'file':
            actual = urlsplit(value).path if value.startswith('file:') else value
            if actual.startswith('/') and Path(unquote(actual)).resolve() == Path(unquote(expected.path)).resolve():
                return True
        elif value.rstrip('/') == url.rstrip('/'):
            return True
    return False


def _opened_window(app, url=None):
    observed = observe(app)
    for _ in range(2):
        if observed.get('status') == 'completed' and observed.get('window_id'):
            break
        time.sleep(.15)  # Re-observe readiness; never repeat the launch.
        observed = observe(app)
    if not url or _matches_browser_url(observed, url):
        return observed
    # Chrome may leave its profile picker as the key window while opening the
    # URL in an existing Guest/profile window. Find the actual address match.
    inventory = run_cli('peekaboo', ['window', 'list', '--app', app, '--json', *desktop_host_flags(app)], timeout=30)
    windows = ((inventory.data or {}).get('data') or {}).get('windows', [])
    candidates = [w for w in windows if w.get('window_id') and w.get('window_id') != observed.get('window_id')
                  and w.get('observation_capability') != 'pixels_only']
    for window in candidates[:12]:
        candidate = observe(app, window['window_id'])
        if candidate.get('status') == 'completed' and _matches_browser_url(candidate, url):
            return candidate
    return observed


def desktop_action(action, app="Safari", url=None, element=None, text=None, window_id=None,
                   key=None, direction=None, amount=3):
    if action not in {"open_app", "open_url", "observe", "fill", "click", "press", "scroll", "move"}:
        raise ValueError("Use open_app, open_url, observe, fill, click, press, scroll or move.")
    if not isinstance(app, str) or not app.strip() or app.startswith("-"):
        raise ValueError("A named app is required.")
    if window_id is not None and (type(window_id) is not int or window_id <= 0):
        raise ValueError("window_id must be a positive integer.")
    if action == "press":
        # One explicit chord per decision, never CLI options or key sequences.
        parts = key.casefold().split('+') if isinstance(key, str) else []
        modifiers = {'cmd', 'command', 'shift', 'option', 'alt', 'ctrl', 'control', 'fn'}
        keys = r'(?:[a-z0-9]|f(?:[1-9]|1[0-2])|return|tab|escape|delete|backspace|forwarddelete|left|right|up|down|space|home|end|pageup|pagedown)'
        if not parts or len(parts) > 5 or any(p not in modifiers for p in parts[:-1]) or not re.fullmatch(keys, parts[-1]):
            raise ValueError("Provide one key chord, such as Return or cmd+l.")
    if action == "scroll" and (direction not in {'up', 'down', 'left', 'right'} or type(amount) is not int or not 1 <= amount <= 20):
        raise ValueError("Scroll needs up/down/left/right and an integer amount from 1 to 20.")
    if action in {"open_app", "open_url"}:
        if action == "open_url" and (not isinstance(url, str) or urlsplit(url).scheme not in {"https", "http", "file"}):
            raise ValueError("Provide an http, https or local file URL.")
        destination = ['--open', url] if action == 'open_url' else []
        result = run_cli("peekaboo", ["app", "launch", app, *destination,
                         "--foreground", "--wait-for-window", "--json", *desktop_host_flags(app)], timeout=30)
        # Opening is not retried: even timeout/failure may have changed the app.
        observed = _opened_window(app, url if action == 'open_url' else None)
        focus = None
        url_verified = action != 'open_url' or _matches_browser_url(observed, url)
        if result.status == 'completed' and url_verified and observed.get('status') == 'completed' and observed.get('window_id'):
            focus = run_cli('peekaboo', ['window', 'focus', '--app', app,
                            '--window-id', str(observed['window_id']), '--verify', '--space-switch',
                            '--json', *desktop_host_flags(app)], timeout=30)
            observed = observe(app, observed['window_id'])
        status = result.status
        if status == 'completed' and (focus is None or focus.status != 'completed' or observed.get('status') != 'completed'):
            status = 'failed'
        error = ((focus.data or {}).get('error') or focus.stderr) if focus and focus.status != 'completed' else None
        if not url_verified:
            error = 'The requested address was not verified in a browser window. Observe current state before retrying.'
        return {"status": status, "action": action, "observation": observed,
                "focus_verified": bool(focus and focus.status == 'completed'),
                "url_verified": url_verified if action == 'open_url' else None,
                "error": error or (result.data or {}).get("error") or result.stderr}
    before = observe(app, window_id)
    if action == "observe":
        return before
    if before["status"] != "completed" or not before["snapshot_id"] or not before["window_id"] or before["is_dialog"]:
        return {"status": "blocked", "reason": "A fresh exact non-dialog window is required.", "observation": before}
    flags = ["--app", app, "--window-id", str(before["window_id"]), "--foreground", "--json", *desktop_host_flags(app)]
    if action in {"press", "scroll"}:
        args = (["press", key] if action == "press" else
                ["scroll", "--direction", direction, "--amount", str(amount)])
        dispatched = run_cli("peekaboo", [*args, "--snapshot", before["snapshot_id"], *flags], timeout=30)
        return {"status": "observed_after_action", "action": action, "dispatch_status": dispatched.status,
                "error": (dispatched.data or {}).get("error") or dispatched.stderr,
                "observation": observe(app, before["window_id"]),
                "note": "Sent once. Verify the requested effect; dispatch alone is not success."}
    if not isinstance(element, str) or not element.strip():
        raise ValueError(f"{action} requires the 'element' parameter: a nonempty exact observed element label.")
    candidates = [e for e in before["elements"]
                  if e.get("label", "").casefold() == element.casefold() and e.get("is_actionable")]
    if action == "fill":
        if not isinstance(text, str) or not text or len(text) > 4000 or any(ord(c) < 32 or ord(c) == 127 for c in text):
            raise ValueError("Fill requires single-line text (1–4000 characters).")
        candidates = [e for e in candidates if e.get("role") == "textField" and e.get("is_value_settable")]
    if len(candidates) != 1:
        return {"status": "blocked", "reason": "Element label must match exactly one actionable target.", "observation": before}
    target = candidates[0]
    if action == "move":
        moved = run_cli("peekaboo", ["move", "--on", target["id"], "--snapshot", before["snapshot_id"], *flags], timeout=30)
        return {"status": "observed_after_action", "action": action, "dispatch_status": moved.status,
                "error": (moved.data or {}).get("error") or moved.stderr,
                "observation": observe(app, before["window_id"]),
                "note": "Pointer moved once to the observed element; inspect any hover effect before continuing."}
    clicked = run_cli("peekaboo", ["click", "--on", target["id"], "--snapshot", before["snapshot_id"], *flags], timeout=30)
    if action == "click":
        after = observe(app, before["window_id"])
        return {"status": "observed_after_action", "dispatch_status": clicked.status,
                "action": action, "observation": after,
                "note": "Check the requested effect in this fresh observation; dispatch alone is not success."}
    # Verify the actual receiver after focus. Do not type into an unknown field.
    focus_result = run_cli("peekaboo", ["see", "--app", app, "--window-id", str(before["window_id"]), "--json", *observation_flags(app)], timeout=30)
    focus = ((focus_result.data or {}).get("data") or {}).get("focused_element") or {}
    if focus_result.status != "completed" or focus.get("role") != "AXTextField" or focus.get("title", "").casefold() != element.casefold():
        return {"status": "blocked", "reason": "The intended input does not hold focus; no text sent."}
    # Peekaboo interprets backslash escapes; preserve literal user text instead
    # of accidentally turning a backslash-n into Return/form submission.
    # Real key events keep the browser DOM and framework input handlers in sync;
    # AX value assignment alone can look correct while Enter reads an empty input.
    typed = run_cli("peekaboo", ["type", "--text", text.replace("\\", "\\\\"), "--clear",
                               "--input-strategy", "synthOnly", *flags], timeout=30)
    after = observe(app, before["window_id"])
    matches = [e for e in after["elements"] if e.get("role") == "textField" and e.get("label", "").casefold() == element.casefold()]
    verified = after["status"] == "completed" and len(matches) == 1 and matches[0].get("value") == text
    return {"status": "verified" if verified else "unverified", "action": action,
            "dispatch_status": typed.status, "observation": after,
            "note": "Text sent at most once; use observed value before deciding on another action."}
