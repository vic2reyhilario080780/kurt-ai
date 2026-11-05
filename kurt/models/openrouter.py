"""
KURT Models — OpenRouter Live Model List
Fetches all 200+ available AI models in real-time
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

KURT_DIR = Path.home() / ".kurt"
CACHE_DIR = KURT_DIR / "cache" / "openrouter"
OPENROUTER_API = "https://openrouter.ai/api/v1/models"
CACHE_TTL = 3600  # 1 hour


def fetch_models(use_cache: bool = True) -> list:
    """Fetch all models from OpenRouter API with 1-hour cache"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "models.json"

    # Check cache
    if use_cache and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL:
            with open(cache_file) as f:
                return json.load(f)

    # Fetch from API
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(OPENROUTER_API)
            data = resp.json()
            models = data.get("data", [])

        # Save cache
        with open(cache_file, "w") as f:
            json.dump(models, f)

        return models

    except Exception as e:
        # Return cached if available
        if cache_file.exists():
            console.print(f"[yellow]⚠️  API error, using cached data: {e}[/yellow]")
            with open(cache_file) as f:
                return json.load(f)
        console.print(f"[red]❌ Failed to fetch models: {e}[/red]")
        return []


def format_price(price_str) -> str:
    """Format price per 1M tokens"""
    try:
        price = float(price_str)
        if price == 0:
            return "[green]FREE[/green]"
        elif price < 0.01:
            return f"[green]${price*1000000:.2f}/1M[/green]"
        elif price < 0.1:
            return f"[yellow]${price*1000000:.2f}/1M[/yellow]"
        else:
            return f"[red]${price*1000000:.2f}/1M[/red]"
    except Exception:
        return "[dim]-[/dim]"


def format_context(ctx) -> str:
    """Format context window"""
    try:
        ctx = int(ctx)
        if ctx >= 1_000_000:
            return f"{ctx // 1_000_000}M"
        elif ctx >= 1000:
            return f"{ctx // 1000}K"
        return str(ctx)
    except Exception:
        return "-"


def models_list(
    search: str = None,
    free_only: bool = False,
    provider: str = None,
    limit: int = 30,
):
    """List all available OpenRouter models"""
    console.print("\n[bold cyan]🤖 OpenRouter — Available AI Models[/bold cyan]")
    console.print("[dim]Source: openrouter.ai | Real-time pricing[/dim]\n")

    models = fetch_models()
    if not models:
        console.print("[red]❌ Walang models na nakuha.[/red]")
        return

    # Filter
    filtered = []
    for m in models:
        mid = m.get("id", "")
        name = m.get("name", "")
        pricing = m.get("pricing", {})
        prompt_price = float(pricing.get("prompt", 0))

        if free_only and prompt_price != 0:
            continue
        if search and search.lower() not in mid.lower() and search.lower() not in name.lower():
            continue
        if provider and provider.lower() not in mid.lower():
            continue

        filtered.append(m)

    # Sort: free first, then by name
    filtered.sort(key=lambda m: (
        float(m.get("pricing", {}).get("prompt", 0)) > 0,
        m.get("id", "")
    ))

    free_count = sum(1 for m in filtered if float(m.get("pricing", {}).get("prompt", 0)) == 0)

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=False,
        title=f"{'🆓 Free Models' if free_only else 'All Models'} ({len(filtered)} shown, {free_count} free)",
    )
    table.add_column("Model ID", style="cyan", width=38)
    table.add_column("Name", style="white", width=28)
    table.add_column("Context", style="dim", width=8, justify="right")
    table.add_column("Input/1M", width=14, justify="right")
    table.add_column("Output/1M", width=14, justify="right")

    for m in filtered[:limit]:
        pricing = m.get("pricing", {})
        ctx = m.get("context_length", 0)
        table.add_row(
            m.get("id", ""),
            (m.get("name", "")[:26] + "..") if len(m.get("name", "")) > 28 else m.get("name", ""),
            format_context(ctx),
            format_price(pricing.get("prompt", 0)),
            format_price(pricing.get("completion", 0)),
        )

    console.print(table)

    if len(filtered) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(filtered)} models. Use --limit N para makita lahat.[/dim]")

    console.print(f"\n[dim]💡 Tips:[/dim]")
    console.print(f"[dim]  kurt models --free        — libre lang[/dim]")
    console.print(f"[dim]  kurt models --search gpt  — search by name[/dim]")
    console.print(f"[dim]  kurt models --provider anthropic[/dim]")
    console.print(f"[dim]  kurt models --limit 100   — show more[/dim]")
    console.print()


def models_free():
    """Show only free models"""
    models_list(free_only=True, limit=50)


def models_stats():
    """Show model statistics"""
    models = fetch_models()
    if not models:
        return

    total = len(models)
    free = sum(1 for m in models if float(m.get("pricing", {}).get("prompt", 0)) == 0)

    # Count by provider
    providers = {}
    for m in models:
        mid = m.get("id", "")
        prov = mid.split("/")[0] if "/" in mid else "unknown"
        providers[prov] = providers.get(prov, 0) + 1

    top_providers = sorted(providers.items(), key=lambda x: x[1], reverse=True)[:10]

    console.print(Panel.fit(
        f"[bold cyan]📊 OpenRouter Model Stats[/bold cyan]\n\n"
        f"[white]Total models:[/white] [cyan]{total}[/cyan]\n"
        f"[white]Free models:[/white]  [green]{free}[/green]\n"
        f"[white]Paid models:[/white]  [yellow]{total - free}[/yellow]",
        box=box.ROUNDED,
        border_style="cyan",
    ))

    table = Table(title="Top Providers", box=box.SIMPLE, border_style="dim")
    table.add_column("Provider", style="cyan", width=20)
    table.add_column("Models", style="white", width=8, justify="right")

    for prov, count in top_providers:
        table.add_row(prov, str(count))

    console.print(table)
