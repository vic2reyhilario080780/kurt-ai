"""
KURT MCP Client — Phase 4
Connect to any MCP server (stdio or HTTP/SSE), list tools, execute tool calls.
Works with: local servers, remote HTTP servers, Composio, Zapier MCP, etc.
"""

import os
import json
import asyncio
import httpx
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
MCP_REGISTRY_PATH = KURT_DIR / "mcp_connections.json"


# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    server_name: str = ""

    def to_tools_prompt_line(self) -> str:
        params = json.dumps(self.input_schema.get("properties", {}), ensure_ascii=False)[:120]
        return f'- **{self.server_name}/{self.name}**: {self.description}\n  Params: {params}'


@dataclass
class MCPConnection:
    name: str
    transport: str          # "stdio" | "http" | "sse"
    # stdio fields
    command: Optional[str] = None
    args: list = field(default_factory=list)
    env: dict = field(default_factory=dict)
    # http/sse fields
    url: Optional[str] = None
    headers: dict = field(default_factory=dict)
    # state
    enabled: bool = True
    description: str = ""


# ─────────────────────────────────────────────────────────────
# Registry (persist connections to ~/.kurt/mcp_connections.json)
# ─────────────────────────────────────────────────────────────

def load_registry() -> dict[str, MCPConnection]:
    """Load saved MCP connections"""
    KURT_DIR.mkdir(exist_ok=True)
    if not MCP_REGISTRY_PATH.exists():
        return {}
    try:
        raw = json.loads(MCP_REGISTRY_PATH.read_text())
        if not isinstance(raw, dict) or not all(isinstance(v, dict) for v in raw.values()):
            raise ValueError("Expected a server configuration map.")
        result = {}
        for name, data in raw.items():
            result[name] = MCPConnection(**{**data, "name": name})
        return result
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid MCP connections file; fix it before adding connections.") from exc


def save_registry(connections: dict[str, MCPConnection]):
    """Save MCP connections"""
    KURT_DIR.mkdir(exist_ok=True)
    raw = {}
    for name, conn in connections.items():
        raw[name] = {
            "name": conn.name,
            "transport": conn.transport,
            "command": conn.command,
            "args": conn.args,
            "env": conn.env,
            "url": conn.url,
            "headers": conn.headers,
            "enabled": conn.enabled,
            "description": conn.description,
        }
    import tempfile
    # Connection configs can hold tokens; preserve the old file until replacement.
    fd, temp_path = tempfile.mkstemp(prefix=".mcp-", dir=KURT_DIR)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(raw, stream, indent=2)
        os.replace(temp_path, MCP_REGISTRY_PATH)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def add_connection(conn: MCPConnection) -> str:
    """Add or update an MCP connection"""
    registry = load_registry()
    registry[conn.name] = conn
    save_registry(registry)
    return f"✅ Saved MCP connection: {conn.name}"


def remove_connection(name: str) -> str:
    """Remove an MCP connection"""
    registry = load_registry()
    if name not in registry:
        return f"❌ Connection not found: {name}"
    del registry[name]
    save_registry(registry)
    return f"✅ Removed MCP connection: {name}"


# ─────────────────────────────────────────────────────────────
# Protocol sessions (official SDK: initialization, SSE, HTTP, stdio)
# ─────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager
from datetime import timedelta


