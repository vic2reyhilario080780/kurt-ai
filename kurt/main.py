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
from rich.prompt import Confirm
from rich import box

from kurt.utils.env_loader import load_env, check_setup
from kurt.core.orchestrator import analyze_task, TaskType
from kurt.core.router import ModelRouter
from kurt.core.memory import init_db, save_message, get_history
from kurt.core.persona import (
    load_persona, get_theme, get_language, get_user_name, get_icon,
    get_greeting, get_language_system_prompt, get_ai_mode,
    config_show, config_theme_wizard, config_language_wizard,
    config_name_wizard, config_icon_wizard, config_aimode_wizard,
    config_projects_wizard, config_full_wizard, reset_persona,
    BUILTIN_THEMES, SUPPORTED_LANGUAGES,
)
from kurt.skills.manager import list_skills, install_skill, remove_skill, \
    create_skill_template, get_skill_prompt, list_engineering_skills
from kurt.plugins.manager import list_plugins, enable_plugin, disable_plugin
from kurt.core.projects import (
    list_projects, add_project, remove_project, note_project,
    get_active_project_contexts,
)
from kurt.core.artifacts import (
    list_artifacts, show_artifact, clean_artifacts, save_artifact, open_artifact
)
from kurt.core.scheduler import (
    list_schedules, add_schedule, remove_schedule, run_schedule, toggle_schedule
)

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
hub_app = typer.Typer(help="🌐 Universal Hub — aitmpl.com, Composio, MCPs, n8n, Zapier")
connect_app = typer.Typer(help="🔌 Connect apps via Composio (250+ apps)")
models_app = typer.Typer(help="🤖 OpenRouter — 200+ live AI models")

config_app = typer.Typer(help="🎨 Personalize KURT — themes, language, name, greeting")
project_app = typer.Typer(help="📁 Manage projects with AI context")
artifact_app = typer.Typer(help="📦 Manage AI-generated code artifacts")
schedule_app = typer.Typer(help="⏰ Schedule recurring KURT tasks")

app.add_typer(skill_app, name="skill")
app.add_typer(plugin_app, name="plugin")
app.add_typer(mcp_app, name="mcp")
app.add_typer(hub_app, name="hub")
app.add_typer(connect_app, name="connect")
app.add_typer(models_app, name="models")
app.add_typer(config_app, name="config")
app.add_typer(project_app, name="project")
app.add_typer(artifact_app, name="artifact")
app.add_typer(schedule_app, name="schedule")

KURT_ASCII = """
 ██╗  ██╗██╗   ██╗██████╗ ████████╗
 ██║ ██╔╝██║   ██║██╔══██╗╚══██╔══╝
 █████╔╝ ██║   ██║██████╔╝   ██║
 ██╔═██╗ ██║   ██║██╔══██╗   ██║
 ██║  ██╗╚██████╔╝██║  ██║   ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝
"""


