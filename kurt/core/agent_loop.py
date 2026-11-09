"""
KURT Agent Loop — Phase 3
Multi-step agentic task execution. Routes tool calls and loops until done.
Like Claude Code CLI's agentic mode — plan → execute → verify → repeat.
"""

import os
import re
import json
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box

from kurt.core.file_ops import (
    read_file, read_file_summary, apply_edit,
    write_new_file, run_file, run_code_string, list_dir
)
from kurt.core.mcp_client import (
    load_registry, list_tools as mcp_list_tools,
    call_tool as mcp_call_tool, execute_mcp_tool
)

console = Console()

MAX_STEPS = 15  # Safety limit — prevent infinite loops


# ─────────────────────────────────────────────────────────────
# Tool Definitions (what the AI can call)
# ─────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_native",
        "description": "Find executable Kurt-native CSV/JSON data workflows. Returns IDs and names; search by domain, metric or operation.",
        "parameters": {"query": "string", "kind": "optional: skill, agent or plugin", "limit": "optional integer, default 10"},
    },
    {
        "name": "run_native",
        "description": "Execute a native data workflow ID on a user-supplied CSV/JSON file. Requires no API key and never modifies the input. Returns a descriptive report, not external app actions.",
        "parameters": {"capability_id": "string from search_native", "input_path": "string: user's CSV/JSON path"},
    },
    {
        "name": "read_file",
        "description": "Read a file's contents. Use for understanding code before editing.",
        "parameters": {
            "path": "string — file path to read",
            "lines": "optional string — line range like '10-25' or single line '10'",
        },
    },
    {
        "name": "list_dir",
        "description": "List directory contents as a tree. Use to understand project structure.",
        "parameters": {
            "path": "string — directory path (default: '.')",
            "depth": "int — tree depth 1-3 (default: 2)",
        },
    },
    {
        "name": "edit_file",
        "description": "Edit a file by replacing exact text. MUST read the file first. old_str must be unique.",
        "parameters": {
            "path": "string — file path",
            "old_str": "string — exact text to replace (unique in file)",
            "new_str": "string — replacement text",
        },
    },
    {
        "name": "create_file",
        "description": "Create a new file with content. Only for files that don't exist yet.",
        "parameters": {
            "path": "string — file path to create",
            "content": "string — full file content",
        },
    },
    {
        "name": "run_file",
        "description": "Execute a .py, .sh, or .js file and return output. Use to verify fixes.",
        "parameters": {
            "path": "string — file to run",
            "args": "optional string — command line args",
        },
    },
    {
        "name": "run_code",
        "description": "Run a code snippet directly (without saving to file first).",
        "parameters": {
            "code": "string — code to execute",
            "lang": "string — 'python', 'bash', or 'javascript'",
        },
    },
    {
        "name": "bash",
        "description": "Run a bash command. Use for git, grep, find, pip install, etc.",
        "parameters": {
            "cmd": "string — bash command to run",
        },
    },
    {
        "name": "done",
        "description": "Signal that the task is complete. Include a summary of what was done.",
        "parameters": {
            "summary": "string — what was accomplished",
        },
    },
    {
        "name": "mcp_tool",
        "description": "Call a tool from a connected MCP server. Use 'server_name/tool_name' format.",
        "parameters": {
            "tool_ref": "string — 'server_name/tool_name' or just 'tool_name'",
            "params": "object — tool parameters as JSON object",
        },
    },
    # ── Orchestration Tools ───────────────────────────────────
    {
        "name": "call_model",
        "description": (
            "Delegate a sub-task to a specific AI model/provider and get its full response back as text. "
            "Use this to chain models within one task — e.g. research with one model, then pass its output "
            "to a different model to rewrite or summarize."
        ),
        "parameters": {
            "provider": "string — 'groq', 'openrouter', 'anthropic', or 'ollama'",
            "model": "string — model id for that provider, e.g. 'openai/gpt-oss-120b', 'google/gemma-3-27b-it:free'",
            "prompt": "string — the task/prompt to send to that model",
        },
    },
    {
        "name": "delegate_cli",
        "description": (
            "Delegate a sub-task to an external CLI AI agent or shell and get its output back as text. "
            "Use this to hand work off to Claude Code, Gemini CLI, GitHub CLI, or a raw shell command, "
            "then continue reasoning with the result."
        ),
        "parameters": {
            "tool": "string — 'claude', 'gemini', 'gh', or 'bash'",
            "prompt": "string — the task/prompt (claude/gemini) or command/args (gh/bash)",
        },
    },
    # ── Computer Use Tools ───────────────────────────────────
    {
        "name": "screenshot",
        "description": "Take a screenshot of the current screen. Use to see what's on screen before clicking.",
        "parameters": {},
    },
    {
        "name": "click",
        "description": "Click at screen coordinates (x, y). Use screenshot first to find coordinates.",
        "parameters": {
            "x": "int — x coordinate",
            "y": "int — y coordinate",
            "button": "optional string — 'left' (default), 'right', 'double'",
        },
    },
    {
        "name": "type_text",
        "description": "Type text at current cursor position. Use after clicking an input field.",
        "parameters": {
            "text": "string — text to type",
        },
    },
    {
        "name": "hotkey",
        "description": "Press a keyboard shortcut. E.g. 'cmd+t' for new tab, 'cmd+l' to focus address bar.",
        "parameters": {
            "keys": "string — keys like 'cmd+t', 'ctrl+c', 'enter', 'tab'",
        },
    },
    {
        "name": "open_app",
        "description": "Open an application by name. Kurt will find it even if the name isn't exact.",
        "parameters": {
            "app_name": "string — application name e.g. 'Safari', 'Spotify', 'Terminal'",
        },
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default browser.",
        "parameters": {
            "url": "string — full URL to open",
        },
    },
    {
        "name": "focus_window",
        "description": "Bring an app's window to the foreground.",
        "parameters": {
            "app_name": "string — application name",
        },
    },
    {
        "name": "search_web",
        "description": "Search the web and return results. No browser needed.",
        "parameters": {
            "query": "string — search query",
            "max_results": "optional int — number of results (default 5)",
        },
    },
    {
        "name": "read_webpage",
        "description": "Read the text content of a web page.",
        "parameters": {
            "url": "string — URL to read",
        },
    },
    {
        "name": "run_applescript",
        "description": "Run an AppleScript command for Mac automation. Mac only — returns error on Windows/Linux.",
        "parameters": {
            "script": "string — AppleScript to execute",
        },
    },
]


