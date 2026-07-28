#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

if [ "$#" -lt 1 ]; then
    echo "ERROR: missing Blender Python script path." >&2
    echo "Usage: scripts/tools/run_blender_script.sh SCRIPT [SCRIPT_ARGUMENTS...]" >&2
    exit 2
fi

script_path=$1
shift
case "$script_path" in
    /*) ;;
    *) script_path="$repo_root/$script_path" ;;
esac

blend_file=${BLEND_FILE:-"$repo_root/reference/Johnny.blend"}

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

if [ ! -f "$blend_file" ]; then
    echo "ERROR: Blender input file '$blend_file' does not exist." >&2
    exit 2
fi
if [ ! -f "$script_path" ]; then
    echo "ERROR: Blender Python script '$script_path' does not exist." >&2
    exit 2
fi

exec "$blender_bin" \
    --background \
    --python-exit-code 1 \
    "$blend_file" \
    --python "$script_path" \
    -- \
    "$@"
