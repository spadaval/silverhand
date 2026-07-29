"""Evaluate coordinated component-9/component-20 elbow-interface motion.

Two mapped sub-0.05 mm interface pairs receive identical pairwise motions so
their relative vectors remain exact while the component-20 anchors reach the
1.7 mm cutter floor. The same motions diffuse independently through the
smallest topology neighborhoods on components 9 and 20. The other thirteen
mapped interface vertices remain exact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

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
    expanded_distances,
    harmonic_displacement,
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
    validate_base,
)


OPERATION = "COORDINATED_ELBOW_INTERFACE"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
MAPPING_PATH = Path(
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_full_recon_map/mapping.json"
)
FLOOR_OFFSET_MM = 1.7
PAIR_IDS = [(2074, 1257), (2119, 1295)]
MAXIMUM_RINGS = 24
HARMONIC_ITERATIONS = 500
MINIMUM_EDGE_RATIO = 0.5
MAXIMUM_EDGE_RATIO = 2.0


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-base-sha256",
        default=EXPECTED_BASE_SHA256,
    )
    parser.add_argument(
        "--required-base-shape-key",
        default=EXPECTED_BASE_SHAPE_KEY,
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


def load_mapping() -> dict:
    path = (Path.cwd() / MAPPING_PATH).resolve()
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{OPERATION}: cannot read mapping authority '{path}': {error}"
        ) from error
    records = mapping["exact_component_9_attachment_landmarks"][
        "vertex_records"
    ]
    mapped = {
        (
            record["component_20_vertex_id"],
            record["component_9_vertex_id"],
        )
        for record in records
    }
    if not set(PAIR_IDS) <= mapped:
        raise RuntimeError(
            f"{OPERATION}: mapping authority lacks required pairs {PAIR_IDS}"
        )
    return mapping


def fingerprint(points: list[Vector], ids: list[int]) -> str:
    digest = hashlib.sha256()
    for index in ids:
        digest.update(struct.pack("<Qddd", index, *points[index]))
    return digest.hexdigest()


def topology_record(
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


def component_geometry(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    component: set[int],
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    ids = sorted(component)
    remap = {source_id: result_id for result_id, source_id in enumerate(ids)}
    component_faces = [
        tuple(remap[index] for index in face)
        for face in faces
        if face[0] in component
    ]
    return [points[index] for index in ids], component_faces


def component_overlap_count(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    component: set[int],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
) -> int:
    local_points, local_faces = component_geometry(points, faces, component)
    return len(
        overlap_pairs(
            local_points,
            local_faces,
            cutter_points,
            cutter_faces,
        )
    )


def component_overlap_pairs(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    component: set[int],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
) -> set[tuple[int, int]]:
    ids = sorted(component)
    remap = {source_id: result_id for result_id, source_id in enumerate(ids)}
    component_face_ids = [
        face_index
        for face_index, face in enumerate(faces)
        if face[0] in component
    ]
    component_faces = [
        tuple(remap[index] for index in faces[face_index])
        for face_index in component_face_ids
    ]
    local_points = [points[index] for index in ids]
    return {
        (component_face_ids[local_face_id], cutter_face_id)
        for local_face_id, cutter_face_id in overlap_pairs(
            local_points,
            component_faces,
            cutter_points,
            cutter_faces,
        )
    }


def overlap_pair_records(
    pairs: set[tuple[int, int]],
    rebuild_face_ids: set[int],
) -> list[dict]:
    return [
        {
            "candidate_face_id": candidate_face_id,
            "cutter_face_id": cutter_face_id,
            "candidate_face_in_liner_rebuild": (
                candidate_face_id in rebuild_face_ids
            ),
        }
        for candidate_face_id, cutter_face_id in sorted(pairs)
    ]


def build_variant(
    before: list[Vector],
    components: dict[int, set[int]],
    neighbors: list[list[int]],
    motions: dict[tuple[int, int], Vector],
    frozen: set[int],
    rings: int,
) -> tuple[list[Vector], set[int], list[dict]]:
    after = [point.copy() for point in before]
    affected = set()
    field_records = []
    for c20_vertex, c9_vertex in PAIR_IDS:
        motion = motions[(c20_vertex, c9_vertex)]
        for component_index, anchor in ((20, c20_vertex), (9, c9_vertex)):
            component = components[component_index]
            distances = expanded_distances(
                {anchor},
                component,
                neighbors,
                rings,
            )
            required = [0.0] * len(before)
            required[anchor] = 1.0
            weights = harmonic_displacement(
                required,
                {anchor},
                distances,
                neighbors,
                rings,
                HARMONIC_ITERATIONS,
            )
            local_affected = {
                index
                for index in distances
                if weights[index] > TOLERANCE_MM
                and (index not in frozen or index == anchor)
            }
            for index in local_affected:
                after[index] += motion * weights[index]
            affected.update(local_affected)
            field_records.append(
                {
                    "component": component_index,
                    "anchor_vertex_id": anchor,
                    "topology_rings": rings,
                    "transition_vertex_count": len(distances),
                    "affected_vertex_count": len(local_affected),
                }
            )
    # Pair cores receive exactly one common motion each, unaffected by the
    # other pair's transition field.
    for pair, motion in motions.items():
        after[pair[0]] = before[pair[0]] + motion
        after[pair[1]] = before[pair[1]] + motion
        affected.update(pair)
    return after, affected, field_records


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
    mapping = load_mapping()
    _, component_lists = connected_components(source)
    components = {
        9: set(component_lists[9]),
        20: set(component_lists[20]),
    }
    before, faces, material_indices = evaluated_geometry(candidate)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    interface_records = mapping[
        "exact_component_9_attachment_landmarks"
    ]["vertex_records"]
    all_interface_c20 = {
        record["component_20_vertex_id"] for record in interface_records
    }
    frozen = all_interface_c20 - {pair[0] for pair in PAIR_IDS}
    motions = {}
    for pair in PAIR_IDS:
        target = clamp_to_reserved_wall(
            before[pair[0]],
            target_length,
            grid,
            FLOOR_OFFSET_MM,
        )
        motions[pair] = target - before[pair[0]]

    before_global_overlaps = len(
        overlap_pairs(
            before,
            faces,
            cutter_points,
            cutter_faces,
        )
    )
    before_component_overlaps = {
        component_index: component_overlap_count(
            before,
            faces,
            component,
            cutter_points,
            cutter_faces,
        )
        for component_index, component in components.items()
    }
    before_component_overlap_pairs = {
        component_index: component_overlap_pairs(
            before,
            faces,
            component,
            cutter_points,
            cutter_faces,
        )
        for component_index, component in components.items()
    }
    before_cutter_failures = {
        index
        for index, margin in enumerate(before_margins)
        if margin < -TOLERANCE_MM
    }
    before_reserved_failures = {
        index
        for index, margin in enumerate(before_margins)
        if margin < RESERVED_WALL_MM - TOLERANCE_MM
    }
    edges = [tuple(edge.vertices) for edge in source.data.edges]
    attempts = []
    selected = None
    for rings in range(1, MAXIMUM_RINGS + 1):
        after, affected, fields = build_variant(
            before,
            components,
            neighbors,
            motions,
            frozen,
            rings,
        )
        margins = point_margins(after, target_length, grid)
        orientations = negative_orientation_locators(
            source,
            before,
            after,
            faces,
        )
        edge_quality = edge_ratio_distribution(
            before,
            after,
            edges,
            affected,
        )
        global_overlaps = len(
            overlap_pairs(
                after,
                faces,
                cutter_points,
                cutter_faces,
            )
        )
        component_overlaps = {
            component_index: component_overlap_count(
                after,
                faces,
                component,
                cutter_points,
                cutter_faces,
            )
            for component_index, component in components.items()
        }
        new_cutter_failures = sorted(
            {
                index
                for index, margin in enumerate(margins)
                if margin < -TOLERANCE_MM
            }
            - before_cutter_failures
        )
        new_reserved_failures = sorted(
            {
                index
                for index, margin in enumerate(margins)
                if margin < RESERVED_WALL_MM - TOLERANCE_MM
            }
            - before_reserved_failures
        )
        pair_records = []
        pair_gate = True
        for pair in PAIR_IDS:
            before_vector = before[pair[1]] - before[pair[0]]
            after_vector = after[pair[1]] - after[pair[0]]
            vector_error = (after_vector - before_vector).length
            distance = after_vector.length
            anchor_margin = margins[pair[0]]
            pair_gate = (
                pair_gate
                and vector_error <= TOLERANCE_MM
                and distance < 0.05
                and anchor_margin >= FLOOR_OFFSET_MM - TOLERANCE_MM
            )
            pair_records.append(
                {
                    "component_20_vertex_id": pair[0],
                    "component_9_vertex_id": pair[1],
                    "common_motion": [
                        round(value, 6) for value in motions[pair]
                    ],
                    "motion_mm": round(motions[pair].length, 6),
                    "anchor_margin_mm": round(anchor_margin, 6),
                    "before_pair_distance_mm": round(
                        before_vector.length,
                        6,
                    ),
                    "after_pair_distance_mm": round(distance, 6),
                    "relative_vector_error_mm": round(
                        vector_error,
                        9,
                    ),
                }
            )
        frozen_displacements = {
            index: (after[index] - before[index]).length
            for index in sorted(frozen)
            if (after[index] - before[index]).length > TOLERANCE_MM
        }
        gate = all(
            (
                pair_gate,
                orientations["count"] == 0,
                edge_quality["minimum"] >= MINIMUM_EDGE_RATIO,
                edge_quality["maximum"] <= MAXIMUM_EDGE_RATIO,
                not new_cutter_failures,
                not new_reserved_failures,
                global_overlaps <= before_global_overlaps,
                component_overlaps[9]
                <= before_component_overlaps[9],
                component_overlaps[20]
                <= before_component_overlaps[20],
                not frozen_displacements,
            )
        )
        record = {
            "topology_rings": rings,
            "fields": fields,
            "affected_vertex_count": len(affected),
            "pairs": pair_records,
            "negative_orientation_count": orientations["count"],
            "edge_ratio": edge_quality,
            "global_overlaps": global_overlaps,
            "component_overlaps": component_overlaps,
            "new_cutter_failure_ids": new_cutter_failures,
            "new_reserved_failure_ids": new_reserved_failures,
            "frozen_interface_displacements_mm": frozen_displacements,
            "gate_pass": gate,
        }
        attempts.append(record)
        if gate:
            selected = (after, affected, record, orientations)
            break

    if selected is None:
        least_bad = min(
            attempts,
            key=lambda record: (
                record["negative_orientation_count"],
                len(record["new_reserved_failure_ids"]),
                max(
                    0.0,
                    MINIMUM_EDGE_RATIO - record["edge_ratio"]["minimum"],
                    record["edge_ratio"]["maximum"] - MAXIMUM_EDGE_RATIO,
                ),
                max(
                    0,
                    record["global_overlaps"] - before_global_overlaps,
                ),
            ),
        )
        after, affected, _, orientations = build_variant(
            before,
            components,
            neighbors,
            motions,
            frozen,
            least_bad["topology_rings"],
        ) + (None,)
        orientations = negative_orientation_locators(
            source,
            before,
            after,
            faces,
        )
        selected_record = least_bad
        feasible = False
    else:
        after, affected, selected_record, orientations = selected
        feasible = True

    unchanged_ids = sorted(set(range(len(before))) - affected)
    before_fp = fingerprint(before, unchanged_ids)
    after_fp = fingerprint(after, unchanged_ids)
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
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    topology = topology_record(before_obj, after_obj)
    after_component_overlap_pairs = {
        component_index: component_overlap_pairs(
            after,
            faces,
            component,
            cutter_points,
            cutter_faces,
        )
        for component_index, component in components.items()
    }
    rebuild_face_ids = set(
        mapping["reconstruction_scope"]["rebuild_face_ids"]
    )
    component_overlap_deltas = {}
    for component_index in sorted(components):
        added = (
            after_component_overlap_pairs[component_index]
            - before_component_overlap_pairs[component_index]
        )
        removed = (
            before_component_overlap_pairs[component_index]
            - after_component_overlap_pairs[component_index]
        )
        component_overlap_deltas[str(component_index)] = {
            "added": overlap_pair_records(added, rebuild_face_ids),
            "removed": overlap_pair_records(removed, rebuild_face_ids),
            "added_count": len(added),
            "removed_count": len(removed),
            "net_count_delta": len(added) - len(removed),
        }
    added_c20 = component_overlap_deltas["20"]["added"]
    added_c20_all_in_rebuild = all(
        record["candidate_face_in_liner_rebuild"] for record in added_c20
    )
    gate_pass = all(
        (
            feasible,
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edge_delta"] == 0,
            before_fp == after_fp,
        )
    )
    conditional_pass = all(
        (
            not gate_pass,
            selected_record["topology_rings"] == 3,
            selected_record["negative_orientation_count"] == 0,
            selected_record["edge_ratio"]["minimum"] >= MINIMUM_EDGE_RATIO,
            selected_record["edge_ratio"]["maximum"] <= MAXIMUM_EDGE_RATIO,
            not selected_record["new_cutter_failure_ids"],
            not selected_record["new_reserved_failure_ids"],
            selected_record["global_overlaps"] <= before_global_overlaps,
            selected_record["component_overlaps"][9]
            <= before_component_overlaps[9],
            not selected_record["frozen_interface_displacements_mm"],
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edge_delta"] == 0,
            before_fp == after_fp,
            bool(added_c20),
            added_c20_all_in_rebuild,
        )
    )
    displacements = [
        (after[index] - before[index]).length for index in affected
    ]
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if gate_pass
            else (
                "CONDITIONAL_PASS_FOR_COMBINED_LINER_STAGE"
                if conditional_pass
                else "evaluation_only_shared_band_infeasible"
            )
        ),
        "repair_base": repair_base,
        "selection": {
            "component_20": 20,
            "component_9": 9,
            "pair_ids": [list(pair) for pair in PAIR_IDS],
            "frozen_other_interface_vertex_ids": sorted(frozen),
            "floor_offset_mm": FLOOR_OFFSET_MM,
            "selected_topology_rings": selected_record["topology_rings"],
        },
        "baseline": {
            "global_overlaps": before_global_overlaps,
            "component_overlaps": before_component_overlaps,
        },
        "bounded_attempts": attempts,
        "selected_result": selected_record,
        "overlap_pair_audit": {
            "mapping_authority": str(MAPPING_PATH),
            "liner_rebuild_face_count": len(rebuild_face_ids),
            "component_pair_deltas": component_overlap_deltas,
            "all_added_component_20_faces_in_liner_rebuild": (
                added_c20_all_in_rebuild
            ),
        },
        "distortion": {
            "affected_vertex_count": len(affected),
            "displacement_mm": distribution(displacements),
            "negative_orientation": orientations,
        },
        "topology": topology,
        "preservation": {
            "outside_fingerprint_before": before_fp,
            "outside_fingerprint_after": after_fp,
            "outside_fingerprint_equal": before_fp == after_fp,
        },
        "gate_pass": gate_pass,
        "conditional_pass_for_combined_liner_stage": conditional_pass,
        "blocker": (
            None
            if gate_pass or conditional_pass
            else (
                f"{OPERATION}: no topology neighborhood from 1 through "
                f"{MAXIMUM_RINGS} preserves both shared-pair controls, the "
                "other 13 frozen interface vertices, orientation, edge "
                "quality, clearance-failure sets, and overlap nonincrease"
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
        f"DONE: coordinated elbow interface status={report['status']}; "
        f"standalone_gate_pass={gate_pass}; promotion remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
