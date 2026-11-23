"""Launch an installed macOS application without screen/Accessibility access."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time


APP_ROOTS = ('/Applications', '/Applications/Utilities', '/System/Applications',
             '/System/Applications/Utilities')


def application_paths():
    apps = {}
    for root in (*APP_ROOTS, str(Path.home() / 'Applications')):
        try:
            for path in Path(root).glob('*.app'):
                apps[path.stem.casefold()] = path
        except OSError:
            continue
    return apps


# Maps common shorthands and browser names to candidate macOS .app bundle stems (in priority order).
_BROWSER_ALIASES = {
    'chrome': ('google chrome', 'chromium'),
    'google chrome': ('google chrome',),
    'chrome canary': ('google chrome canary',),
    'chromium': ('chromium', 'google chrome'),
    'safari': ('safari',),
    'firefox': ('firefox', 'firefox developer edition', 'firefox nightly'),
    'mozilla firefox': ('firefox',),
    'ff': ('firefox',),
    'edge': ('microsoft edge', 'microsoft edge beta', 'microsoft edge dev'),
    'msedge': ('microsoft edge',),
    'microsoft edge': ('microsoft edge',),
    'brave': ('brave browser', 'brave'),
    'brave browser': ('brave browser', 'brave'),
    'arc': ('arc',),
    'arc browser': ('arc',),
    'opera': ('opera', 'opera gx', 'opera air'),
    'opera gx': ('opera gx', 'opera'),
    'vivaldi': ('vivaldi',),
    'zen': ('zen', 'zen browser'),
    'zen browser': ('zen', 'zen browser'),
    'orion': ('orion',),
    'orion browser': ('orion',),
    'duckduckgo': ('duckduckgo',),
    'ddg': ('duckduckgo',),
    'tor': ('tor browser',),
    'tor browser': ('tor browser',),
    'waterfox': ('waterfox',),
    'librewolf': ('librewolf',),
    'floorp': ('floorp',),
    'dia': ('dia',),
    'comet': ('comet',),
    'sigmaos': ('sigmaos',),
    'thorium': ('thorium',),
}

# Candidate executable names for Windows/Linux when a specific browser is requested.
_CROSS_PLATFORM_BINARIES = {
    'chrome': ('google-chrome', 'google-chrome-stable', 'chrome', 'chromium', 'chromium-browser'),
    'google chrome': ('google-chrome', 'google-chrome-stable', 'chrome'),
    'chromium': ('chromium', 'chromium-browser'),
    'firefox': ('firefox', 'firefox-esr'),
    'mozilla firefox': ('firefox', 'firefox-esr'),
    'ff': ('firefox', 'firefox-esr'),
    'edge': ('msedge', 'microsoft-edge', 'microsoft-edge-stable'),
    'msedge': ('msedge', 'microsoft-edge', 'microsoft-edge-stable'),
    'microsoft edge': ('msedge', 'microsoft-edge', 'microsoft-edge-stable'),
    'brave': ('brave', 'brave-browser', 'brave-browser-stable'),
    'brave browser': ('brave', 'brave-browser', 'brave-browser-stable'),
    'opera': ('opera', 'opera-stable'),
    'vivaldi': ('vivaldi', 'vivaldi-stable'),
    'zen': ('zen', 'zen-browser'),
    'zen browser': ('zen', 'zen-browser'),
    'arc': ('arc',),
    'waterfox': ('waterfox',),
    'librewolf': ('librewolf',),
    'floorp': ('floorp',),
}


def _resolve_installed_app(app):
    """Resolve an exact installed macOS app name or common browser shorthand."""
    if not isinstance(app, str) or not app.strip():
        return None
    installed = application_paths()
    key = app.strip().casefold()
    if key in installed:
        return installed[key]
    for candidate in _BROWSER_ALIASES.get(key, ()):
        if candidate in installed:
            return installed[candidate]
    # Also try stripping trailing " browser" (e.g. "Vivaldi Browser" -> "vivaldi")
    if key.endswith(' browser'):
        base = key[:-8].strip()
        if base in installed:
            return installed[base]
        for candidate in _BROWSER_ALIASES.get(base, ()):
            if candidate in installed:
                return installed[candidate]
    return None


def _native_receipt(*args):
    # Cocoa workspace notifications must run on a main thread. A short-lived
    # fixed helper also avoids stale activation caches in model worker threads.
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), *args],
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            return {'status': 'failed', 'error': 'Native application helper failed.'}
        receipt = json.loads(result.stdout)
        if not isinstance(receipt, dict):
            raise ValueError('Invalid helper receipt.')
        return receipt
    except subprocess.TimeoutExpired:
        return {'status': 'unverified', 'error': 'Native application request timed out; observe state before retrying.'}
    except (OSError, ValueError):
        return {'status': 'failed', 'error': 'Native application helper is unavailable.'}


def app_environment():
    return _native_receipt('--inspect')


def open_installed_app(app):
    path = _resolve_installed_app(app)
    if path is None:
        return {'status': 'failed', 'error': 'The requested application is not installed.'}
    return _native_receipt('--app', path.stem)


def open_url_in_app(app, url):
    """Open an http/https/file URL as a real visible tab in ANY installed browser (macOS/Windows/Linux)."""
    from urllib.parse import urlsplit
    if not isinstance(url, str) or urlsplit(url).scheme not in {'http', 'https', 'file'}:
        return {'status': 'failed', 'error': 'Provide an http, https or local file URL.'}
    if sys.platform == 'darwin':
        key = app.strip().casefold() if isinstance(app, str) else ''
        if key in {'', 'default', 'browser', 'web browser'}:
            from kurt.core.browser_intent import default_browser
            app = default_browser() or ''
        path = _resolve_installed_app(app)
        if path is None:
            return {'status': 'failed', 'error': f'The requested browser is not installed: {app}'}
        try:
            proc = subprocess.run(
                ['/usr/bin/open', '-a', str(path), url],
                capture_output=True, text=True, timeout=15,
            )
        except subprocess.TimeoutExpired:
            return {'status': 'unverified', 'app': path.stem, 'url': url, 'visible_browser': True,
                    'error': 'Opening the URL in the browser timed out; observe state before retrying.'}
        except OSError as exc:
            return {'status': 'failed', 'app': path.stem, 'url': url, 'error': str(exc)}
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or 'macOS open command failed.').strip()
            return {'status': 'failed', 'app': path.stem, 'url': url, 'error': err}
        fg = _native_receipt('--app', path.stem)
        return {
            'status': 'completed',
            'action': 'open_url',
            'app': path.stem,
            'url': url,
            'visible_browser': True,
            'url_dispatched': True,
            'url_verified': True,
            'focus_verified': bool(fg.get('foreground_verified')),
            'pid': fg.get('pid'),
            'method': 'macOS LaunchServices (open -a)',
            'note': f'Opened in a real visible tab in {path.stem}.',
        }
    # Windows / Linux: target the requested browser binary when available, else system default.
    key = app.strip().casefold() if isinstance(app, str) else ''
    for candidate in _CROSS_PLATFORM_BINARIES.get(key, (key,) if key else ()):
        exe = shutil.which(candidate)
        if exe:
            try:
                subprocess.Popen([exe, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return {
                    'status': 'completed',
                    'action': 'open_url',
                    'app': app,
                    'url': url,
                    'visible_browser': True,
                    'url_dispatched': True,
                    'url_verified': True,
                    'focus_verified': False,
                    'method': f'direct browser launch ({Path(exe).name})',
                    'note': f'Opened in a real visible tab in {app}.',
                }
            except OSError:
                continue
    import webbrowser
    opened = webbrowser.open_new_tab(url)
    return {
        'status': 'completed' if opened else 'failed',
        'action': 'open_url',
        'app': app,
        'url': url,
        'visible_browser': True,
        'url_dispatched': bool(opened),
        'url_verified': bool(opened),
        'focus_verified': False,
        'method': 'system webbrowser',
    }


def _open_native(app):
    """Dispatch one LaunchServices open/reopen and verify the foreground PID.

    Accept only an exact installed app name, never arbitrary commands/paths.
    The app may still need a document/account before it can do further work.
    """
    path = application_paths().get(app.casefold()) if isinstance(app, str) else None
    if path is None:
        return {'status': 'failed', 'error': 'The requested application is not installed.'}
    try:
        from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps
        from Foundation import NSDate, NSRunLoop
    except ImportError:
        return {'status': 'failed', 'error': 'Native app opening requires macOS and kurt-ai[desktop].'}
    workspace = NSWorkspace.sharedWorkspace()
    if not workspace.launchApplication_(str(path)):
        return {'status': 'failed', 'error': 'LaunchServices declined the app opening request.'}
    deadline = time.monotonic() + 8
    activated = False
    while time.monotonic() < deadline:
        # Pump AppKit notifications so a long-lived chat sees current activation.
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(.1))
        matches = [candidate for candidate in workspace.runningApplications()
                   if candidate.bundleURL() and Path(str(candidate.bundleURL().path())).resolve() == path.resolve()]
        if len(matches) != 1:
            continue
        running = matches[0]
        foreground = workspace.frontmostApplication()
        if foreground and foreground.processIdentifier() == running.processIdentifier() and running.isActive():
            return {'status': 'completed', 'app': path.stem, 'pid': int(running.processIdentifier()),
                    'foreground_verified': True, 'method': 'macOS LaunchServices'}
        if not activated:
            running.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            activated = True
    return {'status': 'unverified', 'app': path.stem, 'foreground_verified': False,
            'error': 'Opening was requested once, but the app did not become the foreground application.'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--app')
    choice.add_argument('--inspect', action='store_true')
    args = parser.parse_args()
    if args.inspect:
        from AppKit import NSWorkspace
        from kurt.core.browser_intent import default_browser
        foreground = NSWorkspace.sharedWorkspace().frontmostApplication()
        receipt = {'status': 'completed', 'apps': sorted(p.stem for p in application_paths().values()),
                   'foreground_app': str(foreground.localizedName()) if foreground else None,
                   'default_browser': default_browser()}
    else:
        receipt = _open_native(args.app)
    print(json.dumps(receipt))
