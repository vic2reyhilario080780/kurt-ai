"""
KURT Hub — Composio Integration
250+ app connectors with 1 API key
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

COMPOSIO_BASE = "https://backend.composio.dev/api/v1"
KURT_DIR = Path.home() / ".kurt"

# Popular Composio apps grouped by category
COMPOSIO_APPS = {
    "📧 Communication": [
        ("gmail", "Gmail", "Send & read emails"),
        ("slack", "Slack", "Messages & channels"),
        ("discord", "Discord", "Server & DMs"),
        ("telegram", "Telegram", "Bot & messages"),
        ("outlook", "Outlook", "Microsoft email"),
        ("whatsapp", "WhatsApp Business", "Messaging"),
    ],
    "📅 Productivity": [
        ("googlecalendar", "Google Calendar", "Events & scheduling"),
        ("notion", "Notion", "Docs & databases"),
        ("asana", "Asana", "Project management"),
        ("trello", "Trello", "Kanban boards"),
        ("linear", "Linear", "Issue tracking"),
        ("jira", "Jira", "Bug & issue tracking"),
        ("todoist", "Todoist", "Task management"),
    ],
    "💾 Storage & Files": [
        ("googledrive", "Google Drive", "Files & folders"),
        ("dropbox", "Dropbox", "Cloud storage"),
        ("onedrive", "OneDrive", "Microsoft storage"),
        ("box", "Box", "Enterprise storage"),
        ("airtable", "Airtable", "Spreadsheet DB"),
    ],
    "🛒 E-Commerce": [
        ("shopify", "Shopify", "Store & orders"),
        ("woocommerce", "WooCommerce", "WordPress store"),
        ("stripe", "Stripe", "Payments"),
        ("paypal", "PayPal", "Payments"),
    ],
    "📊 CRM & Marketing": [
        ("hubspot", "HubSpot", "CRM & marketing"),
        ("salesforce", "Salesforce", "Enterprise CRM"),
        ("mailchimp", "Mailchimp", "Email marketing"),
        ("klaviyo", "Klaviyo", "E-com marketing"),
    ],
    "🛠️ Developer Tools": [
        ("github", "GitHub", "Code & repos"),
        ("gitlab", "GitLab", "DevOps platform"),
        ("jira", "Jira", "Issue tracking"),
        ("vercel", "Vercel", "Deployments"),
        ("aws", "AWS", "Cloud services"),
        ("supabase", "Supabase", "Backend as service"),
    ],
    "📈 Analytics": [
        ("googleanalytics", "Google Analytics", "Website analytics"),
        ("mixpanel", "Mixpanel", "Product analytics"),
        ("amplitude", "Amplitude", "User analytics"),
    ],
    "🤖 AI Tools": [
        ("openai", "OpenAI", "GPT & DALL-E"),
        ("anthropic", "Anthropic", "Claude AI"),
        ("elevenlabs", "ElevenLabs", "Voice AI"),
    ],
}


def get_composio_key() -> str | None:
    """Get Composio API key from env"""
    # Load from ~/.kurt/.env
    env_path = KURT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("COMPOSIO_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.getenv("COMPOSIO_API_KEY")


def composio_list(category: str = None, search: str = None):
    """List available Composio connectors"""
    console.print(f"\n[bold cyan]🔌 Composio — 250+ App Connectors[/bold cyan]")

    api_key = get_composio_key()
    if not api_key:
        console.print(Panel(
            "[yellow]⚠️  Walang Composio API key![/yellow]\n\n"
            "Para ma-access ang 250+ connectors:\n"
            "1. Pumunta sa [link=https://app.composio.dev]https://app.composio.dev[/link]\n"
            "2. I-copy ang iyong API key\n"
            "3. I-run: [cyan]kurt setup[/cyan] → i-enter ang Composio key",
            title="🔑 Setup Required",
            box=box.ROUNDED,
            border_style="yellow",
        ))

    # Show built-in catalog (no API needed)
    console.print("\n[dim]Showing built-in app catalog. Connect via API for live status.[/dim]\n")

    for cat_name, apps in COMPOSIO_APPS.items():
        if category and category.lower() not in cat_name.lower():
            continue

        if search:
            apps = [(slug, name, desc) for slug, name, desc in apps
                    if search.lower() in name.lower() or search.lower() in desc.lower()]
            if not apps:
                continue

        table = Table(
            title=cat_name,
            box=box.SIMPLE,
            border_style="dim",
            show_lines=False,
        )
        table.add_column("App", style="cyan", width=20)
        table.add_column("Description", style="white", width=35)
        table.add_column("Connect", style="dim", width=30)

        for slug, name, desc in apps:
            table.add_row(
                name,
                desc,
                f"kurt connect {slug}",
            )

        console.print(table)

    console.print(f"\n[dim]Total: 250+ apps available. Run [cyan]kurt connect <app>[/cyan] to connect.[/dim]")


def composio_connect(app_name: str):
    """Connect to a Composio app"""
    api_key = get_composio_key()

    if not api_key:
        console.print(f"[yellow]⚠️  Need Composio API key. Run [cyan]kurt setup[/cyan] first.[/yellow]")
        return

    console.print(f"[cyan]🔗 Connecting to {app_name} via Composio...[/cyan]")

    try:
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        with httpx.Client(timeout=15) as client:
            # Initiate connection
            resp = client.post(
                f"{COMPOSIO_BASE}/connectedAccounts",
                headers=headers,
                json={"appName": app_name, "authMode": "OAUTH2"},
            )
            data = resp.json()

        if "redirectUrl" in data:
            console.print(Panel(
                f"[green]✅ Open this URL to authorize {app_name}:[/green]\n\n"
                f"[link={data['redirectUrl']}]{data['redirectUrl']}[/link]\n\n"
                f"[dim]After authorizing, it will be connected to KURT.[/dim]",
                title=f"🔗 Connect {app_name}",
                box=box.ROUNDED,
                border_style="green",
            ))
        elif "error" in data:
            console.print(f"[red]❌ Error: {data['error']}[/red]")
        else:
            console.print(f"[green]✅ Connected to {app_name}![/green]")

    except Exception as e:
        console.print(f"[red]❌ Connection failed: {e}[/red]")


def composio_status():
    """Show connected Composio apps"""
    api_key = get_composio_key()

    if not api_key:
        console.print("[yellow]⚠️  No Composio API key. Run kurt setup first.[/yellow]")
        return

    console.print("[cyan]📊 Checking connected apps...[/cyan]")

    try:
        headers = {"x-api-key": api_key}
        with httpx.Client(timeout=15) as client:
            resp = client.get(f"{COMPOSIO_BASE}/connectedAccounts", headers=headers)
            data = resp.json()

        accounts = data.get("items", [])
        if not accounts:
            console.print("[dim]No apps connected yet. Run [cyan]kurt connect <app>[/cyan][/dim]")
            return

        table = Table(
            title="🔌 Connected Apps",
            box=box.ROUNDED,
            border_style="green",
        )
        table.add_column("App", style="cyan", width=20)
        table.add_column("Status", width=15)
        table.add_column("Connected", style="dim", width=20)

        for account in accounts:
            status = "✅ Active" if account.get("status") == "ACTIVE" else "⚠️  " + account.get("status", "Unknown")
            table.add_row(
                account.get("appName", ""),
                status,
                account.get("createdAt", "")[:10],
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Error fetching status: {e}[/red]")
