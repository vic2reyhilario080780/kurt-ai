"""Official provider endpoints and local BYOK credential management."""
import os
import re

EXTRA_PROVIDERS = ('huggingface', 'huggingface_inference', 'huggingface_hub', 'together', 'fireworks', 'replicate', 'wavespeed', 'novita')
HF_HUB_CATALOGS = frozenset(('huggingface_inference', 'huggingface_hub'))
NEW_BYOK_PROVIDERS = frozenset(('huggingface', 'together', 'fireworks', 'wavespeed', 'novita'))
RUNNABLE_BYOK_PROVIDERS = NEW_BYOK_PROVIDERS | HF_HUB_CATALOGS
BYOK_ONLY_PROVIDERS = NEW_BYOK_PROVIDERS | HF_HUB_CATALOGS

# Endpoints are application-owned constants, never supplied by catalog records.
PROVIDERS = {
    'openrouter': {'name': 'OpenRouter', 'key': 'OPENROUTER_API_KEY', 'keys_url': 'https://openrouter.ai/keys'},
    'fal': {'name': 'fal.ai', 'key': 'FAL_API_KEY', 'aliases': ('FAL_KEY',), 'keys_url': 'https://fal.ai/dashboard/keys'},
    'openai': {'name': 'OpenAI', 'key': 'OPENAI_API_KEY', 'keys_url': 'https://platform.openai.com/api-keys'},
    'anthropic': {'name': 'Anthropic', 'key': 'ANTHROPIC_API_KEY', 'keys_url': 'https://platform.claude.com/settings/keys'},
    'google': {'name': 'Google Gemini', 'key': 'GOOGLE_AI_KEY', 'aliases': ('GEMINI_API_KEY', 'GOOGLE_API_KEY'), 'keys_url': 'https://aistudio.google.com/apikey'},
    'groq': {'name': 'Groq', 'key': 'GROQ_API_KEY', 'keys_url': 'https://console.groq.com/keys'},
    'mistral': {'name': 'Mistral', 'key': 'MISTRAL_API_KEY', 'keys_url': 'https://console.mistral.ai/api-keys'},
    'deepseek': {'name': 'DeepSeek', 'key': 'DEEPSEEK_API_KEY', 'keys_url': 'https://platform.deepseek.com/api_keys'},
    'huggingface': {'name': 'Hugging Face (Hosted Chat API)', 'key': 'HF_TOKEN', 'aliases': ('HUGGINGFACE_API_KEY',),
        'keys_url': 'https://huggingface.co/settings/tokens', 'models_url': 'https://huggingface.co/inference/models',
        'catalog_url': 'https://router.huggingface.co/v1/models', 'chat_url': 'https://router.huggingface.co/v1/chat/completions',
        'scope': 'Hosted chat API models; runnable chat defaults via BYOK HF_TOKEN', 'public_catalog': True},
    'huggingface_inference': {'name': 'Hugging Face — Inference Available', 'key': 'HF_TOKEN', 'aliases': ('HUGGINGFACE_API_KEY',),
        'keys_url': 'https://huggingface.co/settings/tokens', 'models_url': 'https://huggingface.co/models?inference_provider=all',
        'catalog_url': 'https://huggingface.co/api/models', 'chat_url': 'https://router.huggingface.co/v1/chat/completions',
        'scope': 'Hugging Face Hub "Inference Available" (57k+); live chat, text-to-image & text-to-video models runnable via BYOK HF_TOKEN', 'public_catalog': True},
    'huggingface_hub': {'name': 'Hugging Face — Full Hub', 'key': 'HF_TOKEN', 'aliases': ('HUGGINGFACE_API_KEY',),
        'keys_url': 'https://huggingface.co/settings/tokens', 'models_url': 'https://huggingface.co/models',
        'catalog_url': 'https://huggingface.co/api/models', 'chat_url': 'https://router.huggingface.co/v1/chat/completions',
        'scope': 'Full Hugging Face Hub (~3M repos); live HF Inference, custom JSON endpoint, or local Ollama GGUF models runnable', 'public_catalog': True},
    'together': {'name': 'Together AI', 'key': 'TOGETHER_API_KEY',
        'keys_url': 'https://api.together.xyz/settings/api-keys', 'models_url': 'https://www.together.ai/models',
        'catalog_url': 'https://api.together.xyz/v1/models', 'chat_url': 'https://api.together.xyz/v1/chat/completions',
        'scope': 'API model catalog'},
    'fireworks': {'name': 'Fireworks AI', 'key': 'FIREWORKS_API_KEY',
        'keys_url': 'https://app.fireworks.ai/settings/users/api-keys', 'models_url': 'https://fireworks.ai/models',
        'catalog_url': 'https://api.fireworks.ai/v1/accounts/fireworks/models', 'chat_url': 'https://api.fireworks.ai/inference/v1/chat/completions',
        'scope': 'Public Fireworks account model catalog; some models need deployment'},
    'replicate': {'name': 'Replicate', 'key': 'REPLICATE_API_TOKEN',
        'keys_url': 'https://replicate.com/account/api-tokens', 'models_url': 'https://replicate.com/explore',
        'catalog_url': 'https://api.replicate.com/v1/models', 'scope': 'Public API catalog, loaded in pages'},
    'wavespeed': {'name': 'WaveSpeedAI', 'key': 'WAVESPEED_API_KEY',
        'keys_url': 'https://wavespeed.ai/accesskey', 'models_url': 'https://wavespeed.ai/models',
        'catalog_url': 'https://api.wavespeed.ai/api/v3/models', 'scope': 'API media catalog'},
    'novita': {'name': 'Novita AI', 'key': 'NOVITA_API_KEY',
        'keys_url': 'https://novita.ai/settings/key-management', 'models_url': 'https://novita.ai/models',
        'catalog_url': 'https://api.novita.ai/openai/v1/models', 'chat_url': 'https://api.novita.ai/openai/v1/chat/completions',
        'scope': 'LLM API catalog; not the full media marketing catalog', 'public_catalog': True},
    'ollama': {'name': 'Ollama (local)', 'key': None, 'keys_url': 'https://ollama.com/download'},
}


