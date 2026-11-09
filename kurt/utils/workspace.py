"""Per-task workspace context; no process-wide chdir across concurrent agents."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from kurt.utils.security import require_public_file

_ROOT = ContextVar('kurt_workspace', default=None)


def active_workspace():
    return _ROOT.get()


def current_workspace():
    return _ROOT.get() or Path.cwd().resolve()


@contextmanager
def workspace(path):
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Workspace must be an existing directory')
    require_public_file(root)
    token = _ROOT.set(root)
    try:
        yield root
    finally:
        _ROOT.reset(token)


def workspace_path(path='.'):
    root = current_workspace()
    original = Path(path).expanduser()
    target = (root / original).resolve() if not original.is_absolute() else original.resolve()
    if target != root and root not in target.parents:
        raise ValueError('Path escapes the active workspace')
    require_public_file(original if original.is_absolute() else root/original)
    return target
