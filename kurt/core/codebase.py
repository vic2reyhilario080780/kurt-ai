"""
KURT Codebase Intelligence — Phase 3
Index a codebase, understand structure, provide context to AI.
Also: AI-powered git diff review.
"""

import os
import re
import json
import subprocess
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import box

console = Console()

KURT_DIR = Path.home() / ".kurt"
INDEX_DIR = KURT_DIR / "codebase_index"


# ─────────────────────────────────────────────────────────────
# File type config
# ─────────────────────────────────────────────────────────────

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".rb", ".swift",
    ".kt", ".scala", ".dart", ".vue", ".svelte", ".html", ".css",
    ".scss", ".less", ".sql", ".sh", ".bash", ".yaml", ".yml",
    ".json", ".toml", ".md", ".txt", ".env.example",
}

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", "eggs", ".eggs", "target", "out",
}

IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", "package-lock.json", "yarn.lock",
    "poetry.lock", "Pipfile.lock", ".env",
}

MAX_FILE_SIZE_KB = 500  # Skip files > 500KB


# ─────────────────────────────────────────────────────────────
# Codebase Indexer
# ─────────────────────────────────────────────────────────────

def _hash_project(path: str) -> str:
    return hashlib.md5(str(Path(path).resolve()).encode()).hexdigest()[:8]


def index_codebase(path: str = ".", force: bool = False) -> dict:
    """
    Scan a directory and build a codebase index.
    Returns index dict: {files, stats, structure, summary}
    """
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {"error": f"Not a directory: {path}"}

    proj_hash = _hash_project(str(root))
    index_file = INDEX_DIR / f"{proj_hash}.json"
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache (skip if indexed < 5 min ago and not forced)
    if not force and index_file.exists():
        try:
            cached = json.loads(index_file.read_text())
            age_seconds = (datetime.now().timestamp() - cached.get("indexed_at", 0))
            if age_seconds < 300:
                console.print(f"[dim]📦 Using cached index (age: {int(age_seconds)}s)[/dim]")
                return cached
        except Exception:
            pass

    console.print(f"[cyan]🔍 Indexing {root}…[/cyan]")

    files = []
    stats = {
        "total_files": 0,
        "total_lines": 0,
        "total_size_kb": 0,
        "by_ext": {},
        "skipped": 0,
    }

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]

        for filename in sorted(filenames):
            if filename in IGNORE_FILES:
                continue
            fp = Path(dirpath) / filename
            ext = fp.suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue

            try:
                size_kb = fp.stat().st_size / 1024
                if size_kb > MAX_FILE_SIZE_KB:
                    stats["skipped"] += 1
                    continue

                content = fp.read_text(encoding="utf-8", errors="replace")
                lines = content.count("\n") + 1
                rel_path = str(fp.relative_to(root))

                # Extract key info per file type
                symbols = _extract_symbols(content, ext)

                file_info = {
                    "path": rel_path,
                    "ext": ext,
                    "lines": lines,
                    "size_kb": round(size_kb, 1),
                    "symbols": symbols,
                }
                files.append(file_info)

                stats["total_files"] += 1
                stats["total_lines"] += lines
                stats["total_size_kb"] += size_kb
                stats["by_ext"][ext] = stats["by_ext"].get(ext, 0) + 1

            except Exception:
                stats["skipped"] += 1

    stats["total_size_kb"] = round(stats["total_size_kb"], 1)

    # Build structure tree (top-level dirs only)
    structure = _build_structure_summary(root, files)

    # Detect project type
    project_type = _detect_project_type(root, files)

    index = {
        "root": str(root),
        "project_hash": proj_hash,
        "project_type": project_type,
        "indexed_at": datetime.now().timestamp(),
        "stats": stats,
        "structure": structure,
        "files": files,
    }

    index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    console.print(f"[green]✅ Indexed {stats['total_files']} files · {stats['total_lines']:,} lines[/green]")
    return index


def _extract_symbols(content: str, ext: str) -> list[str]:
    """Extract class/function/component names from source"""
    symbols = []
    if ext == ".py":
        for m in re.finditer(r"^(class|def|async def)\s+(\w+)", content, re.MULTILINE):
            symbols.append(f"{m.group(1)} {m.group(2)}")
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        for m in re.finditer(
            r"(?:function\s+(\w+)|const\s+(\w+)\s*=|class\s+(\w+)|export\s+(?:default\s+)?(?:function|class)\s+(\w+))",
            content
        ):
            name = next((g for g in m.groups() if g), None)
            if name:
                symbols.append(name)
    elif ext in (".java", ".cs", ".kt"):
        for m in re.finditer(r"(?:class|interface|enum|fun|void|public|private)\s+(\w+)\s*[\({]", content):
            symbols.append(m.group(1))
    return symbols[:20]  # Cap at 20


def _build_structure_summary(root: Path, files: list) -> list[str]:
    """Build top-level directory listing"""
    dirs = set()
    for f in files:
        parts = Path(f["path"]).parts
        if len(parts) > 1:
            dirs.add(parts[0])
    return sorted(dirs)


