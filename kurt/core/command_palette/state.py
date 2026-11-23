"""Palette state primitives: _PaletteState, live-filter/argument parsing,
and the small constants shared by both items.py and engine.py."""

from dataclasses import dataclass, field

from prompt_toolkit.styles import DynamicStyle, Style

from kurt.core.cli_orchestrator import SLASH_COMMANDS, SLASH_GROUPS

ROOT_TABS = ["commands", "agents", "mcp"]
TAB_LABELS = {"commands": "Commands", "agents": "Agents", "mcp": "MCP Connectors"}
WINDOW = 10  # max visible rows at once

# Categories whose root-level command row opens a nested browsing list.
OPEN_TARGETS = {
    "/skill": "skills",
    "/skills": "skills",
    "/mcp": "mcp",
    "/connect": "connectors",
    "/zapier": "zapier",
    "/n8n": "n8n",
    "/agents": "agents",
    "/plugins": "plugins",
    "/library": "library",
    "/model": "model",
    "/models": "model_catalog",
    "/image-model": "media_image",
    "/video-model": "media_video",
    "/config": "config",
    "/setting": "execution_defaults",
    "/cli": "cli_settings",
    "/speech": "speech",
    "/wallet": "wallet",
    "/doctor": "doctor",
    "/computer": "computer",
    "/browser": "browser",
    "/tasks": "tasks",
}

CONFIG_SUBCOMMANDS = [
    ("show", "Show current persona/theme settings"),
    ("theme", "Pick a color theme (with background preview)"),
    ("background", "Pick a background color for themes & pickers"),
    ("icon", "Pick Kurt's icon/emoji"),
    ("language", "Pick reply language (Tagalog/English/Taglish)"),
    ("voice", "Pick Kurt's spoken TTS voice"),
    ("greeting", "Pick greeting style (casual/professional/hype)"),
    ("aimode", "Pick AI mode (hybrid/kurt_only/claude_only)"),
    ("display", "Toggle compact mode & routing info"),
    ("model", "Chat AI — choose default conversational model"),
    ("cli", "CLI — choose default command-line AI"),
    ("image", "Choose a default image generator"),
    ("video", "Choose a default video generator"),
    ("name", "Set Kurt's display name (text input)"),
    ("projects", "Manage per-project context (text input)"),
    ("setup", "Run the full personalization wizard"),
    ("reset", "Reset persona to defaults"),
]

# prompt_toolkit's own defaults.py ships class:bottom-toolbar as "reverse"
# (a solid swapped-color block — that's the "white background" users see).
# An empty string here does NOT cancel it: style merging only overrides
# attributes a later rule explicitly sets, and "" sets nothing, so the
# inherited reverse=True from the built-in default style survives untouched.
# "noreverse" is the explicit attribute that actually clears it.
def _active_bg_hex() -> str:
    try:
        from kurt.core.persona import PERSONA_PATH, get_theme_bg_hex
        if not PERSONA_PATH.exists():
            return ""
        return get_theme_bg_hex() or ""
    except OSError:
        return ""


def _build_toolbar_style() -> Style:
    bg = _active_bg_hex()
    rule = f"noreverse bg:{bg}" if bg else "noreverse"
    return Style.from_dict({"bottom-toolbar": rule, "bottom-toolbar.text": rule})


_STYLE = DynamicStyle(_build_toolbar_style)


@dataclass
class _PaletteState:
    is_open: bool = False
    tab: str = "commands"           # active root tab
    view: str = "root"              # root | show_all | skills | mcp | agents | plugins | model | config
    stack: list = field(default_factory=list)  # back-stack of (view, tab)
    index: int = 0
    notice: str = ""
    settings_only: bool = False


# ── Live filter / argument parsing ───────────────────────────────────

def _after_slash(buf_text: str) -> str:
    return buf_text[1:] if buf_text.startswith("/") else buf_text


def _effective_query(state: "_PaletteState", buf_text: str) -> str:
    """The live filter text. In the root/show-all views only the first
    word is a filter — anything typed after a space is a command
    argument to preserve verbatim, not more filter text (so typing
    `/model openai/gpt-oss-120b` doesn't lose its argument just because
    the argument text doesn't appear in /model's description). Nested
    views have no argument concept, so the whole typed text is the
    (possibly multi-word) search query."""
    if state.view.startswith(('provider_key_input:', 'model_json_input:')):
        return ''  # Secret keys and JSON configs are never catalog/search queries.
    rest = _after_slash(buf_text)
    if state.view in ("root", "show_all"):
        return rest.split(None, 1)[0].casefold() if rest.split() else ""
    return rest.casefold()


def _pending_args(state: "_PaletteState", buf_text: str) -> str:
    """Text typed after the first word, only meaningful in root/show-all."""
    if state.view not in ("root", "show_all"):
        return ""
    parts = _after_slash(buf_text).split(None, 1)
    return parts[1] if len(parts) > 1 else ""


def _matches(query: str, *haystacks: str) -> bool:
    if not query:
        return True
    blob = " ".join(haystacks).casefold()
    return all(word in blob for word in query.casefold().split())


def _flat_commands(query: str) -> list[str]:
    tokens = []
    for _, names in SLASH_GROUPS:
        for name in names:
            if name not in tokens:
                tokens.append(name)
    for name in SLASH_COMMANDS:
        if name not in tokens:
            tokens.append(name)
    # Match on the command name only (not its description) — this is a
    # single-word command-name fragment, so matching description text too
    # causes false hits (e.g. "skill" matching "/info"'s "...active skill").
    matches = [t for t in tokens if _matches(query, t)]
    # Exact commands win over substrings such as /cli inside /deepseek-cli.
    exact = query.strip().lstrip('/').casefold()
    return sorted(matches, key=lambda t: t.lstrip('/').casefold() != exact)
