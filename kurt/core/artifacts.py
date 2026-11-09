"""
KURT Artifacts System v2.3
Auto-save and manage AI-generated code, designs, and outputs.
"""

from kurt.utils.security import redact, write_private_text

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
ARTIFACTS_DIR = KURT_DIR / "artifacts"
ARTIFACTS_INDEX = KURT_DIR / "artifacts_index.json"


def _load_index() -> list:
    if ARTIFACTS_INDEX.exists():
        try:
            return json.loads(ARTIFACTS_INDEX.read_text())
        except Exception:
            pass
    return []


def _save_index(index: list):
    KURT_DIR.mkdir(exist_ok=True)
    write_private_text(ARTIFACTS_INDEX, json.dumps(redact(index), indent=2, ensure_ascii=False))


def extract_code_blocks(text: str) -> list[dict]:
    """Extract code blocks from AI response"""
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    blocks = []
    for lang, code in matches:
        if code.strip():
            blocks.append({
                "language": lang.lower() if lang else "text",
                "code": code.strip(),
            })
    return blocks


def save_artifact(prompt: str, response: str, task_type: str = "code") -> list[str]:
    """Auto-save code blocks from AI response. Returns list of saved file paths."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    prompt, response = redact(prompt), redact(response)
    blocks = extract_code_blocks(response)
    if not blocks:
        return []

    saved_paths = []
    index = _load_index()
    ts = datetime.now()
    ts_str = ts.strftime("%Y%m%d_%H%M%S")

    ext_map = {
        "python": "py", "py": "py",
        "javascript": "js", "js": "js",
        "typescript": "ts", "ts": "ts",
        "html": "html", "css": "css",
        "bash": "sh", "shell": "sh", "sh": "sh",
        "sql": "sql", "json": "json",
        "yaml": "yml", "yml": "yml",
        "rust": "rs", "go": "go",
        "java": "java", "cpp": "cpp", "c": "c",
        "markdown": "md", "md": "md",
    }

    for i, block in enumerate(blocks):
        lang = block["language"]
        ext = ext_map.get(lang, "txt")
        # Slugify prompt for filename
        slug = re.sub(r"[^\w\s-]", "", prompt[:30].lower())
        slug = re.sub(r"[\s]+", "_", slug).strip("_")
        fname = f"{ts_str}_{slug}_{i+1}.{ext}"
        fpath = ARTIFACTS_DIR / fname

        write_private_text(fpath, block["code"])
        saved_paths.append(str(fpath))

        # Add to index
        index.append({
            "id": hashlib.md5(fname.encode()).hexdigest()[:8],
            "filename": fname,
            "path": str(fpath),
            "language": lang,
            "task_type": task_type,
            "prompt": prompt[:100],
            "created": ts.isoformat(),
            "size": len(block["code"]),
        })

    _save_index(index)
    return saved_paths


def list_artifacts(limit: int = 20):
    """Show saved artifacts"""
    from kurt.core.persona import get_theme
    theme = get_theme()
    index = _load_index()

    if not index:
        console.print("[dim]Walang artifacts pa. Mag-generate muna ng code.[/dim]")
        return

    # Show most recent first
    recent = list(reversed(index))[:limit]

    table = Table(box=box.ROUNDED, border_style=theme["border"])
    table.add_column("ID", style=theme["accent"], width=10)
    table.add_column("File", style=theme["primary"])
    table.add_column("Lang", style=theme["secondary"], width=12)
    table.add_column("Task", style=theme["secondary"], width=10)
    table.add_column("Prompt", style="dim")
    table.add_column("Created", style="dim", width=16)

    for a in recent:
        created = a["created"][:16].replace("T", " ")
        table.add_row(
            a["id"],
            a["filename"],
            a.get("language", "?"),
            a.get("task_type", "?"),
            a["prompt"][:35] + ("..." if len(a["prompt"]) > 35 else ""),
            created,
        )

    console.print(Panel(
        table,
        title=f"[{theme['primary']}]📦 KURT Artifacts ({len(index)} total)[/{theme['primary']}]",
        border_style=theme["border"]
    ))


def show_artifact(artifact_id: str):
    """Show contents of an artifact by ID or filename"""
    index = _load_index()
    match = None
    for a in index:
        if a["id"] == artifact_id or a["filename"].startswith(artifact_id):
            match = a
            break

    if not match:
        console.print(f"[red]Artifact '{artifact_id}' not found.[/red]")
        return

    path = Path(match["path"])
    if not path.exists():
        console.print(f"[red]File missing: {match['path']}[/red]")
        return

    code = path.read_text()
    lang = match.get("language", "text")

    console.print(f"\n[dim]📦 {match['filename']} · {match['created'][:16]}[/dim]")
    console.print(f"[dim]Prompt: {match['prompt']}[/dim]\n")

    syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
    console.print(syntax)


def open_artifact(artifact_id: str):
    """Get file path of artifact to open in editor"""
    index = _load_index()
    for a in index:
        if a["id"] == artifact_id or a["filename"].startswith(artifact_id):
            return a["path"]
    return None


def clean_artifacts(keep: int = 50):
    """Remove old artifacts, keep most recent N"""
    index = _load_index()
    if len(index) <= keep:
        console.print(f"[dim]Only {len(index)} artifacts, nothing to clean.[/dim]")
        return

    to_remove = index[:-keep]
    for a in to_remove:
        p = Path(a["path"])
        if p.exists():
            p.unlink()

    _save_index(index[-keep:])
    console.print(f"[green]✅ Cleaned {len(to_remove)} old artifacts.[/green]")
