"""
KURT Setup Wizard - One-time configuration
Nag-aask ng API keys at nag-se-save sa ~/.kurt/.env
"""

import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
ENV_PATH = KURT_DIR / ".env"

API_PROVIDERS = [
    # ══════════════════════════════════════
    # AI MODELS
    # ══════════════════════════════════════
    {
        "section": "🤖 AI MODELS",
        "name": "OpenRouter",
        "key": "OPENROUTER_API_KEY",
        "description": "🔥 PINAKA-IMPORTANTE! 1 key = lahat ng AI models",
        "url": "https://openrouter.ai/keys",
        "required": True,
        "free": True,
        "free_note": "May libre na models! (LLaMA, Gemini, DeepSeek)",
    },
    {
        "name": "Google AI Studio (Gemini)",
        "key": "GOOGLE_AI_KEY",
        "description": "Gemini Flash — 1M context, libre 1,500 req/day!",
        "url": "https://aistudio.google.com/apikey",
        "required": False,
        "free": True,
        "free_note": "Libre! 1,500 requests/day",
    },
    {
        "name": "Groq",
        "key": "GROQ_API_KEY",
        "description": "LLaMA + DeepSeek — SOBRANG BILIS, libre!",
        "url": "https://console.groq.com/keys",
        "required": False,
        "free": True,
        "free_note": "Libre! 14,400 requests/day",
    },
    {
        "name": "DeepSeek",
        "key": "DEEPSEEK_API_KEY",
        "description": "Best coding AI — $2 free credits, $0.014/1M tokens",
        "url": "https://platform.deepseek.com/api_keys",
        "required": False,
        "free": True,
        "free_note": "$2 libre credits sa signup!",
    },
    {
        "name": "OpenAI (ChatGPT)",
        "key": "OPENAI_API_KEY",
        "description": "GPT-4o, o1, DALL-E, Whisper — Computer Use",
        "url": "https://platform.openai.com/api-keys",
        "required": False,
        "free": False,
        "free_note": "$5 libre credits sa signup",
    },
    {
        "name": "Anthropic (Claude)",
        "key": "ANTHROPIC_API_KEY",
        "description": "Claude 3.5 — best writing/coding + Computer Use API",
        "url": "https://console.anthropic.com/settings/keys",
        "required": False,
        "free": False,
        "free_note": "$5 libre credits sa signup",
    },
    {
        "name": "Mistral",
        "key": "MISTRAL_API_KEY",
        "description": "Mistral Large, Codestral — magaling sa code",
        "url": "https://console.mistral.ai/api-keys",
        "required": False,
        "free": True,
        "free_note": "May libre tier!",
    },
    {
        "name": "fal.ai (Images/Video)",
        "key": "FAL_API_KEY",
        "description": "Flux image generation — mabilis at mura",
        "url": "https://fal.ai/dashboard/keys",
        "required": False,
        "free": False,
        "free_note": "$1 libre credits",
    },
    {
        "name": "Replicate (Media AI)",
        "key": "REPLICATE_API_TOKEN",
        "description": "MusicGen, Video AI, Image AI",
        "url": "https://replicate.com/account/api-tokens",
        "required": False,
        "free": False,
        "free_note": "Pay per use, mura lang",
    },
    # ══════════════════════════════════════
    # CONNECTORS / AUTOMATION
    # ══════════════════════════════════════
    {
        "section": "🔌 CONNECTORS & AUTOMATION",
        "name": "Composio",
        "key": "COMPOSIO_API_KEY",
        "description": "250+ app connectors — Gmail, Notion, GitHub, Shopee at iba pa!",
        "url": "https://app.composio.dev/settings",
        "required": False,
        "free": True,
        "free_note": "Libre tier available! 1 key = 250+ apps",
    },
    {
        "name": "Zapier (MCP/NLA)",
        "key": "ZAPIER_NLA_API_KEY",
        "description": "7,000+ app automations via Zapier",
        "url": "https://nla.zapier.com/settings/",
        "required": False,
        "free": True,
        "free_note": "May libre tier — 100 tasks/month",
    },
    {
        "name": "n8n (Self-hosted)",
        "key": "N8N_API_KEY",
        "description": "Trigger your existing n8n workflows from KURT",
        "url": "http://localhost:5678/settings/api",
        "required": False,
        "free": True,
        "free_note": "Libre — self-hosted mo na ito!",
    },
    {
        "name": "n8n Host URL",
        "key": "N8N_HOST",
        "description": "URL ng iyong n8n instance",
        "url": "http://localhost:5678",
        "required": False,
        "free": True,
        "free_note": "Default: http://localhost:5678",
    },
    # ══════════════════════════════════════
    # SEARCH & DATA
    # ══════════════════════════════════════
    {
        "section": "🔍 SEARCH & DATA",
        "name": "Serper (Google Search)",
        "key": "SERPER_API_KEY",
        "description": "Real Google search results — para sa research tasks",
        "url": "https://serper.dev/api-key",
        "required": False,
        "free": True,
        "free_note": "2,500 libre searches sa signup!",
    },
    {
        "name": "Brave Search",
        "key": "BRAVE_API_KEY",
        "description": "Privacy-focused web search",
        "url": "https://api.search.brave.com/register",
        "required": False,
        "free": True,
        "free_note": "2,000 libre queries/month",
    },
    {
        "name": "Tavily (AI Search)",
        "key": "TAVILY_API_KEY",
        "description": "AI-optimized search — mas magaling sa research",
        "url": "https://app.tavily.com/",
        "required": False,
        "free": True,
        "free_note": "1,000 libre searches/month",
    },
    # ══════════════════════════════════════
    # COMMUNICATION
    # ══════════════════════════════════════
    {
        "section": "📧 COMMUNICATION",
        "name": "Telegram Bot",
        "key": "TELEGRAM_BOT_TOKEN",
        "description": "Send/receive messages via Telegram — notify ka ng KURT",
        "url": "https://t.me/botfather",
        "required": False,
        "free": True,
        "free_note": "Libre! Kausapin si @BotFather sa Telegram",
    },
    {
        "name": "Telegram Chat ID",
        "key": "TELEGRAM_CHAT_ID",
        "description": "Ang iyong Telegram user/chat ID",
        "url": "https://t.me/userinfobot",
        "required": False,
        "free": True,
        "free_note": "Libre! Kausapin si @userinfobot",
    },
    # ══════════════════════════════════════
    # ECOMMERCE & SOCIAL
    # ══════════════════════════════════════
    {
        "section": "🛒 ECOMMERCE & SOCIAL",
        "name": "Supabase",
        "key": "SUPABASE_KEY",
        "description": "Database para sa KURT projects at VCore",
        "url": "https://supabase.com/dashboard/account/tokens",
        "required": False,
        "free": True,
        "free_note": "Libre tier — 500MB database",
    },
    {
        "name": "Supabase URL",
        "key": "SUPABASE_URL",
        "description": "URL ng iyong Supabase project",
        "url": "https://supabase.com/dashboard",
        "required": False,
        "free": True,
        "free_note": "Makikita sa project settings",
    },
    {
        "name": "GitHub Token",
        "key": "GITHUB_TOKEN",
        "description": "Para sa kurt code — auto-commit, create repos, etc.",
        "url": "https://github.com/settings/tokens",
        "required": False,
        "free": True,
        "free_note": "Libre — personal access token",
    },
]


