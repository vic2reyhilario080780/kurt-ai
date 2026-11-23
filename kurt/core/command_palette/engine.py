"""Rendering engine: palette visual styles, pagination/selection helpers,
and the interactive PromptSession loop (_build_session/_render) that
drives `kurt chat`'s `/` picker."""

from typing import Optional
from urllib.parse import quote, unquote

from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

from .state import _PaletteState, _effective_query, _pending_args, ROOT_TABS, TAB_LABELS, WINDOW, _STYLE
from .items import _current_items, refresh_model_catalogs, _selection_provider


def _personalized_highlight_style() -> str:
    """Selected clickable item highlight style (bright lavender-violet)."""
    return _STYLE_ITEM_SELECTED


# Palette visual styles (explicit noreverse + clean contrast on dark/stock terminals)
_STYLE_HEADER = "bold fg:#c084fc"          # rich violet title
_STYLE_RULE = "fg:#5b21b6"                 # subtle deep-violet divider
_STYLE_TAB_ACTIVE = "bold fg:#e9d5ff underline"
_STYLE_TAB_INACTIVE = "fg:#94a3b8"
_STYLE_MARKER = "bold fg:#f0abfc"          # bright orchid ▶ indicator
_STYLE_ITEM = "fg:#a78bfa"                 # violet item names
_STYLE_ITEM_SELECTED = "bold fg:#e9d5ff"   # bright lavender-violet selected item
_STYLE_DESC = "fg:#7dd3fc"                 # soft sky-cyan descriptions
_STYLE_DESC_SELECTED = "fg:#67e8f9"        # crisp cyan selected description
_STYLE_BADGE_OK = "fg:#6ee7b7"             # soft emerald for runnable defaults / Ollama GGUF
_STYLE_BADGE_DIM = "fg:#94a3b8"            # muted slate for browse-only
_STYLE_INFO = "fg:#64748b italic"          # non-clickable info notes (prefixed with ℹ)
_STYLE_PAGE = "fg:#a5b4fc"                 # indigo page indicator
_STYLE_NOTICE = "fg:#fde047"               # warm yellow feedback notice
_STYLE_HINT = "fg:#64748b"                 # dim shortcut hint bar


def _first_selectable(items: list[dict], start: int = 0) -> int:
    if not items:
        return 0
    for i in range(start, len(items)):
        if items[i].get("kind") != "info":
            return i
    for i in range(0, min(start, len(items))):
        if items[i].get("kind") != "info":
            return i
    return 0


def _step_selectable(items: list[dict], index: int, step: int) -> int:
    if not items:
        return 0
    n = len(items)
    cur = index % n
    for _ in range(n):
        cur = (cur + step) % n
        if items[cur].get("kind") != "info":
            return cur
    return (index + step) % n


def _split_item_columns(item: dict) -> tuple[str, str, str]:
    """Split a clickable item label into (title, description, badge) for aligned rendering."""
    import re
    label = item.get("label", "")
    if item.get("kind") == "info":
        return (label, "", "")
    if " — " in label:
        parts = [p.strip() for p in label.split(" — ")]
        # Preserve provider titles that include an em-dash (e.g. "Hugging Face — Full Hub")
        if len(parts) >= 3 and parts[0] == "Hugging Face" and parts[1] in ("Full Hub", "Inference Available"):
            title = f"{parts[0]} — {parts[1]}"
            rest = parts[2:]
            if len(rest) >= 2:
                return (title, rest[0], " — ".join(rest[1:]))
            return (title, rest[0], "")
        if len(parts) >= 3 and "[" in parts[0] and "]" in parts[0]:
            return (parts[0], parts[1], " — ".join(parts[2:]))
        return (parts[0], " — ".join(parts[1:]), "")
    match = re.search(r"\s{2,}", label)
    if match:
        left = label[:match.start()].strip()
        right = label[match.end():].strip()
        if left and right:
            return (left, right, "")
    return (label, "", "")


def _with_row_bg(style: str, row_bg: str) -> str:
    if not row_bg or row_bg == "none":
        return style
    return f"{style} bg:{row_bg}".strip()


