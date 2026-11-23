"""Standalone wrappers — same dispatcher as the "/" commands inside kurt
chat, just runnable without opening a session first. No logic is
duplicated here; each one builds the slash-command string and reuses
handle_slash() exactly as the chat loop does."""

import uuid
from typing import Optional

import typer

from kurt.core.cli_orchestrator import handle_slash


def _run_slash_standalone(cmd_line: str) -> str:
    result = handle_slash(
        prompt=cmd_line,
        session_id=str(uuid.uuid4()),
        current_model="auto",
        current_skill=None,
    )
    return result.output


def register_commands(app: typer.Typer, console) -> None:
    @app.command(rich_help_panel="🤝 Delegate to Other CLIs")
    def gh(args: str = typer.Argument(..., help="Arguments to pass straight to the GitHub CLI")):
        """🐙 Run a GitHub CLI command — same as /gh inside chat.

        Halimbawa (example): kurt gh "pr list"
        """
        console.print(_run_slash_standalone(f"/gh {args}"), markup=False)

    @app.command(rich_help_panel="🤝 Delegate to Other CLIs")
    def codex(args: str = typer.Argument("", help="Task for Codex CLI, or omit for status")):
        """🧠 Delegate a coding task to installed Codex CLI (read-only by default) — same as /codex inside chat."""
        console.print(_run_slash_standalone(f"/codex {args}".strip()), markup=False)

    @app.command(rich_help_panel="🤝 Delegate to Other CLIs")
    def claude(prompt: str = typer.Argument(..., help="Prompt to send to Claude Code CLI")):
        """🤖 Delegate a task to Claude Code CLI — same as /claude inside chat.

        Halimbawa (example): kurt claude "review main.py for bugs"
        """
        console.print(_run_slash_standalone(f"/claude {prompt}"), markup=False)

    @app.command(rich_help_panel="🤝 Delegate to Other CLIs")
    def gemini(prompt: str = typer.Argument(..., help="Prompt to send to Gemini CLI")):
        """✨ Delegate a task to Gemini CLI — same as /gemini inside chat.

        Halimbawa (example): kurt gemini "what is in this repo?"
        """
        console.print(_run_slash_standalone(f"/gemini {prompt}"), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def subagent(
        task: str = typer.Argument(..., help="Clear, actionable task for the subagent"),
        role: str = typer.Option("research", "--role", "-r", help="research, coder, mac-doctor, qa-verifier, or custom"),
    ):
        """🤖 Launch an autonomous subagent with its own context window — same as /subagent inside chat.

        Halimbawa (example): kurt subagent "find all API endpoints" --role research
        """
        console.print(_run_slash_standalone(f"/subagent {role} | {task}"), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def plan(
        title: str = typer.Argument(..., help="Plan title / goal"),
        step: list[str] = typer.Option(None, "--step", help="Repeatable — one implementation step per flag"),
    ):
        """📋 Create a structured Markdown implementation plan artifact — same as /plan inside chat.

        Halimbawa (example): kurt plan "Refactor Auth" --step "Audit current flow" --step "Write tests"
        """
        cmd_line = f"/plan {title} | {'; '.join(step)}" if step else f"/plan {title}"
        console.print(_run_slash_standalone(cmd_line), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def tasks(
        action: str = typer.Argument("list", help="list, start, status, or kill"),
        arg: str = typer.Argument("", help="Command (for start) or task ID (for status/kill)"),
    ):
        """🗂️  Manage background shell processes (dev servers, watchers, long builds) — same as /tasks inside chat.

        Halimbawa (example): kurt tasks start "npm run dev"
        """
        console.print(_run_slash_standalone(f"/tasks {action} {arg}".strip()), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def zip(
        action: str = typer.Argument(..., help="export or import"),
        source: str = typer.Argument(..., help="Folder to export, or .zip file to import"),
        destination: Optional[str] = typer.Argument(None, help="Output .zip path (export) or destination folder (import)"),
    ):
        """🗜️  Export a folder to .zip or import a .zip into a folder — same as /zip inside chat.

        Halimbawa (example): kurt zip export ~/Projects/myapp
        """
        cmd_line = f"/zip {action} {source}" + (f" {destination}" if destination else "")
        console.print(_run_slash_standalone(cmd_line), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def web(
        target: str = typer.Argument(..., help="A URL to read, or 'search <query>'"),
    ):
        """🌐 Fetch a web page, or search the web — same as /web inside chat.

        Halimbawa (example): kurt web "search sari-sari store profit margin"
        """
        console.print(_run_slash_standalone(f"/web {target}"), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def browser(
        action: str = typer.Argument(..., help="open, screenshot, click, fill, or close"),
        args: str = typer.Argument("", help="Arguments for the action, e.g. a URL for 'open'"),
    ):
        """🧭 Control a real (Playwright) browser — same as /browser inside chat. Each CLI call is a
        fresh session (state doesn't persist between separate `kurt browser ...` invocations); use
        `kurt chat` instead for a multi-step browsing session.

        Halimbawa (example): kurt browser open https://example.com
        """
        console.print(_run_slash_standalone(f"/browser {action} {args}".strip()), markup=False)

    @app.command(rich_help_panel="🖱️  Automate")
    def computer(
        action: str = typer.Argument(..., help="screenshot, analyze, type, click, or open"),
        args: str = typer.Argument("", help="Arguments for the action"),
    ):
        """🖥️  Control the Mac desktop (screenshot, vision analysis, type, click, open folder) —
        same as /computer inside chat.

        Halimbawa (example): kurt computer screenshot
        """
        console.print(_run_slash_standalone(f"/computer {action} {args}".strip()), markup=False)
