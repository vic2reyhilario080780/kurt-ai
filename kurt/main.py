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
    create_skill_template, get_skill_prompt, list_engineering_skills, list_code_skills, \
    list_files_docs_skills, list_designs_media_skills, list_pipelines_jobs_skills, \
    list_tickets_tasks_skills, list_notes_memory_skills, list_apis_skills, \
    list_reference_docs_skills, list_ai_models_agents_skills, list_websites_skills, \
    list_servers_cloud_skills, list_contacts_leads_skills, list_databases_skills, \
    list_finance_skills, list_marketing_skills, list_logs_errors_skills, \
    list_email_messages_skills, list_pull_requests_skills, \
    list_sales_skills, list_operations_skills, list_product_skills, list_research_skills, \
    list_dependencies_skills, list_learning_skills, list_data_skills, \
    list_financial_services_skills, list_design_skills, list_legal_skills, \
    list_jobs_career_skills, list_it_security_skills, list_retail_ecommerce_skills, \
    list_hr_skills, list_music_skills, list_personal_finance_skills, list_events_skills, \
    list_healthcare_skills, list_customer_support_skills, list_writing_skills, \
    list_puzzles_skills, list_travel_skills, list_health_fitness_skills, list_games_skills, \
    list_shopping_skills, list_government_skills, list_family_relationships_skills, \
    list_media_entertainment_skills, list_education_skills, list_food_skills, \
    list_sports_skills, list_faith_skills, list_home_skills, list_travel_hospitality_skills, \
    list_books_skills, list_nonprofit_skills
from kurt.plugins.manager import list_plugins, enable_plugin, disable_plugin
from kurt.core.cli_orchestrator import handle_slash, SLASH_COMMANDS
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
from kurt.core.file_ops import (
    read_file, list_dir, apply_edit, write_new_file, run_file, run_code_string
)
from kurt.core.codebase import (
    index_codebase, show_index_summary, get_git_diff, get_git_log,
    parse_diff_stats, build_diff_review_prompt, get_codebase_context
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
    session: Optional[str] = typer.Option(None, "--session", help="Continue an existing session ID"),
):
    """💬 Interactive chat mode — mag-usap sa KURT"""
    load_env()
    init_db()

    _persona = load_persona()
    _kurt_name = _persona.get("kurt_name", "KURT")
    _icon = get_icon()
    _theme = get_theme()

    session_id = session if session else str(uuid.uuid4())
    current_model = model or "auto"
    current_skill = skill
    last_response = ""

    # ── Welcome banner ──────────────────────────────────────────────
    console.print(Panel(
        f"[bold cyan]{_icon} {_kurt_name} — Interactive Chat Mode[/bold cyan]\n"
        "[dim]Type [bold]/help[/bold] for slash commands  ·  [bold]/exit[/bold] to quit[/dim]\n"
        f"[dim]Session: {session_id[:8]}  ·  Model: {current_model}  ·  Skill: {current_skill or 'none'}[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
    ))
    console.print("[dim]💡 Slash commands: /claude  /gemini  /gh  /run  /model  /skill  /save  /help[/dim]\n")

    while True:
        # ── Input ────────────────────────────────────────────────────
        try:
            prompt = console.input(f"[bold cyan]You[/bold cyan] [dim]›[/dim] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]👋 Bye![/dim]")
            break

        if not prompt:
            continue

        # Legacy text shortcuts
        if prompt.lower() in ["exit", "quit", "bye"]:
            console.print("[dim]👋 Bye! K.U.R.T. signing off.[/dim]")
            break

        if prompt.lower() == "clear":
            session_id = str(uuid.uuid4())
            console.print(f"[dim]🆕 New session: {session_id[:8]}[/dim]")
            continue

        # ── Slash command handler ────────────────────────────────────
        slash_result = handle_slash(
            prompt=prompt,
            session_id=session_id,
            current_model=current_model,
            current_skill=current_skill,
            last_response=last_response,
        )

        if slash_result.handled:
            if slash_result.output:
                console.print(slash_result.output)
            if slash_result.model_override:
                current_model = slash_result.model_override
                console.print(f"[dim]Model set to: {current_model}[/dim]")
            if not slash_result.continue_chat:
                break
            continue

        # ── Intent Detection ─────────────────────────────────────────
        # Detect if the user typed a task/command (Taglish supported)
        # e.g. "buksan ang spotify", "open spotify", "screenshot"
        try:
            from kurt.core.intent import detect_intent, route_intent
            from kurt.core.intent import INTENT_TASK, INTENT_SEARCH, INTENT_MEMORY, INTENT_CHAT

            # Layer 1+2: keywords+regex (instant). Layer 3: Ollama LLM if ambiguous.
            intent = detect_intent(prompt, use_llm=True)

            if intent.type == INTENT_TASK and intent.confidence >= 0.75:
                # Execute computer/browser action directly — no LLM call needed
                routed = route_intent(intent)
                handler = routed.get("handler", "")
                kwargs = routed.get("kwargs", {})

                console.print(
                    f"\n[bold green]🤖 Kurt[/bold green] [dim](intent: {intent.action} · {intent.confidence:.0%})[/dim]"
                )

                try:
                    if handler == "computer.open_app":
                        from kurt.core.behavior import smart_open_app
                        import re as _re
                        # If LLM detected the intent, trust its target directly (already clean)
                        if intent.detected_by == "llm":
                            clean_name = intent.target.strip()
                        else:
                            # Regex/keyword path: clean up particles manually
                            raw_name = kwargs.get("app_name", intent.target or "")
                            clean_name = raw_name
                            for _ in range(2):
                                clean_name = _re.sub(
                                    r'^(?:naman|po|nga|daw|raw|pala|na|lang|ang|ng|si|mo|ko)\s+',
                                    '', clean_name, flags=_re.IGNORECASE
                                ).strip()
                            clean_name = _re.sub(
                                r'\s+(?:sa\s+(?:aking|iyong|browser|phone|pc|laptop|computer|imac|mac)|'
                                r'in\s+my|on\s+my|using|via|please|pls|na|ngayon|now)\b.*$',
                                '', clean_name, flags=_re.IGNORECASE
                            ).strip()
                        # Use smart_open_app — multi-layer diskarte ni Kurt
                        result = smart_open_app(clean_name)
                        if result.success:
                            method_note = f" [dim]({result.method_used})[/dim]" if result.method_used not in ("open -a", "cached") else ""
                            console.print(f"[green]✓[/green] {result.message}{method_note}")
                        else:
                            console.print(f"[yellow]⚠[/yellow] {result.message}")

                    elif handler == "browser.navigate":
                        from kurt.core.computer_use import open_url
                        result = open_url(kwargs.get("url", ""))
                        if result.success:
                            console.print(f"[green]✓[/green] Binuksan ang URL: [bold]{kwargs.get('url')}[/bold]")
                        else:
                            console.print(f"[yellow]⚠[/yellow] {result.message}")

                    elif handler == "browser.search_web":
                        from kurt.core.computer_use import open_url
                        import urllib.parse
                        query = kwargs.get("query", prompt)
                        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                        result = open_url(url)
                        if result.success:
                            console.print(f"[green]✓[/green] Naghanap: [bold]{query}[/bold]")
                        else:
                            console.print(f"[yellow]⚠[/yellow] {result.message}")

                    elif handler == "computer.screenshot":
                        from kurt.core.computer_use import screenshot
                        result = screenshot()
                        if result.success:
                            console.print(f"[green]✓[/green] Screenshot saved: [dim]{result.data}[/dim]")
                        else:
                            console.print(f"[yellow]⚠[/yellow] {result.message}")

                    elif handler == "computer.type_text":
                        from kurt.core.computer_use import type_text
                        result = type_text(kwargs.get("text", ""))
                        if result.success:
                            console.print(f"[green]✓[/green] Na-type ang text.")
                        else:
                            console.print(f"[yellow]⚠[/yellow] {result.message}")

                    else:
                        # Unknown handler — fall through to LLM
                        raise ValueError(f"Unknown handler: {handler}")

                    # Log to habit memory
                    try:
                        from kurt.core.habit_memory import log_interaction
                        log_interaction(prompt, handler, True)
                    except Exception:
                        pass

                    continue  # Skip LLM call

                except Exception as e:
                    # Action failed — tell user and fall through to LLM
                    console.print(f"[dim]⚡ Direct action failed ({e}), asking AI instead...[/dim]")

        except ImportError:
            pass  # Intent module not available — skip silently

        # ── AI Chat ──────────────────────────────────────────────────
        analysis = analyze_task(prompt)
        if current_model != "auto":
            analysis.model = current_model

        messages = []

        # System prompt: KURT persona
        kurt_system = (
            f"You are {_kurt_name}, a smart, friendly AI assistant built by Daddy Tito. "
            "You communicate in Taglish (Tagalog-English mix) unless asked otherwise. "
            "You are helpful, honest, and efficient. "
            "You are running as a CLI tool called KURT — Kinetic Unified Response Terminal. "
            "Keep responses concise and practical."
        )
        messages.append({"role": "system", "content": kurt_system})

        # Language prompt
        lang_prompt = get_language_system_prompt()
        if lang_prompt:
            messages.append({"role": "system", "content": lang_prompt})

        # Skill prompt
        active_skill = current_skill
        if prompt.startswith("/skill "):
            # Inline skill override
            active_skill = prompt.split(None, 1)[1].strip()
        if active_skill:
            skill_prompt = get_skill_prompt(active_skill)
            if skill_prompt:
                messages.append({"role": "system", "content": skill_prompt})

        history = get_history(session_id, limit=20)
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        save_message(session_id, "user", prompt)

        console.print(
            f"\n[{_theme['primary']}]{_icon} {_kurt_name}[/{_theme['primary']}] "
            f"[dim]({analysis.model} · {analysis.task_type.value})[/dim]"
        )

        asyncio.run(stream_response(
            analysis=analysis,
            messages=messages,
            session_id=session_id,
            no_memory=False,
            verbose=False,
            prompt=prompt,
        ))

        # Store last response for /save
        from kurt.core.memory import get_history as _gh
        _hist = _gh(session_id, limit=1)
        if _hist and _hist[-1]["role"] == "assistant":
            last_response = _hist[-1]["content"]


