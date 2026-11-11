"""
KURT CLI Orchestrator
Handles slash commands inside `kurt chat` — routes to Claude Code CLI,
Gemini CLI, gh CLI, and other terminal tools.
"""

from kurt.utils.security import redact, child_env
from kurt.utils.execution import restricted_run, service_argv
import shlex
import os
import json
import subprocess
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Project root — all CLI tools run from here via npx (node_modules)
PROJECT_ROOT = Path(__file__).parent.parent.parent
NODE_BIN = PROJECT_ROOT / "node_modules" / ".bin"


def _resolve_cmd(name: str) -> str:
    """
    Resolve a CLI command — prefer local node_modules/.bin over global.
    This way LAHAT ng tools nasa project folder, hindi sa iMac globally.
    """
    local = NODE_BIN / name
    if local.exists():
        return str(local)
    # Return an executable path, never a compound shell command.
    resolved = shutil.which(name)
    if resolved:
        return resolved
    raise FileNotFoundError(f"CLI not found: {name}")


@dataclass
class SlashResult:
    handled: bool          # True if this was a slash command
    output: str            # Output to display
    continue_chat: bool    # True = stay in chat, False = exit
    model_override: Optional[str] = None   # Override model for next turn
    skill_override: Optional[str] = None   # Override active skill for next turn
    feed_to_ai: bool = False               # If True, persist `output` into chat history so Kurt's own LLM sees it next turn
    new_session_id: Optional[str] = None   # If set, caller should replace its session_id with this (fresh history)


# ─────────────────────────────────────────
# Slash command registry
# ─────────────────────────────────────────

SLASH_COMMANDS = {
    # ── Navigation — managing the chat session itself ──────────────
    "/help":      "Show this list of commands",
    "/clear":     "Start a fresh session  e.g. /clear",
    "/exit":      "Exit chat  e.g. /exit",
    "/quit":      "Exit chat (same as /exit)  e.g. /quit",
    "/history":   "Show recent messages in this session  e.g. /history",
    "/info":      "Show session ID, active model, and active skill  e.g. /info",
    "/save":      "Save Kurt's last reply to a file  e.g. /save answer.md",
    "/config":    "Personalize Kurt — theme, name, greeting  e.g. /config theme",
    # ── AI Tools — models, skills, and native workflows ─────────────
    "/model":     "Switch the AI model  e.g. /model openai/gpt-oss-120b",
    "/models":    "Show the live model routing table  e.g. /models",
    "/skill":     "Apply a skill to the next message  e.g. /skill tiktok",
    "/skills":    "List or search Kurt's loaded skills  e.g. /skills trading",
    "/agents":    "Discover native workflow agents  e.g. /agents shopee gross_sales",
    "/plugins":   "Discover executable native plugins  e.g. /plugins shopee gross_sales",
    "/library":   "Browse & run native data workflows (local, no AI call)  e.g. /library domains",
    # ── System — shell out to other dev tools ───────────────────────
    "/run":       "Run a shell command  e.g. /run ls -la",
    "/gh":        "Run GitHub CLI  e.g. /gh pr list",
    "/codex":     "Delegate a coding task to installed Codex CLI (read-only by default)",
    "/claude":    "Delegate to Claude Code CLI  e.g. /claude \"review main.py for bugs\"",
    "/gemini":    "Delegate to Gemini CLI  e.g. /gemini \"what is in this repo?\"",
    "/openclaw":  "Delegate a task to OpenClaw  e.g. /openclaw summarize the task results",
    "/peekaboo":  "Run a Peekaboo desktop command  e.g. /peekaboo permissions status --json",
    "/cli":       "CLI availability/readiness  e.g. /cli status | /cli probe",
    "/mcp":       "Connect to & call outside tools  e.g. /mcp list   |   /mcp tools filesystem",
    "/doctor":    "Diagnose & debug your iMac  e.g. /doctor summary | cpu | mem | disk | net | crashes | startup | open <path>",
    "/grep":      "Fast regex/text codebase search  e.g. /grep ModelRouter",
    "/find":      "Find files by glob or substring  e.g. /find *.py",
    "/tasks":     "Manage background tasks  e.g. /tasks list | start <cmd> | status <id> | kill <id>",
    "/subagent":  "Launch an autonomous subagent  e.g. /subagent research | find all API endpoints",
    "/plan":      "Create a structured Markdown plan artifact  e.g. /plan Refactor Auth | step 1; step 2",
    # ── Web & Computer — browsing and desktop control ────────────────
    "/web":       "Fetch a page or search the web  e.g. /web https://example.com",
    "/browser":   "Control a real (Playwright) browser  e.g. /browser open https://example.com",
    "/computer":  "Control the Mac desktop  e.g. /computer screenshot | analyze [image_path] | open <folder>",
    "/zip":       "Export a folder to .zip or import a .zip into a folder  e.g. /zip export ~/Projects/myapp",
}

