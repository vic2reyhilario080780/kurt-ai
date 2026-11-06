"""
KURT File Operations — Phase 2
AI-powered file reading, editing, and code execution.
Comparable to Claude Code CLI file tools.
"""

import os
import re
import sys
import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich import box

console = Console()


# ─────────────────────────────────────────────────────────────
# File Reading
# ─────────────────────────────────────────────────────────────

def read_file(path: str, lines: Optional[str] = None) -> str:
    """
    Read a file and return its contents.
    lines: optional range like '10-25' or '10' (single line)
    Returns the content as string.
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"❌ File not found: {path}"
    if not p.is_file():
        return f"❌ Not a file: {path}"

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Cannot read file: {e}"

    all_lines = content.splitlines()
    total = len(all_lines)

    if lines:
        try:
            if "-" in lines:
                start, end = lines.split("-", 1)
                start = max(1, int(start))
                end = min(total, int(end))
                selected = all_lines[start - 1:end]
                numbered = "\n".join(f"{start + i:4d}  {l}" for i, l in enumerate(selected))
                return f"[Lines {start}–{end} of {total}]\n{numbered}"
            else:
                n = int(lines)
                if 1 <= n <= total:
                    return f"[Line {n}]\n{all_lines[n-1]}"
        except ValueError:
            pass

    # Return full file with line numbers
    numbered = "\n".join(f"{i+1:4d}  {l}" for i, l in enumerate(all_lines))
    return f"[{total} lines — {p}]\n{numbered}"


def read_file_summary(path: str) -> dict:
    """Return file metadata for display"""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    stat = p.stat()
    content = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    lines = content.count("\n") + 1 if content else 0
    ext = p.suffix.lstrip(".") or "txt"
    return {
        "name": p.name,
        "path": str(p),
        "size_kb": round(stat.st_size / 1024, 1),
        "lines": lines,
        "ext": ext,
        "content": content,
    }


# ─────────────────────────────────────────────────────────────
# File Editing (AI-guided)
# ─────────────────────────────────────────────────────────────

def apply_edit(path: str, old_str: str, new_str: str, dry_run: bool = False) -> str:
    """
    Replace old_str with new_str in file.
    Returns success/fail message.
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"❌ File not found: {path}"

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Cannot read: {e}"

    if old_str not in content:
        # Try to give a helpful diff hint
        old_lines = old_str.splitlines()
        first_line = old_lines[0].strip() if old_lines else ""
        if first_line and first_line in content:
            return f"❌ Exact string not found (but first line exists). Check whitespace/indentation."
        return f"❌ String not found in file."

    count = content.count(old_str)
    if count > 1:
        return f"❌ Found {count} occurrences — provide more context to make it unique."

    new_content = content.replace(old_str, new_str, 1)

    if dry_run:
        return f"✅ Dry-run OK — would replace {len(old_str)} chars with {len(new_str)} chars."

    # Backup
    backup_path = str(p) + ".kurt_bak"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        p.write_text(new_content, encoding="utf-8")
        lines_changed = abs(new_content.count("\n") - content.count("\n"))
        return f"✅ Edit applied to {p.name}  (+{new_str.count(chr(10))+1} / -{old_str.count(chr(10))+1} lines)  Backup: {backup_path}"
    except Exception as e:
        return f"❌ Write failed: {e}"


def insert_at_line(path: str, line_num: int, text: str) -> str:
    """Insert text before a specific line number"""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"❌ File not found: {path}"
    try:
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        insert_idx = max(0, min(line_num - 1, len(lines)))
        new_text = text if text.endswith("\n") else text + "\n"
        lines.insert(insert_idx, new_text)
        p.write_text("".join(lines), encoding="utf-8")
        return f"✅ Inserted at line {line_num} in {p.name}"
    except Exception as e:
        return f"❌ Insert failed: {e}"


