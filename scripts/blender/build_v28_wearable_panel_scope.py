#!/usr/bin/env python3
"""Build the read-only V28 three-panel wearable-engineering scope.

This script does not repair source topology or emit panel geometry. It converts
the final V27 wearer-side evidence into a deliberately coarse V28 construction
contract: preserve known exterior references, provisionally remove the hidden
failure scope, and author three independent panels from clean cross-sections.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import solve_v27_c9_split_surface_family as geometry  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402


OPERATION = "BUILD_V28_WEARABLE_PANEL_SCOPE"
MISSION = "R014-JOINT-C9-C20-ELBOW-V28"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
V28 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v28"
)
MASK_AUTHORITY = V27 / "v27_c9_proximal_mask_boundary_authority.json"
DEFAULT_OUTPUT = V28 / "v28_wearable_panel_scope_authority.json"
DEFAULT_RECEIPT = V28 / "v28_wearable_panel_scope_authority_receipt.json"
EXPECTED_MASK_SHA256 = (
    "fcc3e370988a4f92b1c3d7932faaec8280b75899e29135c49df7d9dea28dee63"
)
KNOWN_DECORATIVE_EXTERIOR_FACE_IDS = [2219, 2220, 2221, 2225, 2233, 2276]
FIT_REFERENCE_OBJECT = "REF_FIT_ANATOMY_STRAIGHT"
PANEL_COUNT = 3
MINIMUM_CLEARANCE_MM = 1.7
DEFAULT_ENGINEERING_SEAM_MM = 4.0
DEFAULT_CROSS_SECTION_COUNT = 5


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def main() -> None:
    args = arguments()
    actual_hash = exact.sha_file(MASK_AUTHORITY)
    if actual_hash != EXPECTED_MASK_SHA256:
        raise RuntimeError(
            f"{OPERATION}: V27 mask authority hash mismatch; "
            f"path={MASK_AUTHORITY}; expected={EXPECTED_MASK_SHA256}; "
            f"actual={actual_hash}"
        )
    mask_authority = exact.load_json(MASK_AUTHORITY)
    closure = mask_authority["necessary_clearance_closure"]
    if not (
        closure["passes_fixed_boundary_clearance"]
        and closure["passes_sampled_boundary_edge_clearance"]
    ):
        raise RuntimeError(
            f"{OPERATION}: V28_SOURCE_SCOPE_BOUNDARY_NOT_CLEAR; "
            f"authority={MASK_AUTHORITY}; actionable_reason=repair or widen "
            "the source reference scope before authoring panels"
        )
    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = Path(mask_authority["source_scene"]["blend"]).resolve()
    if blend_path != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}; "
            f"actual={blend_path}"
        )
    source = bpy.data.objects.get(landing.SOURCE_OBJECT)
    cutter = bpy.data.objects.get(landing.CUTTER_OBJECT)
    fit_reference = bpy.data.objects.get(FIT_REFERENCE_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: source mesh missing; object={landing.SOURCE_OBJECT}"
        )
    if cutter is None or cutter.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: cutter mesh missing; object={landing.CUTTER_OBJECT}"
        )
    if fit_reference is None or fit_reference.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: fit-reference mesh missing; "
            f"object={FIT_REFERENCE_OBJECT}"
        )
    if not landing.matrix_is_identity(source.matrix_world):
        raise RuntimeError(
            f"{OPERATION}: source object matrix is not identity; "
            f"object={source.name}"
        )

    reference_face_ids = sorted(
        int(value) for value in closure["source_face_ids"]
    )
    reference_set = set(reference_face_ids)
    exterior_set = set(KNOWN_DECORATIVE_EXTERIOR_FACE_IDS)
    if not exterior_set <= reference_set:
        raise RuntimeError(
            f"{OPERATION}: known exterior references left the V27 scope; "
            f"missing={sorted(exterior_set - reference_set)}"
        )
    provisional_removal = sorted(reference_set - exterior_set)

    fit_context = geometry.cutter_context(fit_reference)
    fit_points = np.asarray(
        [geometry.point_record(point) for point in fit_context["points"]]
    )
    center = fit_points.mean(axis=0)
    covariance = np.cov(fit_points - center, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    axis_array = eigenvectors[:, int(np.argmax(eigenvalues))]
    if axis_array[0] < 0.0:
        axis_array *= -1.0
    axis = Vector(axis_array.tolist()).normalized()
    center_vector = Vector(center.tolist())

    face_stations = {}
    for face_id in reference_face_ids:
        polygon = source.data.polygons[face_id]
        centroid = sum(
            (
                source.data.vertices[int(vertex_id)].co
                for vertex_id in polygon.vertices
            ),
            Vector(),
        ) / len(polygon.vertices)
        face_stations[face_id] = float((centroid - center_vector).dot(axis))
    minimum_station = min(face_stations.values())
    maximum_station = max(face_stations.values())
    station_span = maximum_station - minimum_station
    if station_span <= 1.0e-7:
        raise RuntimeError(
            f"{OPERATION}: source reference station span is degenerate; "
            f"minimum={minimum_station}; maximum={maximum_station}"
        )
    cuts = [
        minimum_station + station_span * index / PANEL_COUNT
        for index in range(PANEL_COUNT + 1)
    ]
    panels = []
    for panel_index in range(PANEL_COUNT):
        lower = cuts[panel_index]
        upper = cuts[panel_index + 1]
        is_last = panel_index == PANEL_COUNT - 1
        references = sorted(
            face_id
            for face_id, station in face_stations.items()
            if lower <= station and (station <= upper if is_last else station < upper)
        )
        panels.append(
            {
                "panel_id": f"V28_PANEL_ZONE_{panel_index}",
                "neutral_region_name": True,
                "station_interval_mm": [lower, upper],
                "source_reference_face_ids": references,
                "source_faces_are_not_panel_topology": True,
                "cross_section_station_count": DEFAULT_CROSS_SECTION_COUNT,
                "minimum_clearance_mm": MINIMUM_CLEARANCE_MM,
                "nominal_engineering_seam_mm": DEFAULT_ENGINEERING_SEAM_MM,
                "construction": (
                    "author clean fit-reference measurements and loft "
                    "independently of source, fit, and cutter topology"
                ),
            }
        )
    if sum(len(panel["source_reference_face_ids"]) for panel in panels) != len(
        reference_face_ids
    ):
        raise RuntimeError(
            f"{OPERATION}: panel reference partition is incomplete"
        )

    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": "V28_WEARABLE_PANEL_SCOPE_READY",
        "scope": (
            "read-only three-panel construction contract; no source mutation "
            "and no generated geometry"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_input": {
            "path": str(MASK_AUTHORITY.relative_to(ROOT)),
            "sha256": actual_hash,
        },
        "source_scene": {
            "blend": str(blend_path),
            "source_object": source.name,
            "fit_reference_object": fit_reference.name,
            "cutter_object": cutter.name,
        },
        "source_reference_scope": {
            "face_count": len(reference_face_ids),
            "source_face_ids": reference_face_ids,
            "known_decorative_exterior_face_ids": sorted(exterior_set),
            "provisional_wearer_side_removal_face_ids": provisional_removal,
            "provisional_removal_requires_exterior_review": True,
            "source_boundary_edge_count": closure["boundary_edge_count"],
            "source_boundary_vertex_clearance_passes": closure[
                "passes_fixed_boundary_clearance"
            ],
            "source_boundary_edge_clearance_passes": closure[
                "passes_sampled_boundary_edge_clearance"
            ],
        },
        "construction_frame": {
            "axis": geometry.point_record(axis),
            "center_mm": geometry.point_record(center_vector),
            "station_range_mm": [minimum_station, maximum_station],
            "wearer_landmark_names_assigned": False,
        },
        "panels": panels,
        "contract": {
            "target_panel_count": PANEL_COUNT,
            "additional_panel_requires_named_reason": True,
            "allowed_additional_panel_reasons": [
                "FIT",
                "MOTION",
                "PRINTING",
                "ASSEMBLY",
            ],
            "preserve_recognizable_exterior_character": True,
            "modest_exterior_relocation_or_trim_allowed": True,
            "preserve_intentional_negative_space": True,
            "cutter_triangles_may_supply_panel_topology": False,
            "fit_reference_triangles_may_supply_panel_topology": False,
            "source_faces_may_supply_hidden_panel_topology": False,
            "cutter_use": [
                "CLEARANCE",
                "BOUNDED_SUBTRACTION",
            ],
            "fit_reference_use": [
                "CONSTRUCTION_FRAME",
                "CROSS_SECTION_REFERENCE",
            ],
            "required_clearance_evidence": [
                "VERTICES",
                "CONTINUOUS_BOUNDARY_EDGES",
                "ADAPTIVE_TRIANGLE_INTERIORS",
            ],
        },
        "invariants": {
            "panel_count_is_three": len(panels) == PANEL_COUNT,
            "reference_partition_is_complete": True,
            "source_mesh_not_mutated": True,
            "fit_reference_mesh_not_mutated": True,
            "cutter_mesh_not_mutated": True,
            "geometry_not_emitted": True,
            "blend_not_saved": True,
        },
        "safety": {
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        },
    }
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": result["status"],
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "panel_count": len(panels),
        "source_reference_face_count": len(reference_face_ids),
        "provisional_removal_face_count": len(provisional_removal),
        "known_decorative_exterior_face_count": len(exterior_set),
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
