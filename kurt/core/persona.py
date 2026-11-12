"""
KURT Persona — Personalization & Config System
Nag-hahandle ng lahat ng settings para ma-personalize si KURT:
  - Color palette & themes
  - Icons
  - Fonts (Rich markup styles)
  - Background/border styles
  - User name & greeting
  - Language / output language
  - Project context (KURT hybrid: sariling logic + Claude)
"""

import json
import os
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
PERSONA_PATH = KURT_DIR / "persona.json"

# ══════════════════════════════════════════════════════════════
# BUILT-IN THEMES
# Each theme = Rich color names for primary, secondary, accent,
# border, dim, success, error, warning
# ══════════════════════════════════════════════════════════════
BUILTIN_THEMES = {
    "cyber": {
        "name": "Cyber (Default)",
        "primary": "bold cyan",
        "secondary": "cyan",
        "accent": "bold magenta",
        "border": "cyan",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim cyan",
        "banner_color": "bold cyan",
        "box_style": "ROUNDED",
        "emoji_prefix": "🤖",
        "background": "on #001414",
    },
    "neon": {
        "name": "Neon Pink",
        "primary": "bold magenta",
        "secondary": "magenta",
        "accent": "bold cyan",
        "border": "magenta",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim magenta",
        "banner_color": "bold magenta",
        "box_style": "DOUBLE",
        "emoji_prefix": "✨",
        "background": "on #15001a",
    },
    "matrix": {
        "name": "Matrix Green",
        "primary": "bold green",
        "secondary": "green",
        "accent": "bold yellow",
        "border": "green",
        "dim": "dim",
        "success": "bold bright_green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim green",
        "banner_color": "bold green",
        "box_style": "MINIMAL",
        "emoji_prefix": "🟢",
        "background": "on #000a00",
    },
    "gold": {
        "name": "Gold / Royal",
        "primary": "bold yellow",
        "secondary": "yellow",
        "accent": "bold white",
        "border": "yellow",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold orange1",
        "info": "dim yellow",
        "banner_color": "bold yellow",
        "box_style": "HEAVY",
        "emoji_prefix": "👑",
        "background": "on #1a1500",
    },
    "minimal": {
        "name": "Minimal White",
        "primary": "bold white",
        "secondary": "white",
        "accent": "bold cyan",
        "border": "white",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim white",
        "banner_color": "bold white",
        "box_style": "SIMPLE",
        "emoji_prefix": "◆",
        "background": "",
    },
    "sunset": {
        "name": "Sunset Orange",
        "primary": "bold orange1",
        "secondary": "orange1",
        "accent": "bold red",
        "border": "orange1",
        "dim": "dim",
        "success": "bold green",
        "error": "bold bright_red",
        "warning": "bold yellow",
        "info": "dim orange1",
        "banner_color": "bold orange1",
        "box_style": "ROUNDED",
        "emoji_prefix": "🌅",
        "background": "on #1a0a00",
    },
    "ocean": {
        "name": "Ocean Blue",
        "primary": "bold blue",
        "secondary": "blue",
        "accent": "bold cyan",
        "border": "blue",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim blue",
        "banner_color": "bold blue",
        "box_style": "ROUNDED",
        "emoji_prefix": "🌊",
        "background": "on #00091a",
    },
    "pinoy": {
        "name": "Pinoy — Blue, Red, Yellow",
        "primary": "bold blue",
        "secondary": "bold red",
        "accent": "bold yellow",
        "border": "blue",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim blue",
        "banner_color": "bold blue",
        "box_style": "ROUNDED",
        "emoji_prefix": "🇵🇭",
        "background": "on #00071a",
    },
}

