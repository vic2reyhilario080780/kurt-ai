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

from kurt.core.themes import (
    BUILTIN_THEMES, BUILTIN_BACKGROUNDS, SUPPORTED_LANGUAGES,
    BUILTIN_ICONS, VOICE_PRESETS, DEFAULT_PERSONA,
)

console = Console()

KURT_DIR = Path.home() / ".kurt"
PERSONA_PATH = KURT_DIR / "persona.json"


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

def get_theme_bg_hex(p: Optional[dict] = None) -> str:
    """Return active background hex color (e.g. '#160a2b') or '' for terminal default."""
    import re
    if p is None:
        p = load_persona()
    bg_choice = (p.get("custom_background") or "theme").strip()
    if bg_choice == "none":
        return ""
    if bg_choice in BUILTIN_BACKGROUNDS and bg_choice != "theme":
        hx = BUILTIN_BACKGROUNDS[bg_choice]["hex"]
        return "" if hx == "none" else hx
    if re.fullmatch(r"#[0-9a-fA-F]{6}", bg_choice):
        return bg_choice.lower()
    base = BUILTIN_THEMES.get(p.get("theme", "cyber"), BUILTIN_THEMES["cyber"])
    return base.get("bg_hex", "")


def get_theme() -> dict:
    """Return current theme dict with resolved active background."""
    p = load_persona()
    theme = dict(BUILTIN_THEMES.get(p.get("theme", "cyber"), BUILTIN_THEMES["cyber"]))
    bg_hex = get_theme_bg_hex(p)
    theme["bg_hex"] = bg_hex
    theme["background"] = f"on {bg_hex}" if bg_hex else ""
    return theme


def set_theme(choice: str) -> str:
    key = (choice or "").strip().lower()
    if key not in BUILTIN_THEMES:
        raise ValueError("Choose theme: " + ", ".join(BUILTIN_THEMES.keys()))
    p = load_persona()
    p["theme"] = key
    save_persona(p)
    theme = BUILTIN_THEMES[key]
    return f"✅ Theme set to: {theme.get('emoji_prefix', '')} {theme['name']} (background: {get_theme_bg_hex(p) or 'terminal default'})"


def set_background(choice: str) -> str:
    import re
    key = (choice or "").strip().lower()
    if key not in BUILTIN_BACKGROUNDS and not re.fullmatch(r"#[0-9a-fA-F]{6}", key):
        raise ValueError("Choose background: " + ", ".join(BUILTIN_BACKGROUNDS.keys()) + " or #rrggbb")
    p = load_persona()
    p["custom_background"] = key
    save_persona(p)
    label = BUILTIN_BACKGROUNDS[key]["name"] if key in BUILTIN_BACKGROUNDS else key
    return f"✅ Background set to: {label} ({get_theme_bg_hex(p) or 'transparent'})"


def set_icon(choice: str) -> str:
    key = (choice or "").strip().lower()
    if key not in BUILTIN_ICONS or key == "custom":
        raise ValueError("Choose icon: " + ", ".join(k for k in BUILTIN_ICONS if k != "custom"))
    p = load_persona()
    p["icon"] = key
    save_persona(p)
    return f"✅ Icon set to: {get_icon()} ({key})"


def set_language(code: str) -> str:
    key = (code or "").strip().lower()
    if key not in SUPPORTED_LANGUAGES:
        raise ValueError("Choose language: " + ", ".join(SUPPORTED_LANGUAGES.keys()))
    p = load_persona()
    p["language"] = key
    save_persona(p)
    lang = SUPPORTED_LANGUAGES[key]
    return f"✅ Language set to: {lang['flag']} {lang['name']}"


def set_voice(choice: str) -> str:
    key = (choice or "").strip().lower()
    if key not in VOICE_PRESETS:
        raise ValueError("Choose voice: " + ", ".join(VOICE_PRESETS.keys()))
    p = load_persona()
    p["voice"] = key
    save_persona(p)
    return f"✅ Voice set to: {VOICE_PRESETS[key]['label']} ({key})"


def set_greeting_style(style: str) -> str:
    key = (style or "").strip().lower()
    if key not in ("casual", "professional", "hype"):
        raise ValueError("Choose greeting style: casual, professional, hype")
    p = load_persona()
    p["greeting_style"] = key
    save_persona(p)
    return f"✅ Greeting style set to: {key}\nPreview: {get_greeting()}"


def set_ai_mode(mode: str) -> str:
    key = (mode or "").strip().lower()
    if key not in ("hybrid", "kurt_only", "claude_only"):
        raise ValueError("Choose AI mode: hybrid, kurt_only, claude_only")
    p = load_persona()
    p["ai_mode"] = key
    save_persona(p)
    return f"✅ AI Mode set to: {key}"


def set_bool_option(field: str, value: str) -> str:
    if field not in ("compact_mode", "show_routing_info"):
        raise ValueError("Unsupported display toggle.")
    norm = (value or "").strip().lower()
    if norm in ("on", "true", "1", "yes"):
        enabled = True
    elif norm in ("off", "false", "0", "no"):
        enabled = False
    else:
        raise ValueError("Use on or off.")
    p = load_persona()
    p[field] = enabled
    save_persona(p)
    label = "Compact Mode" if field == "compact_mode" else "Show Routing Info"
    return f"✅ {label}: {'ON' if enabled else 'OFF'}"


def get_voice_preset() -> dict:
    """Return current TTS voice preset dict (for kurt.core.wake_word.speak())"""
    p = load_persona()
    return VOICE_PRESETS.get(p.get("voice", "young_boy"), VOICE_PRESETS["young_boy"])


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
    theme = get_theme()
    lang = SUPPORTED_LANGUAGES.get(p.get("language", "taglish"), SUPPORTED_LANGUAGES["taglish"])
    icon = get_icon()

    t = theme["primary"]

    table = Table(
        title=f"{icon} KURT Persona Config",
        box=box.ROUNDED,
        border_style=theme["border"],
        style=theme.get("background", ""),
        show_header=True,
        header_style=theme["primary"],
    )
    table.add_column("Setting", style=theme["secondary"], width=20)
    table.add_column("Value", style="white", width=30)
    table.add_column("Description", style=theme["dim"], width=35)

    table.add_row("User Name", p.get("user_name", "Boss"), "Kung paano kang tatawagin ni KURT")
    table.add_row("KURT Name", p.get("kurt_name", "KURT"), "Pangalan ni KURT")
    table.add_row("Theme", f"{p.get('theme','cyber')} — {theme['name']}", "Color palette")
    bg_key = p.get("custom_background", "theme")
    bg_hex = get_theme_bg_hex(p) or "transparent"
    table.add_row("Background", f"{bg_key} ({bg_hex})", "Theme / picker background color")
    table.add_row("Icon", f"{icon} ({p.get('icon','robot')})", "KURT icon")
    voice = VOICE_PRESETS.get(p.get("voice", "young_boy"), VOICE_PRESETS["young_boy"])
    table.add_row("Voice", f"{p.get('voice','young_boy')} — {voice['label']}", "TTS voice (Hey Kurt / F5)")
    table.add_row("Language", f"{lang['flag']} {lang['name']}", "Output language")
    table.add_row("Greeting Style", p.get("greeting_style", "casual"), "casual / professional / hype")
    table.add_row("Default Model", p.get("default_model", "auto"), "Saved model; quota-only failover")
    table.add_row("Default CLI", p.get("default_cli", "auto"), "auto uses the saved model")
    from kurt.core.execution_preferences import media_label
    table.add_row("Default Image", media_label("image", p), "Image generation model")
    table.add_row("Default Video", media_label("video", p), "Video generation model")
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
