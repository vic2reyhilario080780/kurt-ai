"""
KURT - Main CLI Entry Point
Personal AI Orchestrator — K.U.R.T.

Usage:
    kurt "any task here"
    kurt --model gpt4o "task"
    kurt --skill tiktok "gumawa ng script"
    kurt setup
    kurt models
    kurt skills
    kurt plugins
"""

import asyncio
import sys
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich import box

from kurt.utils.env_loader import load_env, check_setup
from kurt.core.orchestrator import analyze_task, TaskType
from kurt.core.router import ModelRouter
from kurt.core.memory import init_db, save_message, get_history
from kurt.skills.manager import list_skills, install_skill, remove_skill, \
    create_skill_template, get_skill_prompt
from kurt.plugins.manager import list_plugins, enable_plugin, disable_plugin

app = typer.Typer(
    name="kurt",
    help="🤖 KURT — Kinetic Unified Response Terminal",
    no_args_is_help=False,
    add_completion=True,
    invoke_without_command=True,
)

console = Console()
skill_app = typer.Typer(help="Manage KURT skills")
plugin_app = typer.Typer(help="Manage KURT plugins")
mcp_app = typer.Typer(help="Manage MCP connections")
hub_app = typer.Typer(help="🌐 Universal Hub — aitmpl.com, Composio, MCPs, n8n")
connect_app = typer.Typer(help="🔌 Connect apps via Composio (250+ apps)")

app.add_typer(skill_app, name="skill")
app.add_typer(plugin_app, name="plugin")
app.add_typer(mcp_app, name="mcp")
app.add_typer(hub_app, name="hub")
app.add_typer(connect_app, name="connect")

KURT_BANNER = """[bold cyan]
 ██╗  ██╗██╗   ██╗██████╗ ████████╗
 ██║ ██╔╝██║   ██║██╔══██╗╚══██╔══╝
 █████╔╝ ██║   ██║██████╔╝   ██║
 ██╔═██╗ ██║   ██║██╔══██╗   ██║
 ██║  ██╗╚██████╔╝██║  ██║   ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝
[/bold cyan]
[dim]Kinetic Unified Response Terminal[/dim]
[dim]Type [cyan]kurt --help[/cyan] for commands[/dim]
"""


def print_banner():
    console.print(KURT_BANNER)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version"),
):
    """🤖 KURT — Kinetic Unified Response Terminal"""
    if version:
        from kurt import __version__
        console.print(f"KURT v{__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("[dim]Usage: kurt ask \"your task here\"[/dim]")
        console.print("[dim]       kurt \"your task here\"  (shortcut via 'ask')[/dim]\n")
        console.print("Examples:")
        console.print('  [cyan]kurt ask "gumawa ng snake game"[/cyan]')
        console.print('  [cyan]kurt ask "research viral products ngayon"[/cyan]')
        console.print('  [cyan]kurt ask --skill tiktok "gumawa ng script"[/cyan]')
        console.print('\nRun [cyan]kurt setup[/cyan] to configure API keys')
        console.print('Run [cyan]kurt --help[/cyan] to see all commands')


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="Your task or question"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Force a specific model"),
    skill: Optional[str] = typer.Option(None, "--skill", "-s", help="Use a specific skill"),
    session: Optional[str] = typer.Option(None, "--session", help="Continue a session by ID"),
    no_memory: bool = typer.Option(False, "--no-memory", help="Huwag i-save ang conversation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show routing details"),
):
    """🤖 Ask KURT — auto-routes to best AI model"""

    # Load env
    load_env()

    # Check setup
    status = check_setup()
    if not status.get("openrouter") and not status.get("groq") and not status.get("ollama"):
        console.print("[red]❌ Walang configured AI provider![/red]")
        console.print("[yellow]Run: kurt setup[/yellow]")
        raise typer.Exit(1)

    # Init DB
    if not no_memory:
        init_db()

    # Session management
    current_session = session or str(uuid.uuid4())

    # Analyze the task
    analysis = analyze_task(prompt)

    # Override model if specified
    if model:
        analysis.model = model
        analysis.reason = f"Manual override: {model}"

    # Show routing info if verbose
    if verbose:
        console.print(Panel(
            f"[cyan]Task Type:[/cyan] {analysis.task_type.value}\n"
            f"[cyan]Model:[/cyan] {analysis.model}\n"
            f"[cyan]Provider:[/cyan] {analysis.provider}\n"
            f"[cyan]Reason:[/cyan] {analysis.reason}",
            title="🔍 Routing Info",
            box=box.ROUNDED,
            border_style="dim",
        ))

    # Build messages
    messages = []

    # Add skill system prompt if specified
    if skill:
        skill_prompt = get_skill_prompt(skill)
        if skill_prompt:
            messages.append({"role": "system", "content": skill_prompt})
            if verbose:
                console.print(f"[dim]🧠 Using skill: {skill}[/dim]")
        else:
            console.print(f"[yellow]⚠️  Skill not found: {skill}[/yellow]")

    # Add conversation history
    if not no_memory and session:
        history = get_history(current_session)
        messages.extend(history)

    # Add current prompt
    messages.append({"role": "user", "content": prompt})

    # Save user message
    if not no_memory:
        save_message(current_session, "user", prompt, analysis.model, analysis.task_type.value)

    # Stream the response
    asyncio.run(stream_response(
        analysis=analysis,
        messages=messages,
        session_id=current_session,
        no_memory=no_memory,
        verbose=verbose,
    ))


