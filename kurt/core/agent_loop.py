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
# Tool Executor
# ─────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, params: dict) -> str:
    """Execute a tool call and return string result"""
    import subprocess

    try:
        if tool_name == "read_file":
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
            import asyncio as _asyncio
            loop = _asyncio.get_event_loop()
            return loop.run_until_complete(execute_mcp_tool(tool_ref, mcp_params))

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
        f"You are KURT, an AI coding assistant. You are working in directory: {cwd}\n\n"
        f"{TOOLS_PROMPT}"
        f"{mcp_section}\n\n"
        "Rules:\n"
        "1. Always read a file before editing it.\n"
        "2. After making changes, run the file to verify it works.\n"
        "3. When done, call the 'done' tool with a summary.\n"
        "4. Be concise. One tool call per response.\n"
        "5. If you encounter an error, fix it and try again.\n"
        "6. For MCP tools, use: mcp_tool with tool_ref='server/toolname' and params={...}\n"
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
