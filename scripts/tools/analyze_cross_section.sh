#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

if [ "$#" -lt 2 ]; then
    echo "ERROR: cross-section requires a fit station index and objects." >&2
    echo "Usage: scripts/tools/analyze_cross_section.sh STATION_INDEX OBJECT..." >&2
    exit 2
fi

station_index=$1
shift
output_path="$repo_root/.work/evidence/cross_section_station_${station_index}.json"

exec "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/analyze_cross_section.py \
    --station-index "$station_index" \
    --objects "$@" \
    --output "$output_path"