async def stream_response(analysis, messages, session_id, no_memory, verbose):
    """Stream AI response with real-time display"""
    router = ModelRouter()

    # Show model info (compact)
    if not verbose:
        console.print(
            f"[dim]🤖 {analysis.model} · {analysis.task_type.value}[/dim]"
        )

    console.print()

    full_response = ""

    try:
        with Live(Text(""), refresh_per_second=10, console=console) as live:
            async for chunk in router.route(
                provider=analysis.provider,
                model=analysis.model,
                messages=messages,
            ):
                full_response += chunk
                live.update(Text(full_response))

        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")

        # Try fallback
        if analysis.fallback_model != analysis.model:
            console.print(f"[yellow]↩ Trying fallback: {analysis.fallback_model}[/yellow]")
            try:
                full_response = ""
                with Live(Text(""), refresh_per_second=10, console=console) as live:
                    async for chunk in router.route(
                        provider=analysis.fallback_provider,
                        model=analysis.fallback_model,
                        messages=messages,
                    ):
                        full_response += chunk
                        live.update(Text(full_response))
                console.print()
            except Exception as e2:
                console.print(f"[red]❌ Fallback also failed: {e2}[/red]")
                return

    # Save to memory
    if not no_memory and full_response:
        save_message(session_id, "assistant", full_response, analysis.model)
        console.print(f"[dim]💾 Session: {session_id[:8]}... (use --session {session_id[:8]}... to continue)[/dim]")


# ══════════════════════════════════════
# SETUP COMMAND
# ══════════════════════════════════════

@app.command()
def setup():
    """⚙️  Configure KURT — API keys at settings"""
    from kurt.utils.setup import run_setup
    run_setup()


# ══════════════════════════════════════
# MODELS COMMAND
# ══════════════════════════════════════

