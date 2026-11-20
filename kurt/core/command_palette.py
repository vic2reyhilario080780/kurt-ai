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
import time
from urllib.parse import quote, unquote

from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
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
_openrouter_cache_at = 0
_fal_cache_at = 0


def _openrouter_models() -> list:
    """Complete OpenRouter catalog — cached in memory for up to an hour
    (fetch_models() itself disk-caches for an hour; this just avoids
    re-reading that file on every keystroke while browsing)."""
    global _openrouter_cache, _openrouter_cache_at
    if _openrouter_cache is None or (_openrouter_cache_at and time.monotonic() - _openrouter_cache_at > 3600):
        from kurt.models.openrouter import fetch_models
        try:
            _openrouter_cache = fetch_models() or []
        except Exception:
            _openrouter_cache = []
        _openrouter_cache_at = time.monotonic()
    return _openrouter_cache


def _fal_models() -> list:
    """Complete fal.ai catalog — only fetched if FAL_API_KEY is
    configured (fetch_models() itself prints a setup hint and needs a real
    key; skip calling it at all here rather than let that print corrupt the
    live palette render)."""
    global _fal_cache, _fal_cache_at
    if _fal_cache is None or (_fal_cache_at and time.monotonic() - _fal_cache_at > 3600):
        import os
        if not (os.getenv("FAL_API_KEY") or os.getenv("FAL_KEY")):
            _fal_cache = []
        else:
            from kurt.models.fal import fetch_models
            try:
                _fal_cache = fetch_models() or []
            except Exception:
                _fal_cache = []
        _fal_cache_at = time.monotonic()
    return _fal_cache


def _catalog_models(provider):
    from kurt.models.catalog import unique_models
    from kurt.models.providers import EXTRA_PROVIDERS
    if provider in EXTRA_PROVIDERS:
        from kurt.models.additional import fetch_catalog, without_primary_duplicates
        models = fetch_catalog(provider)['models']
        return without_primary_duplicates(provider, models, _openrouter_models(), _fal_models())[0]
    return unique_models(_openrouter_models() if provider == 'openrouter' else _fal_models())


def _catalog_link(provider):
    from kurt.models.providers import EXTRA_PROVIDERS, PROVIDERS
    if provider in EXTRA_PROVIDERS:
        from kurt.models.additional import peek_catalog, without_primary_duplicates
        snapshot = peek_catalog(provider)
        if not snapshot or not snapshot.get('models') and snapshot.get('error'):
            text = 'connect / load catalog — BYOK'
        else:
            visible, excluded = without_primary_duplicates(provider, snapshot['models'], _openrouter_models(), _fal_models())
            text = f'{len(visible):,} additional models; {len(excluded):,} primary duplicates excluded'
            if snapshot.get('next'):
                text += ' (more pages available)'
        return {'label': f'{PROVIDERS[provider]["name"]} — {text}', 'kind': 'open',
                'target': f'catalog_provider:{provider}', 'value': ''}
    total = len(_catalog_models(provider))
    label = PROVIDERS[provider]['name']
    return {'label': f'Full {label} catalog — {total:,} models / all categories',
            'kind': 'open', 'target': f'catalog_provider:{provider}', 'value': ''}


def _catalog_root_items(query):
    from kurt.models.providers import EXTRA_PROVIDERS
    rows = [_catalog_link(p) for p in ('openrouter', 'fal', *EXTRA_PROVIDERS)]
    rows.append({'label': 'Refresh provider catalogs', 'kind': 'catalog_refresh', 'value': ''})
    if query and not any(_matches(query, r['label']) for r in rows):
        from kurt.models.additional import peek_catalog, without_primary_duplicates
        extra = [r for p in EXTRA_PROVIDERS for r in _catalog_model_rows(p,
                 without_primary_duplicates(p, peek_catalog(p).get('models', []), _openrouter_models(), _fal_models())[0], query)]
        return [r for provider in ('openrouter', 'fal')
                for r in _catalog_model_rows(provider, _catalog_models(provider), query)] + extra
    return [r for r in rows if _matches(query, r['label'])]


