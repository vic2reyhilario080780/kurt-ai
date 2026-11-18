#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m kurt.main chat
fi
echo "Run Install Kurt.command (macOS) or bash install_deps.sh (Linux) first."
exit 1
