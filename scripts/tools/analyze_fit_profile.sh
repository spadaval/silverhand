#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_path=${1:-"$repo_root/.work/evidence/fit_profile.json"}

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/analyze_fit_profile.py \
    --output "$output_path"