def _catalog_model_rows(provider, models, query):
    from kurt.models.catalog import category, category_label, default_roles
    rows = []
    for model in models:
        mid = model['id']
        cat = category_label(provider, category(provider, model))
        title = model.get('name') or model.get('title') or mid
        roles = default_roles(provider, model)
        if roles:
            status = 'default: ' + '/'.join(roles) + (' + local Ollama GGUF' if model.get('ollama_gguf') else '')
        elif model.get('ollama_gguf'):
            status = 'local Ollama GGUF'
        else:
            status = 'browse only — workflow not supported'
        label = f'{title} [{mid}] — {cat} — {status}'
        if _matches(query, label):
            rows.append({'label': label, 'kind': 'open',
                         'target': f'catalog_model:{provider}:{quote(mid, safe="")}', 'value': ''})
    return rows


def _catalog_provider_items(provider, query, selected_category=None):
    from kurt.models.catalog import groups, category_label
    models = _catalog_models(provider)
    grouped = groups(provider, models)
    from kurt.models.providers import PROVIDERS, EXTRA_PROVIDERS, get_model_config
    from kurt.models.additional import LIVE_SEARCH_PROVIDERS
    label = PROVIDERS[provider]['name']
    if selected_category is not None:
        selected = models if selected_category == '*' else grouped.get(selected_category, [])
        rows = _catalog_model_rows(provider, selected, query)
        header = [{'label': f'{label}: {len(selected):,} models in this view / {len(models):,} visible loaded models; {len(rows):,} matches', 'kind': 'info'}]
        if query and provider in LIVE_SEARCH_PROVIDERS:
            cap = 50 if provider == 'replicate' else 100
            header.append({'label': f'Search {label} API live for "{query}" (top {cap} matches)',
                           'kind': 'provider_search', 'provider': provider, 'query': query})
        return header + rows
    if query:
        return _catalog_provider_items(provider, query, '*')
    rows = [{'label': f'{label}: {len(models):,} visible model IDs — category counts sum to {sum(map(len, grouped.values())):,}', 'kind': 'info'},
            {'label': f'All models — {len(models):,}', 'kind': 'open', 'target': f'catalog_list:{provider}:*'}]
    rows.extend({'label': f'{category_label(provider, cat)} — {len(items):,}', 'kind': 'open',
                 'target': f'catalog_list:{provider}:{quote(cat, safe="")}'} for cat, items in grouped.items())
    if not models:
        rows.append({'label': 'No catalog loaded; check /setup or enter API key below. This is not a live availability check.', 'kind': 'info'})
    rows += _provider_auth_items(provider)
    if PROVIDERS[provider].get('models_url'):
        rows.append({'label': f'Open {label} homepage / models catalog', 'kind': 'browser', 'url': PROVIDERS[provider]['models_url']})
    if get_model_config(provider):
        rows.append({'label': 'Saved JSON config: configured (0600 private)', 'kind': 'info'})
    rows.append({'label': 'Paste JSON config (GitHub repo / custom model / MCP)', 'kind': 'model_json_config', 'provider': provider, 'mid': ''})
    if get_model_config(provider):
        rows.append({'label': 'Remove saved JSON config', 'kind': 'model_json_delete', 'provider': provider, 'mid': ''})
    if provider in EXTRA_PROVIDERS:
        from kurt.models.additional import peek_catalog
        snapshot = peek_catalog(provider)
        rows.append({'label': PROVIDERS[provider]['scope'], 'kind': 'info'})
        rows.append({'label': f'{len(snapshot.get("models", [])):,} source records loaded; {len(snapshot.get("models", [])) - len(models):,} exact primary duplicates excluded. '
                     + ('Catalog complete.' if snapshot.get('complete') else 'More pages may be available; this is not a complete provider total.'), 'kind': 'info'})
        if snapshot.get('error'):
            rows.append({'label': snapshot['error'], 'kind': 'info'})
        if snapshot.get('next'):
            rows.append({'label': 'Load next catalog pages', 'kind': 'provider_more', 'provider': provider})
    rows.append({'label': 'Refresh all provider catalogs', 'kind': 'catalog_refresh', 'value': ''})
    return rows


def _valid_github_url(value):
    if not isinstance(value, str) or not value.strip():
        return None
    from urllib.parse import urlsplit
    parsed = urlsplit(value.strip())
    if parsed.scheme == 'https' and parsed.netloc in ('github.com', 'www.github.com') and parsed.path.strip('/'):
        return value.strip()
    return None


