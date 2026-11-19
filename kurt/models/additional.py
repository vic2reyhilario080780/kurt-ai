"""Optional BYOK catalogs with bounded pagination and exact identity deduplication."""
import json
import time
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import httpx

from kurt.models.catalog import unique_models, write_cache
from kurt.models.providers import PROVIDERS, EXTRA_PROVIDERS, provider_key

CACHE_DIR = Path.home() / '.kurt' / 'cache' / 'providers'
_memory = {}
MAX_RESPONSE = 32 * 1024 * 1024


def _hf_identity(value):
    if not isinstance(value, str) or not value:
        return None
    if value.startswith('https://huggingface.co/'):
        parts = urlsplit(value).path.strip('/').split('/')
        # Do not mistake a branch, collection or user URL for a model ID.
        return '/'.join(parts[:2]) if len(parts) == 2 else None
    return value if value.count('/') == 1 else None


def identities(model, provider):
    result = {'id:' + model['id']}
    for field in ('hugging_face_id', 'hf_model_id', 'huggingFaceUrl'):
        identity = _hf_identity(model.get(field))
        if identity:
            result.add('hf:' + identity)
    if provider == 'huggingface':
        result.add('hf:' + model['id'])
    return result


def without_primary_duplicates(provider, models, openrouter, fal):
    primary = set()
    for source, catalog in (('openrouter', openrouter), ('fal', fal)):
        for model in unique_models(catalog):
            primary.update(identities(model, source))
    visible, excluded = [], []
    for model in unique_models(models):
        (excluded if identities(model, provider) & primary else visible).append(model)
    return visible, excluded


def normalize(provider, raw):
    if not isinstance(raw, dict):
        raise ValueError('Invalid model record.')
    row = dict(raw)
    mid = row.get('model_id') if provider == 'wavespeed' else row.get('name') if provider == 'fireworks' else row.get('id')
    if provider == 'replicate':
        mid = raw.get('owner', '') + '/' + raw.get('name', '')
    if not isinstance(mid, str) or not mid or any(c.isspace() for c in mid):
        raise ValueError('Missing or invalid model ID.')
    row['id'] = mid
    row['name'] = raw.get('displayName') or raw.get('display_name') or raw.get('name') or mid
    kind = raw.get('model_type') or raw.get('type') or raw.get('baseModelDetails', {}).get('modelType') or 'other'
    row['category'] = kind
    if provider in ('huggingface', 'novita'):
        row['architecture'] = raw.get('architecture') or {'output_modalities': raw.get('output_modalities', [])}
    elif provider == 'together' and kind in ('chat', 'language'):
        row.setdefault('architecture', {'output_modalities': ['text']})
    elif provider == 'fireworks' and raw.get('supportsServerless') and kind in ('chat', 'LLM', 'llm', 'causal', 'text'):
        row.setdefault('architecture', {'output_modalities': ['text']})
    if provider == 'wavespeed':
        schemas = raw.get('api_schema', {}).get('api_schemas', [])
        schema = next((s.get('request_schema') for s in schemas if s.get('type') == 'model_run' and s.get('method') == 'POST'), None)
        row['prompt_compatible'] = bool(isinstance(schema, dict) and
            'prompt' in schema.get('properties', {}) and set(schema.get('required', [])) <= {'prompt'})
    return row


def _read(path):
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or not isinstance(data.get('models'), list):
            return None
        if not all(isinstance(m, dict) and isinstance(m.get('id'), str) for m in data['models']):
            return None
        if (type(data.get('fetched_at')) not in (int, float) or type(data.get('complete')) is not bool or
                data.get('next') is not None and not isinstance(data['next'], str)):
            return None
        return data
    except (OSError, ValueError):
        return None


