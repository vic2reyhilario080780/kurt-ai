"""Verify and save provider artifacts before reporting a generated file as ready."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from urllib.parse import urlsplit, urljoin

import httpx
from kurt.utils.security import child_env, require_public_file, redact

OUTPUT_DIR = Path.home()/'Downloads/Kurt'
MAX_BYTES = 150 * 1024 * 1024


def _check_url(url):
    p = urlsplit(url)
    hosts = ('fal.media', 'replicate.delivery', 'storage.googleapis.com', 'wavespeed.ai')
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Artifact requires an HTTPS provider URL.')
    if not any(p.hostname == h or p.hostname.endswith('.'+h) for h in hosts):
        raise ValueError('Artifact host is not an approved provider CDN; download remains unverified.')


def probe_file(path, kind):
    with open(path, 'rb') as stream: header = stream.read(64)
    if kind == 'image':
        from kurt.core.attachments import _mime
        mime = _mime(header)
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        return {'file_verified': True, 'extension': {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}[mime]}
    binary = shutil.which('ffprobe')
    if not binary: raise RuntimeError('ffprobe is required to verify generated video/audio. Provider output exists but playback is unverified.')
    result = subprocess.run([binary, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                            env=child_env(), capture_output=True, text=True, timeout=20)
    if result.returncode: raise RuntimeError('Generated media failed the container/stream check: '+redact(result.stderr[-400:]))
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    wanted = 'video' if kind == 'video' else 'audio'
    if not any(s.get('codec_type') == wanted for s in streams): raise RuntimeError(f'No {wanted} stream was found in provider output.')
    duration = float(data.get('format', {}).get('duration', 0))
    if duration <= 0: raise RuntimeError('Generated media has no positive duration.')
    extension = '.webm' if 'webm' in data.get('format', {}).get('format_name', '') else '.mp4' if kind == 'video' else '.audio'
    return {'file_verified': True, 'duration_seconds': duration, 'has_audio': any(s.get('codec_type') == 'audio' for s in streams), 'extension': extension}


def finalize_artifact(url, kind):
    _check_url(url)
    root = OUTPUT_DIR.expanduser().resolve()
    require_public_file(root); root.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            current = url
            for hop in range(4):
                _check_url(current)
                with client.stream('GET', current) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        current = urljoin(current, response.headers['location']); continue
                    response.raise_for_status()
                    content_type = response.headers.get('content-type', '').split(';')[0]
                    if content_type.startswith('text/') or content_type in ('application/json', 'application/xml'):
                        raise RuntimeError('Provider link returned text/HTML/JSON rather than a media file.')
                    digest, size = hashlib.sha256(), 0
                    with tempfile.NamedTemporaryFile(dir=root, suffix='.part', delete=False) as stream:
                        temporary = Path(stream.name)
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > MAX_BYTES: raise RuntimeError('Generated file exceeds the 150 MiB download limit; check provider before retrying generation.')
                            digest.update(chunk); stream.write(chunk)
                    if not size: raise RuntimeError('Provider returned an empty artifact.')
                    probe = probe_file(temporary, kind)
                    destination = root/(kind+'-'+uuid.uuid4().hex+probe.pop('extension'))
                    os.replace(temporary, destination); temporary = None
                    receipt_path = destination.with_suffix(destination.suffix + '.json')
                    receipt_path.write_text(json.dumps({'kind': kind, 'path': str(destination), 'bytes': size,
                        'sha256': digest.hexdigest(), **probe, 'content_verified': False}, indent=2))
                    return {'path': str(destination), 'bytes': size, 'sha256': digest.hexdigest(), 'content_type': content_type,
                            'output': url, **probe, 'content_verified': False}
            raise RuntimeError('Too many artifact redirects.')
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def completion_text(receipt):
    if receipt.get('status') != 'completed' or receipt.get('file_verified') is not True:
        reason = receipt.get('reason') or 'No verified output file is available.'
        return 'Hindi pa verified na tapos ang generation. '+str(reason)+' Hindi ko ito awtomatikong uulitin; tingnan muna ang provider job status.'
    source = 'May reference image na ipinasa sa provider.' if receipt.get('reference_used') else 'Text-only generation; walang reference image na ginamit.'
    return (f"Na-download at na-check ang {receipt['kind']} file: {receipt['path']}\n"
            f"Model: {receipt['model']} [{receipt['provider']}]\n{source}\n"
            'Hindi pa na-verify ang eksaktong visual content o sinabing dialogue; i-preview muna ang file.')


# Scoped to one tool invocation; never persisted with private image bytes.
from contextvars import ContextVar
REFERENCE_IMAGES = ContextVar('media_reference_images', default=())
FAL_REFERENCE = ContextVar('fal_reference_image', default=None)
I2V_MODELS = {
    'fal-ai/kling-video/v3/standard/image-to-video',
    'fal-ai/kling-video/v3/pro/image-to-video',
}


def ungrounded_media_reply(text, messages):
    """Structural artifact provenance check, not an intent classifier."""
    import re
    candidates = re.findall(r'https?://[^\s<>"\x27]+', text)
    known = '\n'.join(str(m.get('content', '')) for m in messages if m.get('role') != 'assistant')
    for candidate in candidates:
        url = candidate.rstrip(').,]')
        parsed = urlsplit(url)
        media = (parsed.hostname or '').endswith(('fal.media', 'replicate.delivery')) or parsed.path.lower().endswith(('.mp4', '.webm', '.mov'))
        if media and url not in known:
            return 'Walang verified generation receipt para sa media link na iminungkahi ng AI. Hindi ko ito maituturing na rendered o tapos. Kailangan gamitin ang generate_media tool at ma-check ang output file.'
    return text