async def _build_mcp_tools_prompt() -> str:
    """Build MCP tools section for system prompt"""
    registry = load_registry()
    enabled = {n: c for n, c in registry.items() if c.enabled}
    if not enabled:
        return ""

    lines = ["\n\nCONNECTED MCP TOOLS (use with mcp_tool):"]
    for name, conn in enabled.items():
        try:
            tools = await mcp_list_tools(conn)
            if tools:
                lines.append(f"\n[{name}]")
                for t in tools[:10]:  # Cap at 10 per server
                    params = list(t.input_schema.get("properties", {}).keys())[:4]
                    lines.append(f"  {name}/{t.name}: {t.description[:60]}"
                                 + (f"  ({', '.join(params)})" if params else ""))
        except Exception:
            pass

    return "\n".join(lines) if len(lines) > 1 else ""

TOOLS_PROMPT = """You have access to these tools. To call a tool, respond with a JSON block:
```tool
{"tool": "tool_name", "params": {"param": "value"}}
```

Available tools:
""" + "\n".join(
    f'- **{t["name"]}**: {t["description"]}\n  Params: {json.dumps(t["parameters"])}'
    for t in TOOLS
)


# ─────────────────────────────────────────────────────────────
# Agent Step
# ─────────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    step_num: int
    thought: str = ""
    tool_name: str = ""
    tool_params: dict = field(default_factory=dict)
    tool_result: str = ""
    is_done: bool = False
    done_summary: str = ""


