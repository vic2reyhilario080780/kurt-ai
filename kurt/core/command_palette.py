"""
KURT Command Palette
Interactive `/` menu for `kurt chat` — a thin input front-end layered on
top of the existing handle_slash() dispatcher. It never reimplements
business logic: every resolved selection is just the same command string
a user could type by hand, fed straight back into the normal chat loop.
Setup-page actions open the browser while keeping the picker available.

Layout: typing "/" as the first character opens a live menu rendered as
the PromptSession's bottom_toolbar. ←/→ switch root tabs (Commands /
Agents / MCP Connectors), ↑/↓ move the selection, "?" shows every slash
command flattened, Enter on a leaf resolves+submits immediately, Enter on
a category (skills/mcp/agents/plugins/model/config) opens a nested,
type-ahead-filterable list of EVERY known item in that category, Esc goes
back one level (or cancels at root), Tab jumps straight back to the root
Commands tab, Ctrl-C cancels like a normal prompt.
"""

from dataclasses import dataclass, field
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from kurt.core.cli_orchestrator import SLASH_COMMANDS, SLASH_GROUPS

ROOT_TABS = ["commands", "agents", "mcp"]
TAB_LABELS = {"commands": "Commands", "agents": "Agents", "mcp": "MCP Connectors"}
WINDOW = 10  # max visible rows at once

# Categories whose root-level command row opens a nested browsing list.
OPEN_TARGETS = {
    "/skills": "skills",
    "/mcp": "mcp",
    "/connect": "connectors",
    "/zapier": "zapier",
    "/n8n": "n8n",
    "/agents": "agents",
    "/plugins": "plugins",
    "/model": "model",
    "/image-model": "media_image",
    "/video-model": "media_video",
    "/config": "config",
    "/setting": "execution_defaults",
    "/cli": "cli_settings",
}

CONFIG_SUBCOMMANDS = [
    ("show", "Show current persona/theme settings"),
    ("theme", "Pick a color theme"),
    ("name", "Set Kurt's display name"),
    ("icon", "Set Kurt's icon/emoji"),
    ("language", "Set reply language (Tagalog/English/Taglish)"),
    ("model", "Chat AI — choose default conversational model"),
    ("cli", "CLI — choose default command-line AI"),
    ("image", "Choose a default image generator"),
    ("video", "Choose a default video generator"),
    ("aimode", "Set AI personality mode"),
    ("projects", "Manage per-project context"),
    ("setup", "Run the full setup wizard"),
    ("reset", "Reset persona to defaults"),
]

# prompt_toolkit's own defaults.py ships class:bottom-toolbar as "reverse"
# (a solid swapped-color block — that's the "white background" users see).
# An empty string here does NOT cancel it: style merging only overrides
# attributes a later rule explicitly sets, and "" sets nothing, so the
# inherited reverse=True from the built-in default style survives untouched.
# "noreverse" is the explicit attribute that actually clears it.
_STYLE = Style.from_dict({"bottom-toolbar": "noreverse", "bottom-toolbar.text": "noreverse"})


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


# ── Data providers — every item here is just the pre-existing function
# a typed command already calls; nothing here is new business logic
# except the `/mcp authorize` arm added to cli_orchestrator.py.
# ──────────────────────────────────────────────────────────────────────

def _skills_items(query: str) -> list[dict]:
    from kurt.skills.manager import get_all_skills

    skills = get_all_skills(include_native=True)
    if query:
        skills = [s for s in skills if _matches(query, s.get("id", ""), s.get("description", ""))]
    return [
        {
            "label": f"{s['id']}  —  {s.get('description', '')[:60]}",
            "kind": "leaf",
            "value": f"/skill {s['id']}",
        }
        for s in skills
    ]


_catalog_cache: Optional[list] = None


