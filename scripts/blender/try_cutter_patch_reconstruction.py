"""Create a disposable bounded wearer-facing cutter-patch reconstruction.

The trial removes only faces touching selected clearance-failure clusters or
their exact cutter overlaps, then adds a local inward-facing surface sampled
from the clearance cutter plus the reserved wall. It creates evaluation
objects and never replaces the active fitted-surface candidate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from math import atan2, pi
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    evaluated_geometry,
    point_margins,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    RESERVED_WALL_MM,
    SOURCE_NAME,
    SOURCE_AXIS,
    SOURCE_WRIST,
    connected_components,
    sample_grid,
    source_frame,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
    radial_coordinates,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    parse_cluster_selection,
    violation_clusters,
)


REVIEW_COLLECTION = "30_REVIEW"


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--clusters", required=True)
    parser.add_argument("--patch-radius-mm", type=float, required=True)
    parser.add_argument(
        "--patch-offset-mm",
        type=float,
        default=RESERVED_WALL_MM + 0.05,
    )
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--bridge-boundaries", action="store_true")
    parser.add_argument("--bridge-layers", type=int, default=6)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.patch_radius_mm <= 0.0:
        parser.error("--patch-radius-mm must be positive")
    if args.patch_offset_mm < RESERVED_WALL_MM:
        parser.error(
            f"--patch-offset-mm must be at least {RESERVED_WALL_MM} mm"
        )
    if args.bridge_layers < 2:
        parser.error("--bridge-layers must be at least 2")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"CUTTER_PATCH_TRIAL: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def cyclic_angle_difference(first: float, second: float) -> float:
    return abs((first - second + pi) % (2.0 * pi) - pi)


def station_angle_radius(
    point: Vector,
    target_length: float,
) -> tuple[float, float, float]:
    normalized, angle, radius, _ = radial_coordinates(
        point,
        target_length,
    )
    return normalized * target_length, angle, radius


def mesh_audit(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        unseen = set(bm.verts)
        components = 0
        while unseen:
            components += 1
            stack = [unseen.pop()]
            while stack:
                vertex = stack.pop()
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other in unseen:
                        unseen.remove(other)
                        stack.append(other)
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "connected_components": components,
            "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
            "nonmanifold_edges": sum(
                not edge.is_manifold for edge in bm.edges
            ),
        }
    finally:
        bm.free()


def create_object(
    name: str,
    points: list[Vector],
    faces: list[tuple[int, ...]],
    material_indices: list[int],
    materials: list[bpy.types.Material],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    if bpy.data.objects.get(name) is not None:
        raise RuntimeError(
            f"CUTTER_PATCH_TRIAL: evaluation object '{name}' already exists"
        )
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(points, [], faces)
    mesh.update()
    for material in materials:
        mesh.materials.append(material)
    for polygon, material_index in zip(
        mesh.polygons,
        material_indices,
    ):
        polygon.material_index = material_index
    obj = bpy.data.objects.new(name, mesh)
    obj.matrix_world = Matrix.Identity(4)
    collection.objects.link(obj)
    obj["role"] = "bounded cutter-patch reconstruction trial"
    obj["status"] = "evaluation_only_not_approved"
    obj["printable"] = False
    obj.hide_set(True)
    obj.hide_render = True
    return obj


def overlap_pairs(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
) -> list[tuple[int, int]]:
    first = BVHTree.FromPolygons(
        points,
        faces,
        all_triangles=False,
    )
    second = BVHTree.FromPolygons(
        cutter_points,
        cutter_faces,
        all_triangles=False,
    )
    return first.overlap(second)


def boundary_edges(
    selected_faces: set[int],
    faces: list[tuple[int, ...]],
) -> list[tuple[int, int]]:
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for first, second in zip(face, face[1:] + face[:1]):
            edge_faces[tuple(sorted((first, second)))].append(face_index)
    result = []
    for edge, linked_faces in edge_faces.items():
        states = [
            face_index in selected_faces for face_index in linked_faces
        ]
        if any(states) and not all(states):
            result.append(edge)
    return result


def ordered_boundary_groups(
    edges: list[tuple[int, int]],
) -> list[tuple[list[int], bool]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(adjacency)
    groups = []
    while unseen:
        start = unseen.pop()
        stack = [start]
        vertices = {start}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    vertices.add(neighbor)
                    stack.append(neighbor)
        endpoints = [
            index for index in vertices if len(adjacency[index]) == 1
        ]
        closed = not endpoints
        if closed:
            current = min(vertices)
        elif len(endpoints) == 2:
            current = min(endpoints)
        else:
            raise RuntimeError(
                "CUTTER_PATCH_TRIAL: reconstruction boundary is branched; "
                f"degrees are {sorted(len(adjacency[index]) for index in vertices)}"
            )
        ordered = [current]
        previous = None
        while True:
            following = [
                neighbor
                for neighbor in adjacency[current]
                if neighbor != previous
            ]
            if not following:
                break
            candidate = following[0]
            if closed and candidate == ordered[0]:
                break
            if candidate in ordered:
                break
            ordered.append(candidate)
            previous, current = current, candidate
        groups.append((ordered, closed))
    groups.sort(key=lambda value: -len(value[0]))
    return groups


def cumulative_parameters(
    indices: list[int],
    points: list[Vector],
) -> list[float]:
    values = [0.0]
    for first, second in zip(indices, indices[1:]):
        values.append(
            values[-1] + (points[second] - points[first]).length
        )
    if values[-1] <= 1.0e-9:
        raise RuntimeError(
            "CUTTER_PATCH_TRIAL: boundary chain has zero length"
        )
    return [value / values[-1] for value in values]


def zipper_bridge(
    first: list[int],
    second: list[int],
    points: list[Vector],
) -> list[tuple[int, int, int]]:
    first_parameters = cumulative_parameters(first, points)
    second_parameters = cumulative_parameters(second, points)
    first_index = 0
    second_index = 0
    result = []
    while (
        first_index < len(first) - 1
        or second_index < len(second) - 1
    ):
        advance_first = (
            second_index == len(second) - 1
            or (
                first_index < len(first) - 1
                and first_parameters[first_index + 1]
                <= second_parameters[second_index + 1]
            )
        )
        if advance_first:
            result.append(
                (
                    first[first_index],
                    first[first_index + 1],
                    second[second_index],
                )
            )
            first_index += 1
        else:
            result.append(
                (
                    first[first_index],
                    second[second_index + 1],
                    second[second_index],
                )
            )
            second_index += 1
    return result


def best_loop_arc(
    chain: list[int],
    loop: list[int],
    points: list[Vector],
) -> list[int]:
    start = min(
        range(len(loop)),
        key=lambda index: (
            points[loop[index]] - points[chain[0]]
        ).length,
    )
    end = min(
        range(len(loop)),
        key=lambda index: (
            points[loop[index]] - points[chain[-1]]
        ).length,
    )
    if start <= end:
        forward = loop[start : end + 1]
        reverse = loop[start::-1] + loop[:end:-1]
    else:
        forward = loop[start:] + loop[: end + 1]
        reverse = loop[start : end - 1 : -1]
    candidates = [value for value in (forward, reverse) if len(value) >= 2]
    if not candidates:
        raise RuntimeError(
            "CUTTER_PATCH_TRIAL: patch loop cannot supply a boundary arc"
        )
    return min(
        candidates,
        key=lambda arc: sum(
            min(
                (points[index] - points[chain_vertex]).length
                for index in arc
            )
            for chain_vertex in chain
        )
        / len(chain),
    )


def sample_polyline(
    indices: list[int],
    parameters: list[float],
    value: float,
    points: list[Vector],
) -> Vector:
    for offset in range(len(parameters) - 1):
        if value > parameters[offset + 1]:
            continue
        span = parameters[offset + 1] - parameters[offset]
        factor = (
            0.0
            if span <= 1.0e-12
            else (value - parameters[offset]) / span
        )
        return points[indices[offset]].lerp(
            points[indices[offset + 1]],
            factor,
        )
    return points[indices[-1]].copy()


def clamp_to_reserved_wall(
    point: Vector,
    target_length: float,
    grid: list[list[float]],
    patch_offset_mm: float,
) -> Vector:
    normalized, angle, radius, direction = radial_coordinates(
        point,
        target_length,
    )
    minimum_radius = (
        sample_grid(grid, normalized, angle)
        + patch_offset_mm
    )
    if radius >= minimum_radius:
        return point
    return point + direction * (minimum_radius - radius)


def conforming_bridge(
    chain: list[int],
    arc: list[int],
    points: list[Vector],
    target_length: float,
    grid: list[list[float]],
    layers: int,
    patch_offset_mm: float,
) -> list[tuple[int, int, int]]:
    chain_parameters = cumulative_parameters(chain, points)
    arc_parameters = cumulative_parameters(arc, points)
    arc_targets = [
        sample_polyline(
            arc,
            arc_parameters,
            value,
            points,
        )
        for value in chain_parameters
    ]
    rows = [chain]
    for layer in range(1, layers + 1):
        factor = layer / layers
        row = []
        for source_index, target in zip(chain, arc_targets):
            point = points[source_index].lerp(target, factor)
            point = clamp_to_reserved_wall(
                point,
                target_length,
                grid,
                patch_offset_mm,
            )
            row.append(len(points))
            points.append(point)
        rows.append(row)
    result = []
    for first_row, second_row in zip(rows, rows[1:]):
        for offset in range(len(first_row) - 1):
            result.append(
                (
                    first_row[offset],
                    first_row[offset + 1],
                    second_row[offset + 1],
                )
            )
            result.append(
                (
                    first_row[offset],
                    second_row[offset + 1],
                    second_row[offset],
                )
            )
    result.extend(zipper_bridge(rows[-1], arc, points))
    return result


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"CUTTER_PATCH_TRIAL: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )

    component = set(components[args.component])
    before, faces, material_indices = evaluated_geometry(candidate)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    clusters = violation_clusters(
        component,
        before_margins,
        mesh_neighbors(source.data),
    )
    selected_clusters = parse_cluster_selection(
        args.clusters,
        len(clusters),
    )
    core = {
        index
        for cluster_index in selected_clusters
        for index in clusters[cluster_index]
    }
    vertex_component, _ = connected_components(source)
    component_faces = {
        face_index
        for face_index, face in enumerate(faces)
        if vertex_component[face[0]] == args.component
    }
    touched_faces = {
        face_index
        for face_index in component_faces
        if any(index in core for index in faces[face_index])
    }
    before_overlaps = overlap_pairs(
        before,
        faces,
        cutter_points,
        cutter_faces,
    )
    overlapping_component_faces = {
        face_index
        for face_index, _ in before_overlaps
        if face_index in component_faces
        and any(index in core for index in faces[face_index])
    }
    removed_faces = touched_faces | overlapping_component_faces
    if not removed_faces:
        raise RuntimeError(
            f"CUTTER_PATCH_TRIAL: selected component {args.component} "
            "clusters do not touch any candidate faces"
        )

    kept_face_records = [
        (face, material_indices[index])
        for index, face in enumerate(faces)
        if index not in removed_faces
    ]
    used = sorted(
        {
            index
            for face, _ in kept_face_records
            for index in face
        }
    )
    remap = {
        source_index: target_index
        for target_index, source_index in enumerate(used)
    }
    result_points = [before[index] for index in used]
    result_faces = [
        tuple(remap[index] for index in face)
        for face, _ in kept_face_records
    ]
    result_materials = [
        material_index for _, material_index in kept_face_records
    ]

    core_parameters = [
        station_angle_radius(before[index], target_length)
        for index in core
    ]
    patch_face_indices = []
    for face_index, face in enumerate(cutter_faces):
        if len(face) != 4:
            continue
        center = sum(
            (cutter_points[index] for index in face),
            Vector(),
        ) / len(face)
        station, angle, radius = station_angle_radius(
            center,
            target_length,
        )
        nearest = min(
            (
                (station - core_station) ** 2
                + (
                    radius
                    * cyclic_angle_difference(angle, core_angle)
                )
                ** 2
            )
            ** 0.5
            for core_station, core_angle, _ in core_parameters
        )
        if nearest <= args.patch_radius_mm:
            patch_face_indices.append(face_index)
    if not patch_face_indices:
        raise RuntimeError(
            f"CUTTER_PATCH_TRIAL: patch radius "
            f"{args.patch_radius_mm:.3f} mm selected no cutter faces"
        )

    patch_cutter_vertices = sorted(
        {
            index
            for face_index in patch_face_indices
            for index in cutter_faces[face_index]
        }
    )
    patch_remap = {
        cutter_index: len(result_points) + offset
        for offset, cutter_index in enumerate(patch_cutter_vertices)
    }
    for cutter_index in patch_cutter_vertices:
        point = cutter_points[cutter_index]
        _, _, _, direction = radial_coordinates(point, target_length)
        result_points.append(
            point + direction * args.patch_offset_mm
        )
    patch_material = material_indices[next(iter(component_faces))]
    for face_index in patch_face_indices:
        # The replacement is a wearer-facing inner surface, so its winding is
        # opposite the outward-facing cutter.
        result_faces.append(
            tuple(
                patch_remap[index]
                for index in reversed(cutter_faces[face_index])
            )
        )
        result_materials.append(patch_material)

    bridge_faces: list[tuple[int, int, int]] = []
    source_boundary_groups: list[tuple[list[int], bool]] = []
    patch_boundary_groups: list[tuple[list[int], bool]] = []
    if args.bridge_boundaries:
        source_boundary_groups = ordered_boundary_groups(
            boundary_edges(removed_faces, faces)
        )
        patch_boundary_groups = ordered_boundary_groups(
            boundary_edges(set(patch_face_indices), cutter_faces)
        )
        if any(closed for _, closed in source_boundary_groups):
            raise RuntimeError(
                "CUTTER_PATCH_TRIAL: expected open source transition chains, "
                "but found a closed boundary"
            )
        if any(not closed for _, closed in patch_boundary_groups):
            raise RuntimeError(
                "CUTTER_PATCH_TRIAL: expected closed cutter-patch boundaries, "
                "but found an open boundary"
            )
        source_chains = [
            [remap[index] for index in group]
            for group, _ in source_boundary_groups
        ]
        patch_loops = [
            [patch_remap[index] for index in group]
            for group, _ in patch_boundary_groups
        ]
        if len(source_chains) != len(patch_loops):
            raise RuntimeError(
                "CUTTER_PATCH_TRIAL: source transition-chain count "
                f"{len(source_chains)} does not match cutter-patch boundary "
                f"count {len(patch_loops)}"
            )
        unused_loops = set(range(len(patch_loops)))
        for chain in source_chains:
            chain_center = sum(
                (result_points[index] for index in chain),
                Vector(),
            ) / len(chain)
            loop_index = min(
                unused_loops,
                key=lambda index: (
                    chain_center
                    - sum(
                        (
                            result_points[vertex]
                            for vertex in patch_loops[index]
                        ),
                        Vector(),
                    )
                    / len(patch_loops[index])
                ).length,
            )
            unused_loops.remove(loop_index)
            arc = best_loop_arc(
                chain,
                patch_loops[loop_index],
                result_points,
            )
            bridge_faces.extend(
                conforming_bridge(
                    chain,
                    arc,
                    result_points,
                    target_length,
                    grid,
                    args.bridge_layers,
                    args.patch_offset_mm,
                )
            )
        result_faces.extend(bridge_faces)
        result_materials.extend([patch_material] * len(bridge_faces))

    collection = ensure_collection(REVIEW_COLLECTION)
    before_name = f"{args.prefix}_BEFORE"
    after_name = f"{args.prefix}_AFTER"
    before_obj = create_object(
        before_name,
        before,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    after_obj = create_object(
        after_name,
        result_points,
        result_faces,
        result_materials,
        list(candidate.data.materials),
        collection,
    )
    candidate.hide_set(False)
    candidate.hide_render = False
    bpy.context.view_layer.objects.active = candidate

    after_margins = point_margins(
        result_points,
        target_length,
        grid,
    )
    after_overlaps = overlap_pairs(
        result_points,
        result_faces,
        cutter_points,
        cutter_faces,
    )
    report = {
        "tool": Path(__file__).name,
        "status": "evaluation_only_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "selected_clusters": selected_clusters,
        "patch_radius_mm": args.patch_radius_mm,
        "source_edit": {
            "core_vertices": len(core),
            "faces_touching_core_removed": len(touched_faces),
            "exact_overlapping_core_faces_removed": len(
                overlapping_component_faces
            ),
            "total_faces_removed": len(removed_faces),
        },
        "replacement": {
            "cutter_vertices": len(patch_cutter_vertices),
            "cutter_faces": len(patch_face_indices),
            "radial_offset_mm": args.patch_offset_mm,
            "winding": "inward_opposite_cutter",
            "boundary_bridge_enabled": args.bridge_boundaries,
            "source_boundary_groups": [
                {
                    "vertices": len(group),
                    "closed": closed,
                }
                for group, closed in source_boundary_groups
            ],
            "patch_boundary_groups": [
                {
                    "vertices": len(group),
                    "closed": closed,
                }
                for group, closed in patch_boundary_groups
            ],
            "bridge_faces": len(bridge_faces),
            "bridge_layers": (
                args.bridge_layers if args.bridge_boundaries else 0
            ),
        },
        "clearance": {
            "before_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in before_margins
            ),
            "after_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in after_margins
            ),
            "before_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in before_margins
            ),
            "after_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in after_margins
            ),
            "before_triangle_overlaps": len(before_overlaps),
            "after_triangle_overlaps": len(after_overlaps),
        },
        "objects": {
            "before": {
                "name": before_obj.name,
                "audit": mesh_audit(before_obj),
            },
            "after": {
                "name": after_obj.name,
                "audit": mesh_audit(after_obj),
            },
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
        f"DONE: created bounded cutter-patch reconstruction trial for "
        f"component {args.component}; qualitative review remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
