"""
KURT MCP Client — Phase 4
Connect to any MCP server (stdio or HTTP/SSE), list tools, execute tool calls.
Works with: local servers, remote HTTP servers, Composio, Zapier MCP, etc.
"""

import os
import re
import json
import asyncio
import subprocess
import httpx
from pathlib import Path
from typing import Optional, Any
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
        result = {}
        for name, data in raw.items():
            result[name] = MCPConnection(**data)
        return result
    except Exception:
        return {}


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
    MCP_REGISTRY_PATH.write_text(json.dumps(raw, indent=2))


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
# HTTP/SSE MCP Client
# ─────────────────────────────────────────────────────────────

async def _http_list_tools(url: str, headers: dict) -> list[MCPTool]:
    """List tools from an HTTP MCP server"""
    base = url.rstrip("/")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base}",
            headers={"Content-Type": "application/json", **headers},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        resp.raise_for_status()
        data = resp.json()
        tools_raw = data.get("result", {}).get("tools", [])
        return [
            MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools_raw
        ]


async def _http_call_tool(url: str, headers: dict, tool_name: str, params: dict) -> str:
    """Call a tool on an HTTP MCP server"""
    base = url.rstrip("/")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{base}",
            headers={"Content-Type": "application/json", **headers},
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": params},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        content = result.get("content", [])
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(item.get("text", str(item)))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(result)


# ─────────────────────────────────────────────────────────────
# Stdio MCP Client (spawn subprocess, speak JSON-RPC over stdin/stdout)
# ─────────────────────────────────────────────────────────────

class StdioMCPClient:
    """Manages a stdio MCP server subprocess"""

    def __init__(self, conn: MCPConnection):
        self.conn = conn
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._id = 0

    async def start(self):
        env = {**os.environ, **self.conn.env}
        cmd = [self.conn.command] + self.conn.args
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        # Initialize
        await self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
                          "params": {"protocolVersion": "2024-11-05",
                                     "capabilities": {},
                                     "clientInfo": {"name": "kurt", "version": "0.1"}}})

    async def stop(self):
        if self._proc:
            self._proc.terminate()
            await self._proc.wait()

    def _next_id(self):
        self._id += 1
        return self._id

    async def _send(self, msg: dict) -> dict:
        if not self._proc:
            raise RuntimeError("Process not started")
        line = json.dumps(msg) + "\n"
        self._proc.stdin.write(line.encode())
        await self._proc.stdin.drain()
        # Read response (may have multiple lines before the response)
        for _ in range(50):  # max 50 lines
            raw = await asyncio.wait_for(self._proc.stdout.readline(), timeout=10)
            if not raw:
                break
            try:
                resp = json.loads(raw.decode().strip())
                if resp.get("id") == msg.get("id"):
                    return resp
            except json.JSONDecodeError:
                continue
        return {}

    async def list_tools(self) -> list[MCPTool]:
        resp = await self._send({"jsonrpc": "2.0", "id": self._next_id(),
                                  "method": "tools/list", "params": {}})
        tools_raw = resp.get("result", {}).get("tools", [])
        return [
            MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools_raw
        ]

    async def call_tool(self, name: str, params: dict) -> str:
        resp = await self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": params},
        })
        result = resp.get("result", {})
        content = result.get("content", [])
        if isinstance(content, list):
            parts = [item.get("text", str(item)) if isinstance(item, dict) else str(item)
                     for item in content]
            return "\n".join(parts)
        return str(result)


# ─────────────────────────────────────────────────────────────
# Public API: list_tools + call_tool for any connection
# ─────────────────────────────────────────────────────────────

async def list_tools(conn: MCPConnection) -> list[MCPTool]:
    """List tools from any MCP connection"""
    tools = []
    try:
        if conn.transport == "http" or conn.transport == "sse":
            tools = await _http_list_tools(conn.url, conn.headers)
        elif conn.transport == "stdio":
            client = StdioMCPClient(conn)
            await client.start()
            tools = await client.list_tools()
            await client.stop()
    except Exception as e:
        console.print(f"[red]❌ {conn.name}: {e}[/red]")
    for t in tools:
        t.server_name = conn.name
    return tools


async def call_tool(conn: MCPConnection, tool_name: str, params: dict) -> str:
    """Call a tool on any MCP connection"""
    try:
        if conn.transport == "http" or conn.transport == "sse":
            return await _http_call_tool(conn.url, conn.headers, tool_name, params)
        elif conn.transport == "stdio":
            client = StdioMCPClient(conn)
            await client.start()
            result = await client.call_tool(tool_name, params)
            await client.stop()
            return result
    except Exception as e:
        return f"❌ MCP error ({conn.name}/{tool_name}): {e}"
    return "❌ Unknown transport"


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