def _catalog_entries() -> list:
    """Full public MCP registry, loaded once and cached — reloading the
    gzip catalog from disk costs ~0.5s, far too slow to repeat per
    keystroke while browsing 58k+ entries."""
    global _catalog_cache
    if _catalog_cache is None:
        from kurt.core.mcp_catalog import load_catalog
        _catalog_cache = load_catalog()["entries"]
    return _catalog_cache


def _mcp_items(query: str) -> list[dict]:
    from kurt.core.mcp_client import PRESETS, load_registry

    registry = load_registry()
    items = []
    for name, conn in registry.items():
        if _matches(query, name, conn.description):
            items.append({
                "label": f"◇ {name}  [saved; {'enabled' if conn.enabled else 'disabled'}]  {conn.description}",
                "kind": "open", "target": f"connector:mcp:{name}",
            })
    for name, preset in PRESETS.items():
        if name in registry:
            continue
        if _matches(query, name, preset.description):
            items.append({
                "label": f"○ {name}  (preset — setup)  {preset.description}",
                "kind": "open", "target": f"connector:mcp:{name}",
            })
    preset_ids = {f"{p}" for p in PRESETS} | set(registry.keys())
    for entry in _catalog_entries():
        if entry["id"] in preset_ids:
            continue
        if _matches(query, entry["id"], entry.get("title", ""), entry.get("description", "")):
            items.append({
                "label": f"◇ {entry['id']}  (catalog — setup)  {entry.get('description', '')[:60]}",
                "kind": "open", "target": f"connector:mcp:{entry['id']}",
            })
    # All provider setup remains reachable from the MCP list itself.
    providers = [
        ("Composio — app login / API setup", "connectors"),
        ("Zapier — app accounts / MCP setup", "zapier"),
        ("n8n — app credentials / MCP setup", "n8n"),
    ]
    return [{"label": label, "kind": "open", "target": target}
            for label, target in providers if _matches(query, label)] + items


_composio_curated_cache: Optional[dict] = None


def _composio_curated() -> dict:
    """slug -> (name, description, category) for the ~40 hand-written
    entries in COMPOSIO_APPS — used only to give those few a nicer label
    than a bare title-cased slug; everything else in the full 1,633-entry
    bundled directory still works, just without hand-written copy."""
    global _composio_curated_cache
    if _composio_curated_cache is None:
        from kurt.hub.composio import COMPOSIO_APPS
        _composio_curated_cache = {
            slug: (name, desc, cat)
            for cat, apps in COMPOSIO_APPS.items()
            for slug, name, desc in apps
        }
    return _composio_curated_cache


def _connector_items(query: str) -> list[dict]:
    """Full toolkit directory; each app opens its setup/action submenu."""
    from kurt.hub.composio import load_toolkits

    curated = _composio_curated()
    items = []
    for slug in load_toolkits():
        name, desc, cat = curated.get(slug, (slug.replace("_", " ").replace("-", " ").title(), "", ""))
        if _matches(query, slug, name, desc):
            label = f"{name}  —  {desc}  [{cat}]" if desc else name
            items.append({"label": label, "kind": "open", "target": f"connector:composio:{slug}"})
    return items


def _zapier_picker_items(query: str) -> list[dict]:
    """Full Zapier directory with app pages and platform MCP setup."""
    from kurt.hub.mcp_servers import load_zapier_apps

    items = []
    for slug in load_zapier_apps():
        label = slug.replace("-", " ").title()
        if _matches(query, slug, label):
            items.append({"label": label, "kind": "open", "target": f"connector:zapier:{slug}"})
    return items


def _n8n_picker_items(query: str) -> list[dict]:
    """Full n8n directory with credential pages and platform MCP setup."""
    from kurt.hub.mcp_servers import load_n8n_integrations

    items = []
    for slug in load_n8n_integrations():
        label = slug.replace("-", " ").title()
        if _matches(query, slug, label):
            items.append({"label": label, "kind": "open", "target": f"connector:n8n:{slug}"})
    return items


