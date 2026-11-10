"""Conservative, complete-match browser opening for ordinary chat requests."""
from dataclasses import dataclass
import re

from kurt.core.desktop_actions import desktop_action


@dataclass(frozen=True)
class BrowserRequest:
    app: str | None
    url: str | None = None


_APPS = {
    'safari': 'Safari', 'chrome': 'Google Chrome', 'google chrome': 'Google Chrome',
    'edge': 'Microsoft Edge', 'microsoft edge': 'Microsoft Edge', 'firefox': 'Firefox',
    'brave': 'Brave Browser', 'brave browser': 'Brave Browser', 'opera': 'Opera',
    'vivaldi': 'Vivaldi', 'arc': 'Arc', 'zen': 'Zen', 'zen browser': 'Zen',
}
_TARGET = r'(?:google chrome|microsoft edge|brave browser|zen browser|web browser|browser|safari|chrome|edge|firefox|brave|opera|vivaldi|arc|zen)'
_PARTICLE = r'(?:mo|ka|ang|ng|yung|iyong|aking|ako|naman|nga|po|ba|bang|the|a|an|my|your|please)'


def opening_pattern(target_pattern):
    return re.compile(
        rf'^(?:(?:hey\s+)?kurt[,!:\s]+)?'
        rf'(?:(?:can|could|would|will)\s+you\s+|(?:pwede|puwede)(?:ng)?\s+(?:mo\s+)?(?:ba(?:ng)?\s+)?|please\s+)?'
        rf'(?:please\s+)?(?:paki\s+)?'
        rf'(?:open|launch|start|activate|buksan|magbukas|mag-open|magopen|pakibukas|paki-open|i-open|iopen|pa-open)\s+'
        rf'(?:{_PARTICLE}\s+)*(?P<target>{target_pattern})'
        rf'(?:\s+browser)?(?:\s+(?:ko|mo|natin))?'
        rf'(?P<tail>.*?)$', re.IGNORECASE,
    )


_OPEN = opening_pattern(_TARGET)


def parse_browser_request(prompt):
    """Never consume a partial task, quoted example, negation, or explanation."""
    if not isinstance(prompt, str) or len(prompt) > 8192:
        return None
    match = _OPEN.fullmatch(prompt.strip())
    if not match:
        return None
    tail = match['tail'].strip()
    # Politeness may follow the target, but extra work must reach the agent.
    tail = re.sub(r'\s+(?:please|pls|po|naman|nga|ngayon|now)[.!?]*$', '', tail, flags=re.I).strip()
    if re.fullmatch(r'(?:please|pls|po|naman|nga|ngayon|now)?[.!?]*', tail, re.I):
        tail = ''
    url = None
    if tail:
        destination = re.fullmatch(
            r'(?:at\s+(?:pumunta|magpunta)\s+sa|and\s+(?:go|navigate)\s+to|(?:go|navigate)\s+to|to|sa|at|on)\s+'
            r'(?P<url>\S+?)[!?]?\s*', tail, re.I)
        if not destination:
            return None
        url = destination['url'].strip('"\'“”').rstrip('.')
        if not re.fullmatch(r'(?:https?://|file:///)[^\s]+', url, re.I):
            if not re.fullmatch(r'(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d+)?(?:/[^\s]*)?', url, re.I):
                return None
            url = 'https://' + url
    return BrowserRequest(_APPS.get(match['target'].casefold()), url)


def default_browser():
    """Ask macOS which browser handles HTTPS without opening a URL."""
    try:
        from AppKit import NSWorkspace
        from Foundation import NSURL
        target = NSWorkspace.sharedWorkspace().URLForApplicationToOpenURL_(NSURL.URLWithString_('https://example.com'))
        if target:
            from pathlib import Path
            return Path(str(target.path())).stem
    except (ImportError, AttributeError, OSError):
        pass
    return None


def execute_browser_request(request):
    app = request.app or default_browser()
    if not app:
        return {'status': 'failed', 'message': 'Hindi matukoy ang default browser. Sabihin kung Safari, Chrome, o Edge ang bubuksan.'}
    try:
        result = desktop_action('open_url' if request.url else 'open_app', app=app, url=request.url)
    except (ValueError, OSError, RuntimeError) as exc:
        return {'status': 'failed', 'message': f'Hindi nabuksan ang {app}: {exc}'}
    observed = result.get('observation') or {}
    verified = result.get('status') == 'completed' and observed.get('status') == 'completed' and bool(observed.get('window_id'))
    if verified:
        message = f'Nabuksan at na-verify ang {app}' + (f': {request.url}' if request.url else '.')
    else:
        detail = result.get('error') or observed.get('error') or 'Walang verified browser window; tingnan ang desktop permissions o app setup.'
        message = f'Hindi ma-verify ang pagbukas ng {app}: {detail}'
    return {'status': 'completed' if verified else 'failed', 'message': message, 'app': app,
            'url': request.url, 'result': result}