# ══════════════════════════════════════════════════════════════
# SUPPORTED LANGUAGES
# key = language code, value = display info + system instruction
# ══════════════════════════════════════════════════════════════
SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "flag": "🇺🇸",
        "system_prompt": "Always respond in English.",
        "greeting_templates": [
            "Hello, {name}! How can I help you today?",
            "Hey {name}! What can I do for you?",
            "Good to see you, {name}! What's on your mind?",
        ],
        "kurt_label": "KURT",
    },
    "tl": {
        "name": "Filipino / Tagalog",
        "flag": "🇵🇭",
        "system_prompt": "Sumagot ka palagi sa Filipino/Tagalog. Pwedeng Taglish (mix ng Tagalog at English) para sa natural na pagkakataon.",
        "greeting_templates": [
            "Kumusta, {name}! Ano ang maipaglilingkod ko sa iyo?",
            "Hoy {name}! Ano'ng kailangan mo?",
            "Musta {name}! Anong pinaplano mo ngayon?",
        ],
        "kurt_label": "KURT",
    },
    "taglish": {
        "name": "Taglish (Mix)",
        "flag": "🇵🇭",
        "system_prompt": "Sumagot ka sa Taglish — natural na halo ng Tagalog at English, tulad ng tunay na pakikipag-usap ng mga Pilipino. Huwag i-translate nang literal — gamitin ang natural na Taglish flow.",
        "greeting_templates": [
            "Hoy {name}! Ano'ng kailangan mo ngayon?",
            "Kumusta {name}! What can I do for you?",
            "Hey {name}, musta! Anong task natin today?",
        ],
        "kurt_label": "KURT",
    },
    "ja": {
        "name": "日本語 (Japanese)",
        "flag": "🇯🇵",
        "system_prompt": "常に日本語で返答してください。",
        "greeting_templates": [
            "{name}さん、こんにちは！何かお手伝いできますか？",
            "やあ{name}！今日は何をしましょうか？",
        ],
        "kurt_label": "KURT",
    },
    "zh": {
        "name": "中文 (Chinese)",
        "flag": "🇨🇳",
        "system_prompt": "请始终用中文回答。",
        "greeting_templates": [
            "{name}，你好！有什么我可以帮你的吗？",
            "嗨{name}！今天需要什么帮助？",
        ],
        "kurt_label": "KURT",
    },
    "es": {
        "name": "Español (Spanish)",
        "flag": "🇪🇸",
        "system_prompt": "Responde siempre en español.",
        "greeting_templates": [
            "¡Hola, {name}! ¿En qué puedo ayudarte hoy?",
            "¡Hey {name}! ¿Qué necesitas?",
        ],
        "kurt_label": "KURT",
    },
    "ko": {
        "name": "한국어 (Korean)",
        "flag": "🇰🇷",
        "system_prompt": "항상 한국어로 답해주세요.",
        "greeting_templates": [
            "{name}님, 안녕하세요! 무엇을 도와드릴까요?",
            "안녕 {name}! 오늘 무엇이 필요하세요?",
        ],
        "kurt_label": "KURT",
    },
}

# ══════════════════════════════════════════════════════════════
# BUILT-IN ICONS
# ══════════════════════════════════════════════════════════════
BUILTIN_ICONS = {
    "robot":    "🤖",
    "brain":    "🧠",
    "lightning":"⚡",
    "fire":     "🔥",
    "star":     "⭐",
    "diamond":  "💎",
    "crown":    "👑",
    "sword":    "⚔️",
    "shield":   "🛡️",
    "rocket":   "🚀",
    "alien":    "👽",
    "ghost":    "👻",
    "flag_ph":  "🇵🇭",
    "kurt_k":   "K",
    "dot":      "◆",
    "arrow":    "▶",
    "wave":     "🌊",
    "sun":      "☀️",
    "moon":     "🌙",
    "custom":   None,  # user provides their own emoji/char
}

# ══════════════════════════════════════════════════════════════
# DEFAULT PERSONA
# ══════════════════════════════════════════════════════════════
DEFAULT_PERSONA = {
    "version": "2.2",
    # Identity
    "user_name": "Boss",          # Paano tawaging ang user
    "kurt_name": "KURT",          # Pwedeng palitan ang pangalan ni KURT
    # Theme
    "theme": "cyber",             # Key from BUILTIN_THEMES
    "icon": "robot",              # Key from BUILTIN_ICONS
    "custom_icon": None,          # Kung "custom" ang icon, dito ilagay
    # Language
    "language": "taglish",        # Key from SUPPORTED_LANGUAGES
    # Greeting style
    "greeting_style": "casual",   # casual | professional | hype
    "custom_greeting": None,      # Kung gusto ng sariling greeting template
    # AI Mode (hybrid KURT + Claude)
    "ai_mode": "hybrid",          # hybrid | kurt_only | claude_only
    # Projects context (na-dedisplay sa banner)
    "active_projects": [],        # List of active projects for context
    # Misc
    "show_routing_info": False,   # Show model routing by default
    "compact_mode": False,        # Compact output
}


