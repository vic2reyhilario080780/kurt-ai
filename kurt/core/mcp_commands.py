"""MCP catalog/import commands, shared by the terminal and chat."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from kurt.core import mcp_catalog as catalog


def catalog_summary():
    data = catalog.load_catalog()
    entries = data["entries"]
    return (f"{len(entries):,} distinct MCP server entries; "
            f"{sum(bool(e['configs']) for e in entries):,} with supported config recipes.\n"
            f"Fetched: {data.get('fetched_at', 'not synced')}\n"
            f"Source: {data['source']}\n"
            "Listings are not verified live connections or unique apps. "
            "Some require API keys, OAuth access tokens or local runtimes.")


async def test_names(names):
    from kurt.core.mcp_client import load_registry, probe_connection, connection_error
    registry = load_registry()
    lines = []
    failed = False
    for name in names:
        try:
            tools = await probe_connection(registry[name])
            lines.append(f"Connected: {name} — {len(tools)} tools")
        except Exception as exc:
            failed = True
            lines.append(f"Saved, but connection failed: {name} — {connection_error(exc)}")
    return "\n".join(lines), failed


def read_config(source):
    if source == "-":
        return sys.stdin.read()
    if source.strip().startswith(("{", "http://", "https://")):
        return source
    return Path(source).expanduser().read_text()


def chat_command(subcommand, value):
    """Return text for discovery or paste-and-connect in kurt chat."""
    if subcommand == "catalog":
        return catalog_summary()
    if subcommand == "search":
        rows = catalog.search_catalog(value)
        return "\n".join(f"{e['id']} | {e['description'][:110]} | configs: {len(e['configs'])}"
                         for e in rows) or "No matching servers. Try: /mcp search github"
    if subcommand == "config":
        return json.dumps(catalog.export_config(value), indent=2)
    if subcommand in ("connect", "import"):
        names = catalog.import_config(value)
        if subcommand == "connect":
            return asyncio.run(test_names(names))[0]
        return "Saved: " + ", ".join(names) + ". Test with: kurt mcp test <name>"
    raise ValueError("Unknown catalog command.")


def register_commands(app, console):
    @app.command("catalog", rich_help_panel="🔍 Discovery (browse what's out there)")
    def summary():
        """Show how big the bundled public MCP catalog is and where it came from.

        Halimbawa (example): kurt mcp catalog
        """
        console.print(catalog_summary(), markup=False)

    @app.command("search", rich_help_panel="🔍 Discovery (browse what's out there)")
    def search(query: str = typer.Argument(""), limit: int = typer.Option(20, min=1, max=10000)):
        """Search the bundled public MCP catalog offline (no internet needed).

        Halimbawa (example): kurt mcp search github
        """
        rows = catalog.search_catalog(query, limit)
        table = Table(title=f"MCP catalog — {len(rows)} results (limit {limit})")
        table.add_column("Server ID", no_wrap=False)
        table.add_column("Description")
        table.add_column("Configs")
        from rich.text import Text
        for e in rows:
            table.add_row(Text(e["id"]), Text(e["description"][:150]), str(len(e["configs"])))
        console.print(table)
        console.print("Copy config: kurt mcp config <server-id>\nListings are untested; credentials may be required.")

    @app.command("info", rich_help_panel="🔍 Discovery (browse what's out there)")
    def info(server_id: str):
        """Show full setup details for one catalog entry (find the ID with 'kurt mcp search').

        Halimbawa (example): kurt mcp info github
        """
        entry = next((e for e in catalog.load_catalog()["entries"] if e["id"] == server_id), None)
        if not entry:
            raise typer.BadParameter("Unknown server ID. Use kurt mcp search.")
        print(json.dumps(entry, indent=2, ensure_ascii=False))

    @app.command("config", rich_help_panel="🔍 Discovery (browse what's out there)")
    def config(server_id: str, variant: int = typer.Option(0, min=0),
               output: Optional[Path] = typer.Option(None, "--output", "-o")):
        """Export a ready-to-fill-in connection config for a catalog entry (you'll still need to add your own API key/credentials before it works).

        Halimbawa (example): kurt mcp config github
        """
        try:
            text = json.dumps(catalog.export_config(server_id, variant), indent=2)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if output:
            output.write_text(text + "\n")
        else:
            print(text)

    def save(source, name, replace, test):
        from kurt.utils.env_loader import load_env
        load_env()
        try:
            names = catalog.import_config(read_config(source), name, replace)
        except (OSError, ValueError) as exc:
            # JSON parser errors don't contain credential values.
            raise typer.BadParameter(str(exc)) from exc
        if test:
            text, failed = asyncio.run(test_names(names))
            console.print(text, markup=False)
            if failed:
                raise typer.Exit(1)
        else:
            console.print("Saved: " + ", ".join(names), markup=False)

    @app.command("import", rich_help_panel="🔍 Discovery (browse what's out there)")
    def import_cmd(source: str = typer.Argument(..., help="JSON file, JSON text, URL, or - for stdin"),
                   name: Optional[str] = typer.Option(None), replace: bool = typer.Option(False),
                   test: bool = typer.Option(False, help="Also initialize connections and list tools")):
        """Save an existing MCP config (from another tool's settings) into Kurt, without connecting yet.

        Halimbawa (example): kurt mcp import my-config.json
        """
        save(source, name, replace, test)

    @app.command("connect", rich_help_panel="🔍 Discovery (browse what's out there)")
    def connect(source: str = typer.Argument(..., help="JSON file, JSON text, URL, or - for stdin"),
                name: Optional[str] = typer.Option(None), replace: bool = typer.Option(False)):
        """Save an MCP config AND test the connection right away (unlike 'import', which saves only).

        Halimbawa (example): kurt mcp connect my-config.json
        """
        save(source, name, replace, True)

    @app.command("sync", rich_help_panel="🔍 Discovery (browse what's out there)")
    def sync():
        """Refresh Kurt's local copy of the public MCP catalog (doesn't connect to anything).

        Halimbawa (example): kurt mcp sync
        """
        with console.status("Downloading official MCP registry…"):
            data = catalog.sync_catalog()
        console.print(f"Saved {data['count']:,} distinct server entries.")