def _detect_project_type(root: Path, files: list) -> str:
    """Guess project type from files"""
    file_names = {f["path"].split("/")[-1] for f in files}
    root_files = {f.name for f in root.iterdir() if f.is_file()}

    if "package.json" in root_files:
        if any("next.config" in f for f in root_files):
            return "Next.js"
        if any("vite.config" in f for f in root_files):
            return "Vite/React"
        return "Node.js"
    if "requirements.txt" in root_files or "pyproject.toml" in root_files:
        if any(f.endswith("manage.py") for f in file_names):
            return "Django"
        if "app.py" in root_files or "main.py" in root_files:
            return "Python App"
        return "Python"
    if "Cargo.toml" in root_files:
        return "Rust"
    if "go.mod" in root_files:
        return "Go"
    if "pom.xml" in root_files:
        return "Java/Maven"
    return "Unknown"


def show_index_summary(index: dict):
    """Display codebase index in Rich table"""
    stats = index.get("stats", {})
    t = Table(title=f"📦 {index.get('project_type', '?')} · {index.get('root', '.')}", box=box.ROUNDED)
    t.add_column("Metric", style="cyan")
    t.add_column("Value", style="white")
    t.add_row("Files indexed", str(stats.get("total_files", 0)))
    t.add_row("Total lines", f"{stats.get('total_lines', 0):,}")
    t.add_row("Total size", f"{stats.get('total_size_kb', 0):.1f} KB")
    t.add_row("Skipped", str(stats.get("skipped", 0)))
    t.add_row("Top dirs", ", ".join(index.get("structure", [])[:8]))

    ext_counts = stats.get("by_ext", {})
    top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:5]
    t.add_row("Top extensions", "  ".join(f"{e}:{n}" for e, n in top_exts))
    console.print(t)


def get_codebase_context(index: dict, query: str = "", max_files: int = 10) -> str:
    """
    Build a context string from the index to inject into AI prompts.
    Optionally filter files relevant to query.
    """
    lines = [
        f"PROJECT: {index.get('project_type', 'Unknown')} at {index.get('root', '.')}",
        f"FILES: {index['stats']['total_files']} files, {index['stats']['total_lines']:,} lines",
        f"STRUCTURE: {', '.join(index.get('structure', []))}",
        "",
        "KEY FILES:",
    ]

    files = index.get("files", [])

    # If query given, sort by relevance (simple keyword match)
    if query:
        q = query.lower()
        def relevance(f):
            score = 0
            if q in f["path"].lower():
                score += 3
            for sym in f.get("symbols", []):
                if q in sym.lower():
                    score += 1
            return -score
        files = sorted(files, key=relevance)

    for f in files[:max_files]:
        syms = ", ".join(f.get("symbols", [])[:5])
        sym_str = f"  [{syms}]" if syms else ""
        lines.append(f"  {f['path']} ({f['lines']} lines){sym_str}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Git Diff Review
# ─────────────────────────────────────────────────────────────

def get_git_diff(path: str = ".", staged_only: bool = False, commits: Optional[str] = None) -> str:
    """Get git diff output"""
    if commits:
        cmd = ["git", "-C", path, "diff", commits]
    elif staged_only:
        cmd = ["git", "-C", path, "diff", "--cached"]
    else:
        cmd = ["git", "-C", path, "diff", "HEAD"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            # Try without HEAD (new repo)
            result = subprocess.run(
                ["git", "-C", path, "diff"],
                capture_output=True, text=True, timeout=15
            )
        return result.stdout
    except Exception as e:
        return f"❌ git diff failed: {e}"


def get_git_log(path: str = ".", n: int = 5) -> str:
    """Get recent git log"""
    try:
        result = subprocess.run(
            ["git", "-C", path, "log", f"-{n}", "--oneline", "--decorate"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def parse_diff_stats(diff: str) -> dict:
    """Parse diff for quick stats"""
    additions = len(re.findall(r"^\+[^+]", diff, re.MULTILINE))
    deletions = len(re.findall(r"^-[^-]", diff, re.MULTILINE))
    files = re.findall(r"^diff --git a/(.*?) b/", diff, re.MULTILINE)
    return {
        "files_changed": len(set(files)),
        "additions": additions,
        "deletions": deletions,
        "files": list(set(files)),
    }


def build_diff_review_prompt(diff: str, focus: str = "") -> str:
    """Build AI prompt for reviewing a diff"""
    stats = parse_diff_stats(diff)
    focus_line = f"\nFocus on: {focus}" if focus else ""

    # Truncate huge diffs
    diff_content = diff[:8000] + "\n[... truncated ...]" if len(diff) > 8000 else diff

    return f"""Review this git diff as a senior developer. Be concise.{focus_line}

Stats: {stats['files_changed']} files changed, +{stats['additions']} -{stats['deletions']} lines
Files: {', '.join(stats['files'][:10])}

```diff
{diff_content}
```

Provide:
1. **Summary** — what changed and why (1-2 sentences)
2. **Issues** — bugs, security risks, breaking changes (if any)
3. **Improvements** — optional suggestions
4. **Verdict** — ✅ LGTM / ⚠️ Needs review / ❌ Do not merge"""
