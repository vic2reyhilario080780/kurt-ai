"""Complete provider catalogs: one category per endpoint, independent of pickers."""

import json
import os
import tempfile


def validate_models(models):
    if not isinstance(models, list) or not all(isinstance(m, dict) and isinstance(m.get('id'), str) and m['id'] for m in models):
        raise ValueError('Provider returned an invalid model catalog.')
    return unique_models(models)


def read_cache(path):
    try:
        return validate_models(json.loads(path.read_text()))
    except (OSError, ValueError, TypeError):
        return None


def write_cache(path, models):
    """Publish a complete catalog atomically; keep the previous cache on error."""
    fd, temporary = tempfile.mkstemp(prefix='.models-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(models, stream)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def unique_models(models):
    """Count exact provider IDs once; never collapse model families/versions."""
    return list({m['id']: m for m in models
                 if isinstance(m, dict) and isinstance(m.get('id'), str) and m['id']}.values())


PIPELINE_CATALOG_PROVIDERS = ('fal', 'wavespeed', 'replicate', 'huggingface_inference', 'huggingface_hub')
HF_IMAGE_PROVIDERS = ('fal-ai', 'hf-inference', 'together', 'nscale', 'replicate', 'wavespeed')
HF_VIDEO_PROVIDERS = ('fal-ai', 'wavespeed', 'replicate')


def hf_inference_route(model, role):
    """Return the selected live Hugging Face Inference Provider mapping for chat, image, or video."""
    if not isinstance(model, dict):
        return None
    entries = model.get('inference_providers')
    if not isinstance(entries, list):
        return None
    live = [e for e in entries if isinstance(e, dict) and e.get('status') == 'live'
            and isinstance(e.get('provider'), str) and isinstance(e.get('provider_id'), str)
            and isinstance(e.get('task'), str)]
    if role == 'chat':
        return next((e for e in live if e['task'] == 'conversational'), None)
    if role == 'image':
        by_provider = {e['provider']: e for e in live if e['task'] == 'text-to-image'}
        for prov in HF_IMAGE_PROVIDERS:
            if prov in by_provider:
                return by_provider[prov]
    if role == 'video':
        by_provider = {e['provider']: e for e in live if e['task'] == 'text-to-video'}
        for prov in HF_VIDEO_PROVIDERS:
            if prov in by_provider:
                return by_provider[prov]
    return None


def category(provider, model):
    if provider in PIPELINE_CATALOG_PROVIDERS:
        value = model.get('category')
        return value.strip() if isinstance(value, str) and value.strip() else 'other'
    architecture = model.get('architecture') or {}
    if not isinstance(architecture, dict):
        return 'other'
    outputs = architecture.get('output_modalities')
    if outputs is None:
        modality = architecture.get('modality', '')
        outputs = modality.rsplit('->', 1)[-1].split('+') if isinstance(modality, str) and '->' in modality else []
    if not isinstance(outputs, list) or not outputs or not all(isinstance(v, str) and v for v in outputs):
        return (model.get('category') or 'other') if provider != 'openrouter' else 'other'
    return '+'.join(sorted(set(outputs)))


def category_label(provider, value):
    if provider not in PIPELINE_CATALOG_PROVIDERS:
        return {'text': 'Chat / text output', 'other': 'Other / unspecified output'}.get(
            value, ' + '.join(p.title() for p in value.split('+')) + ' output')
    if value == 'other':
        return 'Other / unspecified'
    return value.replace('-to-', ' → ').replace('-', ' ').title()


def groups(provider, models):
    result = {}
    for model in unique_models(models):
        result.setdefault(category(provider, model), []).append(model)
    return dict(sorted(result.items()))


def default_roles(provider, model):
    """Only contracts already implemented by Kurt are selectable defaults."""
    from kurt.models.providers import custom_endpoint_roles
    kind = category(provider, model)
    roles = []
    if provider in ('huggingface_inference', 'huggingface_hub'):
        if hf_inference_route(model, 'chat'):
            roles.append('chat')
        if hf_inference_route(model, 'image'):
            roles.append('image')
        if hf_inference_route(model, 'video'):
            roles.append('video')
    elif provider not in PIPELINE_CATALOG_PROVIDERS:
        if kind == 'text':
            roles.append('chat')
    elif provider == 'replicate':
        pass  # Public list metadata alone does not establish an input contract.
    elif provider == 'wavespeed':
        if model.get('prompt_compatible') and kind in ('text-to-image', 'text-to-video'):
            roles.append(kind.rsplit('-', 1)[-1])
    elif kind == 'text-to-image':
        roles.append('image')
    elif kind == 'text-to-video':
        roles.append('video')
    elif kind == 'image-to-video':
        from kurt.core.media_artifacts import I2V_MODELS
        if model.get('id') in I2V_MODELS:
            roles.append('video')
    mid = model.get('id', '') if isinstance(model, dict) else ''
    for role in custom_endpoint_roles(provider, mid):
        if role not in roles:
            roles.append(role)
    return roles
