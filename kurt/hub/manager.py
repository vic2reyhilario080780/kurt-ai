"""
KURT Hub Manager — Unified interface for all sources
Combines: aitmpl.com + Composio + awesome-mcp-servers + LangChain + n8n
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from .aitmpl import hub_list, hub_search, hub_install, hub_stats, TYPE_ICONS
from .composio import composio_list, composio_connect, composio_status
from .mcp_servers import mcp_list, langchain_list, n8n_list, n8n_trigger, zapier_list

console = Console()

HUB_SOURCES = {
    "aitmpl": {
        "name": "aitmpl.com",
        "icon": "🌐",
        "description": "909 skills, 422 agents, 111 MCPs, 288 commands",
        "url": "https://aitmpl.com",
        "auth": "None — public API!",
        "count": "1,800+",
    },
    "composio": {
        "name": "Composio",
        "icon": "🔌",
        "description": "250+ app connectors — Gmail, Slack, Shopify, etc.",
        "url": "https://composio.dev",
        "auth": "API key (free tier)",
        "count": "250+",
    },
    "mcp-servers": {
        "name": "awesome-mcp-servers",
        "icon": "🛠️",
        "description": "500+ community MCP servers — Postgres, Notion, etc.",
        "url": "https://github.com/punkpeye/awesome-mcp-servers",
        "auth": "None — open source",
        "count": "500+",
    },
    "langchain": {
        "name": "LangChain Tools",
        "icon": "🦜",
        "description": "100+ tools — search, calculator, Python, PDFs",
        "url": "https://github.com/langchain-ai/langchain",
        "auth": "None — open source",
        "count": "100+",
    },
    "n8n": {
        "name": "n8n",
        "icon": "⚙️",
        "description": "400+ workflow nodes — self-hosted automations",
        "url": "https://n8n.io",
        "auth": "Self-hosted API key",
        "count": "400+",
    },
    "zapier": {
        "name": "Zapier",
        "icon": "⚡",
        "description": "9,000+ app automations — Gmail, Shopify, Slack, etc.",
        "url": "https://zapier.com",
        "auth": "Zapier NLA API key",
        "count": "9,000+",
    },
}


def hub_overview():
    """Show KURT Hub overview — all sources"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🌐 KURT Universal Hub[/bold cyan]\n"
        "[dim]Your all-in-one AI skills, connectors & automation store[/dim]",
        box=box.DOUBLE,
        border_style="cyan",
    ))
    console.print()

    table = Table(
        title="📦 Available Sources",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Icon", width=4)
    table.add_column("Source", style="cyan", width=22)
    table.add_column("What's Inside", style="white", width=40)
    table.add_column("Count", style="green", width=8)
    table.add_column("Auth", style="dim", width=20)

    for key, info in HUB_SOURCES.items():
        table.add_row(
            info["icon"],
            info["name"],
            info["description"],
            info["count"],
            info["auth"],
        )

    console.print(table)

    console.print()
    console.print("[bold white]📋 Available Commands:[/bold white]")
    commands = [
        ("kurt hub skills", "Browse 909 skills from aitmpl.com"),
        ("kurt hub agents", "Browse 422 AI agents"),
        ("kurt hub mcp", "Browse 111 MCPs + 500 community MCPs"),
        ("kurt hub commands", "Browse 288 slash commands"),
        ("kurt hub search <query>", "Search across ALL sources"),
        ("kurt hub install <type> <cat>/<name>", "Install a component"),
        ("kurt connect list", "Show 250+ Composio connectors"),
        ("kurt connect <app>", "Connect to an app (Gmail, Slack...)"),
        ("kurt n8n list", "Show 400+ n8n workflow nodes"),
        ("kurt hub stats", "Show hub statistics"),
    ]

    cmd_table = Table(box=box.SIMPLE, border_style="dim", show_header=False)
    cmd_table.add_column("Command", style="cyan", width=40)
    cmd_table.add_column("Description", style="dim", width=45)

    for cmd, desc in commands:
        cmd_table.add_row(cmd, desc)

    console.print(cmd_table)
    console.print()


def hub_command(subcommand: str, args: list = None):
    """Route hub commands to appropriate handler"""
    args = args or []

    if subcommand == "overview" or subcommand is None:
        hub_overview()

    elif subcommand in ["skills", "agents", "commands", "mcps", "hooks", "mods"]:
        search = " ".join(args) if args else None
        hub_list(component_type=subcommand, search=search)

    elif subcommand == "search":
        if not args:
            console.print("[yellow]Usage: kurt hub search <query>[/yellow]")
            return
        query = " ".join(args)
        hub_search(query)

    elif subcommand == "install":
        if len(args) < 2:
            console.print("[yellow]Usage: kurt hub install <type> <category>/<name>[/yellow]")
            return
        hub_install(args[0], args[1])

    elif subcommand == "stats":
        hub_stats()

    elif subcommand == "mcp-servers":
        search = " ".join(args) if args else None
        mcp_list(search=search)

    elif subcommand == "langchain":
        search = " ".join(args) if args else None
        langchain_list(search=search)

    elif subcommand == "n8n":
        n8n_list()

    elif subcommand == "zapier":
        search = " ".join(args) if args else None
        zapier_list(search=search)

    else:
        console.print(f"[yellow]Unknown hub command: {subcommand}[/yellow]")
        console.print("[dim]Run [cyan]kurt hub[/cyan] to see all commands.[/dim]")


def connect_command(subcommand: str = None, args: list = None):
    """Route connect commands"""
    args = args or []

    if subcommand in ["list", None]:
        search = " ".join(args) if args else None
        composio_list(search=search)

    elif subcommand == "status":
        composio_status()

    elif subcommand == "search":
        if not args:
            console.print("[yellow]Usage: kurt connect search <query>[/yellow]")
            return
        composio_list(search=" ".join(args))

    else:
        # Treat as app name to connect
        composio_connect(subcommand)
