#!/usr/bin/env python3
"""Analyze a finite read-only C9 landing-clearance reconstruction family."""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import product
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_v27_local_gap_family as local  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402


OPERATION = "ANALYZE_V27_C9_LANDING"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
FULL_AUTHORITY = V27 / "v27_local_gap_full_exhaustion_authority.json"
FULL_RECEIPT = V27 / "v27_local_gap_full_exhaustion_receipt.json"
FAMILY_AUTHORITY = V27 / "v27_local_gap_family_authority.json"
AGGREGATE_AUTHORITY = V27 / "v27_aggregate_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_landing_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_landing_authority_receipt.json"
SOURCE_OBJECT = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
CUTTER_OBJECT = "CUT_CLEARANCE_ANATOMY_STRAIGHT"
TARGET_EDGE_ID = 12916
TARGET_VERTEX_IDS = (1541, 1543)
TARGET_CHAIN_ID = "LOCAL_GAP_C9_CHAIN_EB7E82AAC63863FF"
MINIMUM_CLEARANCE_MM = 1.7
TOLERANCE_MM = 1e-7
SAMPLE_SPACING_MM = 1.0
LANDING_FACE_MASK = {
    2227,
    2228,
    2230,
    2231,
    2232,
    2235,
    2239,
    2240,
    2243,
    2244,
    2245,
}
OFFSET_VALUES_MM = [0, 1, 1.7, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30]
BLEND_WEIGHTS = [0, 0.25, 0.5, 0.75, 1.0]
ROTATION_DEGREES = [0, -15, 15, -30, 30]

FROZEN_HASHES = {
    "full_exhaustion_authority": (
        FULL_AUTHORITY,
        "c1212eff5367b58c9450bfae0caeddaf6a7efcc0a163a3b096d4175b097abdc3",
    ),
    "full_exhaustion_receipt": (
        FULL_RECEIPT,
        "70c0ed4e3f677d391b4287052d6b5c4b5725bccc9cfc11aa73e86da58e15fadd",
    ),
    "local_gap_family_authority": (
        FAMILY_AUTHORITY,
        "14eccf5706d6325901cb9a025ca16a8cb8898dd190be672863c308403f06866d",
    ),
    "aggregate_authority": (
        AGGREGATE_AUTHORITY,
        "43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338",
    ),
}


def add(left: Iterable[float], right: Iterable[float]) -> list[float]:
    return [a + b for a, b in zip(left, right, strict=True)]


def sub(left: Iterable[float], right: Iterable[float]) -> list[float]:
    return [a - b for a, b in zip(left, right, strict=True)]


def scale(vector: Iterable[float], amount: float) -> list[float]:
    return [value * amount for value in vector]


def dot(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def length(vector: Iterable[float]) -> float:
    return math.sqrt(dot(vector, vector))


def normalized(vector: Iterable[float], label: str) -> list[float]:
    values = list(vector)
    magnitude = length(values)
    if magnitude <= TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_FRAME_DEGENERATE; {label}"
        )
    return scale(values, 1.0 / magnitude)


def interpolate(
    start: list[float], end: list[float], parameter: float
) -> list[float]:
    return add(start, scale(sub(end, start), parameter))


def matrix_is_identity(matrix: Any) -> bool:
    return all(
        abs(float(matrix[row][column]) - (1.0 if row == column else 0.0))
        <= 1e-7
        for row in range(4)
        for column in range(4)
    )


def cutter_geometry(
    cutter: bpy.types.Object,
) -> tuple[
    list[list[float]],
    list[tuple[int, int, int]],
    list[list[list[float]]],
    BVHTree,
]:
    evaluated = cutter.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix = cutter.matrix_world
        points = [
            [float(value) for value in matrix @ vertex.co]
            for vertex in mesh.vertices
        ]
        faces = [
            tuple(int(value) for value in triangle.vertices)
            for triangle in mesh.loop_triangles
        ]
        triangles = [
            [points[index] for index in face]
            for face in faces
        ]
        tree = BVHTree.FromPolygons(
            [Vector(point) for point in points],
            faces,
            all_triangles=True,
        )
        return points, faces, triangles, tree
    finally:
        evaluated.to_mesh_clear()


