#!/usr/bin/env python3
"""Audit the direct 11-face C9 landing deformation without mutating a mesh."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import audit_v26_cutter_authority as cutter_audit  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402


OPERATION = "ANALYZE_V27_C9_LANDING_SURFACE"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
LANDING_AUTHORITY = V27 / "v27_c9_landing_authority.json"
LANDING_RECEIPT = V27 / "v27_c9_landing_authority_receipt.json"
DEFAULT_OUTPUT = V27 / "v27_c9_landing_surface_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_landing_surface_authority_receipt.json"
EXPECTED_LANDING_AUTHORITY_SHA256 = (
    "c2529003261cf0f086c6de01bb700474fc6dfa3c016e03671cf928effa79dfc6"
)
EXPECTED_LANDING_RECEIPT_SHA256 = (
    "e947c383ab4d093a0274160c4d7faa83df1ea4efd98bd36b5134a59807bb285a"
)
MINIMUM_EDGE_RATIO = 0.5
MAXIMUM_EDGE_RATIO = 2.0
MAXIMUM_ASPECT_RATIO = 12.0
TOLERANCE_MM = 1.0e-7


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def point_record(point: Vector) -> list[float]:
    return [float(value) for value in point]


def triangle_area_normal(points: tuple[Vector, Vector, Vector]) -> Vector:
    return (points[1] - points[0]).cross(points[2] - points[0])


def triangle_quality(points: tuple[Vector, Vector, Vector]) -> dict[str, float]:
    lengths = [
        (points[1] - points[0]).length,
        (points[2] - points[1]).length,
        (points[0] - points[2]).length,
    ]
    if min(lengths) <= 1.0e-12:
        return {
            "minimum_angle_degrees": 0.0,
            "aspect_ratio": math.inf,
        }
    angles = []
    for first, second, opposite in (
        (lengths[0], lengths[2], lengths[1]),
        (lengths[0], lengths[1], lengths[2]),
        (lengths[1], lengths[2], lengths[0]),
    ):
        cosine = max(
            -1.0,
            min(
                1.0,
                (
                    first * first
                    + second * second
                    - opposite * opposite
                )
                / (2.0 * first * second),
            ),
        )
        angles.append(math.degrees(math.acos(cosine)))
    return {
        "minimum_angle_degrees": min(angles),
        "aspect_ratio": max(lengths) / min(lengths),
    }


def triangulation(mesh: bpy.types.Mesh) -> list[dict[str, Any]]:
    mesh.calc_loop_triangles()
    return [
        {
            "triangle_id": int(triangle.index),
            "face_id": int(triangle.polygon_index),
            "vertex_ids": tuple(int(value) for value in triangle.vertices),
        }
        for triangle in mesh.loop_triangles
    ]


def segment_contains(point: Vector, first: Vector, second: Vector) -> bool:
    edge = second - first
    if edge.length <= TOLERANCE_MM:
        return (point - first).length <= TOLERANCE_MM
    parameter = (point - first).dot(edge) / edge.length_squared
    if parameter < -TOLERANCE_MM or parameter > 1.0 + TOLERANCE_MM:
        return False
    return (point - (first + edge * parameter)).length <= TOLERANCE_MM


def intersection_points(
    first: tuple[Vector, Vector, Vector],
    second: tuple[Vector, Vector, Vector],
) -> list[Vector]:
    points: list[Vector] = []
    edges = ((0, 1), (1, 2), (2, 0))
    for source, target in ((first, second), (second, first)):
        for start_id, end_id in edges:
            start = source[start_id]
            direction = source[end_id] - start
            if direction.length <= TOLERANCE_MM:
                continue
            point = intersect_ray_tri(
                target[0],
                target[1],
                target[2],
                direction,
                start,
                True,
            )
            if point is None:
                continue
            parameter = (point - start).dot(direction) / direction.length_squared
            if not (-TOLERANCE_MM <= parameter <= 1.0 + TOLERANCE_MM):
                continue
            if not any((point - prior).length <= TOLERANCE_MM for prior in points):
                points.append(point)
    return points


def contact_is_only_shared_topology(
    points: list[Vector],
    shared_vertex_ids: set[int],
    coordinates: list[Vector],
) -> bool:
    if not shared_vertex_ids:
        return False
    shared = sorted(shared_vertex_ids)
    if len(shared) == 1:
        return bool(points) and all(
            (point - coordinates[shared[0]]).length <= TOLERANCE_MM
            for point in points
        )
    shared_edges = [
        (shared[first], shared[second])
        for first in range(len(shared))
        for second in range(first + 1, len(shared))
    ]
    return bool(points) and all(
        any(
            segment_contains(point, coordinates[first], coordinates[second])
            for first, second in shared_edges
        )
        for point in points
    )


def overlap_audit(
    first_records: list[dict[str, Any]],
    second_records: list[dict[str, Any]],
    coordinates: list[Vector],
    same_family: bool,
) -> dict[str, Any]:
    first_points: list[Vector] = []
    first_faces = []
    for record in first_records:
        start = len(first_points)
        first_points.extend(record["points"])
        first_faces.append((start, start + 1, start + 2))
    second_points: list[Vector] = []
    second_faces = []
    for record in second_records:
        start = len(second_points)
        second_points.extend(record["points"])
        second_faces.append((start, start + 1, start + 2))
    first_tree = BVHTree.FromPolygons(first_points, first_faces, all_triangles=True)
    second_tree = BVHTree.FromPolygons(
        second_points, second_faces, all_triangles=True
    )
    raw_pairs = sorted(first_tree.overlap(second_tree))
    conflicts = []
    allowed_contacts = 0
    for first_index, second_index in raw_pairs:
        if same_family and first_index >= second_index:
            continue
        first = first_records[first_index]
        second = second_records[second_index]
        shared = set(first["vertex_ids"]) & set(second["vertex_ids"])
        points = intersection_points(first["points"], second["points"])
        if contact_is_only_shared_topology(points, shared, coordinates):
            allowed_contacts += 1
            continue
        conflicts.append(
            {
                "first_triangle_id": first["triangle_id"],
                "first_face_id": first["face_id"],
                "second_triangle_id": second["triangle_id"],
                "second_face_id": second["face_id"],
                "shared_vertex_ids": sorted(shared),
                "intersection_points_mm": [
                    point_record(point) for point in points
                ],
                "reason": (
                    "no exact witness for BVH overlap"
                    if not points
                    else "intersection extends beyond shared topology"
                ),
            }
        )
    return {
        "raw_bvh_pair_count": len(raw_pairs),
        "allowed_shared_topology_contact_count": allowed_contacts,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def conflict_pair_ids(audit: dict[str, Any]) -> set[tuple[int, int]]:
    return {
        (
            int(record["first_triangle_id"]),
            int(record["second_triangle_id"]),
        )
        for record in audit["conflicts"]
    }


def overlap_delta(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_pairs = conflict_pair_ids(baseline)
    candidate_pairs = conflict_pair_ids(candidate)
    new_pairs = candidate_pairs - baseline_pairs
    resolved_pairs = baseline_pairs - candidate_pairs
    retained_pairs = baseline_pairs & candidate_pairs
    return {
        "baseline": baseline,
        "candidate": candidate,
        "new_conflict_pair_count": len(new_pairs),
        "new_conflict_pair_ids": [list(pair) for pair in sorted(new_pairs)],
        "resolved_conflict_pair_count": len(resolved_pairs),
        "resolved_conflict_pair_ids": [
            list(pair) for pair in sorted(resolved_pairs)
        ],
        "retained_conflict_pair_count": len(retained_pairs),
        "retained_conflict_pair_ids": [
            list(pair) for pair in sorted(retained_pairs)
        ],
    }


def main() -> None:
    args = arguments()
    verified = {
        "landing_authority": {
            "path": str(LANDING_AUTHORITY.relative_to(ROOT)),
            "sha256": exact.sha_file(LANDING_AUTHORITY),
        },
        "landing_receipt": {
            "path": str(LANDING_RECEIPT.relative_to(ROOT)),
            "sha256": exact.sha_file(LANDING_RECEIPT),
        },
    }
    expected = {
        "landing_authority": EXPECTED_LANDING_AUTHORITY_SHA256,
        "landing_receipt": EXPECTED_LANDING_RECEIPT_SHA256,
    }
    for label, record in verified.items():
        if record["sha256"] != expected[label]:
            raise RuntimeError(
                f"{OPERATION}: V27_C9_LANDING_SURFACE_INPUT_HASH_MISMATCH; "
                f"input={label}; expected={expected[label]}; "
                f"actual={record['sha256']}"
            )

    authority = exact.load_json(LANDING_AUTHORITY)
    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = Path(authority["source_scene"]["blend"]).resolve()
    if blend_path != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}; "
            f"actual={blend_path}"
        )
    source = bpy.data.objects.get(landing.SOURCE_OBJECT)
    cutter = bpy.data.objects.get(landing.CUTTER_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: source mesh {landing.SOURCE_OBJECT!r} is missing"
        )
    if cutter is None or cutter.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: cutter mesh {landing.CUTTER_OBJECT!r} is missing"
        )
    if not landing.matrix_is_identity(source.matrix_world):
        raise RuntimeError(
            f"{OPERATION}: source object matrix is not identity"
        )

    mesh = source.data
    original = [vertex.co.copy() for vertex in mesh.vertices]
    candidate = [point.copy() for point in original]
    selected = authority["selection"]
    for vertex_id, coordinate in zip(
        landing.TARGET_VERTEX_IDS,
        selected["moved_endpoint_coordinates_mm"],
        strict=True,
    ):
        candidate[vertex_id] = Vector(coordinate)

    face_mask = set(authority["landing_contract"]["landing_face_mask"])
    endpoint_incident_faces = {
        int(polygon.index)
        for polygon in mesh.polygons
        if set(polygon.vertices) & set(landing.TARGET_VERTEX_IDS)
    }
    if endpoint_incident_faces != face_mask:
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_SURFACE_MASK_INCOMPLETE; "
            f"expected={sorted(face_mask)}; "
            f"actual_endpoint_incidence={sorted(endpoint_incident_faces)}"
        )

    triangles = triangulation(mesh)
    baseline_patch_records = []
    patch_records = []
    complement_records = []
    orientation_records = []
    for record in triangles:
        coordinates = candidate if record["face_id"] in face_mask else original
        expanded = {
            **record,
            "points": tuple(coordinates[index] for index in record["vertex_ids"]),
        }
        if record["face_id"] not in face_mask:
            complement_records.append(expanded)
            continue
        baseline_patch_records.append(
            {
                **record,
                "points": tuple(
                    original[index] for index in record["vertex_ids"]
                ),
            }
        )
        patch_records.append(expanded)
        before_points = tuple(original[index] for index in record["vertex_ids"])
        after_points = expanded["points"]
        before_normal = triangle_area_normal(before_points)
        after_normal = triangle_area_normal(after_points)
        normal_dot = (
            -1.0
            if before_normal.length <= TOLERANCE_MM
            or after_normal.length <= TOLERANCE_MM
            else before_normal.normalized().dot(after_normal.normalized())
        )
        before_quality = triangle_quality(before_points)
        after_quality = triangle_quality(after_points)
        orientation_records.append(
            {
                "triangle_id": record["triangle_id"],
                "face_id": record["face_id"],
                "vertex_ids": list(record["vertex_ids"]),
                "normal_dot": normal_dot,
                "area_ratio": (
                    after_normal.length / before_normal.length
                    if before_normal.length > TOLERANCE_MM
                    else 0.0
                ),
                "before_quality": before_quality,
                "after_quality": after_quality,
            }
        )

    affected_edges = sorted(
        {
            int(edge.index)
            for edge in mesh.edges
            if set(edge.vertices) & set(landing.TARGET_VERTEX_IDS)
        }
    )
    edge_records = []
    for edge_id in affected_edges:
        edge = mesh.edges[edge_id]
        first, second = (int(value) for value in edge.vertices)
        before_length = (original[first] - original[second]).length
        after_length = (candidate[first] - candidate[second]).length
        edge_records.append(
            {
                "edge_id": edge_id,
                "vertex_ids": [first, second],
                "before_length_mm": before_length,
                "after_length_mm": after_length,
                "ratio": (
                    after_length / before_length
                    if before_length > TOLERANCE_MM
                    else math.inf
                ),
            }
        )

    cutter_evaluated = cutter.evaluated_get(
        bpy.context.evaluated_depsgraph_get()
    )
    cutter_mesh = cutter_evaluated.to_mesh()
    try:
        cutter_mesh.calc_loop_triangles()
        cutter_matrix = cutter.matrix_world
        cutter_points = [
            cutter_matrix @ vertex.co for vertex in cutter_mesh.vertices
        ]
        cutter_faces = [
            tuple(int(value) for value in triangle.vertices)
            for triangle in cutter_mesh.loop_triangles
        ]
        signed_volume = sum(
            cutter_points[first].dot(
                cutter_points[second].cross(cutter_points[third])
            )
            for first, second, third in cutter_faces
        ) / 6.0
        orientation_sign = 1.0 if signed_volume >= 0.0 else -1.0
        clearance = cutter_audit.clearance_contract(
            [
                {
                    "triangle_id": record["triangle_id"],
                    "source_fixture": f"source_face_{record['face_id']}",
                    "points": record["points"],
                }
                for record in patch_records
            ],
            cutter_points,
            cutter_faces,
            orientation_sign,
        )
    finally:
        cutter_evaluated.to_mesh_clear()

    clearance_records = [
        {
            "triangle_id": record["candidate_triangle_id"],
            "source_fixture": record["source_fixture"],
            "intersection_pairs": record["intersection_pairs"],
            "minimum_triangle_to_cutter": record[
                "minimum_triangle_to_cutter"
            ],
            "minimum_signed_sample_margin_mm": record[
                "minimum_signed_sample_margin_mm"
            ],
            "rejection_reasons": record["rejection_reasons"],
            "clearance_pass": record["clearance_pass"],
        }
        for record in clearance["triangle_records"]
    ]
    minimum_exact_clearance = min(
        record["minimum_triangle_to_cutter"]["distance_mm"]
        for record in clearance_records
    )
    minimum_signed_margin = min(
        record["minimum_signed_sample_margin_mm"]
        for record in clearance_records
    )

    baseline_complement_overlap = overlap_audit(
        baseline_patch_records,
        complement_records,
        original,
        same_family=False,
    )
    candidate_complement_overlap = overlap_audit(
        patch_records,
        complement_records,
        candidate,
        same_family=False,
    )
    complement_overlap = overlap_delta(
        baseline_complement_overlap,
        candidate_complement_overlap,
    )
    baseline_self_overlap = overlap_audit(
        baseline_patch_records,
        baseline_patch_records,
        original,
        same_family=True,
    )
    candidate_self_overlap = overlap_audit(
        patch_records,
        patch_records,
        candidate,
        same_family=True,
    )
    self_overlap = overlap_delta(
        baseline_self_overlap,
        candidate_self_overlap,
    )

    minimum_normal_dot = min(record["normal_dot"] for record in orientation_records)
    minimum_edge_ratio = min(record["ratio"] for record in edge_records)
    maximum_edge_ratio = max(record["ratio"] for record in edge_records)
    maximum_aspect = max(
        record["after_quality"]["aspect_ratio"]
        for record in orientation_records
    )
    failed = []
    if minimum_normal_dot <= 0.0:
        failed.append("TRIANGLE_ORIENTATION_REVERSAL")
    if minimum_edge_ratio < MINIMUM_EDGE_RATIO:
        failed.append("EDGE_COLLAPSE_BELOW_0.5_RATIO")
    if maximum_edge_ratio > MAXIMUM_EDGE_RATIO:
        failed.append("EDGE_STRETCH_ABOVE_2.0_RATIO")
    if maximum_aspect > MAXIMUM_ASPECT_RATIO:
        failed.append("TRIANGLE_ASPECT_ABOVE_12")
    if clearance["fixture_reject_count"]:
        failed.append("SURFACE_CUTTER_CLEARANCE_FAILED")
    if complement_overlap["new_conflict_pair_count"]:
        failed.append("SOURCE_COMPLEMENT_INTERSECTION")
    if self_overlap["new_conflict_pair_count"]:
        failed.append("LANDING_SURFACE_SELF_INTERSECTION")

    status = (
        "V27_C9_LANDING_DIRECT_SURFACE_FEASIBLE"
        if not failed
        else "V27_C9_LANDING_DIRECT_SURFACE_REJECTED"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": (
            "read-only in-memory direct deformation of the exact 11-face "
            "landing one-ring using the reviewed endpoint coordinates"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": verified,
        "source_scene": {
            "blend": str(blend_path),
            "source_object": source.name,
            "cutter_object": cutter.name,
        },
        "candidate": {
            "landing_face_ids": sorted(face_mask),
            "target_vertex_ids": list(landing.TARGET_VERTEX_IDS),
            "moved_endpoint_coordinates_mm": selected[
                "moved_endpoint_coordinates_mm"
            ],
            "triangle_count": len(patch_records),
            "affected_edge_count": len(edge_records),
            "fingerprint": exact.stable_hash(
                {
                    "landing_face_ids": sorted(face_mask),
                    "target_vertex_ids": list(landing.TARGET_VERTEX_IDS),
                    "moved_endpoint_coordinates_mm": selected[
                        "moved_endpoint_coordinates_mm"
                    ],
                    "triangle_vertex_ids": [
                        list(record["vertex_ids"]) for record in patch_records
                    ],
                }
            ),
        },
        "surface_metrics": {
            "minimum_normal_dot": minimum_normal_dot,
            "minimum_edge_ratio": minimum_edge_ratio,
            "maximum_edge_ratio": maximum_edge_ratio,
            "maximum_triangle_aspect_ratio": maximum_aspect,
            "minimum_exact_triangle_cutter_clearance_mm": (
                minimum_exact_clearance
            ),
            "minimum_signed_sample_margin_mm": minimum_signed_margin,
            "orientation_records": orientation_records,
            "affected_edge_records": edge_records,
            "clearance_records": clearance_records,
            "source_complement_overlap": complement_overlap,
            "self_overlap": self_overlap,
        },
        "acceptance": {
            "minimum_normal_dot_exclusive": 0.0,
            "minimum_edge_ratio": MINIMUM_EDGE_RATIO,
            "maximum_edge_ratio": MAXIMUM_EDGE_RATIO,
            "maximum_triangle_aspect_ratio": MAXIMUM_ASPECT_RATIO,
            "minimum_exact_and_signed_cutter_clearance_mm": (
                landing.MINIMUM_CLEARANCE_MM
            ),
            "source_complement_conflict_count": 0,
            "self_intersection_conflict_count": 0,
        },
        "failed_invariants": failed,
        "invariants": {
            "landing_authority_hash_matches": True,
            "landing_receipt_hash_matches": True,
            "source_matrix_is_identity": True,
            "landing_mask_is_complete_endpoint_one_ring": True,
            "source_mesh_not_mutated": True,
            "candidate_geometry_not_emitted": True,
        },
        "safety": {
            "mutation_started": False,
            "candidate_surface_geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
            "gate_b_run": False,
            "gate_d_run": False,
        },
    }
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "candidate_fingerprint": result["candidate"]["fingerprint"],
        "failed_invariants": failed,
        "surface_metrics": {
            key: result["surface_metrics"][key]
            for key in (
                "minimum_normal_dot",
                "minimum_edge_ratio",
                "maximum_edge_ratio",
                "maximum_triangle_aspect_ratio",
                "minimum_exact_triangle_cutter_clearance_mm",
                "minimum_signed_sample_margin_mm",
            )
        },
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
