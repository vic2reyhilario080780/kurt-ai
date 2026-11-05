"""
KURT Hub — awesome-mcp-servers + LangChain + n8n Integration
500+ community MCP servers, 100+ LangChain tools, 400+ n8n nodes
"""

import os
import httpx
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"

# Curated list of awesome-mcp-servers (github.com/punkpeye/awesome-mcp-servers)
AWESOME_MCP_SERVERS = {
    "🗄️ Databases": [
        ("postgres-mcp", "PostgreSQL", "Query & manage Postgres DBs", "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres"),
        ("sqlite-mcp", "SQLite", "Local SQLite database", "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite"),
        ("mysql-mcp", "MySQL", "MySQL database operations", "https://github.com/benborla/mcp-server-mysql"),
        ("supabase-mcp", "Supabase", "Supabase DB + Auth + Storage", "https://github.com/supabase-community/supabase-mcp"),
        ("redis-mcp", "Redis", "Redis cache & data store", "https://github.com/modelcontextprotocol/servers/tree/main/src/redis"),
        ("mongodb-mcp", "MongoDB", "MongoDB document DB", "https://github.com/kiliczsh/mcp-mongo-server"),
    ],
    "📁 Files & Storage": [
        ("filesystem-mcp", "Filesystem", "Read/write local files", "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem"),
        ("gdrive-mcp", "Google Drive", "Google Drive files", "https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive"),
        ("github-mcp", "GitHub", "Repos, issues, PRs", "https://github.com/modelcontextprotocol/servers/tree/main/src/github"),
        ("gitlab-mcp", "GitLab", "GitLab repos & CI/CD", "https://github.com/zueai/mcp-server-gitlab"),
    ],
    "🌐 Web & Search": [
        ("brave-search-mcp", "Brave Search", "Privacy-focused web search", "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search"),
        ("puppeteer-mcp", "Puppeteer", "Browser automation", "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer"),
        ("fetch-mcp", "Fetch", "HTTP requests & web scraping", "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch"),
        ("serper-mcp", "Serper", "Google Search API", "https://github.com/marcopesani/mcp-server-serper"),
    ],
    "📧 Communication": [
        ("gmail-mcp", "Gmail", "Send & read Gmail", "https://github.com/modelcontextprotocol/servers/tree/main/src/gmail"),
        ("slack-mcp", "Slack", "Slack messages & channels", "https://github.com/modelcontextprotocol/servers/tree/main/src/slack"),
        ("telegram-mcp", "Telegram", "Telegram bot messages", "https://github.com/kfastov/mcp-telegram"),
    ],
    "📝 Productivity": [
        ("notion-mcp", "Notion", "Notion pages & databases", "https://github.com/makenotion/notion-mcp-server"),
        ("obsidian-mcp", "Obsidian", "Obsidian notes vault", "https://github.com/MarkusPfundstein/mcp-obsidian"),
        ("linear-mcp", "Linear", "Linear issues & projects", "https://github.com/linear/linear-mcp-server"),
        ("asana-mcp", "Asana", "Asana tasks & projects", "https://github.com/roychri/mcp-server-asana"),
        ("jira-mcp", "Jira", "Jira issues & sprints", "https://github.com/sooperset/mcp-atlassian"),
    ],
    "🤖 AI & Tools": [
        ("memory-mcp", "Memory", "Persistent AI memory", "https://github.com/modelcontextprotocol/servers/tree/main/src/memory"),
        ("sequential-thinking", "Sequential Thinking", "Chain-of-thought reasoning", "https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking"),
        ("everart-mcp", "EverArt", "AI image generation", "https://github.com/EverArt/everart-mcp"),
    ],
    "⚙️ Developer": [
        ("aws-kb-mcp", "AWS Knowledge Base", "AWS documentation search", "https://github.com/awslabs/mcp"),
        ("docker-mcp", "Docker", "Container management", "https://github.com/ckreiling/mcp-server-docker"),
        ("kubernetes-mcp", "Kubernetes", "K8s cluster management", "https://github.com/strowk/mcp-k8s-go"),
    ],
}

