"""
KURT Plugins Manager - Feature packs na nagdadagdag ng capability
"""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
PLUGINS_DIR = KURT_DIR / "plugins"


BUILTIN_PLUGINS = {
    "web-search": {
        "name": "Web Search",
        "description": "Real-time web search via multiple engines",
        "version": "1.0.0",
        "capabilities": ["search", "fetch_url"],
        "enabled": True,
    },
    "code-runner": {
        "name": "Code Runner",
        "description": "Execute Python, JS, Bash code sa terminal",
        "version": "1.0.0",
        "capabilities": ["execute_python", "execute_bash", "execute_js"],
        "enabled": True,
    },
    "file-manager": {
        "name": "File Manager",
        "description": "Read, write, search files sa local system",
        "version": "1.0.0",
        "capabilities": ["read_file", "write_file", "search_files", "list_dir"],
        "enabled": True,
    },
    "image-viewer": {
        "name": "Image Viewer",
        "description": "Display at analyze images",
        "version": "1.0.0",
        "capabilities": ["view_image", "analyze_image"],
        "enabled": True,
    },
    "pdf-reader": {
        "name": "PDF Reader",
        "description": "Extract text mula sa PDF files",
        "version": "1.0.0",
        "capabilities": ["read_pdf", "extract_text"],
        "enabled": False,
    },
    "web-scraper": {
        "name": "Web Scraper",
        "description": "Scrape data mula sa websites",
        "version": "1.0.0",
        "capabilities": ["scrape_url", "extract_data"],
        "enabled": False,
    },
    "voice": {
        "name": "Voice I/O",
        "description": "Text-to-speech at speech-to-text",
        "version": "1.0.0",
        "capabilities": ["tts", "stt"],
        "enabled": False,
    },
    "shopee": {
        "name": "Shopee PH",
        "description": "Shopee seller center integration",
        "version": "1.0.0",
        "capabilities": ["get_orders", "update_price", "manage_products"],
        "enabled": False,
        "requires_config": ["SHOPEE_SHOP_ID", "SHOPEE_API_KEY"],
    },
    "lazada": {
        "name": "Lazada PH",
        "description": "Lazada seller center integration",
        "version": "1.0.0",
        "capabilities": ["get_orders", "update_listing", "check_inventory"],
        "enabled": False,
        "requires_config": ["LAZADA_APP_KEY", "LAZADA_APP_SECRET"],
    },
}


def init_plugins():
    """Initialize plugins directory"""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    for plugin_id, plugin_data in BUILTIN_PLUGINS.items():
        plugin_file = PLUGINS_DIR / f"{plugin_id}.json"
        if not plugin_file.exists():
            with open(plugin_file, "w") as f:
                json.dump({**plugin_data, "id": plugin_id, "builtin": True}, f, indent=2)


def list_plugins():
    """List all plugins"""
    init_plugins()

    table = Table(
        title="🔌 KURT Plugins",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("ID", style="cyan", width=15)
    table.add_column("Name", style="white", width=20)
    table.add_column("Description", style="dim", width=35)
    table.add_column("Status", style="yellow", width=10)
    table.add_column("Type", style="dim", width=10)

    for plugin_file in sorted(PLUGINS_DIR.glob("*.json")):
        with open(plugin_file) as f:
            plugin = json.load(f)

        status = "[green]✅ ON[/green]" if plugin.get("enabled") else "[red]⭕ OFF[/red]"
        ptype = "[green]Built-in[/green]" if plugin.get("builtin") else "[blue]Custom[/blue]"

        table.add_row(
            plugin["id"],
            plugin["name"],
            plugin["description"],
            status,
            ptype,
        )

    console.print(table)
    from kurt.capabilities.runtime import manifest
    console.print(f"[dim]Also available: {manifest()['counts']['plugin']:,} executable native plugins. Browse: kurt library search <words> --kind plugin[/dim]")
    console.print("[dim]Enable: kurt plugin enable <id>[/dim]")
    console.print("[dim]Disable: kurt plugin disable <id>[/dim]")


def enable_plugin(plugin_id: str):
    """Enable a plugin"""
    if plugin_id.startswith("kurt-plugin--"):
        from kurt.capabilities.runtime import set_enabled
        set_enabled(plugin_id, True)
        console.print(f"Enabled native plugin: {plugin_id}", markup=False)
        return
    init_plugins()
    plugin_file = PLUGINS_DIR / f"{plugin_id}.json"

    if not plugin_file.exists():
        console.print(f"[red]❌ Plugin not found: {plugin_id}[/red]")
        return

    with open(plugin_file) as f:
        plugin = json.load(f)

    # Check if requires config
    if "requires_config" in plugin:
        import os
        missing = [k for k in plugin["requires_config"] if not os.getenv(k)]
        if missing:
            console.print(f"[yellow]⚠️  Requires config keys: {', '.join(missing)}[/yellow]")
            console.print("[dim]Add them to ~/.kurt/.env[/dim]")

    plugin["enabled"] = True
    with open(plugin_file, "w") as f:
        json.dump(plugin, f, indent=2)

    console.print(f"[green]✅ Plugin enabled: {plugin['name']}[/green]")


def disable_plugin(plugin_id: str):
    """Disable a plugin"""
    if plugin_id.startswith("kurt-plugin--"):
        from kurt.capabilities.runtime import set_enabled
        set_enabled(plugin_id, False)
        console.print(f"Disabled native plugin: {plugin_id}", markup=False)
        return
    init_plugins()
    plugin_file = PLUGINS_DIR / f"{plugin_id}.json"

    if not plugin_file.exists():
        console.print(f"[red]❌ Plugin not found: {plugin_id}[/red]")
        return

    with open(plugin_file) as f:
        plugin = json.load(f)

    plugin["enabled"] = False
    with open(plugin_file, "w") as f:
        json.dump(plugin, f, indent=2)

    console.print(f"[yellow]Plugin disabled: {plugin['name']}[/yellow]")


def get_enabled_plugins() -> list:
    """Get list of enabled plugins"""
    init_plugins()
    enabled = []

    for plugin_file in PLUGINS_DIR.glob("*.json"):
        with open(plugin_file) as f:
            plugin = json.load(f)
        if plugin.get("enabled"):
            enabled.append(plugin)

    return enabled
