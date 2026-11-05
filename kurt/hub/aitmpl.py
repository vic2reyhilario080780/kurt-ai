"""
KURT Hub — aitmpl.com Integration
Fetches skills, agents, MCPs, commands, hooks from aitmpl.com public API
No auth required!
"""

import httpx
import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

AITMPL_BASE = "https://aitmpl.com/api/v1"
KURT_DIR = Path.home() / ".kurt"
CACHE_DIR = KURT_DIR / "cache" / "aitmpl"

COMPONENT_TYPES = ["skills", "agents", "commands", "mcps", "hooks", "settings", "mods"]

TYPE_ICONS = {
    "skills": "🧠",
    "agents": "🤖",
    "commands": "⚡",
    "mcps": "🔌",
    "hooks": "🪝",
    "settings": "⚙️",
    "mods": "🔧",
    "plugins": "🧩",
}


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_catalog(component_type: str = None, use_cache: bool = True) -> list:
    """Fetch catalog from aitmpl.com API"""
    _ensure_cache_dir()

    if component_type:
        url = f"{AITMPL_BASE}/catalog/{component_type}.json"
        cache_file = CACHE_DIR / f"{component_type}.json"
    else:
        url = f"{AITMPL_BASE}/catalog.json"
        cache_file = CACHE_DIR / "catalog.json"

    # Use cache if available (1 hour)
    if use_cache and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 3600:  # 1 hour cache
            with open(cache_file) as f:
                cached = json.load(f)
                return cached if isinstance(cached, list) else []

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            raw = resp.json()
        # API may return a dict with a list inside, or a plain list
        if isinstance(raw, dict):
            # Try common keys: 'data', 'items', 'results', or first list value
            data = raw.get("data") or raw.get("items") or raw.get("results") or []
            if not data:
                for v in raw.values():
                    if isinstance(v, list):
                        data = v
                        break
        else:
            data = raw if isinstance(raw, list) else []

        # Save to cache
        with open(cache_file, "w") as f:
            json.dump(data, f)

        return data

    except Exception as e:
        console.print(f"[red]❌ Error fetching from aitmpl.com: {e}[/red]")
        # Try cache as fallback
        if cache_file.exists():
            console.print("[yellow]Using cached data...[/yellow]")
            with open(cache_file) as f:
                cached = json.load(f)
                return cached if isinstance(cached, list) else []
        return []


def fetch_component_content(component_type: str, category: str, name: str) -> dict:
    """Fetch full content of a specific component"""
    url = f"https://aitmpl.com/component-content/{component_type}/{category}/{name}.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        console.print(f"[red]❌ Error fetching component: {e}[/red]")
        return {}


def get_counts() -> dict:
    """Get component counts from aitmpl.com"""
    try:
        url = f"{AITMPL_BASE}/version.json"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {}


def hub_list(component_type: str = None, category: str = None,
             search: str = None, limit: int = 20, show_all: bool = False):
    """List components from aitmpl.com hub"""

    console.print(f"\n[bold cyan]🌐 KURT Hub — aitmpl.com[/bold cyan]")

    if component_type:
        types_to_fetch = [component_type]
    else:
        types_to_fetch = COMPONENT_TYPES

    for ctype in types_to_fetch:
        icon = TYPE_ICONS.get(ctype, "📦")
        data = fetch_catalog(ctype)

        if not data:
            continue

        # Filter by category
        if category:
            data = [c for c in data if c.get("category", "").lower() == category.lower()]

        # Filter by search
        if search:
            search_lower = search.lower()
            data = [c for c in data if
                    search_lower in c.get("name", "").lower() or
                    search_lower in c.get("description", "").lower() or
                    search_lower in c.get("category", "").lower()]

        if not data:
            continue

        shown = len(data) if show_all else min(limit, len(data))
        total = len(data)
        title_suffix = f"showing all {total}" if show_all else f"showing {shown} of {total} — use --all to see all"
        table = Table(
            title=f"{icon} {ctype.upper()} ({title_suffix})",
            box=box.ROUNDED,
            border_style="cyan",
            show_lines=False,
        )
        table.add_column("Name", style="cyan", width=25)
        table.add_column("Category", style="dim", width=20)
        table.add_column("Description", style="white", width=45)
        table.add_column("Downloads", style="green", width=10)

        display_data = data if show_all else data[:limit]
        for item in display_data:
            downloads = item.get("downloadCount", 0)
            dl_str = f"↓ {downloads:,}" if downloads else "-"
            desc = item.get("description", "")
            table.add_row(
                item.get("name", ""),
                item.get("category", ""),
                (desc[:42] + "...") if len(desc) > 42 else desc,
                dl_str,
            )

        console.print(table)
        console.print(f"[dim]Install: kurt hub install {ctype} <category>/<name>[/dim]\n")