# ══════════════════════════════════════════════════════════════
# LOAD / SAVE / RESET
# ══════════════════════════════════════════════════════════════

def load_persona() -> dict:
    """Load persona from ~/.kurt/persona.json"""
    KURT_DIR.mkdir(exist_ok=True)
    if PERSONA_PATH.exists():
        try:
            with open(PERSONA_PATH) as f:
                saved = json.load(f)
            # Merge with defaults para hindi mawala ang bagong keys
            merged = {**DEFAULT_PERSONA, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_PERSONA)


def save_persona(persona: dict):
    """Save persona to ~/.kurt/persona.json"""
    KURT_DIR.mkdir(exist_ok=True)
    with open(PERSONA_PATH, "w") as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)


def reset_persona():
    """Reset to defaults"""
    save_persona(dict(DEFAULT_PERSONA))


# ══════════════════════════════════════════════════════════════
# GETTERS (shortcuts para sa main.py)
# ══════════════════════════════════════════════════════════════

def get_theme() -> dict:
    """Return current theme dict"""
    p = load_persona()
    return BUILTIN_THEMES.get(p.get("theme", "cyber"), BUILTIN_THEMES["cyber"])


def get_language() -> dict:
    """Return current language dict"""
    p = load_persona()
    return SUPPORTED_LANGUAGES.get(p.get("language", "taglish"), SUPPORTED_LANGUAGES["taglish"])


def get_user_name() -> str:
    p = load_persona()
    return p.get("user_name", "Boss")


def get_icon() -> str:
    p = load_persona()
    icon_key = p.get("icon", "robot")
    if icon_key == "custom":
        return p.get("custom_icon") or "🤖"
    return BUILTIN_ICONS.get(icon_key, "🤖") or "🤖"


def get_greeting() -> str:
    """Return personalized greeting for the user"""
    import random
    p = load_persona()
    name = p.get("user_name", "Boss")

    if p.get("custom_greeting"):
        return p["custom_greeting"].replace("{name}", name)

    lang = get_language()
    templates = lang.get("greeting_templates", ["Hey {name}!"])
    style = p.get("greeting_style", "casual")

    # Hype style — lahat ng templates + exclamation
    if style == "hype":
        tpl = random.choice(templates)
        return tpl.format(name=name).rstrip("!") + "!! 🔥"
    elif style == "professional":
        tpl = templates[0]  # First template is always most formal
        return tpl.format(name=name)
    else:
        tpl = random.choice(templates)
        return tpl.format(name=name)


def get_language_system_prompt() -> str:
    """Return system prompt instruction for language"""
    lang = get_language()
    return lang.get("system_prompt", "")


def get_ai_mode() -> str:
    p = load_persona()
    return p.get("ai_mode", "hybrid")


# ══════════════════════════════════════════════════════════════
# INTERACTIVE CONFIG WIZARD
# ══════════════════════════════════════════════════════════════

def config_show():
    """Display current persona config"""
    p = load_persona()
    theme = BUILTIN_THEMES.get(p.get("theme", "cyber"), BUILTIN_THEMES["cyber"])
    lang = SUPPORTED_LANGUAGES.get(p.get("language", "taglish"), SUPPORTED_LANGUAGES["taglish"])
    icon = get_icon()

    t = theme["primary"]

    table = Table(
        title=f"{icon} KURT Persona Config",
        box=box.ROUNDED,
        border_style=theme["border"],
        show_header=True,
        header_style=theme["primary"],
    )
    table.add_column("Setting", style=theme["secondary"], width=20)
    table.add_column("Value", style="white", width=30)
    table.add_column("Description", style=theme["dim"], width=35)

    table.add_row("User Name", p.get("user_name", "Boss"), "Kung paano kang tatawagin ni KURT")
    table.add_row("KURT Name", p.get("kurt_name", "KURT"), "Pangalan ni KURT")
    table.add_row("Theme", f"{p.get('theme','cyber')} — {theme['name']}", "Color palette")
    table.add_row("Icon", f"{icon} ({p.get('icon','robot')})", "KURT icon")
    table.add_row("Language", f"{lang['flag']} {lang['name']}", "Output language")
    table.add_row("Greeting Style", p.get("greeting_style", "casual"), "casual / professional / hype")
    table.add_row("AI Mode", p.get("ai_mode", "hybrid"), "hybrid / kurt_only / claude_only")
    table.add_row("Active Projects", ", ".join(p.get("active_projects", [])) or "—", "Projects for context")
    table.add_row("Compact Mode", str(p.get("compact_mode", False)), "Compact output")
    table.add_row("Show Routing", str(p.get("show_routing_info", False)), "Show model routing")

    console.print(table)
    console.print(f"\n[dim]Config file: {PERSONA_PATH}[/dim]")
    console.print(f"[dim]Edit directly or use: kurt setting <command>[/dim]")


