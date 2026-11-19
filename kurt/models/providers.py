"""Official provider endpoints and local BYOK credential management."""
import os
import re

EXTRA_PROVIDERS = ('huggingface', 'together', 'fireworks', 'replicate', 'wavespeed', 'novita')
NEW_BYOK_PROVIDERS = frozenset(EXTRA_PROVIDERS) - {'replicate'}

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
    'huggingface': {'name': 'Hugging Face', 'key': 'HF_TOKEN', 'aliases': ('HUGGINGFACE_API_KEY',),
        'keys_url': 'https://huggingface.co/settings/tokens', 'models_url': 'https://huggingface.co/inference/models',
        'catalog_url': 'https://router.huggingface.co/v1/models', 'chat_url': 'https://router.huggingface.co/v1/chat/completions',
        'scope': 'Hosted chat API models; not every repository on the Hub', 'public_catalog': True},
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
    if provider in NEW_BYOK_PROVIDERS:
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
    if provider in NEW_BYOK_PROVIDERS:
        raise ValueError('This optional provider requires your own API key.')
    from kurt.core.persona import load_persona, save_persona
    settings = load_persona()
    settings['byok_providers'] = [p for p in settings.get('byok_providers', []) if p != provider]
    save_persona(settings)
