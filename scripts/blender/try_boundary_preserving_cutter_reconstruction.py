"""Create an evaluation-only cutter patch that preserves open boundaries.

The trial removes faces touching selected wearer-facing violation clusters.
For each removed region that reaches an existing open boundary, it replaces
the removed boundary path with a cutter-conforming path having the same number
of edges, then joins that path to the retained transition chain through a
layered strip. It never edits the active fitted-surface candidate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

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
    connected_components,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    parse_cluster_selection,
    violation_clusters,
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


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--clusters", required=True)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--face-rings", type=int, default=0)
    parser.add_argument(
        "--patch-offset-mm",
        type=float,
        default=RESERVED_WALL_MM + 0.05,
    )
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.layers < 2:
        parser.error("--layers must be at least 2")
    if args.face_rings < 0:
        parser.error("--face-rings must be non-negative")
    if args.patch_offset_mm < RESERVED_WALL_MM:
        parser.error(
            f"--patch-offset-mm must be at least {RESERVED_WALL_MM} mm"
        )
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"BOUNDARY_PATCH_TRIAL: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def edge_faces(
    faces: list[tuple[int, ...]],
) -> dict[tuple[int, int], list[int]]:
    result: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for first, second in zip(face, face[1:] + face[:1]):
            result[tuple(sorted((first, second)))].append(face_index)
    return result


def transition_edges(
    selected_faces: set[int],
    linked_faces: dict[tuple[int, int], list[int]],
) -> list[tuple[int, int]]:
    return [
        edge
        for edge, face_indices in linked_faces.items()
        if len(face_indices) == 2
        and sum(index in selected_faces for index in face_indices) == 1
    ]


def removed_open_boundary_edges(
    selected_faces: set[int],
    linked_faces: dict[tuple[int, int], list[int]],
) -> list[tuple[int, int]]:
    return [
        edge
        for edge, face_indices in linked_faces.items()
        if len(face_indices) == 1 and face_indices[0] in selected_faces
    ]


def expand_face_rings(
    selected_faces: set[int],
    allowed_faces: set[int],
    linked_faces: dict[tuple[int, int], list[int]],
    rings: int,
) -> set[int]:
    result = set(selected_faces)
    frontier = set(selected_faces)
    for _ in range(rings):
        following = {
            face_index
            for edge_faces_value in linked_faces.values()
            if any(index in frontier for index in edge_faces_value)
            for face_index in edge_faces_value
            if face_index in allowed_faces and face_index not in result
        }
        if not following:
            break
        result.update(following)
        frontier = following
    return result


def oriented_edge_in_face(
    face: tuple[int, ...],
    first: int,
    second: int,
) -> int:
    for current, following in zip(face, face[1:] + face[:1]):
        if current == first and following == second:
            return 1
        if current == second and following == first:
            return -1
    raise RuntimeError(
        f"BOUNDARY_PATCH_TRIAL: edge ({first}, {second}) is absent from "
        f"face {face}"
    )


def orient_transition_chain(
    chain: list[int],
    selected_faces: set[int],
    faces: list[tuple[int, ...]],
    linked_faces: dict[tuple[int, int], list[int]],
) -> list[int]:
    first, second = chain[:2]
    linked = linked_faces[tuple(sorted((first, second)))]
    kept_faces = [index for index in linked if index not in selected_faces]
    if len(kept_faces) != 1:
        raise RuntimeError(
            "BOUNDARY_PATCH_TRIAL: transition edge "
            f"({first}, {second}) has {len(kept_faces)} retained faces, "
            "expected exactly one"
        )
    direction = oriented_edge_in_face(
        faces[kept_faces[0]],
        first,
        second,
    )
    # The replacement must traverse the shared edge opposite the retained face.
    return list(reversed(chain)) if direction > 0 else chain


def orient_path(
    path: list[int],
    start: int,
    end: int,
    role: str,
) -> list[int]:
    if path[0] == start and path[-1] == end:
        return path
    if path[-1] == start and path[0] == end:
        return list(reversed(path))
    raise RuntimeError(
        f"BOUNDARY_PATCH_TRIAL: {role} endpoints "
        f"{sorted((path[0], path[-1]))} do not match expected "
        f"{sorted((start, end))}"
    )


def match_strip_boundaries(
    transition_groups: list[tuple[list[int], bool]],
    removed_boundary_groups: list[tuple[list[int], bool]],
    selected_faces: set[int],
    faces: list[tuple[int, ...]],
    linked_faces: dict[tuple[int, int], list[int]],
) -> tuple[list[int], list[int], list[int], list[int]]:
    if len(transition_groups) != 2 or any(
        closed for _, closed in transition_groups
    ):
        raise RuntimeError(
            "BOUNDARY_PATCH_TRIAL: boundary-preserving strip requires "
            f"exactly two open retained transitions, got "
            f"{[(len(group), closed) for group, closed in transition_groups]}"
        )
    if len(removed_boundary_groups) != 2 or any(
        closed for _, closed in removed_boundary_groups
    ):
        raise RuntimeError(
            "BOUNDARY_PATCH_TRIAL: boundary-preserving strip requires "
            f"exactly two open removed-boundary connectors, got "
            f"{[(len(group), closed) for group, closed in removed_boundary_groups]}"
        )

    first_raw, second_raw = sorted(
        (group for group, _ in transition_groups),
        key=len,
        reverse=True,
    )
    first = orient_transition_chain(
        first_raw,
        selected_faces,
        faces,
        linked_faces,
    )
    connectors = [group for group, _ in removed_boundary_groups]

    def connector_from(endpoint: int) -> list[int]:
        matches = [
            group
            for group in connectors
            if endpoint in {group[0], group[-1]}
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"BOUNDARY_PATCH_TRIAL: transition endpoint {endpoint} "
                f"touches {len(matches)} removed-boundary connectors, "
                "expected exactly one"
            )
        connector = matches[0]
        connectors.remove(connector)
        return (
            connector
            if connector[0] == endpoint
            else list(reversed(connector))
        )

    left = connector_from(first[0])
    right_from_first = connector_from(first[-1])
    second_left = left[-1]
    second_right = right_from_first[-1]
    second = orient_path(
        second_raw,
        second_left,
        second_right,
        "second retained transition",
    )
    right = right_from_first

    expected_second = list(
        reversed(
            orient_transition_chain(
                second_raw,
                selected_faces,
                faces,
                linked_faces,
            )
        )
    )
    if second != expected_second:
        raise RuntimeError(
            "BOUNDARY_PATCH_TRIAL: retained transition windings disagree; "
            f"first endpoints are {(first[0], first[-1])}, second endpoints "
            f"are {(second[0], second[-1])}"
        )
    return first, second, left, right


def nondegenerate(
    face: tuple[int, int, int],
    points: list[Vector],
) -> bool:
    if len(set(face)) != 3:
        return False
    first, second, third = (points[index] for index in face)
    return (second - first).cross(third - first).length > 1.0e-8


def orientation_audit(obj: bpy.types.Object) -> dict:
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


def boundary_preserving_strip(
    first: list[int],
    second: list[int],
    left_connector: list[int],
    right_connector: list[int],
    remap: dict[int, int],
    before: list[Vector],
    points: list[Vector],
    target_length: float,
    grid: list[list[float]],
    layers: int,
    patch_offset_mm: float,
) -> tuple[list[tuple[int, int, int]], dict[int, int]]:
    first_indices = [remap[index] for index in first]
    second_indices = [remap[index] for index in second]
    first_parameters = cumulative_parameters(first_indices, points)
    second_parameters = cumulative_parameters(second_indices, points)
    second_samples = [
        sample_polyline(
            second_indices,
            second_parameters,
            value,
            points,
        )
        for value in first_parameters
    ]

    projected: dict[int, int] = {
        first[0]: first_indices[0],
        first[-1]: first_indices[-1],
        second[0]: second_indices[0],
        second[-1]: second_indices[-1],
    }

    def projected_connector_vertex(
        connector: list[int],
        layer: int,
    ) -> int:
        edge_count = len(connector) - 1
        source_offset = (layer * edge_count) // layers
        source_index = connector[source_offset]
        existing = projected.get(source_index)
        if existing is not None:
            return existing
        projected[source_index] = len(points)
        points.append(
            clamp_to_reserved_wall(
                before[source_index].copy(),
                target_length,
                grid,
                patch_offset_mm,
            )
        )
        return projected[source_index]

    rows = [first_indices]
    for layer in range(1, layers):
        factor = layer / layers
        row = [
            projected_connector_vertex(left_connector, layer)
        ]
        for source_index, target_point in zip(
            first_indices[1:-1],
            second_samples[1:-1],
        ):
            point = points[source_index].lerp(target_point, factor)
            point = clamp_to_reserved_wall(
                point,
                target_length,
                grid,
                patch_offset_mm,
            )
            row.append(len(points))
            points.append(point)
        row.append(
            projected_connector_vertex(right_connector, layer)
        )
        rows.append(row)

    result = []
    for first_row, second_row in zip(rows, rows[1:]):
        for offset in range(len(first_row) - 1):
            result.extend(
                (
                    (
                        first_row[offset],
                        first_row[offset + 1],
                        second_row[offset + 1],
                    ),
                    (
                        first_row[offset],
                        second_row[offset + 1],
                        second_row[offset],
                    ),
                )
            )
    result.extend(zipper_bridge(rows[-1], second_indices, points))
    return (
        [face for face in result if nondegenerate(face, points)],
        projected,
    )


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")

    vertex_component, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"BOUNDARY_PATCH_TRIAL: component {args.component} is outside "
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
    }
    initial_removed_faces = touched_faces | overlapping_component_faces
    linked_faces = edge_faces(faces)
    removed_faces = expand_face_rings(
        initial_removed_faces,
        component_faces,
        linked_faces,
        args.face_rings,
    )
    if not removed_faces:
        raise RuntimeError(
            f"BOUNDARY_PATCH_TRIAL: component {args.component} clusters "
            f"{selected_clusters} touch no faces"
        )

    transition_groups = ordered_boundary_groups(
        transition_edges(removed_faces, linked_faces)
    )
    removed_boundary_groups = ordered_boundary_groups(
        removed_open_boundary_edges(removed_faces, linked_faces)
    )
    strip_boundaries = match_strip_boundaries(
        transition_groups,
        removed_boundary_groups,
        removed_faces,
        faces,
        linked_faces,
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
    result_points = [before[index].copy() for index in used]
    result_faces = [
        tuple(remap[index] for index in face)
        for face, _ in kept_face_records
    ]
    kept_face_count = len(result_faces)
    result_materials = [
        material_index for _, material_index in kept_face_records
    ]

    first, second, left_connector, right_connector = strip_boundaries
    replacement_faces, projected = boundary_preserving_strip(
        first,
        second,
        left_connector,
        right_connector,
        remap,
        before,
        result_points,
        target_length,
        grid,
        args.layers,
        args.patch_offset_mm,
    )
    replacement_records = [
        {
            "first_transition_vertices": len(first),
            "second_transition_vertices": len(second),
            "left_connector_vertices": len(left_connector),
            "right_connector_vertices": len(right_connector),
            "projected_connector_vertices": len(projected),
            "strip_faces": len(replacement_faces),
        }
    ]

    patch_material = material_indices[next(iter(component_faces))]
    result_faces.extend(replacement_faces)
    result_materials.extend([patch_material] * len(replacement_faces))

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
        result_points,
        result_faces,
        result_materials,
        list(candidate.data.materials),
        collection,
    )

    after_margins = point_margins(result_points, target_length, grid)
    after_overlaps = overlap_pairs(
        result_points,
        result_faces,
        cutter_points,
        cutter_faces,
    )
    before_audit = mesh_audit(before_obj)
    after_audit = mesh_audit(after_obj)
    before_orientation = orientation_audit(before_obj)
    after_orientation = orientation_audit(after_obj)
    report = {
        "tool": Path(__file__).name,
        "status": "evaluation_only_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "selected_clusters": selected_clusters,
        "source_edit": {
            "core_vertices": len(core),
            "faces_touching_core": len(touched_faces),
            "exact_overlapping_component_faces": len(
                overlapping_component_faces
            ),
            "face_rings": args.face_rings,
            "faces_before_ring_expansion": len(initial_removed_faces),
            "faces_removed": len(removed_faces),
        },
        "replacement": {
            "mode": "boundary_count_preserving_cutter_conforming_strips",
            "layers": args.layers,
            "radial_offset_mm": args.patch_offset_mm,
            "paths": replacement_records,
            "faces": len(replacement_faces),
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
            "replacement_triangle_overlaps": sum(
                face_index >= kept_face_count
                for face_index, _ in after_overlaps
            ),
        },
        "objects": {
            "before": {
                "name": before_obj.name,
                "audit": before_audit,
                "orientation": before_orientation,
            },
            "after": {
                "name": after_obj.name,
                "audit": after_audit,
                "orientation": after_orientation,
            },
        },
        "topology_result": {
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
        "DONE: created boundary-count-preserving cutter reconstruction "
        f"trial for component {args.component}; qualitative review remains "
        "PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
