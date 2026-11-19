"""
KURT Models — fal.ai Live Model List
Fetches the complete available generative-media catalog.
"""

import json
import os
import time
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from kurt.models.catalog import read_cache, write_cache, validate_models

console = Console()

KURT_DIR = Path.home() / ".kurt"
CACHE_DIR = KURT_DIR / "cache" / "fal"
FAL_MODELS_API = "https://fal.ai/api/models"
CACHE_TTL = 3600  # 1 hour
PAGE_SIZE = 40  # server-capped — larger `size` values are ignored


def fetch_models(use_cache: bool = True) -> list:
    """Fetch all fal.ai models (paginated) with 1-hour cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "models.json"

    cached = read_cache(cache_file)
    if use_cache and cached is not None and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL:
            return cached

    key = os.getenv("FAL_API_KEY") or os.getenv("FAL_KEY", "")
    if not key:
        console.print("[red]❌ No FAL_API_KEY configured — run `kurt setup`.[/red]")
        return cached or []

    headers = {"Authorization": f"Key {key}"}
    models = []
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(FAL_MODELS_API, headers=headers, params={"page": 1})
            response.raise_for_status()
            first = response.json()
            total_pages, total = first.get('pages'), first.get('total')
            if (first.get('page') != 1 or type(total_pages) is not int or not 1 <= total_pages <= 10000 or
                    type(total) is not int or total < 0):
                raise ValueError('Invalid fal.ai pagination metadata.')
            models.extend(validate_models(first.get('items')))
            for page in range(2, total_pages + 1):
                resp = client.get(FAL_MODELS_API, headers=headers, params={"page": page})
                resp.raise_for_status()
                data = resp.json()
                if data.get('page') != page or data.get('pages') != total_pages or data.get('total') != total:
                    raise ValueError('fal.ai catalog changed during pagination; retry refresh.')
                models.extend(validate_models(data.get('items')))
        models = validate_models(models)
        if len(models) != total:
            raise ValueError('Incomplete fal.ai catalog; keeping previous cache.')
        write_cache(cache_file, models)
        return models

    except Exception as e:
        if cached is not None:
            console.print(f"[yellow]⚠️  API error, using cached data: {e}[/yellow]")
            return cached
        console.print(f"[red]❌ Failed to fetch fal.ai models: {e}[/red]")
        return []


def models_list(
    search: str = None,
    category: str = None,
    limit: int = 30,
):
    """List available fal.ai models."""
    console.print("\n[bold cyan]🎨 fal.ai — Available Generative Models[/bold cyan]")
    console.print("[dim]Source: fal.ai | Image, video, audio, speech, LLM — paid, deducts from your fal.ai top-up[/dim]\n")

    models = fetch_models()
    if not models:
        console.print("[red]❌ Walang models na nakuha.[/red]")
        return

    filtered = []
    for m in models:
        mid = m.get("id", "")
        title = m.get("title", "")
        cat = m.get("category", "")

        if category and category.lower() != cat.lower():
            continue
        if search and search.lower() not in mid.lower() and search.lower() not in title.lower():
            continue

        filtered.append(m)

    filtered.sort(key=lambda m: m.get("id", ""))
    categories = sorted({m.get("category", "") for m in filtered if m.get("category")})

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=False,
        title=f"fal.ai Models ({min(len(filtered), limit)} shown; {len(filtered)} matches / {len(models)} total)",
    )
    table.add_column("Model ID", style="cyan", width=40)
    table.add_column("Title", style="white", width=26)
    table.add_column("Category", style="dim", width=16)

    for m in filtered[:limit]:
        table.add_row(
            m.get("id", ""),
            (m.get("title", "")[:24] + "..") if len(m.get("title", "")) > 26 else m.get("title", ""),
            m.get("category", "-"),
        )

    console.print(table)

    if len(filtered) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(filtered)} models. Use --limit N para makita lahat.[/dim]")

    console.print(f"\n[dim]Categories: {', '.join(categories[:8])}{'…' if len(categories) > 8 else ''}[/dim]")
    console.print(f"\n[dim]💡 Tips:[/dim]")
    console.print(f"[dim]  kurt models fal --category text-to-image[/dim]")
    console.print(f"[dim]  kurt models fal --search flux[/dim]")
    console.print(f"[dim]  kurt models fal --limit 100   — show more[/dim]")
    console.print('[dim]  Browse all categories in chat: /models → fal.ai → All models[/dim]')
    console.print('[dim]  Use /image-model or /video-model for supported defaults; other workflows may need a dedicated adapter.[/dim]')
    console.print()


def models_stats():
    """Show fal.ai model statistics."""
    models = fetch_models()
    if not models:
        return

    total = len(models)
    categories = {}
    for m in models:
        cat = m.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)

    console.print(Panel.fit(
        f"[bold cyan]📊 fal.ai Model Stats[/bold cyan]\n\n"
        f"[white]Total models:[/white] [cyan]{total}[/cyan]\n"
        f"[white]All paid[/white] — billed to your fal.ai account top-up, no separate Kurt charge",
        box=box.ROUNDED,
        border_style="cyan",
    ))

    table = Table(title="By Category", box=box.SIMPLE, border_style="dim")
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Models", style="white", width=8, justify="right")

    for cat, count in top_categories:
        table.add_row(cat, str(count))

    console.print(table)