def config_theme_wizard():
    """Interactive theme picker"""
    p = load_persona()
    console.print("\n[bold]🎨 Available Themes:[/bold]\n")

    for key, theme in BUILTIN_THEMES.items():
        current = " ← current" if key == p.get("theme") else ""
        prefix = theme.get("emoji_prefix", "●")
        bg = theme.get("background", "")
        swatch_style = f"{theme['primary']} {bg}".strip()
        console.print(f"  [{swatch_style}] {prefix} {key:12} — {theme['name']}{current} [/{swatch_style}]")

    console.print()
    choice = Prompt.ask(
        "Piliin ang theme",
        choices=list(BUILTIN_THEMES.keys()),
        default=p.get("theme", "cyber"),
    )
    p["theme"] = choice
    save_persona(p)
    theme = BUILTIN_THEMES[choice]
    console.print(f"[{theme['success']}]✅ Theme set to: {theme['name']}[/{theme['success']}]")


def config_language_wizard():
    """Interactive language picker"""
    p = load_persona()
    console.print("\n[bold]🌐 Available Languages:[/bold]\n")

    for key, lang in SUPPORTED_LANGUAGES.items():
        current = " ← current" if key == p.get("language") else ""
        console.print(f"  {lang['flag']}  [cyan]{key:12}[/cyan] — {lang['name']}{current}")

    console.print()
    choice = Prompt.ask(
        "Piliin ang language",
        choices=list(SUPPORTED_LANGUAGES.keys()),
        default=p.get("language", "taglish"),
    )
    p["language"] = choice
    save_persona(p)
    lang = SUPPORTED_LANGUAGES[choice]
    console.print(f"[bold green]✅ Language set to: {lang['flag']} {lang['name']}[/bold green]")
    console.print(f"[dim]KURT will now respond in: {lang['name']}[/dim]")


def config_name_wizard():
    """Set user name and greeting style"""
    p = load_persona()

    console.print("\n[bold cyan]👤 User Name & Greeting[/bold cyan]")
    name = Prompt.ask("Paano ka tatawagin ni KURT?", default=p.get("user_name", "Boss"))
    p["user_name"] = name

    kurt_name = Prompt.ask("Ano ang pangalan ni KURT?", default=p.get("kurt_name", "KURT"))
    p["kurt_name"] = kurt_name

    console.print("\n[bold]Greeting style:[/bold]")
    console.print("  [cyan]casual[/cyan]      — Relaxed, friendly")
    console.print("  [cyan]professional[/cyan] — Formal, respectful")
    console.print("  [cyan]hype[/cyan]         — Energetic, excited 🔥")

    style = Prompt.ask(
        "Greeting style",
        choices=["casual", "professional", "hype"],
        default=p.get("greeting_style", "casual"),
    )
    p["greeting_style"] = style

    custom = Prompt.ask(
        "Custom greeting template? (press Enter to skip, use {name} as placeholder)",
        default="",
    )
    p["custom_greeting"] = custom.strip() or None

    save_persona(p)
    console.print(f"\n[bold green]✅ Saved![/bold green]")
    console.print(f"[dim]Preview: {get_greeting()}[/dim]")


