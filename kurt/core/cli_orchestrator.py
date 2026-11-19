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
import threading
import sys
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
    suffixes = ('.exe','.cmd','') if sys.platform == 'win32' else ('',)
    for suffix in suffixes:
        local = NODE_BIN / (name+suffix)
        if local.is_file() and os.access(local, os.X_OK):
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
    cli_override: Optional[str] = None
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
    "/setting":   "Choose defaults — Chat AI, CLI, Image AI, Video AI",
    "/setup":     "Add/update your API keys (Groq, OpenRouter, Composio, etc.)  e.g. /setup",
    "/speech":    "Voice language/provider/vocabulary: /speech language tl | /speech word-add <name>",
    # ── AI Tools — models, skills, and native workflows ─────────────
    "/image-model": "Choose default image generator: /image-model <model-id> fal|replicate",
    "/video-model": "Choose default video generator: /video-model <model-id> fal|replicate",
    "/image": "Generate an image using the saved image default: /image <prompt>",
    "/video": "Generate a video using the saved video default: /video <prompt>",
    "/model":     "Switch the AI model  e.g. /model openai/gpt-oss-120b",
    "/models":    "Browse full OpenRouter/fal.ai catalogs; /models refresh or /models routing",
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
    "/deepseek":  "Use installed DeepSeek Agent with Kurt setup key (filesystem read-only)",
    "/deepseek-cli": "Use installed DeepSeek Terminal CLI with Kurt setup key (filesystem read-only)",
    "/copilot":   "Delegate to GitHub Copilot CLI (read-only); /copilot <task>",
    "/gemini":    "Delegate to Gemini CLI  e.g. /gemini \"what is in this repo?\"",
    "/openclaw":  "Delegate a task to OpenClaw  e.g. /openclaw summarize the task results",
    "/peekaboo":  "Run a Peekaboo desktop command  e.g. /peekaboo permissions status --json",
    "/wallet":    "USD balance/history/top-up: actual provider costs with zero markup",
    "/cli":       "CLI defaults/readiness: /cli status | /cli probe all | /cli test <name> (may use credits)",
    "/mcp":       "Connect to & call outside tools  e.g. /mcp list   |   /mcp tools filesystem",
    "/connect":   "Connect an app (Gmail, Slack, Shopify...) — opens the login page for you  e.g. /connect gmail",
    "/zapier":    "Browse 9,000+ Zapier app integrations  e.g. /zapier search shopify | /zapier open gmail",
    "/n8n":       "Browse 2,000+ n8n workflow integrations  e.g. /n8n search postgres | /n8n open slack",
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
    ("🧭 Navigation", ["/help", "/clear", "/exit", "/quit", "/history", "/info", "/save", "/config", "/setup"]),
    ("🧠 AI Tools", ["/model", "/models", "/speech", "/image", "/video", "/image-model", "/video-model", "/skill", "/skills", "/agents", "/plugins", "/library", "/subagent", "/plan"]),
    ("⚙️  System", ["/run", "/gh", "/codex", "/claude", "/gemini", "/deepseek", "/deepseek-cli", "/copilot", "/openclaw", "/peekaboo", "/cli", "/wallet", "/mcp", "/connect", "/zapier", "/n8n", "/doctor", "/grep", "/find", "/tasks", "/zip"]),
    ("🖱️  Web & Computer", ["/web", "/browser", "/computer"]),
]


# ─────────────────────────────────────────
# Persistent Playwright browser session for /browser
# ─────────────────────────────────────────
_browser_session = None
_browser_session_lock = threading.Lock()


def close_browser_session():
    """Tear down the persistent /browser session, if one was started."""
    global _browser_session
    with _browser_session_lock:
        if _browser_session is not None:
            try:
                _browser_session.close()
            finally:
                _browser_session = None


def _get_browser_session():
    global _browser_session
    with _browser_session_lock:
        if _browser_session is None:
            from kurt.core.web_browse import BrowserSession
            candidate = BrowserSession(headless=True)
            try:
                candidate.start()
            except Exception:
                candidate.close()
                raise
            _browser_session = candidate
        return _browser_session


def _cmd_exists(cmd: str) -> bool:
    """Check if a CLI tool is available — local node_modules first, then global"""
    try: _resolve_cmd(cmd); return True
    except FileNotFoundError: return False