# LangChain tools catalog
LANGCHAIN_TOOLS = {
    "🔍 Search": [
        ("SerpAPI", "Google search results", "pip install google-search-results"),
        ("DuckDuckGo", "Privacy-friendly search", "pip install duckduckgo-search"),
        ("Wikipedia", "Wikipedia lookups", "pip install wikipedia"),
        ("Tavily", "AI-optimized search", "pip install tavily-python"),
    ],
    "📊 Data & Math": [
        ("Calculator", "Math calculations", "Built-in"),
        ("Python REPL", "Run Python code", "Built-in"),
        ("Pandas DataFrame", "Analyze CSV/Excel data", "pip install pandas"),
        ("Wolfram Alpha", "Advanced math & science", "pip install wolframalpha"),
    ],
    "🌐 Web": [
        ("Requests", "HTTP web requests", "pip install requests"),
        ("BeautifulSoup", "Web scraping", "pip install beautifulsoup4"),
        ("Playwright", "Browser automation", "pip install playwright"),
    ],
    "📁 Files": [
        ("File System", "Read/write files", "Built-in"),
        ("PDF Reader", "Extract PDF text", "pip install pypdf"),
        ("CSV Agent", "Query CSV files", "Built-in"),
        ("Excel", "Read/write Excel", "pip install openpyxl"),
    ],
}

# n8n nodes catalog
N8N_NODES = {
    "🔗 Triggers": [
        ("Webhook", "HTTP trigger from any service"),
        ("Schedule", "Cron-based triggers"),
        ("Email", "Email inbox triggers"),
        ("RSS", "RSS feed monitoring"),
    ],
    "📧 Communication": [
        ("Gmail", "Send/receive Gmail"),
        ("Slack", "Slack messages"),
        ("Telegram", "Telegram bot"),
        ("Discord", "Discord messages"),
        ("WhatsApp Business", "WhatsApp messages"),
        ("Twilio", "SMS & calls"),
    ],
    "🛒 E-Commerce": [
        ("Shopify", "Orders, products, customers"),
        ("WooCommerce", "WordPress store"),
        ("Stripe", "Payments & subscriptions"),
        ("PayPal", "Payments"),
    ],
    "📊 Data": [
        ("Postgres", "PostgreSQL queries"),
        ("MySQL", "MySQL operations"),
        ("MongoDB", "MongoDB operations"),
        ("Airtable", "Airtable records"),
        ("Google Sheets", "Spreadsheet operations"),
    ],
    "🤖 AI": [
        ("OpenAI", "GPT-4 & DALL-E"),
        ("Anthropic", "Claude AI"),
        ("Langchain Agent", "AI agent execution"),
        ("Embeddings", "Vector embeddings"),
    ],
}


def mcp_list(search: str = None, category: str = None):
    """List awesome-mcp-servers catalog"""
    console.print(f"\n[bold cyan]🔌 awesome-mcp-servers — 500+ Community MCPs[/bold cyan]")
    console.print(f"[dim]Source: github.com/punkpeye/awesome-mcp-servers[/dim]\n")

    shown = 0
    for cat_name, servers in AWESOME_MCP_SERVERS.items():
        if category and category.lower() not in cat_name.lower():
            continue

        if search:
            servers = [(slug, name, desc, url) for slug, name, desc, url in servers
                       if search.lower() in name.lower() or search.lower() in desc.lower()]
            if not servers:
                continue

        table = Table(
            title=cat_name,
            box=box.SIMPLE,
            border_style="dim",
        )
        table.add_column("Server", style="cyan", width=22)
        table.add_column("Description", style="white", width=35)
        table.add_column("Install", style="dim", width=30)

        for slug, name, desc, url in servers:
            table.add_row(name, desc, f"kurt mcp install {slug}")
            shown += 1

        console.print(table)

    console.print(f"\n[dim]Showing {shown} servers. See all 500+ at github.com/punkpeye/awesome-mcp-servers[/dim]")


