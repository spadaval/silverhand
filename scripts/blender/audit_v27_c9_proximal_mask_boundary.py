#!/usr/bin/env python3
"""Historical V27 evidence: audit the proximal C9 micro-repair boundary."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import solve_v27_c9_split_surface_family as family  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402
from v27_historical_guard import require_historical_rerun  # noqa: E402


OPERATION = "AUDIT_V27_C9_PROXIMAL_MASK_BOUNDARY"
ROOT = Path(__file__).resolve().parents[2]
V22 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v22/exact_overlap_attribution.json"
)
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
OUTPUT = V27 / "v27_c9_proximal_mask_boundary_authority.json"
EXPECTED_V22_SHA256 = (
    "d80989e71a37423ac2d3717c0384e8db23ae848fdf97ea97490a23dfa97c9624"
)


def main() -> None:
    require_historical_rerun(OPERATION)
    actual_hash = exact.sha_file(V22)
    if actual_hash != EXPECTED_V22_SHA256:
        raise RuntimeError(
            f"{OPERATION}: V22 authority hash mismatch; path={V22}; "
            f"expected={EXPECTED_V22_SHA256}; actual={actual_hash}"
        )
    authority = exact.load_json(V22)
    mask = set(
        int(value)
        for value in authority["component_9_classification"][
            "proximal_wearer_facing"
        ]["incident_face_ids"]
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
    context = family.cutter_context(cutter)
    vertex_faces: dict[int, set[int]] = defaultdict(set)
    all_edge_faces: dict[tuple[int, int], set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        polygon_vertices = [int(value) for value in polygon.vertices]
        for vertex_id in polygon_vertices:
            vertex_faces[int(vertex_id)].add(int(polygon.index))
        for first, second in zip(
            polygon_vertices,
            polygon_vertices[1:] + polygon_vertices[:1],
            strict=True,
        ):
            all_edge_faces[tuple(sorted((first, second)))].add(
                int(polygon.index)
            )

    def boundary(current_mask: set[int]):
        edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
        for face_id in sorted(current_mask):
            polygon = mesh.polygons[face_id]
            vertices = [int(value) for value in polygon.vertices]
            for first, second in zip(
                vertices, vertices[1:] + vertices[:1], strict=True
            ):
                edge_faces[tuple(sorted((first, second)))].append(face_id)
        edges = sorted(
            edge for edge, faces in edge_faces.items() if len(faces) == 1
        )
        vertices = sorted(
            {vertex_id for edge in edges for vertex_id in edge}
        )
        boundary_records = []
        for vertex_id in vertices:
            point = mesh.vertices[vertex_id].co
            nearest = family.nearest_frame(point, context)
            boundary_records.append(
                {
                    "source_vertex_id": vertex_id,
                    "coordinate_mm": family.point_record(point),
                    "signed_cutter_margin_mm": nearest["signed_margin_mm"],
                    "passes_1_7_mm": (
                        nearest["signed_margin_mm"]
                        >= family.MINIMUM_CLEARANCE_MM - family.TOLERANCE_MM
                    ),
                }
            )
        return edges, vertices, boundary_records

    boundary_edges, boundary_vertices, records = boundary(mask)
    failing = [record for record in records if not record["passes_1_7_mm"]]
    vertex_boundary_degree = Counter(
        vertex_id for edge in boundary_edges for vertex_id in edge
    )
    closure_mask = set(mask)
    closure_iterations = []
    for iteration in range(1, 11):
        edges, vertices, iteration_records = boundary(closure_mask)
        iteration_failing = [
            record
            for record in iteration_records
            if not record["passes_1_7_mm"]
        ]
        if not iteration_failing:
            closure_iterations.append(
                {
                    "iteration": iteration,
                    "face_count_before": len(closure_mask),
                    "failing_boundary_vertex_ids": [],
                    "added_source_face_ids": [],
                    "face_count_after": len(closure_mask),
                    "minimum_boundary_margin_mm": min(
                        record["signed_cutter_margin_mm"]
                        for record in iteration_records
                    ),
                    "closed": True,
                }
            )
            break
        added = sorted(
            {
                face_id
                for record in iteration_failing
                for face_id in vertex_faces[record["source_vertex_id"]]
            }
            - closure_mask
        )
        closure_iterations.append(
            {
                "iteration": iteration,
                "face_count_before": len(closure_mask),
                "failing_boundary_vertex_ids": [
                    record["source_vertex_id"]
                    for record in iteration_failing
                ],
                "added_source_face_ids": added,
                "face_count_after": len(closure_mask) + len(added),
                "minimum_boundary_margin_mm": min(
                    record["signed_cutter_margin_mm"]
                    for record in iteration_records
                ),
                "closed": False,
            }
        )
        if not added:
            break
        closure_mask.update(added)
    closure_edges, closure_vertices, closure_records = boundary(closure_mask)
    closure_failing = [
        record
        for record in closure_records
        if not record["passes_1_7_mm"]
    ]
    def sample_edges(edges):
        sample_records = []
        for first_id, second_id in edges:
            first = mesh.vertices[first_id].co
            second = mesh.vertices[second_id].co
            divisions = max(1, math.ceil((second - first).length))
            margins = [
                family.nearest_frame(
                    first.lerp(second, index / divisions), context
                )["signed_margin_mm"]
                for index in range(divisions + 1)
            ]
            sample_records.append(
                {
                    "source_vertex_ids": [first_id, second_id],
                    "division_count": divisions,
                    "minimum_signed_cutter_margin_mm": min(margins),
                    "passes_1_7_mm": (
                        min(margins)
                        >= family.MINIMUM_CLEARANCE_MM - family.TOLERANCE_MM
                    ),
                }
            )
        return sample_records

    surface_mask = set(closure_mask)
    edge_closure_iterations = []
    for iteration in range(1, 11):
        surface_edges, _, surface_vertex_records = boundary(surface_mask)
        surface_edge_records = sample_edges(surface_edges)
        failing_vertices = [
            record
            for record in surface_vertex_records
            if not record["passes_1_7_mm"]
        ]
        failing_edges = [
            record
            for record in surface_edge_records
            if not record["passes_1_7_mm"]
        ]
        added = {
            face_id
            for record in failing_vertices
            for face_id in vertex_faces[record["source_vertex_id"]]
        }
        added.update(
            face_id
            for record in failing_edges
            for face_id in all_edge_faces[
                tuple(sorted(record["source_vertex_ids"]))
            ]
        )
        added -= surface_mask
        edge_closure_iterations.append(
            {
                "iteration": iteration,
                "face_count_before": len(surface_mask),
                "failing_boundary_vertex_ids": [
                    record["source_vertex_id"]
                    for record in failing_vertices
                ],
                "failing_boundary_edges": [
                    record["source_vertex_ids"]
                    for record in failing_edges
                ],
                "added_source_face_ids": sorted(added),
                "face_count_after": len(surface_mask) + len(added),
                "closed": not failing_vertices and not failing_edges,
            }
        )
        if not failing_vertices and not failing_edges:
            break
        if not added:
            break
        surface_mask.update(added)
    final_edges, final_vertices, final_vertex_records = boundary(surface_mask)
    final_edge_records = sample_edges(final_edges)
    final_failing_vertices = [
        record
        for record in final_vertex_records
        if not record["passes_1_7_mm"]
    ]
    final_failing_edges = [
        record
        for record in final_edge_records
        if not record["passes_1_7_mm"]
    ]
    result = {
        "operation": OPERATION,
        "status": (
            "V27_C9_PROXIMAL_MASK_BOUNDARY_CLEAR"
            if not failing
            else "V27_C9_PROXIMAL_MASK_BOUNDARY_BLOCKED"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_input": {
            "path": str(V22.relative_to(ROOT)),
            "sha256": actual_hash,
        },
        "source_scene": {
            "blend": str(Path(bpy.data.filepath).resolve()),
            "source_object": source.name,
            "cutter_object": cutter.name,
        },
        "mask": {
            "source_face_ids": sorted(mask),
            "face_count": len(mask),
            "boundary_edges": [list(edge) for edge in boundary_edges],
            "boundary_edge_count": len(boundary_edges),
            "boundary_vertex_count": len(boundary_vertices),
            "boundary_is_cycle_union": all(
                degree == 2 for degree in vertex_boundary_degree.values()
            ),
        },
        "minimum_required_margin_mm": family.MINIMUM_CLEARANCE_MM,
        "boundary_vertex_records": records,
        "failing_boundary_vertex_records": failing,
        "minimum_boundary_margin_mm": min(
            record["signed_cutter_margin_mm"] for record in records
        ),
        "necessary_clearance_closure": {
            "iterations": closure_iterations,
            "source_face_ids": sorted(surface_mask),
            "face_count": len(surface_mask),
            "added_source_face_ids": sorted(surface_mask - mask),
            "vertex_clearance_closure_iterations": closure_iterations,
            "edge_clearance_closure_iterations": edge_closure_iterations,
            "boundary_edges": [list(edge) for edge in final_edges],
            "boundary_edge_count": len(final_edges),
            "boundary_vertex_count": len(final_vertices),
            "boundary_vertex_records": final_vertex_records,
            "failing_boundary_vertex_records": final_failing_vertices,
            "passes_fixed_boundary_clearance": not final_failing_vertices,
            "boundary_edge_sample_records": final_edge_records,
            "failing_boundary_edge_sample_records": final_failing_edges,
            "passes_sampled_boundary_edge_clearance": not final_failing_edges,
        },
        "safety": {
            "source_mesh_not_mutated": True,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
        },
    }
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(OUTPUT, result)
    print(json.dumps({
        "status": result["status"],
        "face_count": len(mask),
        "boundary_edge_count": len(boundary_edges),
        "boundary_vertex_count": len(boundary_vertices),
        "failing_boundary_vertex_count": len(failing),
        "minimum_boundary_margin_mm": result["minimum_boundary_margin_mm"],
        "semantic_fingerprint": result["semantic_fingerprint"],
        "closure_face_count": len(surface_mask),
        "closure_added_face_count": len(surface_mask - mask),
        "closure_failing_boundary_vertex_count": len(final_failing_vertices),
        "closure_failing_boundary_edge_count": len(final_failing_edges),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
