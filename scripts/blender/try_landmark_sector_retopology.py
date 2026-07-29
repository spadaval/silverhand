"""Sweep evaluation-only landmark-sector retopology candidates.

The selected disk-like face sector is removed. Its retained outer transition
chain is reused exactly, while its source-open chain is replaced at a
cutter-safe radial floor with the same boundary edge count. Intermediate open
rows taper gradually between those paths and are joined with zipper
triangulation. Current evaluated relief is transferred as residuals from a
graph-parameterized ruled surface before the final minimum-floor clamp.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import heapq
import json
from math import acos, degrees
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    distribution,
    evaluated_geometry,
    point_margins,
)
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
from try_boundary_preserving_cutter_reconstruction import (  # noqa: E402
    edge_faces,
    expand_face_rings,
    orient_path,
    orient_transition_chain,
    removed_open_boundary_edges,
    transition_edges,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    REVIEW_COLLECTION,
    clamp_to_reserved_wall,
    create_object,
    cumulative_parameters,
    ensure_collection,
    mesh_audit,
    ordered_boundary_groups,
    overlap_pairs,
    sample_polyline,
    zipper_bridge,
)


OPERATION = "LANDMARK_SECTOR_RETOPOLOGY"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
SHARP_EDGE_DEGREES = 30.0


def parse_ints(value: str, role: str) -> list[int]:
    try:
        result = sorted({int(item) for item in value.split(",")})
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"{role} contains a non-integer value: {error}"
        ) from error
    if not result or any(item < 2 for item in result):
        raise argparse.ArgumentTypeError(
            f"{role} must contain integers of at least 2"
        )
    return result


def parse_floats(value: str, role: str) -> list[float]:
    try:
        result = sorted({float(item) for item in value.split(",")})
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"{role} contains a non-number value: {error}"
        ) from error
    if not result or any(not 0.0 <= item <= 1.0 for item in result):
        raise argparse.ArgumentTypeError(
            f"{role} must contain numbers between 0 and 1"
        )
    return result


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--cluster", type=int, required=True)
    parser.add_argument("--sector-rings", default="2,3,4")
    parser.add_argument("--row-counts", default="4,6")
    parser.add_argument("--relief-scales", default="0.5,0.75,1.0")
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
    args.sector_rings = parse_ints(args.sector_rings, "--sector-rings")
    args.row_counts = parse_ints(args.row_counts, "--row-counts")
    args.relief_scales = parse_floats(
        args.relief_scales,
        "--relief-scales",
    )
    if args.component < 0 or args.cluster < 0:
        parser.error("--component and --cluster must be non-negative")
    if args.floor_offset_mm < RESERVED_WALL_MM:
        parser.error(
            f"--floor-offset-mm must be at least {RESERVED_WALL_MM} mm"
        )
    if len(args.required_base_sha256) != 64:
        parser.error("--required-base-sha256 must be a SHA-256 digest")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_base(
    candidate: bpy.types.Object,
    required_sha256: str,
    required_shape_key: str,
) -> dict:
    path = Path(bpy.data.filepath).resolve()
    actual = sha256_file(path)
    if actual != required_sha256:
        raise RuntimeError(
            f"{OPERATION}: input blend '{path}' has SHA-256 '{actual}', "
            f"expected '{required_sha256}'"
        )
    keys = candidate.data.shape_keys
    if keys is None:
        raise RuntimeError(
            f"{OPERATION}: candidate '{candidate.name}' has no shape keys"
        )
    required = keys.key_blocks.get(required_shape_key)
    if required is None or required.value < 1.0 - TOLERANCE_MM:
        actual_value = None if required is None else required.value
        raise RuntimeError(
            f"{OPERATION}: required base shape key '{required_shape_key}' "
            f"has state/value '{actual_value}', expected active at 1.0"
        )
    active = [
        key.name for key in keys.key_blocks if key.value > TOLERANCE_MM
    ]
    if not active or active[-1] != required_shape_key:
        raise RuntimeError(
            f"{OPERATION}: latest active shape key is "
            f"'{active[-1] if active else None}', expected "
            f"'{required_shape_key}'"
        )
    return {
        "blend_file": str(path),
        "blend_file_sha256": actual,
        "required_active_shape_key": required_shape_key,
    }


def graph_distances(
    seeds: set[int],
    allowed: set[int],
    neighbors: list[list[int]],
    points: list[Vector],
) -> dict[int, float]:
    distances = {index: 0.0 for index in seeds}
    queue = [(0.0, index) for index in seeds]
    heapq.heapify(queue)
    while queue:
        distance, current = heapq.heappop(queue)
        if distance > distances[current] + 1.0e-12:
            continue
        for neighbor in neighbors[current]:
            if neighbor not in allowed:
                continue
            candidate = (
                distance + (points[current] - points[neighbor]).length
            )
            if candidate >= distances.get(neighbor, float("inf")):
                continue
            distances[neighbor] = candidate
            heapq.heappush(queue, (candidate, neighbor))
    if len(distances) != len(allowed):
        missing = sorted(allowed - distances.keys())
        raise RuntimeError(
            f"{OPERATION}: sector graph distance failed for source vertices "
            f"{missing[:20]}"
        )
    return distances


def nearest_parameter(
    point: Vector,
    chain: list[int],
    parameters: list[float],
    points: list[Vector],
) -> float:
    return parameters[
        min(
            range(len(chain)),
            key=lambda offset: (point - points[chain[offset]]).length,
        )
    ]


def sector_parameterization(
    sector_vertices: set[int],
    outer: list[int],
    open_chain: list[int],
    points: list[Vector],
    neighbors: list[list[int]],
) -> dict[int, dict]:
    outer_set = set(outer)
    open_set = set(open_chain)
    distance_outer = graph_distances(
        outer_set,
        sector_vertices,
        neighbors,
        points,
    )
    distance_open = graph_distances(
        open_set,
        sector_vertices,
        neighbors,
        points,
    )
    outer_parameters = cumulative_parameters(outer, points)
    open_parameters = cumulative_parameters(open_chain, points)
    result = {}
    for index in sector_vertices:
        total = distance_outer[index] + distance_open[index]
        depth = 0.5 if total <= 1.0e-12 else distance_outer[index] / total
        outer_u = nearest_parameter(
            points[index],
            outer,
            outer_parameters,
            points,
        )
        open_u = nearest_parameter(
            points[index],
            open_chain,
            open_parameters,
            points,
        )
        longitudinal = (1.0 - depth) * outer_u + depth * open_u
        base = sample_polyline(
            outer,
            outer_parameters,
            longitudinal,
            points,
        ).lerp(
            sample_polyline(
                open_chain,
                open_parameters,
                longitudinal,
                points,
            ),
            depth,
        )
        result[index] = {
            "u": longitudinal,
            "t": depth,
            "residual": points[index] - base,
        }
    return result


def sampled_residual(
    u: float,
    t: float,
    parameterization: dict[int, dict],
) -> Vector:
    nearest = sorted(
        parameterization.values(),
        key=lambda record: (
            (record["u"] - u) ** 2 + (record["t"] - t) ** 2,
        ),
    )[:4]
    weights = [
        1.0
        / max(
            1.0e-8,
            (record["u"] - u) ** 2 + (record["t"] - t) ** 2,
        )
        for record in nearest
    ]
    return sum(
        (
            record["residual"] * weight
            for record, weight in zip(nearest, weights)
        ),
        Vector(),
    ) / sum(weights)


def tapered_counts(
    outer_count: int,
    open_count: int,
    row_count: int,
) -> list[int]:
    result = []
    for row in range(row_count):
        factor = row / (row_count - 1)
        value = round(
            outer_count + (open_count - outer_count) * factor
        )
        result.append(max(2, value))
    result[0] = outer_count
    result[-1] = open_count
    for previous, current in zip(result, result[1:]):
        if current > previous:
            raise RuntimeError(
                f"{OPERATION}: non-tapering row counts {result}"
            )
    return result


def construct_variant(
    before: list[Vector],
    faces: list[tuple[int, ...]],
    material_indices: list[int],
    sector_faces: set[int],
    outer: list[int],
    open_chain: list[int],
    parameterization: dict[int, dict],
    target_length: float,
    grid: list[list[float]],
    floor_offset_mm: float,
    row_count: int,
    relief_scale: float,
) -> dict:
    kept_records = [
        (index, face, material_indices[index])
        for index, face in enumerate(faces)
        if index not in sector_faces
    ]
    kept_vertices = sorted(
        {
            vertex
            for _, face, _ in kept_records
            for vertex in face
        }
    )
    remap = {
        source_index: result_index
        for result_index, source_index in enumerate(kept_vertices)
    }
    if not set(outer) <= remap.keys():
        missing = sorted(set(outer) - remap.keys())
        raise RuntimeError(
            f"{OPERATION}: outer boundary vertices {missing} are not reused "
            "by retained faces"
        )
    result_points = [before[index].copy() for index in kept_vertices]
    reference_points = [point.copy() for point in result_points]
    result_faces = [
        tuple(remap[index] for index in face)
        for _, face, _ in kept_records
    ]
    result_materials = [material for _, _, material in kept_records]
    retained_face_count = len(result_faces)

    outer_parameters = cumulative_parameters(outer, before)
    projected_open = [
        clamp_to_reserved_wall(
            before[index],
            target_length,
            grid,
            floor_offset_mm,
        )
        for index in open_chain
    ]
    temporary_points = [point.copy() for point in result_points]
    projected_open_indices = []
    for point in projected_open:
        projected_open_indices.append(len(temporary_points))
        temporary_points.append(point)
    open_parameters = cumulative_parameters(
        projected_open_indices,
        temporary_points,
    )

    counts = tapered_counts(len(outer), len(open_chain), row_count)
    rows: list[list[int]] = [[remap[index] for index in outer]]
    added_residuals = []
    for row_index in range(1, row_count):
        depth = row_index / (row_count - 1)
        count = counts[row_index]
        row = []
        for offset in range(count):
            u = offset / (count - 1)
            if offset == 0:
                row.append(remap[outer[0]])
                continue
            if offset == count - 1:
                row.append(remap[outer[-1]])
                continue
            outer_point = sample_polyline(
                [remap[index] for index in outer],
                outer_parameters,
                u,
                result_points,
            )
            open_point = sample_polyline(
                projected_open_indices,
                open_parameters,
                u,
                temporary_points,
            )
            base = outer_point.lerp(open_point, depth)
            residual = sampled_residual(u, depth, parameterization)
            reference_point = clamp_to_reserved_wall(
                base,
                target_length,
                grid,
                floor_offset_mm,
            )
            point = base + residual * relief_scale
            point = clamp_to_reserved_wall(
                point,
                target_length,
                grid,
                floor_offset_mm,
            )
            row.append(len(result_points))
            result_points.append(point)
            reference_points.append(reference_point)
            added_residuals.append((residual * relief_scale).length)
        rows.append(row)

    replacement_faces = []
    for first, second in zip(rows, rows[1:]):
        for face in zipper_bridge(first, second, result_points):
            if len(set(face)) < 3:
                continue
            a, b, c = (result_points[index] for index in face)
            if (b - a).cross(c - a).length <= 1.0e-8:
                continue
            replacement_faces.append(face)
    if not replacement_faces:
        raise RuntimeError(
            f"{OPERATION}: row-count {row_count} generated no replacement "
            "triangles"
        )
    replacement_material = Counter(
        material_indices[index] for index in sector_faces
    ).most_common(1)[0][0]
    result_faces.extend(replacement_faces)
    result_materials.extend(
        [replacement_material] * len(replacement_faces)
    )
    return {
        "points": result_points,
        "reference_points": reference_points,
        "faces": result_faces,
        "materials": result_materials,
        "retained_source_vertex_ids": kept_vertices,
        "retained_face_ids": [index for index, _, _ in kept_records],
        "replacement_face_range": [
            retained_face_count,
            len(result_faces),
        ],
        "row_vertex_counts": counts,
        "rows": rows,
        "transferred_relief_mm": (
            distribution(added_residuals) if added_residuals else None
        ),
    }


def geometry_fingerprint(
    source_ids: list[int],
    points: list[Vector],
) -> str:
    digest = hashlib.sha256()
    for source_id, point in zip(source_ids, points):
        digest.update(struct.pack("<Qddd", source_id, *point))
    return digest.hexdigest()


def audit_noncontiguous(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        manifold = [edge for edge in bm.edges if edge.is_manifold]
        return {
            "manifold_edges": len(manifold),
            "noncontiguous_manifold_edges": sum(
                not edge.is_contiguous for edge in manifold
            ),
        }
    finally:
        bm.free()


def triangle_quality(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    face_range: tuple[int, int],
) -> dict:
    areas = []
    aspect_ratios = []
    minimum_angles = []
    edges = set()
    for face in faces[face_range[0] : face_range[1]]:
        if len(face) != 3:
            continue
        edges.update(
            tuple(sorted((first, second)))
            for first, second in zip(face, face[1:] + face[:1])
        )
        a, b, c = (points[index] for index in face)
        lengths = [(a - b).length, (b - c).length, (c - a).length]
        cross = (b - a).cross(c - a)
        area = cross.length * 0.5
        if area <= 1.0e-12 or min(lengths) <= 1.0e-12:
            continue
        areas.append(area)
        aspect_ratios.append(max(lengths) / min(lengths))
        angles = []
        for first, second, opposite in (
            (lengths[0], lengths[2], lengths[1]),
            (lengths[0], lengths[1], lengths[2]),
            (lengths[1], lengths[2], lengths[0]),
        ):
            cosine = (
                first * first + second * second - opposite * opposite
            ) / (2.0 * first * second)
            angles.append(
                degrees(acos(max(-1.0, min(1.0, cosine))))
            )
        minimum_angles.append(min(angles))
    return {
        "triangle_count": len(areas),
        "edge_length_mm": distribution(
            [(points[first] - points[second]).length for first, second in edges]
        ),
        "area_mm2": distribution(areas) if areas else None,
        "aspect_ratio": (
            distribution(aspect_ratios) if aspect_ratios else None
        ),
        "minimum_angle_degrees": (
            distribution(minimum_angles) if minimum_angles else None
        ),
    }


def face_normal(points: list[Vector], face: tuple[int, ...]) -> Vector:
    if len(face) < 3:
        return Vector()
    normal = Vector()
    for offset in range(1, len(face) - 1):
        normal += (points[face[offset]] - points[face[0]]).cross(
            points[face[offset + 1]] - points[face[0]]
        )
    return normal.normalized() if normal.length > 1.0e-12 else normal


def replacement_orientation_locators(
    reference: list[Vector],
    after: list[Vector],
    after_faces: list[tuple[int, ...]],
    face_range: tuple[int, int],
) -> dict:
    locators = []
    for face_index in range(*face_range):
        face = after_faces[face_index]
        reference_normal = face_normal(reference, face)
        current_normal = face_normal(after, face)
        if (
            reference_normal.length <= 1.0e-12
            or current_normal.length <= 1.0e-12
        ):
            continue
        dot = reference_normal.dot(current_normal)
        if dot < 0.0:
            locators.append(
                {
                    "replacement_face": face_index,
                    "reference": "same triangle on zero-relief ruled sector",
                    "normal_dot": round(dot, 6),
                }
            )
    return {"count": len(locators), "locators": locators}


def sharp_edge_count(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    face_ids: set[int],
) -> int:
    linked = edge_faces(faces)
    normals = [face_normal(points, face) for face in faces]
    result = 0
    for edge, adjacent in linked.items():
        if len(adjacent) != 2 or not any(index in face_ids for index in adjacent):
            continue
        first, second = (normals[index] for index in adjacent)
        if first.length <= 1.0e-12 or second.length <= 1.0e-12:
            continue
        angle = degrees(
            acos(max(-1.0, min(1.0, first.dot(second))))
        )
        if angle >= SHARP_EDGE_DEGREES:
            result += 1
    return result


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
    vertex_component, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"{OPERATION}: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )
    component = set(components[args.component])
    before, faces, material_indices = evaluated_geometry(candidate)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    clusters = violation_clusters(component, before_margins, neighbors)
    if not 0 <= args.cluster < len(clusters):
        raise RuntimeError(
            f"{OPERATION}: cluster {args.cluster} is outside "
            f"0..{len(clusters) - 1}"
        )
    cluster = clusters[args.cluster]
    linked_faces = edge_faces(faces)
    component_faces = {
        index
        for index, face in enumerate(faces)
        if vertex_component[face[0]] == args.component
    }
    core_faces = {
        index
        for index in component_faces
        if any(vertex in cluster for vertex in faces[index])
    }
    before_overlaps = overlap_pairs(
        before,
        faces,
        cutter_points,
        cutter_faces,
    )
    before_audit_obj = None
    variants = []
    geometries = {}
    sector_records = {}
    for rings in args.sector_rings:
        sector_faces = expand_face_rings(
            core_faces,
            component_faces,
            linked_faces,
            rings,
        )
        transition_groups = ordered_boundary_groups(
            transition_edges(sector_faces, linked_faces)
        )
        open_groups = ordered_boundary_groups(
            removed_open_boundary_edges(sector_faces, linked_faces)
        )
        if (
            len(transition_groups) != 1
            or transition_groups[0][1]
            or len(open_groups) != 1
            or open_groups[0][1]
        ):
            raise RuntimeError(
                f"{OPERATION}: ring-{rings} sector requires one open outer "
                "chain and one open source-boundary chain, got transition "
                f"{[(len(v), c) for v, c in transition_groups]} and open "
                f"{[(len(v), c) for v, c in open_groups]}"
            )
        outer = orient_transition_chain(
            transition_groups[0][0],
            sector_faces,
            faces,
            linked_faces,
        )
        open_chain = orient_path(
            open_groups[0][0],
            outer[0],
            outer[-1],
            f"ring-{rings} source-open chain",
        )
        sector_vertices = {
            vertex
            for face_index in sector_faces
            for vertex in faces[face_index]
        }
        parameterization = sector_parameterization(
            sector_vertices,
            outer,
            open_chain,
            before,
            neighbors,
        )
        sector_records[rings] = {
            "face_ids": sector_faces,
            "vertex_ids": sector_vertices,
            "outer": outer,
            "open": open_chain,
            "parameterization": parameterization,
        }
        before_region_overlaps = sum(
            first in sector_faces for first, _ in before_overlaps
        )
        source_sharp = sharp_edge_count(
            before,
            faces,
            sector_faces,
        )
        for row_count in args.row_counts:
            for relief_scale in args.relief_scales:
                geometry = construct_variant(
                    before,
                    faces,
                    material_indices,
                    sector_faces,
                    outer,
                    open_chain,
                    parameterization,
                    target_length,
                    grid,
                    args.floor_offset_mm,
                    row_count,
                    relief_scale,
                )
                after = geometry["points"]
                after_faces = geometry["faces"]
                margins = point_margins(after, target_length, grid)
                overlaps = overlap_pairs(
                    after,
                    after_faces,
                    cutter_points,
                    cutter_faces,
                )
                face_range = tuple(geometry["replacement_face_range"])
                replacement_overlaps = sum(
                    face_range[0] <= first < face_range[1]
                    for first, _ in overlaps
                )
                before_fp = geometry_fingerprint(
                    geometry["retained_source_vertex_ids"],
                    [
                        before[index]
                        for index in geometry["retained_source_vertex_ids"]
                    ],
                )
                after_fp = geometry_fingerprint(
                    geometry["retained_source_vertex_ids"],
                    after[: len(geometry["retained_source_vertex_ids"])],
                )
                record = {
                    "sector_rings": rings,
                    "row_count": row_count,
                    "row_vertex_counts": geometry["row_vertex_counts"],
                    "relief_scale": relief_scale,
                    "vertices": len(after),
                    "faces": len(after_faces),
                    "replacement_faces": face_range[1] - face_range[0],
                    "clearance": {
                        "global_vertices_below_cutter": sum(
                            margin < -TOLERANCE_MM for margin in margins
                        ),
                        "global_vertices_below_reserved_margin": sum(
                            margin
                            < RESERVED_WALL_MM - TOLERANCE_MM
                            for margin in margins
                        ),
                        "cluster_reserved_failures": sum(
                            before_margins[index]
                            < RESERVED_WALL_MM - TOLERANCE_MM
                            for index in cluster
                            if index
                            in geometry["retained_source_vertex_ids"]
                        ),
                        "replacement_vertices_below_reserved_margin": sum(
                            margins[index]
                            < RESERVED_WALL_MM - TOLERANCE_MM
                            for index in range(
                                len(
                                    geometry[
                                        "retained_source_vertex_ids"
                                    ]
                                ),
                                len(after),
                            )
                        ),
                        "global_triangle_overlaps": len(overlaps),
                        "before_replacement_region_overlaps": (
                            before_region_overlaps
                        ),
                        "replacement_region_overlaps": replacement_overlaps,
                    },
                    "orientation": replacement_orientation_locators(
                        geometry["reference_points"],
                        after,
                        after_faces,
                        face_range,
                    ),
                    "triangle_quality": triangle_quality(
                        after,
                        after_faces,
                        face_range,
                    ),
                    "relief": {
                        "transferred_residual_mm": geometry[
                            "transferred_relief_mm"
                        ],
                        "source_sharp_edges": source_sharp,
                        "replacement_sharp_edges": sharp_edge_count(
                            after,
                            after_faces,
                            set(range(*face_range)),
                        ),
                    },
                    "unchanged_outside_fingerprint": {
                        "before": before_fp,
                        "after": after_fp,
                        "equal": before_fp == after_fp,
                    },
                }
                key = (rings, row_count, relief_scale)
                geometries[key] = geometry
                variants.append(record)

    # Full topology gates require temporary objects. Audit every variant and
    # retain the objects only for the selected diagnostic.
    collection = ensure_collection(REVIEW_COLLECTION)
    before_audit_obj = create_object(
        f"{args.prefix}_AUDIT_BEFORE",
        before,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    before_audit = mesh_audit(before_audit_obj)
    before_winding = audit_noncontiguous(before_audit_obj)
    bpy.data.objects.remove(before_audit_obj, do_unlink=True)
    for record in variants:
        key = (
            record["sector_rings"],
            record["row_count"],
            record["relief_scale"],
        )
        geometry = geometries[key]
        audit_obj = create_object(
            f"{args.prefix}_AUDIT_{key[0]}_{key[1]}_"
            f"{str(key[2]).replace('.', '_')}",
            geometry["points"],
            geometry["faces"],
            geometry["materials"],
            list(candidate.data.materials),
            collection,
        )
        after_audit = mesh_audit(audit_obj)
        after_winding = audit_noncontiguous(audit_obj)
        record["topology"] = {
            "connected_component_delta": (
                after_audit["connected_components"]
                - before_audit["connected_components"]
            ),
            "boundary_edge_delta": (
                after_audit["boundary_edges"]
                - before_audit["boundary_edges"]
            ),
            "nonmanifold_edge_delta": (
                after_audit["nonmanifold_edges"]
                - before_audit["nonmanifold_edges"]
            ),
            "noncontiguous_manifold_edge_delta": (
                after_winding["noncontiguous_manifold_edges"]
                - before_winding["noncontiguous_manifold_edges"]
            ),
            "before": before_audit,
            "after": after_audit,
        }
        record["gate_pass"] = all(
            (
                record["topology"]["connected_component_delta"] == 0,
                record["topology"]["boundary_edge_delta"] == 0,
                record["topology"]["nonmanifold_edge_delta"] == 0,
                record["topology"][
                    "noncontiguous_manifold_edge_delta"
                ]
                == 0,
                record["orientation"]["count"] == 0,
                record["clearance"]["cluster_reserved_failures"] == 0,
                record["clearance"][
                    "replacement_vertices_below_reserved_margin"
                ]
                == 0,
                record["clearance"]["replacement_region_overlaps"]
                <= record["clearance"][
                    "before_replacement_region_overlaps"
                ],
                record["unchanged_outside_fingerprint"]["equal"],
            )
        )
        bpy.data.objects.remove(audit_obj, do_unlink=True)

    viable = [record for record in variants if record["gate_pass"]]
    ranked = viable if viable else variants
    selected = min(
        ranked,
        key=lambda record: (
            not record["gate_pass"],
            record["topology"]["connected_component_delta"] != 0,
            record["topology"]["boundary_edge_delta"] != 0,
            record["topology"]["nonmanifold_edge_delta"] != 0,
            record["topology"]["noncontiguous_manifold_edge_delta"] != 0,
            record["orientation"]["count"],
            record["clearance"]["cluster_reserved_failures"],
            max(
                0,
                record["clearance"]["replacement_region_overlaps"]
                - record["clearance"][
                    "before_replacement_region_overlaps"
                ],
            ),
            record["triangle_quality"]["aspect_ratio"]["maximum"],
        ),
    )
    selected_key = (
        selected["sector_rings"],
        selected["row_count"],
        selected["relief_scale"],
    )
    selected_geometry = geometries[selected_key]
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
        selected_geometry["points"],
        selected_geometry["faces"],
        selected_geometry["materials"],
        list(candidate.data.materials),
        collection,
    )
    before_obj["role"] = "landmark sector retopology before"
    after_obj["role"] = "landmark sector retopology after"
    sector = sector_records[selected["sector_rings"]]
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if viable
            else "evaluation_only_no_gate_passing_variant"
        ),
        "units": "millimeters",
        "repair_base": repair_base,
        "selection": {
            "component": args.component,
            "cluster": args.cluster,
            "cluster_vertex_ids": cluster,
            "sector_rings": selected["sector_rings"],
            "removed_face_ids": sorted(sector["face_ids"]),
            "removed_vertex_ids": sorted(sector["vertex_ids"]),
            "outer_transition_vertex_ids_ordered": sector["outer"],
            "source_open_vertex_ids_ordered": sector["open"],
            "outer_transition_edge_count": len(sector["outer"]) - 1,
            "source_open_edge_count": len(sector["open"]) - 1,
            "replacement_open_edge_count": len(sector["open"]) - 1,
            "row_count": selected["row_count"],
            "row_vertex_counts": selected["row_vertex_counts"],
            "relief_scale": selected["relief_scale"],
            "floor_offset_mm": args.floor_offset_mm,
        },
        "method": {
            "outer_boundary": "reused exactly",
            "open_boundary": (
                "same edge count, replaced at 1.7 mm minimum cutter floor"
            ),
            "intermediate_topology": "gradually tapered zipper rows",
            "relief": (
                "current evaluated graph-parameterized ruled-base residual"
            ),
            "cutter_role": "minimum floor only",
        },
        "baseline": {
            "vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in before_margins
            ),
            "vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in before_margins
            ),
            "triangle_overlaps": len(before_overlaps),
        },
        "variants": variants,
        "selected_variant": selected,
        "numerical_result": {
            "viable_variant_count": len(viable),
            "blocker": (
                None
                if viable
                else (
                    f"{OPERATION}: no swept sector/row/relief variant "
                    "satisfied all topology, winding, clearance, orientation, "
                    "overlap, and unchanged-outside gates"
                )
            ),
        },
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
        f"DONE: evaluated {len(variants)} landmark-sector retopology "
        f"variants; gate-passing variants={len(viable)}; promotion remains "
        "PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