def nearest_cutter_record(
    tree: BVHTree, point: list[float]
) -> dict[str, Any]:
    location, normal, triangle_index, distance = tree.find_nearest(Vector(point))
    if location is None or normal is None or triangle_index is None:
        raise RuntimeError(
            f"{OPERATION}: cutter nearest query failed; point_mm={point}"
        )
    return {
        "point_mm": [float(value) for value in point],
        "nearest_cutter_point_mm": [float(value) for value in location],
        "outward_normal": [float(value) for value in normal.normalized()],
        "cutter_triangle_index": int(triangle_index),
        "unsigned_distance_mm": float(distance),
        "signed_distance_mm": float(
            (Vector(point) - location).dot(normal.normalized())
        ),
    }


def signed_segment_clearance(
    start: list[float],
    end: list[float],
    cutter_triangles: list[list[list[float]]],
    cutter_tree: BVHTree,
) -> dict[str, Any]:
    exact_minimum = math.inf
    exact_witness = None
    for triangle_index, triangle in enumerate(cutter_triangles):
        distance = local.segment_triangle_distance(start, end, triangle)
        if distance < exact_minimum:
            exact_minimum = distance
            exact_witness = {
                "cutter_triangle_index": triangle_index,
                "distance_mm": distance,
            }
    divisions = max(1, math.ceil(length(sub(end, start)) / SAMPLE_SPACING_MM))
    signed_records = [
        nearest_cutter_record(
            cutter_tree, interpolate(start, end, index / divisions)
        )
        for index in range(divisions + 1)
    ]
    minimum_signed = min(
        record["signed_distance_mm"] for record in signed_records
    )
    return {
        "exact_minimum_segment_to_cutter_distance_mm": exact_minimum,
        "exact_witness": exact_witness,
        "adaptive_divisions": divisions,
        "adaptive_sample_count": divisions + 1,
        "adaptive_spacing_max_mm": SAMPLE_SPACING_MM,
        "minimum_signed_sample_margin_mm": minimum_signed,
        "minimum_signed_sample": min(
            signed_records, key=lambda record: record["signed_distance_mm"]
        ),
        "passes": (
            exact_minimum >= MINIMUM_CLEARANCE_MM - TOLERANCE_MM
            and minimum_signed >= MINIMUM_CLEARANCE_MM - TOLERANCE_MM
        ),
    }


def segment_segment_distance(
    first_start: list[float],
    first_end: list[float],
    second_start: list[float],
    second_end: list[float],
) -> float:
    point_a, point_b = local.closest_segment_points(
        Vector(first_start),
        Vector(first_end),
        Vector(second_start),
        Vector(second_end),
    )
    return float((point_a - point_b).length)


