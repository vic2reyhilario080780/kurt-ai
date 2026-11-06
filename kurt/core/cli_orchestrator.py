"""
KURT CLI Orchestrator
Handles slash commands inside `kurt chat` — routes to Claude Code CLI,
Gemini CLI, gh CLI, and other terminal tools.
"""

import os
import subprocess
import shutil
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


# ─────────────────────────────────────────
# Slash command registry
# ─────────────────────────────────────────

SLASH_COMMANDS = {
    "/help":      "Show all slash commands",
    "/clear":     "Start a new session",
    "/exit":      "Exit chat",
    "/quit":      "Exit chat",
    "/model":     "Switch AI model  e.g. /model gemini-flash",
    "/skill":     "Apply a skill   e.g. /skill tiktok",
    "/claude":    "Run Claude Code CLI  e.g. /claude 'review this file'",
    "/gemini":    "Run Gemini CLI   e.g. /gemini 'what is in this repo?'",
    "/gh":        "Run GitHub CLI   e.g. /gh pr list",
    "/run":       "Run a shell cmd  e.g. /run ls -la",
    "/models":    "Show available AI models",
    "/skills":    "Show skill categories",
    "/history":   "Show session history",
    "/save":      "Save last response as a file",
    "/info":      "Show KURT session info",
    "/mcp":       "MCP tools: /mcp list | /mcp tools | /mcp call server/tool",
}


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
        lines = ["", "📖  KURT Slash Commands", "─" * 40]
        for slash, desc in SLASH_COMMANDS.items():
            lines.append(f"  {slash:<12}  {desc}")
        lines += ["", "Tip: /claude, /gemini, /gh pipe directly to their CLIs"]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    # ── /exit /quit ─────────────────────────────────────────────────
    if cmd in ("/exit", "/quit"):
        return SlashResult(handled=True, output="👋 Bye! K.U.R.T. signing off.", continue_chat=False)

    # ── /model ──────────────────────────────────────────────────────
    if cmd == "/model":
        if not args:
            return SlashResult(
                handled=True,
                output=f"Current model: {current_model}\nUsage: /model <name>  e.g. /model gemini-flash",
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
        return SlashResult(
            handled=True,
            output=f"✅ Skill activated: {args}  (will apply on next message)",
            continue_chat=True,
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
        lines = [
            "",
            "🤖  Quick Model Reference",
            "─" * 42,
            "  FREE (via OpenRouter)",
            "    meta-llama/llama-3.3-70b-instruct:free",
            "    google/gemini-flash-1.5",
            "    deepseek/deepseek-coder",
            "    deepseek/deepseek-r1",
            "  PAID",
            "    anthropic/claude-3.5-sonnet",
            "    openai/gpt-4o",
            "    anthropic/claude-3-5-haiku",
            "",
            "Switch: /model <model-name>",
        ]
        return SlashResult(handled=True, output="\n".join(lines), continue_chat=True)

    # ── /skills ─────────────────────────────────────────────────────
    if cmd == "/skills":
        lines = [
            "",
            "🧠  Skill Categories (top 10)",
            "─" * 40,
            "  eng, code, files, designs, pipelines,",
            "  tickets, notes, apis, refdocs, aiagents…",
            "",
            "Full list: `kurt skill --help`",
            "Apply skill: /skill <name>",
        ]
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
        return SlashResult(handled=True, output=f"🤖 Claude Code:\n\n{output}", continue_chat=True)

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
        return SlashResult(handled=True, output=f"✨ Gemini:\n\n{output}", continue_chat=True)

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
            output="Usage: /mcp list | /mcp tools | /mcp call server/tool {params}",
            continue_chat=True,
        )

    # ── Unknown slash command ────────────────────────────────────────
    return SlashResult(
        handled=True,
        output=f"❓ Unknown command: {cmd}\nType /help to see all commands.",
        continue_chat=True,
    )
