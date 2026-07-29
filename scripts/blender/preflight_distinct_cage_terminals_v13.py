"""Identify explicit retained-cage terminal islands for Repair 014 v13."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_broad_constituent_network_v9 as v9  # noqa: E402
import preflight_b2_sharp_turn_split_v11 as v11  # noqa: E402
import preflight_direction_field_network_v10 as v10  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "DISTINCT_CAGE_TERMINALS_V13"
REPRESENTATIVE_GROUPS = {
    "representative_2020": [2020],
    "representatives_2007_3924": [2007, 3924],
    "representatives_5702_1784": [5702, 1784],
    "representatives_4875_4877": [4875, 4877],
    "hard_controls_5840_5852": [5840, 5852],
}


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def mesh_components(
    vertex_count: int,
    faces: list[tuple[int, ...]],
) -> list[dict]:
    neighbors = [set() for _ in range(vertex_count)]
    for face in faces:
        for first, second in zip(face, face[1:] + face[:1]):
            neighbors[first].add(second)
            neighbors[second].add(first)
    unseen = set(range(vertex_count))
    components = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        stack = [start]
        vertices = {start}
        while stack:
            current = stack.pop()
            for neighbor in neighbors[current]:
                if neighbor not in unseen:
                    continue
                unseen.remove(neighbor)
                vertices.add(neighbor)
                stack.append(neighbor)
        components.append({"vertices": sorted(vertices)})
    vertex_component = {}
    for component_id, component in enumerate(components):
        for vertex in component["vertices"]:
            vertex_component[vertex] = component_id
    faces_by_component = defaultdict(list)
    for face_id, face in enumerate(faces):
        component_id = vertex_component[face[0]]
        if any(vertex_component[index] != component_id for index in face):
            raise RuntimeError(
                f"{OPERATION}: retained face {face_id} crosses components"
            )
        faces_by_component[component_id].append(face_id)
    for component_id, component in enumerate(components):
        component["faces"] = faces_by_component[component_id]
    return components


def local_component_geometry(points, faces, component):
    vertex_ids = component["vertices"]
    remap = {
        source: local for local, source in enumerate(vertex_ids)
    }
    return (
        [points[index].copy() for index in vertex_ids],
        [
            tuple(remap[index] for index in faces[face_id])
            for face_id in component["faces"]
        ],
    )


def rounded_vector(vector):
    return [round(value, 6) for value in vector]


def main() -> int:
    report_path = report_argument()
    blend_path = Path(bpy.data.filepath).resolve()
    input_sha = v10.sha256_file(blend_path)
    expected_sha = v4.v2.EXPECTED_BLEND_SHA256
    if input_sha != expected_sha:
        raise RuntimeError(
            f"{OPERATION}: input Blend '{blend_path}' has SHA-256 "
            f"'{input_sha}', expected clean open-cage '{expected_sha}'"
        )
    staged = bpy.data.objects[v4.v2.base.STAGED_NAME]
    open_cage = bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    staged_points, staged_faces, staged_materials = evaluated_geometry(staged)
    open_points, open_faces, open_materials = evaluated_geometry(open_cage)
    mapping = json.loads(
        v4.v2.MAPPING_PATH.read_text(encoding="utf-8")
    )
    removed_faces = set(
        mapping["reconstruction_scope"]["rebuild_face_ids"]
    )
    (
        full_open_points,
        full_open_faces,
        full_open_materials,
        full_open_source_ids,
        source_to_open,
    ) = v4.v2.remap_retained(
        staged_points,
        staged_faces,
        staged_materials,
        removed_faces,
    )
    maximum_coordinate_error = max(
        (first - second).length
        for first, second in zip(full_open_points, open_points)
    )
    full_open_exact = all(
        (
            full_open_faces == open_faces,
            full_open_materials == open_materials,
            maximum_coordinate_error <= 1.0e-4,
        )
    )
    if not full_open_exact:
        raise RuntimeError(
            f"{OPERATION}: full open-scene reconstruction disagrees with "
            f"'{open_cage.name}'; faces={len(full_open_faces)}, "
            f"maximum_coordinate_error={maximum_coordinate_error:.9f} mm"
        )
    retained_face_ids = sorted(
        mapping["reconstruction_scope"]["retain_face_ids"]
    )
    retained_source_ids = sorted(
        {
            vertex
            for face_id in retained_face_ids
            for vertex in staged_faces[face_id]
        }
    )
    source_to_retained = {
        source_id: local_id
        for local_id, source_id in enumerate(retained_source_ids)
    }
    retained_points = [
        staged_points[source_id].copy()
        for source_id in retained_source_ids
    ]
    retained_faces = [
        tuple(
            source_to_retained[vertex]
            for vertex in staged_faces[face_id]
        )
        for face_id in retained_face_ids
    ]
    _retained_materials = [
        staged_materials[face_id] for face_id in retained_face_ids
    ]
    open_face_by_source_face = {
        source_face_id: open_face_id
        for open_face_id, source_face_id in enumerate(
            face_id
            for face_id in range(len(staged_faces))
            if face_id not in removed_faces
        )
    }
    subset_matches_open = all(
        open_faces[open_face_by_source_face[face_id]]
        == tuple(
            source_to_open[vertex]
            for vertex in staged_faces[face_id]
        )
        and open_materials[open_face_by_source_face[face_id]]
        == staged_materials[face_id]
        for face_id in retained_face_ids
    )
    cage_exact = all(
        (
            len(retained_faces) == 1409,
            full_open_exact,
            subset_matches_open,
        )
    )
    components = mesh_components(len(retained_points), retained_faces)
    if len(components) != 4:
        raise RuntimeError(
            f"{OPERATION}: exact retained cage has {len(components)} "
            "connected components, expected 4"
        )
    components.sort(
        key=lambda component: min(
            retained_source_ids[index]
            for index in component["vertices"]
        )
    )
    source_terminal = {}
    terminals = []
    for terminal_index, component in enumerate(components):
        terminal_id = f"T_CAGE_{terminal_index}"
        source_ids = [
            retained_source_ids[index]
            for index in component["vertices"]
        ]
        points = [
            retained_points[index] for index in component["vertices"]
        ]
        centroid = sum(points, Vector()) / len(points)
        minimum = Vector(
            tuple(min(point[axis] for point in points) for axis in range(3))
        )
        maximum = Vector(
            tuple(max(point[axis] for point in points) for axis in range(3))
        )
        for source_id in source_ids:
            source_terminal[source_id] = terminal_id
        terminals.append(
            {
                "terminal_id": terminal_id,
                "stable_order_key_minimum_source_vertex_id": min(source_ids),
                "vertex_count": len(component["vertices"]),
                "face_count": len(component["faces"]),
                "source_vertex_ids": source_ids,
                "centroid_mm": rounded_vector(centroid),
                "bounds_mm": {
                    "minimum": rounded_vector(minimum),
                    "maximum": rounded_vector(maximum),
                    "extent": rounded_vector(maximum - minimum),
                },
                "_component": component,
            }
        )
    representative_classification = {}
    for group, source_ids in REPRESENTATIVE_GROUPS.items():
        representative_classification[group] = [
            {
                "source_vertex_id": source_id,
                "retained": source_id in source_to_retained,
                "terminal_id": source_terminal.get(source_id),
            }
            for source_id in source_ids
        ]
    for terminal in terminals:
        terminal["representative_groups"] = sorted(
            group
            for group, records in representative_classification.items()
            if any(
                record["terminal_id"] == terminal["terminal_id"]
                for record in records
            )
        )
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    route = [staged_points[index] for index in centerline_ids]
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    grid, _ = v4.cutter_grid(cutter)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    route_samples, node_ring, _ = v4.obstacle_following_sample_route(
        route,
        target_length,
        grid,
        extend_ends=False,
    )
    v9.GLOBAL_ROUTE.clear()
    v9.GLOBAL_ROUTE.update({"target_length_mm": target_length})
    c9_points, c9_faces = v4.component9_geometry()
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    original_geometry = v9.candidate_geometry
    v9.candidate_geometry = v10.directed_candidate_geometry
    try:
        b0 = v11.evaluate(
            "B0",
            route_samples[node_ring[0] : node_ring[6] + 3],
            210,
            8.0,
            90,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
        )
    finally:
        v9.candidate_geometry = original_geometry
    b0_landings = []
    for terminal in terminals:
        points, faces = local_component_geometry(
            retained_points,
            retained_faces,
            terminal["_component"],
        )
        pairs = overlap_pairs(
            b0["_points"],
            b0["_faces"],
            points,
            faces,
        )
        b0_landings.append(
            {
                "terminal_id": terminal["terminal_id"],
                "triangle_overlap_count": len(pairs),
            }
        )
    total_b0_overlaps = sum(
        record["triangle_overlap_count"] for record in b0_landings
    )
    full_open_pairs = overlap_pairs(
        b0["_points"],
        b0["_faces"],
        open_points,
        open_faces,
    )
    retained_open_face_ids = {
        open_face_by_source_face[face_id]
        for face_id in retained_face_ids
    }
    retained_pair_count = sum(
        open_face_id in retained_open_face_ids
        for _, open_face_id in full_open_pairs
    )
    source = bpy.data.objects[v4.SOURCE_NAME]
    source_vertex_component, source_components = v4.connected_components(
        source
    )
    nonterminal_by_source_component = defaultdict(int)
    for _, open_face_id in full_open_pairs:
        if open_face_id in retained_open_face_ids:
            continue
        open_vertex_id = open_faces[open_face_id][0]
        source_vertex_id = full_open_source_ids[open_vertex_id]
        source_component_id = source_vertex_component[source_vertex_id]
        nonterminal_by_source_component[source_component_id] += 1
    nonterminal_component_records = [
        {
            "source_component_id": component_id,
            "source_component_vertex_count": len(
                source_components[component_id]
            ),
            "triangle_overlap_count": count,
        }
        for component_id, count in sorted(
            nonterminal_by_source_component.items()
        )
    ]
    full_overlap_reconciled = all(
        (
            len(full_open_pairs) == 152,
            retained_pair_count == total_b0_overlaps,
            total_b0_overlaps
            + sum(
                record["triangle_overlap_count"]
                for record in nonterminal_component_records
            )
            == len(full_open_pairs),
        )
    )
    terminal_public = [
        {
            key: value
            for key, value in terminal.items()
            if not key.startswith("_")
        }
        for terminal in terminals
    ]
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": "numeric_preflight_complete",
        "input_blend": str(blend_path),
        "input_blend_sha256": input_sha,
        "retained_cage": {
            "object": open_cage.name,
            "face_count": len(retained_faces),
            "vertex_count": len(retained_points),
            "material_sequence_exact": subset_matches_open,
            "maximum_coordinate_error_mm": round(
                maximum_coordinate_error,
                9,
            ),
            "exact": cage_exact,
            "connected_component_count": len(components),
        },
        "terminals": terminal_public,
        "representative_classification": representative_classification,
        "v12_B0": {
            "candidate": {
                "direction_degrees": 210,
                "offset_mm": 8.0,
                "roll_degrees": 90,
            },
            "machine_gate_pass": b0["gate_pass"],
            "expected_total_cage_overlap_count": 152,
            "measured_full_open_scene_overlap_count": len(full_open_pairs),
            "measured_retained_terminal_overlap_count": total_b0_overlaps,
            "measured_nonterminal_overlap_count": (
                len(full_open_pairs) - retained_pair_count
            ),
            "reconciles_with_v12": full_overlap_reconciled,
            "terminal_landings": b0_landings,
            "hit_terminal_ids": [
                record["terminal_id"]
                for record in b0_landings
                if record["triangle_overlap_count"] > 0
            ],
            "nonterminal_source_component_hits": (
                nonterminal_component_records
            ),
            "landing_conclusion": (
                "v12 B0 hits no retained-cage terminal; its 152 reported "
                "open-scene overlaps are entirely non-terminal"
                if total_b0_overlaps == 0 and len(full_open_pairs) == 152
                else "see explicit terminal and nonterminal attribution"
            ),
        },
        "future_graph_contract": {
            "terminal_nodes": [
                terminal["terminal_id"] for terminal in terminal_public
            ],
            "required": (
                "measured path between two distinct selected major "
                "terminal IDs"
            ),
            "selected_major_terminal_ids": [],
            "selection_status": "AWAITING_VISUAL_ROLE_MAPPING",
            "abstract_B_root_retired": True,
            "v12_abstract_cage_root_gate_valid": False,
            "invalid_reason": (
                "v12 measured B0 against the full 11,840-face open-scene "
                "object, not the explicit 1,409-face retained-cage terminals"
            ),
            "geometry_emission_allowed": False,
        },
        "gates": {
            "retained_1409_face_cage_exact": cage_exact,
            "four_explicit_terminal_components": len(components) == 4,
            "all_requested_representatives_accounted_for": all(
                (
                    record["terminal_id"] is not None
                    if record["retained"]
                    else record["terminal_id"] is None
                )
                for records in representative_classification.values()
                for record in records
            ),
            "v12_B0_machine_candidate_reconstructed": b0["gate_pass"],
            "v12_B0_overlap_reconciled": full_overlap_reconciled,
            "v12_B0_hits_retained_terminal": total_b0_overlaps > 0,
            "geometry_not_emitted": True,
        },
        "gate_pass": False,
        "gate_pass_reason": (
            "numeric preflight passes; production graph remains blocked "
            "until two distinct major terminal IDs are selected"
        ),
        "geometry_emitted": False,
        "qualitative_review": "NOT_REQUESTED",
        "promotion": "NOT_PROMOTED",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if "--save" in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(
        json.dumps(
            {
                "tool": Path(__file__).name,
                "terminal_summaries": [
                    {
                        "terminal_id": terminal["terminal_id"],
                        "vertex_count": terminal["vertex_count"],
                        "face_count": terminal["face_count"],
                        "representative_groups": terminal[
                            "representative_groups"
                        ],
                    }
                    for terminal in terminal_public
                ],
                "B0_landings": b0_landings,
                "geometry_emitted": False,
            },
            indent=2,
        )
    )
    print(
        "DONE: v13 explicit-terminal numeric preflight; "
        "geometry_emitted=False; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
