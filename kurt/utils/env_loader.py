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

    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # .env file takes priority UNLESS the env var looks like a real key
                # (i.e., don't overwrite a key the user explicitly exported in their shell)
                existing = os.environ.get(key, "")
                placeholder_prefixes = (
                    "sk-or-v1-your", "AIzaSy-your", "gsk_your", "sk-your",
                    "sk-ant-your", "your-key", "r8_your", "",
                )
                existing_is_placeholder = not existing or any(
                    existing.startswith(p) for p in placeholder_prefixes
                )
                if existing_is_placeholder:
                    os.environ[key] = value

    return True


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