def _catalog_model_items(provider, mid, settings_only=False):
    from kurt.models.catalog import category, category_label, default_roles
    from kurt.models.providers import PROVIDERS, get_model_config, custom_endpoint_config
    model = next((m for m in _catalog_models(provider) if m['id'] == mid), None)
    if model is None:
        return [{'label': 'Model no longer in this catalog; refresh and search again.', 'kind': 'info'}]
    roles = default_roles(provider, model)
    is_gguf = bool(model.get('ollama_gguf'))
    custom_cfg = custom_endpoint_config(provider, mid)
    rows = [{'label': f'{mid} [{provider}] — {category_label(provider, category(provider, model))}', 'kind': 'info'}]
    if provider == 'openrouter':
        rows.append({'label': _pricing_hint(model), 'kind': 'info'})
    if any(model.get(k) is not None for k in ('downloads', 'likes', 'library_name', 'run_count')):
        parts = []
        if isinstance(model.get('downloads'), int):
            parts.append(f'Downloads: {model["downloads"]:,}')
        if isinstance(model.get('likes'), int):
            parts.append(f'Likes: {model["likes"]:,}')
        if isinstance(model.get('run_count'), int):
            parts.append(f'Runs: {model["run_count"]:,}')
        if isinstance(model.get('library_name'), str) and model['library_name']:
            parts.append(f'Library: {model["library_name"]}')
        if parts:
            rows.append({'label': ' · '.join(parts), 'kind': 'info'})
    if provider in ('huggingface_inference', 'huggingface_hub') and isinstance(model.get('inference_providers'), list) and model['inference_providers']:
        live_labels = [f"{e['provider']} ({e['task']})" for e in model['inference_providers']
                       if isinstance(e, dict) and e.get('status') == 'live']
        if live_labels:
            rows.append({'label': 'Live HF Inference: ' + ', '.join(live_labels[:6]), 'kind': 'info'})
    if custom_cfg:
        rows.append({'label': f"Custom endpoint ready: {custom_cfg['base_url']} (roles: {'/'.join(custom_cfg['roles'])})", 'kind': 'info'})
    if not roles and not is_gguf:
        rows.append({'label': 'Visible in the full catalog. Paste a custom endpoint JSON config below to run it, or open the model page.', 'kind': 'info'})
    if 'chat' in roles:
        if not settings_only:
            rows.append({'label': 'Use for chat in this session', 'kind': 'leaf', 'value': f'/model {mid} {provider}'})
        rows.append({'label': 'Save as default Chat AI', 'kind': 'leaf', 'value': f'/model default {mid} {provider}'})
    for kind in ('image', 'video'):
        if kind in roles:
            rows.append({'label': f'Save as default {kind.title()} AI', 'kind': 'leaf', 'value': f'/{kind}-model {mid} {provider}'})
    if is_gguf:
        ollama_id = f'hf.co/{mid}'
        rows.append({'label': f"Local GGUF (Ollama): run 'ollama pull {ollama_id}' first if not downloaded (no auto-download).", 'kind': 'info'})
        if not settings_only:
            rows.append({'label': f'Use locally via Ollama ({ollama_id}) in this session', 'kind': 'leaf', 'value': f'/model {ollama_id} ollama'})
        rows.append({'label': f'Save as default Chat AI (local Ollama {ollama_id})', 'kind': 'leaf', 'value': f'/model default {ollama_id} ollama'})
    base = {
        'openrouter': 'https://openrouter.ai/',
        'fal': 'https://fal.ai/models/',
        'huggingface': 'https://huggingface.co/',
        'huggingface_inference': 'https://huggingface.co/',
        'huggingface_hub': 'https://huggingface.co/',
        'replicate': 'https://replicate.com/',
    }.get(provider)
    url = base + quote(mid, safe='/') if base else PROVIDERS[provider]['models_url']
    rows += _provider_auth_items(provider)
    rows.append({'label': 'Open official model page / setup requirements', 'kind': 'browser', 'url': url})
    gh_url = _valid_github_url(model.get('github_url'))
    if gh_url:
        rows.append({'label': f'Open GitHub repository — {gh_url}', 'kind': 'browser', 'url': gh_url})
    if get_model_config(provider, mid):
        rows.append({'label': 'Saved JSON config: configured (0600 private)', 'kind': 'info'})
    rows.append({'label': 'Paste JSON config (GitHub repo / custom model / MCP)', 'kind': 'model_json_config', 'provider': provider, 'mid': mid})
    if get_model_config(provider, mid):
        rows.append({'label': 'Remove saved JSON config', 'kind': 'model_json_delete', 'provider': provider, 'mid': mid})
    rows.append({'label': 'Catalog listing is not proof of account access, credits or successful generation.', 'kind': 'info'})
    return rows