SLASH_GROUPS = [
    ("🧭 Navigation", ["/help", "/clear", "/exit", "/quit", "/history", "/info", "/save", "/config"]),
    ("🧠 AI Tools", ["/model", "/models", "/skill", "/skills", "/agents", "/plugins", "/library", "/subagent", "/plan"]),
    ("⚙️  System", ["/run", "/gh", "/codex", "/claude", "/gemini", "/openclaw", "/peekaboo", "/cli", "/mcp", "/doctor", "/grep", "/find", "/tasks", "/zip"]),
    ("🖱️  Web & Computer", ["/web", "/browser", "/computer"]),
]


# ─────────────────────────────────────────
# Persistent Playwright browser session for /browser
# ─────────────────────────────────────────
_browser_session = None


def close_browser_session():
    """Tear down the persistent /browser session, if one was started."""
    global _browser_session
    if _browser_session is not None:
        try:
            _browser_session.close()
        except Exception:
            pass
        _browser_session = None


def _get_browser_session():
    global _browser_session
    if _browser_session is None:
        from kurt.core.web_browse import KurtBrowser
        _browser_session = KurtBrowser(headless=True)
        _browser_session.start()
    return _browser_session


def _cmd_exists(cmd: str) -> bool:
    """Check if a CLI tool is available — local node_modules first, then global"""
    local = NODE_BIN / cmd
    if local.exists():
        return True
    return shutil.which(cmd) is not None


def _ai_cli_env(cmd):
    """Keep CLI login usable and translate Kurt's Google key name explicitly."""
    name = Path(cmd).name
    allowed = ("ANTHROPIC_API_KEY",) if name == "claude" else ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_CLI_TRUST_WORKSPACE") if name == "gemini" else ("GH_TOKEN", "GITHUB_TOKEN")
    env = child_env(allow=allowed)
    if name == "gemini" and not env.get("GEMINI_API_KEY") and not env.get("GOOGLE_API_KEY"):
        if os.getenv("GOOGLE_AI_KEY"):
            env["GEMINI_API_KEY"] = os.environ["GOOGLE_AI_KEY"]
    if name == "claude" and env.get("ANTHROPIC_API_KEY"):
        mode = os.getenv("KURT_CLAUDE_AUTH", "auto")
        if mode not in {"auto", "api", "login"}:
            raise ValueError("KURT_CLAUDE_AUTH must be auto, api, or login.")
        if mode == "login":
            env.pop("ANTHROPIC_API_KEY", None)
        elif mode == "auto":
            try:
                status = subprocess.run(service_argv([cmd, "auth", "status"], "claude"),
                                        env=child_env(), capture_output=True, text=True, timeout=10)
                data = json.loads(status.stdout) if status.returncode == 0 else {}
                if data.get("loggedIn") is True and data.get("authMethod") == "claude.ai":
                    env.pop("ANTHROPIC_API_KEY", None)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
    return env


def _run_shell(cmd: str, args: str) -> str:
    """Run a shell command and return output"""
    full_cmd = f"{cmd} {args}".strip()
    try:
        trusted = Path(cmd).name in {"claude", "gemini", "gh"}
        runner = subprocess.run if trusted else restricted_run
        from kurt.utils.workspace import current_workspace
        options = {"env": _ai_cli_env(cmd), "cwd": str(current_workspace())} if trusted else {}
        if trusted and Path(cmd).name in {"claude", "gemini"}:
            from kurt.utils.process import run_bounded
            result = run_bounded(service_argv([cmd, *shlex.split(args)], Path(cmd).name),
                                 env=options['env'], cwd=options['cwd'], timeout=120, max_output=65536)
            out, err = redact(result['stdout'].strip()), redact(result['stderr'].strip())
            if result['status'] != 'completed':
                detail = err or f"CLI status: {result['status']}; exit code: {result['exit_code']}."
                return f"❌ Error:\n{detail}\n[stdout]\n{out}" if out else f"❌ Error:\n{detail}"
            return out or '(no output)'
        result = runner(
            service_argv([cmd, *shlex.split(args)], Path(cmd).name) if trusted else full_cmd,
            shell=not trusted,
            capture_output=True,
            text=True,
            timeout=30,
            **options,
        )
        out = redact(result.stdout.strip())
        err = redact(result.stderr.strip())
        if result.returncode != 0:
            detail = err or f"Command exited with code {result.returncode}."
            return f"❌ Error:\n{detail}\n[stdout]\n{out}" if out else f"❌ Error:\n{detail}"
        return out if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "❌ Command timed out (30s)"
    except Exception as e:
        return f"❌ Failed to run: {e}"


