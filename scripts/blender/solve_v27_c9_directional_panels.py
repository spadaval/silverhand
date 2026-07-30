#!/usr/bin/env python3
"""Historical V27 evidence: evaluate rejected diagnostic chart panels."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import analyze_v27_c9_landing_surface as surface  # noqa: E402
import solve_v27_c9_split_surface_family as split_family  # noqa: E402
import solve_v27_c9_subdivided_retopology_family as retopo  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402
from v27_historical_guard import require_historical_rerun  # noqa: E402


OPERATION = "SOLVE_V27_C9_DIRECTIONAL_PANELS"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
CHART_AUTHORITY = V27 / "v27_c9_directional_chart_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_directional_panel_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_directional_panel_authority_receipt.json"
EXPECTED_CHART_SHA256 = (
    "4508da1717caaa208242963fdd9efe613b1e0ab2ea395e7b407ad76e46b0f0dd"
)
SUBDIVISIONS = [1, 2, 4]
TARGET_CLEARANCES_MM = [1.7, 2.0, 3.0, 4.0]
TOLERANCE_MM = 1.0e-7


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def solve_scalar_field(
    keys,
    topology,
    baseline_points,
    fixed_edges,
    direction,
    target_clearance,
    context,
):
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
    fixed = {
        key for key in keys if retopo.key_on_boundary(key, fixed_edges)
    }
    required = {}
    unresolved = []
    for key in keys:
        if key in fixed:
            required[key] = 0.0
            continue
        point = baseline_points[key]
        frame = split_family.nearest_frame(point, context)
        if frame["signed_margin_mm"] >= retopo.MINIMUM_CLEARANCE_MM:
            required[key] = 0.0
            continue
        if frame["signed_margin_mm"] < 0.0:
            _, _, _, distance = context["tree"].ray_cast(
                point, direction, 500.0
            )
            if distance is None:
                unresolved.append(key)
                required[key] = 500.0
            else:
                required[key] = float(distance) + target_clearance
            continue
        rate = direction.dot(frame["outward"])
        if rate <= 0.05:
            unresolved.append(key)
            required[key] = 500.0
        else:
            required[key] = (
                retopo.MINIMUM_CLEARANCE_MM - frame["signed_margin_mm"]
            ) / rate
    scalar = dict(required)
    for _ in range(1000):
        updated = {}
        maximum_change = 0.0
        for key in keys:
            if key in fixed:
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
    return scalar, fixed, unresolved


def main():
    require_historical_rerun(OPERATION)
    args = arguments()
    actual_hash = exact.sha_file(CHART_AUTHORITY)
    if actual_hash != EXPECTED_CHART_SHA256:
        raise RuntimeError(
            f"{OPERATION}: chart authority hash mismatch; "
            f"expected={EXPECTED_CHART_SHA256}; actual={actual_hash}; "
            f"path={CHART_AUTHORITY}"
        )
    chart_authority = exact.load_json(CHART_AUTHORITY)
    selection = chart_authority["selection"]
    if selection is None:
        raise RuntimeError(
            f"{OPERATION}: chart authority has no selection; "
            f"path={CHART_AUTHORITY}"
        )
    external_edges = {
        tuple(sorted(int(value) for value in edge))
        for edge in selection["external_boundary_edges"]
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
    context = split_family.cutter_context(cutter)
    panel_results = []
    all_selected = True
    for chart in selection["charts"]:
        face_ids = set(int(value) for value in chart["source_face_ids"])
        source_triangles = []
        chart_edges = set()
        for triangle in mesh.loop_triangles:
            face_id = int(triangle.polygon_index)
            if face_id not in face_ids:
                continue
            vertex_ids = tuple(int(value) for value in triangle.vertices)
            points = tuple(original[index] for index in vertex_ids)
            normal = surface.triangle_area_normal(points)
            source_triangles.append(
                {
                    "triangle_id": int(triangle.index),
                    "face_id": face_id,
                    "vertex_ids": vertex_ids,
                    "source_normal": normal.normalized(),
                }
            )
            chart_edges.update(
                tuple(sorted((first, second)))
                for first, second in (
                    (vertex_ids[0], vertex_ids[1]),
                    (vertex_ids[1], vertex_ids[2]),
                    (vertex_ids[2], vertex_ids[0]),
                )
            )
        fixed_edges = chart_edges & external_edges
        direction = Vector(chart["mean_exit_direction"]).normalized()
        counts = Counter()
        first_counterexamples = {}
        selected_panel = None
        member_index = 0
        for subdivisions in SUBDIVISIONS:
            topology = retopo.subdivided_topology(
                source_triangles, subdivisions
            )
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
                key: retopo.source_point(key, subdivisions, original)
                for key in keys
            }
            baseline = retopo.records_for(
                topology, baseline_points, key_ids
            )
            for target_clearance in TARGET_CLEARANCES_MM:
                scalar, fixed, unresolved = solve_scalar_field(
                    keys,
                    topology,
                    baseline_points,
                    fixed_edges,
                    direction,
                    target_clearance,
                    context,
                )
                candidate_points = {
                    key: baseline_points[key] + direction * scalar[key]
                    for key in keys
                }
                candidate = retopo.records_for(
                    topology, candidate_points, key_ids
                )
                metrics = retopo.metrics(baseline, candidate, context)
                member = {
                    "member_index": member_index,
                    "subdivisions": subdivisions,
                    "target_clearance_mm": target_clearance,
                    "triangle_count": len(candidate),
                    "control_point_count": len(keys),
                    "fixed_external_control_count": len(fixed),
                    "unresolved_exit_control_count": len(unresolved),
                    "maximum_scalar_displacement_mm": max(scalar.values()),
                    **metrics,
                }
                member_index += 1
                if unresolved:
                    reason = "UNRESOLVED_DIRECTIONAL_EXIT"
                elif (
                    metrics["minimum_sampled_cutter_margin_mm"]
                    < retopo.MINIMUM_CLEARANCE_MM - TOLERANCE_MM
                ):
                    reason = "SAMPLED_CUTTER_CLEARANCE_FAILED"
                elif metrics["minimum_normal_dot"] <= 0.0:
                    reason = "ORIENTATION_FAILED"
                elif metrics["minimum_edge_ratio"] < retopo.MINIMUM_EDGE_RATIO:
                    reason = "EDGE_COLLAPSE_FAILED"
                elif metrics["maximum_edge_ratio"] > retopo.MAXIMUM_EDGE_RATIO:
                    reason = "EDGE_STRETCH_FAILED"
                elif (
                    metrics["maximum_triangle_aspect_ratio"]
                    > retopo.MAXIMUM_ASPECT_RATIO
                ):
                    reason = "TRIANGLE_QUALITY_FAILED"
                else:
                    reason = ""
                if reason:
                    counts[reason] += 1
                    first_counterexamples.setdefault(reason, member)
                    continue
                selected_panel = {
                    **member,
                    "direction": split_family.point_record(direction),
                    "control_points": [
                        {
                            "virtual_vertex_id": key_ids[key],
                            "source_barycentric_key": [
                                [vertex_id, weight]
                                for vertex_id, weight in key
                            ],
                            "coordinate_mm": split_family.point_record(
                                candidate_points[key]
                            ),
                            "external_boundary_exact": key in fixed,
                        }
                        for key in keys
                    ],
                    "triangles": [
                        {
                            "triangle_id": record["triangle_id"],
                            "source_face_id": record["face_id"],
                            "vertex_ids": list(record["vertex_ids"]),
                        }
                        for record in candidate
                    ],
                }
                selected_panel["fingerprint"] = exact.stable_hash(
                    selected_panel
                )
                break
            if selected_panel is not None:
                break
        if selected_panel is None:
            all_selected = False
        panel_results.append(
            {
                "chart_id": chart["chart_id"],
                "source_face_ids": chart["source_face_ids"],
                "evaluation": {
                    "evaluated_member_count": member_index,
                    "rejection_counts": dict(sorted(counts.items())),
                    "first_counterexamples": first_counterexamples,
                },
                "selection": selected_panel,
            }
        )
    status = (
        "V27_C9_DIRECTIONAL_PANELS_CHEAP_GATES_SOLVED"
        if all_selected
        else "V27_C9_DIRECTIONAL_PANELS_INCOMPLETE"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": "read-only per-chart directional panel cheap gates",
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_input": {
            "path": str(CHART_AUTHORITY.relative_to(ROOT)),
            "sha256": actual_hash,
        },
        "family": {
            "subdivisions": SUBDIVISIONS,
            "target_clearances_mm": TARGET_CLEARANCES_MM,
        },
        "panels": panel_results,
        "selected_panel_count": sum(
            panel["selection"] is not None for panel in panel_results
        ),
        "required_panel_count": len(panel_results),
        "safety": {
            "source_mesh_not_mutated": True,
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
        "status": status,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "selected_panel_count": result["selected_panel_count"],
        "required_panel_count": result["required_panel_count"],
        "panel_status": {
            str(panel["chart_id"]): (
                panel["selection"]["fingerprint"]
                if panel["selection"] is not None
                else panel["evaluation"]["rejection_counts"]
            )
            for panel in panel_results
        },
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