def print_banner():
    """Dynamic themed banner using persona settings"""
    theme = get_theme()
    persona = load_persona()
    icon = get_icon()
    kurt_name = persona.get("kurt_name", "KURT")
    greeting = get_greeting()
    lang = get_language()
    projects = persona.get("active_projects", [])
    ai_mode = persona.get("ai_mode", "hybrid")

    color = theme["banner_color"]
    border = theme["border"]

    console.print(f"[{color}]{KURT_ASCII}[/{color}]")

    # Subtitle line
    mode_badge = {
        "hybrid": "⚡ KURT × Claude",
        "kurt_only": "🤖 KURT Engine",
        "claude_only": "🧠 Claude Mode",
    }.get(ai_mode, "⚡ KURT × Claude")

    console.print(f"[{theme['secondary']}]  Kinetic Unified Response Terminal[/{theme['secondary']}]  [{theme['dim']}]{mode_badge}[/{theme['dim']}]")
    console.print(f"[{theme['dim']}]  {lang['flag']} {lang['name']}  ·  v2.3[/{theme['dim']}]")

    # Greeting
    console.print(f"\n  {icon} [{color}]{greeting}[/{color}]")

    # Active projects
    if projects:
        proj_str = "  ".join(f"[{theme['accent']}]{p}[/{theme['accent']}]" for p in projects)
        console.print(f"\n  [{theme['dim']}]📁 Projects:[/{theme['dim']}] {proj_str}")

    console.print(f"\n  [{theme['dim']}]Type [{theme['secondary']}]kurt --help[/{theme['secondary']}] for commands  ·  [{theme['secondary']}]kurt config[/{theme['secondary']}] to personalize[/{theme['dim']}]\n")


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

    # Hybrid mode: override provider based on ai_mode
    ai_mode = get_ai_mode()
    if ai_mode == "hybrid":
        # KURT classifies (already done), Claude handles generation for text tasks
        text_tasks = {TaskType.CODE, TaskType.CHAT, TaskType.WRITE, TaskType.RESEARCH,
                      TaskType.MATH, TaskType.TRANSLATE, TaskType.DESIGN, TaskType.ARTIFACT,
                      TaskType.GAME, TaskType.UNKNOWN}
        if analysis.task_type in text_tasks:
            analysis.provider = "anthropic"
            analysis.model = "claude-3-5-haiku-20241022"
            if verbose:
                console.print(f"[dim]⚡ Hybrid mode: routing to Claude Anthropic[/dim]")
    elif ai_mode == "claude_only":
        analysis.provider = "anthropic"
        analysis.model = "claude-3-5-sonnet-20241022"
        if verbose:
            console.print(f"[dim]🧠 Claude-only mode[/dim]")
    # kurt_only: no override, use ROUTING_TABLE as-is

    # Build messages
    messages = []

    # Language system prompt — always inject first
    lang_prompt = get_language_system_prompt()
    if lang_prompt:
        messages.append({"role": "system", "content": lang_prompt})

    # Inject active project contexts
    persona = load_persona()
    active_projects = persona.get("active_projects", [])
    if active_projects:
        proj_ctx = get_active_project_contexts(active_projects)
        if proj_ctx:
            messages.append({
                "role": "system",
                "content": f"ACTIVE PROJECTS CONTEXT:\n{proj_ctx}"
            })
            if verbose:
                console.print(f"[dim]📁 Injecting context for: {', '.join(active_projects)}[/dim]")

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
        prompt=prompt,
    ))


async def stream_response(analysis, messages, session_id, no_memory, verbose, prompt=""):
    """Stream AI response with real-time display"""
    router = ModelRouter()

    # Show model info (compact)
    if not verbose:
        ai_badge = "⚡ hybrid" if get_ai_mode() == "hybrid" else get_ai_mode()
        console.print(
            f"[dim]🤖 {analysis.model} · {analysis.task_type.value} · {ai_badge}[/dim]"
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

    # Auto-save code artifacts for CODE/DESIGN/ARTIFACT tasks
    if full_response and analysis.task_type in {TaskType.CODE, TaskType.DESIGN, TaskType.ARTIFACT, TaskType.GAME}:
        saved = save_artifact(prompt or "kurt-output", full_response, analysis.task_type.value)
        if saved:
            for p in saved:
                console.print(f"[dim]📦 Saved artifact: {p}[/dim]")

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
# MODELS SUBCOMMANDS — OpenRouter live
# ══════════════════════════════════════

@models_app.callback(invoke_without_command=True)
def models_callback(ctx: typer.Context):
    """🤖 OpenRouter — browse 200+ live AI models with real-time pricing"""
    if ctx.invoked_subcommand is None:
        from kurt.models.openrouter import models_list
        models_list()


@models_app.command("list")
def models_list_cmd(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Filter by name/ID"),
    free: bool = typer.Option(False, "--free", "-f", help="Show free models only"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    limit: int = typer.Option(30, "--limit", "-n", help="Max results"),
):
    """📋 List all 200+ OpenRouter models with pricing"""
    from kurt.models.openrouter import models_list
    models_list(search=search, free_only=free, provider=provider, limit=limit)


@models_app.command("free")
def models_free_cmd():
    """🆓 Show libre/free models only"""
    from kurt.models.openrouter import models_free
    models_free()


@models_app.command("stats")
def models_stats_cmd():
    """📊 Show model stats — total, free, by provider"""
    from kurt.models.openrouter import models_stats
    models_stats()


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

        # Language prompt
        lang_prompt = get_language_system_prompt()
        if lang_prompt:
            messages.append({"role": "system", "content": lang_prompt})

        if skill:
            skill_prompt = get_skill_prompt(skill)
            if skill_prompt:
                messages.append({"role": "system", "content": skill_prompt})

        history = get_history(session_id)
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        save_message(session_id, "user", prompt)
        _theme = get_theme()
        _persona = load_persona()
        _kurt_name = _persona.get("kurt_name", "KURT")
        _icon = get_icon()
        console.print(f"\n[{_theme['primary']}]{_icon} {_kurt_name}[/{_theme['primary']}] [{_theme['dim']}]({analysis.model}):[/{_theme['dim']}]")

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


@skill_app.command("eng")
def skill_engineering(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (agentic, security, frontend, backend, cloud_devops, testing, ai_ml, mobile, data, observability, enterprise, workflow_automation, documentation)"),
):
    """Browse 1,203 Engineering skills from Claude's marketplace"""
    list_engineering_skills(domain=domain, search=search)


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
    limit: int = typer.Option(20, "--limit", "-n", help="Max results (default 20)"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all results"),
):
    """🧠 Browse 909 skills from aitmpl.com"""
    from kurt.hub import hub_list
    hub_list(component_type="skills", search=search, limit=limit, show_all=show_all)


@hub_app.command("agents")
def hub_agents(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results (default 20)"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all results"),
):
    """🤖 Browse 422 AI agents from aitmpl.com"""
    from kurt.hub import hub_list
    hub_list(component_type="agents", search=search, limit=limit, show_all=show_all)


@hub_app.command("commands")
def hub_commands(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results (default 20)"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all results"),
):
    """⚡ Browse 288 slash commands from aitmpl.com"""
    from kurt.hub import hub_list
    hub_list(component_type="commands", search=search, limit=limit, show_all=show_all)


