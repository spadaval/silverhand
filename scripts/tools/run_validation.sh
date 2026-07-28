#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec python3 "$repo_root/scripts/tools/validate_stl_exports.py" \
  "$repo_root/exports/current" "$@"
