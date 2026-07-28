#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

if [ "$#" -ne 2 ]; then
    echo "ERROR: export requires an explicit manifest and output directory." >&2
    echo "Usage: scripts/tools/export_from_manifest.sh MANIFEST OUTPUT_DIR" >&2
    exit 2
fi

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/export_from_manifest.py \
    --manifest "$1" \
    --output-dir "$2"
