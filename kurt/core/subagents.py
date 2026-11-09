"""
KURT Subagents, Background Task Manager & Planning Artifacts
Gives KURT Antigravity / Gemini CLI-level capabilities:
  1. Background task management (start, list, status, kill long-running servers/builds)
  2. Autonomous Subagents & Multi-Agent Parallel Swarms
  3. Structured Markdown Planning Artifacts (with Mermaid diagrams & GFM alerts)
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from kurt.core.file_ops import _is_dangerous
from kurt.utils.security import child_env, redact, sensitive_path
from kurt.utils.execution import restricted_argv
from kurt.utils.workspace import workspace_path, current_workspace, active_workspace

KURT_ARTIFACTS_DIR = Path.home() / ".kurt" / "artifacts"


# ─────────────────────────────────────────────────────────────
# 1. Background Task Manager (like Antigravity's manage_task)
# ─────────────────────────────────────────────────────────────

@dataclass
class BackgroundTask:
    task_id: str
    cmd: str
    cwd: str
    started_at: float
    process: subprocess.Popen
    log_path: Path


_TASKS: dict[str, BackgroundTask] = {}


def manage_background_task(
    action: str = "list",
    cmd: Optional[str] = None,
    task_id: Optional[str] = None,
    cwd: str = ".",
) -> dict:
    """
    Manage background shell tasks (dev servers, watchers, long test runs).
    Actions:
      - 'start': Launch `cmd` in background and return its `task_id`
      - 'list': List all tracked background tasks and their live state
      - 'status': Check status and recent log output for `task_id`
      - 'kill': Terminate `task_id` and its process group
    """
    act = (action or "list").strip().lower()

    if act == "start":
        if not cmd or not str(cmd).strip():
            return {"status": "error", "error": "start requires 'cmd'"}
        danger = _is_dangerous(cmd)
        if danger:
            return {"status": "error", "error": f"Refused dangerous pattern: {danger}"}

        if sum(t.process.poll() is None for t in _TASKS.values()) >= 4:
            return {"status":"error","error":"Background process limit reached (4)"}
        tid = f"task-{uuid.uuid4().hex[:8]}"
        work_dir = str(workspace_path(cwd) if active_workspace() else Path(cwd).expanduser().resolve())
        log_dir = Path(tempfile.gettempdir()) / "kurt_tasks"
        log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        log_file = log_dir / f"{tid}.log"

        try:
            import platform as _platform
            with open(log_file, "w+", encoding="utf-8") as log_fp:
                if _platform.system() == "Darwin":
                    argv = restricted_argv(["/bin/sh", "-c", 'ulimit -f 2048; exec /bin/sh -c "$1"', "kurt-background", cmd], cwd=work_dir)
                    proc = subprocess.Popen(
                        argv,
                        stdout=log_fp,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        cwd=work_dir,
                        env=child_env(),
                        start_new_session=True,
                    )
                else:
                    proc = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=log_fp,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        cwd=work_dir,
                        env=child_env(),
                        start_new_session=(_platform.system() != "Windows"),
                    )
        except Exception as exc:
            return {"status": "error", "error": redact(str(exc))}

        _TASKS[tid] = BackgroundTask(
            task_id=tid,
            cmd=redact(cmd),
            cwd=work_dir,
            started_at=time.time(),
            process=proc,
            log_path=log_file,
        )
        return {
            "status": "started",
            "task_id": tid,
            "pid": proc.pid,
            "cmd": redact(cmd),
            "cwd": work_dir,
        }

    if act == "list":
        items = []
        for tid, t in list(_TASKS.items()):
            rc = t.process.poll()
            state = "running" if rc is None else f"exited({rc})"
            items.append({
                "task_id": tid,
                "pid": t.process.pid,
                "state": state,
                "cmd": t.cmd,
                "uptime_sec": round(time.time() - t.started_at, 1),
            })
        return {"status": "ok", "count": len(items), "tasks": items}

    if act == "status":
        if not task_id or task_id not in _TASKS:
            return {"status": "error", "error": f"Unknown task_id: {task_id}"}
        t = _TASKS[task_id]
        rc = t.process.poll()
        state = "running" if rc is None else "completed" if rc == 0 else "failed"
        output = ""
        try:
            if t.log_path.exists():
                raw = t.log_path.read_text(encoding="utf-8", errors="replace")
                output = redact(raw[-4000:])
        except Exception:
            pass
        return {
            "status": "ok",
            "task_id": task_id,
            "pid": t.process.pid,
            "state": state,
            "exit_code": rc,
            "cmd": t.cmd,
            "output": output,
        }

    if act == "kill":
        if not task_id or task_id not in _TASKS:
            return {"status": "error", "error": f"Unknown task_id: {task_id}"}
        t = _TASKS[task_id]
        if t.process.poll() is None:
            import platform as _platform
            if _platform.system() == "Windows":
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(t.process.pid)], capture_output=True, timeout=5)
                except Exception:
                    t.process.kill()
            else:
                try:
                    os.killpg(t.process.pid, signal.SIGTERM)
                    t.process.wait(timeout=2)
                except Exception:
                    try:
                        os.killpg(t.process.pid, signal.SIGKILL)
                    except Exception:
                        t.process.kill()
        return {"status": "killed", "task_id": task_id, "pid": t.process.pid}

    return {"status": "error", "error": f"Unknown action '{action}'. Use start, list, status, or kill."}


# ─────────────────────────────────────────────────────────────
# 2. Autonomous Subagents & Multi-Agent Swarm
# ─────────────────────────────────────────────────────────────

SUBAGENT_ROLES = {
    "research": (
        "You are KURT's Research Subagent. Focus on exploring files, searching code with grep_search "
        "and find_files, or searching the web. Do NOT modify files unless explicitly asked. "
        "Finish by calling 'done' with a concise, well-structured findings report."
    ),
    "coder": (
        "You are KURT's Coding Subagent. Read target files carefully, implement clean edits with edit_file "
        "or multi_edit, verify changes by running tests or files, and call 'done' with a summary of changes."
    ),
    "mac-doctor": (
        "You are KURT's Host System Diagnostics Subagent. Use mac_doctor to inspect system health, CPU/RAM hogs, "
        "disk usage, network ports, or crash logs across macOS/Windows/Linux, and call 'done' with actionable recommendations."
    ),
    "system-doctor": (
        "You are KURT's Host System Diagnostics Subagent. Use mac_doctor to inspect system health, CPU/RAM hogs, "
        "disk usage, network ports, or crash logs across macOS/Windows/Linux, and call 'done' with actionable recommendations."
    ),
    "qa-verifier": (
        "You are KURT's QA Verification Subagent. Run tests, inspect outputs or screenshots, verify edge cases, "
        "and call 'done' reporting pass/fail status and any defects found."
    ),
}


async def run_subagent_async(
    role: str,
    task: str,
    cwd: str = ".",
    model: Optional[str] = None,
    provider: Optional[str] = None,
    max_steps: int = 8,
) -> dict:
    """
    Launch an isolated subagent loop with its own role and context window.
    Returns a summary dict with steps taken, files changed, and final output.
    """
    from kurt.core.agent_loop import run_agent
    from kurt.core.orchestrator import analyze_task
    from kurt.core.router import ModelRouter

    role_key = (role or "research").strip().lower()
    role_instructions = SUBAGENT_ROLES.get(
        role_key,
        f"You are KURT's specialized '{role}' Subagent. Complete the assigned sub-task thoroughly and call 'done'.",
    )

    analysis = analyze_task(task)
    if model:
        analysis.model = model
    if provider:
        analysis.provider = provider

    router = ModelRouter()
    enriched_task = f"[SUBAGENT ROLE: {role}]\n{role_instructions}\n\nAssigned Sub-Task: {task}"
    max_steps = max(1, min(int(max_steps), 15))

    result = await run_agent(
        task=enriched_task,
        analysis=analysis,
        router=router,
        cwd=cwd,
        max_steps=max_steps,
        verbose=False,
    )
    return {
        "status": "completed" if result.success else "incomplete",
        "role": role,
        "model": analysis.model,
        "steps_taken": len(result.steps),
        "files_changed": result.files_changed,
        "summary": redact(result.final_summary),
    }


async def run_swarm_async(subtasks: list[dict], cwd: str = ".") -> dict:
    """
    Execute multiple subagents in parallel and aggregate their results.
    Each item in `subtasks` is {"role": "...", "task": "...", "model": optional}.
    """
    if not isinstance(subtasks, list) or not subtasks:
        return {"status": "error", "error": "subtasks must be a non-empty list"}

    capped = subtasks[:5]  # Cap parallel subagents at 5 for safety
    coros = [
        run_subagent_async(
            role=item.get("role", "research"),
            task=item.get("task", ""),
            cwd=cwd,
            model=item.get("model"),
            provider=item.get("provider"),
            max_steps=int(item.get("max_steps", 6)),
        )
        for item in capped
        if isinstance(item, dict) and item.get("task")
    ]
    if not coros:
        return {"status": "error", "error": "No valid tasks in subtasks list"}

    results = await asyncio.gather(*coros, return_exceptions=True)
    formatted = []
    for idx, res in enumerate(results, 1):
        if isinstance(res, Exception):
            formatted.append({"agent_index": idx, "status": "error", "error": redact(str(res))})
        else:
            formatted.append({"agent_index": idx, **res})

    return {
        "status": "ok",
        "subagents_run": len(formatted),
        "results": formatted,
    }


# ─────────────────────────────────────────────────────────────
# 3. Structured Planning Artifacts (like Antigravity /plan)
# ─────────────────────────────────────────────────────────────

def create_plan_artifact(
    title: str,
    summary: str,
    steps: list[str],
    mermaid_diagram: Optional[str] = None,
    verification: Optional[list[str]] = None,
    output_path: Optional[str] = None,
) -> dict:
    """
    Create a structured GitHub-Flavored Markdown implementation plan artifact
    with alerts, Mermaid diagrams, and a verification checklist.
    """
    if not title or not str(title).strip():
        return {"status": "error", "error": "Plan title is required"}

    slug = "".join(ch if ch.isalnum() else "_" for ch in title.lower()).strip("_")[:40] or "plan"
    if output_path:
        target = Path(output_path).expanduser().resolve()
        if sensitive_path(target):
            return {"status": "error", "error": "Cannot write plan artifact to a sensitive path"}
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        KURT_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        target = KURT_ARTIFACTS_DIR / f"plan_{slug}_{int(time.time())}.md"

    lines = [
        f"# 📋 {redact(title.strip())}",
        "",
        f"> [!IMPORTANT]",
        f"> **Goal Summary:** {redact(summary.strip()) if summary else 'Implementation & Execution Plan'}",
        "",
    ]

    if mermaid_diagram and mermaid_diagram.strip():
        diag = mermaid_diagram.strip()
        if not diag.startswith("```mermaid"):
            diag = f"```mermaid\n{diag}\n```"
        lines.extend([
            "## 🗺️ Architecture & Workflow Diagram",
            "",
            redact(diag),
            "",
        ])

    lines.extend([
        "## 🛠️ Step-by-Step Implementation Plan",
        "",
    ])
    for idx, step in enumerate(steps or [], 1):
        lines.append(f"- [ ] **Step {idx}:** {redact(str(step))}")

    if verification:
        lines.extend([
            "",
            "## ✅ Verification & Testing Checklist",
            "",
        ])
        for v in verification:
            lines.append(f"- [ ] {redact(str(v))}")

    content = "\n".join(lines) + "\n"
    target.write_text(content, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(target),
        "title": redact(title.strip()),
        "steps_count": len(steps or []),
        "preview": content[:1000],
    }
