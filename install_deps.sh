#!/usr/bin/env bash
# Isolated setup for macOS/Linux. Optional: --features web,media,voice,desktop --cli-tools --browser
set -e
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  exec python3 bootstrap.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python bootstrap.py "$@"
fi
echo "Install Python 3.10+ from https://www.python.org/downloads/ and run this installer again." >&2
exit 1
