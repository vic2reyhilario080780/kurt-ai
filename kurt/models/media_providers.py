"""WaveSpeed prompt-only media adapter; submission is never replayed."""
import asyncio
import re
import time
from urllib.parse import urlsplit

from kurt.models.additional import find_cached_model
from kurt.models.catalog import default_roles


async def generate_wavespeed(router, model, prompt, kind):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', model) or any(p in ('.', '..') for p in model.split('/')):
        raise ValueError('Use the exact WaveSpeed model ID.')
    contract = find_cached_model('wavespeed', model)
    if not contract or kind not in default_roles('wavespeed', contract):
        raise ValueError('Load the WaveSpeed catalog and choose a supported prompt-only image/video contract first.')
    base = 'https://api.wavespeed.ai/api/v3'
    headers = {'Authorization': 'Bearer ' + router.byok_keys['wavespeed']}
    async with router._http_client(provider='wavespeed', timeout=60, follow_redirects=False) as client:
        response = await client.post(base + '/' + model, headers=headers, json={'prompt': prompt})
        response.raise_for_status()
        body = response.json()
        if body.get('code') not in (None, 200):
            raise RuntimeError('WaveSpeed rejected the submission. Check the provider before retrying.')
        data = body.get('data', {})
        job = data.get('id')
        if not isinstance(job, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', job):
            raise RuntimeError('No verified WaveSpeed job ID; do not automatically resubmit.')
        deadline = time.monotonic() + 180
        while data.get('status') != 'completed':
            if data.get('status') in {'failed', 'cancelled', 'timeout', 'deleted'}:
                raise RuntimeError(f'WaveSpeed job {job}: {data["status"]}.')
            if time.monotonic() >= deadline:
                raise TimeoutError(f'WaveSpeed job {job} is still pending; inspect it before retrying generation.')
            await asyncio.sleep(2)
            response = await client.get(base + '/predictions/' + job + '/result', headers=headers)
            response.raise_for_status()
            data = response.json().get('data', {})
        outputs = data.get('outputs')
        if not isinstance(outputs, list) or not outputs or not isinstance(outputs[0], str):
            raise RuntimeError(f'WaveSpeed job {job} returned no media URL.')
        parsed = urlsplit(outputs[0])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise RuntimeError(f'WaveSpeed job {job} returned an invalid artifact URL.')
        yield outputs[0]  # Existing artifact verification must still succeed.