@asynccontextmanager
async def mcp_session(conn: MCPConnection):
    """Own transport and session in one task; always clean up on failure."""
    from contextlib import AsyncExitStack
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamable_http_client

    if not conn.enabled:
        raise ValueError("Connection is disabled.")
    async with AsyncExitStack() as stack:
        if conn.transport == "stdio":
            import tempfile
            # Drain subprocess diagnostics without exposing secrets to the chat.
            errors = stack.enter_context(tempfile.TemporaryFile(mode="w+"))
            streams = await stack.enter_async_context(stdio_client(
                StdioServerParameters(command=conn.command, args=conn.args,
                                      env={**os.environ, **conn.env}), errlog=errors))
        elif conn.transport == "sse":
            streams = await stack.enter_async_context(sse_client(
                conn.url, headers=conn.headers, timeout=15, sse_read_timeout=30))
        elif conn.transport == "http":
            client = await stack.enter_async_context(httpx.AsyncClient(
                headers=conn.headers, timeout=httpx.Timeout(30, connect=15), follow_redirects=True))
            streams = await stack.enter_async_context(streamable_http_client(
                conn.url, http_client=client))
        else:
            raise ValueError("Unsupported MCP transport.")
        session = await stack.enter_async_context(ClientSession(
            streams[0], streams[1], read_timeout_seconds=timedelta(seconds=30)))
        await session.initialize()
        yield session


async def probe_connection(conn: MCPConnection) -> list[MCPTool]:
    """Initialize and list every page of tools, raising on real failures."""
    tools = []
    async with mcp_session(conn) as session:
        cursor = None
        seen = set()
        while True:
            result = await session.list_tools(cursor=cursor)
            tools.extend(MCPTool(name=t.name, description=t.description or "",
                                 input_schema=t.inputSchema, server_name=conn.name)
                         for t in result.tools)
            cursor = result.nextCursor
            if not cursor:
                break
            if cursor in seen:
                raise ValueError("Server repeated its tool pagination cursor.")
            seen.add(cursor)
    return tools


def connection_error(exc: Exception) -> str:
    """Return useful diagnostics without printing credential-bearing URLs."""
    children = getattr(exc, "exceptions", None)
    if children:
        return "; ".join(dict.fromkeys(connection_error(e) for e in children))
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return f"HTTP {code}: access denied; provide the app's API key/access token. Browser OAuth sign-in is not implemented."
        return f"HTTP {code}: server rejected the MCP request."
    if isinstance(exc, FileNotFoundError):
        return "Required executable is missing; install the configured command (such as npx or uvx)."
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return "Connection timed out."
    # Error messages from packages and endpoints can contain secrets.
    return f"{type(exc).__name__}: connection failed; check transport, endpoint and credentials."


async def list_tools(conn: MCPConnection) -> list[MCPTool]:
    try:
        return await probe_connection(conn)
    except Exception as exc:
        console.print(f"❌ {conn.name}: {connection_error(exc)}", markup=False)
        return []


async def call_tool(conn: MCPConnection, tool_name: str, params: dict) -> str:
    try:
        async with mcp_session(conn) as session:
            result = await session.call_tool(tool_name, arguments=params)
            parts = [item.text if hasattr(item, "text") else item.model_dump_json()
                     for item in result.content]
            text = "\n".join(parts)
            if result.structuredContent:
                text += "\n" + json.dumps(result.structuredContent, ensure_ascii=False)
            return ("❌ Tool error: " if result.isError else "") + text
    except Exception as exc:
        return f"❌ MCP error ({conn.name}/{tool_name}): {connection_error(exc)}"


async def list_all_tools() -> dict[str, list[MCPTool]]:
    """List tools from ALL enabled connections"""
    registry = load_registry()
    enabled = {name: conn for name, conn in registry.items() if conn.enabled}
    if not enabled:
        return {}

    results = {}
    tasks = [(name, list_tools(conn)) for name, conn in enabled.items()]
    for name, coro in tasks:
        tools = await coro
        if tools:
            results[name] = tools
    return results


async def execute_mcp_tool(tool_ref: str, params: dict) -> str:
    """
    Execute a tool by reference: "server_name/tool_name" or just "tool_name"
    Searches all enabled connections.
    """
    registry = load_registry()

    # Parse server/tool format
    if "/" in tool_ref:
        server_name, tool_name = tool_ref.split("/", 1)
        if server_name not in registry:
            return f"❌ MCP server not found: {server_name}"
        return await call_tool(registry[server_name], tool_name, params)

    # Search all servers for the tool
    for name, conn in registry.items():
        if not conn.enabled:
            continue
        tools = await list_tools(conn)
        for t in tools:
            if t.name == tool_ref:
                return await call_tool(conn, tool_ref, params)

    return f"❌ Tool not found in any MCP server: {tool_ref}"


