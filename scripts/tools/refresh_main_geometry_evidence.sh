#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
output_root=${1:-"$repo_root/_validation/main_geometry_evidence"}
mkdir -p "$output_root"

run_evidence_step() {
    step_name=$1
    log_path=$2
    shift 2
    echo "START $step_name"
    if ! "$@" >"$log_path" 2>&1; then
        echo "ERROR: $step_name failed; log: $log_path" >&2
        tail -100 "$log_path" >&2
        exit 1
    fi
    echo "DONE  $step_name"
}

run_evidence_step \
    "master scene validation" \
    "$output_root/master_validation.log" \
    "$repo_root/scripts/tools/run_blender_script.sh" \
    scripts/blender/validate_master.py

run_evidence_step \
    "working geometry inventory" \
    "$output_root/inventory.log" \
    "$repo_root/scripts/tools/inventory_working_geometry.sh" \
    "$output_root/working_geometry_inventory.json"

run_evidence_step \
    "clearance analysis" \
    "$output_root/clearance.log" \
    "$repo_root/scripts/tools/analyze_clearance.sh" \
    "$output_root/clearance_report.json"

run_evidence_step \
    "connectivity analysis" \
    "$output_root/connectivity.log" \
    "$repo_root/scripts/tools/analyze_connectivity.sh" \
    "$output_root/connectivity_report.json"

run_evidence_step \
    "thickness analysis" \
    "$output_root/thickness.log" \
    "$repo_root/scripts/tools/analyze_thickness.sh" \
    "$output_root/thickness_report.json"

run_evidence_step \
    "fit profile extraction" \
    "$output_root/fit_profile.log" \
    "$repo_root/scripts/tools/analyze_fit_profile.sh" \
    "$output_root/fit_profile.json"

run_evidence_step \
    "matched visual comparison" \
    "$output_root/comparison.log" \
    "$repo_root/scripts/tools/render_geometry_comparison.sh" \
    "$output_root/comparison"

echo "Evidence refresh complete: $output_root"
