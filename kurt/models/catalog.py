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


def category(provider, model):
    if provider in ('fal', 'wavespeed', 'replicate'):
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
    if provider not in ('fal', 'wavespeed', 'replicate'):
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
    kind = category(provider, model)
    if provider not in ('fal', 'wavespeed', 'replicate'):
        return ['chat'] if kind == 'text' else []
    if provider == 'replicate':
        return []  # Public list metadata alone does not establish an input contract.
    if provider == 'wavespeed':
        if model.get('prompt_compatible') and kind in ('text-to-image', 'text-to-video'):
            return [kind.rsplit('-', 1)[-1]]
        return []
    if kind == 'text-to-image':
        return ['image']
    if kind == 'text-to-video':
        return ['video']
    if kind == 'image-to-video':
        from kurt.core.media_artifacts import I2V_MODELS
        if model.get('id') in I2V_MODELS:
            return ['video']
    return []