def _connector_detail_items(provider: str, ref: str, query: str) -> list[dict]:
    from kurt.core.connector_pages import connector_pages
    from kurt.core.mcp_client import PRESETS, load_registry

    items = []
    entry = None
    if provider == "mcp":
        saved = load_registry().get(ref)
        entry = next((e for e in _catalog_entries() if e["id"] == ref), None)
        if saved:
            items.append({"label": "Test saved connection / list available tools", "kind": "leaf", "value": f"/mcp tools {ref}"})
        if ref in PRESETS or (entry and entry.get("configs")):
            items.append({"label": "Connect / authorize — guided setup", "kind": "leaf", "value": f"/mcp authorize {ref}"})
            if entry and len(entry.get("configs", [])) > 1:
                for index, recipe in enumerate(entry["configs"]):
                    label = recipe.get("type", "stdio")
                    if recipe.get("command"):
                        label += " / " + recipe["command"]
                    items.append({"label": f"Connect option {index + 1}: {label}", "kind": "leaf",
                                  "value": f"/mcp authorize {ref} --variant {index}"})
        elif not saved:
            items.append({"label": "No connection recipe published — open setup instructions below", "kind": "info"})
    elif provider == "composio":
        items.append({"label": "Connect app — browser login / guided credentials", "kind": "leaf", "value": f"/connect {ref}"})
        items.append({"label": "Check account authorization status", "kind": "leaf", "value": "/connect status"})
    else:
        items.append({"label": "Connect platform MCP to Kurt — paste your server URL", "kind": "leaf", "value": f"/mcp platform {provider}"})
        items.append({"label": "App accounts are configured on the platform; only exposed tools reach Kurt", "kind": "info"})
    pages = connector_pages(provider, ref, entry)
    items.extend({"label": f"Open {label} — {url}", "kind": "browser", "url": url}
                 for label, url in pages.items())
    if not pages:
        items.append({"label": "No website or repository published by this connector", "kind": "info"})
    return [item for item in items if _matches(query, item["label"])]


def _capability_items(query: str, kind: str, cmd: str) -> list[dict]:
    from kurt.capabilities.runtime import search

    # include_disabled=True only when browsing everything (empty query) —
    # the per-item availability check thrashes a small LRU cache across
    # ~100 domains when scanning all 10,000 entries, which is slow; a
    # real (small) search result set stays fast and keeps the same
    # "hide disabled" behavior the typed /agents and /plugins commands have.
    rows = search(query, kind=kind, include_disabled=not query, limit=10_000)
    return [
        {"label": f"{r['id']}  —  {r['name']}", "kind": "leaf", "value": f"{cmd} {r['id']}"}
        for r in rows
    ]


_openrouter_cache: Optional[list] = None
_fal_cache: Optional[list] = None


def _openrouter_models() -> list:
    """All 400+ OpenRouter text models — cached in-memory for the session
    (fetch_models() itself disk-caches for an hour; this just avoids
    re-reading that file on every keystroke while browsing)."""
    global _openrouter_cache
    if _openrouter_cache is None:
        from kurt.models.openrouter import fetch_models
        try:
            _openrouter_cache = fetch_models() or []
        except Exception:
            _openrouter_cache = []
    return _openrouter_cache


def _fal_models() -> list:
    """All 1,400+ fal.ai generation models — only fetched if FAL_API_KEY is
    configured (fetch_models() itself prints a setup hint and needs a real
    key; skip calling it at all here rather than let that print corrupt the
    live palette render)."""
    global _fal_cache
    if _fal_cache is None:
        import os
        if not (os.getenv("FAL_API_KEY") or os.getenv("FAL_KEY")):
            _fal_cache = []
        else:
            from kurt.models.fal import fetch_models
            try:
                _fal_cache = fetch_models() or []
            except Exception:
                _fal_cache = []
    return _fal_cache