def _json(client, url, headers, params=None):
    # Catalog pagination must not redirect credentials to another host.
    with client.stream('GET', url, headers=headers, params=params) as response:
        response.raise_for_status()
        chunks = bytearray()
        for chunk in response.iter_bytes():
            chunks.extend(chunk)
            if len(chunks) > MAX_RESPONSE:
                raise ValueError('Provider catalog page too large.')
    return json.loads(chunks)


def fetch_catalog(provider, refresh=False, more=False, page_budget=3):
    if provider not in EXTRA_PROVIDERS:
        raise ValueError('Unknown optional provider.')
    spec = PROVIDERS[provider]
    path = CACHE_DIR / (provider + '.json')
    previous = _memory.get(provider) or _read(path)
    if previous and not refresh and not more and time.time() - previous.get('checked_at', previous.get('fetched_at', 0)) < (60 if previous.get('error') else 3600):
        return previous
    key = provider_key(provider)
    if not key and not spec.get('public_catalog'):
        return {**(previous or {'models': [], 'complete': False}), 'error': 'Add your API key to load this catalog.'}
    if more and previous and previous.get('complete'):
        return previous
    rows = list(previous['models']) if more and previous else []
    cursor = previous.get('next') if more and previous else None
    headers = {'Authorization': 'Bearer ' + key} if key else {}
    expected_total = previous.get('total') if more and previous else None
    try:
        seen = set()
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
            for _ in range(page_budget):
                params = None
                if provider == 'fireworks':
                    params = {'pageSize': 200}
                    if cursor:
                        params['pageToken'] = cursor
                elif provider == 'replicate' and cursor:
                    params = {'cursor': cursor}
                data = _json(client, spec['catalog_url'], headers, params)
                if provider == 'fireworks':
                    records = data.get('models')
                    cursor = data.get('nextPageToken') or None
                    if expected_total is not None and data.get('totalSize') != expected_total:
                        raise ValueError('Catalog changed during pagination.')
                    expected_total = data.get('totalSize')
                elif provider == 'replicate':
                    records = data.get('results')
                    next_url = data.get('next')
                    cursor = None
                    if next_url:
                        parsed = urlsplit(next_url)
                        if (parsed.scheme != 'https' or parsed.netloc != 'api.replicate.com' or
                                parsed.path not in ('/v1/models', '/v1/models/') or parsed.fragment):
                            raise ValueError('Untrusted catalog continuation URL.')
                        cursor = parse_qs(parsed.query).get('cursor', [None])[0]
                        if not cursor:
                            raise ValueError('Missing catalog continuation cursor.')
                else:
                    records = data if isinstance(data, list) else data.get('data')
                    cursor = None
                if not isinstance(records, list):
                    raise ValueError('Invalid catalog response.')
                rows.extend(normalize(provider, m) for m in records)
                if not cursor:
                    break
                if not isinstance(cursor, str) or cursor in seen:
                    raise ValueError('Repeated/invalid pagination cursor.')
                seen.add(cursor)
        rows = unique_models(rows)
        complete = cursor is None
        if complete and type(expected_total) is int and len(rows) != expected_total:
            raise ValueError('Incomplete provider catalog.')
        result = {'models': rows, 'next': cursor, 'complete': complete,
                  'total': len(rows) if complete else expected_total, 'fetched_at': time.time(), 'error': ''}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        write_cache(path, result)
        _memory[provider] = result
        return result
    except Exception as exc:
        code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        error = f'Catalog HTTP {code}; check API access.' if code else 'Catalog unavailable; last saved data retained.'
        result = {**(previous or {'models': [], 'complete': False}), 'error': error, 'checked_at': time.time()}
        _memory[provider] = result
        return result


def peek_catalog(provider):
    return _memory.get(provider) or _read(CACHE_DIR / (provider + '.json')) or {}


def invalidate(provider):
    _memory.pop(provider, None)


def find_cached_model(provider, mid):
    snapshot = _memory.get(provider) or _read(CACHE_DIR / (provider + '.json')) or {}
    return next((m for m in snapshot.get('models', []) if m['id'] == mid), None)
