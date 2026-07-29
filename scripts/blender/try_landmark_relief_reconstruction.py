"""Sweep bounded differential-coordinate relief reconstructions.

This evaluation-only tool reconstructs one clearance-failure sector without
editing the fitted-surface candidate.  It preserves the current sector
Laplacian coordinates, fixes the explicit outer transition boundary, and adds
soft cutter-floor constraints only at the selected violating vertices.
Outside the selected face-ring sector, every coordinate remains bit-for-bit
unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import acos, degrees, sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    distribution,
    edge_ratio_distribution,
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
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
    negative_orientation_locators,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    violation_clusters,
)
from try_boundary_preserving_cutter_reconstruction import (  # noqa: E402
    edge_faces,
    expand_face_rings,
    orientation_audit,
    transition_edges,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    REVIEW_COLLECTION,
    clamp_to_reserved_wall,
    create_object,
    ensure_collection,
    mesh_audit,
    overlap_pairs,
)


OPERATION = "LANDMARK_RELIEF_RECONSTRUCTION"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
SHARP_EDGE_DEGREES = 30.0


def parse_csv_ints(value: str, role: str) -> list[int]:
    try:
        result = sorted({int(item) for item in value.split(",")})
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"{role} contains a non-integer value: {error}"
        ) from error
    if not result or any(item <= 0 for item in result):
        raise argparse.ArgumentTypeError(
            f"{role} must contain positive integers"
        )
    return result


def parse_csv_floats(value: str, role: str) -> list[float]:
    try:
        result = sorted({float(item) for item in value.split(",")})
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"{role} contains a non-number value: {error}"
        ) from error
    if not result or any(item <= 0.0 for item in result):
        raise argparse.ArgumentTypeError(
            f"{role} must contain positive numbers"
        )
    return result


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--cluster", type=int, required=True)
    parser.add_argument("--sector-rings", default="2,3,4")
    parser.add_argument("--constraint-weights", default="10,100,1000")
    parser.add_argument(
        "--floor-offset-mm",
        type=float,
        default=RESERVED_WALL_MM + 0.10,
    )
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
    args.sector_rings = parse_csv_ints(
        args.sector_rings,
        "--sector-rings",
    )
    args.constraint_weights = parse_csv_floats(
        args.constraint_weights,
        "--constraint-weights",
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
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise RuntimeError(
            f"{OPERATION}: cannot fingerprint blend file '{path}': {error}"
        ) from error
    return digest.hexdigest()


def validate_base(
    candidate: bpy.types.Object,
    required_sha256: str,
    required_shape_key: str,
) -> dict:
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha256 = sha256_file(blend_path)
    if actual_sha256 != required_sha256:
        raise RuntimeError(
            f"{OPERATION}: input blend '{blend_path}' has SHA-256 "
            f"'{actual_sha256}', expected exact Repair 013 base "
            f"'{required_sha256}'"
        )
    shape_keys = candidate.data.shape_keys
    if shape_keys is None:
        raise RuntimeError(
            f"{OPERATION}: candidate '{candidate.name}' has no shape keys"
        )
    required = shape_keys.key_blocks.get(required_shape_key)
    if required is None:
        raise RuntimeError(
            f"{OPERATION}: required base shape key '{required_shape_key}' "
            f"is missing from '{candidate.name}'"
        )
    if required.value < 1.0 - TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: required base shape key '{required_shape_key}' "
            f"has value {required.value}, expected 1.0"
        )
    active = [
        key.name
        for key in shape_keys.key_blocks
        if key.value > TOLERANCE_MM
    ]
    if active[-1] != required_shape_key:
        raise RuntimeError(
            f"{OPERATION}: latest active shape key is '{active[-1]}', "
            f"expected '{required_shape_key}'"
        )
    return {
        "blend_file": str(blend_path),
        "blend_file_sha256": actual_sha256,
        "required_active_shape_key": required_shape_key,
        "active_shape_keys": active,
    }


def face_normal(points: list[Vector], face: tuple[int, ...]) -> Vector:
    normal = Vector()
    for offset, first in enumerate(face):
        second = face[(offset + 1) % len(face)]
        a = points[first]
        b = points[second]
        normal.x += (a.y - b.y) * (a.z + b.z)
        normal.y += (a.z - b.z) * (a.x + b.x)
        normal.z += (a.x - b.x) * (a.y + b.y)
    return normal.normalized() if normal.length > 1.0e-12 else normal


def dihedral(
    normals: list[Vector],
    linked: list[int],
) -> float | None:
    if len(linked) != 2:
        return None
    first = normals[linked[0]]
    second = normals[linked[1]]
    if first.length <= 1.0e-12 or second.length <= 1.0e-12:
        return None
    return degrees(acos(max(-1.0, min(1.0, first.dot(second)))))


def relief_metrics(
    before: list[Vector],
    after: list[Vector],
    faces: list[tuple[int, ...]],
    linked_faces: dict[tuple[int, int], list[int]],
    sector_edges: set[tuple[int, int]],
    free_vertices: set[int],
    neighbors: list[list[int]],
) -> dict:
    before_normals = [face_normal(before, face) for face in faces]
    after_normals = [face_normal(after, face) for face in faces]
    sharp_changes = []
    retained_sharp = 0
    sharp_count = 0
    for edge in sector_edges:
        before_angle = dihedral(before_normals, linked_faces[edge])
        after_angle = dihedral(after_normals, linked_faces[edge])
        if before_angle is None or after_angle is None:
            continue
        if before_angle >= SHARP_EDGE_DEGREES:
            sharp_count += 1
            sharp_changes.append(abs(after_angle - before_angle))
            if after_angle >= SHARP_EDGE_DEGREES:
                retained_sharp += 1

    laplacian_residuals = []
    for index in free_vertices:
        local = neighbors[index]
        if not local:
            continue
        before_delta = before[index] - sum(
            (before[neighbor] for neighbor in local),
            Vector(),
        ) / len(local)
        after_delta = after[index] - sum(
            (after[neighbor] for neighbor in local),
            Vector(),
        ) / len(local)
        laplacian_residuals.append((after_delta - before_delta).length)
    return {
        "sharp_edge_threshold_degrees": SHARP_EDGE_DEGREES,
        "source_sharp_edges": sharp_count,
        "retained_sharp_edges": retained_sharp,
        "retained_sharp_fraction": (
            round(retained_sharp / sharp_count, 6)
            if sharp_count
            else None
        ),
        "sharp_edge_dihedral_change_degrees": (
            distribution(sharp_changes) if sharp_changes else None
        ),
        "laplacian_coordinate_residual_mm": (
            distribution(laplacian_residuals)
            if laplacian_residuals
            else None
        ),
    }


def solve_variant(
    before: list[Vector],
    free_vertices: set[int],
    boundary_vertices: set[int],
    sector_vertices: set[int],
    constrained_targets: dict[int, Vector],
    neighbors: list[list[int]],
    weight: float,
) -> list[Vector]:
    if constrained_targets.keys() & boundary_vertices:
        conflict = sorted(constrained_targets.keys() & boundary_vertices)
        raise RuntimeError(
            f"{OPERATION}: cutter constraints intersect fixed boundary at "
            f"source vertices {conflict}"
        )
    ordered_free = sorted(free_vertices)
    columns = {vertex: offset for offset, vertex in enumerate(ordered_free)}
    rows: list[np.ndarray] = []
    rhs: list[list[float]] = []
    for index in ordered_free:
        local = neighbors[index]
        if not local:
            raise RuntimeError(
                f"{OPERATION}: free source vertex {index} has no neighbors"
            )
        row = np.zeros(len(ordered_free), dtype=np.float64)
        row[columns[index]] = 1.0
        reciprocal = 1.0 / len(local)
        fixed_sum = Vector()
        for neighbor in local:
            if neighbor in columns:
                row[columns[neighbor]] -= reciprocal
            else:
                fixed_sum += before[neighbor] * reciprocal
        delta = before[index] - sum(
            (before[neighbor] for neighbor in local),
            Vector(),
        ) * reciprocal
        target_rhs = delta + fixed_sum
        rows.append(row)
        rhs.append(list(target_rhs))

    target_scale = sqrt(weight)
    for index, target in sorted(constrained_targets.items()):
        if index not in columns:
            raise RuntimeError(
                f"{OPERATION}: constrained source vertex {index} is outside "
                "the free reconstruction region"
            )
        row = np.zeros(len(ordered_free), dtype=np.float64)
        row[columns[index]] = target_scale
        rows.append(row)
        rhs.append([value * target_scale for value in target])

    matrix = np.vstack(rows)
    values = np.asarray(rhs, dtype=np.float64)
    solution, _, rank, _ = np.linalg.lstsq(matrix, values, rcond=None)
    if rank < len(ordered_free):
        raise RuntimeError(
            f"{OPERATION}: differential solve rank {rank} is below "
            f"{len(ordered_free)} free vertices"
        )
    after = [point.copy() for point in before]
    for index, row in columns.items():
        after[index] = Vector(solution[row])

    outside = set(range(len(before))) - sector_vertices
    changed_outside = [
        index for index in outside if after[index] != before[index]
    ]
    changed_boundary = [
        index
        for index in boundary_vertices
        if after[index] != before[index]
    ]
    if changed_outside or changed_boundary:
        raise RuntimeError(
            f"{OPERATION}: exact preservation failed; changed outside "
            f"vertices={changed_outside[:10]}, changed boundary "
            f"vertices={changed_boundary[:10]}"
        )
    return after


def sector_definition(
    component_faces: set[int],
    core_faces: set[int],
    linked_faces: dict[tuple[int, int], list[int]],
    rings: int,
    faces: list[tuple[int, ...]],
) -> dict:
    sector_faces = expand_face_rings(
        core_faces,
        component_faces,
        linked_faces,
        rings,
    )
    boundary_edges = set(transition_edges(sector_faces, linked_faces))
    boundary_vertices = {
        index for edge in boundary_edges for index in edge
    }
    sector_vertices = {
        index
        for face_index in sector_faces
        for index in faces[face_index]
    }
    free_vertices = sector_vertices - boundary_vertices
    if not boundary_edges:
        raise RuntimeError(
            f"{OPERATION}: ring-{rings} sector has no outer transition "
            "boundary"
        )
    if not free_vertices:
        raise RuntimeError(
            f"{OPERATION}: ring-{rings} sector has no free vertices"
        )
    return {
        "rings": rings,
        "face_ids": sector_faces,
        "vertex_ids": sector_vertices,
        "boundary_edge_ids": boundary_edges,
        "boundary_vertex_ids": boundary_vertices,
        "free_vertex_ids": free_vertices,
    }


def candidate_metrics(
    before: list[Vector],
    after: list[Vector],
    faces: list[tuple[int, ...]],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
    margins: list[float],
    component: set[int],
    cluster: list[int],
    sector: dict,
    source: bpy.types.Object,
    neighbors: list[list[int]],
    linked_faces: dict[tuple[int, int], list[int]],
    before_overlaps: list[tuple[int, int]],
) -> dict:
    affected = {
        index
        for index in sector["free_vertex_ids"]
        if (after[index] - before[index]).length > TOLERANCE_MM
    }
    displacements = [
        (after[index] - before[index]).length for index in affected
    ]
    overlaps = overlap_pairs(
        after,
        faces,
        cutter_points,
        cutter_faces,
    )
    sector_faces = sector["face_ids"]
    sector_edges = {
        tuple(sorted((first, second)))
        for face_index in sector_faces
        for first, second in zip(
            faces[face_index],
            faces[face_index][1:] + faces[face_index][:1],
        )
    }
    return {
        "affected_vertex_count": len(affected),
        "changed_vertex_ids": sorted(affected),
        "changed_face_count": sum(
            any(index in affected for index in faces[face_index])
            for face_index in sector_faces
        ),
        "displacement_mm": (
            distribution(displacements) if displacements else None
        ),
        "clearance": {
            "global_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in margins
            ),
            "global_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in margins
            ),
            "component_vertices_below_cutter": sum(
                margins[index] < -TOLERANCE_MM for index in component
            ),
            "component_vertices_below_reserved_margin": sum(
                margins[index] < RESERVED_WALL_MM - TOLERANCE_MM
                for index in component
            ),
            "cluster_vertices_below_cutter": sum(
                margins[index] < -TOLERANCE_MM for index in cluster
            ),
            "cluster_vertices_below_reserved_margin": sum(
                margins[index] < RESERVED_WALL_MM - TOLERANCE_MM
                for index in cluster
            ),
            "cluster_minimum_margin_mm": round(
                min(margins[index] for index in cluster),
                6,
            ),
            "global_triangle_overlaps": len(overlaps),
            "before_replacement_region_triangle_overlaps": sum(
                first in sector_faces for first, _ in before_overlaps
            ),
            "replacement_region_triangle_overlaps": sum(
                first in sector_faces for first, _ in overlaps
            ),
            "replacement_region_overlap_face_ids": sorted(
                {first for first, _ in overlaps if first in sector_faces}
            ),
        },
        "distortion": {
            "negative_orientation": negative_orientation_locators(
                source,
                before,
                after,
                faces,
            ),
            "affected_edge_ratio": edge_ratio_distribution(
                before,
                after,
                [tuple(edge.vertices) for edge in source.data.edges],
                affected,
            ),
            "relief_preservation": relief_metrics(
                before,
                after,
                faces,
                linked_faces,
                sector_edges,
                sector["free_vertex_ids"],
                neighbors,
            ),
        },
    }


def topology_record(
    before_obj: bpy.types.Object,
    after_obj: bpy.types.Object,
) -> dict:
    before = mesh_audit(before_obj)
    after = mesh_audit(after_obj)
    before_orientation = orientation_audit(before_obj)
    after_orientation = orientation_audit(after_obj)
    return {
        "before": before,
        "after": after,
        "deltas": {
            "connected_components": (
                after["connected_components"] - before["connected_components"]
            ),
            "boundary_edges": (
                after["boundary_edges"] - before["boundary_edges"]
            ),
            "nonmanifold_edges": (
                after["nonmanifold_edges"] - before["nonmanifold_edges"]
            ),
            "noncontiguous_manifold_edges": (
                after_orientation["noncontiguous_manifold_edges"]
                - before_orientation["noncontiguous_manifold_edges"]
            ),
        },
        "orientation": {
            "before": before_orientation,
            "after": after_orientation,
        },
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
            f"0..{len(clusters) - 1} for component {args.component}"
        )
    cluster = clusters[args.cluster]
    linked_faces = edge_faces(faces)
    component_faces = {
        face_index
        for face_index, face in enumerate(faces)
        if vertex_component[face[0]] == args.component
    }
    core_faces = {
        face_index
        for face_index in component_faces
        if any(index in cluster for index in faces[face_index])
    }
    constrained_targets = {
        index: clamp_to_reserved_wall(
            before[index],
            target_length,
            grid,
            args.floor_offset_mm,
        )
        for index in cluster
    }

    before_overlaps = overlap_pairs(
        before,
        faces,
        cutter_points,
        cutter_faces,
    )
    variants = []
    variant_geometry: dict[tuple[int, float], list[Vector]] = {}
    for rings in args.sector_rings:
        sector = sector_definition(
            component_faces,
            core_faces,
            linked_faces,
            rings,
            faces,
        )
        for weight in args.constraint_weights:
            after = solve_variant(
                before,
                sector["free_vertex_ids"],
                sector["boundary_vertex_ids"],
                sector["vertex_ids"],
                constrained_targets,
                neighbors,
                weight,
            )
            margins = point_margins(after, target_length, grid)
            metrics = candidate_metrics(
                before,
                after,
                faces,
                cutter_points,
                cutter_faces,
                margins,
                component,
                cluster,
                sector,
                source,
                neighbors,
                linked_faces,
                before_overlaps,
            )
            record = {
                "sector_rings": rings,
                "constraint_weight": weight,
                "sector_face_count": len(sector["face_ids"]),
                "sector_vertex_count": len(sector["vertex_ids"]),
                "outer_boundary_edge_count": len(
                    sector["boundary_edge_ids"]
                ),
                "fixed_boundary_vertex_count": len(
                    sector["boundary_vertex_ids"]
                ),
                **metrics,
            }
            variants.append(record)
            variant_geometry[(rings, weight)] = after

    viable = [
        record
        for record in variants
        if (
            record["distortion"]["negative_orientation"]["count"] == 0
            and record["clearance"][
                "cluster_vertices_below_reserved_margin"
            ]
            == 0
        )
    ]
    ranked = viable if viable else variants
    selected = min(
        ranked,
        key=lambda record: (
            record["clearance"]["cluster_vertices_below_reserved_margin"],
            record["distortion"]["negative_orientation"]["count"],
            record["clearance"]["replacement_region_triangle_overlaps"],
            max(
                record["distortion"]["affected_edge_ratio"]["maximum"],
                1.0
                / record["distortion"]["affected_edge_ratio"]["minimum"],
            ),
            record["sector_vertex_count"],
            record["constraint_weight"],
        ),
    )
    selected_key = (
        selected["sector_rings"],
        selected["constraint_weight"],
    )
    selected_after = variant_geometry[selected_key]
    selected_sector = sector_definition(
        component_faces,
        core_faces,
        linked_faces,
        selected["sector_rings"],
        faces,
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
        selected_after,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    before_obj["role"] = "landmark relief reconstruction before"
    after_obj["role"] = "landmark relief reconstruction after"
    topology = topology_record(before_obj, after_obj)

    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if viable
            else "evaluation_only_no_orientation_safe_variant"
        ),
        "units": "millimeters",
        "repair_base": repair_base,
        "selection": {
            "component": args.component,
            "cluster": args.cluster,
            "cluster_vertex_ids": cluster,
            "cluster_vertex_count": len(cluster),
            "core_face_ids": sorted(core_faces),
            "core_face_count": len(core_faces),
            "sector_rings": selected["sector_rings"],
            "sector_face_ids": sorted(selected_sector["face_ids"]),
            "sector_vertex_ids": sorted(selected_sector["vertex_ids"]),
            "fixed_outer_boundary_edge_vertex_ids": [
                list(edge)
                for edge in sorted(selected_sector["boundary_edge_ids"])
            ],
            "fixed_outer_boundary_vertex_ids": sorted(
                selected_sector["boundary_vertex_ids"]
            ),
            "free_vertex_ids": sorted(selected_sector["free_vertex_ids"]),
            "constraint_weight": selected["constraint_weight"],
            "floor_offset_mm": args.floor_offset_mm,
        },
        "method": {
            "coordinates": "current evaluated differential coordinates",
            "boundary": "fixed exact outer transition",
            "cutter_role": "minimum reserved-wall floor only",
            "topology_changed": False,
            "outside_sector_changed_vertices": 0,
            "fixed_boundary_changed_vertices": 0,
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
                    f"{OPERATION}: every swept ring/weight variant either "
                    "retains reserved-margin failures or introduces negative "
                    "orientation locators; do not begin image review"
                )
            ),
        },
        "topology": topology,
        "objects": {
            "before": before_obj.name,
            "after": after_obj.name,
        },
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
        f"DONE: selected ring-{selected['sector_rings']} weight-"
        f"{selected['constraint_weight']:g} evaluation for component "
        f"{args.component} cluster {args.cluster}; promotion remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