def _provider_auth_items(provider, command=''):
    from kurt.models.providers import PROVIDERS, provider_key, BYOK_ONLY_PROVIDERS, custom_endpoint_config
    spec = PROVIDERS[provider]
    configured = bool(provider_key(provider)) if spec['key'] else True
    custom_ready = False
    if command:
        parts = command.split()
        idx = 2 if parts[:2] == ['/model', 'default'] else 1
        cmd_mid = parts[idx] if len(parts) > idx else ''
        if cmd_mid and custom_endpoint_config(provider, cmd_mid):
            custom_ready = True
    rows = [{'label': f'{spec["name"]}: ' + ('key saved (not live-verified)' if configured and spec['key'] else 'local; no API key needed' if not spec['key'] else 'custom JSON endpoint configured' if custom_ready else 'API key not configured'), 'kind': 'info'}]
    if spec['key']:
        rows.append({'label': 'Enter / replace API key — hidden input', 'kind': 'provider_key', 'provider': provider})
    rows.append({'label': 'Open official API key / login page' if spec['key'] else 'Open local provider setup page',
                 'kind': 'browser', 'url': spec['keys_url']})
    from kurt.models.providers import EXTRA_PROVIDERS
    if provider in EXTRA_PROVIDERS:
        rows.append({'label': 'Load / refresh this provider catalog (read-only)', 'kind': 'provider_refresh', 'provider': provider})
    if command:
        if custom_ready and not configured:
            rows.append({'label': 'Use saved custom JSON endpoint and select model',
                         'kind': 'leaf', 'value': command})
        elif configured:
            rows.append({'label': 'Use my saved provider key (BYOK) and select model' if spec['key'] else 'Select local model',
                         'kind': 'leaf', 'value': command, 'confirmed_provider': provider, 'billing': 'byok'})
        else:
            rows.append({'label': 'Add your API key above before selecting this model.', 'kind': 'info'})
        from kurt.billing.client import active
        if active() and provider not in BYOK_ONLY_PROVIDERS and spec['key']:
            rows.append({'label': 'Use Kurt wallet instead of my own provider key', 'kind': 'leaf',
                         'value': command, 'confirmed_provider': provider, 'billing': 'wallet'})
    rows.append({'label': 'BYOK uses your provider balance; it does not deduct Kurt wallet credits. Website login happens in your browser.', 'kind': 'info'})
    return rows


def _selection_provider(command):
    from kurt.core.execution_preferences import parse_model
    parts = command.split()
    if not parts or parts[0] not in ('/model', '/image-model', '/video-model'):
        return None
    index = 2 if parts[:2] == ['/model', 'default'] else 1
    if len(parts) <= index or parts[index] in ('auto', 'choose', 'choose-default'):
        return None
    try:
        _, provider = parse_model(parts[index], parts[index + 1] if len(parts) > index + 1 else None)
        return provider
    except ValueError:
        return None


def refresh_model_catalogs():
    """Explicit refresh is also available without leaving a settings picker."""
    global _openrouter_cache, _fal_cache, _openrouter_cache_at, _fal_cache_at
    from kurt.models.openrouter import fetch_models as fetch_openrouter
    from kurt.models.fal import fetch_models as fetch_fal
    _openrouter_cache = fetch_openrouter(use_cache=False)
    _fal_cache = fetch_fal(use_cache=False)
    _openrouter_cache_at = _fal_cache_at = time.monotonic()
    from kurt.models.providers import EXTRA_PROVIDERS
    from kurt.models.additional import fetch_catalog
    for provider in EXTRA_PROVIDERS:
        fetch_catalog(provider, refresh=True)
    return f'Catalogs loaded: OpenRouter {len(_catalog_models("openrouter")):,}; fal.ai {len(_catalog_models("fal")):,}. Optional BYOK catalogs updated where accessible; unavailable providers retain saved data. Paginated catalogs may need Load next pages.'


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
    for model, provider in (("mistral-small-latest", "mistral"), ("gemini-3.5-flash-lite", "google"), ("deepseek-flash", "deepseek"), ("deepseek-v4-pro", "deepseek")):
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
    rows.append(_catalog_link('openrouter'))
    rows.append({'label': 'Additional providers — BYOK catalogs', 'kind': 'open', 'target': 'model_catalog', 'value': ''})
    rows.extend({"label": label, "kind": "leaf", "value": f"/model {model}" + (f" {provider}" if provider != "openrouter" else "")}
                for model, provider, label in _chat_choices())
    return [row for row in rows if _matches(query, row["label"])]


