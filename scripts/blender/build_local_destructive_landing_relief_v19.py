"""Resolve v19 landing masks and stop safely when hard bounds are invalid."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from math import degrees
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402


OPERATION = "LOCAL_DESTRUCTIVE_LANDING_RELIEF_V19"
AUTHORITY_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
MAXIMUM_RADIUS_MM = 8.0
RIDGE_LIMIT_DEGREES = 35.0
BRANCH_A_EXCLUSION_MM = 6.0
PRIMARY = {
    "name": "primary",
    "upper_endpoint": 1780,
    "lower_endpoint": 1789,
    "upper_seed_faces": [5773, 8706],
    "lower_seed_faces": [2667, 9174, 9176, 9177, 9178],
    "initial_displacement_mm": 1.35,
    "cap_mm": 1.60,
}
FALLBACK = {
    "name": "fallback",
    "upper_endpoint": 1781,
    "lower_endpoint": 1789,
    "upper_seed_faces": [5773, 9132],
    "lower_seed_faces": [2667, 9174, 9176, 9177, 9178],
    "initial_displacement_mm": 1.45,
    "cap_mm": 1.75,
}


def stable_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def public_coordinates(vertex_ids, points):
    return [
        {
            "source_vertex_id": source_id,
            "coordinate_mm": [round(value, 9) for value in points[source_id]],
        }
        for source_id in vertex_ids
    ]


def polygon_normal(points, face):
    origin = points[face[0]]
    result = (points[face[1]] - origin).cross(points[face[2]] - origin)
    return result.normalized()


def resolve_patch(
    role,
    endpoint,
    seed_faces,
    terminal_ids,
    branch_a_endpoint,
    retained_faces,
    staged_points,
    staged_faces,
    staged_materials,
    face_neighbors,
    shared_edge,
    open_edges,
):
    seed_materials = {staged_materials[face_id] for face_id in seed_faces}
    reasons = []
    if len(seed_materials) != 1:
        reasons.append("seed_faces_cross_material_boundary")
    seed_material = min(seed_materials)

    def face_reasons(face_id):
        result = []
        face = staged_faces[face_id]
        if face_id not in retained_faces:
            result.append("not_retained")
        if not set(face) <= terminal_ids:
            result.append("outside_named_terminal_or_T2_T3")
        distances = [
            (staged_points[vertex] - staged_points[endpoint]).length
            for vertex in face
        ]
        if max(distances) > MAXIMUM_RADIUS_MM + 1.0e-6:
            result.append("vertex_beyond_8mm")
        if staged_materials[face_id] != seed_material:
            result.append("material_boundary")
        if any(
            (
                staged_points[vertex]
                - staged_points[branch_a_endpoint]
            ).length
            < BRANCH_A_EXCLUSION_MM - 1.0e-6
            for vertex in face
        ):
            result.append("branch_a_landing_footprint")
        if endpoint == 1789 and 1784 in face:
            result.append("immutable_V1784_in_moving_face")
        return result

    seed_validation = {
        str(face_id): {
            "vertices": list(staged_faces[face_id]),
            "endpoint_distances_mm": [
                round(
                    (
                        staged_points[vertex]
                        - staged_points[endpoint]
                    ).length,
                    6,
                )
                for vertex in staged_faces[face_id]
            ],
            "reasons": face_reasons(face_id),
        }
        for face_id in seed_faces
    }
    for face_id, validation in seed_validation.items():
        reasons.extend(
            f"seed_F{face_id}:{reason}" for reason in validation["reasons"]
        )
    rings = [set(seed_faces)]
    crossing_rejections = []
    for distance in (1, 2):
        ring = set()
        for face_id in rings[-1]:
            for neighbor in face_neighbors[face_id]:
                if neighbor in set().union(*rings):
                    continue
                edge = shared_edge[(face_id, neighbor)]
                edge_key = tuple(sorted(edge))
                local_reasons = face_reasons(neighbor)
                if edge_key in open_edges:
                    local_reasons.append("source_open_edge")
                first_normal = polygon_normal(
                    staged_points,
                    staged_faces[face_id],
                )
                second_normal = polygon_normal(
                    staged_points,
                    staged_faces[neighbor],
                )
                ridge = degrees(first_normal.angle(second_normal))
                if ridge >= RIDGE_LIMIT_DEGREES:
                    local_reasons.append("ridge_at_or_above_35deg")
                if local_reasons:
                    crossing_rejections.append(
                        {
                            "from_face_id": face_id,
                            "candidate_face_id": neighbor,
                            "shared_edge": list(edge_key),
                            "ridge_degrees": round(ridge, 6),
                            "reasons": sorted(set(local_reasons)),
                        }
                    )
                else:
                    ring.add(neighbor)
        rings.append(ring)
    core, transition, anchor = rings
    patch_faces = sorted(core | transition | anchor)
    patch_vertices = sorted(
        {
            vertex
            for face_id in patch_faces
            for vertex in staged_faces[face_id]
        }
    )
    movable_vertices = sorted(
        {
            vertex
            for face_id in core | transition
            for vertex in staged_faces[face_id]
        }
        - {
            vertex
            for face_id in anchor
            for vertex in staged_faces[face_id]
        }
    )
    if endpoint not in movable_vertices:
        reasons.append("endpoint_not_in_movable_core_transition")
    if 1784 in movable_vertices:
        reasons.append("immutable_V1784_would_move")
    if not anchor:
        reasons.append("empty_anchor_ring")
    return {
        "role": role,
        "endpoint_source_vertex_id": endpoint,
        "seed_face_ids": seed_faces,
        "seed_validation": seed_validation,
        "core_face_ids": sorted(core),
        "transition_face_ids": sorted(transition),
        "anchor_face_ids": sorted(anchor),
        "patch_face_ids": patch_faces,
        "patch_vertex_ids": patch_vertices,
        "movable_vertex_ids": movable_vertices,
        "crossing_rejections": crossing_rejections,
        "valid": not reasons,
        "invalid_reasons": sorted(set(reasons)),
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    context = v17.baseline_context()
    if context["blend_sha"] != AUTHORITY_SHA256:
        raise RuntimeError(
            f"{OPERATION}: input Blend SHA '{context['blend_sha']}', "
            f"expected '{AUTHORITY_SHA256}'"
        )
    v13_report = json.loads(v16_report_path().read_text(encoding="utf-8"))
    terminal_ids = {
        terminal["terminal_id"]: set(terminal["source_vertex_ids"])
        for terminal in v13_report["terminals"]
    }
    retained_faces = set(context["retained_face_ids"])
    staged_faces = context["staged_faces"]
    edge_faces = defaultdict(list)
    for face_id in retained_faces:
        face = staged_faces[face_id]
        for index, first in enumerate(face):
            second = face[(index + 1) % len(face)]
            edge_faces[tuple(sorted((first, second)))].append(face_id)
    face_neighbors = defaultdict(set)
    shared_edge = {}
    for edge, face_ids in edge_faces.items():
        if len(face_ids) != 2:
            continue
        first, second = face_ids
        face_neighbors[first].add(second)
        face_neighbors[second].add(first)
        shared_edge[(first, second)] = edge
        shared_edge[(second, first)] = edge
    mapping = context["mapping"]
    open_edges = {
        tuple(sorted(edge))
        for group in mapping["exact_source_open_edges"]["groups"]
        for edge in group["edge_vertex_ids"]
    }
    attempts = []
    for specification in (PRIMARY, FALLBACK):
        upper = resolve_patch(
            f"{specification['name']}_upper",
            specification["upper_endpoint"],
            specification["upper_seed_faces"],
            terminal_ids["T_CAGE_1"],
            5702,
            retained_faces,
            context["staged_points"],
            staged_faces,
            context["staged_materials"],
            face_neighbors,
            shared_edge,
            open_edges,
        )
        lower = resolve_patch(
            f"{specification['name']}_lower",
            specification["lower_endpoint"],
            specification["lower_seed_faces"],
            terminal_ids["T_CAGE_0"],
            1784,
            retained_faces,
            context["staged_points"],
            staged_faces,
            context["staged_materials"],
            face_neighbors,
            shared_edge,
            open_edges,
        )
        patch_vertices = sorted(
            set(upper["patch_vertex_ids"]) | set(lower["patch_vertex_ids"])
        )
        complement_vertices = sorted(
            set(context["retained_ids"]) - set(patch_vertices)
        )
        patch_faces = sorted(
            set(upper["patch_face_ids"]) | set(lower["patch_face_ids"])
        )
        checkpoint = {
            "patch_vertex_ids": patch_vertices,
            "patch_coordinates": public_coordinates(
                patch_vertices,
                context["staged_points"],
            ),
            "patch_face_ids": patch_faces,
            "patch_faces": [
                {
                    "source_face_id": face_id,
                    "vertices": list(staged_faces[face_id]),
                    "material_index": context["staged_materials"][face_id],
                }
                for face_id in patch_faces
            ],
            "complement_vertex_ids": complement_vertices,
            "complement_coordinates": public_coordinates(
                complement_vertices,
                context["staged_points"],
            ),
        }
        checkpoint["patch_fingerprint"] = stable_hash(
            {
                "coordinates": checkpoint["patch_coordinates"],
                "faces": checkpoint["patch_faces"],
            }
        )
        checkpoint["complement_fingerprint"] = stable_hash(
            checkpoint["complement_coordinates"]
        )
        valid = upper["valid"] and lower["valid"]
        attempts.append(
            {
                "pair": specification,
                "upper_patch": upper,
                "lower_patch": lower,
                "original_checkpoint": checkpoint,
                "mask_gate_pass": valid,
                "displacement_attempted": False,
                "construction_attempted": False,
                "geometry_emitted": False,
            }
        )
        if valid:
            raise RuntimeError(
                f"{OPERATION}: mask unexpectedly valid; bounded relief "
                "construction implementation is required before mutation"
            )
    status = "NO_SAFE_LOCAL_LANDING_RELIEF"
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "authority_recovery": context["checks"],
        "attempts": attempts,
        "stop_reason": (
            "The fixed V1789 lower CORE_FACES violate the <=8 mm all-vertex "
            "mask before mutation; primary and exact fallback share that "
            "lower mask."
        ),
        "source_coordinates_changed": False,
        "geometry_emitted": False,
        "blend_saved_by_script": False,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "primary_mask_gate": attempts[0]["mask_gate_pass"],
                "fallback_mask_gate": attempts[1]["mask_gate_pass"],
                "source_coordinates_changed": False,
                "geometry_emitted": False,
                "blend_saved_by_script": False,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        "DONE: v19 mask preflight status=NO_SAFE_LOCAL_LANDING_RELIEF; "
        "geometry_emitted=False; blend_saved_by_script=False"
    )
    return 0


def v16_report_path():
    return (
        SCRIPT_DIR.parent.parent
        / "_validation/experiments/geometry_repair/component_20_methods"
        / "repair_014_distinct_cage_terminals_v13/build_report.json"
    )


if __name__ == "__main__":
    raise SystemExit(main())