def _format_aligned_row(item: dict, selected: bool, title_w: int, desc_w: int) -> list[tuple[str, str]]:
    if item.get("kind") == "info":
        return [(_STYLE_INFO, f"  ℹ {item.get('label', '')}"), ("", "\n")]
    row_bg = item.get("bg_hex", "")
    title, desc, badge = _split_item_columns(item)
    marker_chunk = (_with_row_bg(_STYLE_MARKER, row_bg), "▶ ") if selected else (_with_row_bg("", row_bg), "  ")
    title_style = _with_row_bg(_STYLE_ITEM_SELECTED if selected else _STYLE_ITEM, row_bg)
    desc_style = _with_row_bg(_STYLE_DESC_SELECTED if selected else _STYLE_DESC, row_bg)
    chunks = [marker_chunk]
    if desc or badge:
        padded_title = title.ljust(title_w) if len(title) < title_w else title
        chunks.append((title_style, padded_title))
        if desc:
            if badge:
                padded_desc = desc.ljust(desc_w) if len(desc) < desc_w else desc
                chunks.append((desc_style, f"  {padded_desc}"))
            else:
                chunks.append((desc_style, f"  {desc}"))
        if badge:
            low = badge.lower()
            is_runnable = low.startswith("default:") or "ollama gguf" in low
            badge_style = _with_row_bg(_STYLE_BADGE_OK if is_runnable else _STYLE_BADGE_DIM, row_bg)
            chunks.append((badge_style, f"  · {badge}"))
    else:
        chunks.append((title_style, title))
    chunks.append(("", "\n"))
    return chunks