def _default_model_items(query):
    rows = [{"label": "Choose chat provider + exact model ID", "kind": "leaf", "value": "/model choose-default"},
            {"label": "Auto — let Kurt route chat requests", "kind": "leaf", "value": "/model default auto"}]
    rows.append(_catalog_link('openrouter'))
    rows.append({'label': 'Additional providers — BYOK catalogs', 'kind': 'open', 'target': 'model_catalog', 'value': ''})
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
    rows.append(_catalog_link('fal'))
    rows.append({'label': 'Additional providers — BYOK catalogs', 'kind': 'open', 'target': 'model_catalog', 'value': ''})
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


_CONFIG_PICKER_TARGETS = {
    "theme": "config_theme",
    "background": "config_background",
    "icon": "config_icon",
    "language": "config_language",
    "voice": "config_voice",
    "greeting": "config_greeting",
    "aimode": "config_aimode",
    "display": "config_display",
    "reset": "config_reset",
    "model": "default_models",
    "cli": "cli_settings",
    "image": "media_image",
    "video": "media_video",
}


def _safe_persona() -> dict:
    try:
        from kurt.core.persona import load_persona
        return load_persona()
    except OSError:
        from kurt.core.persona import DEFAULT_PERSONA
        return dict(DEFAULT_PERSONA)


def _config_items(query: str) -> list[dict]:
    return [
        {"label": f"{sub:<12} {desc}", "kind": "open", "target": _CONFIG_PICKER_TARGETS[sub]}
        if sub in _CONFIG_PICKER_TARGETS else
        {"label": f"{sub:<12} {desc}", "kind": "leaf", "value": f"/config {sub}"}
        for sub, desc in CONFIG_SUBCOMMANDS
        if _matches(query, sub, desc)
    ]