# ══════════════════════════════════════
# VOICE COMMAND — "Hey Kurt"
# ══════════════════════════════════════

@app.command()
def voice(
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    speak: bool = typer.Option(True, "--speak/--no-speak", help="Text-to-speech responses"),
    hotkey_only: bool = typer.Option(False, "--hotkey", help="Hotkey only (no mic listening)"),
):
    """🎤 Voice mode — say 'Hey Kurt' to activate (Ctrl+Shift+K as fallback)"""
    load_env()
    init_db()

    _persona = load_persona()
    _kurt_name = _persona.get("kurt_name", "KURT")
    session_id = str(uuid.uuid4())

    console.print(Panel(
        f"[bold cyan]🎤 {_kurt_name} — Voice Mode[/bold cyan]\n"
        "[dim]Say 'Hey Kurt' or press [bold]Ctrl+Shift+K[/bold] to activate\n"
        "Press Ctrl+C to exit[/dim]",
        box=box.ROUNDED, border_style="cyan"
    ))

    # Check voice dependencies
    try:
        from kurt.core.wake_word import check_dependencies, start_listening, speak as kurt_speak
        deps = check_dependencies()

        if not deps.get("can_record"):
            console.print("[yellow]⚠ Microphone not available. Install: pip install sounddevice soundfile[/yellow]")
            console.print("[dim]Running in hotkey-only mode (Ctrl+Shift+K)[/dim]")
            hotkey_only = True

        if not deps.get("can_transcribe"):
            console.print("[yellow]⚠ STT not available. Install: pip install faster-whisper[/yellow]")
            if not hotkey_only:
                console.print("[red]Cannot run voice mode without STT.[/red]")
                return

    except ImportError:
        console.print("[red]❌ Voice module not available.[/red]")
        return

    def handle_voice_command(event):
        """Process a voice command through Kurt's AI"""
        text = event.text.strip()
        if not text:
            return

        console.print(f"\n[bold cyan]You[/bold cyan] [dim](voice)[/dim]: {text}")

        # Detect if it's a computer action (open app, etc.)
        try:
            from kurt.core.intent import detect_intent, route_intent, INTENT_TASK
            intent = detect_intent(text, use_llm=True)

            if intent.type == INTENT_TASK and intent.confidence >= 0.75:
                routed = route_intent(intent)
                handler = routed.get("handler", "")
                kwargs = routed.get("kwargs", {})

                from kurt.core.agent_loop import execute_tool
                tool_map = {
                    "computer.open_app": ("open_app", {"app_name": kwargs.get("app_name", intent.target)}),
                    "browser.navigate": ("open_url", {"url": kwargs.get("url", "")}),
                    "computer.screenshot": ("screenshot", {}),
                }

                if handler in tool_map:
                    tool_name, tool_params = tool_map[handler]
                    result = execute_tool(tool_name, tool_params)
                    reply = result.replace("✓ ", "").replace("❌ ", "")
                    console.print(f"[bold green]🤖 {_kurt_name}[/bold green]: {reply}")
                    if speak:
                        kurt_speak(reply, blocking=False)
                    return
        except Exception:
            pass

        # Send to AI for natural response
        analysis = analyze_task(text)
        if model:
            analysis.model = model

        messages = [
            {"role": "system", "content": (
                f"You are {_kurt_name}, a voice assistant. "
                "Give SHORT responses (1-2 sentences max) suitable for text-to-speech. "
                "Speak naturally in Taglish."
            )},
            {"role": "user", "content": text},
        ]

        # Get AI response synchronously
        import asyncio as _asyncio
        full_response = ""

        async def _get_response():
            nonlocal full_response
            router = ModelRouter()
            async for chunk in router.route(
                provider=analysis.provider,
                model=analysis.model,
                messages=messages,
            ):
                full_response += chunk

        try:
            _asyncio.run(_get_response())
        except Exception as e:
            full_response = f"Sorry, may error: {e}"

        console.print(f"\n[bold green]🤖 {_kurt_name}[/bold green]: {full_response}")

        if speak and full_response:
            kurt_speak(full_response, blocking=False)

        save_message(session_id, "user", text)
        save_message(session_id, "assistant", full_response)

    # Start the voice listener
    console.print("[dim]Starting voice listener...[/dim]")
    try:
        from kurt.core.wake_word import start_listening, speak as kurt_speak
        listener = start_listening(callback=handle_voice_command)
        kurt_speak(f"Hey! {_kurt_name} voice mode activated. Say hey Kurt anytime!", blocking=False)
        console.print(f"[green]✓ Voice mode active![/green] [dim]Listening for 'Hey Kurt'...[/dim]")

        # Keep running
        import time
        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        console.print("\n[dim]Voice mode stopped.[/dim]")
    except Exception as e:
        console.print(f"[red]❌ Voice mode error: {e}[/red]")