def hub_search(query: str, limit: int = 10):
    """Search across all component types"""
    console.print(f"\n[bold cyan]🔍 Searching hub for: '{query}'[/bold cyan]\n")

    results = []
    for ctype in COMPONENT_TYPES:
        data = fetch_catalog(ctype)
        query_lower = query.lower()
        matches = [
            {**c, "_type": ctype}
            for c in data
            if query_lower in c.get("name", "").lower()
            or query_lower in c.get("description", "").lower()
            or query_lower in c.get("category", "").lower()
        ]
        results.extend(matches)

    if not results:
        console.print(f"[yellow]Walang nahanap para sa '{query}'[/yellow]")
        return

    table = Table(
        title=f"🔍 Search Results: '{query}' ({len(results)} found)",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Type", style="dim", width=10)
    table.add_column("Name", style="cyan", width=25)
    table.add_column("Category", style="dim", width=20)
    table.add_column("Description", style="white", width=45)

    display_results = results if limit == 0 else results[:limit]
    for item in display_results:
        icon = TYPE_ICONS.get(item["_type"], "📦")
        desc = item.get("description", "")
        table.add_row(
            f"{icon} {item['_type']}",
            item.get("name", ""),
            item.get("category", ""),
            (desc[:42] + "...") if len(desc) > 42 else desc,
        )

    console.print(table)
    console.print(f"\n[dim]Install: kurt hub install <type> <category>/<name>[/dim]")


def hub_install(component_type: str, path: str):
    """Install a component from aitmpl.com to KURT"""
    parts = path.split("/")
    if len(parts) != 2:
        console.print("[red]❌ Format: kurt hub install <type> <category>/<name>[/red]")
        return

    category, name = parts
    console.print(f"[cyan]⬇️  Installing {component_type}: {category}/{name}...[/cyan]")

    content = fetch_component_content(component_type, category, name)
    if not content:
        console.print("[red]❌ Component not found![/red]")
        return

    # Save to ~/.kurt/hub/<type>/<category>/<name>.json
    install_dir = KURT_DIR / "hub" / component_type / category
    install_dir.mkdir(parents=True, exist_ok=True)
    install_path = install_dir / f"{name}.json"

    with open(install_path, "w") as f:
        json.dump(content, f, indent=2)

    console.print(f"[green]✅ Installed: {component_type}/{category}/{name}[/green]")
    console.print(f"[dim]Saved to: {install_path}[/dim]")

    # Show content preview
    if "content" in content:
        preview_text = content["content"]
        preview = (preview_text[:200] + "...") if len(preview_text) > 200 else preview_text
        console.print(Panel(
            preview,
            title="📄 Preview",
            box=box.ROUNDED,
            border_style="dim",
        ))


def hub_stats():
    """Show hub statistics"""
    console.print("\n[bold cyan]📊 KURT Hub Statistics[/bold cyan]\n")

    version_data = get_counts()

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Source", style="cyan", width=25)
    table.add_column("Type", style="white", width=15)
    table.add_column("Count", style="green", width=10)
    table.add_column("Status", width=20)

    # aitmpl.com counts
    counts = version_data.get("counts", {})
    for ctype, count in counts.items():
        icon = TYPE_ICONS.get(ctype, "📦")
        table.add_row(
            "aitmpl.com",
            f"{icon} {ctype}",
            str(count),
            "[green]✅ Online[/green]"
        )

    # Other sources
    other_sources = [
        ("Composio", "connectors", "250+", "🔑 Needs API key"),
        ("awesome-mcp-servers", "MCPs", "500+", "✅ Open source"),
        ("LangChain", "tools", "100+", "✅ Open source"),
        ("n8n", "nodes", "400+", "✅ Self-hosted"),
        ("Zapier", "automations", "7,000+", "🔑 Needs API key"),
    ]

    for source, ctype, count, status in other_sources:
        table.add_row(source, ctype, count, f"[dim]{status}[/dim]")

    console.print(table)
    console.print(f"\n[dim]Run [cyan]kurt hub search <query>[/cyan] to find components[/dim]")