def _config_theme_items(query: str) -> list[dict]:
    from kurt.core.persona import BUILTIN_THEMES
    p = _safe_persona()
    cur = p.get("theme", "cyber")
    rows = [{"label": f"Current theme: {cur} — Enter to apply immediately (preview shows each theme's background)", "kind": "info"}]
    for key, theme in BUILTIN_THEMES.items():
        prefix = theme.get("emoji_prefix", "●")
        bg_hex = theme.get("bg_hex", "")
        mark = " · ✓ current" if key == cur else ""
        bg_note = bg_hex or "transparent"
        rows.append({
            "label": f"{prefix} {key} — {theme['name']} (bg: {bg_note}){mark}",
            "kind": "leaf",
            "value": f"/config theme {key}",
            "bg_hex": bg_hex or "none",
        })
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_background_items(query: str) -> list[dict]:
    from kurt.core.persona import BUILTIN_BACKGROUNDS, get_theme_bg_hex
    p = _safe_persona()
    cur = p.get("custom_background", "theme")
    rows = [{"label": f"Current background: {cur} ({get_theme_bg_hex(p) or 'transparent'}) — Enter to apply", "kind": "info"}]
    for key, spec in BUILTIN_BACKGROUNDS.items():
        mark = " · ✓ current" if key == cur else ""
        hx = spec["hex"]
        preview = hx if hx.startswith("#") else ("none" if hx == "none" else get_theme_bg_hex(p) or "none")
        rows.append({
            "label": f"{spec['name']} [{key}] — {spec['desc']}{mark}",
            "kind": "leaf",
            "value": f"/config background {key}",
            "bg_hex": preview,
        })
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_icon_items(query: str) -> list[dict]:
    from kurt.core.persona import BUILTIN_ICONS
    cur = _safe_persona().get("icon", "robot")
    rows = [{"label": f"Current icon: {cur} — Enter to select", "kind": "info"}]
    for key, emoji in BUILTIN_ICONS.items():
        mark = " · ✓ current" if key == cur else ""
        if emoji is None:
            rows.append({"label": f"✨ custom — Enter your own emoji/icon{mark}", "kind": "leaf", "value": "/config icon custom"})
        else:
            rows.append({"label": f"{emoji} {key} — Use {emoji} as Kurt's icon{mark}", "kind": "leaf", "value": f"/config icon {key}"})
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_language_items(query: str) -> list[dict]:
    from kurt.core.persona import SUPPORTED_LANGUAGES
    cur = _safe_persona().get("language", "taglish")
    rows = [{"label": f"Current language: {cur} — Enter to select", "kind": "info"}]
    for code, lang in SUPPORTED_LANGUAGES.items():
        mark = " · ✓ current" if code == cur else ""
        rows.append({"label": f"{lang['flag']} {lang['name']} [{code}] — Reply in {lang['name']}{mark}", "kind": "leaf", "value": f"/config language {code}"})
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_voice_items(query: str) -> list[dict]:
    from kurt.core.persona import VOICE_PRESETS
    cur = _safe_persona().get("voice", "young_boy")
    rows = [{"label": f"Current TTS voice: {cur} — Enter to select", "kind": "info"}]
    for key, spec in VOICE_PRESETS.items():
        mark = " · ✓ current" if key == cur else ""
        rows.append({"label": f"🎤 {spec['label']} [{key}] — Edge voice {spec['edge_voice']}{mark}", "kind": "leaf", "value": f"/config voice {key}"})
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_greeting_items(query: str) -> list[dict]:
    cur = _safe_persona().get("greeting_style", "casual")
    opts = [
        ("casual", "Relaxed, friendly Taglish/English greetings"),
        ("professional", "Formal, respectful greetings"),
        ("hype", "Energetic, excited greetings 🔥"),
    ]
    rows = [{"label": f"Current greeting style: {cur} — Enter to select", "kind": "info"}]
    for key, desc in opts:
        mark = " · ✓ current" if key == cur else ""
        rows.append({"label": f"{key} — {desc}{mark}", "kind": "leaf", "value": f"/config greeting {key}"})
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_aimode_items(query: str) -> list[dict]:
    cur = _safe_persona().get("ai_mode", "hybrid")
    opts = [
        ("hybrid", "KURT routing + Claude fallback/boost"),
        ("kurt_only", "KURT providers only (OpenRouter/Groq/Ollama/BYOK)"),
        ("claude_only", "Claude only (requires ANTHROPIC_API_KEY)"),
    ]
    rows = [{"label": f"Current AI mode: {cur} — Enter to select", "kind": "info"}]
    for key, desc in opts:
        mark = " · ✓ current" if key == cur else ""
        rows.append({"label": f"{key} — {desc}{mark}", "kind": "leaf", "value": f"/config aimode {key}"})
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _config_display_items(query: str) -> list[dict]:
    p = _safe_persona()
    compact = bool(p.get("compact_mode", False))
    routing = bool(p.get("show_routing_info", False))
    rows = [
        {"label": f"Compact Mode — currently {'ON' if compact else 'OFF'} (toggle {'OFF' if compact else 'ON'})",
         "kind": "leaf", "value": f"/config compact {'off' if compact else 'on'}"},
        {"label": f"Show Routing Info — currently {'ON' if routing else 'OFF'} (toggle {'OFF' if routing else 'ON'})",
         "kind": "leaf", "value": f"/config routing {'off' if routing else 'on'}"},
    ]
    return [r for r in rows if _matches(query, r["label"])]


