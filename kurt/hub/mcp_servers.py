"""
KURT Hub — awesome-mcp-servers + LangChain + n8n + Zapier Integration
500+ community MCP servers, 100+ LangChain tools, 400+ n8n nodes, 9000+ Zapier apps
"""

import os
import httpx
import json
import webbrowser
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
DATA_DIR = Path(__file__).parents[1] / "data"

_zapier_apps_cache: list | None = None
_n8n_integrations_cache: list | None = None


def load_zapier_apps() -> list[str]:
    """Full bundled snapshot of Zapier's public app directory (10,090 app
    slugs at time of writing — scraped from Zapier's own sitemap, the same
    public listing their site indexes for search engines). ZAPIER_APPS
    below is only a small curated subset for the printed category
    browser; this backs the full picker."""
    global _zapier_apps_cache
    if _zapier_apps_cache is None:
        _zapier_apps_cache = json.loads((DATA_DIR / "zapier_apps.json").read_text())
    return _zapier_apps_cache


def load_n8n_integrations() -> list[str]:
    """Full bundled snapshot of n8n's public integrations directory (2,635
    slugs at time of writing — scraped from n8n.io's own sitemap)."""
    global _n8n_integrations_cache
    if _n8n_integrations_cache is None:
        _n8n_integrations_cache = json.loads((DATA_DIR / "n8n_integrations.json").read_text())
    return _n8n_integrations_cache


def zapier_open(slug: str):
    """Zapier itself hosts the actual connect/Zap-building UI for a given
    app — there's no API for a third party like Kurt to establish a live
    per-app OAuth session the way Composio or native MCP servers allow.
    The honest move is to open the real integration page for the user."""
    url = f"https://zapier.com/apps/{slug}/integrations"
    label = slug.replace("-", " ").title()
    console.print(Panel(
        f"[green]Opening {label}'s Zapier integration page…[/green]\n\n"
        f"[link={url}]{url}[/link]\n\n"
        f"[dim]Build the Zap there — Zapier doesn't expose a way for Kurt "
        f"to connect a third-party app on your behalf. Once it's built, "
        f"Kurt can call it through Zapier's own webhook or NLA actions "
        f"(set a ZAPIER_NLA_API_KEY with [cyan]kurt setup[/cyan]).[/dim]",
        title=f"⚡ {label}", box=box.ROUNDED, border_style="green",
    ))
    try:
        webbrowser.open(url)
    except Exception:
        pass


def n8n_open(slug: str):
    """Same reasoning as zapier_open: n8n nodes are built and run inside
    your own n8n instance — Kurt can trigger an existing n8n workflow
    (see n8n_trigger below) but can't remotely 'connect' one of n8n's
    built-in node types on your behalf."""
    url = f"https://n8n.io/integrations/{slug}/"
    label = slug.replace("-", " ").title()
    console.print(Panel(
        f"[green]Opening {label}'s n8n integration page…[/green]\n\n"
        f"[link={url}]{url}[/link]\n\n"
        f"[dim]Build the workflow in your n8n instance, then trigger it "
        f"from Kurt with [cyan]kurt n8n run <workflow-id>[/cyan].[/dim]",
        title=f"⚙️  {label}", box=box.ROUNDED, border_style="green",
    ))
    try:
        webbrowser.open(url)
    except Exception:
        pass

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


