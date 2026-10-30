#!/bin/zsh
set -eu
script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
exec python3 "$script_dir/Rebuild/Scripts/clean-macos.py"
