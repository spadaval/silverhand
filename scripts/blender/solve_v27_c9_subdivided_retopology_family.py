#!/usr/bin/env python3
"""Evaluate cutter-following subdivision retopology for the proximal C9 mask."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Vector
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import analyze_v27_c9_landing_surface as surface  # noqa: E402
import solve_v27_c9_split_surface_family as split_family  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402


OPERATION = "SOLVE_V27_C9_SUBDIVIDED_RETOPOLOGY_FAMILY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
MASK_AUTHORITY = V27 / "v27_c9_proximal_mask_boundary_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_subdivided_retopology_family_authority.json"
DEFAULT_RECEIPT = (
    V27 / "v27_c9_subdivided_retopology_family_authority_receipt.json"
)
EXPECTED_MASK_SHA256 = (
    "fcc3e370988a4f92b1c3d7932faaec8280b75899e29135c49df7d9dea28dee63"
)
SUBDIVISIONS = [2, 4, 8]
TARGET_CLEARANCES_MM = [1.7, 2.0, 2.5, 3.0, 4.0]
MINIMUM_CLEARANCE_MM = 1.7
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


def barycentric_key(
    vertex_ids: tuple[int, int, int],
    weights: tuple[int, int, int],
) -> tuple[tuple[int, int], ...]:
    combined: dict[int, int] = {}
    for vertex_id, weight in zip(vertex_ids, weights, strict=True):
        if weight:
            combined[vertex_id] = combined.get(vertex_id, 0) + weight
    return tuple(sorted(combined.items()))


def subdivided_topology(
    source_triangles: list[dict[str, Any]], subdivisions: int
) -> list[dict[str, Any]]:
    result = []
    triangle_id = 0
    for source in source_triangles:
        vertex_ids = source["vertex_ids"]
        for first in range(subdivisions):
            for second in range(subdivisions - first):
                third = subdivisions - first - second
                a = (first, second, third)
                b = (first + 1, second, third - 1)
                c = (first, second + 1, third - 1)
                result.append(
                    {
                        "triangle_id": triangle_id,
                        "source_face_id": source["face_id"],
                        "source_normal": source["source_normal"],
                        "keys": tuple(
                            barycentric_key(vertex_ids, weights)
                            for weights in (a, b, c)
                        ),
                    }
                )
                triangle_id += 1
                if third >= 2:
                    d = (first + 1, second + 1, third - 2)
                    result.append(
                        {
                            "triangle_id": triangle_id,
                            "source_face_id": source["face_id"],
                            "source_normal": source["source_normal"],
                            "keys": tuple(
                                barycentric_key(vertex_ids, weights)
                                for weights in (b, d, c)
                            ),
                        }
                    )
                    triangle_id += 1
    return result


def source_point(
    key: tuple[tuple[int, int], ...],
    subdivisions: int,
    original: list[Vector],
) -> Vector:
    return sum(
        (
            original[vertex_id] * (weight / subdivisions)
            for vertex_id, weight in key
        ),
        Vector(),
    )


def key_on_boundary(
    key: tuple[tuple[int, int], ...],
    boundary_edges: set[tuple[int, int]],
) -> bool:
    vertex_ids = tuple(vertex_id for vertex_id, _ in key)
    if len(vertex_ids) == 1:
        return vertex_ids[0] in {
            vertex_id for edge in boundary_edges for vertex_id in edge
        }
    return (
        len(vertex_ids) == 2
        and tuple(sorted(vertex_ids)) in boundary_edges
    )


def project_point(
    point: Vector,
    target_clearance: float,
    context: dict[str, Any],
) -> tuple[Vector, float]:
    frame = split_family.nearest_frame(point, context)
    if frame["signed_margin_mm"] >= target_clearance:
        return point.copy(), frame["signed_margin_mm"]
    if frame["signed_margin_mm"] < 0.0:
        direction = context["global_exit_direction"]
        location, _, _, _ = context["tree"].ray_cast(
            point, direction, 500.0
        )
        if location is not None:
            return location + direction * target_clearance, frame[
                "signed_margin_mm"
            ]
    return (
        frame["nearest_point"] + frame["outward"] * target_clearance,
        frame["signed_margin_mm"],
    )


def records_for(
    topology: list[dict[str, Any]],
    points: dict[tuple[tuple[int, int], ...], Vector],
    key_ids: dict[tuple[tuple[int, int], ...], int],
) -> list[dict[str, Any]]:
    return [
        {
            "triangle_id": record["triangle_id"],
            "face_id": record["source_face_id"],
            "vertex_ids": tuple(key_ids[key] for key in record["keys"]),
            "points": tuple(points[key] for key in record["keys"]),
            "source_normal": record["source_normal"],
        }
        for record in topology
    ]


def metrics(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, float]:
    minimum_dot = 1.0
    minimum_edge_ratio = float("inf")
    maximum_edge_ratio = 0.0
    maximum_aspect = 0.0
    minimum_margin = float("inf")
    seen_edges = set()
    for before, after in zip(baseline, candidate, strict=True):
        normal = surface.triangle_area_normal(after["points"])
        source_normal = after["source_normal"]
        normal_dot = (
            -1.0
            if normal.length <= TOLERANCE_MM
            else normal.normalized().dot(source_normal)
        )
        minimum_dot = min(minimum_dot, normal_dot)
        maximum_aspect = max(
            maximum_aspect,
            surface.triangle_quality(after["points"])["aspect_ratio"],
        )
        first, second, third = after["points"]
        for point in (
            first,
            second,
            third,
            (first + second) * 0.5,
            (second + third) * 0.5,
            (third + first) * 0.5,
            (first + second + third) / 3.0,
        ):
            minimum_margin = min(
                minimum_margin,
                split_family.nearest_frame(point, context)[
                    "signed_margin_mm"
                ],
            )
        for first_index, second_index in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((
                after["vertex_ids"][first_index],
                after["vertex_ids"][second_index],
            )))
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            before_length = (
                before["points"][first_index]
                - before["points"][second_index]
            ).length
            after_length = (
                after["points"][first_index]
                - after["points"][second_index]
            ).length
            ratio = (
                math.inf
                if before_length <= TOLERANCE_MM
                else after_length / before_length
            )
            minimum_edge_ratio = min(minimum_edge_ratio, ratio)
            maximum_edge_ratio = max(maximum_edge_ratio, ratio)
    return {
        "minimum_normal_dot": minimum_dot,
        "minimum_edge_ratio": minimum_edge_ratio,
        "maximum_edge_ratio": maximum_edge_ratio,
        "maximum_triangle_aspect_ratio": maximum_aspect,
        "minimum_sampled_cutter_margin_mm": minimum_margin,
    }


def main() -> None:
    args = arguments()
    actual_mask_hash = exact.sha_file(MASK_AUTHORITY)
    if actual_mask_hash != EXPECTED_MASK_SHA256:
        raise RuntimeError(
            f"{OPERATION}: mask authority hash mismatch; "
            f"expected={EXPECTED_MASK_SHA256}; actual={actual_mask_hash}; "
            f"path={MASK_AUTHORITY}"
        )
    authority = exact.load_json(MASK_AUTHORITY)
    closure = authority["necessary_clearance_closure"]
    if not (
        closure["passes_fixed_boundary_clearance"]
        and closure["passes_sampled_boundary_edge_clearance"]
    ):
        raise RuntimeError(
            f"{OPERATION}: reconstruction boundary is not continuously clear; "
            f"path={MASK_AUTHORITY}"
        )
    mask = set(int(value) for value in closure["source_face_ids"])
    boundary_edges = {
        tuple(sorted(int(value) for value in edge))
        for edge in closure["boundary_edges"]
    }
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
    original = [vertex.co.copy() for vertex in mesh.vertices]
    mesh.calc_loop_triangles()
    source_triangles = []
    for triangle in mesh.loop_triangles:
        face_id = int(triangle.polygon_index)
        if face_id not in mask:
            continue
        vertex_ids = tuple(int(value) for value in triangle.vertices)
        points = tuple(original[index] for index in vertex_ids)
        normal = surface.triangle_area_normal(points)
        if normal.length <= TOLERANCE_MM:
            raise RuntimeError(
                f"{OPERATION}: degenerate source triangle; "
                f"triangle={triangle.index}; face={face_id}"
            )
        source_triangles.append(
            {
                "triangle_id": int(triangle.index),
                "face_id": face_id,
                "vertex_ids": vertex_ids,
                "source_normal": normal.normalized(),
            }
        )
    context = split_family.cutter_context(cutter)
    cutter_array = np.asarray(
        [split_family.point_record(point) for point in context["points"]]
    )
    principal_center = cutter_array.mean(axis=0)
    covariance = np.cov(cutter_array - principal_center, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    principal_axis = eigenvectors[:, int(np.argmax(eigenvalues))]
    context["principal_center"] = Vector(principal_center.tolist())
    context["principal_axis"] = Vector(principal_axis.tolist()).normalized()
    patch_vertex_ids = sorted(
        {
            vertex_id
            for triangle in source_triangles
            for vertex_id in triangle["vertex_ids"]
        }
    )
    negative_frames = [
        split_family.nearest_frame(original[vertex_id], context)
        for vertex_id in patch_vertex_ids
        if split_family.nearest_frame(original[vertex_id], context)[
            "signed_margin_mm"
        ]
        < 0.0
    ]
    global_exit_direction = sum(
        (frame["outward"] for frame in negative_frames), Vector()
    )
    if global_exit_direction.length <= TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: global exit direction is degenerate; "
            f"negative_frame_count={len(negative_frames)}"
        )
    context["global_exit_direction"] = global_exit_direction.normalized()
    family_definition = {
        "projection_mode": "GLOBAL_EXIT_DIRECTION_HARMONIC_SCALAR_MAJORANT",
        "global_exit_direction": split_family.point_record(
            context["global_exit_direction"]
        ),
        "subdivisions": SUBDIVISIONS,
        "target_clearances_mm": TARGET_CLEARANCES_MM,
        "ordering": "subdivision declaration order, then target clearance declaration order",
        "member_count": len(SUBDIVISIONS) * len(TARGET_CLEARANCES_MM),
        "source_face_count": len(mask),
        "boundary_edge_count": len(boundary_edges),
    }
    family_fingerprint = exact.stable_hash(family_definition)
    counts: Counter[str] = Counter()
    first_counterexamples = {}
    best_clearance = None
    best_orientation = None
    selected = None
    member_index = 0
    for subdivisions in SUBDIVISIONS:
        topology = subdivided_topology(source_triangles, subdivisions)
        keys = sorted(
            {key for record in topology for key in record["keys"]}
        )
        key_ids = {
            key: (
                key[0][0]
                if len(key) == 1 and key[0][1] == subdivisions
                else len(original) + index
            )
            for index, key in enumerate(keys)
        }
        baseline_points = {
            key: source_point(key, subdivisions, original) for key in keys
        }
        baseline = records_for(topology, baseline_points, key_ids)
        adjacency = {key: set() for key in keys}
        for record in topology:
            first, second, third = record["keys"]
            for start, end in (
                (first, second),
                (second, third),
                (third, first),
            ):
                adjacency[start].add(end)
                adjacency[end].add(start)
        for target_clearance in TARGET_CLEARANCES_MM:
            required = {}
            for key in keys:
                point = baseline_points[key]
                if key_on_boundary(key, boundary_edges):
                    required[key] = 0.0
                    continue
                frame = split_family.nearest_frame(point, context)
                if frame["signed_margin_mm"] >= MINIMUM_CLEARANCE_MM:
                    required[key] = 0.0
                    continue
                if frame["signed_margin_mm"] < 0.0:
                    _, _, _, distance = context["tree"].ray_cast(
                        point,
                        context["global_exit_direction"],
                        500.0,
                    )
                    required[key] = (
                        float(distance) + target_clearance
                        if distance is not None
                        else 500.0
                    )
                    continue
                outward_rate = context["global_exit_direction"].dot(
                    frame["outward"]
                )
                required[key] = (
                    (
                        MINIMUM_CLEARANCE_MM
                        - frame["signed_margin_mm"]
                    )
                    / outward_rate
                    if outward_rate > 0.05
                    else 500.0
                )
            scalar = dict(required)
            for _ in range(1000):
                updated = {}
                maximum_change = 0.0
                for key in keys:
                    if key_on_boundary(key, boundary_edges):
                        updated[key] = 0.0
                        continue
                    average = sum(
                        scalar[neighbor] for neighbor in adjacency[key]
                    ) / len(adjacency[key])
                    updated[key] = max(required[key], average)
                    maximum_change = max(
                        maximum_change, abs(updated[key] - scalar[key])
                    )
                scalar = updated
                if maximum_change <= 1.0e-7:
                    break
            candidate_points = {
                key: (
                    baseline_points[key]
                    + context["global_exit_direction"] * scalar[key]
                )
                for key in keys
            }
            moved_key_count = sum(
                value > TOLERANCE_MM for value in scalar.values()
            )
            candidate = records_for(topology, candidate_points, key_ids)
            result_metrics = metrics(baseline, candidate, context)
            member = {
                "member_index": member_index,
                "subdivisions": subdivisions,
                "target_clearance_mm": target_clearance,
                "triangle_count": len(candidate),
                "control_point_count": len(keys),
                "moved_control_point_count": moved_key_count,
                "maximum_scalar_displacement_mm": max(scalar.values()),
                **result_metrics,
            }
            member_index += 1
            if (
                best_clearance is None
                or result_metrics["minimum_sampled_cutter_margin_mm"]
                > best_clearance["minimum_sampled_cutter_margin_mm"]
            ):
                best_clearance = member
            if (
                best_orientation is None
                or result_metrics["minimum_normal_dot"]
                > best_orientation["minimum_normal_dot"]
            ):
                best_orientation = member
            if (
                result_metrics["minimum_sampled_cutter_margin_mm"]
                < MINIMUM_CLEARANCE_MM - TOLERANCE_MM
            ):
                reason = "SAMPLED_CUTTER_CLEARANCE_FAILED"
            elif result_metrics["minimum_normal_dot"] <= 0.0:
                reason = "ORIENTATION_FAILED"
            elif result_metrics["minimum_edge_ratio"] < MINIMUM_EDGE_RATIO:
                reason = "EDGE_COLLAPSE_FAILED"
            elif result_metrics["maximum_edge_ratio"] > MAXIMUM_EDGE_RATIO:
                reason = "EDGE_STRETCH_FAILED"
            elif (
                result_metrics["maximum_triangle_aspect_ratio"]
                > MAXIMUM_ASPECT_RATIO
            ):
                reason = "TRIANGLE_QUALITY_FAILED"
            else:
                reason = ""
            if reason:
                counts[reason] += 1
                first_counterexamples.setdefault(reason, member)
                continue
            selected = {
                **member,
                "candidate_control_points": [
                    {
                        "virtual_vertex_id": key_ids[key],
                        "source_barycentric_key": [
                            [vertex_id, weight]
                            for vertex_id, weight in key
                        ],
                        "coordinate_mm": split_family.point_record(
                            candidate_points[key]
                        ),
                        "boundary_exact": key_on_boundary(
                            key, boundary_edges
                        ),
                    }
                    for key in keys
                ],
                "candidate_triangles": [
                    {
                        "triangle_id": record["triangle_id"],
                        "source_face_id": record["face_id"],
                        "vertex_ids": list(record["vertex_ids"]),
                    }
                    for record in candidate
                ],
            }
            selected["fingerprint"] = exact.stable_hash(selected)
            break
        if selected is not None:
            break
    status = (
        "V27_C9_SUBDIVIDED_RETOPOLOGY_CHEAP_GATES_SOLVED"
        if selected is not None
        else "V27_C9_SUBDIVIDED_RETOPOLOGY_FAMILY_EXHAUSTED"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": "read-only cutter-following subdivision retopology cheap gates",
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_input": {
            "path": str(MASK_AUTHORITY.relative_to(ROOT)),
            "sha256": actual_mask_hash,
        },
        "finite_family": family_definition,
        "family_fingerprint": family_fingerprint,
        "evaluation": {
            "evaluated_member_count": member_index,
            "rejection_counts": dict(sorted(counts.items())),
            "first_counterexamples": first_counterexamples,
            "best_clearance_counterexample": best_clearance,
            "best_orientation_counterexample": best_orientation,
        },
        "selection": selected,
        "invariants": {
            "source_mesh_not_mutated": True,
            "candidate_geometry_not_emitted": True,
        },
        "safety": {
            "mutation_started": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
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
        "family_fingerprint": family_fingerprint,
        "evaluated_member_count": member_index,
        "rejection_counts": dict(sorted(counts.items())),
        "selection_fingerprint": (
            selected["fingerprint"] if selected is not None else None
        ),
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
