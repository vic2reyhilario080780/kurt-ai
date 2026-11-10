"""Literal local app, Mail, Music, and download actions with result verification."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shlex
import tempfile
import time
from urllib.parse import unquote, urlsplit

import httpx

from kurt.core.browser_intent import opening_pattern
from kurt.core.desktop_actions import desktop_action
from kurt.utils.security import require_public_file, redact


@dataclass(frozen=True)
class LocalRequest:
    action: str
    app: str | None = None
    url: str | None = None
    output: str | None = None


def installed_apps():
    apps = {}
    for root in ('/Applications', '/Applications/Utilities', '/System/Applications',
                 '/System/Applications/Utilities', str(Path.home() / 'Applications')):
        for path in Path(root).glob('*.app'):
            apps[path.stem.casefold()] = path.stem
    for alias, name in {'apple mail': 'Mail', 'apple music': 'Music', 'settings': 'System Settings'}.items():
        if name.casefold() in apps:
            apps[alias] = name
    return apps


def parse_local_request(prompt):
    if not isinstance(prompt, str) or len(prompt) > 8192:
        return None
    text = re.sub(r'^(?:hey\s+)?kurt[,!:\s]+', '', prompt.strip(), flags=re.I)
    text = re.sub(r'^(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?|'
                  r'(?:pwede|puwede)(?:ng)?\s+(?:mo\s+)?(?:ba(?:ng)?\s+)?)', '', text, flags=re.I)
    apps = installed_apps()
    if apps:
        names = '|'.join(re.escape(name) for name in sorted(apps, key=len, reverse=True))
        match = opening_pattern(rf'(?:{names})').fullmatch(prompt.strip())
        if match and re.fullmatch(r'\s*(?:please|pls|po|naman|nga|ngayon|now)?[.!?]*', match['tail'], re.I):
            return LocalRequest('open_app', app=apps[match['target'].casefold()])
    if re.fullmatch(r'(?:please\s+)?(?:check|i-check|icheck|tingnan|tignan)\s+'
                    r'(?:(?:mo|nga|po|ang|yung|aking|my|the|unread|new)\s+)*'
                    r'(?:email|emails|mail|inbox)(?:\s+(?:ko|please|po))?[.!?]*', text, re.I):
        return LocalRequest('check_mail', app='Mail')
    if re.fullmatch(r'(?:please\s+)?(?:play|i-play|iplay|magpatugtog|patugtugin)\s+'
                    r'(?:(?:mo|ka|nga|naman|po|ang|ng|yung|aking|my|some|the|a|an)\s+)*'
                    r'(?:music|musika|kanta|song|songs)(?:\s+(?:sa\s+|in\s+|on\s+)?(?:apple\s+)?music)?'
                    r'(?:\s+(?:please|po))?[.!?]*', text, re.I):
        return LocalRequest('play_music', app='Music')
    if re.fullmatch(r'(?:please\s+)?(?:pause|stop|i-pause|itigil|ihinto)\s+'
                    r'(?:(?:mo|ang|yung|the|my)\s+)*(?:music|musika|kanta)[.!?]*', text, re.I):
        return LocalRequest('pause_music', app='Music')
    download = re.fullmatch(r'(?:please\s+)?(?:download|i-download|idownload)\s+'
                            r'(?:(?:mo|nga|po|ang|yung)\s+)*(?P<url>https?://\S+)'
                            r'(?:\s+(?:to|sa|as)\s+(?P<output>.+?))?[.!?]*', text, re.I)
    if download:
        output = download['output']
        if output:
            try:
                paths = shlex.split(output)
            except ValueError:
                return None
            if len(paths) != 1:
                return None
            output = paths[0]
        return LocalRequest('download', url=download['url'], output=output)
    if re.fullmatch(r'(?:please\s+)?(?:download|i-download|idownload)(?:\s+(?:mo|nga|po|ito|this|ganito|file))*[.!?]*', text, re.I):
        return LocalRequest('download')
    return None


_DELEGATE_CLASS = None


def _native_action(action):
    """Fixed native selectors only; OS Automation permissions still apply.

    This trusted adapter accepts no scripts, commands, bundle IDs or model
    code. Generated code and external CLIs retain their existing sandboxes.
    """
    if action not in {'check_mail', 'music_status', 'play_music', 'pause_music'}:
        raise ValueError('Unsupported native app action.')
    try:
        from ScriptingBridge import SBApplication
        from Foundation import NSObject
    except ImportError as exc:
        raise RuntimeError('Native Mail/Music requires macOS and kurt-ai[desktop].') from exc
    global _DELEGATE_CLASS
    if _DELEGATE_CLASS is None:
        class KurtLocalAppEventDelegate(NSObject):
            def eventDidFail_withError_(self, event, error):
                self.last_error = str(error.localizedDescription())
                return None
        _DELEGATE_CLASS = KurtLocalAppEventDelegate
    delegate = _DELEGATE_CLASS.alloc().init()
    delegate.last_error = None
    bundle = 'com.apple.mail' if action == 'check_mail' else 'com.apple.Music'
    target = SBApplication.applicationWithBundleIdentifier_(bundle)
    if target is None:
        raise RuntimeError('The required native app is unavailable.')
    target.setTimeout_(1200)  # Apple-event ticks: 20 seconds.
    target.setDelegate_(delegate)
    try:
        if action == 'check_mail':
            accounts = int(target.accounts().count())
            result = {'accounts': accounts, 'unread': int(target.inbox().unreadCount()) if accounts else 0}
        else:
            states = {int.from_bytes(code.encode(), 'big'): name
                      for code, name in [('kPSP', 'playing'), ('kPSp', 'paused'), ('kPSS', 'stopped')]}
            library = target.libraryPlaylists().objectAtIndex_(0)
            tracks = int(library.tracks().count())
            state = states.get(int(target.playerState()), 'unknown')
            if delegate.last_error:
                raise RuntimeError(f'Native app Automation failed: {delegate.last_error}')
            if action == 'play_music' and tracks:
                if state == 'paused':
                    target.playOnce_(False)
                elif state == 'stopped':
                    playable = None
                    for track in library.fileTracks()[:32]:
                        location = track.location()
                        if location is None:
                            continue
                        path = Path(str(location.path()))
                        try:
                            require_public_file(path)
                            if path.is_file() and path.suffix.lower() in {'.mp3', '.m4a', '.aac', '.wav', '.aiff', '.aif', '.flac', '.alac', '.mp4'}:
                                playable = track
                                break
                        except (OSError, ValueError):
                            continue
                    if playable is None:
                        if delegate.last_error:
                            raise RuntimeError(f'Native app Automation failed: {delegate.last_error}')
                        return {'player_state': 'stopped', 'library_tracks': tracks,
                                'needs_track': True}
                    target.play_once_(playable, False)
            elif action == 'pause_music':
                target.pause()
            state = states.get(int(target.playerState()), 'unknown')
            if action == 'play_music' and tracks:
                for _ in range(5):
                    if state == 'playing' or delegate.last_error:
                        break
                    time.sleep(.2)
                    state = states.get(int(target.playerState()), 'unknown')
            result = {'player_state': state, 'library_tracks': tracks}
        if delegate.last_error:
            raise RuntimeError(f'Native app Automation failed: {delegate.last_error}')
        return result
    finally:
        target.setDelegate_(None)


def mail_status():
    return _native_action('check_mail')


def music_status():
    return _native_action('music_status')


def download_file(url, output=None, max_bytes=10 * 1024 * 1024):
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('A direct HTTP(S) download URL without embedded login credentials is required.')
    filename = Path(unquote(parsed.path)).name or 'download.bin'
    if not filename or filename in {'.', '..'} or any(ord(c) < 32 for c in filename):
        raise ValueError('Provide a valid output filename.')
    destination = Path(output).expanduser() if output else Path.home() / 'Downloads' / filename
    destination = destination.absolute()
    require_public_file(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('The destination already exists; choose another filename.')
    if not destination.parent.is_dir():
        raise ValueError('The destination folder must already exist.')
    temp_path = None
    size, digest = 0, hashlib.sha256()
    deadline = time.monotonic() + 60
    try:
        with httpx.Client(timeout=20, follow_redirects=True, max_redirects=5) as client:
            with client.stream('GET', url) as response:
                response.raise_for_status()
                length = response.headers.get('content-length')
                if length and int(length) > max_bytes:
                    raise ValueError('Download exceeds the 10-MiB limit for this action.')
                with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.kurt-download-', delete=False) as stream:
                    temp_path = Path(stream.name)
                    for chunk in response.iter_bytes():
                        if time.monotonic() > deadline:
                            raise TimeoutError('Download exceeded its time budget.')
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError('Download exceeds the 10-MiB limit for this action.')
                        digest.update(chunk)
                        stream.write(chunk)
        # Hard-link publication is exclusive even if another process creates
        # the destination during the transfer. Never overwrite user files.
        os.link(temp_path, destination)
        return {'path': str(destination), 'bytes': size, 'sha256': digest.hexdigest()}
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def execute_local_request(request):
    try:
        if request.action == 'open_app':
            result = desktop_action('open_app', app=request.app)
            if result.get('status') != 'completed':
                return {'status': 'failed', 'message': f'Hindi ma-verify ang pagbukas ng {request.app}: {result.get("error") or "app/window unavailable"}'}
            return {'status': 'completed', 'message': f'Nabuksan at na-verify ang {request.app}.', 'app': request.app}
        if request.action == 'check_mail':
            result = mail_status()
            if result['accounts'] == 0:
                return {'status': 'needs_setup', 'message': 'Walang naka-configure na email account sa Apple Mail. Sabihin kung Gmail, Outlook, o ibang account ang gagamitin.'}
            return {'status': 'completed', 'message': f'Na-check ang Apple Mail: {result["unread"]} unread email sa inbox.', **result}
        if request.action == 'play_music':
            player = _native_action('play_music')
            state = player['player_state']
            if player['library_tracks'] == 0:
                return {'status': 'needs_input', 'message': 'Walang track sa Music library. Sabihin ang kanta, file, o music service na gagamitin.'}
            if player.get('needs_track'):
                return {'status': 'needs_input', 'message': 'Walang ma-verify na available na local track. Sabihin ang kanta o music service na gagamitin.'}
            if state != 'playing':
                return {'status': 'failed', 'message': f'Hindi ma-verify ang playback sa Music: {state}.'}
            return {'status': 'completed', 'message': 'Tumutugtog na ang Music; na-verify ang player state.', 'player_state': state}
        if request.action == 'pause_music':
            state = _native_action('pause_music')['player_state']
            return {'status': 'completed' if state in {'paused', 'stopped'} else 'failed',
                    'message': f'Music player state: {state}.', 'player_state': state}
        if request.action == 'download':
            if not request.url:
                return {'status': 'needs_input', 'message': 'Ibigay ang direct HTTP(S) download link at, kung kailangan, ang filename o save folder.'}
            result = download_file(request.url, request.output)
            return {'status': 'completed', 'message': f'Na-download at na-verify ang {result["bytes"]} bytes: {result["path"]}', **result}
        raise ValueError('Unsupported local action.')
    except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
        return {'status': 'failed', 'message': f'Hindi natapos ang action: {redact(str(exc))}'}