@app.command()
def models():
    """📋 Show available AI models at status nila"""
    load_env()
    status = check_setup()

    from rich.table import Table
    table = Table(
        title="🤖 Available AI Models",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Provider", style="cyan", width=15)
    table.add_column("Models", style="white", width=40)
    table.add_column("Best For", style="dim", width=25)
    table.add_column("Status", width=12)

    model_list = [
        ("OpenRouter", "LLaMA 3.3, Gemini, DeepSeek...", "Everything!", "openrouter"),
        ("Google AI", "Gemini Flash, Gemini Pro", "Research, long docs", "google"),
        ("Groq", "LLaMA 3.3 70B, DeepSeek R1", "Speed, chat", "groq"),
        ("DeepSeek", "DeepSeek V3, R1, Coder", "Code, math, cheap", "deepseek"),
        ("OpenAI", "GPT-4o, o1, DALL-E", "General, images", "openai"),
        ("Anthropic", "Claude 3.5 Sonnet/Haiku", "Writing, coding", "anthropic"),
        ("Mistral", "Mistral Large, Codestral", "Code, multilingual", "mistral"),
        ("fal.ai", "Flux Schnell, SDXL", "Image generation", "fal"),
        ("Replicate", "MusicGen, Wan, CogVideo", "Music, video, media", "replicate"),
        ("Ollama", "Local LLaMA, Mistral...", "Offline mode!", "ollama"),
    ]

    for name, mdls, best_for, key in model_list:
        configured = status.get(key, False)
        status_text = "[green]✅ Ready[/green]" if configured else "[red]❌ No key[/red]"
        if key == "ollama":
            status_text = "[blue]📦 Local[/blue]"
        table.add_row(name, mdls, best_for, status_text)

    console.print(table)
    console.print("\n[dim]Run [cyan]kurt setup[/cyan] to add missing API keys[/dim]")


# ══════════════════════════════════════
# CHAT COMMAND (Interactive Mode)
# ══════════════════════════════════════

@app.command()
def chat(
    skill: Optional[str] = typer.Option(None, "--skill", "-s"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
):
    """💬 Interactive chat mode — mag-usap sa KURT"""
    load_env()
    init_db()

    session_id = str(uuid.uuid4())
    console.print(Panel(
        "[bold cyan]KURT — Interactive Chat Mode[/bold cyan]\n"
        "[dim]Type 'exit' or 'quit' to stop\n"
        "Type 'clear' to start new session\n"
        f"Session: {session_id[:8]}[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
    ))

    while True:
        try:
            prompt = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye! 👋[/dim]")
            break

        if not prompt:
            continue

        if prompt.lower() in ["exit", "quit", "bye"]:
            console.print("[dim]Bye! 👋[/dim]")
            break

        if prompt.lower() == "clear":
            session_id = str(uuid.uuid4())
            console.print(f"[dim]New session: {session_id[:8]}[/dim]")
            continue

        analysis = analyze_task(prompt)
        if model:
            analysis.model = model

        messages = []
        if skill:
            skill_prompt = get_skill_prompt(skill)
            if skill_prompt:
                messages.append({"role": "system", "content": skill_prompt})

        history = get_history(session_id)
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        save_message(session_id, "user", prompt)
        console.print(f"\n[bold green]KURT[/bold green] [dim]({analysis.model}):[/dim]")

        asyncio.run(stream_response(
            analysis=analysis,
            messages=messages,
            session_id=session_id,
            no_memory=False,
            verbose=False,
        ))


# ══════════════════════════════════════
# SKILL SUBCOMMANDS
# ══════════════════════════════════════

@skill_app.command("list")
def skill_list():
    """List all available skills"""
    list_skills()


@skill_app.command("install")
def skill_install(path: str = typer.Argument(..., help="Path to skill JSON file")):
    """Install a skill from JSON file"""
    install_skill(path)


@skill_app.command("remove")
def skill_remove(skill_id: str = typer.Argument(..., help="Skill ID to remove")):
    """Remove a custom skill"""
    remove_skill(skill_id)


@skill_app.command("create")
def skill_create(skill_id: str = typer.Argument(..., help="New skill ID")):
    """Create a new skill template"""
    create_skill_template(skill_id)


# ══════════════════════════════════════
# PLUGIN SUBCOMMANDS
# ══════════════════════════════════════

@plugin_app.command("list")
def plugin_list():
    """List all plugins"""
    list_plugins()


@plugin_app.command("enable")
def plugin_enable(plugin_id: str = typer.Argument(...)):
    """Enable a plugin"""
    enable_plugin(plugin_id)


@plugin_app.command("disable")
def plugin_disable(plugin_id: str = typer.Argument(...)):
    """Disable a plugin"""
    disable_plugin(plugin_id)


# ══════════════════════════════════════
# MCP SUBCOMMANDS
# ══════════════════════════════════════

@mcp_app.command("list")
def mcp_list():
    """List MCP connections"""
    console.print("[bold cyan]🔌 MCP Connections[/bold cyan]")
    console.print("[dim]Coming soon! MCP support in v0.2[/dim]")
    console.print("\nPlanned connectors:")
    mcps = [
        ("gmail", "📧 Gmail"),
        ("notion", "📝 Notion"),
        ("github", "🐙 GitHub"),
        ("slack", "💬 Slack"),
        ("tiktok", "🎵 TikTok"),
        ("shopee", "🛒 Shopee"),
        ("gcal", "📅 Google Calendar"),
        ("gdrive", "📁 Google Drive"),
        ("supabase", "🗄️  Supabase"),
        ("n8n", "⚙️  n8n"),
    ]
    for mcp_id, name in mcps:
        console.print(f"  [dim]kurt mcp connect {mcp_id}[/dim]  — {name}")


@mcp_app.command("connect")
def mcp_connect(service: str = typer.Argument(...)):
    """Connect an MCP service"""
    from kurt.hub import composio_connect
    composio_connect(service)


# ══════════════════════════════════════
# HUB COMMANDS — aitmpl.com + all sources
# ══════════════════════════════════════

@hub_app.callback(invoke_without_command=True)
def hub_callback(ctx: typer.Context):
    """🌐 Universal Hub — browse 1,800+ skills, MCPs, connectors"""
    if ctx.invoked_subcommand is None:
        from kurt.hub import hub_overview
        hub_overview()


@hub_app.command("skills")
def hub_skills(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """🧠 Browse 909 skills from aitmpl.com"""
    from kurt.hub import hub_list
    hub_list(component_type="skills", search=search, limit=limit)


@hub_app.command("agents")
def hub_agents(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """🤖 Browse 422 AI agents from aitmpl.com"""
    from kurt.hub import hub_list
    hub_list(component_type="agents", search=search, limit=limit)


@hub_app.command("commands")
def hub_commands(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """⚡ Browse 288 slash commands from aitmpl.com"""
    from kurt.hub import hub_list
    hub_list(component_type="commands", search=search, limit=limit)


@hub_app.command("mcp")
def hub_mcp(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """🔌 Browse 111 MCPs (aitmpl) + 500 community MCPs"""
    from kurt.hub import hub_list, mcp_list
    hub_list(component_type="mcps", search=search, limit=limit)
    console.print("\n[bold cyan]Community MCPs (awesome-mcp-servers):[/bold cyan]")
    mcp_list(search=search)


@hub_app.command("search")
def hub_search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n"),
):
    """🔍 Search across ALL hub sources"""
    from kurt.hub import hub_search
    hub_search(query, limit=limit)


@hub_app.command("install")
def hub_install_cmd(
    component_type: str = typer.Argument(..., help="Type: skills/agents/mcps/commands"),
    path: str = typer.Argument(..., help="Format: category/name"),
):
    """⬇️  Install a component from aitmpl.com"""
    from kurt.hub import hub_install
    hub_install(component_type, path)


@hub_app.command("stats")
def hub_stats_cmd():
    """📊 Show hub statistics"""
    from kurt.hub import hub_stats
    hub_stats()


@hub_app.command("langchain")
def hub_langchain(search: Optional[str] = typer.Argument(None)):
    """🦜 Browse 100+ LangChain tools"""
    from kurt.hub import langchain_list
    langchain_list(search=search)


@hub_app.command("n8n")
def hub_n8n():
    """⚙️  Browse 400+ n8n workflow nodes"""
    from kurt.hub import n8n_list
    n8n_list()


# ══════════════════════════════════════
# CONNECT COMMANDS — Composio
# ══════════════════════════════════════

@connect_app.callback(invoke_without_command=True)
def connect_callback(ctx: typer.Context):
    """🔌 Connect to 250+ apps via Composio"""
    if ctx.invoked_subcommand is None:
        from kurt.hub import composio_list
        composio_list()


@connect_app.command("list")
def connect_list(
    search: Optional[str] = typer.Argument(None, help="Search apps"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
):
    """📋 List all 250+ available app connectors"""
    from kurt.hub import composio_list
    composio_list(category=category, search=search)


@connect_app.command("status")
def connect_status():
    """✅ Show currently connected apps"""
    from kurt.hub import composio_status
    composio_status()


@connect_app.command("app")
def connect_app_cmd(app_name: str = typer.Argument(..., help="App to connect")):
    """🔗 Connect to an app (gmail, slack, shopify...)"""
    from kurt.hub import composio_connect
    composio_connect(app_name)


def run():
    """Entry point para sa CLI"""
    app()


if __name__ == "__main__":
    run()
