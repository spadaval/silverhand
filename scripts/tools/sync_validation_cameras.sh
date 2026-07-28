#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/sync_validation_cameras.py \
    --save
