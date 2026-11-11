"""
KURT Command Palette
Interactive `/` menu for `kurt chat` — a thin input front-end layered on
top of the existing handle_slash() dispatcher. It never reimplements
business logic: every resolved selection is just the same command string
a user could type by hand, fed straight back into the normal chat loop.

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
    "/agents": "agents",
    "/plugins": "plugins",
    "/model": "model",
    "/config": "config",
}

CONFIG_SUBCOMMANDS = [
    ("show", "Show current persona/theme settings"),
    ("theme", "Pick a color theme"),
    ("name", "Set Kurt's display name"),
    ("icon", "Set Kurt's icon/emoji"),
    ("language", "Set reply language (Tagalog/English/Taglish)"),
    ("aimode", "Set AI personality mode"),
    ("projects", "Manage per-project context"),
    ("setup", "Run the full setup wizard"),
    ("reset", "Reset persona to defaults"),
]

# No style override needed beyond stripping the default "reverse" the
# bottom-toolbar class ships with (prompt_toolkit's own defaults.py sets
# it to a solid reversed block) — that solid bar is what read as a "white
# background" in a light-background terminal. Leaving it blank lets the
# terminal's own (transparent) background show through.
_STYLE = Style.from_dict({"bottom-toolbar": "", "bottom-toolbar.text": ""})


@dataclass
class _PaletteState:
    is_open: bool = False
    tab: str = "commands"           # active root tab
    view: str = "root"              # root | show_all | skills | mcp | agents | plugins | model | config
    stack: list = field(default_factory=list)  # back-stack of (view, tab)
    index: int = 0


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
    return all(word in blob for word in query.split())


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
    return [t for t in tokens if _matches(query, t)]


# ── Data providers — every item here is just the pre-existing function
# a typed command already calls; nothing here is new business logic
# except the one `/mcp connect-preset` arm added to cli_orchestrator.py.
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
                "label": f"✓ {name}  [{conn.transport}]  {conn.description}",
                "kind": "leaf",
                "value": "",
            })
    for name, preset in PRESETS.items():
        if name in registry:
            continue
        if _matches(query, name, preset.description):
            items.append({
                "label": f"○ {name}  (preset — ready to connect)  {preset.description}",
                "kind": "leaf",
                "value": f"/mcp connect-preset {name}",
            })
    preset_ids = {f"{p}" for p in PRESETS} | set(registry.keys())
    for entry in _catalog_entries():
        short = entry["id"].split("/", 1)[-1]
        if short in preset_ids or entry["id"] in preset_ids:
            continue
        if _matches(query, entry["id"], entry.get("title", ""), entry.get("description", "")):
            items.append({
                "label": f"◇ {entry['id']}  (catalog — needs config)  {entry.get('description', '')[:60]}",
                "kind": "leaf",
                # Not a one-click connect: most catalog servers need an
                # API key/URL filled in first. `/mcp config <id>` already
                # prints the ready-to-fill connection template.
                "value": f"/mcp config {entry['id']}",
            })
    return items


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
        if not os.getenv("FAL_API_KEY"):
            _fal_cache = []
        else:
            from kurt.models.fal import fetch_models
            try:
                _fal_cache = fetch_models() or []
            except Exception:
                _fal_cache = []
    return _fal_cache


def _model_items(query: str) -> list[dict]:
    from kurt.core.orchestrator import ROUTING_TABLE

    names = ["auto"]
    for route in ROUTING_TABLE.values():
        for model, provider in ((route["model"], route["provider"]),
                                 (route["fallback_model"], route["fallback_provider"])):
            label = f"{model} [{provider}]"
            if label not in names:
                names.append(label)
    rows = [n.split(" [")[0] for n in names]
    out = []
    seen = set()
    for raw, label in zip(rows, names):
        if raw in seen or not _matches(query, label):
            continue
        seen.add(raw)
        out.append({"label": label, "kind": "leaf", "value": f"/model {raw}"})

    for m in _openrouter_models():
        mid = m.get("id", "")
        if not mid or mid in seen or not _matches(query, mid, m.get("name", "")):
            continue
        seen.add(mid)
        out.append({
            "label": f"{mid}  [openrouter]  {m.get('name', '')[:40]}",
            "kind": "leaf",
            "value": f"/model {mid}",
        })

    for m in _fal_models():
        mid = m.get("id", "")
        if not mid or mid in seen or not _matches(query, mid, m.get("title", ""), m.get("category", "")):
            continue
        seen.add(mid)
        out.append({
            "label": f"{mid}  [fal]  {m.get('title', m.get('category', ''))[:40]}",
            "kind": "leaf",
            # Explicit provider tag — fal.ai and OpenRouter ids share the
            # same "vendor/name" shape, so this is required, not optional.
            "value": f"/model {mid} fal",
        })

    return out


def _config_items(query: str) -> list[dict]:
    return [
        {"label": f"{sub:<10} {desc}", "kind": "leaf", "value": f"/config {sub}"}
        for sub, desc in CONFIG_SUBCOMMANDS
        if _matches(query, sub, desc)
    ]


def _current_items(state: _PaletteState, query: str) -> list[dict]:
    if state.view == "show_all":
        return [{"label": f"{t}  {SLASH_COMMANDS.get(t, '')}", "kind": "leaf", "value": t}
                for t in _flat_commands(query)]
    if state.view == "skills":
        return _skills_items(query)
    if state.view == "mcp":
        return _mcp_items(query)
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
        rows = [{"label": "/mcp       Connect to & call outside tools", "kind": "open", "target": "mcp"}]
        return [r for r in rows if _matches(query, r["label"])]
    return []


def _render(state: _PaletteState, buf_text: str):
    query = _effective_query(state, buf_text)
    items = _current_items(state, query)
    if items:
        state.index %= len(items)
    else:
        state.index = 0

    lines = []

    if state.view == "root":
        tab_bar = []
        for t in ROOT_TABS:
            label = f" {TAB_LABELS[t]} "
            tab_bar.append(("reverse" if t == state.tab else "", label))
            tab_bar.append(("", "  "))
        lines.append(tab_bar + [("", "\n")])
    elif state.view == "show_all":
        lines.append([("bold", "📖 All commands"), ("", "\n")])
    else:
        icon = {"skills": "🧠", "mcp": "🔌", "agents": "⚙️", "plugins": "⚙️",
                "model": "🤖", "config": "🛠️"}.get(state.view, "")
        lines.append([("bold", f"{icon} {state.view}"), ("", "\n")])

    if not items:
        lines.append([("dim", "  (no matches)"), ("", "\n")])
    else:
        start = max(0, min(state.index - WINDOW // 2, max(0, len(items) - WINDOW)))
        for i, item in enumerate(items[start:start + WINDOW], start=start):
            marker = "▶ " if i == state.index else "  "
            style = "reverse" if i == state.index else ""
            lines.append([(style, f"{marker}{item['label']}"), ("", "\n")])
        if len(items) > WINDOW:
            lines.append([("dim", f"  ... {len(items)} total, scroll with ↑↓"), ("", "\n")])

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
        state.view = "show_all"
        state.stack = []
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("tab", filter=palette_open, eager=True)
    def _home(event):
        state.view = "root"
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
        items = _current_items(state, _effective_query(state, buf_text))
        if not items:
            return
        item = items[state.index % len(items)]
        args = _pending_args(state, buf_text)
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
        event.app.exit(result=value)

    session = PromptSession(
        message=HTML("<ansicyan><b>You</b></ansicyan> <ansibrightblack>›</ansibrightblack> "),
        key_bindings=kb,
        bottom_toolbar=lambda: _render(state, session.default_buffer.text) if state.is_open else None,
        style=_STYLE,
    )
    return session, state


_session: Optional[PromptSession] = None
_state: Optional[_PaletteState] = None


def read_chat_input(console, prompt_label: str = "You") -> str:
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

    global _session, _state
    if _session is None:
        _session, _state = _build_session()
    with patch_stdout():
        return _session.prompt()
