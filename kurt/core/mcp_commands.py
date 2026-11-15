"""MCP catalog/import commands, shared by the terminal and chat."""

import asyncio
import json
import os
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


_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}|\{([A-Za-z_][A-Za-z0-9_.-]*)\}|<([A-Za-z_][A-Za-z0-9_ -]*)>")


def _recipe_missing_fields(recipe: dict) -> list[str]:
    names = []
    def inspect(key, value):
        fields = [next(g for g in m.groups() if g) for m in _PLACEHOLDER.finditer(str(value))]
        if value == "":
            fields = [key]
        for field in fields:
            if field not in names:
                names.append(field)
    for mapping_key in ("env", "headers"):
        for key, value in recipe.get(mapping_key, {}).items():
            inspect(key, value)
    for value in recipe.get("args", []):
        inspect("ARGUMENT", value)
    for key in ("url", "command"):
        if recipe.get(key):
            inspect(key, recipe[key])
    return names


def _fill_recipe(recipe: dict, values: dict) -> dict:
    def resolve(key, value):
        resolved = values.get(key, value) if value == "" else _PLACEHOLDER.sub(
            lambda m: values.get(next(g for g in m.groups() if g), m[0]), str(value))
        if key.lower() == "authorization" and resolved and not _PLACEHOLDER.search(resolved) and not resolved.lower().startswith(("bearer ", "basic ", "token ")):
            resolved = f"Bearer {resolved}"
        return resolved
    filled = dict(recipe)
    for mapping_key in ("env", "headers"):
        if mapping_key in recipe:
            filled[mapping_key] = {k: resolve(k, v) for k, v in recipe[mapping_key].items()}
    if "args" in recipe:
        filled["args"] = [resolve("", a) for a in recipe["args"]]
    for key in ("url", "command"):
        if key in recipe:
            filled[key] = resolve(key, recipe[key])
    return filled


def _show_setup_pages(pages, open_browser=False):
    from kurt.core.connector_pages import open_page
    opened = set()
    for label, url in pages.items():
        console.print(f"{label}: {url}", markup=False)
        if open_browser and url not in opened:
            console.print(open_page(url), markup=False)
            opened.add(url)


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


def connect_platform(provider: str):
    """Attach the user's Zapier/n8n MCP endpoint, without hand-editing JSON."""
    from kurt.core.connector_pages import PLATFORM_PAGES
    from rich.prompt import Prompt

    if provider not in ("zapier", "n8n"):
        console.print("Choose zapier or n8n.")
        return
    instructions = (
        "Create a server, add the app actions you want, then copy the server URL from Connect."
        if provider == "zapier" else
        "In your n8n instance, enable MCP access in Settings, expose the workflows you want, "
        "then copy the MCP server URL and access token from its connection settings."
    )
    console.print(instructions)
    _show_setup_pages(PLATFORM_PAGES[provider], open_browser=sys.stdin.isatty())
    if not sys.stdin.isatty():
        console.print(f"Continue in a terminal: /mcp platform {provider}")
        return
    try:
        # Zapier server URLs may contain credentials: never echo them in chat.
        url = Prompt.ask("MCP server URL (Ctrl-C to cancel)", password=True).strip()
        catalog.parse_config(url, name=provider)  # validate before contacting it
        token = Prompt.ask("Access token (blank if included in URL / using OAuth)", password=True, default="").strip()
        headers = {}
        if token:
            headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        else:
            from kurt.core import mcp_oauth
            try:
                tokens = mcp_oauth.authorize(url)
                headers["Authorization"] = f"Bearer {tokens['access_token']}"
            except mcp_oauth.NotOAuthProtected:
                pass
        conn = catalog.parse_config(json.dumps({provider: {"url": url, "headers": headers}}))[0]
        _save_and_report(conn, provider)
    except (KeyboardInterrupt, EOFError):
        console.print("Connection cancelled; nothing saved.")
    except (ValueError, RuntimeError):
        console.print("Connection setup failed. Check the MCP URL, credentials and provider setup instructions.")



