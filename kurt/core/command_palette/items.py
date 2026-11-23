"""Picker data providers — every `_xxx_items(query)` builder, plus the
root `_current_items` dispatcher and model/catalog helpers. Each item here
is just the pre-existing function a typed command already calls; nothing
here is new business logic except the `/mcp authorize` arm added to
cli_orchestrator.py."""

from typing import Optional
import time
from urllib.parse import quote, unquote

from kurt.core.cli_orchestrator import SLASH_COMMANDS

from .state import _PaletteState, _matches, _flat_commands, OPEN_TARGETS, CONFIG_SUBCOMMANDS


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

    items = []
    try:
        registry = load_registry()
    except (ValueError, OSError) as exc:
        registry = {}
        items.append({"label": f"MCP registry unavailable ({exc}); showing built-in presets & catalog", "kind": "info"})
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
        try:
            saved = load_registry().get(ref)
        except (ValueError, OSError):
            saved = None
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
    items = [
        {"label": f"{r['id']}  —  {r['name']}", "kind": "leaf", "value": f"{cmd} {r['id']}"}
        for r in rows
    ]
    disclosure = (
        "ℹ Deterministic plugin, fixture-tested directly"
        if kind == "plugin" else
        f"ℹ Deterministic workflow when run directly via {cmd} run; relies on a correct "
        "AI tool-call when chosen autonomously in chat — not fixture-verified in that path"
    )
    return [{"label": disclosure, "kind": "info"}] + items


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
        {"label": "ℹ Deterministic & fixture-tested when run directly via /library run — "
                  "100 domains share 10 reviewed algorithms, not 30,000 distinct ones", "kind": "info"},
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
    return [r for r in rows if r["kind"] == "info" or _matches(query, r["label"])]


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