def _is_chat_model(model):
    architecture = model.get("architecture") or {}
    if not isinstance(architecture, dict):
        return False
    outputs = architecture.get("output_modalities")
    if outputs is None:
        modality = architecture.get("modality", "")
        outputs = modality.rsplit("->", 1)[-1].split("+") if "->" in modality else []
    # Vision/input modalities are fine. Generation outputs belong in media pickers.
    return isinstance(outputs, list) and bool(outputs) and set(outputs) == {"text"}


def _pricing_hint(model):
    pricing = model.get("pricing") or {}
    if not isinstance(pricing, dict):
        return "pricing unavailable"
    import math
    try:
        values = [float(pricing[k]) for k in ("prompt", "completion", "request") if pricing.get(k) is not None]
    except (ValueError, TypeError):
        values = []
    if not values or not all(math.isfinite(v) and v >= 0 for v in values) or pricing.get("prompt") is None or pricing.get("completion") is None:
        return "pricing unavailable"
    return "Paid" if any(v > 0 for v in values) else "Free"


def _chat_choices():
    from kurt.core.execution_preferences import TEXT_PROVIDERS
    from kurt.core.orchestrator import ROUTING_TABLE, TaskType
    seen = set()
    rows = []
    for task, route in ROUTING_TABLE.items():
        if task in (TaskType.IMAGE, TaskType.VIDEO, TaskType.MUSIC, TaskType.TRANSCRIBE):
            continue
        for model, provider in ((route["model"], route["provider"]), (route["fallback_model"], route["fallback_provider"])):
            if provider in TEXT_PROVIDERS and (model, provider) not in seen:
                seen.add((model, provider))
                rows.append((model, provider, f"{model} [{provider}]"))
    for model, provider in (("mistral-small-latest", "mistral"), ("deepseek-flash", "deepseek"), ("deepseek-v4-pro", "deepseek")):
        if (model, provider) not in seen:
            seen.add((model, provider))
            rows.append((model, provider, f"{model} [{provider}]"))
    for model in _openrouter_models():
        mid = model.get("id", "")
        if not mid or not _is_chat_model(model) or (mid, "openrouter") in seen:
            continue
        seen.add((mid, "openrouter"))
        rows.append((mid, "openrouter", f"{mid} [openrouter] — {_pricing_hint(model)} — {model.get('name', '')[:40]}"))
    return rows


def _model_items(query: str) -> list[dict]:
    rows = [{"label": "Auto — route chat requests", "kind": "leaf", "value": "/model auto"}]
    rows.extend({"label": label, "kind": "leaf", "value": f"/model {model}" + (f" {provider}" if provider != "openrouter" else "")}
                for model, provider, label in _chat_choices())
    return [row for row in rows if _matches(query, row["label"])]


def _default_model_items(query):
    rows = [{"label": "Choose chat provider + exact model ID", "kind": "leaf", "value": "/model choose-default"},
            {"label": "Auto — let Kurt route chat requests", "kind": "leaf", "value": "/model default auto"}]
    rows.extend({"label": label + " — save Chat AI default", "kind": "leaf", "value": f"/model default {model} {provider}"}
                for model, provider, label in _chat_choices())
    return [row for row in rows if _matches(query, row["label"])]


def _execution_default_items(query):
    rows = [
        {"label": "Chat AI — conversational models only", "kind": "open", "target": "default_models"},
        {"label": "CLI — installed/supported AI command-line tools", "kind": "open", "target": "cli_settings"},
        {"label": "Image AI — text-to-image generators", "kind": "open", "target": "media_image"},
        {"label": "Video AI — text-to-video generators", "kind": "open", "target": "media_video"},
    ]
    return [row for row in rows if _matches(query, row["label"])]