def langchain_list(search: str = None):
    """List LangChain tools"""
    console.print(f"\n[bold cyan]🦜 LangChain Tools — 100+ Tools[/bold cyan]")
    console.print(f"[dim]Source: github.com/langchain-ai/langchain[/dim]\n")

    for cat_name, tools in LANGCHAIN_TOOLS.items():
        if search:
            tools = [(name, desc, install) for name, desc, install in tools
                     if search.lower() in name.lower() or search.lower() in desc.lower()]
            if not tools:
                continue

        table = Table(title=cat_name, box=box.SIMPLE, border_style="dim")
        table.add_column("Tool", style="cyan", width=20)
        table.add_column("Description", style="white", width=35)
        table.add_column("Install", style="dim", width=30)

        for name, desc, install in tools:
            table.add_row(name, desc, install)

        console.print(table)


def n8n_list(search: str = None):
    """List n8n nodes"""
    console.print(f"\n[bold cyan]⚙️  n8n Nodes — 400+ Workflow Nodes[/bold cyan]")
    console.print(f"[dim]Source: github.com/n8n-io/n8n (self-hosted)[/dim]\n")

    # Check if n8n is configured
    env_path = KURT_DIR / ".env"
    n8n_key = None
    n8n_host = "http://localhost:5678"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("N8N_API_KEY="):
                    n8n_key = line.split("=", 1)[1].strip()
                elif line.startswith("N8N_HOST="):
                    n8n_host = line.split("=", 1)[1].strip()

    if n8n_key:
        console.print(f"[green]✅ n8n connected at {n8n_host}[/green]\n")
    else:
        console.print(f"[yellow]⚠️  n8n not configured. Run [cyan]kurt setup[/cyan] to add N8N_API_KEY[/yellow]\n")

    for cat_name, nodes in N8N_NODES.items():
        if search:
            nodes = [(name, desc) for name, desc in nodes
                     if search.lower() in name.lower() or search.lower() in desc.lower()]
            if not nodes:
                continue

        table = Table(title=cat_name, box=box.SIMPLE, border_style="dim")
        table.add_column("Node", style="cyan", width=25)
        table.add_column("Description", style="white", width=40)

        for name, desc in nodes:
            table.add_row(name, desc)

        console.print(table)

    console.print(f"\n[dim]To trigger n8n workflow: [cyan]kurt n8n run <workflow-id>[/cyan][/dim]")


def n8n_trigger(workflow_id: str, data: dict = None):
    """Trigger an n8n workflow via webhook"""
    env_path = KURT_DIR / ".env"
    n8n_key = None
    n8n_host = "http://localhost:5678"

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("N8N_API_KEY="):
                    n8n_key = line.split("=", 1)[1].strip()
                elif line.startswith("N8N_HOST="):
                    n8n_host = line.split("=", 1)[1].strip()

    if not n8n_key:
        console.print("[yellow]⚠️  n8n not configured. Run kurt setup first.[/yellow]")
        return

    console.print(f"[cyan]⚡ Triggering n8n workflow: {workflow_id}...[/cyan]")

    try:
        headers = {"X-N8N-API-KEY": n8n_key, "Content-Type": "application/json"}
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{n8n_host}/api/v1/workflows/{workflow_id}/activate",
                headers=headers,
                json=data or {},
            )
            result = resp.json()

        if resp.status_code == 200:
            console.print(f"[green]✅ Workflow triggered successfully![/green]")
            console.print(f"[dim]Result: {json.dumps(result, indent=2)[:200]}[/dim]")
        else:
            console.print(f"[red]❌ Error: {result}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Failed to trigger workflow: {e}[/red]")
