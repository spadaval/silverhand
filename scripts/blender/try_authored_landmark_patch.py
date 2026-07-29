"""Evaluate one authored component-20 landmark-cell retriangulation.

The exact Repair 013 base is required. Component 20 cluster 1 is moved only to
the 1.7 mm minimum cutter floor. The seven-triangle fan around source vertex
4863 is replaced by the winding-compatible heptagon triangulation that
maximizes its minimum triangle angle. No generic sweep is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import acos, degrees
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import evaluated_geometry, point_margins  # noqa: E402
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    RESERVED_WALL_MM,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, mesh_neighbors  # noqa: E402
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    violation_clusters,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    REVIEW_COLLECTION,
    clamp_to_reserved_wall,
    create_object,
    ensure_collection,
    mesh_audit,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    audit_noncontiguous,
    face_normal,
    triangle_quality,
    validate_base,
)


OPERATION = "AUTHORED_LANDMARK_PATCH"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
CELL_FACE_IDS = [7471, 7472, 7473, 7474, 7475, 7477, 7478]
CELL_CENTER_VERTEX_ID = 4863
BOUNDARY_VERTEX_IDS = [4860, 4861, 4864, 4865, 4866, 4867, 4869]
DOCUMENTED_DIAGONAL_FLIP_CELL_FACE_COUNT = 49


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, default=20)
    parser.add_argument("--cluster", type=int, default=1)
    parser.add_argument("--floor-offset-mm", type=float, default=1.7)
    parser.add_argument(
        "--required-base-sha256",
        default=EXPECTED_BASE_SHA256,
    )
    parser.add_argument(
        "--required-base-shape-key",
        default=EXPECTED_BASE_SHAPE_KEY,
    )
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.component != 20 or args.cluster != 1:
        parser.error("this authored candidate is fixed to component 20 cluster 1")
    if args.floor_offset_mm != 1.7:
        parser.error("this authored candidate requires --floor-offset-mm 1.7")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def validate_cell(faces: list[tuple[int, ...]]) -> None:
    expected = [
        (CELL_CENTER_VERTEX_ID, BOUNDARY_VERTEX_IDS[offset],
         BOUNDARY_VERTEX_IDS[(offset + 1) % len(BOUNDARY_VERTEX_IDS)])
        for offset in range(len(BOUNDARY_VERTEX_IDS))
    ]
    for face_id, expected_vertices in zip(CELL_FACE_IDS, expected):
        actual = faces[face_id]
        if len(actual) != 3 or set(actual) != set(expected_vertices):
            raise RuntimeError(
                f"{OPERATION}: source face {face_id} has vertices {actual}, "
                f"expected fan triangle {expected_vertices}"
            )
    incident = [
        index
        for index, face in enumerate(faces)
        if CELL_CENTER_VERTEX_ID in face
    ]
    if incident != CELL_FACE_IDS:
        raise RuntimeError(
            f"{OPERATION}: interior source vertex {CELL_CENTER_VERTEX_ID} is "
            f"incident to faces {incident}, expected exactly {CELL_FACE_IDS}"
        )


def polygon_triangulations(count: int) -> list[list[tuple[int, int, int]]]:
    cache: dict[tuple[int, int], list[list[tuple[int, int, int]]]] = {}

    def solve(start: int, end: int) -> list[list[tuple[int, int, int]]]:
        key = (start, end)
        if key in cache:
            return cache[key]
        if end <= start + 1:
            return [[]]
        result = []
        for middle in range(start + 1, end):
            for left in solve(start, middle):
                for right in solve(middle, end):
                    result.append(
                        left + right + [(start, middle, end)]
                    )
        cache[key] = result
        return result

    return solve(0, count - 1)


def triangle_angles(
    triangle: tuple[int, int, int],
    points: list[Vector],
) -> list[float]:
    a, b, c = (points[index] for index in triangle)
    lengths = [(a - b).length, (b - c).length, (c - a).length]
    if min(lengths) <= 1.0e-12:
        return [0.0, 0.0, 0.0]
    result = []
    for first, second, opposite in (
        (lengths[0], lengths[2], lengths[1]),
        (lengths[0], lengths[1], lengths[2]),
        (lengths[1], lengths[2], lengths[0]),
    ):
        cosine = (
            first * first + second * second - opposite * opposite
        ) / (2.0 * first * second)
        result.append(degrees(acos(max(-1.0, min(1.0, cosine)))))
    return result


def choose_triangulation(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> tuple[list[tuple[int, int, int]], dict]:
    reference = sum(
        (face_normal(points, faces[index]) for index in CELL_FACE_IDS),
        Vector(),
    )
    if reference.length <= 1.0e-12:
        raise RuntimeError(
            f"{OPERATION}: seven-face cell has no coherent reference normal"
        )
    reference.normalize()
    candidates = []
    for local_faces in polygon_triangulations(len(BOUNDARY_VERTEX_IDS)):
        triangles = [
            tuple(BOUNDARY_VERTEX_IDS[index] for index in triangle)
            for triangle in local_faces
        ]
        normals = [face_normal(points, triangle) for triangle in triangles]
        if any(
            normal.length <= 1.0e-12 or normal.dot(reference) <= 0.0
            for normal in normals
        ):
            continue
        angles = [
            angle
            for triangle in triangles
            for angle in triangle_angles(triangle, points)
        ]
        edge_lengths = [
            (points[first] - points[second]).length
            for triangle in triangles
            for first, second in zip(
                triangle,
                triangle[1:] + triangle[:1],
            )
        ]
        candidates.append(
            (
                min(angles),
                -max(edge_lengths),
                triangles,
                {
                    "minimum_angle_degrees": round(min(angles), 6),
                    "maximum_edge_mm": round(max(edge_lengths), 6),
                },
            )
        )
    if not candidates:
        raise RuntimeError(
            f"{OPERATION}: no winding-compatible triangulation exists for "
            f"boundary loop {BOUNDARY_VERTEX_IDS}"
        )
    selected = max(candidates, key=lambda value: (value[0], value[1]))
    return selected[2], {
        "candidate_count": len(candidates),
        **selected[3],
    }


def fingerprint(
    ids: list[int],
    points_by_source_id: dict[int, Vector],
) -> str:
    digest = hashlib.sha256()
    for source_id in ids:
        point = points_by_source_id[source_id]
        digest.update(struct.pack("<Qddd", source_id, *point))
    return digest.hexdigest()


def retained_orientation_locators(
    before: list[Vector],
    before_faces: list[tuple[int, ...]],
    after: list[Vector],
    after_faces: list[tuple[int, ...]],
    retained_face_ids: list[int],
) -> dict:
    locators = []
    for after_id, source_face_id in enumerate(retained_face_ids):
        before_normal = face_normal(before, before_faces[source_face_id])
        after_normal = face_normal(after, after_faces[after_id])
        if (
            before_normal.length <= 1.0e-12
            or after_normal.length <= 1.0e-12
        ):
            continue
        dot = before_normal.dot(after_normal)
        if dot < 0.0:
            locators.append(
                {
                    "source_face": source_face_id,
                    "result_face": after_id,
                    "normal_dot": round(dot, 6),
                }
            )
    return {"count": len(locators), "locators": locators}


def topology_delta(
    before_obj: bpy.types.Object,
    after_obj: bpy.types.Object,
) -> dict:
    before = mesh_audit(before_obj)
    after = mesh_audit(after_obj)
    before_winding = audit_noncontiguous(before_obj)
    after_winding = audit_noncontiguous(after_obj)
    return {
        "before": before,
        "after": after,
        "connected_component_delta": (
            after["connected_components"] - before["connected_components"]
        ),
        "boundary_edge_delta": (
            after["boundary_edges"] - before["boundary_edges"]
        ),
        "nonmanifold_edge_delta": (
            after["nonmanifold_edges"] - before["nonmanifold_edges"]
        ),
        "noncontiguous_manifold_edge_delta": (
            after_winding["noncontiguous_manifold_edges"]
            - before_winding["noncontiguous_manifold_edges"]
        ),
    }


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    repair_base = validate_base(
        candidate,
        args.required_base_sha256,
        args.required_base_shape_key,
    )
    _, components = connected_components(source)
    component = set(components[args.component])
    before, faces, material_indices = evaluated_geometry(candidate)
    validate_cell(faces)
    materials = {material_indices[index] for index in CELL_FACE_IDS}
    if len(materials) != 1:
        raise RuntimeError(
            f"{OPERATION}: selected source faces have materials "
            f"{sorted(materials)}, expected one preserved material"
        )
    replacement_material = next(iter(materials))
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    clusters = violation_clusters(
        component,
        before_margins,
        mesh_neighbors(source.data),
    )
    cluster = clusters[args.cluster]
    after_by_source_id = {index: point.copy() for index, point in enumerate(before)}
    for index in cluster:
        after_by_source_id[index] = clamp_to_reserved_wall(
            before[index],
            target_length,
            grid,
            args.floor_offset_mm,
        )
    replacement_source_faces, selection_quality = choose_triangulation(
        [after_by_source_id[index] for index in range(len(before))],
        faces,
    )

    retained_records = [
        (index, face, material_indices[index])
        for index, face in enumerate(faces)
        if index not in CELL_FACE_IDS
    ]
    used_source_ids = sorted(
        {
            vertex
            for _, face, _ in retained_records
            for vertex in face
        }
        | {
            vertex
            for face in replacement_source_faces
            for vertex in face
        }
    )
    if CELL_CENTER_VERTEX_ID in used_source_ids:
        raise RuntimeError(
            f"{OPERATION}: retired interior vertex "
            f"{CELL_CENTER_VERTEX_ID} remains used after retriangulation"
        )
    remap = {
        source_id: result_id
        for result_id, source_id in enumerate(used_source_ids)
    }
    after = [after_by_source_id[index] for index in used_source_ids]
    after_faces = [
        tuple(remap[index] for index in face)
        for _, face, _ in retained_records
    ]
    after_materials = [material for _, _, material in retained_records]
    replacement_start = len(after_faces)
    after_faces.extend(
        tuple(remap[index] for index in face)
        for face in replacement_source_faces
    )
    after_materials.extend(
        [replacement_material] * len(replacement_source_faces)
    )
    replacement_range = (replacement_start, len(after_faces))

    before_overlaps = overlap_pairs(
        before,
        faces,
        cutter_points,
        cutter_faces,
    )
    after_overlaps = overlap_pairs(
        after,
        after_faces,
        cutter_points,
        cutter_faces,
    )
    before_region_overlaps = sum(
        first in CELL_FACE_IDS for first, _ in before_overlaps
    )
    after_region_overlaps = sum(
        replacement_range[0] <= first < replacement_range[1]
        for first, _ in after_overlaps
    )
    after_margins = point_margins(after, target_length, grid)
    source_to_result = {
        source_id: result_id for result_id, source_id in enumerate(used_source_ids)
    }
    cluster_after_failures = [
        source_id
        for source_id in cluster
        if source_id in source_to_result
        and after_margins[source_to_result[source_id]]
        < RESERVED_WALL_MM - TOLERANCE_MM
    ]

    unchanged_ids = sorted(set(used_source_ids) - set(cluster))
    before_fp = fingerprint(
        unchanged_ids,
        {index: point for index, point in enumerate(before)},
    )
    after_fp = fingerprint(unchanged_ids, after_by_source_id)
    retained_face_ids = [index for index, _, _ in retained_records]
    retained_reversals = retained_orientation_locators(
        before,
        faces,
        after,
        after_faces,
        retained_face_ids,
    )
    reference_normal = sum(
        (face_normal(before, faces[index]) for index in CELL_FACE_IDS),
        Vector(),
    ).normalized()
    replacement_reversals = []
    for face_id in range(*replacement_range):
        dot = face_normal(after, after_faces[face_id]).dot(reference_normal)
        if dot < 0.0:
            replacement_reversals.append(
                {"result_face": face_id, "normal_dot": round(dot, 6)}
            )

    collection = ensure_collection(REVIEW_COLLECTION)
    before_obj = create_object(
        f"{args.prefix}_BEFORE",
        before,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    after_obj = create_object(
        f"{args.prefix}_AFTER",
        after,
        after_faces,
        after_materials,
        list(candidate.data.materials),
        collection,
    )
    topology = topology_delta(before_obj, after_obj)
    quality = triangle_quality(
        after,
        after_faces,
        replacement_range,
    )
    gate_pass = all(
        (
            not cluster_after_failures,
            after_region_overlaps <= before_region_overlaps,
            retained_reversals["count"] == 0,
            not replacement_reversals,
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edge_delta"] == 0,
            before_fp == after_fp,
        )
    )
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if gate_pass
            else "evaluation_only_gate_failure"
        ),
        "repair_base": repair_base,
        "selection": {
            "component": args.component,
            "cluster": args.cluster,
            "cluster_vertex_ids": cluster,
            "floor_offset_mm": args.floor_offset_mm,
            "removed_face_ids": CELL_FACE_IDS,
            "retired_interior_vertex_id": CELL_CENTER_VERTEX_ID,
            "verified_boundary_loop_vertex_ids": BOUNDARY_VERTEX_IDS,
            "replacement_faces_source_vertex_ids": replacement_source_faces,
            "material_index": replacement_material,
            "documented_diagonal_flip_cell_face_count": (
                DOCUMENTED_DIAGONAL_FLIP_CELL_FACE_COUNT
            ),
            "diagonal_changes_outside_selected_cell": 0,
            "triangulation_selection": selection_quality,
        },
        "clearance": {
            "before_global_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in before_margins
            ),
            "after_global_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in after_margins
            ),
            "before_global_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in before_margins
            ),
            "after_global_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in after_margins
            ),
            "cluster_reserved_failure_source_vertex_ids": (
                cluster_after_failures
            ),
            "before_global_triangle_overlaps": len(before_overlaps),
            "after_global_triangle_overlaps": len(after_overlaps),
            "before_replacement_region_overlaps": before_region_overlaps,
            "after_replacement_region_overlaps": after_region_overlaps,
        },
        "orientation": {
            "retained_faces": retained_reversals,
            "replacement_faces": {
                "count": len(replacement_reversals),
                "locators": replacement_reversals,
            },
        },
        "topology": topology,
        "quality": quality,
        "unchanged_outside_fingerprint": {
            "before": before_fp,
            "after": after_fp,
            "equal": before_fp == after_fp,
        },
        "gate_pass": gate_pass,
        "gate_failure_reason": (
            None
            if gate_pass
            else (
                f"{OPERATION}: authored cell failed one or more exact "
                "clearance, overlap, orientation, topology, or unchanged-"
                "outside gates"
            )
        ),
        "objects": {"before": before_obj.name, "after": after_obj.name},
        "qualitative_review": "PENDING",
        "promotion": "NOT_PROMOTED",
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: authored landmark patch gate_pass={gate_pass}; promotion "
        "remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