def _config_reset_items(query: str) -> list[dict]:
    rows = [
        {"label": "Warning: resets theme, background, icon, language, voice & defaults to factory values.", "kind": "info"},
        {"label": "Cancel — keep current persona settings", "kind": "leaf", "value": "/config reset cancel"},
        {"label": "Confirm Reset — restore all persona defaults", "kind": "leaf", "value": "/config reset"},
    ]
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _speech_items(query: str) -> list[dict]:
    p = _safe_persona()
    prov = p.get("speech_provider", "auto")
    lang = p.get("speech_language", "auto")
    pause = p.get("speech_pause_seconds", 2.0)
    rows = [
        {"label": f"Speech settings: provider={prov} · language={lang} · pause={pause}s", "kind": "info"},
        {"label": "Status — inspect speech readiness, mic & vocabulary", "kind": "leaf", "value": "/speech status"},
        {"label": f"Provider: Auto — Groq when configured, else cached local{' · ✓' if prov == 'auto' else ''}", "kind": "leaf", "value": "/speech provider auto"},
        {"label": f"Provider: Groq — Whisper large-v3/turbo online{' · ✓' if prov == 'groq' else ''}", "kind": "leaf", "value": "/speech provider groq"},
        {"label": f"Provider: Local — cached local Whisper only{' · ✓' if prov == 'local' else ''}", "kind": "leaf", "value": "/speech provider local"},
        {"label": f"Language: Auto (Taglish) — automatic mixed Filipino/English{' · ✓' if lang == 'auto' else ''}", "kind": "leaf", "value": "/speech language auto"},
        {"label": f"Language: Tagalog (tl) — explicit Filipino speech recognition{' · ✓' if lang == 'tl' else ''}", "kind": "leaf", "value": "/speech language tl"},
        {"label": f"Language: English (en) — explicit English speech recognition{' · ✓' if lang == 'en' else ''}", "kind": "leaf", "value": "/speech language en"},
        {"label": "Pause: 1.0s — faster reply after speaking", "kind": "leaf", "value": "/speech pause 1.0"},
        {"label": "Pause: 1.5s — balanced trailing silence", "kind": "leaf", "value": "/speech pause 1.5"},
        {"label": "Pause: 2.0s — default trailing silence", "kind": "leaf", "value": "/speech pause 2.0"},
        {"label": "Pause: 3.0s — extra thinking time mid-sentence", "kind": "leaf", "value": "/speech pause 3.0"},
        {"label": "Pause: 4.0s — maximum pause before sending", "kind": "leaf", "value": "/speech pause 4.0"},
        {"label": "Tip: add custom vocabulary words via /speech word-add <name>", "kind": "info"},
    ]
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _wallet_items(query: str) -> list[dict]:
    rows = [
        {"label": "Kurt Wallet — USD actual provider costs, 0% markup", "kind": "info"},
        {"label": "Status — view USD balance, holds & available funds", "kind": "leaf", "value": "/wallet status"},
        {"label": "History — view recent wallet ledger entries", "kind": "leaf", "value": "/wallet history"},
        {"label": "Catalog — view wallet-supported providers", "kind": "leaf", "value": "/wallet catalog"},
        {"label": "Top up $5 — create $5 USD Stripe Checkout link", "kind": "leaf", "value": "/wallet topup 5"},
        {"label": "Top up $10 — create $10 USD Stripe Checkout link", "kind": "leaf", "value": "/wallet topup 10"},
        {"label": "Top up $25 — create $25 USD Stripe Checkout link", "kind": "leaf", "value": "/wallet topup 25"},
    ]
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _doctor_items(query: str) -> list[dict]:
    rows = [
        {"label": "Summary — overall system health diagnostics", "kind": "leaf", "value": "/doctor summary"},
        {"label": "CPU — top CPU-consuming processes", "kind": "leaf", "value": "/doctor cpu"},
        {"label": "Memory — RAM & swap pressure report", "kind": "leaf", "value": "/doctor mem"},
        {"label": "Disk — free storage space & largest folders", "kind": "leaf", "value": "/doctor disk"},
        {"label": "Network — active interfaces & connectivity", "kind": "leaf", "value": "/doctor net"},
        {"label": "Crashes — recent crash reports & logs", "kind": "leaf", "value": "/doctor crashes"},
        {"label": "Startup — login items & background launch agents", "kind": "leaf", "value": "/doctor startup"},
    ]
    return [r for r in rows if _matches(query, r["label"])]


def _computer_items(query: str) -> list[dict]:
    rows = [
        {"label": "Screenshot — capture current screen to ~/.kurt/screenshots", "kind": "leaf", "value": "/computer screenshot"},
        {"label": "Analyze screen — describe what is currently on screen", "kind": "leaf", "value": "/computer analyze"},
        {"label": "Open current folder — reveal workspace in Finder/Explorer", "kind": "leaf", "value": "/computer open ."},
        {"label": "Open Downloads — reveal ~/Downloads folder", "kind": "leaf", "value": "/computer open ~/Downloads"},
        {"label": "Open Desktop — reveal ~/Desktop folder", "kind": "leaf", "value": "/computer open ~/Desktop"},
    ]
    return [r for r in rows if _matches(query, r["label"])]