# ─────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────

def show_connections():
    """Display all MCP connections in a Rich table"""
    registry = load_registry()
    if not registry:
        console.print("[dim]No MCP connections saved. Use: kurt mcp add[/dim]")
        return

    t = Table(title="🔌 KURT MCP Connections", box=box.ROUNDED)
    t.add_column("Name", style="cyan")
    t.add_column("Transport", style="yellow")
    t.add_column("Target")
    t.add_column("Status")
    t.add_column("Description", style="dim")

    for name, conn in registry.items():
        target = conn.url or (f"{conn.command} {' '.join(conn.args)}" if conn.command else "—")
        status = "[green]✓ enabled[/green]" if conn.enabled else "[dim]disabled[/dim]"
        t.add_row(name, conn.transport, target[:50], status, conn.description[:40])

    console.print(t)


async def show_tools(server_name: Optional[str] = None):
    """Display available tools from connected MCP servers"""
    registry = load_registry()
    if not registry:
        console.print("[dim]No MCP connections. Add one with: kurt mcp add[/dim]")
        return

    to_check = {}
    if server_name:
        if server_name not in registry:
            console.print(f"[red]❌ Server not found: {server_name}[/red]")
            return
        to_check = {server_name: registry[server_name]}
    else:
        to_check = {n: c for n, c in registry.items() if c.enabled}

    total = 0
    for name, conn in to_check.items():
        console.print(f"\n[cyan]🔌 {name}[/cyan] [dim]({conn.transport})[/dim]")
        tools = await list_tools(conn)
        if not tools:
            console.print("  [dim]No tools found or connection failed[/dim]")
            continue
        for t in tools:
            schema_preview = ", ".join(list(t.input_schema.get("properties", {}).keys())[:5])
            console.print(f"  [yellow]•[/yellow] [bold]{t.name}[/bold]  [dim]{t.description[:60]}[/dim]")
            if schema_preview:
                console.print(f"    [dim]params: {schema_preview}[/dim]")
            total += 1

    console.print(f"\n[dim]Total: {total} tools across {len(to_check)} server(s)[/dim]")


# ─────────────────────────────────────────────────────────────
# Quick-add presets for common MCP servers
# ─────────────────────────────────────────────────────────────

PRESETS = {
    "filesystem": MCPConnection(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        description="Local filesystem access",
    ),
    "github": MCPConnection(
        name="github",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
        description="GitHub repos, issues, PRs",
    ),
    "postgres": MCPConnection(
        name="postgres",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres",
              os.environ.get("DATABASE_URL", "postgresql://localhost/mydb")],
        description="PostgreSQL database",
    ),
    "brave-search": MCPConnection(
        name="brave-search",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={"BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY", "")},
        description="Brave web search",
    ),
    "sqlite": MCPConnection(
        name="sqlite",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sqlite", "--db-path", "./data.db"],
        description="SQLite database",
    ),
    "puppeteer": MCPConnection(
        name="puppeteer",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
        description="Browser automation",
    ),
}


def get_preset(name: str) -> Optional[MCPConnection]:
    return PRESETS.get(name.lower())


def list_presets():
    """Show available quick-add presets"""
    t = Table(title="⚡ MCP Quick-Add Presets", box=box.ROUNDED)
    t.add_column("Preset", style="cyan")
    t.add_column("Transport", style="yellow")
    t.add_column("Description")
    t.add_column("Needs")
    for name, conn in PRESETS.items():
        needs = ""
        if conn.env:
            needs = ", ".join(conn.env.keys())
        t.add_row(name, conn.transport, conn.description, needs or "—")
    console.print(t)
    console.print("\n[dim]Usage: kurt mcp add --preset <name>[/dim]")
