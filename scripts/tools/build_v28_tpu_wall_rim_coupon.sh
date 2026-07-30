#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
default_blend="$repo_root/blender_files/experiments/geometry_repair/repair_014_joint_c9_c20_elbow_v28_reversible_edge_softening.blend"

if [ -z "${BLEND_FILE:-}" ]; then
    BLEND_FILE=$default_blend
    export BLEND_FILE
fi

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/build_v28_tpu_wall_rim_coupon.py \
    "$@"
