"""
KURT Projects System v2.3
Manage active projects with context, notes, and task tracking.
Hybrid: KURT stores context, Claude assists with project intelligence.
"""

import json
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
PROJECTS_FILE = KURT_DIR / "projects.json"


def _load_projects() -> dict:
    KURT_DIR.mkdir(exist_ok=True)
    if PROJECTS_FILE.exists():
        try:
            return json.loads(PROJECTS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_projects(projects: dict):
    KURT_DIR.mkdir(exist_ok=True)
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2, ensure_ascii=False))


def get_project_context(project_name: str) -> str:
    """Returns project context string for injection into AI prompts"""
    projects = _load_projects()
    p = projects.get(project_name.lower())
    if not p:
        return ""
    lines = [f"PROJECT: {p['name']}"]
    if p.get("description"):
        lines.append(f"Description: {p['description']}")
    if p.get("stack"):
        lines.append(f"Tech stack: {p['stack']}")
    if p.get("goals"):
        lines.append(f"Goals: {p['goals']}")
    if p.get("notes"):
        lines.append(f"Notes: {p['notes']}")
    return "\n".join(lines)


def get_active_project_contexts(active_projects: list) -> str:
    """Returns combined context for all active projects"""
    contexts = []
    for name in active_projects:
        ctx = get_project_context(name)
        if ctx:
            contexts.append(ctx)
    if not contexts:
        return ""
    return "\n\n---\n".join(contexts)


def list_projects():
    """Show all saved projects"""
    from kurt.core.persona import get_theme
    theme = get_theme()
    projects = _load_projects()

    if not projects:
        console.print("[dim]Walang projects pa. Run: kurt project add[/dim]")
        return

    table = Table(box=box.ROUNDED, border_style=theme["border"])
    table.add_column("Name", style=theme["primary"])
    table.add_column("Description", style=theme["secondary"])
    table.add_column("Stack", style=theme["accent"])
    table.add_column("Active", style=theme["success"])

    from kurt.core.persona import load_persona
    active = load_persona().get("active_projects", [])

    for key, p in projects.items():
        is_active = "✅" if p["name"] in active else "—"
        table.add_row(
            p["name"],
            p.get("description", "")[:50],
            p.get("stack", ""),
            is_active,
        )

    console.print(Panel(table, title="📁 KURT Projects", border_style=theme["border"]))


def add_project():
    """Add a new project interactively"""
    from kurt.core.persona import get_theme
    theme = get_theme()
    console.print(f"\n[{theme['primary']}]📁 Add New Project[/{theme['primary']}]\n")

    name = Prompt.ask("Project name (e.g., VCore, Sari-Sari POS)")
    if not name.strip():
        console.print("[dim]Cancelled.[/dim]")
        return

    projects = _load_projects()
    key = name.lower().replace(" ", "-")

    description = Prompt.ask("Short description", default="")
    stack = Prompt.ask("Tech stack (e.g., Python, React, Supabase)", default="")
    goals = Prompt.ask("Main goal / what are you building?", default="")

    projects[key] = {
        "name": name,
        "description": description,
        "stack": stack,
        "goals": goals,
        "notes": "",
        "created": datetime.now().isoformat(),
    }
    _save_projects(projects)

    # Offer to set as active
    if Confirm.ask(f"Set '{name}' as active project?", default=True):
        from kurt.core.persona import load_persona, save_persona
        persona = load_persona()
        active = persona.get("active_projects", [])
        if name not in active:
            active.append(name)
        persona["active_projects"] = active
        save_persona(persona)
        console.print(f"[bold {theme['success']}]✅ Project '{name}' added and activated![/bold {theme['success']}]")
    else:
        console.print(f"[bold {theme['success']}]✅ Project '{name}' saved![/bold {theme['success']}]")


def remove_project(name: str):
    """Remove a project"""
    projects = _load_projects()
    key = name.lower().replace(" ", "-")
    if key in projects:
        del projects[key]
        _save_projects(projects)
        # Remove from active too
        from kurt.core.persona import load_persona, save_persona
        persona = load_persona()
        persona["active_projects"] = [p for p in persona.get("active_projects", []) if p.lower() != name.lower()]
        save_persona(persona)
        console.print(f"[green]✅ Project '{name}' removed.[/green]")
    else:
        console.print(f"[red]Project '{name}' not found.[/red]")


def note_project(name: str, note: str):
    """Add a note to a project"""
    projects = _load_projects()
    key = name.lower().replace(" ", "-")
    if key in projects:
        existing = projects[key].get("notes", "")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        projects[key]["notes"] = f"{existing}\n[{ts}] {note}".strip()
        _save_projects(projects)
        console.print(f"[green]✅ Note added to '{name}'.[/green]")
    else:
        console.print(f"[red]Project '{name}' not found.[/red]")