def _cli_default_items(query):
    from kurt.core.execution_preferences import DEFAULT_CLIS, cli_platform_limit
    from kurt.core.cli_orchestrator import _cmd_exists
    rows = []
    for name in DEFAULT_CLIS:
        installed = name == 'auto' or _cmd_exists(name)
        status = "use selected API model" if name == "auto" else ("installed; auth/credits not verified" if installed else "not installed — install before selecting")
        if name in {"codex", "vibe", "deepseek", "deepseek-cli", "copilot"}:
            status += "; read-only by default"
        if name == "vibe":
            status += "; Mistral Vibe"
        if name == 'deepseek': status += '; DeepSeek Agent (Python)'
        if name == 'deepseek-cli': status += '; DeepSeek Terminal CLI (Node)'
        if name == 'copilot': status += '; GitHub Copilot — login or wallet provider required'
        action = 'save default' if installed else 'unavailable'
        limitation = cli_platform_limit(name)
        if limitation: status=limitation; action='unavailable on this OS'
        rows.append({"label": f"{name} — {status} — {action}", "kind": "leaf" if installed and not limitation else "info", "value": f"/cli default {name}"})
    return [row for row in rows if _matches(query, row["label"])]


def _media_model_items(kind, query):
    from kurt.core.execution_preferences import media_label, MEDIA_PRESETS
    command = f"/{kind}-model"
    rows = [
        {"label": f"Current: {media_label(kind)}", "kind": "info"},
        {"label": "Auto — use Kurt's generation default", "kind": "leaf", "value": f"{command} auto"},
        {"label": "Choose provider + exact model ID (fal / Replicate)", "kind": "leaf", "value": f"{command} choose"},
    ]
    presets = MEDIA_PRESETS[kind]
    seen = set()
    for label, mid in presets:
        seen.add(mid)
        rows.append({"label": f"{label} [{mid}] [fal] — {'image-to-video' if mid.endswith('/image-to-video') else 'text-to-' + kind}", "kind": "leaf", "value": f"{command} {mid} fal"})
    for model in _fal_models():
        if model.get("category") != f"text-to-{kind}" or not model.get("id") or model["id"] in seen:
            continue
        mid = model["id"]
        seen.add(mid)
        rows.append({"label": f"{model.get('title') or mid} [{mid}] [fal]", "kind": "leaf", "value": f"{command} {mid} fal"})
    return [row for row in rows if _matches(query, row["label"])]


def _config_items(query: str) -> list[dict]:
    return [
        {"label": f"{sub:<10} {desc}", "kind": "open", "target": {"model": "default_models", "cli": "cli_settings", "image": "media_image", "video": "media_video"}[sub]}
        if sub in ("model", "cli", "image", "video") else
        {"label": f"{sub:<10} {desc}", "kind": "leaf", "value": f"/config {sub}"}
        for sub, desc in CONFIG_SUBCOMMANDS
        if _matches(query, sub, desc)
    ]


