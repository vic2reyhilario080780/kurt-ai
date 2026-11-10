"""Launch an installed macOS application without screen/Accessibility access."""
from pathlib import Path
import json
import subprocess
import sys
import time


APP_ROOTS = ('/Applications', '/Applications/Utilities', '/System/Applications',
             '/System/Applications/Utilities')


def application_paths():
    apps = {}
    for root in (*APP_ROOTS, str(Path.home() / 'Applications')):
        for path in Path(root).glob('*.app'):
            apps[path.stem.casefold()] = path
    return apps


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
    if not isinstance(app, str) or app.casefold() not in application_paths():
        return {'status': 'failed', 'error': 'The requested application is not installed.'}
    return _native_receipt('--app', app)


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