def credential_path():
    from kurt.utils.env_loader import ENV_PATH
    return ENV_PATH


def usable_key(value):
    return (isinstance(value, str) and bool(value.strip()) and
            value.strip().lower() not in ('none', 'null', 'changeme', 'your-key', 'your_api_key') and
            not re.search(r'your[_ -]|placeholder|replace[_ -]?me|^<.*>$|\$\{', value, re.I))


def provider_key(provider):
    spec = PROVIDERS[provider]
    if not spec['key']:
        return ''
    from dotenv import dotenv_values
    path = credential_path()
    saved = dotenv_values(path, interpolate=False) if path.is_file() else {}
    names = (spec['key'], *spec.get('aliases', ()))
    # An explicit saved value, including a cleared/placeholder key, wins over
    # inherited credentials. Key rotation takes effect without restarting Kurt.
    for name in names:
        if name in saved:
            value = saved[name]
            return value.strip() if usable_key(value) else ''
    for name in names:
        if usable_key(os.environ.get(name)):
            return os.environ[name].strip()
    return ''


def save_provider_key(provider, value):
    """Private atomic write; preserve unrelated environment entries verbatim."""
    spec = PROVIDERS[provider]
    value = value.strip() if isinstance(value, str) else value
    if not spec['key']:
        raise ValueError('This local provider does not require an API key.')
    if (not isinstance(value, str) or not usable_key(value) or len(value) > 4096 or
            any(c.isspace() or ord(c) < 32 for c in value) or not value.isascii()):
        raise ValueError('Enter one nonempty API key/token, without spaces, placeholders or control characters.')
    from kurt.utils.security import write_private_text, register_secrets
    path = credential_path()
    original = path.read_text() if path.is_file() else ''
    names = {spec['key'], *spec.get('aliases', ())}
    retained = [line for line in original.splitlines(keepends=True)
                if not any(re.match(r'^\s*(?:export\s+)?' + re.escape(name) + r'\s*=', line) for name in names)]
    body = ''.join(retained)
    if body and not body.endswith('\n'):
        body += '\n'
    escaped = value.replace('\\', '\\\\').replace("'", "\\'")
    write_private_text(path, body + spec['key'] + "='" + escaped + "'\n")
    for name in names:
        os.environ.pop(name, None)
    os.environ[spec['key']] = value
    register_secrets([value])


