#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
bash install_deps.sh "$@"
result=$?
read -r -p "Press Enter to close..." _reply
exit "$result"