def run_setup():
    """Run the KURT setup wizard"""
    console.clear()

    # Banner
    console.print(Panel.fit(
        "[bold cyan]🤖 KURT SETUP WIZARD[/bold cyan]\n"
        "[dim]Personal AI Orchestrator — Kinetic Unified Response Terminal[/dim]",
        box=box.DOUBLE,
        border_style="cyan",
    ))

    console.print()
    console.print("[yellow]Mag-setup tayo ng API keys para sa lahat ng AI models![/yellow]")
    console.print("[dim]Tips: Libre muna ang pinakamahalagang providers. Skip ang hindi needed.[/dim]")
    console.print()

    # Create .kurt directory
    KURT_DIR.mkdir(exist_ok=True)

    # Load existing keys
    existing = {}
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    existing[key.strip()] = val.strip()

    new_keys = dict(existing)
    skip_all = False

    for i, provider in enumerate(API_PROVIDERS, 1):
        # Print section header if present
        if provider.get("section"):
            console.print()
            console.print(f"[bold yellow]{'═' * 50}[/bold yellow]")
            console.print(f"[bold yellow]  {provider['section']}[/bold yellow]")
            console.print(f"[bold yellow]{'═' * 50}[/bold yellow]")

        console.print(f"[bold cyan]{'─' * 50}[/bold cyan]")
        console.print(
            f"[bold white][{i}/{len(API_PROVIDERS)}] {provider['name']}[/bold white]"
        )
        console.print(f"  [dim]{provider['description']}[/dim]")

        # Free badge
        if provider["free"]:
            console.print(f"  [green]✅ {provider['free_note']}[/green]")
        else:
            console.print(f"  [yellow]💳 {provider['free_note']}[/yellow]")

        console.print(f"  [blue]🔗 Get key: {provider['url']}[/blue]")

        # Flag an existing key WITHOUT showing any of its characters on screen
        # or leaving them in terminal scrollback — only the owner running
        # setup should ever see key material, and only while typing it in.
        current = existing.get(provider["key"], "")
        if current:
            console.print(f"  [green]✅ Already configured[/green]")
            if not Confirm.ask(f"  Update this key?", default=False):
                console.print()
                continue

        # Required vs optional
        if provider["required"]:
            prompt_text = f"  [bold red]*Required*[/bold red] Paste your {provider['name']} key"
        else:
            prompt_text = f"  Paste your {provider['name']} key (Enter to skip)"

        key_value = Prompt.ask(prompt_text, default="", password=True)

        if key_value:
            new_keys[provider["key"]] = key_value
            console.print(f"  [green]✅ Saved![/green]")
        else:
            if provider["required"]:
                console.print(
                    f"  [red]⚠️  OpenRouter key is required for KURT to work![/red]"
                )
                console.print(
                    f"  [dim]Get it free at: {provider['url']}[/dim]"
                )
            else:
                console.print(f"  [dim]Skipped.[/dim]")

        console.print()

    # Ollama config
    console.print(f"[bold cyan]{'─' * 50}[/bold cyan]")
    console.print("[bold white][Bonus] Ollama (Local AI - Offline Mode)[/bold white]")
    console.print("  [dim]Para mag-work kahit walang internet![/dim]")
    console.print("  [green]✅ Libre, walang API key — local lang sa computer mo[/green]")

    ollama_host = existing.get("OLLAMA_HOST", "http://localhost:11434")
    custom_ollama = Prompt.ask(
        "  Ollama host URL",
        default=ollama_host
    )
    new_keys["OLLAMA_HOST"] = custom_ollama
    console.print()

    # Save to .env file
    with open(ENV_PATH, "w") as f:
        f.write("# KURT Configuration\n")
        f.write("# Auto-generated by kurt setup\n")
        f.write("# DO NOT SHARE THIS FILE!\n\n")

        for key, value in new_keys.items():
            f.write(f"{key}={value}\n")

    # Summary
    console.print(Panel.fit(
        "[bold green]✅ KURT Setup Complete![/bold green]\n\n"
        f"[dim]Config saved to: {ENV_PATH}[/dim]\n\n"
        "[white]Pwede ka na magsimula:[/white]\n"
        "[cyan]  kurt \"hello world\"[/cyan]\n"
        "[cyan]  kurt \"gumawa ng snake game\"[/cyan]\n"
        "[cyan]  kurt \"research viral products ngayon\"[/cyan]",
        box=box.ROUNDED,
        border_style="green",
    ))

    # Count configured keys
    configured = sum(1 for p in API_PROVIDERS if new_keys.get(p["key"]))
    console.print(
        f"\n[dim]Configured {configured}/{len(API_PROVIDERS)} providers. "
        f"Run [cyan]kurt models[/cyan] to see all available models.[/dim]"
    )
