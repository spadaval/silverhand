"""Build one deterministic combined component-20 inner-bowl liner candidate.

The exact coordinated-interface EVAL object is the geometry base. Exactly 724
mapped wearer-facing faces are replaced while retained geometry, materials,
open routes, aperture loops, and staged component-9/interface coordinates stay
exact. This tool creates evaluation objects only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    evaluated_geometry,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    radial_coordinates,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    clamp_to_reserved_wall,
    create_object,
    ensure_collection,
    mesh_audit,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    REVIEW_COLLECTION,
    audit_noncontiguous,
    triangle_quality,
)


OPERATION = "COMBINED_AUTHORED_INNER_BOWL_LINER"
STAGED_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
EXPECTED_BLEND_SHA256 = (
    "393a7c1a29c96c876fe2be849c3b9a4e42c771416cd59b3f733a7f0c65342bcd"
)
MAPPING_PATH = Path(
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_full_recon_map/mapping.json"
)
INITIAL_FLOOR_MM = 2.5
TARGET_EDGE_MM = 5.0
MAXIMUM_EDGE_MM = 6.0
PUSH_STEP_MM = 0.5
MAXIMUM_PUSH_ITERATIONS = 80
TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-blend-sha256",
        default=EXPECTED_BLEND_SHA256,
    )
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(sys.argv[separator + 1 :])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def fingerprint(
    source_ids: list[int],
    points: list[Vector],
) -> str:
    digest = hashlib.sha256()
    for source_id, point in sorted(zip(source_ids, points)):
        digest.update(struct.pack("<Qddd", source_id, *point))
    return digest.hexdigest()


def face_edges(face: tuple[int, ...]) -> list[tuple[int, int]]:
    return [
        tuple(sorted((first, second)))
        for first, second in zip(face, face[1:] + face[:1])
    ]


def boundary_cycles(
    faces: list[tuple[int, ...]],
    rebuild_faces: set[int],
) -> tuple[list[list[int]], set[tuple[int, int]]]:
    counts = Counter(
        edge
        for face_id in rebuild_faces
        for edge in face_edges(faces[face_id])
    )
    boundary = {edge for edge, count in counts.items() if count == 1}
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in boundary:
        adjacency[first].add(second)
        adjacency[second].add(first)
    invalid = {
        vertex: len(neighbors)
        for vertex, neighbors in adjacency.items()
        if len(neighbors) not in {2, 4}
    }
    if invalid:
        raise RuntimeError(
            f"{OPERATION}: removed-region boundary has unsupported vertex "
            f"degrees {invalid}; expected closed cycles with at most one "
            "shared articulation"
        )
    unused = set(boundary)
    cycles = []
    while unused:
        branch_candidates = sorted(
            vertex
            for vertex, neighbors in adjacency.items()
            if len(neighbors) == 4
            and any(
                tuple(sorted((vertex, neighbor))) in unused
                for neighbor in neighbors
            )
        )
        start = (
            branch_candidates[0]
            if branch_candidates
            else min(min(edge) for edge in unused)
        )
        first = min(
            neighbor
            for neighbor in adjacency[start]
            if tuple(sorted((start, neighbor))) in unused
        )
        cycle = [start]
        current = first
        unused.remove(tuple(sorted((start, first))))
        while current != start:
            cycle.append(current)
            choices = sorted(
                neighbor
                for neighbor in adjacency[current]
                if tuple(sorted((current, neighbor))) in unused
            )
            if not choices:
                raise RuntimeError(
                    f"{OPERATION}: boundary walk from V{start} terminated "
                    f"at V{current} instead of closing"
                )
            following = choices[0]
            unused.remove(tuple(sorted((current, following))))
            current = following
            if len(cycle) > len(boundary) + 1:
                raise RuntimeError(
                    f"{OPERATION}: boundary walk from V{start} did not "
                    "converge"
                )
        cycles.append(cycle)
    return cycles, boundary


def mean_region_normal(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    face_ids: set[int],
) -> Vector:
    normal = Vector((0.0, 0.0, 0.0))
    for face_id in sorted(face_ids):
        face = faces[face_id]
        origin = points[face[0]]
        for offset in range(1, len(face) - 1):
            normal += (points[face[offset]] - origin).cross(
                points[face[offset + 1]] - origin
            )
    if normal.length <= 1.0e-9:
        raise RuntimeError(
            f"{OPERATION}: removed-region mean normal is degenerate"
        )
    return normal.normalized()


def plane_basis(normal: Vector) -> tuple[Vector, Vector]:
    helper = (
        Vector((1.0, 0.0, 0.0))
        if abs(normal.x) < 0.8
        else Vector((0.0, 1.0, 0.0))
    )
    first = normal.cross(helper).normalized()
    return first, normal.cross(first).normalized()


def projected(
    point: Vector,
    first: Vector,
    second: Vector,
) -> tuple[float, float]:
    return point.dot(first), point.dot(second)


def signed_area(loop: list[int], projected_points: dict[int, tuple]) -> float:
    result = 0.0
    for first, second in zip(loop, loop[1:] + loop[:1]):
        x1, y1 = projected_points[first]
        x2, y2 = projected_points[second]
        result += x1 * y2 - x2 * y1
    return result * 0.5


def point_in_polygon(
    point: tuple[float, float],
    loop: list[int],
    projected_points: dict[int, tuple],
) -> bool:
    x, y = point
    inside = False
    for first, second in zip(loop, loop[1:] + loop[:1]):
        x1, y1 = projected_points[first]
        x2, y2 = projected_points[second]
        if (y1 > y) == (y2 > y):
            continue
        crossing = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        if crossing > x:
            inside = not inside
    return inside


def orient_boundary_loops(
    cycles: list[list[int]],
    points: list[Vector],
    normal: Vector,
) -> tuple[list[list[int]], list[int]]:
    first, second = plane_basis(normal)
    ids = {vertex for cycle in cycles for vertex in cycle}
    projected_points = {
        vertex: projected(points[vertex], first, second) for vertex in ids
    }
    depths = []
    result = []
    for index, cycle in enumerate(cycles):
        centroid = (
            sum(projected_points[vertex][0] for vertex in cycle) / len(cycle),
            sum(projected_points[vertex][1] for vertex in cycle) / len(cycle),
        )
        depth = sum(
            point_in_polygon(centroid, other, projected_points)
            for other_index, other in enumerate(cycles)
            if other_index != index
        )
        area = signed_area(cycle, projected_points)
        should_positive = depth % 2 == 0
        oriented = list(cycle)
        if (area > 0.0) != should_positive:
            oriented.reverse()
        result.append(oriented)
        depths.append(depth)
    return result, depths


def triangle_normal(
    points: list[Vector],
    face: tuple[int, int, int],
) -> Vector:
    return (points[face[1]] - points[face[0]]).cross(
        points[face[2]] - points[face[0]]
    )


def tessellate_boundaries(
    cycles: list[list[int]],
    points: list[Vector],
    normal: Vector,
) -> list[tuple[int, int, int]]:
    vectors = [[points[index].copy() for index in cycle] for cycle in cycles]
    coordinate_ids: dict[tuple[float, float, float], int] = {}
    flattened_ids = []
    for cycle, loop_vectors in zip(cycles, vectors):
        for source_id, point in zip(cycle, loop_vectors):
            coordinate_ids[tuple(point)] = source_id
            flattened_ids.append(source_id)
    triangles = []
    for triangle in tessellate_polygon(vectors):
        if triangle and isinstance(triangle[0], int):
            try:
                face = tuple(flattened_ids[index] for index in triangle)
            except IndexError as error:
                raise RuntimeError(
                    f"{OPERATION}: tessellator emitted flattened index "
                    f"outside 0..{len(flattened_ids) - 1}: {triangle}"
                ) from error
        else:
            try:
                face = tuple(
                    coordinate_ids[tuple(point)] for point in triangle
                )
            except KeyError as error:
                raise RuntimeError(
                    f"{OPERATION}: tessellator emitted an unknown boundary "
                    f"coordinate {error}"
                ) from error
        if len(set(face)) != 3:
            continue
        if triangle_normal(points, face).dot(normal) < 0.0:
            face = (face[0], face[2], face[1])
        triangles.append(face)
    if not triangles:
        raise RuntimeError(
            f"{OPERATION}: tessellate_polygon returned no triangles for "
            f"{len(cycles)} closed boundary loops"
        )
    return triangles


def barycentric_contains(
    point: tuple[float, float],
    triangle: list[tuple[float, float]],
) -> bool:
    (x, y), (x1, y1), (x2, y2), (x3, y3) = (
        point,
        triangle[0],
        triangle[1],
        triangle[2],
    )
    denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(denominator) <= 1.0e-12:
        return False
    first = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / denominator
    second = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / denominator
    third = 1.0 - first - second
    return min(first, second, third) >= -1.0e-7


def insert_fixed_controls(
    triangles: list[tuple[int, int, int]],
    controls: list[int],
    points: list[Vector],
    normal: Vector,
) -> list[tuple[int, int, int]]:
    first, second = plane_basis(normal)
    coordinates = {
        index: projected(point, first, second)
        for index, point in enumerate(points)
    }
    result = list(triangles)
    present = {vertex for face in result for vertex in face}
    for control in controls:
        if control in present:
            continue
        containing = next(
            (
                index
                for index, face in enumerate(result)
                if barycentric_contains(
                    coordinates[control],
                    [coordinates[vertex] for vertex in face],
                )
            ),
            None,
        )
        if containing is None:
            raise RuntimeError(
                f"{OPERATION}: exact interface control V{control} is not "
                "represented by retained geometry and cannot be inserted "
                "inside the boundary tessellation"
            )
        face = result.pop(containing)
        additions = [
            (face[0], face[1], control),
            (face[1], face[2], control),
            (face[2], face[0], control),
        ]
        for addition in additions:
            if triangle_normal(points, addition).dot(normal) < 0.0:
                addition = (addition[0], addition[2], addition[1])
            result.append(addition)
        present.add(control)
    return result


def subdivide_replacement(
    triangles: list[tuple[int, int, int]],
    boundary: set[tuple[int, int]],
    points: list[Vector],
    fixed_source_ids: set[int],
) -> tuple[list[Vector], list[tuple[int, int, int]], list[int]]:
    used = sorted({vertex for face in triangles for vertex in face})
    source_to_local = {
        source_id: local_id for local_id, source_id in enumerate(used)
    }
    mesh = bpy.data.meshes.new("REPAIR_014_LINER_TEMP")
    mesh.from_pydata(
        [points[index] for index in used],
        [],
        [
            tuple(source_to_local[index] for index in face)
            for face in triangles
        ],
    )
    mesh.update()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        for _ in range(12):
            long_edges = [
                edge
                for edge in bm.edges
                if not edge.is_boundary
                and edge.calc_length() > MAXIMUM_EDGE_MM
            ]
            if not long_edges:
                break
            bmesh.ops.subdivide_edges(
                bm,
                edges=long_edges,
                cuts=1,
                use_grid_fill=True,
            )
            bm.verts.ensure_lookup_table()
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.verts.ensure_lookup_table()
        result_points = [vertex.co.copy() for vertex in bm.verts]
        coordinate_source_ids = {
            tuple(points[source_id]): source_id for source_id in used
        }
        source_ids = [
            coordinate_source_ids.get(tuple(vertex.co), -1)
            for vertex in bm.verts
        ]
        result_faces = [tuple(vertex.index for vertex in face.verts) for face in bm.faces]
    finally:
        bm.free()
        bpy.data.meshes.remove(mesh)
    for source_id in fixed_source_ids:
        if source_id not in source_ids:
            raise RuntimeError(
                f"{OPERATION}: subdivision lost exact control V{source_id}"
            )
    return result_points, result_faces, source_ids


def project_new_vertices(
    replacement_points: list[Vector],
    source_ids: list[int],
    old_region_points: list[Vector],
    old_region_faces: list[tuple[int, ...]],
    target_length: float,
    grid: list[list[float]],
) -> set[int]:
    region_bvh = BVHTree.FromPolygons(
        old_region_points,
        old_region_faces,
        all_triangles=False,
    )
    new_ids = set()
    for index, source_id in enumerate(source_ids):
        if source_id >= 0:
            continue
        nearest = region_bvh.find_nearest(replacement_points[index])
        source_sample = nearest[0] if nearest is not None else replacement_points[index]
        replacement_points[index] = clamp_to_reserved_wall(
            source_sample,
            target_length,
            grid,
            INITIAL_FLOOR_MM,
        )
        new_ids.add(index)
    return new_ids


def converge_triangle_clearance(
    points: list[Vector],
    faces: list[tuple[int, int, int]],
    new_ids: set[int],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
    target_length: float,
) -> dict:
    history = []
    for iteration in range(MAXIMUM_PUSH_ITERATIONS + 1):
        overlaps = overlap_pairs(points, faces, cutter_points, cutter_faces)
        history.append(len(overlaps))
        if not overlaps:
            return {
                "converged": True,
                "iterations": iteration,
                "overlap_history": history,
                "terminal_overlap_pairs": [],
            }
        movable = sorted(
            {
                vertex
                for face_id, _ in overlaps
                for vertex in faces[face_id]
                if vertex in new_ids
            }
        )
        if not movable or iteration == MAXIMUM_PUSH_ITERATIONS:
            return {
                "converged": False,
                "iterations": iteration,
                "overlap_history": history,
                "terminal_overlap_pairs": [
                    [face_id, cutter_id]
                    for face_id, cutter_id in sorted(overlaps)
                ],
                "terminal_unmovable_face_ids": sorted(
                    {
                        face_id
                        for face_id, _ in overlaps
                        if not set(faces[face_id]) & new_ids
                    }
                ),
            }
        for vertex in movable:
            _, _, _, direction = radial_coordinates(
                points[vertex],
                target_length,
            )
            points[vertex] += direction * PUSH_STEP_MM
    raise AssertionError("unreachable")


def remap_combined(
    staged_points: list[Vector],
    staged_faces: list[tuple[int, ...]],
    material_indices: list[int],
    rebuild_faces: set[int],
    replacement_points: list[Vector],
    replacement_faces: list[tuple[int, int, int]],
    replacement_source_ids: list[int],
    replacement_material: int,
) -> tuple[list[Vector], list[tuple[int, ...]], list[int], list[int], list[int]]:
    retained_records = [
        (face_id, staged_faces[face_id], material_indices[face_id])
        for face_id in range(len(staged_faces))
        if face_id not in rebuild_faces
    ]
    used_source_ids = sorted(
        {
            vertex
            for _, face, _ in retained_records
            for vertex in face
        }
        | {
            source_id
            for source_id in replacement_source_ids
            if source_id >= 0
        }
    )
    source_to_result = {
        source_id: result_id
        for result_id, source_id in enumerate(used_source_ids)
    }
    result_points = [staged_points[source_id].copy() for source_id in used_source_ids]
    replacement_to_result = {}
    for local_id, source_id in enumerate(replacement_source_ids):
        if source_id >= 0:
            replacement_to_result[local_id] = source_to_result[source_id]
        else:
            replacement_to_result[local_id] = len(result_points)
            result_points.append(replacement_points[local_id].copy())
    result_faces = [
        tuple(source_to_result[vertex] for vertex in face)
        for _, face, _ in retained_records
    ]
    result_materials = [material for _, _, material in retained_records]
    replacement_start = len(result_faces)
    result_faces.extend(
        tuple(replacement_to_result[vertex] for vertex in face)
        for face in replacement_faces
    )
    result_materials.extend(
        [replacement_material] * len(replacement_faces)
    )
    return (
        result_points,
        result_faces,
        result_materials,
        used_source_ids,
        [replacement_start, len(result_faces)],
    )


def topology_record(before_obj: bpy.types.Object, after_obj: bpy.types.Object) -> dict:
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
        "boundary_edge_delta": after["boundary_edges"] - before["boundary_edges"],
        "nonmanifold_edge_delta": (
            after["nonmanifold_edges"] - before["nonmanifold_edges"]
        ),
        "noncontiguous_manifold_edges": (
            after_winding["noncontiguous_manifold_edges"]
        ),
        "noncontiguous_manifold_edge_delta": (
            after_winding["noncontiguous_manifold_edges"]
            - before_winding["noncontiguous_manifold_edges"]
        ),
    }


def main() -> int:
    args = parse_args()
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha = sha256_file(blend_path)
    if actual_sha != args.required_blend_sha256:
        raise RuntimeError(
            f"{OPERATION}: staged blend '{blend_path}' has SHA-256 "
            f"{actual_sha}, expected {args.required_blend_sha256}"
        )
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    staged = require_mesh(STAGED_NAME, "coordinated-interface staged geometry")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    rebuild_faces = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    retain_c20_faces = set(mapping["reconstruction_scope"]["retain_face_ids"])
    staged_points, staged_faces, materials = evaluated_geometry(staged)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    _, components = connected_components(source)
    component9 = set(components[9])
    component20 = set(components[20])
    component20_faces = {
        face_id
        for face_id, face in enumerate(staged_faces)
        if face[0] in component20
    }
    if rebuild_faces | retain_c20_faces != component20_faces:
        raise RuntimeError(
            f"{OPERATION}: mapped component-20 partition does not match "
            "staged topology"
        )
    cycles, complete_boundary = boundary_cycles(staged_faces, rebuild_faces)
    mapped_seam = {
        tuple(sorted(edge))
        for group in mapping["exact_full_inner_bowl_seam"]["boundary_groups"]
        for edge in group["edge_vertex_ids"]
    }
    if not mapped_seam <= complete_boundary:
        raise RuntimeError(
            f"{OPERATION}: {len(mapped_seam - complete_boundary)} mapped "
            "seam edges are absent from the complete removed-region boundary"
        )
    normal = mean_region_normal(staged_points, staged_faces, rebuild_faces)
    cycles, cycle_depths = orient_boundary_loops(
        cycles,
        staged_points,
        normal,
    )
    coarse = tessellate_boundaries(cycles, staged_points, normal)
    retained_vertices = {
        vertex
        for face_id, face in enumerate(staged_faces)
        if face_id not in rebuild_faces
        for vertex in face
    }
    interface_ids = {
        record["component_20_vertex_id"]
        for record in mapping["exact_component_9_attachment_landmarks"][
            "vertex_records"
        ]
    }
    removed_only_controls = sorted(interface_ids - retained_vertices)
    coarse = insert_fixed_controls(
        coarse,
        removed_only_controls,
        staged_points,
        normal,
    )
    fixed_source_ids = (
        set().union(*map(set, cycles)) | set(removed_only_controls)
    )
    (
        replacement_points,
        replacement_faces,
        replacement_source_ids,
    ) = subdivide_replacement(
        coarse,
        complete_boundary,
        staged_points,
        fixed_source_ids,
    )
    old_region_vertex_ids = sorted(
        {
            vertex
            for face_id in rebuild_faces
            for vertex in staged_faces[face_id]
        }
    )
    old_to_local = {
        source_id: local_id
        for local_id, source_id in enumerate(old_region_vertex_ids)
    }
    old_region_points = [staged_points[index] for index in old_region_vertex_ids]
    old_region_faces = [
        tuple(old_to_local[vertex] for vertex in staged_faces[face_id])
        for face_id in sorted(rebuild_faces)
    ]
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    new_ids = project_new_vertices(
        replacement_points,
        replacement_source_ids,
        old_region_points,
        old_region_faces,
        target_length,
        grid,
    )
    convergence = converge_triangle_clearance(
        replacement_points,
        replacement_faces,
        new_ids,
        cutter_points,
        cutter_faces,
        target_length,
    )
    replacement_material = Counter(
        materials[face_id] for face_id in rebuild_faces
    ).most_common(1)[0][0]
    (
        result_points,
        result_faces,
        result_materials,
        retained_source_ids,
        replacement_range,
    ) = remap_combined(
        staged_points,
        staged_faces,
        materials,
        rebuild_faces,
        replacement_points,
        replacement_faces,
        replacement_source_ids,
        replacement_material,
    )
    collection = ensure_collection(REVIEW_COLLECTION)
    before_obj = create_object(
        f"{args.prefix}_BEFORE",
        staged_points,
        staged_faces,
        materials,
        list(staged.data.materials),
        collection,
    )
    after_obj = create_object(
        f"{args.prefix}_AFTER",
        result_points,
        result_faces,
        result_materials,
        list(staged.data.materials),
        collection,
    )
    topology = topology_record(before_obj, after_obj)
    baseline_global = len(
        overlap_pairs(staged_points, staged_faces, cutter_points, cutter_faces)
    )
    after_global = len(
        overlap_pairs(result_points, result_faces, cutter_points, cutter_faces)
    )
    source_to_result = {
        source_id: result_id
        for result_id, source_id in enumerate(retained_source_ids)
    }
    staged_component9_faces = [
        face
        for face in staged_faces
        if face[0] in component9
    ]
    result_component9_faces = [
        tuple(source_to_result[vertex] for vertex in face)
        for face in staged_component9_faces
    ]
    staged_component9_points = [
        staged_points[index] for index in sorted(component9)
    ]
    c9_local = {
        source_id: local_id
        for local_id, source_id in enumerate(sorted(component9))
    }
    baseline_c9 = len(
        overlap_pairs(
            staged_component9_points,
            [
                tuple(c9_local[vertex] for vertex in face)
                for face in staged_component9_faces
            ],
            cutter_points,
            cutter_faces,
        )
    )
    result_c9_ids = sorted(source_to_result[index] for index in component9)
    result_c9_remap = {
        result_id: local_id
        for local_id, result_id in enumerate(result_c9_ids)
    }
    after_c9 = len(
        overlap_pairs(
            [result_points[index] for index in result_c9_ids],
            [
                tuple(result_c9_remap[vertex] for vertex in face)
                for face in result_component9_faces
            ],
            cutter_points,
            cutter_faces,
        )
    )
    retained_points_before = [
        staged_points[index] for index in retained_source_ids
    ]
    retained_points_after = [
        result_points[index] for index in range(len(retained_source_ids))
    ]
    retained_fingerprint_before = fingerprint(
        retained_source_ids,
        retained_points_before,
    )
    retained_fingerprint_after = fingerprint(
        retained_source_ids,
        retained_points_after,
    )
    pair_errors = []
    for record in mapping["exact_component_9_attachment_landmarks"][
        "vertex_records"
    ]:
        c20 = record["component_20_vertex_id"]
        c9 = record["component_9_vertex_id"]
        if c20 not in source_to_result or c9 not in source_to_result:
            pair_errors.append({"missing_pair": [c20, c9]})
            continue
        before_vector = staged_points[c9] - staged_points[c20]
        after_vector = (
            result_points[source_to_result[c9]]
            - result_points[source_to_result[c20]]
        )
        error = (after_vector - before_vector).length
        if error > TOLERANCE_MM:
            pair_errors.append(
                {
                    "pair": [c20, c9],
                    "relative_vector_error_mm": round(error, 9),
                }
            )
    replacement_overlaps = overlap_pairs(
        replacement_points,
        replacement_faces,
        cutter_points,
        cutter_faces,
    )
    quality = triangle_quality(
        result_points,
        result_faces,
        tuple(replacement_range),
    )
    replacement_normals_negative = sum(
        triangle_normal(replacement_points, face).dot(normal) <= 0.0
        for face in replacement_faces
    )
    gate_pass = all(
        (
            convergence["converged"],
            not replacement_overlaps,
            after_global < baseline_global,
            after_c9 <= baseline_c9,
            not pair_errors,
            retained_fingerprint_before == retained_fingerprint_after,
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edges"] == 0,
            replacement_normals_negative == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
        )
    )
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if gate_pass
            else "evaluation_only_combined_liner_failed"
        ),
        "operation": OPERATION,
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": actual_sha,
            "staged_object": STAGED_NAME,
        },
        "mapping": {
            "path": str(MAPPING_PATH),
            "sha256": sha256_file(MAPPING_PATH),
            "removed_face_count": len(rebuild_faces),
            "retained_component_20_face_count": len(retain_c20_faces),
        },
        "boundary": {
            "complete_edge_count": len(complete_boundary),
            "mapped_seam_edge_count": len(mapped_seam),
            "source_open_edge_count": len(complete_boundary - mapped_seam),
            "cycle_count": len(cycles),
            "cycle_vertex_counts": [len(cycle) for cycle in cycles],
            "cycle_nesting_depths": cycle_depths,
        },
        "construction": {
            "coarse_triangle_count": len(coarse),
            "replacement_vertex_count": len(replacement_points),
            "new_interior_vertex_count": len(new_ids),
            "replacement_triangle_count": len(replacement_faces),
            "removed_only_exact_interface_controls": removed_only_controls,
            "initial_floor_mm": INITIAL_FLOOR_MM,
            "target_edge_mm": TARGET_EDGE_MM,
            "maximum_edge_mm": MAXIMUM_EDGE_MM,
            "replacement_material_index": replacement_material,
            "clearance_convergence": convergence,
        },
        "clearance": {
            "global_overlaps_before": baseline_global,
            "global_overlaps_after": after_global,
            "component_9_overlaps_before": baseline_c9,
            "component_9_overlaps_after": after_c9,
            "replacement_overlap_count": len(replacement_overlaps),
            "replacement_overlap_pairs": [
                list(pair) for pair in sorted(replacement_overlaps)
            ],
        },
        "preservation": {
            "retained_source_vertex_count": len(retained_source_ids),
            "retained_fingerprint_before": retained_fingerprint_before,
            "retained_fingerprint_after": retained_fingerprint_after,
            "retained_fingerprint_equal": (
                retained_fingerprint_before == retained_fingerprint_after
            ),
            "interface_pair_errors": pair_errors,
        },
        "topology": topology,
        "quality": {
            "replacement": quality,
            "replacement_triangles_against_mean_normal": (
                replacement_normals_negative
            ),
        },
        "gate_pass": gate_pass,
        "blocker": (
            None
            if gate_pass
            else (
                f"{OPERATION}: deterministic boundary tessellation failed one "
                "or more combined clearance, preservation, topology, "
                "orientation, or quality gates; inspect recorded exact fields"
            )
        ),
        "objects": {"before": before_obj.name, "after": after_obj.name},
        "images": {"generated": False, "reviewed": False},
        "qualitative_review": "PENDING" if gate_pass else "NOT_REQUESTED",
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
        f"DONE: combined inner-bowl liner gate_pass={gate_pass}; "
        f"replacement_overlaps={len(replacement_overlaps)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