def _current_items(state: _PaletteState, query: str) -> list[dict]:
    if state.view == "execution_defaults":
        return _execution_default_items(query)
    if state.view in ("media_image", "media_video"):
        return _media_model_items(state.view.split("_", 1)[1], query)
    if state.view == "default_models":
        return _default_model_items(query)
    if state.view == "cli_settings":
        return _cli_default_items(query)
    if state.view.startswith("connector:"):
        _, provider, ref = state.view.split(":", 2)
        return _connector_detail_items(provider, ref, query)
    if state.view == "show_all":
        return [{"label": f"{t}  {SLASH_COMMANDS.get(t, '')}", "kind": "leaf", "value": t}
                for t in _flat_commands(query)]
    if state.view == "skills":
        return _skills_items(query)
    if state.view == "mcp":
        return _mcp_items(query)
    if state.view == "connectors":
        return _connector_items(query)
    if state.view == "zapier":
        return _zapier_picker_items(query)
    if state.view == "n8n":
        return _n8n_picker_items(query)
    if state.view == "agents":
        return _capability_items(query, "agent", "/agents")
    if state.view == "plugins":
        return _capability_items(query, "plugin", "/plugins")
    if state.view == "model":
        return _model_items(query)
    if state.view == "config":
        return _config_items(query)

    # state.view == "root"
    if state.tab == "commands":
        return [
            {"label": f"{t}  {SLASH_COMMANDS.get(t, '')}", "kind": "open", "target": OPEN_TARGETS[t]}
            if t in OPEN_TARGETS else
            {"label": f"{t}  {SLASH_COMMANDS.get(t, '')}", "kind": "leaf", "value": t}
            for t in _flat_commands(query)
        ]
    if state.tab == "agents":
        rows = [
            {"label": "/agents    Discover native workflow agents", "kind": "open", "target": "agents"},
            {"label": "/plugins   Discover executable native plugins", "kind": "open", "target": "plugins"},
        ]
        return [r for r in rows if _matches(query, r["label"])]
    if state.tab == "mcp":
        rows = [
            {"label": "/connect   Connect an app — 1,633 Composio toolkits", "kind": "open", "target": "connectors"},
            {"label": "/mcp       Connect to & call outside tools — 58K+ public MCP servers", "kind": "open", "target": "mcp"},
            {"label": "/zapier    Browse 9,000+ Zapier app integrations", "kind": "open", "target": "zapier"},
            {"label": "/n8n       Browse 2,000+ n8n workflow integrations", "kind": "open", "target": "n8n"},
        ]
        return [r for r in rows if _matches(query, r["label"])]
    return []


def _personalized_highlight_style() -> str:
    """Plain text (no color, no background block) until the user has
    actually personalized Kurt via `kurt setting` — persona.json existing on
    disk is that signal. Once personalized, the active tab / selected row
    use the user's own theme color instead of a hardcoded reversed block,
    so the highlight is never a flat white/inverted bar in a stock terminal."""
    from kurt.core.persona import PERSONA_PATH, get_theme

    if not PERSONA_PATH.exists():
        return ""
    color = get_theme().get("primary", "bold cyan").split()[-1]
    color = {"orange1": "orange"}.get(color, color)
    return f"bold fg:{color}"


