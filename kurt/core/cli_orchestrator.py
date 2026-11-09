"""
KURT CLI Orchestrator
Handles slash commands inside `kurt chat` — routes to Claude Code CLI,
Gemini CLI, gh CLI, and other terminal tools.
"""

import os
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
    # Fallback: npx (still uses project node_modules first)
    return f"npx --prefix {PROJECT_ROOT} {name}"


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
    # ── AI Tools — models, skills, and native workflows ─────────────
    "/model":     "Switch the AI model  e.g. /model openai/gpt-oss-120b",
    "/models":    "Show the live model routing table  e.g. /models",
    "/skill":     "Apply a skill to the next message  e.g. /skill tiktok",
    "/skills":    "List or search Kurt's loaded skills  e.g. /skills trading",
    "/library":   "Run a native data workflow (local, no AI call)  e.g. /library stats",
    # ── System — shell out to other dev tools ───────────────────────
    "/run":       "Run a shell command  e.g. /run ls -la",
    "/gh":        "Run GitHub CLI  e.g. /gh pr list",
    "/claude":    "Delegate to Claude Code CLI  e.g. /claude \"review main.py for bugs\"",
    "/gemini":    "Delegate to Gemini CLI  e.g. /gemini \"what is in this repo?\"",
    "/mcp":       "Connect to & call outside tools  e.g. /mcp list   |   /mcp tools filesystem",
    # ── Web & Computer — browsing and desktop control ────────────────
    "/web":       "Fetch a page or search the web  e.g. /web https://example.com",
    "/browser":   "Control a real (Playwright) browser  e.g. /browser open https://example.com",
    "/computer":  "Control the Mac desktop  e.g. /computer screenshot",
}

SLASH_GROUPS = [
    ("🧭 Navigation", ["/help", "/clear", "/exit", "/quit", "/history", "/info", "/save"]),
    ("🧠 AI Tools", ["/model", "/models", "/skill", "/skills", "/library"]),
    ("⚙️  System", ["/run", "/gh", "/claude", "/gemini", "/mcp"]),
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


def _run_shell(cmd: str, args: str) -> str:
    """Run a shell command and return output"""
    full_cmd = f"{cmd} {args}".strip()
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode != 0 and err:
            return f"[stderr]\n{err}\n[stdout]\n{out}" if out else f"❌ Error:\n{err}"
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
        lines += ["", "Tip: /claude, /gemini, /gh pipe directly to their CLIs"]
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
                    "  Groq (libre, mabilis): /model openai/gpt-oss-120b\n"
                    "  Groq (pinakamabilis):  /model llama-3.1-8b-instant\n"
                    "  OpenRouter free:      /model google/gemma-3-27b-it:free\n"
                    "  Auto-route:           /model auto"
                ),
                continue_chat=True,
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
        lines = [
            "",
            "ℹ️   KURT Session Info",
            "─" * 35,
            f"  Session ID  : {session_id[:8]}…",
            f"  Model       : {current_model}",
            f"  Skill       : {current_skill or 'none'}",
            f"  Claude CLI  : {'✅ installed' if _cmd_exists('claude') else '❌ not found'}",
            f"  Gemini CLI  : {'✅ installed' if _cmd_exists('gemini') else '❌ not found'}",
            f"  gh CLI      : {'✅ installed' if _cmd_exists('gh') else '❌ not found'}",
            "",
        ]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

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
        output = _run_shell(claude_cmd, f'--print "{args}"')
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
        output = _run_shell(gemini_cmd, f'-p "{args}"')
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

        return SlashResult(
            handled=True,
            output="Usage: /computer screenshot | /computer type <text> | /computer click <x> <y>",
            continue_chat=True,
        )

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
