#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_path=${1:-"$repo_root/.work/evidence/thickness_report.json"}

if [ "$#" -ge 2 ]; then
    exec "$repo_root/scripts/tools/run_blender_script.sh" \
        scripts/blender/analyze_thickness.py \
        --output "$output_path" \
        --threshold-mm "$2"
fi

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/analyze_thickness.py \
    --output "$output_path"
