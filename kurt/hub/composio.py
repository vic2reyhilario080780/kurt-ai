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

COMPOSIO_BASE = "https://backend.composio.dev/api/v3.1"  # v1 was retired by Composio
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
    "🎵 Music & Media": [
        ("spotify", "Spotify", "Playback, playlists & search"),
        ("youtube", "YouTube", "Videos & channels"),
    ],
}


def get_composio_key() -> str | None:
    """Get Composio API key from env"""
    # Load from ~/.kurt/.env — setup.py saves values quoted (quote_mode="always"),
    # so this must go through dotenv's parser rather than a naive split("="),
    # which left the literal quote characters in the value and made every
    # key look "invalid" to Composio.
    env_path = KURT_DIR / ".env"
    if env_path.exists():
        from dotenv import dotenv_values
        value = dotenv_values(env_path).get("COMPOSIO_API_KEY")
        if value:
            return value
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


def _composio_error(data: dict, resp: httpx.Response) -> str:
    err = data.get("error")
    if isinstance(err, dict):
        msg = err.get("message", "Unknown error")
        fix = err.get("suggested_fix")
        return f"{msg} ({fix})" if fix else msg
    return f"HTTP {resp.status_code}: {data}"


def composio_connect(app_name: str):
    """Connect to a Composio app — mirrors Claude's 'open link, log in, authorize' flow:
    1. Make sure a (Composio-managed) auth config exists for the toolkit.
    2. Start a connected account against it — Composio hands back a redirect URL.
    3. User opens that URL, logs into the real app, and authorizes.
    No manual tokens or JSON editing required.
    """
    api_key = get_composio_key()
    slug = app_name.strip().lower()

    if not api_key:
        console.print(f"[yellow]⚠️  Need Composio API key. Run [cyan]kurt setup[/cyan] first.[/yellow]")
        return

    console.print(f"[cyan]🔗 Connecting to {slug} via Composio...[/cyan]")

    try:
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        with httpx.Client(timeout=20) as client:
            # 1. Get (or create) a Composio-managed OAuth app registration for this toolkit —
            #    this is what lets us skip asking the user for their own client id/secret.
            resp = client.post(
                f"{COMPOSIO_BASE}/auth_configs",
                headers=headers,
                json={
                    "toolkit": {"slug": slug},
                    "auth_config": {"type": "use_composio_managed_auth"},
                },
            )
            data = resp.json()
            if resp.status_code >= 400:
                console.print(f"[red]❌ {_composio_error(data, resp)}[/red]")
                return
            auth_config_id = data["auth_config"]["id"]

            # 2. Start linking an account under that auth config.
            resp = client.post(
                f"{COMPOSIO_BASE}/connected_accounts",
                headers=headers,
                json={
                    "auth_config": {"id": auth_config_id},
                    "connection": {"user_id": "default"},
                },
            )
            data = resp.json()
            if resp.status_code >= 400:
                console.print(f"[red]❌ {_composio_error(data, resp)}[/red]")
                return

        redirect_url = (data.get("connectionData") or {}).get("val", {}).get("redirectUrl")
        if redirect_url:
            console.print(Panel(
                f"[green]✅ Open this URL to authorize {slug}:[/green]\n\n"
                f"[link={redirect_url}]{redirect_url}[/link]\n\n"
                f"[dim]Log in and approve — KURT picks up the connection automatically once you're done.[/dim]",
                title=f"🔗 Connect {slug}",
                box=box.ROUNDED,
                border_style="green",
            ))
        else:
            # No OAuth step needed (e.g. API-key-only toolkits) — already linked.
            console.print(f"[green]✅ Connected to {slug}![/green]")

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
            resp = client.get(f"{COMPOSIO_BASE}/connected_accounts", headers=headers)
            data = resp.json()

        if resp.status_code >= 400:
            console.print(f"[red]❌ {_composio_error(data, resp)}[/red]")
            return

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
            status_val = account.get("status", "Unknown")
            status = "✅ Active" if status_val == "ACTIVE" else "⚠️  " + status_val
            table.add_row(
                account.get("toolkit", {}).get("slug", ""),
                status,
                (account.get("created_at") or "")[:10],
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Error fetching status: {e}[/red]")