@dataclass
class AgentResult:
    success: bool
    steps: list[AgentStep]
    final_summary: str
    files_changed: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Orchestration helpers
# ─────────────────────────────────────────────────────────────

async def _collect_model_response(provider: str, model: str, messages: list) -> str:
    """Run one model call to completion and return the full text."""
    from kurt.core.router import ModelRouter
    router = ModelRouter()
    full = ""
    async for chunk in router.route(provider=provider, model=model, messages=messages):
        full += chunk
    return full


def _run_coro_blocking(coro):
    """
    Run an async coroutine to completion from sync code, regardless of whether
    the calling thread already has a running event loop (execute_tool is called
    synchronously both from inside run_agent's active asyncio.run() loop and
    from plain sync callers like the voice-command handler). A dedicated thread
    with its own fresh loop avoids 'event loop is already running' errors either way.
    """
    import threading
    outcome = {}

    def _runner():
        try:
            outcome["value"] = asyncio.run(coro)
        except Exception as e:
            outcome["error"] = e

    t = threading.Thread(target=_runner)
    t.start()
    t.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value", "")


# ─────────────────────────────────────────────────────────────
# Tool Executor
# ─────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, params: dict) -> str:
    """Execute a tool call and return string result"""
    import subprocess

    try:
        if tool_name == "search_native":
            from kurt.capabilities.runtime import search
            return json.dumps(search(params.get("query", ""), params.get("kind"), int(params.get("limit", 10))), ensure_ascii=False)

        elif tool_name == "run_native":
            from kurt.capabilities.runtime import run_capability
            result = run_capability(params.get("capability_id", ""), input_path=params.get("input_path"))
            text = json.dumps(result, ensure_ascii=False, allow_nan=False)
            return text[:16000] + " [truncated; use kurt library run --output for the complete result]" if len(text) > 16000 else text

        elif tool_name == "read_file":
            return read_file(params.get("path", ""), params.get("lines"))

        elif tool_name == "list_dir":
            return list_dir(params.get("path", "."), int(params.get("depth", 2)))

        elif tool_name == "edit_file":
            return apply_edit(
                params.get("path", ""),
                params.get("old_str", ""),
                params.get("new_str", ""),
            )

        elif tool_name == "create_file":
            return write_new_file(params.get("path", ""), params.get("content", ""))

        elif tool_name == "run_file":
            r = run_file(params.get("path", ""), params.get("args", ""))
            if "error" in r:
                return f"❌ {r['error']}"
            out = r.get("stdout", "")
            err = r.get("stderr", "")
            rc = r.get("returncode", 0)
            rt = r.get("runtime_ms", 0)
            result = f"[Exit {rc} · {rt}ms]\n"
            if out:
                result += f"stdout:\n{out}\n"
            if err:
                result += f"stderr:\n{err}\n"
            return result.strip() or "(no output)"

        elif tool_name == "run_code":
            r = run_code_string(params.get("code", ""), params.get("lang", "python"))
            if "error" in r:
                return f"❌ {r['error']}"
            out = r.get("stdout", "")
            err = r.get("stderr", "")
            rc = r.get("returncode", 0)
            result = f"[Exit {rc}]\n"
            if out:
                result += f"stdout:\n{out}\n"
            if err:
                result += f"stderr:\n{err}\n"
            return result.strip() or "(no output)"

        elif tool_name == "bash":
            cmd = params.get("cmd", "")
            if not cmd:
                return "❌ No command given"
            # Safety check
            from kurt.core.file_ops import _is_dangerous
            danger = _is_dangerous(cmd)
            if danger:
                return f"🚨 Refused: dangerous pattern '{danger}'"
            try:
                r = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30
                )
                out = r.stdout.strip()
                err = r.stderr.strip()
                if r.returncode != 0:
                    return f"[Exit {r.returncode}]\n{err or out}"
                return out or "(no output)"
            except subprocess.TimeoutExpired:
                return "❌ Timed out (30s)"
            except Exception as e:
                return f"❌ {e}"

        elif tool_name == "mcp_tool":
            tool_ref = params.get("tool_ref", "")
            mcp_params = params.get("params", {})
            if not tool_ref:
                return "❌ mcp_tool requires 'tool_ref'"
            return _run_coro_blocking(execute_mcp_tool(tool_ref, mcp_params))

        # ── Orchestration Tools ───────────────────────────────────

        elif tool_name == "call_model":
            provider = (params.get("provider") or "").strip().lower()
            model = (params.get("model") or "").strip()
            prompt = params.get("prompt", "")
            if not provider or not model or not prompt:
                return "❌ call_model requires 'provider', 'model', and 'prompt'"
            try:
                response = _run_coro_blocking(
                    _collect_model_response(provider, model, [{"role": "user", "content": prompt}])
                )
                return response.strip() or "(empty response)"
            except Exception as e:
                return f"❌ call_model failed: {e}"

        elif tool_name == "delegate_cli":
            import shlex
            cli_tool = (params.get("tool") or "").strip().lower()
            prompt = params.get("prompt", "")
            if not cli_tool:
                return "❌ delegate_cli requires 'tool' ('claude', 'gemini', 'gh', or 'bash')"
            if not prompt:
                return "❌ delegate_cli requires 'prompt'"

            from kurt.core.cli_orchestrator import _resolve_cmd, _run_shell, _cmd_exists

            if cli_tool == "claude":
                if not _cmd_exists("claude"):
                    return "❌ Claude Code CLI not found. Run: npm install"
                return _run_shell(_resolve_cmd("claude"), f"--print {shlex.quote(prompt)}")

            elif cli_tool == "gemini":
                if not _cmd_exists("gemini"):
                    return "❌ Gemini CLI not found. Run: npm install"
                return _run_shell(_resolve_cmd("gemini"), f"-p {shlex.quote(prompt)}")

            elif cli_tool == "gh":
                if not _cmd_exists("gh"):
                    return "❌ GitHub CLI (gh) not found. Install: brew install gh"
                return _run_shell("gh", prompt)

            elif cli_tool == "bash":
                from kurt.core.file_ops import _is_dangerous
                danger = _is_dangerous(prompt)
                if danger:
                    return f"🚨 Refused: dangerous pattern '{danger}'"
                return _run_shell("", prompt)

            else:
                return f"❌ Unknown delegate_cli tool: {cli_tool}. Use 'claude', 'gemini', 'gh', or 'bash'"

        # ── Computer Use Tools ───────────────────────────────────

        elif tool_name == "screenshot":
            from kurt.core.computer_use import screenshot
            result = screenshot()
            if result.success:
                # Return description + path
                path = result.data.get("path", "") if result.data else ""
                return f"✓ Screenshot taken: {path}\n{result.message}"
            return f"❌ {result.message}"

        elif tool_name == "click":
            from kurt.core.computer_use import click
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            button = params.get("button", "left")
            result = click(x, y, button)
            if result.success:
                return f"✓ {result.message}"
            return f"❌ {result.message}"

        elif tool_name == "type_text":
            from kurt.core.computer_use import type_text
            text = params.get("text", "")
            result = type_text(text)
            if result.success:
                return f"✓ {result.message}"
            return f"❌ {result.message}"

        elif tool_name == "hotkey":
            from kurt.core.computer_use import hotkey
            keys = params.get("keys", "")
            result = hotkey(keys)
            if result.success:
                return f"✓ {result.message}"
            return f"❌ {result.message}"

        elif tool_name == "open_app":
            from kurt.core.behavior import smart_open_app
            app_name = params.get("app_name", "")
            result = smart_open_app(app_name)
            if result.success:
                return f"✓ {result.message} [{result.method_used}]"
            return f"❌ {result.message}"

        elif tool_name == "open_url":
            from kurt.core.computer_use import open_url
            url = params.get("url", "")
            result = open_url(url)
            if result.success:
                return f"✓ {result.message}"
            return f"❌ {result.message}"

        elif tool_name == "focus_window":
            from kurt.core.computer_use import focus_window
            app_name = params.get("app_name", "")
            result = focus_window(app_name)
            if result.success:
                return f"✓ {result.message}"
            return f"❌ {result.message}"

        elif tool_name == "search_web":
            from kurt.core.web_browse import search_web
            query = params.get("query", "")
            max_r = int(params.get("max_results", 5))
            result = search_web(query, max_r)
            if result.success:
                return result.summary()
            return f"❌ {result.error}"

        elif tool_name == "read_webpage":
            from kurt.core.web_browse import read_page
            url = params.get("url", "")
            result = read_page(url)
            if result.success:
                return f"Title: {result.title}\n\n{result.content[:3000]}"
            return f"❌ {result.error}"

        elif tool_name == "run_applescript":
            import platform as _platform
            if _platform.system() != "Darwin":
                return "❌ run_applescript is Mac only. Use run_command with PowerShell (Windows) or bash (Linux) instead."
            script = params.get("script", "")
            if not script:
                return "❌ No script given"
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                return r.stdout.strip() or "✓ Script ran successfully"
            return f"❌ AppleScript error: {r.stderr.strip()}"

        elif tool_name == "done":
            return f"DONE: {params.get('summary', 'Task complete.')}"

        else:
            return f"❌ Unknown tool: {tool_name}"

    except Exception as e:
        return f"❌ Tool error: {e}"