def config_icon_wizard():
    """Interactive icon picker"""
    p = load_persona()
    console.print("\n[bold]🎯 Available Icons:[/bold]\n")

    items = [(k, v) for k, v in BUILTIN_ICONS.items() if v is not None]
    for key, emoji in items:
        current = " ← current" if key == p.get("icon") else ""
        console.print(f"  {emoji}  [cyan]{key:12}[/cyan]{current}")
    console.print(f"  ?  [cyan]custom      [/cyan] — Provide your own emoji")

    all_keys = list(BUILTIN_ICONS.keys())
    choice = Prompt.ask("Piliin ang icon", choices=all_keys, default=p.get("icon", "robot"))
    p["icon"] = choice

    if choice == "custom":
        custom_icon = Prompt.ask("I-type ang iyong emoji/icon")
        p["custom_icon"] = custom_icon.strip()[:4]

    save_persona(p)
    console.print(f"[bold green]✅ Icon set to: {get_icon()}[/bold green]")


def config_aimode_wizard():
    """Set AI mode — hybrid KURT+Claude, kurt_only, claude_only"""
    p = load_persona()
    console.print("\n[bold cyan]🤖 AI Mode — KURT Hybrid System[/bold cyan]\n")

    console.print("[bold]hybrid[/bold]      — KURT's own routing + Claude as fallback/boost")
    console.print("               Pinaka-matalino: KURT decides which model, Claude assists")
    console.print()
    console.print("[bold]kurt_only[/bold]   — KURT lang gamit ang OpenRouter/Groq/Ollama")
    console.print("               Mas mabilis, mas mura, walang Claude API needed")
    console.print()
    console.print("[bold]claude_only[/bold] — Claude lang (Anthropic API required)")
    console.print("               Best quality, but needs ANTHROPIC_API_KEY")
    console.print()

    choice = Prompt.ask(
        "Piliin ang AI mode",
        choices=["hybrid", "kurt_only", "claude_only"],
        default=p.get("ai_mode", "hybrid"),
    )
    p["ai_mode"] = choice
    save_persona(p)
    console.print(f"\n[bold green]✅ AI Mode set to: {choice}[/bold green]")

    if choice == "hybrid":
        console.print("[dim]KURT will use its own routing AND leverage Claude for complex tasks.[/dim]")
    elif choice == "kurt_only":
        console.print("[dim]KURT will only use OpenRouter/Groq/Ollama providers.[/dim]")
    elif choice == "claude_only":
        console.print("[dim]KURT will route everything through Claude (Anthropic API).[/dim]")


def config_projects_wizard():
    """Set active projects for context"""
    p = load_persona()
    current = p.get("active_projects", [])

    console.print("\n[bold cyan]📁 Active Projects[/bold cyan]")
    console.print("[dim]These projects appear in KURT's banner and provide context.[/dim]\n")

    if current:
        console.print(f"Current projects: {', '.join(current)}")
    else:
        console.print("[dim]No active projects set.[/dim]")

    console.print("\nI-enter ang iyong mga projects (comma-separated):")
    console.print("[dim]Example: VCore, TikTok Agents, Sari-Sari POS, KURT[/dim]")

    raw = Prompt.ask("Projects", default=", ".join(current) if current else "")
    if raw.strip():
        projects = [x.strip() for x in raw.split(",") if x.strip()]
        p["active_projects"] = projects
    else:
        p["active_projects"] = []

    save_persona(p)
    console.print(f"[bold green]✅ Projects saved: {', '.join(p['active_projects']) or '—'}[/bold green]")


def config_full_wizard():
    """Full interactive config wizard"""
    p = load_persona()
    theme = BUILTIN_THEMES.get(p.get("theme", "cyber"), BUILTIN_THEMES["cyber"])

    console.print(Panel(
        f"[{theme['primary']}]KURT Personalization Wizard[/{theme['primary']}]\n"
        "[dim]I-customize ang iyong KURT experience[/dim]",
        box=box.ROUNDED,
        border_style=theme["border"],
    ))

    steps = [
        ("1. User Name & Greeting", config_name_wizard),
        ("2. Language", config_language_wizard),
        ("3. Theme & Colors", config_theme_wizard),
        ("4. Icon", config_icon_wizard),
        ("5. AI Mode (Hybrid)", config_aimode_wizard),
        ("6. Active Projects", config_projects_wizard),
    ]

    for label, fn in steps:
        console.print(f"\n[bold cyan]━━ {label} ━━[/bold cyan]")
        fn()

    console.print("\n")
    config_show()
    console.print(f"\n[bold green]🎉 KURT personalization complete![/bold green]")
    p2 = load_persona()
    icon = get_icon()
    greeting = get_greeting()
    console.print(f"{icon} {greeting}")