def _ai_cli_env(cmd):
    """Keep CLI login usable and translate Kurt's Google key name explicitly."""
    name = Path(cmd).name
    if name.lower().endswith(('.cmd','.exe','.bat')): name=Path(name).stem
    allowed = ("ANTHROPIC_API_KEY",) if name == "claude" else ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_CLI_TRUST_WORKSPACE") if name == "gemini" else ("MISTRAL_API_KEY",) if name == "vibe" else () if name in {"deepseek", "deepseek-cli"} else ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN") if name == 'copilot' else ("GH_TOKEN", "GITHUB_TOKEN")
    env = child_env(allow=allowed)
    # Agent hosts can prepend private helper binaries (e.g. ~/.codex) to
    # PATH. A different CLI must not try to resolve tools through that vault.
    from kurt.utils.execution import _protected_paths
    protected, _ = _protected_paths(service=name)
    entries = []
    for entry in env.get('PATH', '').split(os.pathsep):
        if not entry: continue
        path = Path(entry).expanduser().resolve()
        if not any(path == root.resolve() or root.resolve() in path.parents for root in protected):
            entries.append(entry)
    env['PATH'] = os.pathsep.join([str(NODE_BIN), *(entries or os.defpath.split(os.pathsep))])
    from kurt.billing.client import active, cli_environment
    if active():
        return cli_environment(name, env) or child_env(source=env)
    if name in {'deepseek', 'deepseek-cli'}:
        from kurt.utils.env_loader import setup_api_key
        from kurt.core.deepseek_adapter import MODEL, BASE_URL
        env['DEEPSEEK_MODEL'] = MODEL
        env['DEEPSEEK_BASE_URL'] = BASE_URL
        key = setup_api_key('DEEPSEEK_API_KEY')
        if key: env['DEEPSEEK_API_KEY'] = key
        if name == 'deepseek':
            env['TAVILY_API_KEY'] = setup_api_key('TAVILY_API_KEY') or 'not-configured'
        import ssl
        cert = ssl.get_default_verify_paths().cafile
        if cert: env['SSL_CERT_FILE'] = cert
    if name == 'vibe':
        # The user's shared Kurt setup is authoritative, even after key rotation
        # in a running chat. Never inherit a stale shell key or use Vibe Keychain.
        from kurt.utils.env_loader import setup_mistral_key
        env.pop('MISTRAL_API_KEY', None)
        key = setup_mistral_key()
        if key:
            env['MISTRAL_API_KEY'] = key
        # Exact, read-only connector tools. Other tool permissions remain intact.
        env['VIBE_TOOLS'] = json.dumps({
            'connector_web_search_news_search': {'permission': 'always'},
            'connector_web_search_web_search': {'permission': 'always'},
        })
        import ssl
        cert = ssl.get_default_verify_paths().cafile
        if cert:
            env['SSL_CERT_FILE'] = cert
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


def run_ai_cli(cmd, args):
    """Return structured process status for the existing AI CLI adapters."""
    from kurt.utils.process import run_bounded
    from kurt.utils.workspace import current_workspace
    from kurt.billing.client import active, CLI_CONTEXT, cli_session
    name = Path(cmd).name
    if name.lower().endswith(('.cmd','.exe','.bat')): name=Path(name).stem
    if active() and CLI_CONTEXT.get() is None and args not in (['--version'], ['--help']):
        with cli_session(name):
            return run_ai_cli(cmd, args)
    if name not in {"claude", "gemini", "vibe"}:
        raise ValueError("Expected Claude Code, Gemini or Vibe CLI.")
    env = _ai_cli_env(cmd)
    if name == 'gemini' and args not in (['--version'], ['--help']) and not active():
        # Pin a current model instead of the CLI's overloaded/retired auto route.
        # Explicit caller selection wins; wallet routing chooses its own model.
        if not any(arg in ('-m', '--model') or arg.startswith(('--model=', '-m=')) for arg in args):
            model = os.getenv('KURT_GEMINI_MODEL', '').strip() or 'gemini-3.8-flash'
            args = [*args, '--model', model]
    if name == 'vibe' and args != ['--version'] and not env.get('MISTRAL_API_KEY'):
        raise ValueError('Vibe CLI uses the Mistral API key from Kurt /setup. Configure MISTRAL_API_KEY there first; no Vibe request was sent.')
    return run_bounded(service_argv([cmd, *args], name),
                       env=env, cwd=str(current_workspace()), timeout=120, max_output=65536)