# ─────────────────────────────────────────────────────────────
# Parse tool call from AI response
# ─────────────────────────────────────────────────────────────

def parse_tool_call(response: str) -> Optional[tuple[str, dict]]:
    """Extract tool name and params from AI response"""
    # Look for ```tool ... ``` block
    pattern = r"```tool\s*\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1).strip())
            return data.get("tool"), data.get("params", {})
        except json.JSONDecodeError:
            pass

    # Also look for plain JSON with "tool" key
    json_pattern = r'\{"tool":\s*"(\w+)"[^}]*"params":\s*(\{[^}]*\})'
    jmatch = re.search(json_pattern, response, re.DOTALL)
    if jmatch:
        try:
            tool = jmatch.group(1)
            params = json.loads(jmatch.group(2))
            return tool, params
        except Exception:
            pass

    return None, None


# ─────────────────────────────────────────────────────────────
# Main Agent Loop
# ─────────────────────────────────────────────────────────────

async def run_agent(
    task: str,
    analysis,
    router,
    cwd: str = ".",
    max_steps: int = MAX_STEPS,
    verbose: bool = False,
) -> AgentResult:
    """
    Multi-step agent loop.
    Sends task to AI → gets tool call → executes → feeds result back → repeats.
    """
    steps = []
    files_changed = []

    # Build MCP tools section
    mcp_section = await _build_mcp_tools_prompt()

    system_prompt = (
        f"You are KURT, an AI assistant for Daddy Tito's iMac. Working dir: {cwd}\n\n"
        f"{TOOLS_PROMPT}"
        f"{mcp_section}\n\n"
        "RULES:\n"
        "1. For app/browser tasks: open_app first → screenshot → click → type_text\n"
        "2. Always screenshot before clicking to see current screen state\n"
        "3. After making file changes, run the file to verify it works\n"
        "4. When done, call 'done' with a summary\n"
        "5. One tool call per response — be efficient\n"
        "6. If a tool fails, try an alternative approach\n"
        "7. For web tasks: use search_web or open_url instead of manual typing when possible\n"
        "8. Use run_applescript for Mac-only automation; use run_command with PowerShell/bash on Windows/Linux\n"
        "9. For multi-model tasks (e.g. 'research with X then write with Y'), use call_model to run a sub-task "
        "on a specific provider/model and get its text back, or delegate_cli to hand a sub-task to claude/gemini/gh/bash\n"
        "\nEXAMPLE MULTI-STEP TASK (open spotify in safari):\n"
        "Step 1: open_app('Safari')\n"
        "Step 2: screenshot() — verify Safari opened\n"
        "Step 3: hotkey('cmd+l') — focus address bar\n"
        "Step 4: type_text('spotify.com')\n"
        "Step 5: hotkey('enter')\n"
        "Step 6: screenshot() — verify page loaded\n"
        "Step 7: done('Opened spotify.com in Safari')\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {task}"},
    ]

    console.print(Panel(
        f"[bold cyan]🤖 KURT Agent Mode[/bold cyan]\n"
        f"[dim]Task: {task}[/dim]\n"
        f"[dim]Max steps: {max_steps} · Model: {analysis.model}[/dim]",
        box=box.ROUNDED, border_style="cyan"
    ))

    for step_num in range(1, max_steps + 1):
        step = AgentStep(step_num=step_num)
        steps.append(step)

        console.print(f"\n[bold cyan]Step {step_num}/{max_steps}[/bold cyan]", end="")

        # Get AI response
        full_response = ""
        try:
            with Live(Text(""), refresh_per_second=8, console=console) as live:
                async for chunk in router.route(
                    provider=analysis.provider,
                    model=analysis.model,
                    messages=messages,
                ):
                    full_response += chunk
                    # Show thinking in dim
                    preview = full_response[-200:].replace("\n", " ")
                    live.update(Text(f" {preview}", style="dim"))
        except Exception as e:
            console.print(f"\n[red]❌ AI error: {e}[/red]")
            break

        step.thought = full_response
        console.print()

        # Parse tool call
        tool_name, tool_params = parse_tool_call(full_response)

        if not tool_name:
            # AI responded but no tool call — treat as final answer
            step.is_done = True
            step.done_summary = full_response
            console.print(f"[dim]ℹ️  No tool call found — treating as final response[/dim]")
            console.print(full_response)
            break

        step.tool_name = tool_name
        step.tool_params = tool_params or {}

        # Show what tool is being called
        params_preview = json.dumps(tool_params, ensure_ascii=False)[:80] if tool_params else ""
        console.print(f"  🔧 [yellow]{tool_name}[/yellow] [dim]{params_preview}[/dim]")

        # Execute tool
        result = execute_tool(tool_name, tool_params or {})
        step.tool_result = result

        # Track edited files
        if tool_name in ("edit_file", "create_file"):
            fp = (tool_params or {}).get("path", "")
            if fp and fp not in files_changed:
                files_changed.append(fp)

        # Show result
        result_preview = result[:300] + "…" if len(result) > 300 else result
        console.print(f"  [green]→[/green] [dim]{result_preview}[/dim]")

        # Check if done
        if tool_name == "done" or result.startswith("DONE:"):
            step.is_done = True
            step.done_summary = tool_params.get("summary", result)
            console.print(f"\n[bold green]✅ Agent done![/bold green]")
            console.print(f"[dim]{step.done_summary}[/dim]")
            break

        # Feed result back to AI
        messages.append({"role": "assistant", "content": full_response})
        messages.append({"role": "user", "content": f"Tool result:\n{result}"})

    else:
        console.print(f"\n[yellow]⚠️  Reached max steps ({max_steps})[/yellow]")

    # Build summary
    done_step = next((s for s in reversed(steps) if s.is_done), None)
    summary = done_step.done_summary if done_step else f"Completed {len(steps)} steps"

    return AgentResult(
        success=bool(done_step),
        steps=steps,
        final_summary=summary,
        files_changed=files_changed,
    )
