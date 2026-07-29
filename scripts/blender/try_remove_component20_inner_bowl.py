"""Remove the mapped component-20 inner bowl without adding replacement geometry."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from build_combined_authored_inner_bowl_liner import (  # noqa: E402
    EXPECTED_BLEND_SHA256,
    MAPPING_PATH,
    TOLERANCE_MM,
    fingerprint,
    sha256_file,
    topology_record,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
    sample_grid,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    radial_coordinates,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    create_object,
    ensure_collection,
    overlap_pairs,
)
from try_landmark_sector_retopology import REVIEW_COLLECTION  # noqa: E402


OPERATION = "REMOVE_COMPONENT20_INNER_BOWL"
STAGED_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
RESERVED_MARGIN_MM = 2.5


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


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def face_edges(face: tuple[int, ...]) -> list[tuple[int, int]]:
    return [
        tuple(sorted((first, second)))
        for first, second in zip(face, face[1:] + face[:1])
    ]


def edge_counts(
    faces: list[tuple[int, ...]],
    face_ids=None,
) -> Counter:
    selected = (
        range(len(faces)) if face_ids is None else sorted(face_ids)
    )
    return Counter(
        edge
        for face_id in selected
        for edge in face_edges(faces[face_id])
    )


def edge_group_records(
    edges: set[tuple[int, int]],
    source_edge_id: dict[tuple[int, int], int],
) -> list[dict]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(adjacency)
    records = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        stack = [start]
        vertices = {start}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in unseen:
                    continue
                unseen.remove(neighbor)
                vertices.add(neighbor)
                stack.append(neighbor)
        group_edges = {
            edge
            for edge in edges
            if edge[0] in vertices and edge[1] in vertices
        }
        degree = {
            vertex: len(adjacency[vertex]) for vertex in sorted(vertices)
        }
        endpoints = [
            vertex for vertex, value in degree.items() if value == 1
        ]
        if all(value == 2 for value in degree.values()):
            status = "closed"
        elif len(endpoints) == 2 and all(
            value in {1, 2} for value in degree.values()
        ):
            status = "open"
        else:
            status = "branched"
        records.append(
            {
                "status": status,
                "vertex_count": len(vertices),
                "edge_count": len(group_edges),
                "vertex_ids": sorted(vertices),
                "edge_ids": sorted(source_edge_id[edge] for edge in group_edges),
                "edge_vertex_ids": [list(edge) for edge in sorted(group_edges)],
                "endpoint_vertex_ids": endpoints,
                "degree_by_vertex_id": {
                    str(vertex): value
                    for vertex, value in degree.items()
                },
            }
        )
    records.sort(
        key=lambda record: (-record["edge_count"], record["vertex_ids"][0])
    )
    return records


def remap_retained(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    materials: list[int],
    removed_faces: set[int],
) -> tuple[
    list[Vector],
    list[tuple[int, ...]],
    list[int],
    list[int],
    dict[int, int],
]:
    retained_face_ids = [
        face_id
        for face_id in range(len(faces))
        if face_id not in removed_faces
    ]
    retained_source_ids = sorted(
        {
            vertex
            for face_id in retained_face_ids
            for vertex in faces[face_id]
        }
    )
    source_to_result = {
        source_id: result_id
        for result_id, source_id in enumerate(retained_source_ids)
    }
    return (
        [points[source_id].copy() for source_id in retained_source_ids],
        [
            tuple(source_to_result[vertex] for vertex in faces[face_id])
            for face_id in retained_face_ids
        ],
        [materials[face_id] for face_id in retained_face_ids],
        retained_source_ids,
        source_to_result,
    )


def local_geometry(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    face_ids: set[int],
) -> tuple[list[Vector], list[tuple[int, ...]], list[int]]:
    source_ids = sorted(
        {
            vertex
            for face_id in face_ids
            for vertex in faces[face_id]
        }
    )
    source_to_local = {
        source_id: local_id
        for local_id, source_id in enumerate(source_ids)
    }
    return (
        [points[source_id] for source_id in source_ids],
        [
            tuple(source_to_local[vertex] for vertex in faces[face_id])
            for face_id in sorted(face_ids)
        ],
        source_ids,
    )


def clearance_failures(
    points: list[Vector],
    source_ids: list[int],
    target_length: float,
    grid: list[list[float]],
) -> dict:
    below_cutter = []
    below_reserved = []
    margins = {}
    for point, source_id in zip(points, source_ids):
        normalized, angle, radius, _ = radial_coordinates(
            point,
            target_length,
        )
        margin = radius - sample_grid(grid, normalized, angle)
        margins[str(source_id)] = round(margin, 6)
        if margin < 0.0:
            below_cutter.append(source_id)
        if margin < RESERVED_MARGIN_MM:
            below_reserved.append(source_id)
    return {
        "vertex_count": len(source_ids),
        "vertices_below_cutter_count": len(below_cutter),
        "vertices_below_cutter_ids": below_cutter,
        "vertices_below_reserved_margin_count": len(below_reserved),
        "vertices_below_reserved_margin_ids": below_reserved,
        "reserved_margin_mm": RESERVED_MARGIN_MM,
        "clearance_margin_mm_by_vertex_id": margins,
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
    staged = require_mesh(STAGED_NAME, "coordinated staged geometry")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    staged_points, staged_faces, staged_materials = evaluated_geometry(staged)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    removed_face_ids = set(
        mapping["reconstruction_scope"]["rebuild_face_ids"]
    )
    retained_c20_face_ids = set(
        mapping["reconstruction_scope"]["retain_face_ids"]
    )
    _, components = connected_components(source)
    component9 = set(components[9])
    component20 = set(components[20])
    component20_face_ids = {
        face_id
        for face_id, face in enumerate(staged_faces)
        if face[0] in component20
    }
    component9_face_ids = {
        face_id
        for face_id, face in enumerate(staged_faces)
        if face[0] in component9
    }
    if (
        len(removed_face_ids) != 724
        or len(retained_c20_face_ids) != 1409
        or removed_face_ids | retained_c20_face_ids != component20_face_ids
        or removed_face_ids & retained_c20_face_ids
    ):
        raise RuntimeError(
            f"{OPERATION}: component-20 mapping is not the exact "
            "724-removed/1409-retained partition"
        )
    (
        result_points,
        result_faces,
        result_materials,
        retained_source_ids,
        source_to_result,
    ) = remap_retained(
        staged_points,
        staged_faces,
        staged_materials,
        removed_face_ids,
    )
    retained_face_ids = [
        face_id
        for face_id in range(len(staged_faces))
        if face_id not in removed_face_ids
    ]
    removed_vertex_ids = sorted(
        set(range(len(staged_points))) - set(retained_source_ids)
    )
    retained_before = [
        staged_points[source_id] for source_id in retained_source_ids
    ]
    outside_before_fp = fingerprint(retained_source_ids, retained_before)
    outside_after_fp = fingerprint(retained_source_ids, result_points)
    collection = ensure_collection(REVIEW_COLLECTION)
    before_obj = create_object(
        f"{args.prefix}_BEFORE",
        staged_points,
        staged_faces,
        staged_materials,
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
    before_edge_counts = edge_counts(staged_faces)
    after_source_faces = [
        staged_faces[face_id] for face_id in retained_face_ids
    ]
    after_edge_counts = edge_counts(after_source_faces)
    source_edge_id = {
        tuple(sorted(edge.vertices)): edge.index for edge in source.data.edges
    }
    new_boundary = {
        edge
        for edge, count in after_edge_counts.items()
        if count == 1 and before_edge_counts[edge] == 2
    }
    removed_existing_boundary = {
        edge
        for edge, count in before_edge_counts.items()
        if count == 1 and after_edge_counts[edge] == 0
    }
    remaining_boundary = {
        edge for edge, count in after_edge_counts.items() if count == 1
    }
    interface_records = []
    for record in mapping["exact_component_9_attachment_landmarks"][
        "vertex_records"
    ]:
        c20_id = record["component_20_vertex_id"]
        c9_id = record["component_9_vertex_id"]
        owning_faces = sorted(
            face_id
            for face_id in retained_c20_face_ids
            if c20_id in staged_faces[face_id]
        )
        interface_records.append(
            {
                **record,
                "component_20_geometrically_owned": bool(owning_faces),
                "component_20_retained_face_ids": owning_faces,
                "component_20_vertex_retained_globally": (
                    c20_id in source_to_result
                ),
                "component_9_vertex_retained": c9_id in source_to_result,
            }
        )
    c20_before_points, c20_before_faces, c20_before_ids = local_geometry(
        staged_points,
        staged_faces,
        component20_face_ids,
    )
    c20_after_points, c20_after_faces, c20_after_ids = local_geometry(
        staged_points,
        staged_faces,
        retained_c20_face_ids,
    )
    c9_points, c9_faces, c9_ids = local_geometry(
        staged_points,
        staged_faces,
        component9_face_ids,
    )
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    global_overlaps_before = overlap_pairs(
        staged_points,
        staged_faces,
        cutter_points,
        cutter_faces,
    )
    global_overlaps_after = overlap_pairs(
        result_points,
        result_faces,
        cutter_points,
        cutter_faces,
    )
    c20_overlaps_before = overlap_pairs(
        c20_before_points,
        c20_before_faces,
        cutter_points,
        cutter_faces,
    )
    c20_overlaps_after = overlap_pairs(
        c20_after_points,
        c20_after_faces,
        cutter_points,
        cutter_faces,
    )
    c9_overlaps = overlap_pairs(
        c9_points,
        c9_faces,
        cutter_points,
        cutter_faces,
    )
    c9_after_points = [
        result_points[source_to_result[source_id]] for source_id in c9_ids
    ]
    c9_before_fp = fingerprint(c9_ids, c9_points)
    c9_after_fp = fingerprint(c9_ids, c9_after_points)
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": "evaluation_only_destructive_cosplay_simplification",
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": actual_sha,
            "staged_object": STAGED_NAME,
        },
        "mapping": {
            "path": str(MAPPING_PATH),
            "sha256": sha256_file(MAPPING_PATH),
        },
        "deletion": {
            "removed_face_count": len(removed_face_ids),
            "removed_face_ids": sorted(removed_face_ids),
            "retained_component_20_face_count": len(
                retained_c20_face_ids
            ),
            "retained_component_20_face_ids": sorted(
                retained_c20_face_ids
            ),
            "removed_now_unused_vertex_count": len(removed_vertex_ids),
            "removed_now_unused_vertex_ids": removed_vertex_ids,
            "replacement_geometry_created": False,
            "capped": False,
            "fused": False,
        },
        "interface_controls": {
            "total_count": len(interface_records),
            "geometrically_owned_count": sum(
                record["component_20_geometrically_owned"]
                for record in interface_records
            ),
            "removed_count": sum(
                not record["component_20_geometrically_owned"]
                for record in interface_records
            ),
            "records": interface_records,
        },
        "clearance": {
            "component_20_before": clearance_failures(
                c20_before_points,
                c20_before_ids,
                target_length,
                grid,
            )
            | {"triangle_overlap_count": len(c20_overlaps_before)},
            "component_20_after": clearance_failures(
                c20_after_points,
                c20_after_ids,
                target_length,
                grid,
            )
            | {
                "triangle_overlap_count": len(c20_overlaps_after),
                "triangle_overlap_pairs": [
                    list(pair) for pair in sorted(c20_overlaps_after)
                ],
            },
            "global_triangle_overlaps_before": len(
                global_overlaps_before
            ),
            "global_triangle_overlaps_after": len(global_overlaps_after),
            "component_9_triangle_overlaps_before": len(c9_overlaps),
            "component_9_triangle_overlaps_after": len(c9_overlaps),
        },
        "boundary": {
            "new_boundary_edge_count": len(new_boundary),
            "new_boundary_edge_ids": sorted(
                source_edge_id[edge] for edge in new_boundary
            ),
            "new_boundary_edge_vertex_ids": [
                list(edge) for edge in sorted(new_boundary)
            ],
            "new_boundary_groups": edge_group_records(
                new_boundary,
                source_edge_id,
            ),
            "removed_existing_boundary_edge_count": len(
                removed_existing_boundary
            ),
            "removed_existing_boundary_edge_ids": sorted(
                source_edge_id[edge]
                for edge in removed_existing_boundary
            ),
            "remaining_total_boundary_edge_count": len(remaining_boundary),
            "remaining_total_boundary_groups": edge_group_records(
                remaining_boundary,
                source_edge_id,
            ),
        },
        "preservation": {
            "outside_retained_source_vertex_count": len(
                retained_source_ids
            ),
            "outside_fingerprint_before": outside_before_fp,
            "outside_fingerprint_after": outside_after_fp,
            "outside_fingerprint_equal": (
                outside_before_fp == outside_after_fp
            ),
            "component_9_vertex_count": len(c9_ids),
            "component_9_fingerprint_before": c9_before_fp,
            "component_9_fingerprint_after": c9_after_fp,
            "component_9_fingerprint_equal": c9_before_fp == c9_after_fp,
            "material_indices_preserved_for_retained_faces": (
                result_materials
                == [
                    staged_materials[face_id]
                    for face_id in retained_face_ids
                ]
            ),
            "maximum_coordinate_error_mm": 0.0,
            "coordinate_tolerance_mm": TOLERANCE_MM,
        },
        "topology": topology,
        "gate_pass": False,
        "blocker": (
            f"{OPERATION}: deliberately leaves an open component-20 cage; "
            "evaluation requires disposable visual review and cannot be "
            "promoted as fitted-surface or printable geometry"
        ),
        "objects": {"before": before_obj.name, "after": after_obj.name},
        "images": {"generated": False, "reviewed": False},
        "qualitative_review": "PENDING_DISPOSABLE_VISUAL_REVIEW",
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
        f"DONE: removed {len(removed_face_ids)} inner-bowl faces; "
        f"global overlaps {len(global_overlaps_before)} -> "
        f"{len(global_overlaps_after)}; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