@hub_app.command("mcp")
def hub_mcp(
    search: Optional[str] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results (default 20)"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all results"),
):
    """🔌 Browse 111 MCPs (aitmpl) + 500 community MCPs"""
    from kurt.hub import hub_list, mcp_list
    hub_list(component_type="mcps", search=search, limit=limit, show_all=show_all)
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


@hub_app.command("zapier")
def hub_zapier(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search apps by name"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all results"),
):
    """⚡ Browse 9,000+ Zapier app automations"""
    from kurt.hub.mcp_servers import zapier_list
    zapier_list(search=search, category=category, show_all=show_all)


@hub_app.command("gpts")
def hub_gpts(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search plugins"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """🤖 Browse ChatGPT Plugins & GPT Actions catalog"""
    from kurt.hub.mcp_servers import gpt_plugins_list
    gpt_plugins_list(search=search, category=category)


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


# ══════════════════════════════════════
# CONFIG SUBCOMMANDS — Personalization
# ══════════════════════════════════════

@config_app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context):
    """🎨 Personalize KURT — themes, language, name, greeting, AI mode"""
    if ctx.invoked_subcommand is None:
        config_show()
        console.print(f"\n[dim]Run [cyan]kurt config setup[/cyan] for full wizard[/dim]")
        console.print(f"[dim]Or use: kurt config theme / language / name / icon / aimode / projects[/dim]")


@config_app.command("show")
def config_show_cmd():
    """📋 Show current persona settings"""
    config_show()


@config_app.command("setup")
def config_setup_cmd():
    """🧙 Full personalization wizard — theme, language, name, icon, AI mode"""
    config_full_wizard()


@config_app.command("theme")
def config_theme_cmd():
    """🎨 Change color theme — cyber, neon, matrix, gold, minimal, sunset, ocean, pinoy"""
    config_theme_wizard()


@config_app.command("language")
def config_language_cmd():
    """🌐 Set output language — en, tl, taglish, ja, zh, es, ko"""
    config_language_wizard()


@config_app.command("name")
def config_name_cmd():
    """👤 Set your name, KURT's name, and greeting style"""
    config_name_wizard()


@config_app.command("icon")
def config_icon_cmd():
    """🎯 Change KURT's icon"""
    config_icon_wizard()


@config_app.command("aimode")
def config_aimode_cmd():
    """🤖 Set AI mode — hybrid (KURT+Claude), kurt_only, claude_only"""
    config_aimode_wizard()


@config_app.command("projects")
def config_projects_cmd():
    """📁 Set active projects for context in banner"""
    config_projects_wizard()


@config_app.command("reset")
def config_reset_cmd():
    """♻️  Reset all persona settings to defaults"""
    if Confirm.ask("Reset lahat ng persona settings sa default?"):
        reset_persona()
        console.print("[bold green]✅ Persona reset to defaults![/bold green]")
    else:
        console.print("[dim]Cancelled.[/dim]")


@config_app.command("lang")
def config_lang_shortcut():
    """🌐 Shortcut para sa language — same as 'kurt config language'"""
    config_language_wizard()


# ══════════════════════════════════════
# PROJECT SUBCOMMANDS
# ══════════════════════════════════════

@project_app.callback(invoke_without_command=True)
def project_callback(ctx: typer.Context):
    """📁 Manage projects with AI-aware context injection"""
    if ctx.invoked_subcommand is None:
        list_projects()


@project_app.command("list")
def project_list_cmd():
    """📋 List all projects"""
    list_projects()


@project_app.command("add")
def project_add_cmd():
    """➕ Add a new project"""
    add_project()


@project_app.command("remove")
def project_remove_cmd(name: str = typer.Argument(..., help="Project name")):
    """🗑️  Remove a project"""
    remove_project(name)


@project_app.command("note")
def project_note_cmd(
    name: str = typer.Argument(..., help="Project name"),
    note: str = typer.Argument(..., help="Note to add"),
):
    """📝 Add a note to a project"""
    note_project(name, note)


# ══════════════════════════════════════
# ARTIFACT SUBCOMMANDS
# ══════════════════════════════════════

@artifact_app.callback(invoke_without_command=True)
def artifact_callback(ctx: typer.Context):
    """📦 View and manage AI-generated code artifacts"""
    if ctx.invoked_subcommand is None:
        list_artifacts()


@artifact_app.command("list")
def artifact_list_cmd(limit: int = typer.Option(20, "--limit", "-n")):
    """📋 List saved artifacts"""
    list_artifacts(limit=limit)


@artifact_app.command("show")
def artifact_show_cmd(artifact_id: str = typer.Argument(..., help="Artifact ID or filename prefix")):
    """👁️  Show artifact contents"""
    show_artifact(artifact_id)


@artifact_app.command("open")
def artifact_open_cmd(artifact_id: str = typer.Argument(..., help="Artifact ID")):
    """📂 Show artifact file path (open in editor)"""
    path = open_artifact(artifact_id)
    if path:
        console.print(f"[cyan]{path}[/cyan]")
    else:
        console.print(f"[red]Artifact '{artifact_id}' not found.[/red]")


@artifact_app.command("clean")
def artifact_clean_cmd(keep: int = typer.Option(50, "--keep", help="Number to keep")):
    """🧹 Clean old artifacts"""
    clean_artifacts(keep=keep)


# ══════════════════════════════════════
# SCHEDULE SUBCOMMANDS
# ══════════════════════════════════════

@schedule_app.callback(invoke_without_command=True)
def schedule_callback(ctx: typer.Context):
    """⏰ Schedule recurring KURT tasks"""
    if ctx.invoked_subcommand is None:
        list_schedules()


@schedule_app.command("list")
def schedule_list_cmd():
    """📋 List all scheduled tasks"""
    list_schedules()


@schedule_app.command("add")
def schedule_add_cmd():
    """➕ Add a new scheduled task"""
    add_schedule()


@schedule_app.command("remove")
def schedule_remove_cmd(task_id: str = typer.Argument(..., help="Task ID")):
    """🗑️  Remove a scheduled task"""
    remove_schedule(task_id)


@schedule_app.command("run")
def schedule_run_cmd(task_id: str = typer.Argument(..., help="Task ID to run now")):
    """▶️  Run a scheduled task immediately"""
    load_env()
    task_prompt = run_schedule(task_id)
    if task_prompt:
        # Execute the prompt via ask
        analysis = analyze_task(task_prompt)
        ai_mode = get_ai_mode()
        if ai_mode in ("hybrid", "claude_only"):
            analysis.provider = "anthropic"
            analysis.model = "claude-3-5-haiku-20241022"
        messages = []
        lang_prompt = get_language_system_prompt()
        if lang_prompt:
            messages.append({"role": "system", "content": lang_prompt})
        messages.append({"role": "user", "content": task_prompt})
        asyncio.run(stream_response(
            analysis=analysis, messages=messages,
            session_id="schedule-run", no_memory=True, verbose=False, prompt=task_prompt
        ))


@schedule_app.command("toggle")
def schedule_toggle_cmd(task_id: str = typer.Argument(..., help="Task ID")):
    """⏸/▶️  Pause or resume a task"""
    toggle_schedule(task_id)


# ══════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════

def run():
    """Entry point para sa CLI"""
    app()


if __name__ == "__main__":
    run()
