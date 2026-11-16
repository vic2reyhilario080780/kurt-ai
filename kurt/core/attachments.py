"""Explicit local image attachments, independent of conversational intent routing."""
import base64
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
import stat
from urllib.parse import unquote, urlsplit

from kurt.utils.security import redact, require_public_file

EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.heif', '.tif', '.tiff', '.bmp'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 15 * 1024 * 1024
MAX_IMAGES = 4
_SUFFIX = r'\.(?:png|jpe?g|gif|webp|heic|heif|tiff?|bmp)'
_QUOTED = re.compile(r'''(?P<q>['"])(?P<p>(?:/|~/|file://)[^\r\n]*?)(?P=q)''')
_TOKEN = re.compile(r'''(?<![\w'"/:])(?:file://|~/|/)(?:\\.|[^\s'"\\])+''')
_DATA = re.compile(r'data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/]+={0,2}\Z')


def is_local_path_input(text):
    text = text.strip()
    return bool(re.match(r'^(?:/[^/\s]+/|~/|file://)', text) or
                re.match(r'^/[^/\s]+'+_SUFFIX+r'(?=$|\s)', text, re.I))


def _local_path(value):
    if value.startswith('file://'):
        uri = urlsplit(value)
        if uri.netloc not in ('', 'localhost') or uri.query or uri.fragment:
            raise ValueError('Use a local file:// image URL without a remote host.')
        value = unquote(uri.path)
    return Path(value).expanduser()


@dataclass
class ImageInput:
    text: str
    paths: list


def parse_image_input(text):
    # Finder/Terminal may shell-escape an apostrophe as '\'' inside a path.
    try: tokens = shlex.split(text)
    except ValueError: tokens = []
    if len(tokens) == 1 and tokens[0].startswith(('/', '~/', 'file://')):
        path = _local_path(tokens[0])
        if path.suffix.lower() in EXTENSIONS: return ImageInput('', [path])
    matches = []
    covered = []
    for match in _QUOTED.finditer(text):
        if _local_path(match['p']).suffix.lower() in EXTENSIONS:
            matches.append((match.start(), match.end(), match['p']))
            covered.append((match.start(), match.end()))
    # macOS also pastes unquoted absolute paths containing literal spaces.
    prefix = re.match(r'^(?:/|~/)[^\r\n]*?'+_SUFFIX+r'(?=$|\s)', text, re.I)
    if prefix and not any(a <= prefix.start() < b for a, b in covered):
        value = prefix.group()
        if '\\' in value:
            try: value = shlex.split(value)[0]
            except ValueError: pass
        matches.append((prefix.start(), prefix.end(), value)); covered.append(prefix.span())
    for match in _TOKEN.finditer(text):
        if any(a <= match.start() < b for a, b in covered): continue
        try: value = shlex.split(match.group())[0]
        except ValueError: continue
        if _local_path(value).suffix.lower() in EXTENSIONS:
            matches.append((match.start(), match.end(), value))
    matches.sort()
    paths = []
    pieces, cursor = [], 0
    for start, end, value in matches:
        if start < cursor: continue
        path = _local_path(value)
        if path not in paths: paths.append(path)
        pieces.append(text[cursor:start]); cursor = end
    pieces.append(text[cursor:])
    if len(paths) > MAX_IMAGES: raise ValueError(f'Attach at most {MAX_IMAGES} images per message.')
    return ImageInput(' '.join(''.join(pieces).split()), paths)


def _mime(raw):
    if raw.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    if raw.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    if raw.startswith((b'GIF87a', b'GIF89a')): return 'image/gif'
    if raw.startswith(b'RIFF') and raw[8:12] == b'WEBP': return 'image/webp'
    raise ValueError('Unsupported image data. Export the picture as JPEG, PNG, GIF or WebP first.')


def load_images(paths):
    images, total = [], 0
    for original in paths:
        require_public_file(original)
        path = Path(original).resolve(strict=True)
        require_public_file(path)
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode): raise ValueError('An image attachment must be a regular file.')
            if info.st_size > MAX_IMAGE_BYTES: raise ValueError('Image exceeds the 5 MiB attachment limit.')
            raw = stream.read(MAX_IMAGE_BYTES+1)
        if len(raw) > MAX_IMAGE_BYTES: raise ValueError('Image exceeds the 5 MiB attachment limit.')
        total += len(raw)
        if total > MAX_TOTAL_BYTES: raise ValueError('Combined image attachments exceed 15 MiB.')
        mime = _mime(raw)
        images.append({'name': path.name, 'url': f'data:{mime};base64,'+base64.b64encode(raw).decode()})
    return images


def image_content(text, images):
    return [{'type': 'text', 'text': text}] + [{'type': 'image_url', 'image_url': {'url': img['url']}} for img in images]


def redact_messages(messages):
    """Redact text/credentials without corrupting validated inline image bytes."""
    result = []
    for message in messages:
        item = redact({k: v for k, v in message.items() if k != 'content'})
        content = message.get('content')
        if isinstance(content, list):
            blocks = []
            for block in content:
                url = block.get('image_url', {}).get('url') if isinstance(block, dict) and isinstance(block.get('image_url'), dict) else None
                if isinstance(url, str) and len(url) <= 8 * MAX_IMAGE_BYTES and _DATA.fullmatch(url):
                    blocks.append({'type': 'image_url', 'image_url': {'url': url}})
                else: blocks.append(redact(block))
            item['content'] = blocks
        else: item['content'] = redact(content)
        result.append(item)
    return result


def provider_image_messages(messages, provider):
    if provider not in ('anthropic', 'ollama'): return messages
    result = []
    for message in messages:
        content = message.get('content')
        if not isinstance(content, list): result.append(message); continue
        blocks, images = [], []
        for block in content:
            if block.get('type') != 'image_url': blocks.append(block); continue
            url = block['image_url']['url']
            if not _DATA.fullmatch(url): raise ValueError('This provider requires inline local image data.')
            header, encoded = url.split(',', 1)
            mime = header[5:].split(';')[0]
            if provider == 'anthropic': blocks.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': encoded}})
            else: images.append(encoded)
        if provider == 'ollama':
            result.append({**message, 'content': '\n'.join(b.get('text', '') for b in blocks), 'images': images})
        else: result.append({**message, 'content': blocks})
    return result
