#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_dir=${1:-"$repo_root/_validation/main_geometry_comparison"}

"$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/render_geometry_comparison.py \
    --output "$output_dir"

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required to build the annotated contact sheet." >&2
    echo "Install uv or run scripts/tools/build_contact_sheet.py with a Python environment containing Pillow." >&2
    exit 2
fi

exec uv run "$repo_root/scripts/tools/build_contact_sheet.py" \
    --manifest "$output_dir/manifest.json"
