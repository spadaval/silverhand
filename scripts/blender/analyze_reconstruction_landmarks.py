"""Record durable topology landmarks for one bounded reconstruction region.

This diagnostic is read-only. It verifies an explicit shape-key checkpoint,
identifies one current reserved-margin violation cluster, and records stable
source vertex, edge, and face IDs for candidate reconstruction boundaries.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
from rescue_clearance_fragments import cutter_grid, mesh_neighbors  # noqa: E402
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    violation_clusters,
)
from try_boundary_preserving_cutter_reconstruction import (  # noqa: E402
    edge_faces,
    expand_face_rings,
    removed_open_boundary_edges,
    transition_edges,
)


OPERATION = "RECONSTRUCTION_LANDMARK_AUDIT"


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--cluster", type=int, required=True)
    parser.add_argument(
        "--topology-rings",
        default="0,1,2,3,4,6,8",
        help="Comma-separated non-negative face-ring counts.",
    )
    parser.add_argument(
        "--base-shape-key",
        required=True,
        help="Shape key that must be active at value 1.0.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[separator + 1 :])
    try:
        args.topology_rings = sorted(
            {int(value) for value in args.topology_rings.split(",")}
        )
    except ValueError as error:
        parser.error(
            f"--topology-rings contains a non-integer value: {error}"
        )
    if not args.topology_rings or any(
        value < 0 for value in args.topology_rings
    ):
        parser.error("--topology-rings must contain non-negative integers")
    if args.component < 0:
        parser.error("--component must be non-negative")
    if args.cluster < 0:
        parser.error("--cluster must be non-negative")
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


def geometry_sha256(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> str:
    digest = hashlib.sha256()
    digest.update(struct.pack("<QQ", len(points), len(faces)))
    for point in points:
        digest.update(struct.pack("<ddd", point.x, point.y, point.z))
    for face in faces:
        digest.update(struct.pack("<Q", len(face)))
        digest.update(struct.pack(f"<{len(face)}Q", *face))
    return digest.hexdigest()


def face_normal(
    points: list[Vector],
    face: tuple[int, ...],
) -> Vector:
    normal = Vector((0.0, 0.0, 0.0))
    for index, current in enumerate(face):
        following = face[(index + 1) % len(face)]
        first = points[current]
        second = points[following]
        normal.x += (first.y - second.y) * (first.z + second.z)
        normal.y += (first.z - second.z) * (first.x + second.x)
        normal.z += (first.x - second.x) * (first.y + second.y)
    if normal.length <= 1.0e-12:
        return normal
    return normal.normalized()


def dihedral_degrees(
    normals: list[Vector],
    adjacent_faces: list[int],
) -> float | None:
    if len(adjacent_faces) != 2:
        return None
    first = normals[adjacent_faces[0]]
    second = normals[adjacent_faces[1]]
    if first.length <= 1.0e-12 or second.length <= 1.0e-12:
        return None
    return degrees(acos(max(-1.0, min(1.0, first.dot(second)))))


def exact_groups(
    edges: list[tuple[int, int]],
    edge_ids: dict[tuple[int, int], int],
) -> dict:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    degree_counts = Counter(len(neighbors) for neighbors in adjacency.values())
    unseen_vertices = set(adjacency)
    groups = []
    while unseen_vertices:
        seed = min(unseen_vertices)
        stack = [seed]
        vertices = set()
        while stack:
            current = stack.pop()
            if current in vertices:
                continue
            vertices.add(current)
            unseen_vertices.discard(current)
            stack.extend(sorted(adjacency[current] - vertices, reverse=True))
        group_edges = sorted(
            edge for edge in edges if edge[0] in vertices
        )
        group_degrees = {
            vertex: len(adjacency[vertex]) for vertex in sorted(vertices)
        }
        endpoints = sorted(
            vertex for vertex, degree in group_degrees.items() if degree == 1
        )
        branched = any(degree > 2 for degree in group_degrees.values())
        groups.append(
            {
                "status": (
                    "branched"
                    if branched
                    else "closed"
                    if not endpoints and group_edges
                    else "open"
                ),
                "vertex_ids": sorted(vertices),
                "edge_ids": [edge_ids[edge] for edge in group_edges],
                "edge_vertex_ids": [list(edge) for edge in group_edges],
                "endpoint_vertex_ids": endpoints,
                "degree_by_vertex_id": {
                    str(vertex): degree
                    for vertex, degree in group_degrees.items()
                },
            }
        )
    return {
        "edge_count": len(edges),
        "vertex_count": len(adjacency),
        "degree_counts": {
            str(degree): count
            for degree, count in sorted(degree_counts.items())
        },
        "groups": groups,
    }


def edge_record(
    edge: tuple[int, int],
    edge_ids: dict[tuple[int, int], int],
    linked_faces: dict[tuple[int, int], list[int]],
    source_points: list[Vector],
    current_points: list[Vector],
    source_normals: list[Vector],
    current_normals: list[Vector],
) -> dict:
    first, second = edge
    adjacent_faces = sorted(linked_faces[edge])
    source_length = (source_points[first] - source_points[second]).length
    current_length = (current_points[first] - current_points[second]).length
    return {
        "edge_id": edge_ids[edge],
        "vertex_ids": [first, second],
        "adjacent_face_ids": adjacent_faces,
        "source_length_mm": round(source_length, 6),
        "current_length_mm": round(current_length, 6),
        "current_to_source_length_ratio": (
            round(current_length / source_length, 6)
            if source_length > 1.0e-12
            else None
        ),
        "source_dihedral_degrees": (
            None
            if (value := dihedral_degrees(source_normals, adjacent_faces))
            is None
            else round(value, 6)
        ),
        "current_dihedral_degrees": (
            None
            if (value := dihedral_degrees(current_normals, adjacent_faces))
            is None
            else round(value, 6)
        ),
    }


def edge_cue_summary(records: list[dict]) -> dict:
    with_dihedral = [
        record
        for record in records
        if record["current_dihedral_degrees"] is not None
    ]
    return {
        "sharpest_current_dihedral_edge_ids": [
            record["edge_id"]
            for record in sorted(
                with_dihedral,
                key=lambda item: (
                    -item["current_dihedral_degrees"],
                    item["edge_id"],
                ),
            )[:12]
        ],
        "longest_current_edge_ids": [
            record["edge_id"]
            for record in sorted(
                records,
                key=lambda item: (
                    -item["current_length_mm"],
                    item["edge_id"],
                ),
            )[:12]
        ],
        "largest_length_change_edge_ids": [
            record["edge_id"]
            for record in sorted(
                records,
                key=lambda item: (
                    -abs(item["current_to_source_length_ratio"] - 1.0),
                    item["edge_id"],
                ),
            )[:12]
            if record["current_to_source_length_ratio"] is not None
        ],
    }


def custom_property_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    blend_path = Path(bpy.data.filepath).resolve()
    if not blend_path.is_file():
        raise RuntimeError(
            f"{OPERATION}: active blend target '{blend_path}' is not a file"
        )

    shape_keys = candidate.data.shape_keys
    if shape_keys is None:
        raise RuntimeError(
            f"{OPERATION}: fitted-surface candidate '{candidate.name}' "
            "has no shape keys"
        )
    base_key = shape_keys.key_blocks.get(args.base_shape_key)
    if base_key is None:
        raise RuntimeError(
            f"{OPERATION}: required base shape key "
            f"'{args.base_shape_key}' is missing from '{candidate.name}'"
        )
    if abs(base_key.value - 1.0) > TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: base shape key '{base_key.name}' has value "
            f"{base_key.value:.6f}, expected 1.0"
        )
    latest_patch = candidate.get("latest_clearance_patch")
    if latest_patch != args.base_shape_key:
        raise RuntimeError(
            f"{OPERATION}: candidate '{candidate.name}' records latest "
            f"patch '{latest_patch}', expected '{args.base_shape_key}'"
        )

    vertex_component, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"{OPERATION}: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )
    component = set(components[args.component])
    source_points, source_faces, _ = evaluated_geometry(source)
    current_points, current_faces, _ = evaluated_geometry(candidate)
    if len(source_points) != len(current_points):
        raise RuntimeError(
            f"{OPERATION}: source/candidate vertex counts differ "
            f"({len(source_points)} != {len(current_points)}); stable "
            "source vertex IDs cannot be used"
        )
    if source_faces != current_faces:
        raise RuntimeError(
            f"{OPERATION}: source/candidate face topology differs; stable "
            "source edge and face IDs cannot be used"
        )

    neighbors = mesh_neighbors(source.data)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    margins = point_margins(current_points, target_length, grid)
    clusters = violation_clusters(component, margins, neighbors)
    if not 0 <= args.cluster < len(clusters):
        raise RuntimeError(
            f"{OPERATION}: cluster {args.cluster} is outside "
            f"0..{len(clusters) - 1} for component {args.component}"
        )
    cluster = set(clusters[args.cluster])

    linked_faces = edge_faces(current_faces)
    edge_ids = {
        tuple(sorted(edge.vertices)): edge.index for edge in source.data.edges
    }
    missing_edges = sorted(set(linked_faces) - set(edge_ids))
    if missing_edges:
        raise RuntimeError(
            f"{OPERATION}: source edge IDs are missing for "
            f"{len(missing_edges)} evaluated topology edges; first missing "
            f"edge is {missing_edges[0]}"
        )
    component_faces = {
        face_index
        for face_index, face in enumerate(current_faces)
        if vertex_component[face[0]] == args.component
    }
    core_faces = {
        face_index
        for face_index in component_faces
        if any(vertex in cluster for vertex in current_faces[face_index])
    }
    source_normals = [
        face_normal(source_points, face) for face in source_faces
    ]
    current_normals = [
        face_normal(current_points, face) for face in current_faces
    ]

    boundary_candidates = []
    all_open_contact_vertices = set()
    for rings in args.topology_rings:
        selected_faces = expand_face_rings(
            core_faces,
            component_faces,
            linked_faces,
            rings,
        )
        boundary_edges = sorted(
            transition_edges(selected_faces, linked_faces)
        )
        open_edges = sorted(
            removed_open_boundary_edges(selected_faces, linked_faces)
        )
        all_open_contact_vertices.update(
            vertex for edge in open_edges for vertex in edge
        )
        boundary_records = [
            edge_record(
                edge,
                edge_ids,
                linked_faces,
                source_points,
                current_points,
                source_normals,
                current_normals,
            )
            for edge in boundary_edges
        ]
        open_records = [
            edge_record(
                edge,
                edge_ids,
                linked_faces,
                source_points,
                current_points,
                source_normals,
                current_normals,
            )
            for edge in open_edges
        ]
        boundary_candidates.append(
            {
                "topology_rings": rings,
                "selected_face_ids": sorted(selected_faces),
                "new_ring_face_ids": sorted(selected_faces - core_faces),
                "transition_boundary": {
                    **exact_groups(boundary_edges, edge_ids),
                    "edge_records": boundary_records,
                    "cue_summary": edge_cue_summary(boundary_records),
                },
                "source_open_boundary_contacts": {
                    **exact_groups(open_edges, edge_ids),
                    "edge_records": open_records,
                },
            }
        )

    cluster_margin_records = [
        {
            "vertex_id": vertex,
            "cutter_margin_mm": round(margins[vertex], 6),
            "reserved_margin_delta_mm": round(
                margins[vertex] - RESERVED_WALL_MM,
                6,
            ),
            "current_world_mm": [
                round(value, 6) for value in current_points[vertex]
            ],
            "source_world_mm": [
                round(value, 6) for value in source_points[vertex]
            ],
        }
        for vertex in sorted(cluster)
    ]
    active_keys = [
        {
            "name": key.name,
            "value": round(key.value, 6),
            "relative_key": (
                key.relative_key.name if key.relative_key is not None else None
            ),
        }
        for key in shape_keys.key_blocks
        if abs(key.value) > TOLERANCE_MM
    ]
    report = {
        "tool": Path(__file__).name,
        "status": "diagnostic_only_no_geometry_saved",
        "units": "millimeters",
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": sha256_file(blend_path),
            "required_active_shape_key": args.base_shape_key,
            "active_shape_keys": active_keys,
            "candidate_latest_patch": latest_patch,
            "candidate_custom_properties": {
                key: custom_property_value(candidate[key])
                for key in sorted(candidate.keys())
                if key.startswith("latest_clearance_patch")
                or key == "target_length_mm"
            },
            "source_geometry_sha256": geometry_sha256(
                source_points,
                source_faces,
            ),
            "evaluated_candidate_geometry_sha256": geometry_sha256(
                current_points,
                current_faces,
            ),
            "source_vertices": len(source_points),
            "source_edges": len(source.data.edges),
            "source_faces": len(source_faces),
        },
        "selection": {
            "component": args.component,
            "component_vertex_count": len(component),
            "component_vertex_ids": sorted(component),
            "current_violation_cluster_count": len(clusters),
            "cluster": args.cluster,
            "cluster_vertex_count": len(cluster),
            "cluster_vertex_ids": sorted(cluster),
            "cluster_face_ids": sorted(core_faces),
        },
        "cutter_margins": {
            "reserved_wall_mm": RESERVED_WALL_MM,
            "component_vertices_below_cutter": sum(
                margins[vertex] < -TOLERANCE_MM for vertex in component
            ),
            "component_vertices_below_reserved_margin": sum(
                margins[vertex] < RESERVED_WALL_MM - TOLERANCE_MM
                for vertex in component
            ),
            "cluster_minimum_margin_mm": round(
                min(margins[vertex] for vertex in cluster),
                6,
            ),
            "cluster_maximum_margin_mm": round(
                max(margins[vertex] for vertex in cluster),
                6,
            ),
            "cluster_vertex_records": cluster_margin_records,
            "deepest_cluster_vertex_ids": [
                record["vertex_id"]
                for record in sorted(
                    cluster_margin_records,
                    key=lambda item: (
                        item["cutter_margin_mm"],
                        item["vertex_id"],
                    ),
                )[:12]
            ],
        },
        "reconstruction_boundary_candidates": boundary_candidates,
        "landmark_summary": {
            "source_open_boundary_contact_vertex_ids": sorted(
                all_open_contact_vertices
            ),
            "stable_id_namespace": (
                "SRC_GAME_TPU_ONLY_BASELINE mesh vertex/edge/polygon indices"
            ),
            "use_note": (
                "Use explicit IDs only with the recorded blend and evaluated "
                "geometry fingerprints; re-run after any topology change."
            ),
        },
        "promotion": "NOT_PROMOTED",
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"DONE: recorded reconstruction landmarks for component "
        f"{args.component} cluster {args.cluster} in '{output}'; no "
        "geometry was saved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
