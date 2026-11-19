"""BYOK media adapters (WaveSpeed & Hugging Face Inference Router); submissions are never replayed."""
import asyncio
import base64
import re
import time
from urllib.parse import urlsplit

from kurt.models.additional import find_cached_model
from kurt.models.catalog import default_roles, hf_inference_route


def _valid_path_id(value):
    return (isinstance(value, str) and bool(value) and
            bool(re.fullmatch(r'[A-Za-z0-9_.:/-]+', value)) and
            not value.startswith('/') and not value.endswith('/') and
            not any(p in ('', '.', '..') for p in value.split('/')))


def _checked_https_url(value, label):
    if not isinstance(value, str) or not value:
        raise RuntimeError(f'{label} returned no media URL.')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError(f'{label} returned an invalid artifact URL.')
    return value


def _store_local_bytes(data, kind, content_type, source):
    from kurt.core.media_artifacts import finalize_artifact_bytes, LOCAL_ARTIFACT_HOLDER
    receipt = finalize_artifact_bytes(data, kind, content_type=content_type, source=source)
    holder = LOCAL_ARTIFACT_HOLDER.get()
    if isinstance(holder, dict):
        holder['receipt'] = receipt
    return receipt['path']


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
        yield _checked_https_url(outputs[0], f'WaveSpeed job {job}')  # Existing artifact verification must still succeed.


