#!/usr/bin/env python3
"""Read-only exact-match audit. Outputs counts/paths, never secret values.

Run from the repository: python3 tools/security_audit.py
Does not detect retired/unknown secrets or prove absence of compromise.
"""
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kurt.utils.security import secret_values

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def main():
    secrets = [v.encode() for v in secret_values()]
    def matches(data):
        return any(value in data for value in secrets)
    files = git('ls-files', '-z').decode().split('\0')
    tree_hits, count = [], 0
    for name in filter(None, files):
        path = ROOT/name
        if path.is_file() and not path.is_symlink():
            count += 1
            if matches(path.read_bytes()): tree_hits.append(name)
    objects = git('rev-list', '--objects', '--all').decode().splitlines()
    blobs, history_hits = 0, 0
    # Read individual blobs; never echo Git content or credential-bearing paths.
    for line in objects:
        oid = line.split(' ', 1)[0]
        if git('cat-file', '-t', oid).strip() != b'blob': continue
        blobs += 1
        if matches(git('cat-file', 'blob', oid)): history_hits += 1
    modes = {}
    for name in ('.env', 'mcp_connections.json', 'memory.db'):
        path = Path.home()/'.kurt'/name
        if path.exists(): modes[name] = oct(path.stat().st_mode & 0o777)
    report = {'configured_secret_values_checked': len(secrets), 'tracked_files_scanned':count,
              'tracked_matching_paths':tree_hits, 'reachable_git_blobs_scanned':blobs,
              'reachable_matching_blobs':history_hits, 'private_file_modes':modes,
              'limits':'Exact current-value matches only; excludes unknown/retired keys, unreachable Git objects, remote copies and third-party runtime activity.'}
    print(json.dumps(report, indent=2))
    return bool(tree_hits or history_hits)

if __name__ == '__main__':
    raise SystemExit(main())
