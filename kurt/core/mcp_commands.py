"""MCP catalog/import commands, shared by the terminal and chat."""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from kurt.core import mcp_catalog as catalog

console = Console()


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


_PLACEHOLDER = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def _recipe_missing_fields(recipe: dict) -> list[str]:
    """Field names this recipe still needs before it can connect: either an
    unresolved catalog placeholder (${NAME}) or a preset default that fell
    back to "" because its environment variable isn't set."""
    names = []
    for mapping_key in ("env", "headers"):
        for key, value in recipe.get(mapping_key, {}).items():
            if (value == "" or _PLACEHOLDER.match(str(value))) and key not in names:
                names.append(key)
    for value in recipe.get("args", []):
        m = _PLACEHOLDER.match(str(value))
        if m and m.group(1) not in names:
            names.append(m.group(1))
    return names


def _fill_recipe(recipe: dict, values: dict) -> dict:
    def resolve(key, value):
        if not (value == "" or _PLACEHOLDER.match(str(value))):
            return value
        resolved = values.get(key, value)
        # Users naturally paste the bare token, not the HTTP scheme prefix
        # — add it back for them rather than making "Bearer " part of what
        # they have to remember to type into an "Authorization" prompt.
        if key == "Authorization" and resolved and not resolved.lower().startswith(("bearer ", "basic ", "token ")):
            resolved = f"Bearer {resolved}"
        return resolved

    filled = dict(recipe)
    for mapping_key in ("env", "headers"):
        if mapping_key in recipe:
            filled[mapping_key] = {k: resolve(k, v) for k, v in recipe[mapping_key].items()}
    if "args" in recipe:
        filled["args"] = [
            (values.get(m.group(1), a) if (m := _PLACEHOLDER.match(str(a))) else a)
            for a in recipe["args"]
        ]
    return filled


def _save_and_report(conn, name: str):
    from kurt.core.mcp_client import add_connection, probe_connection, connection_error
    try:
        tools = asyncio.run(probe_connection(conn))
    except Exception as exc:
        add_connection(conn)
        console.print(f"[yellow]⚠️  Saved {name}, but a test call failed:[/yellow] {connection_error(exc)}")
        return
    add_connection(conn)
    console.print(Panel(
        f"[green]✅ Connected: {name} — {len(tools)} tools available.[/green]",
        box=box.ROUNDED, border_style="green",
    ))


# Presets authenticate against a fixed, well-known service (not a
# catalog listing with its own website/repository field), so the
# "where do I get this key" link has to be hardcoded per preset instead.
_PRESET_KEY_URLS = {
    "github": "https://github.com/settings/tokens",
    "brave-search": "https://api.search.brave.com/app/keys",
}


def connect_entry(ref: str):
    """One unified 'Connect <App>' flow for anything in kurt's MCP list —
    a quick preset (github, postgres...) or one of the 58K+ public catalog
    entries. Tries the server's OWN OAuth sign-in first — Dynamic Client
    Registration + PKCE, discovered live, no third-party connector
    platform in between — mirroring how Claude's built-in MCP connectors
    authorize: pick one, approve in the browser, done. Only when a server
    publishes no OAuth of its own does this fall back to asking, right
    here, for the couple of fields it actually needs — never a raw JSON
    template to hand-edit."""
    from kurt.core import mcp_oauth
    from kurt.core.mcp_client import MCPConnection, PRESETS

    preset = PRESETS.get(ref.lower())
    if preset is not None:
        name = ref.lower()
        description = preset.description
        key_url = _PRESET_KEY_URLS.get(name, "")
        if preset.transport == "stdio":
            recipes = [{"type": "stdio", "command": preset.command, "args": list(preset.args), "env": dict(preset.env)}]
        else:
            recipes = [{"type": preset.transport, "url": preset.url, "headers": dict(preset.headers)}]
    else:
        entry = next((e for e in catalog.load_catalog()["entries"] if e["id"] == ref), None)
        if entry is None:
            console.print(f"[red]❌ Unknown server:[/red] {ref}  [dim](not a preset or catalog ID — try: kurt mcp search)[/dim]")
            return
        name = entry["id"].split("/", 1)[-1]
        description = entry.get("description", "")
        key_url = entry.get("website") or entry.get("repository") or ""
        recipes = entry["configs"]

    if not recipes:
        console.print(f"[yellow]⚠️  {name} has no published connection recipe yet.[/yellow]")
        return

    remote = next((c for c in recipes if c.get("type") in ("http", "sse", "streamable-http")), None)

    if remote:
        console.print(f"[cyan]🔎 Checking how {name} signs in…[/cyan]")
        try:
            with console.status(f"[cyan]Waiting for you to finish authorizing {name} in the browser…[/cyan]"):
                tokens = mcp_oauth.authorize(remote["url"])
            headers = dict(remote.get("headers", {}))
            headers["Authorization"] = f"Bearer {tokens['access_token']}"
            conn = MCPConnection(name=name, transport={"streamable-http": "http"}.get(remote["type"], remote["type"]),
                                 url=remote["url"], headers=headers, description=description)
            _save_and_report(conn, name)
            return
        except mcp_oauth.NotOAuthProtected:
            pass  # no OAuth of its own — fall through to the guided manual connect below
        except RuntimeError as exc:
            console.print(f"[red]❌ Authorization failed:[/red] {exc}")
            return

    recipe = remote or recipes[0]
    missing = _recipe_missing_fields(recipe)
    values = {}
    if missing:
        key_line = f"\n\nGet one here: [link={key_url}]{key_url}[/link]" if key_url else ""
        if not sys.stdin.isatty():
            console.print(Panel(
                f"[bold]{name}[/bold]\n{description}\n\n"
                f"Needs: {', '.join(missing)}{key_line}\n\n"
                f"Run this from a real terminal to be prompted for them, "
                f"or export them as environment variables first.",
                title="🔌 Connect", box=box.ROUNDED, border_style="yellow",
            ))
            return
        from rich.prompt import Prompt
        console.print(Panel(f"[bold]{name}[/bold]\n{description}{key_line}",
                            title="🔌 Connect", box=box.ROUNDED, border_style="cyan"))
        for field in missing:
            values[field] = Prompt.ask(f"  {field}", password=True)

    filled = _fill_recipe(recipe, values)
    transport = {"streamable-http": "http"}.get(filled.get("type"), filled.get("type", "stdio"))
    conn = MCPConnection(
        name=name, transport=transport,
        command=filled.get("command"), args=filled.get("args", []), env=filled.get("env", {}),
        url=filled.get("url"), headers=filled.get("headers", {}), description=description,
    )
    _save_and_report(conn, name)


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

    @app.command("authorize", rich_help_panel="🔍 Discovery (browse what's out there)")
    def authorize(ref: str = typer.Argument(..., help="A preset name (github, postgres...) or a catalog server ID")):
        """Connect a preset or catalog entry — tries the server's own OAuth sign-in first (opens your browser), and only prompts you for a manual API key when the server has none.

        Halimbawa (example): kurt mcp authorize github
        """
        connect_entry(ref)

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