def uses_byok(provider):
    if provider in BYOK_ONLY_PROVIDERS:
        return True
    if provider in PROVIDERS:
        from kurt.core.persona import load_persona
        return provider in load_persona().get('byok_providers', [])
    return False


def confirm_byok(provider):
    """Explicit key selection opts this provider out of wallet billing."""
    if provider in PROVIDERS and PROVIDERS[provider]['key']:
        value = provider_key(provider)
        if not value:
            raise ValueError('Add a provider key before choosing BYOK.')
        spec = PROVIDERS[provider]
        for name in (spec['key'], *spec.get('aliases', ())):
            os.environ.pop(name, None)
        os.environ[spec['key']] = value
        from kurt.core.persona import load_persona, save_persona
        settings = load_persona()
        settings['byok_providers'] = sorted(set(settings.get('byok_providers', [])) | {provider})
        save_persona(settings)


def request_provider_key(provider):
    from rich.prompt import Prompt
    value = Prompt.ask(f"{PROVIDERS[provider]['name']} API key (hidden; blank cancels)", password=True, default='', show_default=False)
    if not value:
        return 'Cancelled; no key changed.'
    save_provider_key(provider, value)
    return 'API key saved privately. Authentication and available credits are not yet verified.'


def confirm_wallet(provider):
    if provider in BYOK_ONLY_PROVIDERS:
        raise ValueError('This optional provider requires your own API key.')
    from kurt.core.persona import load_persona, save_persona
    settings = load_persona()
    settings['byok_providers'] = [p for p in settings.get('byok_providers', []) if p != provider]
    save_persona(settings)


MAX_MODEL_CONFIG_BYTES = 1024 * 1024


def model_config_path():
    return credential_path().parent / 'model_configs.json'


def load_model_configs():
    import json
    path = model_config_path()
    try:
        data = json.loads(path.read_text()) if path.is_file() else {}
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _config_key(provider, mid=''):
    return f'{provider}:{mid}' if mid else provider


def get_model_config(provider, mid=''):
    return load_model_configs().get(_config_key(provider, mid))


def _validated_custom_base_url(value):
    from urllib.parse import urlsplit
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().rstrip('/')
    parsed = urlsplit(raw)
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        return None
    host = parsed.hostname.lower()
    if parsed.scheme == 'https':
        return raw
    if parsed.scheme == 'http' and host in ('localhost', '127.0.0.1', '::1'):
        return raw
    return None


def custom_endpoint_config(provider, mid=''):
    """Return a validated runnable custom endpoint from saved model JSON config, if configured."""
    entry = get_model_config(provider, mid) or (get_model_config(provider) if mid else None)
    cfg = entry.get('config') if isinstance(entry, dict) else None
    if not isinstance(cfg, dict):
        return None
    base_url = _validated_custom_base_url(cfg.get('base_url') or cfg.get('endpoint') or cfg.get('url'))
    if not base_url:
        return None
    raw_roles = cfg.get('roles')
    if isinstance(raw_roles, list):
        roles = [r.strip().lower() for r in raw_roles if isinstance(r, str) and r.strip().lower() in ('chat', 'image')]
    elif isinstance(cfg.get('role'), str) and cfg['role'].strip().lower() in ('chat', 'image'):
        roles = [cfg['role'].strip().lower()]
    else:
        roles = ['chat']
    if not roles:
        roles = ['chat']
    api_key = cfg.get('api_key') or cfg.get('token') or ''
    api_key = api_key.strip() if isinstance(api_key, str) and usable_key(api_key) else ''
    headers = {}
    if isinstance(cfg.get('headers'), dict):
        for k, v in cfg['headers'].items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and '\n' not in k and '\r' not in k and '\n' not in v and '\r' not in v:
                headers[k.strip()] = v.strip()
    model_name = cfg.get('model') if isinstance(cfg.get('model'), str) and cfg['model'].strip() else mid
    return {
        'base_url': base_url,
        'api_key': api_key,
        'model': model_name,
        'roles': list(dict.fromkeys(roles)),
        'headers': headers,
    }