def write_new_file(path: str, content: str) -> str:
    """Create a new file with given content"""
    p = Path(path).expanduser().resolve()
    if p.exists():
        return f"❌ File already exists: {path}. Use apply_edit to modify it."
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return f"✅ Created {p.name}  ({lines} lines)"
    except Exception as e:
        return f"❌ Create failed: {e}"


# ─────────────────────────────────────────────────────────────
# Code Execution
# ─────────────────────────────────────────────────────────────

SAFE_EXTENSIONS = {".py", ".js", ".ts", ".sh", ".bash"}
DANGEROUS_PATTERNS = [
    r"rm\s+-rf", r"sudo\s+", r"mkfs", r"dd\s+if=",
    r"chmod\s+777", r":(){ :|:& };:", r"> /dev/sda",
]


def _is_dangerous(code: str) -> Optional[str]:
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, code, re.IGNORECASE):
            return pat
    return None


def run_file(path: str, args: str = "", timeout: int = 30) -> dict:
    """
    Execute a file and return stdout/stderr/returncode.
    Returns dict: {stdout, stderr, returncode, runtime_ms}
    """
    import time
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}

    ext = p.suffix.lower()
    content = p.read_text(encoding="utf-8", errors="replace")

    danger = _is_dangerous(content)
    if danger:
        return {"error": f"🚨 Dangerous pattern detected: {danger}. Refusing to run."}

    # Pick interpreter
    if ext == ".py":
        cmd = [sys.executable, str(p)] + (args.split() if args else [])
    elif ext in (".sh", ".bash"):
        cmd = ["bash", str(p)] + (args.split() if args else [])
    elif ext == ".js":
        cmd = ["node", str(p)] + (args.split() if args else [])
    else:
        return {"error": f"Unsupported file type: {ext}. Supported: .py .sh .js"}

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(p.parent),
        )
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "runtime_ms": elapsed_ms,
            "cmd": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timed out after {timeout}s"}
    except FileNotFoundError as e:
        return {"error": f"Interpreter not found: {e}"}
    except Exception as e:
        return {"error": str(e)}


def run_code_string(code: str, lang: str = "python", timeout: int = 30) -> dict:
    """
    Run a code string in a temp file. Returns same dict as run_file.
    """
    import time
    ext_map = {"python": ".py", "py": ".py", "javascript": ".js", "js": ".js", "bash": ".sh", "sh": ".sh"}
    ext = ext_map.get(lang.lower(), ".py")

    danger = _is_dangerous(code)
    if danger:
        return {"error": f"🚨 Dangerous pattern detected: {danger}"}

    with tempfile.NamedTemporaryFile(suffix=ext, mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = run_file(tmp_path, timeout=timeout)
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# Directory listing (like `ls` with context)
# ─────────────────────────────────────────────────────────────

def list_dir(path: str = ".", depth: int = 2) -> str:
    """List directory tree up to depth"""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"❌ Path not found: {path}"
    if not p.is_dir():
        return f"❌ Not a directory: {path}"

    lines = [f"📁 {p}/"]
    _walk_tree(p, lines, prefix="", depth=depth, current=0)
    return "\n".join(lines)


def _walk_tree(p: Path, lines: list, prefix: str, depth: int, current: int):
    if current >= depth:
        return
    try:
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        lines.append(f"{prefix}  [permission denied]")
        return

    # Skip hidden and common noise
    entries = [e for e in entries if not e.name.startswith(".") and e.name not in
               {"__pycache__", "node_modules", ".git", "venv", ".venv", "dist", "build"}]

    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        icon = "📁" if entry.is_dir() else "📄"
        size = ""
        if entry.is_file():
            try:
                kb = entry.stat().st_size / 1024
                size = f"  [{kb:.1f}KB]" if kb > 1 else ""
            except Exception:
                pass
        lines.append(f"{prefix}{connector}{icon} {entry.name}{size}")
        if entry.is_dir() and current + 1 < depth:
            extension = "    " if is_last else "│   "
            _walk_tree(entry, lines, prefix + extension, depth, current + 1)