# ══════════════════════════════════════
# DO COMMAND — Agent + Computer Use
# ══════════════════════════════════════

@app.command()
def do(
    task: str = typer.Argument(..., help="Task for Kurt to execute with computer control"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    max_steps: int = typer.Option(15, "--max-steps", help="Max steps"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """🖱️ Do a computer task — Kurt will click, type, open apps as needed"""
    load_env()
    init_db()

    console.print(Panel(
        f"[bold cyan]🖱️ Computer Task[/bold cyan]\n"
        f"[dim]{task}[/dim]",
        box=box.ROUNDED, border_style="cyan"
    ))

    from kurt.core.agent_loop import run_agent
    router = ModelRouter()

    # For computer tasks, use Ollama local model (libre) or best available
    analysis = analyze_task(task)
    if not model:
        # Try local Ollama first (libre, no cost)
        try:
            import requests
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.ok:
                models_list = [m["name"] for m in r.json().get("models", [])]
                # Prefer llama3.2 or similar for tasks
                for preferred in ["llama3.2", "llama3.1", "llama3", "mistral", "gemma"]:
                    if any(preferred in m for m in models_list):
                        analysis.model = next(m for m in models_list if preferred in m)
                        analysis.provider = "ollama"
                        break
        except Exception:
            pass
    else:
        analysis.model = model

    result = asyncio.run(run_agent(
        task=task,
        analysis=analysis,
        router=router,
        cwd=".",
        max_steps=max_steps,
        verbose=verbose,
    ))

    if result.success:
        console.print(f"\n[bold green]✅ Done![/bold green] {result.final_summary}")
    else:
        console.print(f"\n[yellow]⚠ Task incomplete after {len(result.steps)} steps[/yellow]")


# ══════════════════════════════════════
# PHASE 2 — FILE COMMANDS
# ══════════════════════════════════════

@app.command()
def read(
    path: str = typer.Argument(..., help="File path to read"),
    lines: Optional[str] = typer.Option(None, "--lines", "-l", help="Line range e.g. '10-25' or '10'"),
    ask: Optional[str] = typer.Option(None, "--ask", "-a", help="Ask AI a question about this file"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
):
    """📖 Read a file — with optional AI analysis"""
    load_env()
    content = read_file(path, lines)
    console.print(content)

    if ask:
        init_db()
        from kurt.core.file_ops import read_file_summary
        file_info = read_file_summary(path)
        if "error" in file_info:
            console.print(f"[red]{file_info['error']}[/red]")
            return
        analysis = analyze_task(ask)
        if model:
            analysis.model = model
        session_id = str(uuid.uuid4())
        messages = [
            {"role": "system", "content": "You are KURT, an expert code reviewer. Be concise and practical."},
            {"role": "user", "content": f"File: {file_info['path']}\n\n```{file_info['ext']}\n{file_info['content'][:6000]}\n```\n\nQuestion: {ask}"},
        ]
        _theme = get_theme()
        console.print(f"\n[{_theme['primary']}]🤖 KURT[/{_theme['primary']}] [dim]({analysis.model}):[/dim]")
        asyncio.run(stream_response(
            analysis=analysis, messages=messages,
            session_id=session_id, no_memory=True, verbose=False, prompt=ask,
        ))


@app.command()
def edit(
    path: str = typer.Argument(..., help="File to edit"),
    instruction: str = typer.Argument(..., help="What to change, in plain English"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only — don't write"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """✏️  AI-powered file editing — describe what to change"""
    load_env()
    init_db()

    from kurt.core.file_ops import read_file_summary, apply_edit
    file_info = read_file_summary(path)
    if "error" in file_info:
        console.print(f"[red]{file_info['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]📄 {file_info['name']}[/cyan] [dim]({file_info['lines']} lines)[/dim]")
    console.print(f"[dim]Instruction: {instruction}[/dim]\n")

    # Ask AI to generate the edit as old_str/new_str
    edit_prompt = (
        f"You must edit this file. Return ONLY a JSON object with 'old_str' and 'new_str' keys.\n"
        f"old_str: exact text from the file to replace (must be unique)\n"
        f"new_str: the replacement text\n\n"
        f"File: {file_info['path']}\n"
        f"Instruction: {instruction}\n\n"
        f"File content:\n```{file_info['ext']}\n{file_info['content'][:6000]}\n```\n\n"
        f"Return ONLY this JSON format (no explanation):\n"
        f'{{"old_str": "...", "new_str": "..."}}'
    )

    analysis = analyze_task(instruction)
    if model:
        analysis.model = model
    # Force to code-capable model
    if analysis.model not in ("deepseek/deepseek-coder", "anthropic/claude-3.5-sonnet"):
        analysis.model = "deepseek/deepseek-coder"
        analysis.provider = "openrouter"

    session_id = str(uuid.uuid4())
    messages = [
        {"role": "system", "content": "You are a precise code editor. Output only valid JSON."},
        {"role": "user", "content": edit_prompt},
    ]

    console.print("[dim]🤖 Generating edit…[/dim]")
    full_response = ""

    async def _get_edit():
        nonlocal full_response
        from kurt.core.router import ModelRouter
        router = ModelRouter()
        async for chunk in router.route(provider=analysis.provider, model=analysis.model, messages=messages):
            full_response += chunk

    asyncio.run(_get_edit())

    # Parse JSON from response
    import json as _json
    json_match = re.search(r'\{[^{}]*"old_str"[^{}]*\}', full_response, re.DOTALL)
    if not json_match:
        console.print("[red]❌ AI did not return valid JSON edit.[/red]")
        console.print(f"[dim]{full_response[:500]}[/dim]")
        raise typer.Exit(1)

    try:
        edit_data = _json.loads(json_match.group(0))
        old_str = edit_data.get("old_str", "")
        new_str = edit_data.get("new_str", "")
    except _json.JSONDecodeError as e:
        console.print(f"[red]❌ JSON parse error: {e}[/red]")
        raise typer.Exit(1)

    if not old_str:
        console.print("[red]❌ AI returned empty old_str.[/red]")
        raise typer.Exit(1)

    # Preview
    console.print(Panel(
        f"[red]- {old_str[:200]}[/red]\n[green]+ {new_str[:200]}[/green]",
        title="Proposed Edit", box=box.ROUNDED,
    ))

    if dry_run:
        console.print("[dim]Dry run — no changes written.[/dim]")
        return

    if not yes:
        if not Confirm.ask("Apply this edit?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    result = apply_edit(path, old_str, new_str)
    color = "green" if result.startswith("✅") else "red"
    console.print(f"[{color}]{result}[/{color}]")


@app.command("run")
def run_cmd(
    path: str = typer.Argument(..., help="File to execute (.py .sh .js)"),
    args: str = typer.Option("", "--args", "-a", help="Arguments to pass"),
    explain: bool = typer.Option(False, "--explain", "-e", help="Ask AI to explain the output"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
):
    """▶️  Execute a file and optionally explain the output"""
    load_env()

    console.print(f"[cyan]▶ Running {path}[/cyan] [dim]{args}[/dim]\n")
    result = run_file(path, args)

    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        raise typer.Exit(1)

    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    rc = result.get("returncode", 0)
    rt = result.get("runtime_ms", 0)

    status_color = "green" if rc == 0 else "red"
    console.print(f"[{status_color}]Exit {rc}[/{status_color}] [dim]· {rt}ms[/dim]")
    if stdout:
        console.print(stdout)
    if stderr:
        console.print(f"[yellow]{stderr}[/yellow]")

    if explain:
        init_db()
        from kurt.core.file_ops import read_file_summary
        file_info = read_file_summary(path)
        analysis = analyze_task("explain code output")
        if model:
            analysis.model = model
        session_id = str(uuid.uuid4())
        messages = [
            {"role": "system", "content": "You are KURT, an expert debugger. Explain clearly and concisely."},
            {"role": "user", "content": (
                f"File: {path}\nCode:\n```\n{file_info.get('content','')[:3000]}\n```\n\n"
                f"Output (exit {rc}):\n{stdout[:2000]}\n{stderr[:1000]}\n\n"
                f"Explain what happened and if there are any issues."
            )},
        ]
        _theme = get_theme()
        console.print(f"\n[{_theme['primary']}]🤖 KURT[/{_theme['primary']}] [dim]({analysis.model}):[/dim]")
        asyncio.run(stream_response(
            analysis=analysis, messages=messages,
            session_id=session_id, no_memory=True, verbose=False,
        ))


@app.command()
def ls(
    path: str = typer.Argument(".", help="Directory to list"),
    depth: int = typer.Option(2, "--depth", "-d", help="Tree depth 1-3"),
):
    """📁 List directory as tree"""
    console.print(list_dir(path, depth))


# ══════════════════════════════════════
# PHASE 3 — AGENT + CODEBASE + DIFF
# ══════════════════════════════════════

@app.command()
def agent(
    task: str = typer.Argument(..., help="Task for the agent to complete autonomously"),
    path: str = typer.Option(".", "--path", "-p", help="Working directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    max_steps: int = typer.Option(15, "--max-steps", help="Max agent steps (safety limit)"),
):
    """🤖 Agentic mode — multi-step AI task execution (like Claude Code!)"""
    load_env()
    init_db()

    from kurt.core.agent_loop import run_agent
    from kurt.core.router import ModelRouter

    analysis = analyze_task(task)
    # Agent mode: prefer code-capable model
    if not model:
        analysis.model = "deepseek/deepseek-coder"
        analysis.provider = "openrouter"
        analysis.fallback_model = "anthropic/claude-3.5-sonnet"
    else:
        analysis.model = model

    router = ModelRouter()
    result = asyncio.run(run_agent(
        task=task,
        analysis=analysis,
        router=router,
        cwd=str(Path(path).expanduser().resolve()),
        max_steps=max_steps,
    ))

    if result.files_changed:
        console.print(f"\n[dim]📝 Files changed: {', '.join(result.files_changed)}[/dim]")


@app.command()
def index(
    path: str = typer.Argument(".", help="Project directory to index"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-index"),
    ask: Optional[str] = typer.Option(None, "--ask", "-a", help="Ask AI about the codebase"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
):
    """🔍 Index codebase — understand project structure"""
    load_env()

    idx = index_codebase(path, force=force)
    if "error" in idx:
        console.print(f"[red]{idx['error']}[/red]")
        raise typer.Exit(1)

    show_index_summary(idx)

    if ask:
        init_db()
        context = get_codebase_context(idx, query=ask)
        analysis = analyze_task(ask)
        if model:
            analysis.model = model
        session_id = str(uuid.uuid4())
        messages = [
            {"role": "system", "content": "You are KURT, an expert software architect. Answer based on the codebase context."},
            {"role": "user", "content": f"{context}\n\nQuestion: {ask}"},
        ]
        _theme = get_theme()
        console.print(f"\n[{_theme['primary']}]🤖 KURT[/{_theme['primary']}] [dim]({analysis.model}):[/dim]")
        asyncio.run(stream_response(
            analysis=analysis, messages=messages,
            session_id=session_id, no_memory=True, verbose=False, prompt=ask,
        ))


@app.command()
def diff(
    path: str = typer.Argument(".", help="Git repo path"),
    staged: bool = typer.Option(False, "--staged", "-s", help="Review staged changes only"),
    commits: Optional[str] = typer.Option(None, "--commits", "-c", help="Commit range e.g. 'HEAD~3..HEAD'"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Focus area e.g. 'security' or 'performance'"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
):
    """🔎 AI-powered git diff review"""
    load_env()
    init_db()

    # Get diff
    diff_content = get_git_diff(path, staged_only=staged, commits=commits)
    if not diff_content.strip():
        console.print("[dim]No changes to review.[/dim]")
        return
    if diff_content.startswith("❌"):
        console.print(f"[red]{diff_content}[/red]")
        raise typer.Exit(1)

    stats = parse_diff_stats(diff_content)
    console.print(Panel(
        f"[cyan]{stats['files_changed']} files[/cyan]  "
        f"[green]+{stats['additions']}[/green] [red]-{stats['deletions']}[/red]\n"
        f"[dim]{', '.join(stats['files'][:5])}{'…' if len(stats['files']) > 5 else ''}[/dim]",
        title="📊 Diff Stats", box=box.ROUNDED,
    ))

    # Recent commits context
    log = get_git_log(path, n=3)
    if log:
        console.print(f"[dim]Recent commits:\n{log}[/dim]\n")

    # AI review
    review_prompt = build_diff_review_prompt(diff_content, focus or "")
    analysis = analyze_task("code review")
    analysis.model = model or "anthropic/claude-3-5-haiku"
    analysis.provider = "anthropic"
    analysis.fallback_model = "deepseek/deepseek-coder"
    analysis.fallback_provider = "openrouter"

    session_id = str(uuid.uuid4())
    messages = [
        {"role": "system", "content": "You are KURT, a senior code reviewer. Be direct, concise, and actionable."},
        {"role": "user", "content": review_prompt},
    ]

    _theme = get_theme()
    console.print(f"[{_theme['primary']}]🤖 KURT Code Review[/{_theme['primary']}] [dim]({analysis.model}):[/dim]\n")
    asyncio.run(stream_response(
        analysis=analysis, messages=messages,
        session_id=session_id, no_memory=True, verbose=False,
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


@skill_app.command("code")
def skill_code(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (agentic_frameworks, code_review, security, frontend, backend, cloud_devops, testing, ai_ml, mobile, data, workflow_automation, documentation, game_dev, enterprise, shopify)"),
):
    """Browse 1,104 Code skills from Claude's marketplace"""
    list_code_skills(domain=domain, search=search)


@skill_app.command("files")
def skill_files(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (document_creation, seo_marketing, resume_career, legal_compliance, memory_context, writing_editing, productivity_tools, data_spreadsheet, file_management, project_management, ai_integration, ecommerce_business)"),
):
    """Browse 850 Files & Documents skills from Claude's marketplace"""
    list_files_docs_skills(domain=domain, search=search)


@skill_app.command("designs")
def skill_designs(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (ui_ux_design, video_creation, image_generation, social_media, music_audio, presentation_slides, web_design, diagramming_visualization, brand_marketing, tools_utilities, game_creative, analytics_insights)"),
):
    """Browse 433 Designs & Media skills from Claude's marketplace"""
    list_designs_media_skills(domain=domain, search=search)


@skill_app.command("tickets")
def skill_tickets(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (project_task_management, crm_sales, legal_compliance, hr_recruiting, customer_support, finance_accounting, project_planning, communication_meetings, ecommerce_operations, monitoring_incident, productivity_tools)"),
):
    """Browse 365 Tickets & Tasks skills from Claude's marketplace"""
    list_tickets_tasks_skills(domain=domain, search=search)


@skill_app.command("notes")
def skill_notes(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (personal_knowledge_management, ai_memory_systems, note_taking_apps, learning_study, writing_content, productivity_context, career_professional, social_community, research_analysis, tools_integrations)"),
):
    """Browse 290 Notes & Memory skills from Claude's marketplace"""
    list_notes_memory_skills(domain=domain, search=search)


@skill_app.command("apis")
def skill_apis(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (payment_billing, cloud_infrastructure, developer_tools, marketing_ads, security_auth, data_analytics, communication_messaging, commerce_ecommerce, ai_ml_tools, monitoring_devops, finance_wealth, enterprise_integrations, healthcare_bio, legal_compliance)"),
):
    """Browse 346 APIs skills from Claude's marketplace"""
    list_apis_skills(domain=domain, search=search)


@skill_app.command("refdocs")
def skill_refdocs(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (legal_research, knowledge_documentation, market_research, medical_health, developer_reference, business_strategy, government_public_sector, education_learning, seo_marketing, finance_economics, productivity_tools, real_estate_property, data_analytics, niche_specialized)"),
):
    """Browse 324 Reference Docs skills from Claude's marketplace"""
    list_reference_docs_skills(domain=domain, search=search)


@skill_app.command("aiagents")
def skill_aiagents(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (agent_frameworks, claude_tools, prompt_engineering, llm_ops_monitoring, cloud_ai_platforms, ai_governance_safety, product_analytics, ml_research, enterprise_ai, chatbot_voice, developer_productivity, knowledge_memory, startup_venture, niche_specialized)"),
):
    """Browse 311 AI Models & Agents skills from Claude's marketplace"""
    list_ai_models_agents_skills(domain=domain, search=search)


@skill_app.command("websites")
def skill_websites(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (seo_tools, website_builders, testing_qa, analytics_tracking, ecommerce, content_marketing, ads_paid_media, web_scraping_data, infrastructure_hosting, chatbot_support, design_ux, portfolio_showcase, niche_specialized)"),
):
    """Browse 285 Websites skills from Claude's marketplace"""
    list_websites_skills(domain=domain, search=search)


@skill_app.command("serverscloud")
def skill_serverscloud(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (aws, gcp_azure, kubernetes_containers, databases_cache, monitoring_observability, security_devops, serverless_paas, networking_cdn, iac_automation, cloud_cost_finops, data_platforms, developer_tools, enterprise_integrations, niche_specialized)"),
):
    """Browse 251 Servers & Cloud skills from Claude's marketplace"""
    list_servers_cloud_skills(domain=domain, search=search)


@skill_app.command("contactsleads")
def skill_contactsleads(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (crm_sales, b2b_prospecting, job_search_career, marketing_outreach, financial_advisors, hr_recruiting, real_estate_property, customer_success, data_enrichment, niche_specialized)"),
):
    """Browse 246 Contacts & Leads skills from Claude's marketplace"""
    list_contacts_leads_skills(domain=domain, search=search)


@skill_app.command("databases")
def skill_databases(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (sql_relational, nosql_vector, data_warehouse_analytics, orm_migration, erp_enterprise, cloud_data_platforms, test_seed_data, niche_specialized)"),
):
    """Browse 246 Databases skills from Claude's marketplace"""
    list_databases_skills(domain=domain, search=search)


@skill_app.command("finance")
def skill_finance(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (investment_wealth, accounting_erp, payments_fintech, trading_crypto, risk_insurance, marketing_analytics, cloud_cost_ops, niche_specialized)"),
):
    """Browse 230 Finance skills from Claude's marketplace"""
    list_finance_skills(domain=domain, search=search)


@skill_app.command("marketing")
def skill_marketing(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (seo_search, paid_ads, social_media, content_seo, email_marketing, growth_analytics, creative_assets, niche_specialized)"),
):
    """Browse 221 Marketing skills from Claude's marketplace"""
    list_marketing_skills(domain=domain, search=search)


@skill_app.command("logs")
def skill_logs(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (observability_monitoring, incident_management, security_compliance, debugging_testing, infrastructure_devops, ai_agent_tools, niche_specialized)"),
):
    """Browse 200 Logs & Errors skills from Claude's marketplace"""
    list_logs_errors_skills(domain=domain, search=search)


@skill_app.command("email")
def skill_email(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (email_marketing, social_messaging, crm_sales_outreach, messaging_platforms, productivity_automation, business_communication, niche_specialized)"),
):
    """Browse 187 Email & Messages skills from Claude's marketplace"""
    list_email_messages_skills(domain=domain, search=search)


@skill_app.command("pr")
def skill_pr(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (code_review, security_audit, git_github, agile_workflow, developer_tools, ai_agent_tools, niche_specialized)"),
):
    """Browse 162 Pull Requests skills from Claude's marketplace"""
    list_pull_requests_skills(domain=domain, search=search)


@skill_app.command("sales")
def skill_sales(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (crm_pipeline, prospecting_leads, financial_advisory, sales_enablement, deals_proposals, recruiting_careers, niche_specialized)"),
):
    """Browse 84 Sales skills from Claude's marketplace"""
    list_sales_skills(domain=domain, search=search)


@skill_app.command("ops")
def skill_ops(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (erp_business_systems, project_management, meetings_productivity, supply_chain_logistics, real_estate_property, business_operations, niche_specialized)"),
):
    """Browse 94 Operations skills from Claude's marketplace"""
    list_operations_skills(domain=domain, search=search)


@skill_app.command("product")
def skill_product(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (product_management, analytics_metrics, strategy_research, ux_design, ideation_innovation, content_publishing, niche_specialized)"),
):
    """Browse 95 Product skills from Claude's marketplace"""
    list_product_skills(domain=domain, search=search)


@skill_app.command("research")
def skill_research(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (academic_research, web_research, knowledge_management, investment_research, media_content, language_translation, niche_specialized)"),
):
    """Browse 94 Research skills from Claude's marketplace"""
    list_research_skills(domain=domain, search=search)


@skill_app.command("deps")
def skill_deps(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (security_compliance, package_management, cloud_infrastructure, framework_platform, integration_automation, code_quality, niche_specialized)"),
):
    """Browse 97 Dependencies & Packages skills from Claude's marketplace"""
    list_dependencies_skills(domain=domain, search=search)


@skill_app.command("learn")
def skill_learn(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (study_productivity, tutoring_coaching, language_learning, knowledge_management, academic_research, creative_experiential, niche_specialized)"),
):
    """Browse 93 Learning skills from Claude's marketplace"""
    list_learning_skills(domain=domain, search=search)


@skill_app.command("data")
def skill_data(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (analytics_bi, data_engineering, data_quality, life_sciences, ml_ai_data, data_platforms, niche_specialized)"),
):
    """Browse 88 Data skills from Claude's marketplace"""
    list_data_skills(domain=domain, search=search)


@skill_app.command("finserv")
def skill_finserv(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (wealth_advisory, investment_research, risk_compliance, accounting_reporting, payments_fintech, fund_private_markets, niche_specialized)"),
):
    """Browse 82 Financial Services skills from Claude's marketplace"""
    list_financial_services_skills(domain=domain, search=search)


@skill_app.command("design")
def skill_design(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (ui_ux_design, figma_tools, icons_assets, design_systems, design_review, prototyping_tools, niche_specialized)"),
):
    """Browse 83 Design skills from Claude's marketplace"""
    list_design_skills(domain=domain, search=search)


@skill_app.command("legal")
def skill_legal(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (enterprise_legal, contracts_compliance, regional_eu, regional_india, litigation_courts, ip_patents, niche_specialized)"),
):
    """Browse 74 Legal skills from Claude's marketplace"""
    list_legal_skills(domain=domain, search=search)


@skill_app.command("career")
def skill_career(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (resume_cv, job_search, interview_prep, career_development, entrepreneurship, portfolio_showcase, niche_specialized)"),
):
    """Browse 64 Jobs & Career skills from Claude's marketplace"""
    list_jobs_career_skills(domain=domain, search=search)


@skill_app.command("itsec")
def skill_itsec(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (cybersecurity, governance_compliance, sector_overlays, infrastructure_ops, niche_specialized)"),
):
    """Browse 55 IT & Security skills from Claude's marketplace"""
    list_it_security_skills(domain=domain, search=search)


@skill_app.command("retail")
def skill_retail(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (shopify_ecosystem, marketplace_platforms, product_catalog, customer_engagement, analytics_operations, niche_specialized)"),
):
    """Browse 53 Retail & E-commerce skills from Claude's marketplace"""
    list_retail_ecommerce_skills(domain=domain, search=search)


@skill_app.command("hr")
def skill_hr(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (resume_recruiting, talent_acquisition, interviewing, people_operations, career_development, niche_specialized)"),
):
    """Browse 41 HR skills from Claude's marketplace"""
    list_hr_skills(domain=domain, search=search)


@skill_app.command("music")
def skill_music(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search music skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 38 Music skills from Claude's marketplace"""
    list_music_skills(domain=domain, search=search)


@skill_app.command("finance-personal")
def skill_personal_finance(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search personal finance skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 35 Personal Finance skills from Claude's marketplace"""
    list_personal_finance_skills(domain=domain, search=search)


@skill_app.command("events")
def skill_events(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search events skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 31 Events skills from Claude's marketplace"""
    list_events_skills(domain=domain, search=search)


@skill_app.command("healthcare")
def skill_healthcare(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search healthcare skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 32 Healthcare skills from Claude's marketplace"""
    list_healthcare_skills(domain=domain, search=search)


@skill_app.command("support")
def skill_customer_support(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search customer support skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 30 Customer Support skills from Claude's marketplace"""
    list_customer_support_skills(domain=domain, search=search)


@skill_app.command("writing")
def skill_writing(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search writing skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 29 Writing skills from Claude's marketplace"""
    list_writing_skills(domain=domain, search=search)


@skill_app.command("puzzles")
def skill_puzzles(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search puzzles skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 25 Puzzles skills from Claude's marketplace"""
    list_puzzles_skills(domain=domain, search=search)


@skill_app.command("travel")
def skill_travel(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search travel skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 25 Travel skills from Claude's marketplace"""
    list_travel_skills(domain=domain, search=search)


@skill_app.command("fitness")
def skill_health_fitness(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search health & fitness skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 21 Health & Fitness skills from Claude's marketplace"""
    list_health_fitness_skills(domain=domain, search=search)


@skill_app.command("games")
def skill_games(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search games skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 14 Games skills from Claude's marketplace"""
    list_games_skills(domain=domain, search=search)


@skill_app.command("shopping")
def skill_shopping(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search shopping skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 13 Shopping skills from Claude's marketplace"""
    list_shopping_skills(domain=domain, search=search)


@skill_app.command("gov")
def skill_government(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search government skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 15 Government skills from Claude's marketplace"""
    list_government_skills(domain=domain, search=search)


@skill_app.command("family")
def skill_family_relationships(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search family & relationships skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 12 Family & Relationships skills from Claude's marketplace"""
    list_family_relationships_skills(domain=domain, search=search)


@skill_app.command("media")
def skill_media_entertainment(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search media & entertainment skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 12 Media & Entertainment skills from Claude's marketplace"""
    list_media_entertainment_skills(domain=domain, search=search)


@skill_app.command("edu")
def skill_education(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search education skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 10 Education skills from Claude's marketplace"""
    list_education_skills(domain=domain, search=search)


@skill_app.command("food")
def skill_food(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search food skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 8 Food skills from Claude's marketplace"""
    list_food_skills(domain=domain, search=search)


@skill_app.command("sports")
def skill_sports(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search sports skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 8 Sports skills from Claude's marketplace"""
    list_sports_skills(domain=domain, search=search)


@skill_app.command("faith")
def skill_faith(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search faith skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 7 Faith skills from Claude's marketplace"""
    list_faith_skills(domain=domain, search=search)


@skill_app.command("home")
def skill_home(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search home skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 6 Home skills from Claude's marketplace"""
    list_home_skills(domain=domain, search=search)


@skill_app.command("hospitality")
def skill_travel_hospitality(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search travel hospitality skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 6 Travel Hospitality skills from Claude's marketplace"""
    list_travel_hospitality_skills(domain=domain, search=search)


@skill_app.command("books")
def skill_books(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search books skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 5 Books skills from Claude's marketplace"""
    list_books_skills(domain=domain, search=search)


@skill_app.command("nonprofit")
def skill_nonprofit(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search nonprofit skills"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Browse 4 Nonprofit skills from Claude's marketplace"""
    list_nonprofit_skills(domain=domain, search=search)


@skill_app.command("pipelines")
def skill_pipelines(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for a skill by name"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (ci_cd_devops, project_management, monitoring_observability, data_pipeline, cloud_infrastructure, ai_agents, testing_qa, business_automation, developer_tools, security_compliance, product_analytics, sdlc_planning)"),
):
    """Browse 368 Pipelines & Jobs skills from Claude's marketplace"""
    list_pipelines_jobs_skills(domain=domain, search=search)


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
# MCP SUBCOMMANDS (Phase 4 — full MCP tool-call loop)
# ══════════════════════════════════════

@mcp_app.command("list")
def mcp_list():
    """📋 List all saved MCP connections"""
    from kurt.core.mcp_client import show_connections
    show_connections()


@mcp_app.command("tools")
def mcp_tools(
    server: Optional[str] = typer.Argument(None, help="Server name (or all if omitted)"),
):
    """🔧 List available tools from connected MCP servers"""
    from kurt.core.mcp_client import show_tools
    asyncio.run(show_tools(server))


@mcp_app.command("add")
def mcp_add(
    name: str = typer.Argument(..., help="Unique name for this connection"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="HTTP/SSE server URL"),
    command: Optional[str] = typer.Option(None, "--cmd", "-c", help="Stdio command (e.g. 'npx')"),
    args: Optional[str] = typer.Option(None, "--args", "-a", help="Command args (space-separated)"),
    env_vars: Optional[str] = typer.Option(None, "--env", "-e", help="Env vars KEY=VAL,KEY2=VAL2"),
    header: Optional[str] = typer.Option(None, "--header", "-H", help="HTTP headers KEY:VAL,KEY2:VAL2"),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Use a preset (filesystem/github/postgres/brave-search/sqlite/puppeteer)"),
):
    """➕ Add an MCP server connection"""
    from kurt.core.mcp_client import MCPConnection, add_connection, get_preset, list_presets

    if preset:
        conn = get_preset(preset)
        if not conn:
            console.print(f"[red]❌ Unknown preset: {preset}[/red]")
            list_presets()
            return
        conn.name = name or preset
        result = add_connection(conn)
        console.print(f"[green]{result}[/green]")
        console.print(f"[dim]Test it: kurt mcp test {conn.name}[/dim]")
        return

    if not url and not command:
        console.print("[red]❌ Provide either --url (HTTP) or --cmd (stdio)[/red]")
        console.print("\n[bold]Examples:[/bold]")
        console.print("  [dim]# HTTP server:[/dim]")
        console.print("  kurt mcp add myserver --url http://localhost:3000/mcp")
        console.print("  [dim]# Stdio server:[/dim]")
        console.print("  kurt mcp add myserver --cmd npx --args '-y @modelcontextprotocol/server-filesystem .'")
        console.print("  [dim]# From preset:[/dim]")
        console.print("  kurt mcp add mygithub --preset github")
        return

    # Parse transport
    transport = "http" if url else "stdio"

    # Parse env vars
    env = {}
    if env_vars:
        for pair in env_vars.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                env[k.strip()] = v.strip()

    # Parse headers
    headers = {}
    if header:
        for pair in header.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                headers[k.strip()] = v.strip()

    # Parse args list
    cmd_args = args.split() if args else []

    conn = MCPConnection(
        name=name,
        transport=transport,
        command=command,
        args=cmd_args,
        env=env,
        url=url,
        headers=headers,
        description=description,
    )

    result = add_connection(conn)
    console.print(f"[green]{result}[/green]")
    console.print(f"[dim]Test it: kurt mcp test {name}[/dim]")


@mcp_app.command("remove")
def mcp_remove(name: str = typer.Argument(..., help="Connection name to remove")):
    """🗑️  Remove an MCP connection"""
    from kurt.core.mcp_client import remove_connection
    result = remove_connection(name)
    color = "green" if result.startswith("✅") else "red"
    console.print(f"[{color}]{result}[/{color}]")


@mcp_app.command("test")
def mcp_test(name: str = typer.Argument(..., help="Connection name to test")):
    """🧪 Test an MCP connection — list its tools"""
    from kurt.core.mcp_client import load_registry, show_tools
    registry = load_registry()
    if name not in registry:
        console.print(f"[red]❌ Connection not found: {name}[/red]")
        console.print("[dim]Run: kurt mcp list[/dim]")
        return
    console.print(f"[cyan]🧪 Testing {name}…[/cyan]")
    asyncio.run(show_tools(name))


@mcp_app.command("call")
def mcp_call(
    tool_ref: str = typer.Argument(..., help="Tool to call: 'server/tool' or 'tool'"),
    params_json: str = typer.Option("{}", "--params", "-p", help="JSON params"),
):
    """⚡ Call an MCP tool directly"""
    from kurt.core.mcp_client import execute_mcp_tool
    import json as _json
    try:
        params = _json.loads(params_json)
    except _json.JSONDecodeError:
        console.print("[red]❌ Invalid JSON params[/red]")
        return
    console.print(f"[dim]Calling {tool_ref}…[/dim]")
    result = asyncio.run(execute_mcp_tool(tool_ref, params))
    console.print(result)


@mcp_app.command("presets")
def mcp_presets():
    """⚡ Show quick-add presets for popular MCP servers"""
    from kurt.core.mcp_client import list_presets
    list_presets()


@mcp_app.command("enable")
def mcp_enable(name: str = typer.Argument(...)):
    """✅ Enable an MCP connection"""
    from kurt.core.mcp_client import load_registry, save_registry
    registry = load_registry()
    if name not in registry:
        console.print(f"[red]❌ Not found: {name}[/red]")
        return
    registry[name].enabled = True
    save_registry(registry)
    console.print(f"[green]✅ Enabled: {name}[/green]")


@mcp_app.command("disable")
def mcp_disable(name: str = typer.Argument(...)):
    """🚫 Disable an MCP connection (keep saved, don't use)"""
    from kurt.core.mcp_client import load_registry, save_registry
    registry = load_registry()
    if name not in registry:
        console.print(f"[red]❌ Not found: {name}[/red]")
        return
    registry[name].enabled = False
    save_registry(registry)
    console.print(f"[dim]Disabled: {name}[/dim]")


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
