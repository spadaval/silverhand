#!/usr/bin/env python3
"""Historical V27 evidence: audit the rejected split-disk boundary."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import solve_v27_c9_split_surface_family as family  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402
from v27_historical_guard import require_historical_rerun  # noqa: E402


OPERATION = "AUDIT_V27_C9_SPLIT_FIXED_BOUNDARY"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
SPLIT_AUTHORITY = V27 / "v27_c9_split_incidence_authority.json"
OUTPUT = V27 / "v27_c9_split_fixed_boundary_authority.json"


def main() -> None:
    require_historical_rerun(OPERATION)
    split = exact.load_json(SPLIT_AUTHORITY)
    if exact.sha_file(SPLIT_AUTHORITY) != family.EXPECTED_HASHES[
        "split_authority"
    ][1]:
        raise RuntimeError(
            f"{OPERATION}: split authority hash mismatch; "
            f"path={SPLIT_AUTHORITY}"
        )
    source = bpy.data.objects.get(landing.SOURCE_OBJECT)
    cutter = bpy.data.objects.get(landing.CUTTER_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: source mesh missing; object={landing.SOURCE_OBJECT}"
        )
    if cutter is None or cutter.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: cutter mesh missing; object={landing.CUTTER_OBJECT}"
        )
    mesh = source.data
    reconstruction = split["reconstruction_authority"]
    split_symbols = {
        record["reconstructed_symbolic_vertex_id"]
        for record in reconstruction["split_records"]
    }
    boundary_symbols = sorted(
        {
            symbol
            for edge in reconstruction["symbolic_boundary_edges"]
            for symbol in edge["symbolic_vertex_ids"]
        }
    )
    endpoint_targets = {
        int(vertex_id): Vector(coordinate)
        for vertex_id, coordinate in zip(
            landing.TARGET_VERTEX_IDS,
            reconstruction["candidate_endpoint_target"]["moved_coordinates_mm"],
            strict=True,
        )
    }
    context = family.cutter_context(cutter)
    records = []
    for symbol in boundary_symbols:
        if symbol in split_symbols:
            continue
        vertex_id = int(symbol.removeprefix("VSRC_"))
        point = endpoint_targets.get(vertex_id, mesh.vertices[vertex_id].co)
        nearest = family.nearest_frame(point, context)
        records.append(
            {
                "symbolic_vertex_id": symbol,
                "source_vertex_id": vertex_id,
                "coordinate_mm": family.point_record(point),
                "signed_cutter_margin_mm": nearest["signed_margin_mm"],
                "passes_1_7_mm": (
                    nearest["signed_margin_mm"]
                    >= family.MINIMUM_CLEARANCE_MM - family.TOLERANCE_MM
                ),
            }
        )
    failing = [
        record for record in records if not record["passes_1_7_mm"]
    ]
    aggregate = exact.load_json(family.AGGREGATE_AUTHORITY)
    selected_faces = {
        int(value)
        for values in aggregate["aggregate_mask"]["source_face_ids"].values()
        for value in values
    }
    immutable_faces = {
        int(value)
        for values in aggregate["aggregate_mask"][
            "immutable_complement_source_face_ids"
        ].values()
        for value in values
    }
    reconstruction_faces = {
        int(record["source_face_id"])
        for record in reconstruction["face_records"]
    }
    incidence_records = []
    for boundary in failing:
        vertex_id = boundary["source_vertex_id"]
        incident = sorted(
            int(polygon.index)
            for polygon in mesh.polygons
            if vertex_id in polygon.vertices
        )
        incidence_records.append(
            {
                "source_vertex_id": vertex_id,
                "incident_source_face_ids": incident,
                "inside_current_reconstruction_face_ids": sorted(
                    set(incident) & reconstruction_faces
                ),
                "outside_current_reconstruction_face_ids": sorted(
                    set(incident) - reconstruction_faces
                ),
                "outside_aggregate_selected_face_ids": sorted(
                    (set(incident) - reconstruction_faces) & selected_faces
                ),
                "outside_immutable_complement_face_ids": sorted(
                    (set(incident) - reconstruction_faces) & immutable_faces
                ),
                "unclassified_outside_face_ids": sorted(
                    (set(incident) - reconstruction_faces)
                    - selected_faces
                    - immutable_faces
                ),
            }
        )
    result = {
        "operation": OPERATION,
        "status": (
            "V27_C9_SPLIT_FIXED_BOUNDARY_CLEAR"
            if not failing
            else "V27_C9_SPLIT_FIXED_BOUNDARY_BLOCKED"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_input": {
            "path": str(SPLIT_AUTHORITY.relative_to(ROOT)),
            "sha256": exact.sha_file(SPLIT_AUTHORITY),
        },
        "minimum_required_margin_mm": family.MINIMUM_CLEARANCE_MM,
        "fixed_boundary_records": records,
        "failing_fixed_boundary_records": failing,
        "failing_fixed_boundary_incidence_records": incidence_records,
        "minimum_fixed_boundary_margin_mm": min(
            record["signed_cutter_margin_mm"] for record in records
        ),
        "safety": {
            "source_mesh_not_mutated": True,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
        },
    }
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(OUTPUT, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