def _browser_items(query: str) -> list[dict]:
    rows = [
        {"label": "Playwright browser controls (type /browser open <url> to navigate)", "kind": "info"},
        {"label": "Screenshot — save screenshot of current open page", "kind": "leaf", "value": "/browser screenshot"},
        {"label": "Close — shut down persistent browser session", "kind": "leaf", "value": "/browser close"},
    ]
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


def _tasks_items(query: str) -> list[dict]:
    rows = [{"label": "List tasks — show all background shell tasks", "kind": "leaf", "value": "/tasks list"}]
    try:
        from kurt.core.subagents import manage_background_task
        listed = manage_background_task(action="list")
        for task in listed.get("tasks", []) if isinstance(listed, dict) else []:
            tid = task.get("id") or task.get("task_id")
            if not tid:
                continue
            status = task.get("status", "unknown")
            cmd = str(task.get("cmd", ""))[:36]
            rows.append({"label": f"Status {tid} — [{status}] {cmd}", "kind": "leaf", "value": f"/tasks status {tid}"})
            if status == "running":
                rows.append({"label": f"Kill {tid} — stop running task ({cmd})", "kind": "leaf", "value": f"/tasks kill {tid}"})
    except Exception:
        pass
    return [r for r in rows if _matches(query, r["label"])]


def _library_items(query: str) -> list[dict]:
    rows = [
        {"label": "Stats — native library overview & counts", "kind": "leaf", "value": "/library stats"},
        {"label": "All domains — list all 100 native data domains", "kind": "leaf", "value": "/library domains"},
    ]
    try:
        from kurt.capabilities import runtime
        domains = sorted({e["domain"] for e in runtime.manifest().get("index", []) if e.get("domain")})
        for dom in domains:
            rows.append({"label": f"{dom} — inspect native workflows & metrics", "kind": "leaf", "value": f"/library domains {dom}"})
    except Exception:
        pass
    return [r for r in rows if _matches(query, r["label"])]


def _current_items(state: _PaletteState, query: str) -> list[dict]:
    if state.view.startswith('provider_key_input:'):
        return [{'label': 'Paste API key (hidden). Enter saves privately; Esc cancels. Nothing is sent to an AI.', 'kind': 'info'}]
    if state.view.startswith('model_json_input:'):
        return [{'label': 'Paste JSON config object (or path to .json file). Enter saves privately; Esc cancels. Nothing is executed.', 'kind': 'info'}]
    if state.view.startswith('model_setup:'):
        _, provider, command = state.view.split(':', 2)
        return [r for r in _provider_auth_items(provider, unquote(command)) if _matches(query, r['label'])]
    if state.view == 'model_catalog':
        return _catalog_root_items(query)
    if state.view.startswith('catalog_provider:'):
        return _catalog_provider_items(state.view.split(':', 1)[1], query)
    if state.view.startswith('catalog_list:'):
        _, provider, category = state.view.split(':', 2)
        return _catalog_provider_items(provider, query, unquote(category))
    if state.view.startswith('catalog_model:'):
        _, provider, mid = state.view.split(':', 2)
        rows = _catalog_model_items(provider, unquote(mid), state.settings_only)
        return [r for r in rows if _matches(query, r['label'])]
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
    if state.view == "config_theme":
        return _config_theme_items(query)
    if state.view == "config_background":
        return _config_background_items(query)
    if state.view == "config_icon":
        return _config_icon_items(query)
    if state.view == "config_language":
        return _config_language_items(query)
    if state.view == "config_voice":
        return _config_voice_items(query)
    if state.view == "config_greeting":
        return _config_greeting_items(query)
    if state.view == "config_aimode":
        return _config_aimode_items(query)
    if state.view == "config_display":
        return _config_display_items(query)
    if state.view == "config_reset":
        return _config_reset_items(query)
    if state.view == "speech":
        return _speech_items(query)
    if state.view == "wallet":
        return _wallet_items(query)
    if state.view == "doctor":
        return _doctor_items(query)
    if state.view == "computer":
        return _computer_items(query)
    if state.view == "browser":
        return _browser_items(query)
    if state.view == "tasks":
        return _tasks_items(query)
    if state.view == "library":
        return _library_items(query)

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
        parts = label.split(" — ")
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