def _run_shell(cmd: str, args: str) -> str:
    """Run a shell command and return output"""
    full_cmd = f"{cmd} {args}".strip()
    try:
        name = Path(cmd).name
        if name.lower().endswith(('.cmd','.exe','.bat')): name=Path(name).stem
        trusted = name in {"claude", "gemini", "gh"}
        runner = subprocess.run if trusted else restricted_run
        from kurt.utils.workspace import current_workspace
        if trusted and name in {"claude", "gemini"}:
            result = run_ai_cli(cmd, shlex.split(args))
            out, err = redact(result['stdout'].strip()), redact(result['stderr'].strip())
            if result['status'] != 'completed':
                if name == 'gemini':
                    from kurt.core.execution_preferences import cli_failure_detail
                    return f"❌ Error:\n{cli_failure_detail(name, result)}"
                detail = err or f"CLI status: {result['status']}; exit code: {result['exit_code']}."
                return f"❌ Error:\n{detail}\n[stdout]\n{out}" if out else f"❌ Error:\n{detail}"
            return out or '(no output)'
        options = {"env": _ai_cli_env(cmd), "cwd": str(current_workspace())} if trusted else {}
        result = runner(
            service_argv([cmd, *shlex.split(args)], name) if trusted else full_cmd,
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
    current_cli: str = "auto",
) -> SlashResult:
    """
    Check if prompt is a slash command. Returns SlashResult.
    If not a slash command, returns SlashResult(handled=False).
    """

    p = prompt.strip()
    from kurt.core.attachments import is_local_path_input
    if is_local_path_input(p):
        return SlashResult(handled=False, output='', continue_chat=True)

    # Typing the literal CLI invocation instead of the in-chat command is an
    # easy slip — the chat's own prompt line also just reads "kurt ...".
    # Without this, it falls straight through to the AI as a normal message
    # and Kurt free-associates a vague "do you want help setting up?" reply
    # instead of actually opening the setup wizard.
    if p.lower().rstrip(".!? ") in ("kurt setup", "kurt setup wizard"):
        p = "/setup"

    if not p.startswith("/"):
        return SlashResult(handled=False, output="", continue_chat=True)

    # Split into command + args
    parts = p.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    if cmd == "/setting":
        cmd = "/config"

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

    if cmd == '/wallet':
        from kurt.billing.commands import slash
        try: output = json.dumps(slash(args), ensure_ascii=False, indent=2)
        except (ValueError, OSError, RuntimeError) as exc: output = str(exc)
        return SlashResult(True, output, True)

    if cmd == '/speech':
        from kurt.core.speech_recognition import slash
        try: output=slash(args)
        except (ValueError,OSError) as exc: output=str(exc)
        return SlashResult(True,output,True)

    if cmd in ('/image', '/video'):
        from kurt.core.media_generation import generate_selected_media
        kind = cmd[1:]
        if not args.strip():
            return SlashResult(True, f'Usage: {cmd} <generation prompt>. Uses the saved {kind} model.', True)
        try:
            result = generate_selected_media(kind, args)
            output = json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            output = f'Generation failed; no alternate model was used. {redact(str(exc))[:1000]}'
        return SlashResult(True, output, True, feed_to_ai=True)

    if cmd in ("/image-model", "/video-model"):
        from kurt.core.execution_preferences import save_default_media, media_label
        kind = "image" if cmd == "/image-model" else "video"
        fields = args.split()
        if not fields:
            return SlashResult(True, f"Default {kind}: {media_label(kind)}\nSet: {cmd} <model-id> fal|replicate | {cmd} auto", True)
        if fields == ["choose"]:
            import sys
            if not sys.stdin.isatty():
                return SlashResult(True, f"Set: {cmd} <model-id> fal|replicate", True)
            from rich.prompt import Prompt
            try:
                provider = Prompt.ask("Generation provider", choices=["fal", "replicate", 'wavespeed'])
                model_id = Prompt.ask(f"Exact text-to-{kind} model ID")
                save_default_media(kind, model_id, provider)
            except (KeyboardInterrupt, EOFError):
                return SlashResult(True, "Cancelled; defaults unchanged.", True)
            except ValueError as exc:
                return SlashResult(True, str(exc), True)
        else:
            if len(fields) > 2:
                return SlashResult(True, f"Usage: {cmd} <model-id> [fal|replicate]", True)
            try:
                save_default_media(kind, fields[0], fields[1] if len(fields) == 2 else None)
            except ValueError as exc:
                return SlashResult(True, str(exc), True)
        return SlashResult(True, f"Default {kind} generator saved: {media_label(kind)}. Applies to new generation requests and the next welcome banner.", True)

    # ── /model ──────────────────────────────────────────────────────
    if cmd == "/model":
        from kurt.core.execution_preferences import save_default_model
        if args.strip() == "choose-default":
            import sys
            if not sys.stdin.isatty():
                return SlashResult(True, "Set: /model default <model-id> [provider]. Example: /model default mistral-small-latest mistral", True)
            from rich.prompt import Prompt
            from kurt.core.execution_preferences import TEXT_PROVIDERS
            try:
                provider = Prompt.ask("Chat provider", choices=list(TEXT_PROVIDERS), default="openrouter")
                model_id = Prompt.ask("Exact model ID from your provider's model list")
                selected = save_default_model(model_id, provider)
            except (KeyboardInterrupt, EOFError):
                return SlashResult(True, "Cancelled; defaults unchanged.", True)
            except ValueError as exc:
                return SlashResult(True, str(exc), True)
            return SlashResult(True, f"Default model saved: {selected}. CLI mode: auto.",
                               True, model_override=selected, cli_override="auto")
        if args.split()[:1] == ["default"]:
            parts = args.split()[1:]
            if not parts:
                from kurt.core.persona import load_persona
                return SlashResult(True, f"Saved model: {load_persona().get('default_model', 'auto')}\nUsage: /model default <model-id> [provider]", True)
            if len(parts) > 2:
                return SlashResult(True, "Usage: /model default <model-id> [provider]", True)
            try:
                selected = save_default_model(parts[0], parts[1] if len(parts) == 2 else None)
            except ValueError as exc:
                return SlashResult(True, str(exc), True)
            return SlashResult(True, f"Default model saved: {selected}. CLI mode: auto. Applies now and to new chats.",
                               True, model_override=selected, cli_override="auto")
        if not args:
            return SlashResult(
                handled=True,
                output=(
                    f"Current model: {current_model}\n"
                    "Usage: /model <model-id> [provider] (this session)\n"
                    "Save default: /model default <model-id> [provider]\n"
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
        from kurt.core.execution_preferences import PROVIDERS
        if len(parts) == 2 and parts[1] in PROVIDERS:
            model_id, explicit_provider = parts
            return SlashResult(
                handled=True,
                output=f"✅ Switched to model: {model_id}  [{explicit_provider}]",
                continue_chat=True,
                model_override=f"{model_id}|{explicit_provider}",
            )
        from kurt.core.execution_preferences import parse_model
        try:
            parse_model(args)
        except ValueError as exc:
            return SlashResult(True, str(exc), True)
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
            f"  CLI         : {current_cli}",
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
        if args.strip() in ("model", "cli", "image", "video"):
            from kurt.core.persona import load_persona
            settings = load_persona()
            kind = args.strip()
            usage = "/model default <model-id> [provider]" if kind == "model" else (f"/{kind}-model <model-id> fal|replicate" if kind in ("image", "video") else "/cli default <name>")
            key = f"default_{kind}_model" if kind in ("image", "video") else f"default_{kind}"
            return SlashResult(True, f"Default {kind}: {settings.get(key, 'auto')}\nSet: {usage}\nOr choose from / → /config → {kind}.", True)
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

    # ── /setup ──────────────────────────────────────────────────────
    # API keys (Groq, OpenRouter, Composio, ...) — distinct from "/config
    # setup", which is the persona wizard (theme/name/language/icon).
    if cmd == "/setup":
        from kurt.utils.setup import run_setup
        run_setup()
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
        if args.strip() != 'routing':
            from kurt.core.command_palette import _catalog_models, refresh_model_catalogs
            from kurt.models.catalog import groups, category_label
            if args.strip() == 'refresh':
                return SlashResult(handled=True, output=refresh_model_catalogs(), continue_chat=True)
            lines = ['Complete provider model catalogs (cached; not a live inference test)']
            for provider in ('openrouter', 'fal'):
                models = _catalog_models(provider)
                grouped = groups(provider, models)
                lines.append(f'\n{provider}: {len(models):,} unique model IDs')
                lines.extend(f'  {category_label(provider, cat)}: {len(items):,}' for cat, items in grouped.items())
            lines += ['\nOpen /models in the picker to browse every model and its supported defaults.',
                      'Refresh: /models refresh | Routing rules: /models routing']
            return SlashResult(handled=True, output='\n'.join(lines), continue_chat=True)
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
        from kurt.core.execution_preferences import DEFAULT_CLIS, save_default_cli, cli_platform_limit
        parts = args.split()
        if len(parts) == 2 and parts[0] in ('probe', 'test'):
            from kurt.core.cli_readiness import probe_clis, test_default_cli
            try:
                if parts[0] == 'probe':
                    entries = probe_clis(parts[1])
                    report = entries if parts[1] == 'all' else entries[0]
                else:
                    report = test_default_cli(parts[1])
            except ValueError as exc:
                return SlashResult(True, str(exc), True)
            return SlashResult(True, json.dumps(report, indent=2), True)
        if parts and parts[0] in ("default", "use"):
            if len(parts) != 2 or parts[1] not in DEFAULT_CLIS:
                return SlashResult(True, "Usage: /cli default|use " + "|".join(DEFAULT_CLIS), True)
            selected = parts[1]
            if cli_platform_limit(selected):
                return SlashResult(True, cli_platform_limit(selected), True)
            if parts[0] == "default":
                save_default_cli(selected)
            scope = "Default saved" if parts[0] == "default" else "This session"
            return SlashResult(True, f"{scope}: CLI {selected}. Auto uses the selected API model. Login/setup must be ready.",
                               True, cli_override=selected)
        if args in ("", "status"):
            from kurt.core.persona import load_persona
            settings = load_persona()
            rows = [f"Current CLI: {current_cli}", f"Saved default CLI: {settings.get('default_cli', 'auto')}",
                    f"Saved default model: {settings.get('default_model', 'auto')}"]
            rows.extend(f"{name}: {'installed' if _cmd_exists(name) else 'not installed'}" for name in DEFAULT_CLIS if name != "auto")
            rows.append("Set default: /cli default <name> | Session only: /cli use <name> | Versions: /cli probe all | Live response: /cli test <name> (may use credits)")
            return SlashResult(True, "\n".join(rows), True)
        from kurt.core.cli_tools import cli_status
        if args not in ("", "status", "probe"):
            return SlashResult(True, "Usage: /cli status | /cli probe [all|name] | /cli test <name> (may use credits) | /cli default <name> | /cli use <name>", True)
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
        if args in ("", "status"):
            return SlashResult(True, json.dumps(codex_status(),ensure_ascii=False),True)
        try:
            result=run_codex(args,cwd=Path.cwd())
            return SlashResult(True,json.dumps(result,ensure_ascii=False),True,feed_to_ai=True)
        except (ValueError,OSError,RuntimeError) as exc:
            return SlashResult(True,"Codex delegation failed: "+redact(str(exc)),True)

    # ── /claude ─────────────────────────────────────────────────────
    if cmd == '/copilot':
        if not args.strip():
            return SlashResult(True, 'Usage: /copilot <task>. Install: npm install. Login: node_modules/.bin/copilot login. Read-only delegation; wallet mode uses its configured API provider.', True)
        from kurt.core.execution_preferences import run_default_cli
        try:
            output = run_default_cli('copilot', [{'role': 'user', 'content': args}])
        except (ValueError, OSError, RuntimeError) as exc:
            output = f'Copilot request incomplete; task was not replayed. {redact(str(exc))}'
        return SlashResult(True, output, True, feed_to_ai=True)

    if cmd in ('/deepseek', '/deepseek-cli'):
        if not args.strip():
            return SlashResult(True, f'Usage: {cmd} <task>. Uses DEEPSEEK_API_KEY from Kurt /setup; project files are read-only.', True)
        from kurt.core.execution_preferences import run_default_cli
        try:
            output = run_default_cli(cmd[1:], [{'role': 'user', 'content': args}])
        except (ValueError, OSError, RuntimeError) as exc:
            output = f'DeepSeek request incomplete; task was not replayed. {redact(str(exc))}'
        return SlashResult(True, output, True, feed_to_ai=True)

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

        if sub_cmd == "platform":
            from kurt.core.mcp_commands import connect_platform
            connect_platform(sub_args)
            return SlashResult(handled=True, output="", continue_chat=True)

        if sub_cmd in ("catalog", "search", "config", "connect", "import"):
            from kurt.core.mcp_commands import chat_command
            try:
                output = chat_command(sub_cmd, sub_args)
            except (ValueError, OSError) as exc:
                output = f"MCP: {exc}"
            return SlashResult(handled=True, output=output, continue_chat=True)

        # "connect-preset" is a legacy spelling kept for compatibility —
        # both now go through the same unified connect flow.
        if sub_cmd in ("authorize", "connect-preset"):
            from kurt.core.mcp_commands import connect_entry
            if not sub_args:
                return SlashResult(handled=True, output=f"Usage: /mcp {sub_cmd} <preset or server-id>", continue_chat=True)
            ref, marker, option = sub_args.rpartition(" --variant ")
            if marker:
                if not option.isdigit():
                    return SlashResult(handled=True, output="Variant must be a non-negative number.", continue_chat=True)
                connect_entry(ref, variant=int(option))
            else:
                connect_entry(sub_args)
            # connect_entry prints its own progress/result straight to the console.
            return SlashResult(handled=True, output="", continue_chat=True)

        if sub_cmd == "list":
            from kurt.core.mcp_client import load_registry
            registry = load_registry()
            if not registry:
                return SlashResult(
                    handled=True,
                    output="No MCP connections.\nAdd one: kurt mcp add <name> --url <url>",
                    continue_chat=True,
                )
            lines = ["", "🔌 Saved MCP Servers (not a live connection check)", "─" * 40]
            for name, conn in registry.items():
                target = conn.command or "remote endpoint"
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
                if sub_args and name != sub_args:
                    continue
                if not conn.enabled:
                    lines.append(f"[{name}] Saved but disabled.")
                    continue
                from kurt.core.mcp_client import probe_connection as _list_tools
                try:
                    tools = _asyncio.run(_list_tools(conn))
                    lines.append(f"\n[{name}]")
                    for t in tools[:8]:
                        lines.append(f"  • {t.name}  {t.description[:50]}")
                except Exception as e:
                    from kurt.core.mcp_client import connection_error
                    lines.append(f"\n[{name}] Connection failed: {connection_error(e)}")
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
            output="Usage: /mcp catalog | search <app> | authorize <id> | config <id> | connect <JSON or URL> | list | tools | call server/tool {params}",
            continue_chat=True,
        )

    # ── /connect (Composio app connectors — Gmail, Slack, Shopify...) ──
    if cmd == "/connect":
        from kurt.hub.composio import composio_list, composio_connect, composio_status
        sub = args.split(None, 1)
        sub_cmd = sub[0].strip() if sub else ""

        if not sub_cmd or sub_cmd.lower() == "list":
            composio_list()
        elif sub_cmd.lower() == "status":
            composio_status()
        elif sub_cmd.lower() == "search":
            composio_list(search=sub[1].strip() if len(sub) > 1 else "")
        else:
            composio_connect(sub_cmd)
        # composio_list/status/connect print their own Rich panels/tables
        # straight to the console — nothing left to echo back here.
        return SlashResult(handled=True, output="", continue_chat=True)

    # ── /zapier (9,000+ app directory — no per-app API, so "open" just
    # hands you the real Zapier integration page instead of faking a
    # connect step Zapier doesn't expose to third parties) ─────────────
    if cmd == "/zapier":
        from kurt.hub.mcp_servers import zapier_list, zapier_open
        sub = args.split(None, 1)
        sub_cmd = sub[0].lower() if sub else ""
        sub_args = sub[1].strip() if len(sub) > 1 else ""
        if sub_cmd == "open":
            if not sub_args:
                return SlashResult(handled=True, output="Usage: /zapier open <app-slug>", continue_chat=True)
            zapier_open(sub_args)
        elif sub_cmd == "search":
            zapier_list(search=sub_args)
        else:
            zapier_list(search=args.strip() or None)
        return SlashResult(handled=True, output="", continue_chat=True)

    # ── /n8n (2,000+ integration directory — same reasoning as /zapier) ─
    if cmd == "/n8n":
        from kurt.hub.mcp_servers import n8n_list, n8n_open
        sub = args.split(None, 1)
        sub_cmd = sub[0].lower() if sub else ""
        sub_args = sub[1].strip() if len(sub) > 1 else ""
        if sub_cmd == "open":
            if not sub_args:
                return SlashResult(handled=True, output="Usage: /n8n open <integration-slug>", continue_chat=True)
            n8n_open(sub_args)
        elif sub_cmd == "search":
            n8n_list(search=sub_args)
        else:
            n8n_list(search=args.strip() or None)
        return SlashResult(handled=True, output="", continue_chat=True)

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
