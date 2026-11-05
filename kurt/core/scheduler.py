"""
KURT Scheduler v2.3
Schedule recurring tasks — runs via system cron or manual trigger.
Hybrid: KURT manages schedule, Claude executes the AI task.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
SCHEDULE_FILE = KURT_DIR / "schedule.json"


def _load_schedule() -> list:
    if SCHEDULE_FILE.exists():
        try:
            return json.loads(SCHEDULE_FILE.read_text())
        except Exception:
            pass
    return []


def _save_schedule(tasks: list):
    KURT_DIR.mkdir(exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False))


def _next_id(tasks: list) -> str:
    if not tasks:
        return "task-001"
    nums = [int(t["id"].split("-")[1]) for t in tasks if "-" in t.get("id", "")]
    return f"task-{max(nums or [0]) + 1:03d}"


CRON_PRESETS = {
    "every minute": "* * * * *",
    "every 5 minutes": "*/5 * * * *",
    "every hour": "0 * * * *",
    "every day 9am": "0 9 * * *",
    "every day midnight": "0 0 * * *",
    "every monday 9am": "0 9 * * 1",
    "weekdays 9am": "0 9 * * 1-5",
}


def list_schedules():
    """Show all scheduled tasks"""
    from kurt.core.persona import get_theme
    theme = get_theme()
    tasks = _load_schedule()

    if not tasks:
        console.print("[dim]Walang scheduled tasks pa. Run: kurt schedule add[/dim]")
        return

    table = Table(box=box.ROUNDED, border_style=theme["border"])
    table.add_column("ID", style=theme["accent"], width=12)
    table.add_column("Name", style=theme["primary"])
    table.add_column("Cron", style=theme["secondary"], width=16)
    table.add_column("Prompt", style="dim")
    table.add_column("Active", width=8)
    table.add_column("Last Run", style="dim", width=18)

    for t in tasks:
        active = "✅" if t.get("active", True) else "⏸"
        last_run = t.get("last_run", "Never")[:16] if t.get("last_run") else "Never"
        table.add_row(
            t["id"],
            t["name"],
            t.get("cron", "manual"),
            t["prompt"][:40] + ("..." if len(t["prompt"]) > 40 else ""),
            active,
            last_run,
        )

    console.print(Panel(table, title="⏰ KURT Scheduled Tasks", border_style=theme["border"]))


def add_schedule():
    """Add a scheduled task interactively"""
    from kurt.core.persona import get_theme
    theme = get_theme()
    console.print(f"\n[{theme['primary']}]⏰ Add Scheduled Task[/{theme['primary']}]\n")

    name = Prompt.ask("Task name (e.g., Daily Research Summary)")
    if not name.strip():
        console.print("[dim]Cancelled.[/dim]")
        return

    prompt = Prompt.ask("What should KURT ask/do? (e.g., 'Summarize today's AI news')")
    if not prompt.strip():
        console.print("[dim]Cancelled.[/dim]")
        return

    console.print("\n[dim]Cron presets:[/dim]")
    for i, (label, cron) in enumerate(CRON_PRESETS.items(), 1):
        console.print(f"  [{theme['accent']}]{i}[/{theme['accent']}] {label} [dim]({cron})[/dim]")
    console.print(f"  [{theme['accent']}]c[/{theme['accent']}] Custom cron expression")

    choice = Prompt.ask("Choose schedule", default="4")
    cron = ""

    if choice == "c":
        cron = Prompt.ask("Cron expression (e.g., 0 9 * * 1)")
    else:
        try:
            idx = int(choice) - 1
            keys = list(CRON_PRESETS.keys())
            if 0 <= idx < len(keys):
                cron = CRON_PRESETS[keys[idx]]
            else:
                cron = "0 9 * * *"
        except ValueError:
            cron = "0 9 * * *"

    tasks = _load_schedule()
    task = {
        "id": _next_id(tasks),
        "name": name,
        "prompt": prompt,
        "cron": cron,
        "active": True,
        "created": datetime.now().isoformat(),
        "last_run": None,
        "run_count": 0,
    }
    tasks.append(task)
    _save_schedule(tasks)

    # Offer to install in system cron
    console.print(f"\n[bold {theme['success']}]✅ Task '{name}' scheduled![/bold {theme['success']}]")
    console.print(f"[dim]Cron: {cron}[/dim]")
    console.print(f"[dim]ID: {task['id']}[/dim]")

    if Confirm.ask("\nInstall in system cron? (requires crontab access)", default=True):
        install_cron(task)

    return task


def install_cron(task: dict):
    """Install task into system crontab"""
    kurt_bin = sys.executable.replace("python", "kurt")
    # Use kurt CLI if available, else python -m kurt
    kurt_cmd = f"kurt ask '{task['prompt']}' >> ~/.kurt/logs/{task['id']}.log 2>&1"
    cron_line = f"{task['cron']} {kurt_cmd}"

    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""

        if cron_line not in existing:
            new_crontab = existing.rstrip() + f"\n# KURT: {task['name']}\n{cron_line}\n"
            proc = subprocess.run(
                ["crontab", "-"],
                input=new_crontab,
                capture_output=True, text=True
            )
            if proc.returncode == 0:
                console.print(f"[green]✅ Installed in crontab![/green]")
                console.print(f"[dim]{cron_line}[/dim]")
            else:
                console.print(f"[yellow]⚠️ Could not install cron: {proc.stderr}[/yellow]")
                console.print(f"[dim]Manual: add this to crontab -e[/dim]")
                console.print(f"[dim]{cron_line}[/dim]")
        else:
            console.print("[dim]Already in crontab.[/dim]")
    except FileNotFoundError:
        console.print("[yellow]⚠️ crontab not available. Add manually:[/yellow]")
        console.print(f"[dim]{cron_line}[/dim]")


def remove_schedule(task_id: str):
    """Remove a scheduled task"""
    tasks = _load_schedule()
    before = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    if len(tasks) < before:
        _save_schedule(tasks)
        console.print(f"[green]✅ Task '{task_id}' removed.[/green]")
    else:
        console.print(f"[red]Task '{task_id}' not found.[/red]")


def run_schedule(task_id: str):
    """Manually trigger a scheduled task"""
    tasks = _load_schedule()
    for t in tasks:
        if t["id"] == task_id:
            console.print(f"[dim]Running: {t['prompt']}[/dim]")
            # Update last_run
            t["last_run"] = datetime.now().isoformat()
            t["run_count"] = t.get("run_count", 0) + 1
            _save_schedule(tasks)
            return t["prompt"]
    console.print(f"[red]Task '{task_id}' not found.[/red]")
    return None


def toggle_schedule(task_id: str):
    """Pause/resume a scheduled task"""
    tasks = _load_schedule()
    for t in tasks:
        if t["id"] == task_id:
            t["active"] = not t.get("active", True)
            _save_schedule(tasks)
            status = "▶ Resumed" if t["active"] else "⏸ Paused"
            console.print(f"[green]✅ Task '{task_id}' {status}.[/green]")
            return
    console.print(f"[red]Task '{task_id}' not found.[/red]")
