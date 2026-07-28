#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_path=${1:-"$repo_root/_validation/working_geometry_inventory.json"}

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/inventory_working_geometry.py \
    --output "$output_path"