# Zapier apps catalog (9,000+ apps — curated popular ones)
ZAPIER_APPS = {
    "📧 Communication": [
        ("gmail", "Gmail", "Send & receive emails"),
        ("slack", "Slack", "Team messaging"),
        ("outlook", "Outlook", "Microsoft email"),
        ("discord", "Discord", "Community & gaming"),
        ("telegram", "Telegram", "Bot messaging"),
        ("whatsapp", "WhatsApp Business", "Customer messaging"),
        ("sms", "SMS by Zapier", "Send text messages"),
        ("twilio", "Twilio", "SMS, Voice, WhatsApp"),
    ],
    "📅 Productivity": [
        ("google-calendar", "Google Calendar", "Events & scheduling"),
        ("notion", "Notion", "Docs & databases"),
        ("trello", "Trello", "Kanban boards"),
        ("asana", "Asana", "Project management"),
        ("todoist", "Todoist", "Task management"),
        ("monday", "Monday.com", "Work OS"),
        ("clickup", "ClickUp", "Project management"),
        ("airtable", "Airtable", "Spreadsheet DB"),
        ("google-sheets", "Google Sheets", "Spreadsheets"),
        ("microsoft-teams", "Microsoft Teams", "Team collaboration"),
    ],
    "🛒 E-Commerce": [
        ("shopify", "Shopify", "Store & orders"),
        ("woocommerce", "WooCommerce", "WordPress store"),
        ("lazada", "Lazada", "Southeast Asia marketplace"),
        ("shopee", "Shopee", "SEA marketplace"),
        ("stripe", "Stripe", "Payments"),
        ("paypal", "PayPal", "Payments"),
        ("paymongorc", "PayMongo", "PH payments"),
        ("gcash", "GCash", "PH mobile wallet"),
    ],
    "📊 CRM & Marketing": [
        ("hubspot", "HubSpot", "CRM & marketing"),
        ("salesforce", "Salesforce", "Enterprise CRM"),
        ("mailchimp", "Mailchimp", "Email marketing"),
        ("klaviyo", "Klaviyo", "E-com email"),
        ("activecampaign", "ActiveCampaign", "Marketing automation"),
        ("facebook-lead-ads", "Facebook Lead Ads", "Lead generation"),
    ],
    "💾 Storage & Files": [
        ("google-drive", "Google Drive", "Files & folders"),
        ("dropbox", "Dropbox", "Cloud storage"),
        ("onedrive", "OneDrive", "Microsoft storage"),
        ("box", "Box", "Enterprise storage"),
    ],
    "🛠️ Developer": [
        ("github", "GitHub", "Code & repos"),
        ("gitlab", "GitLab", "DevOps"),
        ("jira", "Jira", "Issue tracking"),
        ("webhook", "Webhooks by Zapier", "Custom HTTP triggers"),
        ("code", "Code by Zapier", "Run Python/JS code"),
        ("filter", "Filter by Zapier", "Conditional logic"),
        ("schedule", "Schedule by Zapier", "Time-based triggers"),
    ],
    "🤖 AI & Data": [
        ("openai", "OpenAI", "GPT & DALL-E"),
        ("anthropic", "Anthropic (Claude)", "Claude AI"),
        ("google-gemini", "Google Gemini", "Gemini AI"),
        ("formatter", "Formatter by Zapier", "Data transformation"),
        ("digest", "Digest by Zapier", "Collect & summarize"),
    ],
}


