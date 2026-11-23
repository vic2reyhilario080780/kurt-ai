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

Split into state.py (palette state + live-filter parsing), items.py
(every `_xxx_items` picker data provider + the `_current_items`
dispatcher) and engine.py (visual styles + the interactive render/session
loop) — this file re-exports every public and internal name those three
modules used to expose directly, so `from kurt.core.command_palette import
X` and `kurt.core.command_palette.X` keep resolving exactly as before the
split. Tests that monkeypatch a name which is *also* read internally by a
sibling function (e.g. `PromptSession` inside `_build_session`, or
`_openrouter_models` inside `_catalog_root_items`) must patch the owning
submodule directly (`command_palette.engine.X` / `command_palette.items.X`)
for the patch to be visible to that internal call — patching this
package's own copy of the name only affects code that looks the name up
through this package's namespace.
"""

from . import state, items, engine

from .state import (
    ROOT_TABS, TAB_LABELS, WINDOW, OPEN_TARGETS, CONFIG_SUBCOMMANDS,
    _active_bg_hex, _build_toolbar_style, _STYLE, _PaletteState,
    _after_slash, _effective_query, _pending_args, _matches, _flat_commands,
)

from .items import (
    _skills_items, _catalog_entries, _mcp_items, _composio_curated,
    _connector_items, _zapier_picker_items, _n8n_picker_items,
    _connector_detail_items, _capability_items, _openrouter_models,
    _fal_models, _catalog_models, _catalog_link, _catalog_root_items,
    _catalog_model_rows, _catalog_provider_items, _valid_github_url,
    _catalog_model_items, _provider_auth_items, _selection_provider,
    refresh_model_catalogs, _is_chat_model, _pricing_hint, _chat_choices,
    _model_items, _default_model_items, _execution_default_items,
    _cli_default_items, _media_model_items, _CONFIG_PICKER_TARGETS,
    _safe_persona, _config_items, _config_theme_items,
    _config_background_items, _config_icon_items, _config_language_items,
    _config_voice_items, _config_greeting_items, _config_aimode_items,
    _config_display_items, _config_reset_items, _speech_items,
    _wallet_items, _doctor_items, _computer_items, _browser_items,
    _tasks_items, _library_items, _current_items,
)

from .engine import (
    PromptSession,
    _personalized_highlight_style, _STYLE_HEADER, _STYLE_RULE,
    _STYLE_TAB_ACTIVE, _STYLE_TAB_INACTIVE, _STYLE_MARKER, _STYLE_ITEM,
    _STYLE_ITEM_SELECTED, _STYLE_DESC, _STYLE_DESC_SELECTED,
    _STYLE_BADGE_OK, _STYLE_BADGE_DIM, _STYLE_INFO, _STYLE_PAGE,
    _STYLE_NOTICE, _STYLE_HINT, _first_selectable, _step_selectable,
    _split_item_columns, _with_row_bg, _format_aligned_row,
    _paginated_provider, _render, _build_session, _active_voice_input,
    _session, _state, read_chat_input, pick_execution_default,
)

__all__ = [
    "state", "items", "engine",
    "ROOT_TABS", "TAB_LABELS", "WINDOW", "OPEN_TARGETS", "CONFIG_SUBCOMMANDS",
    "_active_bg_hex", "_build_toolbar_style", "_STYLE", "_PaletteState",
    "_after_slash", "_effective_query", "_pending_args", "_matches", "_flat_commands",
    "_skills_items", "_catalog_entries", "_mcp_items", "_composio_curated",
    "_connector_items", "_zapier_picker_items", "_n8n_picker_items",
    "_connector_detail_items", "_capability_items", "_openrouter_models",
    "_fal_models", "_catalog_models", "_catalog_link", "_catalog_root_items",
    "_catalog_model_rows", "_catalog_provider_items", "_valid_github_url",
    "_catalog_model_items", "_provider_auth_items", "_selection_provider",
    "refresh_model_catalogs", "_is_chat_model", "_pricing_hint", "_chat_choices",
    "_model_items", "_default_model_items", "_execution_default_items",
    "_cli_default_items", "_media_model_items", "_CONFIG_PICKER_TARGETS",
    "_safe_persona", "_config_items", "_config_theme_items",
    "_config_background_items", "_config_icon_items", "_config_language_items",
    "_config_voice_items", "_config_greeting_items", "_config_aimode_items",
    "_config_display_items", "_config_reset_items", "_speech_items",
    "_wallet_items", "_doctor_items", "_computer_items", "_browser_items",
    "_tasks_items", "_library_items", "_current_items",
    "PromptSession",
    "_personalized_highlight_style", "_STYLE_HEADER", "_STYLE_RULE",
    "_STYLE_TAB_ACTIVE", "_STYLE_TAB_INACTIVE", "_STYLE_MARKER", "_STYLE_ITEM",
    "_STYLE_ITEM_SELECTED", "_STYLE_DESC", "_STYLE_DESC_SELECTED",
    "_STYLE_BADGE_OK", "_STYLE_BADGE_DIM", "_STYLE_INFO", "_STYLE_PAGE",
    "_STYLE_NOTICE", "_STYLE_HINT", "_first_selectable", "_step_selectable",
    "_split_item_columns", "_with_row_bg", "_format_aligned_row",
    "_paginated_provider", "_render", "_build_session", "_active_voice_input",
    "_session", "_state", "read_chat_input", "pick_execution_default",
]