def build_direction_modes(
    source_normals: list[list[float]],
    cutter_normals: list[list[float]],
    tangent: list[float],
) -> list[dict[str, Any]]:
    modes = []
    for blend_weight in BLEND_WEIGHTS:
        independent = []
        for source_normal, cutter_normal in zip(
            source_normals, cutter_normals, strict=True
        ):
            aligned_source = list(source_normal)
            if dot(aligned_source, cutter_normal) < 0.0:
                aligned_source = scale(aligned_source, -1.0)
            independent.append(
                normalized(
                    add(
                        scale(cutter_normal, 1.0 - blend_weight),
                        scale(aligned_source, blend_weight),
                    ),
                    f"independent blend {blend_weight}",
                )
            )
        common = normalized(
            add(independent[0], independent[1]),
            f"common blend {blend_weight}",
        )
        for common_mode, base_directions in (
            (False, independent),
            (True, [common, common]),
        ):
            for degrees in ROTATION_DEGREES:
                directions = [
                    normalized(
                        local.rotate_about_axis(direction, tangent, degrees),
                        (
                            f"rotated landing direction; blend={blend_weight}; "
                            f"common={common_mode}; degrees={degrees}"
                        ),
                    )
                    for direction in base_directions
                ]
                record = {
                    "blend_weight_source_normal": blend_weight,
                    "common_direction": common_mode,
                    "rotation_about_source_edge_degrees": degrees,
                    "endpoint_directions": directions,
                }
                record["mode_id"] = (
                    f"LANDING_DIRECTION_{exact.stable_hash(record)[:16].upper()}"
                )
                record["fingerprint"] = exact.stable_hash(record)
                modes.append(record)
    return sorted(
        modes,
        key=lambda record: (
            record["blend_weight_source_normal"],
            record["common_direction"],
            abs(record["rotation_about_source_edge_degrees"]),
            record["rotation_about_source_edge_degrees"],
            record["mode_id"],
        ),
    )


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def main() -> None:
    args = arguments()
    verified_inputs = {}
    for label, (path, expected) in sorted(FROZEN_HASHES.items()):
        actual = exact.sha_file(path)
        if actual != expected:
            raise RuntimeError(
                f"{OPERATION}: V27_C9_LANDING_INPUT_HASH_MISMATCH; "
                f"input={label}; path={path}; expected={expected}; actual={actual}"
            )
        verified_inputs[label] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": expected,
        }
    aggregate = exact.load_json(AGGREGATE_AUTHORITY)
    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = ROOT / aggregate["verified_inputs"]["input_blend"]["path"]
    if blend_path != expected_blend.resolve():
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend.resolve()}; "
            f"actual={blend_path}"
        )
    source = bpy.data.objects.get(SOURCE_OBJECT)
    cutter = bpy.data.objects.get(CUTTER_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: required source mesh {SOURCE_OBJECT!r} is missing"
        )
    if cutter is None or cutter.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: required cutter mesh {CUTTER_OBJECT!r} is missing"
        )
    if not matrix_is_identity(source.matrix_world):
        raise RuntimeError(
            f"{OPERATION}: source object matrix is not identity; exact frozen "
            "local coordinates cannot be compared to cutter world coordinates"
        )
    mesh = source.data
    edge = mesh.edges[TARGET_EDGE_ID]
    actual_vertices = tuple(int(value) for value in edge.vertices)
    if set(actual_vertices) != set(TARGET_VERTEX_IDS):
        raise RuntimeError(
            f"{OPERATION}: target edge identity mismatch; edge={TARGET_EDGE_ID}; "
            f"expected_vertices={TARGET_VERTEX_IDS}; actual={actual_vertices}"
        )
    original_points = [
        [float(value) for value in mesh.vertices[vertex_id].co]
        for vertex_id in TARGET_VERTEX_IDS
    ]
    family = exact.load_json(FAMILY_AUTHORITY)
    chain = next(
        record
        for record in family["finite_family"]["chains"]["C9"]
        if record["chain_id"] == TARGET_CHAIN_ID
    )
    if chain["ordered_vertex_ids"] != list(TARGET_VERTEX_IDS):
        raise RuntimeError(
            f"{OPERATION}: frozen C9 chain vertices changed; "
            f"expected={TARGET_VERTEX_IDS}; actual={chain['ordered_vertex_ids']}"
        )
    source_normals = [list(frame["normal"]) for frame in chain["frames"]]
    tangent = normalized(
        sub(original_points[1], original_points[0]), "source edge tangent"
    )

    _, _, cutter_triangles, cutter_tree = cutter_geometry(cutter)
    original_nearest = [
        nearest_cutter_record(cutter_tree, point)
        for point in original_points
    ]
    cutter_normals = [
        record["outward_normal"] for record in original_nearest
    ]
    direction_modes = build_direction_modes(
        source_normals, cutter_normals, tangent
    )
    offset_pairs = sorted(
        product(OFFSET_VALUES_MM, repeat=2),
        key=lambda values: (
            max(values),
            sum(values),
            abs(values[0] - values[1]),
            values,
        ),
    )
    members = [
        {
            "mode_id": mode["mode_id"],
            "endpoint_offsets_mm": list(offsets),
        }
        for offsets in offset_pairs
        for mode in direction_modes
    ]
    family_descriptor = {
        "target_edge_id": TARGET_EDGE_ID,
        "target_vertex_ids": list(TARGET_VERTEX_IDS),
        "landing_face_mask": sorted(LANDING_FACE_MASK),
        "direction_modes": direction_modes,
        "endpoint_offset_values_mm": OFFSET_VALUES_MM,
        "member_order": members,
        "member_count": len(members),
    }
    family_fingerprint = exact.stable_hash(family_descriptor)

    source_triangles = {
        int(polygon.index): exact.polygon_triangles(mesh, int(polygon.index))
        for polygon in mesh.polygons
        if int(polygon.index) not in LANDING_FACE_MASK
    }
    source_face_aabbs = {
        face_id: local.aabb(
            [point for triangle in triangles for point in triangle]
        )
        for face_id, triangles in source_triangles.items()
    }
    source_spatial_index = local.build_spatial_index(source_face_aabbs)
    negative = exact.load_json(
        ROOT / aggregate["verified_inputs"]["negative_space_authority"]["path"]
    )
    keepout_cells = exact.collect_keepout_cells(negative)
    terminal = exact.load_json(
        ROOT / aggregate["verified_inputs"]["terminal_authority"]["path"]
    )
    terminal_segments = [
        {
            "chain_id": terminal["selection"][component][side]["chain_id"],
            "start": list(start),
            "end": list(end),
        }
        for component in ("C20", "C9")
        for side in ("LOWER", "UPPER")
        for start, end in zip(
            terminal["selection"][component][side][
                "exact_source_coordinates_mm"
            ],
            terminal["selection"][component][side][
                "exact_source_coordinates_mm"
            ][1:],
            strict=False,
        )
    ]

    mode_by_id = {mode["mode_id"]: mode for mode in direction_modes}
    selected = None
    rejection_counts: Counter[str] = Counter()
    first_counterexamples = {}
    evaluated_records = []
    for member_index, member in enumerate(members):
        mode = mode_by_id[member["mode_id"]]
        offsets = member["endpoint_offsets_mm"]
        moved = [
            add(
                original_points[index],
                scale(mode["endpoint_directions"][index], offsets[index]),
            )
            for index in range(2)
        ]
        clearance = signed_segment_clearance(
            moved[0], moved[1], cutter_triangles, cutter_tree
        )
        reasons = []
        if not clearance["passes"]:
            reasons.append("CUTTER_CLEARANCE_FAILED")
        complement_hits = set()
        terminal_hits = set()
        protected_keepout_hits = set()
        central_opening_hits = set()
        if not reasons:
            segment_box = local.aabb(moved)
            for face_id in local.spatial_candidates(
                source_spatial_index, segment_box
            ):
                if any(
                    local.segment_triangle_distance(
                        moved[0], moved[1], triangle
                    )
                    <= TOLERANCE_MM
                    for triangle in source_triangles[face_id]
                ):
                    complement_hits.add(face_id)
            if complement_hits:
                reasons.append("SOURCE_COMPLEMENT_INTERSECTION")
        if not reasons:
            for record in terminal_segments:
                if (
                    segment_segment_distance(
                        moved[0], moved[1], record["start"], record["end"]
                    )
                    <= TOLERANCE_MM
                ):
                    terminal_hits.add(record["chain_id"])
            if terminal_hits:
                reasons.append("TERMINAL_CONFLICT")
        if not reasons:
            for cell in keepout_cells:
                intersects, _ = exact.clip_segment(
                    moved[0], moved[1], cell["half_spaces"]
                )
                if not intersects:
                    continue
                if cell["kind"] == "CENTRAL_OPENING":
                    central_opening_hits.add(cell["cell_id"])
                else:
                    protected_keepout_hits.add(cell["cell_id"])
            if protected_keepout_hits:
                reasons.append("PROTECTED_NEGATIVE_SPACE_CONFLICT")
        for reason in reasons:
            rejection_counts[reason] += 1
            first_counterexamples.setdefault(
                reason,
                {
                    "member_index": member_index,
                    "member": member,
                    "moved_endpoint_coordinates_mm": moved,
                    "clearance": clearance,
                    "source_complement_face_ids": sorted(complement_hits),
                    "terminal_chain_ids": sorted(terminal_hits),
                    "protected_keepout_cell_ids": sorted(
                        protected_keepout_hits
                    ),
                    "central_opening_cell_ids": sorted(central_opening_hits),
                },
            )
        evaluation = {
            "member_index": member_index,
            "mode_id": member["mode_id"],
            "endpoint_offsets_mm": offsets,
            "accepted": not reasons,
            "reasons": reasons,
            "exact_minimum_cutter_distance_mm": clearance[
                "exact_minimum_segment_to_cutter_distance_mm"
            ],
            "minimum_signed_sample_margin_mm": clearance[
                "minimum_signed_sample_margin_mm"
            ],
            "source_complement_hit_count": len(complement_hits),
            "terminal_hit_count": len(terminal_hits),
            "protected_keepout_hit_count": len(protected_keepout_hits),
            "central_opening_hit_count": len(central_opening_hits),
        }
        evaluated_records.append(evaluation)
        if not reasons:
            selected = {
                **evaluation,
                "member": member,
                "mode": mode,
                "original_endpoint_coordinates_mm": original_points,
                "moved_endpoint_coordinates_mm": moved,
                "clearance": clearance,
                "source_complement_face_ids_intersected": [],
                "terminal_chain_ids_intersected": [],
                "protected_keepout_cell_ids_intersected": [],
                "central_opening_cell_ids_intersected": sorted(
                    central_opening_hits
                ),
                "moved_edge_length_mm": length(sub(moved[1], moved[0])),
                "original_edge_length_mm": length(
                    sub(original_points[1], original_points[0])
                ),
            }
            selected["edge_length_ratio"] = (
                selected["moved_edge_length_mm"]
                / selected["original_edge_length_mm"]
            )
            selected["fingerprint"] = exact.stable_hash(selected)
            break

    status = (
        "V27_C9_LANDING_CLEARANCE_SOLVED"
        if selected is not None
        else "V27_NO_VALID_C9_LANDING_CLEARANCE"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": (
            "read-only finite C9 landing endpoint-clearance analysis; the "
            "11-face one-ring is candidate authority only; no mesh mutation, "
            "candidate geometry emission, image work, Blend save, Gate B/D, "
            "or promotion"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": verified_inputs,
        "source_scene": {
            "blend": str(blend_path),
            "source_object": SOURCE_OBJECT,
            "cutter_object": CUTTER_OBJECT,
            "source_matrix_identity": True,
            "cutter_triangle_count": len(cutter_triangles),
        },
        "landing_contract": {
            "target_edge_id": TARGET_EDGE_ID,
            "target_vertex_ids": list(TARGET_VERTEX_IDS),
            "target_chain_id": TARGET_CHAIN_ID,
            "original_endpoint_coordinates_mm": original_points,
            "original_endpoint_cutter_records": original_nearest,
            "landing_face_mask": sorted(LANDING_FACE_MASK),
            "prior_selected_faces": [2228, 2230, 2240, 2243, 2244],
            "prior_immutable_faces": [2227, 2231, 2232, 2245],
            "outside_prior_maximum_mask_faces": [2235, 2239],
            "minimum_clearance_mm": MINIMUM_CLEARANCE_MM,
        },
        "finite_family": {
            **family_descriptor,
            "fingerprint": family_fingerprint,
            "enumerated_before_evaluation": True,
        },
        "evaluation": {
            "evaluated_member_count": len(evaluated_records),
            "selected_first_complete_pass": selected is not None,
            "records": evaluated_records,
            "rejection_counts": dict(sorted(rejection_counts.items())),
            "first_counterexamples": first_counterexamples,
        },
        "selection": selected,
        "invariants": {
            "frozen_hashes_match": True,
            "source_matrix_is_identity": True,
            "target_edge_and_vertices_match": True,
            "landing_face_mask_count_is_11": len(LANDING_FACE_MASK) == 11,
            "family_enumerated_before_evaluation": True,
            "family_fingerprint_recorded": True,
            "cutter_used_only_for_direction_and_clearance": True,
            "no_candidate_geometry_emitted": True,
        },
        "safety": {
            "mutation_started": False,
            "candidate_surface_geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
            "gate_b_run": False,
            "gate_d_run": False,
        },
    }
    if not all(result["invariants"].values()):
        failed = [
            name for name, passed in result["invariants"].items() if not passed
        ]
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_INVARIANT_FAILED; failed={failed}"
        )
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "family_fingerprint": family_fingerprint,
        "family_member_count": len(members),
        "evaluated_member_count": len(evaluated_records),
        "selected_member_index": (
            selected["member_index"] if selected is not None else None
        ),
        "selected_member_fingerprint": (
            selected["fingerprint"] if selected is not None else None
        ),
        "selected_endpoint_offsets_mm": (
            selected["endpoint_offsets_mm"] if selected is not None else None
        ),
        "selected_minimum_signed_margin_mm": (
            selected["clearance"]["minimum_signed_sample_margin_mm"]
            if selected is not None
            else None
        ),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