def _render(state: _PaletteState, buf_text: str):
    query = _effective_query(state, buf_text)
    items = _current_items(state, query)
    if items:
        state.index %= len(items)
    else:
        state.index = 0

    highlight = _personalized_highlight_style()
    lines = []

    if state.view == "root":
        tab_bar = []
        for t in ROOT_TABS:
            label = f" {TAB_LABELS[t]} "
            tab_bar.append((highlight if t == state.tab else "", label))
            tab_bar.append(("", "  "))
        lines.append(tab_bar + [("", "\n")])
    elif state.view == "show_all":
        lines.append([("bold", "📖 All commands"), ("", "\n")])
    else:
        icon = {"skills": "🧠", "mcp": "🔌", "connectors": "🔗", "zapier": "⚡", "n8n": "⚙️",
                "agents": "⚙️", "plugins": "⚙️", "model": "🤖", "config": "🛠️"}.get(state.view, "")
        title = {"execution_defaults": "Choose a default", "default_models": "Chat AI — save default", "model": "Chat AI — this session", "cli_settings": "CLI — save default", "media_image": "Image AI — save default", "media_video": "Video AI — save default"}.get(state.view, state.view)
        lines.append([("bold", f"{icon} {title}"), ("", "\n")])

    if not items:
        lines.append([("dim", "  (no matches)"), ("", "\n")])
    else:
        start = max(0, min(state.index - WINDOW // 2, max(0, len(items) - WINDOW)))
        for i, item in enumerate(items[start:start + WINDOW], start=start):
            marker = "▶ " if i == state.index else "  "
            style = highlight if i == state.index else ""
            lines.append([(style, f"{marker}{item['label']}"), ("", "\n")])
        if len(items) > WINDOW:
            lines.append([("dim", f"  ... {len(items)} total, scroll with ↑↓"), ("", "\n")])

    if state.notice:
        lines.append([("", state.notice), ("", "\n")])

    lines.append([("dim", "↑↓ select  ←→ tabs  ? all  Tab⇥ home  Enter open/run  Esc back  Ctrl-C cancel")])

    result = []
    for chunk in lines:
        result.extend(chunk)
    return result


def _build_session() -> tuple[PromptSession, _PaletteState]:
    state = _PaletteState()
    kb = KeyBindings()

    palette_open = Condition(lambda: state.is_open)
    at_root = Condition(lambda: state.is_open and state.view == "root")

    def _reset_query(buf):
        buf.text = "/"
        buf.cursor_position = 1

    @kb.add("/", filter=Condition(lambda: not state.is_open and get_app().current_buffer.text == ""))
    def _open(event):
        event.current_buffer.insert_text("/")
        state.is_open = True
        state.tab = "commands"
        state.view = "root"
        state.stack = []
        state.index = 0

    @kb.add("left", filter=at_root, eager=True)
    def _tab_left(event):
        idx = ROOT_TABS.index(state.tab)
        state.tab = ROOT_TABS[(idx - 1) % len(ROOT_TABS)]
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("right", filter=at_root, eager=True)
    def _tab_right(event):
        idx = ROOT_TABS.index(state.tab)
        state.tab = ROOT_TABS[(idx + 1) % len(ROOT_TABS)]
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("up", filter=palette_open, eager=True)
    def _up(event):
        items = _current_items(state, _effective_query(state, event.current_buffer.text))
        if items:
            state.index = (state.index - 1) % len(items)

    @kb.add("down", filter=palette_open, eager=True)
    def _down(event):
        items = _current_items(state, _effective_query(state, event.current_buffer.text))
        if items:
            state.index = (state.index + 1) % len(items)

    @kb.add("?", filter=palette_open, eager=True)
    def _show_all(event):
        state.view = "execution_defaults" if state.settings_only else "show_all"
        state.stack = []
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("tab", filter=palette_open, eager=True)
    def _home(event):
        state.view = "execution_defaults" if state.settings_only else "root"
        state.tab = "commands"
        state.stack = []
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("escape", filter=palette_open, eager=True)
    def _back(event):
        if state.stack:
            state.view, state.tab = state.stack.pop()
            state.index = 0
            _reset_query(event.current_buffer)
        else:
            if state.settings_only:
                event.app.exit(result="")
                return
            state.is_open = False
            event.current_buffer.text = ""
            event.current_buffer.cursor_position = 0

    @kb.add("c-c", filter=palette_open, eager=True)
    def _cancel(event):
        state.is_open = False
        event.app.exit(exception=KeyboardInterrupt())

    @kb.add("enter", filter=palette_open, eager=True)
    def _select(event):
        buf_text = event.current_buffer.text
        from kurt.core.attachments import is_local_path_input
        if not state.settings_only and is_local_path_input(buf_text):
            state.is_open = False
            event.app.exit(result=buf_text)
            return
        if not state.settings_only and buf_text.strip().casefold() in {'exit', 'quit', 'bye', '/exit', '/quit'}:
            state.is_open = False
            event.app.exit(result=buf_text.strip())
            return
        items = _current_items(state, _effective_query(state, buf_text))
        if not items:
            return
        item = items[state.index % len(items)]
        args = _pending_args(state, buf_text)
        if item["kind"] == "info":
            return
        if item["kind"] == "browser":
            from kurt.core.connector_pages import open_page
            state.notice = open_page(item["url"])
            return
        state.notice = ""
        if item["kind"] == "open":
            if args:
                # User already typed a full "/command <args>" by hand —
                # respect that instead of drilling into the nested
                # browser and discarding what they typed.
                state.is_open = False
                event.app.exit(result=buf_text)
                return
            state.stack.append((state.view, state.tab))
            state.view = item["target"]
            state.index = 0
            _reset_query(event.current_buffer)
            return
        state.is_open = False
        value = item["value"]
        if value and args:
            value = f"{value} {args}"
        event.current_buffer.text = value
        event.app.exit(result=value)

    session = PromptSession(
        message=HTML("<ansicyan><b>You</b></ansicyan> <ansibrightblack>›</ansibrightblack> "),
        key_bindings=kb,
        bottom_toolbar=lambda: _render(state, session.default_buffer.text) if state.is_open else (
            [("dim", f"🎤 {_active_voice_input.status} · F5 toggle")]
            if _active_voice_input is not None else None),
        style=_STYLE,
    )
    def sync_palette(buffer):
        # A deleted/replaced slash must not leave Enter trapped in an empty
        # picker. Standalone settings deliberately accept plain search text.
        from kurt.core.attachments import is_local_path_input
        if state.is_open and not state.settings_only and (not buffer.text.startswith('/') or is_local_path_input(buffer.text)):
            state.is_open = False
            state.stack = []
            state.index = 0
    session.default_buffer.on_text_changed += sync_palette
    return session, state


_session: Optional[PromptSession] = None
_state: Optional[_PaletteState] = None
_active_voice_input = None


def read_chat_input(console, prompt_label: str = "You", *, voice_input=None):
    """Drop-in replacement for console.input(...): returns the resolved
    command/text string exactly as if typed and submitted. Raises
    KeyboardInterrupt/EOFError the same way the call it replaces did.

    Falls back to the plain Rich prompt when stdin isn't a real
    interactive terminal (piped input, CliRunner-style tests, CI) —
    prompt_toolkit's raw key capture needs a real tty and would
    otherwise just raise EOFError immediately."""
    import sys

    if not sys.stdin.isatty():
        return console.input(f"[bold cyan]{prompt_label}[/bold cyan] [dim]›[/dim] ")

    global _session, _state, _active_voice_input
    if voice_input is not None:
        pending = voice_input.pop()
        if pending is not None:
            return pending
    if _session is None:
        _session, _state = _build_session()
    from prompt_toolkit.application import create_app_session
    # Match stdout to this prompt's output (including redirected/test consoles)
    # instead of asking Windows for an unrelated console screen buffer.
    with create_app_session(output=_session.app.output), patch_stdout():
        if voice_input is None:
            return _session.prompt()
        import asyncio
        from kurt.core.voice_input import VOICE_READY
        _active_voice_input = voice_input
        def bind():
            voice_input.bind(_session.app, asyncio.get_running_loop())
        try:
            value = _session.prompt(default=voice_input.take_draft(), pre_run=bind)
            return voice_input.pop() if value is VOICE_READY else value
        finally:
            voice_input.unbind()
            _active_voice_input = None


def pick_execution_default(kind=None):
    """Open the four-category picker outside chat; run only a settings action."""
    import sys
    from kurt.core.persona import load_persona
    from kurt.core.cli_orchestrator import handle_slash
    from kurt.utils.env_loader import load_env
    load_env()
    if not sys.stdin.isatty():
        return False
    views = {None: "execution_defaults", "model": "default_models", "cli": "cli_settings",
             "image": "media_image", "video": "media_video"}
    if kind not in views:
        raise ValueError("Choose model, cli, image or video.")
    session, state = _build_session()
    state.is_open = True
    state.view = views[kind]
    state.settings_only = True
    try:
        with patch_stdout():
            command = session.prompt(default="/")
    except (KeyboardInterrupt, EOFError):
        return False
    allowed = ("/model default ", "/model choose-default", "/cli default ", "/image-model ", "/video-model ")
    if not command.startswith(allowed):
        return False
    settings = load_persona()
    result = handle_slash(command, "settings", settings.get("default_model", "auto"), None)
    from rich.console import Console
    Console().print(result.output, markup=False)
    return True