def connect_entry(ref: str, variant: int | None = None):
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
    from kurt.core.connector_pages import connector_pages
    from kurt.core.mcp_client import PRESETS

    preset = PRESETS.get(ref.lower())
    if preset is not None:
        name = ref.lower()
        description = preset.description
        pages = connector_pages("mcp", name)
        if preset.transport == "stdio":
            recipes = [{"type": "stdio", "command": preset.command, "args": list(preset.args), "env": dict(preset.env)}]
        else:
            recipes = [{"type": preset.transport, "url": preset.url, "headers": dict(preset.headers)}]
            if name == "github" and os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
                recipes[0]["headers"]["Authorization"] = f"Bearer {os.environ['GITHUB_PERSONAL_ACCESS_TOKEN']}"
    else:
        entry = next((e for e in catalog.load_catalog()["entries"] if e["id"] == ref), None)
        if entry is None:
            console.print(f"[red]❌ Unknown server:[/red] {ref}  [dim](not a preset or catalog ID — try: kurt mcp search)[/dim]")
            return
        name = entry["id"]
        description = entry.get("description", "")
        pages = connector_pages("mcp", ref, entry)
        recipes = entry["configs"]

    if not recipes:
        console.print(f"[yellow]⚠️  {name} has no published connection recipe yet.[/yellow]")
        _show_setup_pages(pages, open_browser=sys.stdin.isatty())
        return

    if variant is not None:
        if variant < 0 or variant >= len(recipes):
            console.print("Unknown connection option.")
            return
        recipes = [recipes[variant]]
    # Respect credentials exported after the module/presets were first loaded.
    recipes = [_fill_recipe(c, {field: os.environ[field] for field in _recipe_missing_fields(c)
                               if os.environ.get(field)}) for c in recipes]
    remote = next((c for c in recipes if c.get("type") in ("http", "sse", "streamable-http")), None)

    has_credentials = remote and any(v and not catalog._has_placeholders(v)
        for k, v in remote.get("headers", {}).items() if k.lower() not in ("accept", "content-type"))
    if remote and not has_credentials and not catalog._has_placeholders(remote["url"]):
        console.print(f"[cyan]🔎 Checking how {name} signs in…[/cyan]")
        try:
            with console.status(f"[cyan]Waiting for you to finish authorizing {name} in the browser…[/cyan]"):
                tokens = mcp_oauth.authorize(remote["url"])
            remote = {**remote, "headers": {**remote.get("headers", {}),
                                           "Authorization": f"Bearer {tokens['access_token']}"}}
        except mcp_oauth.NotOAuthProtected:
            pass  # no OAuth of its own — fall through to the guided manual connect below
        except (RuntimeError, OSError) as exc:
            console.print(f"Authorization failed: {type(exc).__name__}. Check the publisher's setup instructions.")
            _show_setup_pages(pages)
            return
        except (KeyboardInterrupt, EOFError):
            console.print("Connection cancelled; nothing saved.")
            return

    recipe = remote or recipes[0]
    missing = _recipe_missing_fields(recipe)
    values = {}
    if missing:
        key_line = "\n\n" + "\n".join(f"{label}: {url}" for label, url in pages.items()) if pages else "\n\nNo setup website was published; consult the server publisher."
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
        _show_setup_pages(pages, open_browser=True)
        console.print("Paste the requested values below. Ctrl-C cancels without saving.")
        try:
            for field in missing:
                value = ""
                while not value.strip():
                    value = Prompt.ask(f"  {field}", password=True)
                values[field] = value.strip()
        except (KeyboardInterrupt, EOFError):
            console.print("Connection cancelled; nothing saved.")
            return

    filled = _fill_recipe(recipe, values)
    try:
        conn = catalog.parse_config(json.dumps({name: {**filled, "description": description}}))[0]
    except ValueError as exc:
        console.print(f"Cannot connect: {exc}", markup=False)
        return
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

    @app.command("platform", rich_help_panel="🔍 Discovery (browse what's out there)")
    def platform(provider: str):
        """Connect your own Zapier or n8n MCP endpoint with guided prompts."""
        connect_platform(provider)

    @app.command("authorize", rich_help_panel="🔍 Discovery (browse what's out there)")
    def authorize(ref: str = typer.Argument(..., help="A preset name or catalog server ID"),
                  variant: Optional[int] = typer.Option(None, min=0)):
        """Connect a preset or catalog entry — tries the server's own OAuth sign-in first (opens your browser), and only prompts you for a manual API key when the server has none.

        Halimbawa (example): kurt mcp authorize github
        """
        connect_entry(ref, variant=variant)

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
