"""
KURT Archive — zip a folder for export, unzip a folder for import.
Plain stdlib (shutil + zipfile), no new dependency.
"""

import os
import shutil
import zipfile
from pathlib import Path


def export_folder(src: str, dest: str = None) -> str:
    """Compress a folder into a .zip file. Returns the resulting zip path."""
    src_path = Path(src).expanduser().resolve()
    if not src_path.is_dir():
        raise ValueError(f"Not a folder: {src}")
    if dest:
        dest_path = Path(dest).expanduser()
        if dest_path.suffix.lower() == ".zip":
            dest_path = dest_path.with_suffix("")
    else:
        dest_path = src_path.parent / src_path.name
    archive_path = shutil.make_archive(str(dest_path), "zip", root_dir=str(src_path))
    return archive_path


def import_zip(src: str, dest: str = None) -> str:
    """Extract a .zip file into a folder. Returns the destination folder path.

    Rejects any entry that would resolve outside the destination folder
    (zip-slip path traversal) before extracting anything."""
    src_path = Path(src).expanduser().resolve()
    if not src_path.is_file() or src_path.suffix.lower() != ".zip":
        raise ValueError(f"Not a zip file: {src}")
    dest_path = Path(dest).expanduser().resolve() if dest else src_path.parent / src_path.stem
    dest_path.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src_path) as zf:
        for member in zf.infolist():
            target = (dest_path / member.filename).resolve()
            if target != dest_path and not str(target).startswith(str(dest_path) + os.sep):
                raise ValueError(f"Unsafe zip entry, refusing to extract: {member.filename}")
        zf.extractall(dest_path)
    return str(dest_path)