async def generate_huggingface_media(router, model, prompt, kind='image', catalog_provider='huggingface_inference'):
    """Generate an image or video through Hugging Face Inference Router using the live provider mapping."""
    if kind not in ('image', 'video'):
        raise ValueError('Hugging Face Inference media routing currently supports text-to-image and text-to-video only.')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', model) or any(p in ('.', '..') for p in model.split('/')):
        raise ValueError('Use the exact Hugging Face model ID (owner/model).')
    contract = (find_cached_model(catalog_provider, model) or
                find_cached_model('huggingface_inference', model) or
                find_cached_model('huggingface_hub', model))
    route = hf_inference_route(contract, kind) if contract else None
    if not route:
        raise ValueError(f'Load the Hugging Face catalog and choose a model with a live text-to-{kind} provider first.')
    hf_provider = route['provider']
    provider_id = route['provider_id']
    if not _valid_path_id(provider_id):
        raise ValueError('Invalid Hugging Face inference provider model ID.')
    token = (router.byok_keys.get(catalog_provider) or router.byok_keys.get('huggingface_inference') or
             router.byok_keys.get('huggingface_hub') or router.byok_keys.get('huggingface', ''))
    if not token:
        raise RuntimeError('Missing HF_TOKEN for Hugging Face Inference. Add your token in /models or /setup.')
    headers = {'Authorization': 'Bearer ' + token}
    base = 'https://router.huggingface.co'
    async with router._http_client(provider='huggingface_inference', timeout=120, follow_redirects=False) as client:
        if hf_provider == 'fal-ai' and kind == 'image':
            response = await client.post(f'{base}/fal-ai/{provider_id}', headers=headers, json={'prompt': prompt})
            response.raise_for_status()
            images = response.json().get('images')
            url = images[0].get('url') if isinstance(images, list) and images and isinstance(images[0], dict) else None
            yield _checked_https_url(url, 'Hugging Face (fal-ai)')
            return
        if hf_provider == 'fal-ai' and kind == 'video':
            response = await client.post(f'{base}/fal-ai/{provider_id}?_subdomain=queue', headers=headers, json={'prompt': prompt})
            response.raise_for_status()
            body = response.json()
            req_id = body.get('request_id')
            resp_path = urlsplit(str(body.get('response_url') or '')).path.strip('/')
            if not isinstance(req_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', req_id) or not _valid_path_id(resp_path):
                raise RuntimeError('No verified Hugging Face (fal-ai) video job ID; do not automatically resubmit.')
            status_url = f'{base}/fal-ai/{resp_path}/status?_subdomain=queue'
            result_url = f'{base}/fal-ai/{resp_path}?_subdomain=queue'
            status = body.get('status')
            deadline = time.monotonic() + 240
            while status != 'COMPLETED':
                if status in {'FAILED', 'CANCELLED', 'ERROR'}:
                    raise RuntimeError(f'Hugging Face (fal-ai) video job {req_id}: {status}.')
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Hugging Face (fal-ai) video job {req_id} is still pending; inspect before retrying.')
                await asyncio.sleep(2)
                poll = await client.get(status_url, headers=headers)
                poll.raise_for_status()
                status = poll.json().get('status')
            final = await client.get(result_url, headers=headers)
            final.raise_for_status()
            video = final.json().get('video')
            vid_url = video.get('url') if isinstance(video, dict) else None
            yield _checked_https_url(vid_url, f'Hugging Face (fal-ai) video job {req_id}')
            return
        if hf_provider == 'hf-inference' and kind == 'image':
            url = f'{base}/hf-inference/models/{provider_id}'
            response = await client.post(url, headers=headers, json={'inputs': prompt})
            response.raise_for_status()
            yield _store_local_bytes(response.content, 'image', response.headers.get('content-type', ''), url)
            return
        if hf_provider in ('together', 'nscale') and kind == 'image':
            url = f'{base}/{hf_provider}/v1/images/generations'
            fmt = 'base64' if hf_provider == 'together' else 'b64_json'
            response = await client.post(url, headers=headers, json={'prompt': prompt, 'model': provider_id, 'response_format': fmt})
            response.raise_for_status()
            items = response.json().get('data')
            first = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
            if isinstance(first.get('b64_json'), str) and first['b64_json']:
                try:
                    raw = base64.b64decode(first['b64_json'], validate=True)
                except ValueError as exc:
                    raise RuntimeError(f'Hugging Face ({hf_provider}) returned invalid base64 image data.') from exc
                yield _store_local_bytes(raw, 'image', 'image/png', url)
                return
            yield _checked_https_url(first.get('url'), f'Hugging Face ({hf_provider})')
            return
        if hf_provider == 'replicate':
            req_headers = {**headers, 'Prefer': 'wait'}
            payload = {'input': {'prompt': prompt}}
            if ':' in provider_id:
                url = f'{base}/replicate/v1/predictions'
                payload['version'] = provider_id.split(':', 1)[1]
            else:
                url = f'{base}/replicate/v1/models/{provider_id}/predictions'
            response = await client.post(url, headers=req_headers, json=payload)
            response.raise_for_status()
            output = response.json().get('output')
            out_url = output if isinstance(output, str) else output[0] if isinstance(output, list) and output and isinstance(output[0], str) else None
            if not out_url:
                raise TimeoutError('Hugging Face (replicate) returned no output yet; inspect provider status before retrying.')
            yield _checked_https_url(out_url, 'Hugging Face (replicate)')
            return
        if hf_provider == 'wavespeed':
            response = await client.post(f'{base}/wavespeed/api/v3/{provider_id}', headers=headers, json={'prompt': prompt})
            response.raise_for_status()
            body = response.json()
            if body.get('code') not in (None, 200):
                raise RuntimeError('Hugging Face (wavespeed) rejected the submission. Check provider status before retrying.')
            data = body.get('data', {})
            job = data.get('id')
            if not isinstance(job, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', job):
                raise RuntimeError('No verified Hugging Face (wavespeed) job ID; do not automatically resubmit.')
            deadline = time.monotonic() + (240 if kind == 'video' else 180)
            while data.get('status') != 'completed':
                if data.get('status') in {'failed', 'cancelled', 'timeout', 'deleted'}:
                    raise RuntimeError(f'Hugging Face (wavespeed) job {job}: {data["status"]}.')
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Hugging Face (wavespeed) job {job} is still pending; inspect before retrying.')
                await asyncio.sleep(2)
                poll = await client.get(f'{base}/wavespeed/api/v3/predictions/{job}/result', headers=headers)
                poll.raise_for_status()
                data = poll.json().get('data', {})
            outputs = data.get('outputs')
            if not isinstance(outputs, list) or not outputs or not isinstance(outputs[0], str):
                raise RuntimeError(f'Hugging Face (wavespeed) job {job} returned no media URL.')
            yield _checked_https_url(outputs[0], f'Hugging Face (wavespeed) job {job}')
            return
        raise ValueError(f'Unsupported Hugging Face {kind} inference provider: {hf_provider}')


generate_huggingface_image = generate_huggingface_media


async def generate_custom_endpoint_image(router, provider, model, prompt):
    """Generate an image via a user-configured private JSON endpoint (OpenAI images or raw image bytes)."""
    from kurt.models.providers import custom_endpoint_config, provider_key
    cfg = custom_endpoint_config(provider, model)
    if not cfg or 'image' not in cfg['roles']:
        raise ValueError('No runnable custom image endpoint JSON config found for this model.')
    base = cfg['base_url'].rstrip('/')
    if base.endswith('/images/generations') or '/models/' in base:
        url = base
    elif base.endswith('/v1'):
        url = base + '/images/generations'
    else:
        url = base + '/v1/images/generations'
    headers = dict(cfg.get('headers') or {})
    token = cfg.get('api_key') or router.byok_keys.get(provider) or provider_key(provider)
    if token and not any(k.lower() == 'authorization' for k in headers):
        headers['Authorization'] = 'Bearer ' + token
    payload = {'inputs': prompt} if '/models/' in url and not url.endswith('/images/generations') else {
        'prompt': prompt, 'model': cfg['model'] or model, 'response_format': 'b64_json'
    }
    async with router._http_client(provider='custom_endpoint', timeout=120, follow_redirects=False) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        ctype = response.headers.get('content-type', '').split(';')[0].strip().lower()
        if ctype.startswith('image/'):
            yield _store_local_bytes(response.content, 'image', ctype, url)
            return
        body = response.json()
        items = body.get('data') if isinstance(body, dict) else None
        first = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
        if isinstance(first.get('b64_json'), str) and first['b64_json']:
            try:
                raw = base64.b64decode(first['b64_json'], validate=True)
            except ValueError as exc:
                raise RuntimeError('Custom endpoint returned invalid base64 image data.') from exc
            yield _store_local_bytes(raw, 'image', 'image/png', url)
            return
        yield _checked_https_url(first.get('url'), 'Custom image endpoint')