def handle_slash(
    prompt: str,
    session_id: str,
    current_model: str,
    current_skill: Optional[str],
    last_response: str = "",
) -> SlashResult:
    """
    Check if prompt is a slash command. Returns SlashResult.
    If not a slash command, returns SlashResult(handled=False).
    """

    p = prompt.strip()

    if not p.startswith("/"):
        return SlashResult(handled=False, output="", continue_chat=True)

    # Split into command + args
    parts = p.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    # ── /help ───────────────────────────────────────────────────────
    if cmd == "/help":
        lines = ["", "📖  KURT Slash Commands", "═" * 50]
        for group_name, slash_names in SLASH_GROUPS:
            lines.append(f"\n{group_name}")
            lines.append("─" * 40)
            for slash in slash_names:
                desc = SLASH_COMMANDS.get(slash, "")
                lines.append(f"  {slash:<12}  {desc}")
        lines += ["", "Tip: /claude, /gemini, /openclaw and /peekaboo return their CLI results to Kurt"]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    # ── /clear ──────────────────────────────────────────────────────
    if cmd == "/clear":
        new_id = str(uuid.uuid4())
        return SlashResult(
            handled=True,
            output=f"🆕 New session: {new_id[:8]}",
            continue_chat=True,
            new_session_id=new_id,
        )

    # ── /exit /quit ─────────────────────────────────────────────────
    if cmd in ("/exit", "/quit"):
        close_browser_session()
        return SlashResult(handled=True, output="👋 Bye! K.U.R.T. signing off.", continue_chat=False)

    # ── /model ──────────────────────────────────────────────────────
    if cmd == "/model":
        if not args:
            return SlashResult(
                handled=True,
                output=(
                    f"Current model: {current_model}\n"
                    "Usage: /model <name>\n"
                    "  Groq (libre, mabilis):  /model openai/gpt-oss-120b\n"
                    "  Auto-route:             /model auto\n\n"
                    "Gustong paid na model? Browse first, then switch:\n"
                    "  kurt models list    — 400+ OpenRouter text models (bills OpenRouter top-up)\n"
                    "  kurt models fal     — 1,400+ fal.ai image/video/audio models (bills fal.ai top-up)\n"
                    "  Then: /model <id-from-that-list>"
                ),
                continue_chat=True,
            )
        parts = args.split()
        # "/model <id> <provider>" — explicit provider tag, needed because fal.ai
        # and OpenRouter model ids can look identical (both "vendor/name" style)
        # and auto-detection by id shape alone would guess wrong for fal models.
        if len(parts) == 2 and parts[1] in ("openrouter", "fal", "groq", "anthropic", "replicate", "kling", "suno", "openai"):
            model_id, explicit_provider = parts
            return SlashResult(
                handled=True,
                output=f"✅ Switched to model: {model_id}  [{explicit_provider}]",
                continue_chat=True,
                model_override=f"{model_id}|{explicit_provider}",
            )
        return SlashResult(
            handled=True,
            output=f"✅ Switched to model: {args}",
            continue_chat=True,
            model_override=args,
        )

    # ── /skill ──────────────────────────────────────────────────────
    if cmd == "/skill":
        if not args:
            return SlashResult(
                handled=True,
                output="Usage: /skill <name>  e.g. /skill tiktok\nRun `kurt skill list` to see all skills.",
                continue_chat=True,
            )
        from kurt.skills.manager import get_skill_prompt
        if not get_skill_prompt(args):
            return SlashResult(
                handled=True,
                output=f"❌ Unknown skill: {args}\nRun `kurt skill list` to see all skills.",
                continue_chat=True,
            )
        return SlashResult(
            handled=True,
            output=f"✅ Skill activated: {args}  (will apply on next message)",
            continue_chat=True,
            skill_override=args,
        )

    # ── /info ───────────────────────────────────────────────────────
    if cmd == "/info":
        from kurt.core.mac_doctor import get_os_profile
        prof = get_os_profile()
        lines = [
            "",
            "ℹ️   KURT Session & Host Info",
            "─" * 35,
            f"  Session ID  : {session_id[:8]}…",
            f"  Host OS     : {prof['os_label']} ({prof['system']} {prof['release']}, {prof['machine']})",
            f"  Shell / Pkg : {prof['shell']} · {prof['package_manager']}",
            f"  Model       : {current_model}",
            f"  Skill       : {current_skill or 'none'}",
            f"  Claude CLI  : {'✅ installed' if _cmd_exists('claude') else '❌ not found'}",
            f"  Gemini CLI  : {'✅ installed' if _cmd_exists('gemini') else '❌ not found'}",
            f"  gh CLI      : {'✅ installed' if _cmd_exists('gh') else '❌ not found'}",
            f"  OpenClaw CLI: {'✅ installed' if _cmd_exists('openclaw') else '❌ not found'}",
            f"  Peekaboo CLI: {'✅ installed' if _cmd_exists('peekaboo') else '❌ not found'}",
            "",
        ]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    # ── /config ─────────────────────────────────────────────────────
    if cmd == "/config":
        from kurt.core.persona import (
            config_show, config_theme_wizard, config_name_wizard,
            config_icon_wizard, config_language_wizard, config_aimode_wizard,
            config_projects_wizard, config_full_wizard, reset_persona,
        )
        wizards = {
            "": config_show,
            "show": config_show,
            "theme": config_theme_wizard,
            "name": config_name_wizard,
            "icon": config_icon_wizard,
            "language": config_language_wizard,
            "lang": config_language_wizard,
            "aimode": config_aimode_wizard,
            "projects": config_projects_wizard,
            "setup": config_full_wizard,
        }
        sub = args.strip().lower()
        if sub == "reset":
            reset_persona()
            return SlashResult(handled=True, output="♻️  Persona reset to defaults.", continue_chat=True)
        wizard = wizards.get(sub)
        if wizard is None:
            return SlashResult(
                handled=True,
                output="Usage: /config [show|theme|name|icon|language|aimode|projects|setup|reset]",
                continue_chat=True,
            )
        # These wizards print/prompt directly (interactive Rich prompts) — run them
        # in place, same as any other console.input() in this loop.
        wizard()
        return SlashResult(handled=True, output="", continue_chat=True)

    # ── /history ────────────────────────────────────────────────────
    if cmd == "/history":
        from kurt.core.memory import get_history
        history = get_history(session_id, limit=10)
        if not history:
            return SlashResult(handled=True, output="No history yet in this session.", continue_chat=True)
        lines = ["", "📜  Recent History (last 10 messages)", "─" * 40]
        for msg in history:
            role = "You " if msg["role"] == "user" else "KURT"
            snippet = msg["content"][:120].replace("\n", " ")
            lines.append(f"  [{role}]  {snippet}…" if len(msg["content"]) > 120 else f"  [{role}]  {snippet}")
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    # ── /models ─────────────────────────────────────────────────────
    if cmd == "/models":
        from kurt.core.orchestrator import ROUTING_TABLE
        lines = ["", "🤖  Model Routing Table (live)", "─" * 50]
        for task_type, route in ROUTING_TABLE.items():
            lines.append(f"  {task_type.value:<10} → {route['model']}  [{route['provider']}]")
            lines.append(f"              fallback → {route['fallback_model']}  [{route['fallback_provider']}]")
        lines += ["", "Switch: /model <model-name>", "  e.g. /model openai/gpt-oss-120b"]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    if cmd == "/library":
        from kurt.capabilities.commands import chat_command
        try:
            output = chat_command(args)
        except (ValueError, OSError) as exc:
            output = f"Native workflow: {exc}"
        return SlashResult(handled=True, output=output, continue_chat=True,
                           feed_to_ai=args.strip().startswith("run "))

    if cmd in ("/agents", "/plugins"):
        from kurt.capabilities.runtime import search
        kind = "agent" if cmd == "/agents" else "plugin"
        rows = search(args, kind=kind, include_disabled=False)
        output = "\n".join(f"{e['id']} | {e['name']}" for e in rows) or "No ready native workflows matched."
        return SlashResult(handled=True, output=output, continue_chat=True)

    # ── /skills ─────────────────────────────────────────────────────
    if cmd == "/skills":
        from kurt.skills.manager import get_all_skills
        skills = get_all_skills()
        lines = ["", f"🧠  Installed Skills ({len(skills)})", "─" * 40]
        if args:
            skills = [s for s in skills if args.casefold() in (s['id'] + ' ' + s['description']).casefold()]
        for s in skills[:40]:
            kind = "built-in" if s.get("builtin") else "custom"
            lines.append(f"  {s['id']:<15} {s['description']} [{kind}]")
        lines += ["", f"Showing {min(40, len(skills))} matches. Native workflows: /library search <words>", "Apply skill: /skill <name>"]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    # ── /save ───────────────────────────────────────────────────────
    if cmd == "/save":
        if not last_response:
            return SlashResult(handled=True, output="Nothing to save yet. Ask something first!", continue_chat=True)
        filename = args if args else f"kurt_output_{session_id[:8]}.md"
        if not filename.endswith((".md", ".txt", ".py", ".js", ".html")):
            filename += ".md"
        try:
            with open(filename, "w") as f:
                f.write(last_response)
            return SlashResult(handled=True, output=f"✅ Saved to: {filename}", continue_chat=True)
        except Exception as e:
            return SlashResult(handled=True, output=f"❌ Could not save: {e}", continue_chat=True)

    # ── /run ────────────────────────────────────────────────────────
    if cmd == "/run":
        if not args:
            return SlashResult(handled=True, output="Usage: /run <shell command>  e.g. /run ls -la", continue_chat=True)
        output = _run_shell("", args)
        return SlashResult(handled=True, output=f"$ {args}\n\n{output}", continue_chat=True)

    if cmd == "/cli":
        from kurt.core.cli_tools import cli_status
        import json
        if args not in ("", "status", "probe"):
            return SlashResult(True, "Usage: /cli status | /cli probe", True)
        return SlashResult(True, json.dumps(cli_status(probe=args == "probe"), indent=2), True)

    if cmd in ("/openclaw", "/peekaboo"):
        from kurt.core.cli_tools import delegate_desktop_cli
        if not args:
            usage = "/openclaw <task>" if cmd == "/openclaw" else "/peekaboo <command and args>, e.g. permissions status --json"
            return SlashResult(True, "Usage: " + usage, True)
        try:
            result = delegate_desktop_cli(cmd[1:], args)
            output = result.text()
        except ValueError as exc:
            output = f"CLI configuration error: {exc}"
        return SlashResult(True, output, True, feed_to_ai=True)

    if cmd == "/codex":
        from kurt.core.codex_adapter import run_codex, codex_status
        import json
        if args in ("", "status"):
            return SlashResult(True, json.dumps(codex_status(),ensure_ascii=False),True)
        try:
            result=run_codex(args,cwd=Path.cwd())
            return SlashResult(True,json.dumps(result,ensure_ascii=False),True,feed_to_ai=True)
        except (ValueError,OSError,RuntimeError) as exc:
            return SlashResult(True,"Codex delegation failed: "+redact(str(exc)),True)

    # ── /claude ─────────────────────────────────────────────────────
    if cmd == "/claude":
        if not _cmd_exists("claude"):
            return SlashResult(
                handled=True,
                output=(
                    "❌ Claude Code CLI not found.\n"
                    "Run: npm install  (sa project folder)\n"
                    "Docs: https://claude.ai/code"
                ),
                continue_chat=True,
            )
        if not args:
            return SlashResult(
                handled=True,
                output="Usage: /claude <prompt>\ne.g. /claude review my main.py for bugs",
                continue_chat=True,
            )
        claude_cmd = _resolve_cmd("claude")
        output = _run_shell(claude_cmd, f'--print {shlex.quote(redact(args))}')
        return SlashResult(handled=True, output=f"🤖 Claude Code:\n\n{output}", continue_chat=True, feed_to_ai=True)

    # ── /gemini ─────────────────────────────────────────────────────
    if cmd == "/gemini":
        if not _cmd_exists("gemini"):
            return SlashResult(
                handled=True,
                output=(
                    "❌ Gemini CLI not found.\n"
                    "Run: npm install  (sa project folder)"
                ),
                continue_chat=True,
            )
        if not args:
            return SlashResult(
                handled=True,
                output="Usage: /gemini <prompt>\ne.g. /gemini what files are in this repo?",
                continue_chat=True,
            )
        gemini_cmd = _resolve_cmd("gemini")
        output = _run_shell(gemini_cmd, f'-p {shlex.quote(redact(args))}')
        return SlashResult(handled=True, output=f"✨ Gemini:\n\n{output}", continue_chat=True, feed_to_ai=True)

    # ── /gh ─────────────────────────────────────────────────────────
    if cmd == "/gh":
        if not _cmd_exists("gh"):
            return SlashResult(
                handled=True,
                output=(
                    "❌ GitHub CLI (gh) not found.\n"
                    "Install: https://cli.github.com\n"
                    "macOS: brew install gh"
                ),
                continue_chat=True,
            )
        if not args:
            return SlashResult(
                handled=True,
                output="Usage: /gh <gh command>\ne.g. /gh pr list\n       /gh issue create\n       /gh repo view",
                continue_chat=True,
            )
        output = _run_shell("gh", args)
        return SlashResult(handled=True, output=f"🐙 GitHub CLI:\n\n{output}", continue_chat=True)

    # ── /mcp ────────────────────────────────────────────────────────
    if cmd == "/mcp":
        # /mcp list | /mcp tools | /mcp call server/tool {params}
        sub = args.split(None, 1)
        sub_cmd = sub[0].lower() if sub else "list"
        sub_args = sub[1].strip() if len(sub) > 1 else ""

        if sub_cmd in ("catalog", "search", "config", "connect", "import"):
            from kurt.core.mcp_commands import chat_command
            try:
                output = chat_command(sub_cmd, sub_args)
            except (ValueError, OSError) as exc:
                output = f"MCP: {exc}"
            return SlashResult(handled=True, output=output, continue_chat=True)

        if sub_cmd == "connect-preset":
            from kurt.core.mcp_client import get_preset, add_connection
            conn = get_preset(sub_args)
            if not conn:
                return SlashResult(handled=True, output=f"❌ Unknown preset: {sub_args}", continue_chat=True)
            conn.name = sub_args
            result = add_connection(conn)
            return SlashResult(handled=True, output=result, continue_chat=True)

        if sub_cmd == "list":
            from kurt.core.mcp_client import load_registry
            registry = load_registry()
            if not registry:
                return SlashResult(
                    handled=True,
                    output="No MCP connections.\nAdd one: kurt mcp add <name> --url <url>",
                    continue_chat=True,
                )
            lines = ["", "🔌 Connected MCP Servers", "─" * 40]
            for name, conn in registry.items():
                target = conn.url or conn.command or "—"
                status = "✓" if conn.enabled else "○"
                lines.append(f"  {status} {name}  [{conn.transport}]  {target[:40]}")
            return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

        elif sub_cmd == "tools":
            import asyncio as _asyncio
            from kurt.core.mcp_client import show_tools, load_registry
            registry = load_registry()
            if not registry:
                return SlashResult(
                    handled=True,
                    output="No MCP connections. Add one with: kurt mcp add",
                    continue_chat=True,
                )
            lines = ["", "🔧 MCP Tools", "─" * 40]
            for name, conn in registry.items():
                if not conn.enabled:
                    continue
                from kurt.core.mcp_client import list_tools as _list_tools
                try:
                    tools = _asyncio.run(_list_tools(conn))
                    lines.append(f"\n[{name}]")
                    for t in tools[:8]:
                        lines.append(f"  • {t.name}  {t.description[:50]}")
                except Exception as e:
                    lines.append(f"\n[{name}] ❌ {e}")
            return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

        elif sub_cmd == "call":
            # /mcp call server/tool {"key": "val"}
            import asyncio as _asyncio
            import json as _json
            parts2 = sub_args.split(None, 1)
            if not parts2:
                return SlashResult(handled=True, output="Usage: /mcp call server/tool {params}", continue_chat=True)
            tool_ref = parts2[0]
            params_raw = parts2[1] if len(parts2) > 1 else "{}"
            try:
                params = _json.loads(params_raw)
            except Exception:
                params = {}
            from kurt.core.mcp_client import execute_mcp_tool
            result = _asyncio.run(execute_mcp_tool(tool_ref, params))
            return SlashResult(handled=True, output=f"🔌 {tool_ref}:\n\n{result}", continue_chat=True)

        return SlashResult(
            handled=True,
            output="Usage: /mcp catalog | search <app> | config <id> | connect <JSON or URL> | list | tools | call server/tool {params}",
            continue_chat=True,
        )

    # ── /computer ───────────────────────────────────────────────────
    if cmd == "/computer":
        sub = args.split(None, 1)
        sub_cmd = sub[0].lower() if sub else ""
        sub_args = sub[1].strip() if len(sub) > 1 else ""

        if sub_cmd == "screenshot":
            import time as _time
            from kurt.core.computer_use import screenshot as _screenshot
            shots_dir = Path.home() / ".kurt" / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            save_path = str(shots_dir / f"kurt_{int(_time.time())}.png")
            result = _screenshot(save_path=save_path)
            if result.success:
                return SlashResult(handled=True, output=f"📸 {result.message}\nSaved: {save_path}", continue_chat=True)
            return SlashResult(handled=True, output=f"❌ Screenshot failed: {result.message}", continue_chat=True)

        elif sub_cmd == "type":
            if not sub_args:
                return SlashResult(handled=True, output="Usage: /computer type <text>", continue_chat=True)
            from kurt.core.computer_use import type_text as _type_text
            result = _type_text(sub_args)
            if result.success:
                return SlashResult(handled=True, output=f"⌨️  {result.message}", continue_chat=True)
            return SlashResult(handled=True, output=f"❌ Type failed: {result.message}", continue_chat=True)

        elif sub_cmd == "click":
            coords = sub_args.split()
            if len(coords) != 2 or not all(c.lstrip("-").isdigit() for c in coords):
                return SlashResult(handled=True, output="Usage: /computer click <x> <y>", continue_chat=True)
            from kurt.core.computer_use import click as _click
            result = _click(int(coords[0]), int(coords[1]))
            if result.success:
                return SlashResult(handled=True, output=f"🖱️  {result.message}", continue_chat=True)
            return SlashResult(handled=True, output=f"❌ Click failed: {result.message}", continue_chat=True)

        elif sub_cmd == "analyze":
            from kurt.core.agent_loop import execute_tool
            tokens = sub_args.split(None, 1)
            maybe_path = Path(tokens[0]).expanduser() if tokens else None
            if maybe_path and maybe_path.is_file():
                img_query = tokens[1].strip() if len(tokens) > 1 else ""
                out = execute_tool("analyze_screen", {"mode": "describe", "path": str(maybe_path), "query": img_query})
            else:
                out = execute_tool("analyze_screen", {"mode": "describe", "query": sub_args})
            return SlashResult(handled=True, output=out, continue_chat=True, feed_to_ai=True)

        elif sub_cmd == "open":
            from kurt.core.mac_doctor import open_folder
            res = open_folder(sub_args or ".")
            if res.get("status") == "ok":
                return SlashResult(handled=True, output=f"📂 {res['message']}", continue_chat=True)
            return SlashResult(handled=True, output=f"❌ {res.get('error')}", continue_chat=True)

        return SlashResult(
            handled=True,
            output="Usage: /computer screenshot | analyze [image_path] [question] | type <text> | click <x> <y> | open <folder>",
            continue_chat=True,
        )

    # ── /zip (export/import a project folder) ────────────────────────
    if cmd == "/zip":
        sub = args.split(None, 1)
        sub_cmd = sub[0].lower() if sub else ""
        sub_args = sub[1].strip() if len(sub) > 1 else ""

        if sub_cmd == "export":
            parts = sub_args.split()
            if not parts:
                return SlashResult(handled=True, output="Usage: /zip export <folder> [output.zip]", continue_chat=True)
            from kurt.core.archive import export_folder
            try:
                output_path = export_folder(parts[0], parts[1] if len(parts) > 1 else None)
                return SlashResult(handled=True, output=f"✅ Exported: {output_path}", continue_chat=True)
            except (ValueError, OSError) as exc:
                return SlashResult(handled=True, output=f"❌ Export failed: {exc}", continue_chat=True)

        if sub_cmd == "import":
            parts = sub_args.split()
            if not parts:
                return SlashResult(handled=True, output="Usage: /zip import <file.zip> [destination_folder]", continue_chat=True)
            from kurt.core.archive import import_zip
            try:
                output_dir = import_zip(parts[0], parts[1] if len(parts) > 1 else None)
                return SlashResult(handled=True, output=f"✅ Imported to: {output_dir}", continue_chat=True)
            except (ValueError, OSError) as exc:
                return SlashResult(handled=True, output=f"❌ Import failed: {exc}", continue_chat=True)

        return SlashResult(
            handled=True,
            output="Usage: /zip export <folder> [output.zip]  |  /zip import <file.zip> [destination_folder]",
            continue_chat=True,
        )

    # ── /doctor, /mac, or /system (Cross-Platform Host Diagnostics) ─
    if cmd in ("/doctor", "/mac", "/system"):
        from kurt.core.mac_doctor import run_doctor_action, format_doctor_report
        sub = args.split(None, 1)
        act = sub[0].lower() if sub else "summary"
        target = sub[1].strip() if len(sub) > 1 else None
        data = run_doctor_action(action=act, target=target)
        report = format_doctor_report(data)
        return SlashResult(handled=True, output=report, continue_chat=True, feed_to_ai=True)

    # ── /grep ───────────────────────────────────────────────────────
    if cmd == "/grep":
        if not args:
            return SlashResult(handled=True, output="Usage: /grep <pattern> [path]", continue_chat=True)
        from kurt.core.file_ops import grep_search
        parts2 = args.split(None, 1)
        query = parts2[0]
        path = parts2[1].strip() if len(parts2) > 1 else "."
        try:
            out = grep_search(query=query, path=path)
        except Exception as e:
            out = f"❌ {e}"
        return SlashResult(handled=True, output=out, continue_chat=True, feed_to_ai=True)

    # ── /find ───────────────────────────────────────────────────────
    if cmd == "/find":
        from kurt.core.file_ops import find_files
        parts2 = args.split(None, 1) if args else ["*"]
        pat = parts2[0]
        path = parts2[1].strip() if len(parts2) > 1 else "."
        try:
            out = find_files(pattern=pat, path=path)
        except Exception as e:
            out = f"❌ {e}"
        return SlashResult(handled=True, output=out, continue_chat=True, feed_to_ai=True)

    # ── /tasks ──────────────────────────────────────────────────────
    if cmd == "/tasks":
        import json as _json
        from kurt.core.subagents import manage_background_task
        sub = args.split(None, 1)
        act = sub[0].lower() if sub else "list"
        rest = sub[1].strip() if len(sub) > 1 else ""
        if act == "start":
            res = manage_background_task(action="start", cmd=rest)
        elif act in ("status", "kill"):
            res = manage_background_task(action=act, task_id=rest)
        else:
            res = manage_background_task(action="list")
        return SlashResult(handled=True, output=_json.dumps(res, indent=2, ensure_ascii=False), continue_chat=True)

    # ── /subagent ───────────────────────────────────────────────────
    if cmd == "/subagent":
        if not args:
            return SlashResult(
                handled=True,
                output="Usage: /subagent <role> | <task>\nRoles: research, coder, mac-doctor, qa-verifier\ne.g. /subagent research | find how routing works",
                continue_chat=True,
            )
        import json as _json
        from kurt.core.agent_loop import _run_coro_blocking
        from kurt.core.subagents import run_subagent_async
        if "|" in args:
            role, task_str = [x.strip() for x in args.split("|", 1)]
        else:
            role, task_str = "research", args.strip()
        res = _run_coro_blocking(run_subagent_async(role=role, task=task_str))
        return SlashResult(
            handled=True,
            output=f"🤖 Subagent [{role}] ({res.get('status')}):\n\n{res.get('summary', '')}",
            continue_chat=True,
            feed_to_ai=True,
        )

    # ── /plan ───────────────────────────────────────────────────────
    if cmd == "/plan":
        if not args:
            return SlashResult(
                handled=True,
                output="Usage: /plan <title> | <step 1; step 2; step 3>",
                continue_chat=True,
            )
        from kurt.core.subagents import create_plan_artifact
        if "|" in args:
            title, steps_raw = [x.strip() for x in args.split("|", 1)]
            steps_list = [s.strip() for s in steps_raw.split(";") if s.strip()]
        else:
            title = args.strip()
            steps_list = ["Analyze requirements and existing files", "Implement core changes", "Run tests and verify"]
        res = create_plan_artifact(title=title, summary=title, steps=steps_list)
        if res.get("status") == "ok":
            return SlashResult(
                handled=True,
                output=f"📋 Plan Artifact Created: {res['path']}\n\n{res['preview']}",
                continue_chat=True,
                feed_to_ai=True,
            )
        return SlashResult(handled=True, output=f"❌ {res.get('error')}", continue_chat=True)

    # ── /web ────────────────────────────────────────────────────────
    if cmd == "/web":
        if not args:
            return SlashResult(handled=True, output="Usage: /web <url>  |  /web search <query>", continue_chat=True)

        sub = args.split(None, 1)
        if sub[0].lower() == "search" and len(sub) > 1:
            from kurt.core.web_browse import search_web
            result = search_web(sub[1].strip())
            if result.success:
                return SlashResult(handled=True, output=f"🔎 Results for: {result.query}\n\n{result.summary()}", continue_chat=True)
            return SlashResult(handled=True, output=f"❌ Search failed: {result.error}", continue_chat=True)

        from kurt.core.web_browse import read_page
        result = read_page(args)
        if result.success:
            body = result.content[:2000] + ("…" if len(result.content) > 2000 else "")
            return SlashResult(handled=True, output=f"🌐 {result.title}\n{result.url}\n\n{body}", continue_chat=True)
        return SlashResult(handled=True, output=f"❌ Could not fetch {args}: {result.error}", continue_chat=True)

    # ── /browser (Playwright) ──────────────────────────────────────
    if cmd == "/browser":
        sub = args.split(None, 1)
        sub_cmd = sub[0].lower() if sub else ""
        sub_args = sub[1].strip() if len(sub) > 1 else ""

        if sub_cmd == "open":
            if not sub_args:
                return SlashResult(handled=True, output="Usage: /browser open <url>", continue_chat=True)
            try:
                session = _get_browser_session()
                result = session.go(sub_args)
            except ImportError as e:
                return SlashResult(handled=True, output=f"❌ {e}", continue_chat=True)
            if result.success:
                return SlashResult(handled=True, output=f"🧭 Opened: {result.title}\n{result.url}", continue_chat=True)
            return SlashResult(handled=True, output=f"❌ Navigation failed: {result.error}", continue_chat=True)

        elif sub_cmd == "screenshot":
            if _browser_session is None:
                return SlashResult(handled=True, output="No open page yet. Run /browser open <url> first.", continue_chat=True)
            import base64 as _b64, time as _time
            shots_dir = Path.home() / ".kurt" / "browser_screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            b64 = _browser_session.screenshot_b64()
            if not b64:
                return SlashResult(handled=True, output="❌ Screenshot failed.", continue_chat=True)
            save_path = shots_dir / f"kurt_browser_{int(_time.time())}.png"
            save_path.write_bytes(_b64.b64decode(b64))
            return SlashResult(handled=True, output=f"📸 Saved: {save_path}", continue_chat=True)

        elif sub_cmd == "click":
            if not sub_args:
                return SlashResult(handled=True, output="Usage: /browser click <selector>", continue_chat=True)
            if _browser_session is None:
                return SlashResult(handled=True, output="No open page yet. Run /browser open <url> first.", continue_chat=True)
            ok = _browser_session.click(selector=sub_args)
            return SlashResult(handled=True, output=("🖱️  Clicked." if ok else f"❌ Could not click: {sub_args}"), continue_chat=True)

        elif sub_cmd == "fill":
            fill_parts = sub_args.split(None, 1)
            if len(fill_parts) != 2:
                return SlashResult(handled=True, output="Usage: /browser fill <selector> <value>", continue_chat=True)
            if _browser_session is None:
                return SlashResult(handled=True, output="No open page yet. Run /browser open <url> first.", continue_chat=True)
            ok = _browser_session.type(fill_parts[0], fill_parts[1])
            return SlashResult(handled=True, output=("✅ Filled." if ok else f"❌ Could not fill: {fill_parts[0]}"), continue_chat=True)

        elif sub_cmd == "close":
            close_browser_session()
            return SlashResult(handled=True, output="🧭 Browser session closed.", continue_chat=True)

        return SlashResult(
            handled=True,
            output="Usage: /browser open <url> | screenshot | click <selector> | fill <selector> <value> | close",
            continue_chat=True,
        )

    # ── Unknown slash command ────────────────────────────────────────
    return SlashResult(
        handled=True,
        output=f"❓ Unknown command: {cmd}\nType /help to see all commands.",
        continue_chat=True,
    )