def custom_endpoint_roles(provider, mid=''):
    cfg = custom_endpoint_config(provider, mid)
    return list(cfg['roles']) if cfg else []


def _collect_secret_strings(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            if any(tok in key for tok in ('key', 'token', 'secret', 'auth', 'password')):
                if isinstance(v, str) and len(v.strip()) >= 6:
                    out.append(v.strip())
            elif key in ('env', 'headers') and isinstance(v, dict):
                for ev in v.values():
                    if isinstance(ev, str) and len(ev.strip()) >= 6:
                        out.append(ev.strip())
            else:
                _collect_secret_strings(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_secret_strings(item, out)


def _read_json_input(raw_input):
    import json
    from pathlib import Path
    if not isinstance(raw_input, str) or not raw_input.strip():
        raise ValueError('Paste a JSON object or enter a path to a .json file.')
    text = raw_input.strip()
    if not text.startswith('{'):
        candidate = text.strip('\'"')
        if candidate.startswith('file://'):
            from urllib.parse import urlsplit, unquote
            candidate = unquote(urlsplit(candidate).path)
        path = Path(candidate).expanduser()
        if not path.is_file():
            raise ValueError('Invalid JSON object and file path not found.')
        if path.stat().st_size > MAX_MODEL_CONFIG_BYTES:
            raise ValueError('JSON config file exceeds the 1 MB limit.')
        text = path.read_text(encoding='utf-8')
    if len(text.encode('utf-8')) > MAX_MODEL_CONFIG_BYTES:
        raise ValueError('JSON config exceeds the 1 MB limit.')
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise ValueError('Invalid JSON syntax; enter a valid JSON object.') from exc
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError('JSON config must be a nonempty JSON object.')
    return parsed, text


def save_model_json_config(provider, mid, raw_input):
    """Save a custom model / GitHub repo JSON config privately, or import mcpServers."""
    import json
    if provider not in PROVIDERS:
        raise ValueError('Unknown provider.')
    parsed, raw_text = _read_json_input(raw_input)
    secrets = []
    _collect_secret_strings(parsed, secrets)
    from kurt.utils.security import write_private_text, register_secrets
    if secrets:
        register_secrets(secrets)
    if 'mcpServers' in parsed:
        from kurt.core import mcp_catalog
        from kurt.core.mcp_client import load_registry, save_registry
        conns = mcp_catalog.parse_config(raw_text)
        if not conns:
            raise ValueError('No valid MCP servers found in mcpServers JSON.')
        registry = load_registry()
        names = []
        for conn in conns:
            registry[conn.name] = conn
            names.append(conn.name)
        save_registry(registry)
        return {'kind': 'mcp', 'names': names,
                'message': f'Imported {len(names)} MCP server config(s) privately ({", ".join(names)}). No commands executed.'}
    configs = load_model_configs()
    entry_key = _config_key(provider, mid)
    configs[entry_key] = {
        'provider': provider,
        'model': mid or '',
        'config': parsed,
    }
    write_private_text(model_config_path(), json.dumps(configs, indent=2, ensure_ascii=False) + '\n')
    target_label = mid or PROVIDERS[provider]['name']
    return {'kind': 'model_config', 'key': entry_key,
            'message': f'JSON config saved privately for {target_label} (0600). No commands executed.'}


def delete_model_config(provider, mid=''):
    import json
    from kurt.utils.security import write_private_text
    configs = load_model_configs()
    entry_key = _config_key(provider, mid)
    if entry_key not in configs:
        return False
    configs.pop(entry_key, None)
    write_private_text(model_config_path(), json.dumps(configs, indent=2, ensure_ascii=False) + '\n')
    return True