def _get_zapier_key() -> str:
    """Read Zapier NLA API key from ~/.kurt/.env"""
    env_path = KURT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("ZAPIER_NLA_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    return val if val else None
    return None


def _fetch_zapier_live(search: str = None, limit: int = 50) -> list:
    """Fetch live apps from Zapier NLA API"""
    key = _get_zapier_key()
    if not key:
        return []
    try:
        params = {"limit": limit}
        if search:
            params["search"] = search
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                "https://nla.zapier.com/api/v1/apps/",
                headers={"X-API-KEY": key},
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("results") or data.get("data") or []
            return data if isinstance(data, list) else []
    except Exception as e:
        console.print(f"[dim yellow]Zapier API error: {e} — using local catalog[/dim yellow]")
        return []


def zapier_list(search: str = None, category: str = None, limit: int = 0, show_all: bool = False):
    """List Zapier apps — Live API if key exists, fallback to static catalog"""
    console.print(f"\n[bold cyan]⚡ Zapier — 9,000+ App Automations[/bold cyan]")
    console.print(f"[dim]Source: zapier.com | Trigger workflows from KURT[/dim]\n")

    key = _get_zapier_key()
    if key:
        console.print(f"[green]✅ Zapier connected — fetching live catalog...[/green]\n")
        fetch_limit = 200 if show_all else (limit if limit > 0 else 50)
        live_apps = _fetch_zapier_live(search=search, limit=fetch_limit)
        if live_apps:
            _zapier_show_live(live_apps, search=search)
            return
        # fallback if live fetch failed
        console.print(f"[yellow]Live fetch failed — showing local catalog[/yellow]\n")
    else:
        console.print(f"[yellow]⚠️  Walang Zapier key → showing local catalog (48 apps)[/yellow]")
        console.print(f"[dim]Run [cyan]kurt setup[/cyan] → ZAPIER_NLA_API_KEY para makita 9,000+ apps[/dim]\n")

    # Static fallback
    shown = 0
    for cat_name, apps in ZAPIER_APPS.items():
        if category and category.lower() not in cat_name.lower():
            continue
        filtered = apps
        if search:
            filtered = [(slug, name, desc) for slug, name, desc in apps
                        if search.lower() in name.lower() or search.lower() in desc.lower()]
            if not filtered:
                continue

        table = Table(title=cat_name, box=box.SIMPLE, border_style="dim")
        table.add_column("App", style="cyan", width=22)
        table.add_column("Description", style="white", width=35)
        table.add_column("Connect", style="dim", width=28)

        for slug, name, desc in filtered:
            table.add_row(name, desc, f"kurt connect zapier {slug}")
            shown += 1

        console.print(table)

    console.print(f"\n[dim]Showing {shown} popular apps from local catalog[/dim]")
    console.print(f"[dim]💡 Get Zapier API key at [cyan]https://nla.zapier.com/settings/[/cyan][/dim]\n")


def _zapier_show_live(apps: list, search: str = None):
    """Display live Zapier apps in a Rich table"""
    title = f"⚡ ZAPIER LIVE ({len(apps)} apps)"
    if search:
        title += f" — search: '{search}'"

    table = Table(title=title, box=box.ROUNDED, border_style="cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("App", style="cyan", width=28)
    table.add_column("Slug", style="dim", width=22)
    table.add_column("Description", style="white", width=40)

    for i, app in enumerate(apps, 1):
        name = app.get("title") or app.get("name") or ""
        slug = app.get("slug") or app.get("id") or ""
        desc = app.get("description") or ""
        if len(desc) > 38:
            desc = desc[:38] + "..."
        table.add_row(str(i), name, slug, desc)

    console.print(table)
    console.print(f"\n[dim]💡 Use [cyan]kurt hub zapier --search <query>[/cyan] to filter[/dim]\n")


# ══════════════════════════════════════
# GPT PLUGINS / ACTIONS CATALOG
# Archived from OpenAI plugin store (deprecated 2024)
# Now lives as "GPT Actions" in CustomGPTs
# ══════════════════════════════════════

GPT_PLUGINS = {
    "🔍 Search & Research": [
        ("bing", "Bing Search", "Real-time web search by Microsoft"),
        ("wolfram", "Wolfram Alpha", "Computation, math, science, data"),
        ("scholar", "ScholarAI", "Search peer-reviewed papers (PubMed, ArXiv)"),
        ("aylien", "AYLIEN News", "Real-time news search & analysis"),
        ("metaphor", "Metaphor Search", "Neural search engine"),
        ("you-search", "You.com Search", "Privacy-focused web search"),
        ("edgar", "SEC EDGAR", "SEC filings & financial documents"),
    ],
    "🛒 Shopping & Price": [
        ("klarna", "Klarna", "Shop 1,000+ stores — price compare"),
        ("shein", "Shein", "Fashion & clothing search"),
        ("instacart", "Instacart", "Grocery delivery"),
        ("expedia", "Expedia", "Travel — flights, hotels, cars"),
        ("kayak", "KAYAK", "Travel search & booking"),
        ("opentable", "OpenTable", "Restaurant reservations"),
        ("yelp", "Yelp", "Local businesses & reviews"),
    ],
    "💼 Productivity & Docs": [
        ("noteable", "Noteable", "Create notebooks — Python, SQL, Markdown"),
        ("askyourpdf", "AskYourPDF", "Chat with any PDF document"),
        ("docmaker", "DocMaker", "Create PDFs from templates"),
        ("smart-slides", "SmartSlides", "Generate slide presentations"),
        ("mermaid", "MermaidChart", "Create diagrams & flowcharts"),
        ("monday", "Monday.com", "Project management"),
        ("trello", "Trello", "Kanban boards"),
        ("jira", "Jira", "Issue & sprint tracking"),
    ],
    "🤖 Code & Dev": [
        ("github-copilot", "GitHub Copilot", "Code suggestions & completion"),
        ("replit", "Replit", "Run code in browser"),
        ("code-runner", "Code Runner", "Execute Python, JS, SQL"),
        ("sql-query", "SQL Query", "Natural language to SQL"),
        ("zapier-ai", "Zapier AI Actions", "Connect 5,000+ apps"),
        ("make", "Make (Integromat)", "Visual automation workflows"),
    ],
    "📊 Data & Finance": [
        ("portfoliopilot", "PortfolioPilot", "AI investment advisor"),
        ("clearbit", "Clearbit", "Company & contact data"),
        ("polygon", "Polygon.io", "Real-time stock market data"),
        ("world-news", "World News", "Global news aggregator"),
        ("coinmarketcap", "CoinMarketCap", "Crypto prices & data"),
        ("alpha-vantage", "Alpha Vantage", "Stock & forex data"),
    ],
    "🎨 Creative & Media": [
        ("dalle-image", "DALL-E 3", "AI image generation (OpenAI built-in)"),
        ("stable-diffusion", "Stable Diffusion", "Open-source image AI"),
        ("video-insights", "Video Insights", "Chat with YouTube videos"),
        ("photorealistic", "Photorealistic", "Detailed image prompts"),
        ("there-is-an-ai", "There's An AI For That", "Find AI tools by use case"),
    ],
    "🌏 Philippine & SEA": [
        ("lazada-ph", "Lazada Philippines", "PH e-commerce marketplace"),
        ("shopee-ph", "Shopee Philippines", "SEA marketplace"),
        ("gcash-api", "GCash", "PH mobile wallet integration"),
        ("paymongo", "PayMongo", "PH payment gateway"),
        ("grab", "Grab", "SEA transport & delivery"),
        ("foodpanda", "foodpanda", "Food delivery in PH"),
    ],
}


def gpt_plugins_list(search: str = None, category: str = None, show_all: bool = False):
    """Browse ChatGPT plugins & GPT Actions catalog"""
    console.print(f"\n[bold cyan]🤖 ChatGPT Plugins & GPT Actions Catalog[/bold cyan]")
    console.print(f"[dim]Source: OpenAI Plugin Store archive + community GPT Actions[/dim]\n")
    console.print(f"[yellow]ℹ️  OpenAI deprecated plugins in 2024 → now 'GPT Actions' in CustomGPTs[/yellow]\n")

    shown = 0
    for cat_name, plugins in GPT_PLUGINS.items():
        if category and category.lower() not in cat_name.lower():
            continue

        filtered = plugins
        if search:
            sl = search.lower()
            filtered = [(slug, name, desc) for slug, name, desc in plugins
                        if sl in name.lower() or sl in desc.lower()]
            if not filtered:
                continue

        table = Table(title=cat_name, box=box.SIMPLE, border_style="dim")
        table.add_column("Plugin/Action", style="cyan", width=24)
        table.add_column("Description", style="white", width=40)
        table.add_column("Status", style="dim", width=16)

        for slug, name, desc in filtered:
            status = "✅ GPT Action" if slug in ("dalle-image",) else "📦 Archived plugin"
            table.add_row(name, desc, status)
            shown += 1

        console.print(table)

    total = sum(len(v) for v in GPT_PLUGINS.values())
    console.print(f"\n[dim]Showing {shown} of {total} plugins in catalog[/dim]")
    console.print(f"[dim]💡 These are usable as GPT Actions — integrate via OpenAI API or Zapier[/dim]\n")


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
