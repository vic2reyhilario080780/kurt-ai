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
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value

    return True


def check_setup() -> dict:
    """Check which providers are configured"""
    load_env()

    providers = {
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "google": bool(os.getenv("GOOGLE_AI_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mistral": bool(os.getenv("MISTRAL_API_KEY")),
        "fal": bool(os.getenv("FAL_API_KEY")),
        "replicate": bool(os.getenv("REPLICATE_API_TOKEN")),
        "ollama": True,  # Always available if installed
    }

    return providers
