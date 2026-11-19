"""
KURT Env Loader - Nag-loload ng API keys mula sa ~/.kurt/.env
"""

import os
from pathlib import Path

KURT_DIR = Path.home() / ".kurt"
ENV_PATH = KURT_DIR / ".env"


def load_env():
    """Load environment variables from ~/.kurt/.env"""
    if not ENV_PATH.exists():
        return False

    from dotenv import dotenv_values
    for key, value in dotenv_values(ENV_PATH).items():
        if value is None:
            continue
        existing = os.environ.get(key, "")
        prefixes = ("sk-or-v1-your", "AIzaSy-your", "gsk_your", "sk-your", "sk-ant-your", "your-key", "r8_your")
        if not existing or existing.startswith(prefixes):
            os.environ[key] = value

    return True


def setup_api_key(variable):
    """Read one configured provider key without stale inherited env precedence."""
    if variable not in {'MISTRAL_API_KEY', 'DEEPSEEK_API_KEY', 'TAVILY_API_KEY'}:
        raise ValueError('Unsupported setup credential.')
    if not ENV_PATH.is_file(): return ''
    from dotenv import dotenv_values
    value = dotenv_values(ENV_PATH, interpolate=False).get(variable)
    return value.strip() if isinstance(value, str) else ''


def setup_mistral_key():
    return setup_api_key('MISTRAL_API_KEY')


def check_setup() -> dict:
    """Check which providers are configured"""
    load_env()

    providers = {
        # AI Models
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "google": bool(os.getenv("GOOGLE_AI_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mistral": bool(os.getenv("MISTRAL_API_KEY")),
        "fal": bool(os.getenv("FAL_API_KEY")),
        "replicate": bool(os.getenv("REPLICATE_API_TOKEN")),
        "ollama": True,
        "huggingface": bool(os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_API_KEY')),
        "together": bool(os.getenv('TOGETHER_API_KEY')),
        "fireworks": bool(os.getenv('FIREWORKS_API_KEY')),
        "wavespeed": bool(os.getenv('WAVESPEED_API_KEY')),
        "novita": bool(os.getenv('NOVITA_API_KEY')),
        # Connectors
        "composio": bool(os.getenv("COMPOSIO_API_KEY")),
        "zapier": bool(os.getenv("ZAPIER_NLA_API_KEY")),
        "n8n": bool(os.getenv("N8N_API_KEY")),
        # Search
        "serper": bool(os.getenv("SERPER_API_KEY")),
        "brave": bool(os.getenv("BRAVE_API_KEY")),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        # Communication
        "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        # Data & Dev
        "supabase": bool(os.getenv("SUPABASE_KEY")),
        "github": bool(os.getenv("GITHUB_TOKEN")),
    }

    return providers
