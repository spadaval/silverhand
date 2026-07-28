#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_path=${1:-"$repo_root/_validation/connectivity_report.json"}

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/analyze_connectivity.py \
    --output "$output_path"
