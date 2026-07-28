#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_dir=${1:-"$repo_root/_validation/previews"}

if [ -n "${BLENDER_PATH:-}" ]; then
    blender_bin=$BLENDER_PATH
elif command -v blender >/dev/null 2>&1; then
    blender_bin=$(command -v blender)
elif [ -x "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    blender_bin="/Applications/Blender.app/Contents/MacOS/Blender"
else
    echo "ERROR: Blender executable not found. Set BLENDER_PATH to the executable." >&2
    exit 2
fi

exec "$blender_bin" \
    --background \
    --python-exit-code 1 \
    --factory-startup \
    --python "$repo_root/scripts/blender/render_validation_previews.py" \
    -- "$repo_root/exports/current" "$output_dir"