def _paginated_provider(state: _PaletteState) -> Optional[str]:
    if not state.view.startswith(('catalog_list:', 'catalog_provider:')):
        return None
    provider = state.view.split(':', 2)[1]
    from kurt.models.providers import EXTRA_PROVIDERS
    if provider not in EXTRA_PROVIDERS:
        return None
    from kurt.models.additional import peek_catalog
    return provider if peek_catalog(provider).get('next') else None


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
            tab_bar.append((_STYLE_TAB_ACTIVE if t == state.tab else _STYLE_TAB_INACTIVE, label))
            tab_bar.append(("", "  "))
        lines.append(tab_bar + [("", "\n")])
    elif state.view == "show_all":
        lines.append([(_STYLE_HEADER, "📖 All commands"), ("", "\n")])
    else:
        icon = {"skills": "🧠", "mcp": "🔌", "connectors": "🔗", "zapier": "⚡", "n8n": "⚙️",
                "agents": "⚙️", "plugins": "⚙️", "model": "🤖", "config": "🛠️",
                "config_theme": "🎨", "config_background": "🖼️", "config_icon": "🎯",
                "config_language": "🌐", "config_voice": "🎤", "config_greeting": "👋",
                "config_aimode": "🤖", "config_display": "🖥️", "config_reset": "♻️",
                "speech": "🎤", "wallet": "💳", "doctor": "🩺", "computer": "🖱️",
                "browser": "🌐", "tasks": "🗂️", "library": "📚",
                "model_catalog": "📚", "execution_defaults": "⚙️", "default_models": "💬",
                "cli_settings": "⌨️", "media_image": "🎨", "media_video": "🎬"}.get(state.view, "✨")
        title = {
            "execution_defaults": "Choose a default",
            "default_models": "Chat AI — save default",
            "model": "Chat AI — this session",
            "cli_settings": "CLI — save default",
            "media_image": "Image AI — save default",
            "media_video": "Video AI — save default",
            "config": "Personalize Kurt — pick a setting",
            "config_theme": "Color Themes — live background preview",
            "config_background": "Theme & Picker Background",
            "config_icon": "Kurt Icon — pick an emoji",
            "config_language": "Reply Language",
            "config_voice": "TTS Voice Preset",
            "config_greeting": "Greeting Style",
            "config_aimode": "AI Mode",
            "config_display": "Display Toggles",
            "config_reset": "Reset Persona Settings",
            "speech": "Voice & Speech Recognition",
            "wallet": "Kurt USD Wallet",
            "doctor": "System Diagnostics",
            "computer": "Desktop & Screen Actions",
            "browser": "Playwright Browser",
            "tasks": "Background Shell Tasks",
            "library": "Native Data Library (100 Domains)",
        }.get(state.view, state.view)
        if state.view == 'model_catalog':
            title = 'Complete AI model catalogs'
        elif state.view.startswith(('catalog_provider:', 'catalog_list:', 'catalog_model:')):
            from kurt.models.providers import PROVIDERS
            title = PROVIDERS[state.view.split(':')[1]]['name'] + ' — model catalog'
        elif state.view.startswith('model_setup:'):
            from kurt.models.providers import PROVIDERS
            title = PROVIDERS[state.view.split(':')[1]]['name'] + ' — connect / select model'
        elif state.view.startswith('provider_key_input:'):
            title = 'Enter API key — hidden, not submitted to chat'
        elif state.view.startswith('model_json_input:'):
            title = 'Paste JSON config (custom endpoint / GitHub repo / MCP) — saved privately'
        lines.append([(_STYLE_HEADER, f"{icon} {title}"), ("", "\n")])

    lines.append([(_STYLE_RULE, "  " + "─" * 58), ("", "\n")])

    if not items:
        lines.append([(_STYLE_INFO, "  (no matches)"), ("", "\n")])
    else:
        page = state.index // WINDOW
        total_pages = max(1, (len(items) + WINDOW - 1) // WINDOW)
        start = page * WINDOW
        end = min(len(items), start + WINDOW)
        visible = items[start:end]
        parsed = [_split_item_columns(item) for item in visible]
        title_lengths = [len(t) for item, (t, d, b) in zip(visible, parsed) if item.get("kind") != "info" and (d or b)]
        desc_lengths = [len(d) for item, (t, d, b) in zip(visible, parsed) if item.get("kind") != "info" and d and b]
        title_w = min(max(title_lengths, default=0), 42)
        if title_w:
            title_w = max(title_w, 14)
        desc_w = min(max(desc_lengths, default=0), 22)
        for i, item in enumerate(visible, start=start):
            lines.append(_format_aligned_row(item, i == state.index, title_w, desc_w))
        more_remote = bool(_paginated_provider(state)) and not query
        if len(items) > WINDOW or more_remote:
            jump = " · PgUp/PgDn ±10p" if total_pages >= 10 else ""
            more_hint = " · → at last page loads more" if more_remote else ""
            lines.append([(_STYLE_PAGE, f"  Page {page + 1:,}/{total_pages:,}{'+' if more_remote else ''}  ({start + 1:,}–{end:,} of {len(items):,}) · ←→ page{jump}{more_hint}"), ("", "\n")])

    if state.notice:
        lines.append([(_STYLE_NOTICE, f"  {state.notice}"), ("", "\n")])

    hint = ("  ↑↓ select  ←→ tabs  ? all  Tab⇥ home  Enter open/run  Esc back  Ctrl-C cancel"
            if state.view == "root" else
            "  ↑↓ select  ←→ page  PgUp/PgDn ±10p  Tab⇥ home  Enter open/run  Esc back  Ctrl-C cancel")
    lines.append([(_STYLE_HINT, hint)])

    result = []
    for chunk in lines:
        result.extend(chunk)
    return result


def _build_session() -> tuple[PromptSession, _PaletteState]:
    state = _PaletteState()
    kb = KeyBindings()

    palette_open = Condition(lambda: state.is_open)
    browsing = palette_open & Condition(lambda: not state.view.startswith(('provider_key_input:', 'model_json_input:')))
    at_root = Condition(lambda: state.is_open and state.view == "root")
    nested_browsing = browsing & Condition(lambda: state.view != "root")

    def _reset_query(buf):
        buf.text = "/"
        buf.cursor_position = 1

    def _jump_pages(event, delta: int):
        query = _effective_query(state, event.current_buffer.text)
        items = _current_items(state, query)
        if not items:
            return
        cur_page = (state.index % len(items)) // WINDOW
        total_pages = max(1, (len(items) + WINDOW - 1) // WINDOW)
        target_page = cur_page + delta
        if delta > 0 and target_page >= total_pages and not query:
            more_provider = _paginated_provider(state)
            if more_provider:
                from kurt.models.additional import fetch_catalog
                result = fetch_catalog(more_provider, more=True)
                items = _current_items(state, query)
                total_pages = max(1, (len(items) + WINDOW - 1) // WINDOW)
                state.notice = result.get('error') or f'Loaded more pages ({len(result["models"]):,} source model records cached).'
        target_page = max(0, min(target_page, total_pages - 1))
        new_index = target_page * WINDOW
        page_end = min(len(items), new_index + WINDOW)
        while new_index + 1 < page_end and items[new_index].get('kind') == 'info':
            new_index += 1
        state.index = new_index

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

    @kb.add("left", filter=nested_browsing, eager=True)
    def _page_prev(event):
        _jump_pages(event, -1)

    @kb.add("right", filter=nested_browsing, eager=True)
    def _page_next(event):
        _jump_pages(event, 1)

    @kb.add("pageup", filter=nested_browsing, eager=True)
    def _page_prev_ten(event):
        _jump_pages(event, -10)

    @kb.add("pagedown", filter=nested_browsing, eager=True)
    def _page_next_ten(event):
        _jump_pages(event, 10)

    @kb.add("up", filter=browsing, eager=True)
    def _up(event):
        items = _current_items(state, _effective_query(state, event.current_buffer.text))
        if items:
            state.index = _step_selectable(items, state.index, -1)

    @kb.add("down", filter=browsing, eager=True)
    def _down(event):
        items = _current_items(state, _effective_query(state, event.current_buffer.text))
        if items:
            state.index = _step_selectable(items, state.index, 1)

    @kb.add("?", filter=browsing, eager=True)
    def _show_all(event):
        state.view = "execution_defaults" if state.settings_only else "show_all"
        state.stack = []
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("tab", filter=browsing, eager=True)
    def _home(event):
        state.view = "execution_defaults" if state.settings_only else "root"
        state.tab = "commands"
        state.stack = []
        state.index = 0
        _reset_query(event.current_buffer)

    @kb.add("escape", filter=palette_open, eager=True)
    def _back(event):
        if state.view.startswith(('provider_key_input:', 'model_json_input:')):
            event.current_buffer.reset(append_to_history=False)
            event.app._kurt_secret_input = False
        if state.stack:
            state.view, state.tab = state.stack.pop()
            state.index = _first_selectable(_current_items(state, ""))
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
        if state.view.startswith(('provider_key_input:', 'model_json_input:')):
            event.current_buffer.reset(append_to_history=False)
            event.app._kurt_secret_input = False
            state.view, state.stack = 'root', []
        state.is_open = False
        event.app.exit(exception=KeyboardInterrupt())

    @kb.add("enter", filter=palette_open, eager=True)
    def _select(event):
        if state.view.startswith('model_json_input:'):
            from kurt.models.providers import save_model_json_config
            _, provider, encoded_mid = state.view.split(':', 2)
            mid = unquote(encoded_mid)
            try:
                saved = save_model_json_config(provider, mid, event.current_buffer.text)
            except (ValueError, OSError) as exc:
                state.notice = f'Config not saved: {exc} (Esc to cancel)'
                return
            event.current_buffer.reset(append_to_history=False)
            _reset_query(event.current_buffer)
            event.app._kurt_secret_input = False
            state.view, state.tab = state.stack.pop()
            state.index = _first_selectable(_current_items(state, ""))
            state.notice = saved['message']
            return
        if state.view.startswith('provider_key_input:'):
            from kurt.models.providers import save_provider_key
            provider = state.view.split(':', 1)[1]
            try:
                save_provider_key(provider, event.current_buffer.text)
            except (ValueError, OSError):
                state.notice = 'Key not saved. Enter one API token without spaces/placeholders, or Esc to cancel.'
                return
            from kurt.models.providers import EXTRA_PROVIDERS, HF_HUB_CATALOGS
            if provider in EXTRA_PROVIDERS:
                from kurt.models.additional import invalidate
                if provider in ({'huggingface'} | HF_HUB_CATALOGS):
                    for hf_provider in ('huggingface', 'huggingface_inference', 'huggingface_hub'):
                        invalidate(hf_provider)
                else:
                    invalidate(provider)
            elif provider == 'fal':
                global _fal_cache, _fal_cache_at
                _fal_cache, _fal_cache_at = None, 0
            elif provider == 'openrouter':
                global _openrouter_cache, _openrouter_cache_at
                _openrouter_cache, _openrouter_cache_at = None, 0
            event.current_buffer.reset(append_to_history=False)  # Drop secret undo/redo drafts too.
            _reset_query(event.current_buffer)  # Clear before turning off masking.
            event.app._kurt_secret_input = False
            state.view, state.tab = state.stack.pop()
            state.index = _first_selectable(_current_items(state, ""))
            state.notice = 'API key saved privately, not live-verified. Load/refresh the provider catalog if needed.'
            return
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
        if item['kind'] == 'provider_key':
            state.stack.append((state.view, state.tab))
            state.view = 'provider_key_input:' + item['provider']
            event.app._kurt_secret_input = True
            state.notice = ''
            state.index = 0
            event.current_buffer.reset(append_to_history=False)
            return
        if item['kind'] == 'model_json_config':
            state.stack.append((state.view, state.tab))
            state.view = f"model_json_input:{item['provider']}:{quote(item.get('mid', ''), safe='')}"
            event.app._kurt_secret_input = True
            state.notice = ''
            state.index = 0
            event.current_buffer.reset(append_to_history=False)
            return
        if item['kind'] == 'model_json_delete':
            from kurt.models.providers import delete_model_config
            removed = delete_model_config(item['provider'], item.get('mid', ''))
            state.notice = 'Saved JSON config removed.' if removed else 'No saved JSON config to remove.'
            state.index = _first_selectable(_current_items(state, _effective_query(state, buf_text)))
            return
        if item['kind'] in ('provider_refresh', 'provider_more'):
            from kurt.models.additional import fetch_catalog
            result = fetch_catalog(item['provider'], refresh=item['kind'] == 'provider_refresh', more=item['kind'] == 'provider_more')
            state.notice = result.get('error') or f'{len(result["models"]):,} source model records loaded.'
            state.index = _first_selectable(_current_items(state, _effective_query(state, buf_text)))
            return
        if item['kind'] == 'provider_search':
            from kurt.models.additional import search_catalog
            result = search_catalog(item['provider'], item['query'])
            state.notice = result.get('error') or f'{result["matched"]:,} live API matches loaded ({result["total_loaded"]:,} cached total).'
            state.index = _first_selectable(_current_items(state, _effective_query(state, buf_text)))
            return
        if item['kind'] == 'catalog_refresh':
            import io
            from contextlib import redirect_stdout
            with redirect_stdout(io.StringIO()) as captured:
                notice = refresh_model_catalogs()
            state.notice = notice + (' Refresh reported an error; cached data may be shown. Check provider credentials/network.' if captured.getvalue() else '')
            state.index = _first_selectable(_current_items(state, _effective_query(state, buf_text)))
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
            state.index = _first_selectable(_current_items(state, ""))
            _reset_query(event.current_buffer)
            return
        state.is_open = False
        value = item["value"]
        if value and args:
            value = f"{value} {args}"
        provider = _selection_provider(value)
        if provider and item.get('confirmed_provider') != provider:
            state.is_open = True
            state.stack.append((state.view, state.tab))
            state.view = f'model_setup:{provider}:{quote(value, safe="")}'
            state.index = _first_selectable(_current_items(state, ""))
            _reset_query(event.current_buffer)
            return
        if provider and item.get('billing'):
            from kurt.models.providers import confirm_byok, confirm_wallet
            try:
                (confirm_byok if item['billing'] == 'byok' else confirm_wallet)(provider)
            except (ValueError, OSError):
                state.is_open = True
                state.notice = 'Provider setup incomplete; key/billing selection was not applied. Check setup and try again.'
                return
        event.current_buffer.text = value
        event.app.exit(result=value)

    session = PromptSession(
        message=HTML("<ansicyan><b>You</b></ansicyan> <ansibrightblack>›</ansibrightblack> "),
        key_bindings=kb,
        bottom_toolbar=lambda: _render(state, session.default_buffer.text) if state.is_open else (
            [("dim", f"🎤 {_active_voice_input.status} · F5 toggle")]
            if _active_voice_input is not None else None),
        style=_STYLE,
        is_password=Condition(lambda: state.is_open and state.view.startswith('provider_key_input:')),
    )
    def sync_palette(buffer):
        # A deleted/replaced slash must not leave Enter trapped in an empty
        # picker. Standalone settings deliberately accept plain search text.
        from kurt.core.attachments import is_local_path_input
        if state.view.startswith(('provider_key_input:', 'model_json_input:')):
            return
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
    """Open the settings/config picker outside chat; run only a settings/config action."""
    import sys
    from kurt.core.persona import load_persona
    from kurt.core.cli_orchestrator import handle_slash
    from kurt.utils.env_loader import load_env
    load_env()
    if not sys.stdin.isatty():
        return False
    views = {
        None: "execution_defaults", "model": "default_models", "cli": "cli_settings",
        "image": "media_image", "video": "media_video",
        "config": "config", "theme": "config_theme", "background": "config_background",
        "icon": "config_icon", "language": "config_language", "voice": "config_voice",
        "greeting": "config_greeting", "aimode": "config_aimode", "display": "config_display",
    }
    if kind not in views:
        raise ValueError("Choose model, cli, image, video, theme, background, icon, language, voice, greeting, aimode or config.")
    session, state = _build_session()
    state.is_open = True
    state.view = views[kind]
    state.settings_only = True
    state.index = _first_selectable(_current_items(state, ""))
    try:
        with patch_stdout():
            command = session.prompt(default="/")
    except (KeyboardInterrupt, EOFError):
        return False
    allowed = ("/model default ", "/model choose-default", "/cli default ", "/image-model ", "/video-model ", "/config ")
    if not command.startswith(allowed):
        return False
    settings = load_persona()
    result = handle_slash(command, "settings", settings.get("default_model", "auto"), None)
    from rich.console import Console
    Console().print(result.output, markup=False)
    return True
