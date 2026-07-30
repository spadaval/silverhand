#!/usr/bin/env python3
"""Evaluate the frozen V27 Stage 2b local flex-gap family read-only."""

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
from mathutils.geometry import closest_point_on_tri, intersect_ray_tri


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import solve_v27_flex_gap as exact  # noqa: E402


OPERATION = "EVALUATE_V27_LOCAL_GAP_FAMILY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
FAMILY_PATH = V27 / "v27_local_gap_family_authority.json"
FAMILY_RECEIPT_PATH = V27 / "v27_local_gap_family_authority_receipt.json"
DEFAULT_OUTPUT = V27 / "v27_local_gap_evaluation_authority.json"
DEFAULT_RECEIPT = V27 / "v27_local_gap_evaluation_authority_receipt.json"
SOURCE_OBJECT = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
CUTTER_OBJECT = "CUT_CLEARANCE_ANATOMY_STRAIGHT"
TOLERANCE_MM = 1e-7
AREA_TOLERANCE_MM2 = 1e-9
MINIMUM_CLEARANCE_MM = 1.7
ADAPTIVE_SPACING_MM = 1.0
SPATIAL_BIN_MM = 10.0

FROZEN_HASHES = {
    "local_gap_family_authority": (
        FAMILY_PATH,
        "14eccf5706d6325901cb9a025ca16a8cb8898dd190be672863c308403f06866d",
    ),
    "local_gap_family_receipt": (
        FAMILY_RECEIPT_PATH,
        "5a1da9d6636138f32c2dc3b11a5da8f1e15967fa9693d620c4a66622625c36aa",
    ),
    "exact_geometry_library": (
        ROOT / "scripts/blender/solve_v27_flex_gap.py",
        "89fcc72b20e569f86997ed9f2295ac1fea972c6f43e30eb02b6c8594d4707e9c",
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


def cross(left: Iterable[float], right: Iterable[float]) -> list[float]:
    a = list(left)
    b = list(right)
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def length(vector: Iterable[float]) -> float:
    return math.sqrt(dot(vector, vector))


def normalized(vector: Iterable[float]) -> list[float] | None:
    values = list(vector)
    magnitude = length(values)
    if magnitude <= TOLERANCE_MM:
        return None
    return scale(values, 1.0 / magnitude)


def rotate_about_axis(
    vector: list[float], axis: list[float], degrees: float
) -> list[float]:
    radians = math.radians(degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    return add(
        add(scale(vector, cosine), scale(cross(axis, vector), sine)),
        scale(axis, dot(axis, vector) * (1.0 - cosine)),
    )


def taper(normalized_arclength: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            normalized_arclength / 0.25,
            (1.0 - normalized_arclength) / 0.25,
        ),
    )


def polygon_area(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0
    origin = points[0]
    return sum(
        length(cross(sub(points[index], origin), sub(points[index + 1], origin)))
        / 2.0
        for index in range(1, len(points) - 1)
    )


def aabb(points: list[list[float]]) -> tuple[list[float], list[float]]:
    return (
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    )


def aabb_overlaps(
    left: tuple[list[float], list[float]],
    right: tuple[list[float], list[float]],
) -> bool:
    return all(
        left[0][axis] <= right[1][axis] + TOLERANCE_MM
        and right[0][axis] <= left[1][axis] + TOLERANCE_MM
        for axis in range(3)
    )


def spatial_bin_keys(
    bounds: tuple[list[float], list[float]]
) -> Iterable[tuple[int, int, int]]:
    lower = [math.floor(value / SPATIAL_BIN_MM) for value in bounds[0]]
    upper = [math.floor(value / SPATIAL_BIN_MM) for value in bounds[1]]
    for first in range(lower[0], upper[0] + 1):
        for second in range(lower[1], upper[1] + 1):
            for third in range(lower[2], upper[2] + 1):
                yield (first, second, third)


def build_spatial_index(
    face_bounds: dict[int, tuple[list[float], list[float]]]
) -> dict[tuple[int, int, int], set[int]]:
    index: dict[tuple[int, int, int], set[int]] = {}
    for face_id, bounds in face_bounds.items():
        for key in spatial_bin_keys(bounds):
            index.setdefault(key, set()).add(face_id)
    return index


def spatial_candidates(
    index: dict[tuple[int, int, int], set[int]],
    bounds: tuple[list[float], list[float]],
) -> set[int]:
    return {
        face_id
        for key in spatial_bin_keys(bounds)
        for face_id in index.get(key, ())
    }


def oriented_prism(
    start20: list[float],
    start9: list[float],
    end20: list[float],
    end9: list[float],
    start_chord: list[float],
    end_chord: list[float],
    width: float,
    depth: float,
) -> dict[str, Any] | None:
    mid_start = scale(add(start20, start9), 0.5)
    mid_end = scale(add(end20, end9), 0.5)
    tangent = normalized(sub(mid_end, mid_start))
    chord = normalized(add(start_chord, end_chord))
    if tangent is None or chord is None:
        return None
    chord = normalized(sub(chord, scale(tangent, dot(chord, tangent))))
    if chord is None:
        return None
    normal = normalized(cross(tangent, chord))
    if normal is None:
        return None
    center = scale(add(mid_start, mid_end), 0.5)
    tangent_extent = length(sub(mid_end, mid_start)) / 2.0
    extents = (tangent_extent, width / 2.0, depth)
    axes = (tangent, chord, normal)
    half_spaces = []
    for axis, extent in zip(axes, extents, strict=True):
        half_spaces.extend(
            [
                {
                    "normal": axis,
                    "offset_mm": dot(axis, center) + extent,
                    "inside_test": "dot(normal, point) <= offset_mm + tolerance_mm",
                },
                {
                    "normal": scale(axis, -1.0),
                    "offset_mm": -dot(axis, center) + extent,
                    "inside_test": "dot(normal, point) <= offset_mm + tolerance_mm",
                },
            ]
        )
    vertices = []
    for tangent_sign, chord_sign, normal_sign in product((-1.0, 1.0), repeat=3):
        point = list(center)
        point = add(point, scale(tangent, tangent_sign * tangent_extent))
        point = add(point, scale(chord, chord_sign * width / 2.0))
        point = add(point, scale(normal, normal_sign * depth))
        vertices.append(point)
    return {
        "center_mm": center,
        "axes": {
            "tangent": tangent,
            "chord": chord,
            "normal": normal,
        },
        "half_extents_mm": {
            "tangent": tangent_extent,
            "chord": width / 2.0,
            "normal": depth,
        },
        "vertices_mm": vertices,
        "half_spaces": half_spaces,
        "aabb_mm": aabb(vertices),
    }


def member_geometry(
    pair: dict[str, Any], parameters: dict[str, float]
) -> tuple[dict[str, Any] | None, str | None]:
    width = parameters["requested_empty_chord_width_mm"]
    orientation = parameters["chord_orientation_degrees"]
    depth20 = parameters["c20_signed_local_normal_depth_mm"]
    depth9 = parameters["c9_signed_local_normal_depth_mm"]
    allocation = parameters["c20_to_c9_displacement_allocation"]
    samples = []
    minimum_chord = math.inf
    for record in pair["correspondence"]:
        p20 = record["c20"]["point_mm"]
        p9 = record["c9"]["point_mm"]
        n20 = list(record["c20"]["normal"])
        n9 = list(record["c9"]["normal"])
        if dot(n20, n9) < 0.0:
            n9 = scale(n9, -1.0)
        rotation_axis = normalized(add(n20, n9))
        if rotation_axis is None:
            return None, "FRAME_DEGENERATE"
        base_chord = record["oriented_c20_to_c9_chord"]
        chord = normalized(
            rotate_about_axis(base_chord, rotation_axis, orientation)
        )
        if chord is None:
            return None, "FRAME_DEGENERATE"
        source_projection = dot(sub(p9, p20), chord)
        delta = max(0.0, width - source_projection)
        amount = taper(float(record["normalized_arclength"]))
        displaced20 = add(
            sub(p20, scale(chord, amount * allocation * delta)),
            scale(n20, amount * depth20),
        )
        displaced9 = add(
            add(p9, scale(chord, amount * (1.0 - allocation) * delta)),
            scale(n9, amount * depth9),
        )
        measured = dot(sub(displaced9, displaced20), chord)
        minimum_chord = min(minimum_chord, measured)
        samples.append(
            {
                "normalized_arclength": record["normalized_arclength"],
                "c20_point_mm": displaced20,
                "c9_point_mm": displaced9,
                "chord": chord,
                "c20_normal": n20,
                "c9_normal": n9,
                "source_projection_mm": source_projection,
                "applied_delta_mm": delta * amount,
                "measured_chord_mm": measured,
            }
        )
    if minimum_chord < width - TOLERANCE_MM:
        return {
            "samples": samples,
            "minimum_chord_mm": minimum_chord,
            "prisms": [],
        }, "CHORD_WIDTH_FAILED"
    prism_depth = max(abs(depth20), abs(depth9)) + MINIMUM_CLEARANCE_MM
    prisms = []
    for index in range(len(samples) - 1):
        start = samples[index]
        end = samples[index + 1]
        prism = oriented_prism(
            start["c20_point_mm"],
            start["c9_point_mm"],
            end["c20_point_mm"],
            end["c9_point_mm"],
            start["chord"],
            end["chord"],
            width,
            prism_depth,
        )
        if prism is None:
            return None, "FRAME_DEGENERATE"
        prism["prism_index"] = index
        prisms.append(prism)
    return {
        "samples": samples,
        "minimum_chord_mm": minimum_chord,
        "prism_depth_mm": prism_depth,
        "prisms": prisms,
    }, None


def positive_area_face_intersection(
    triangles: list[list[list[float]]],
    triangle_aabbs: list[tuple[list[float], list[float]]],
    prism: dict[str, Any],
) -> bool:
    for triangle, triangle_box in zip(triangles, triangle_aabbs, strict=True):
        if not aabb_overlaps(triangle_box, prism["aabb_mm"]):
            continue
        intersects, clipped = exact.triangle_intersects_cell(
            triangle, prism["half_spaces"]
        )
        if intersects and polygon_area(clipped) > AREA_TOLERANCE_MM2:
            return True
    return False


def closest_segment_points(
    first_a: Vector, first_b: Vector, second_a: Vector, second_b: Vector
) -> tuple[Vector, Vector]:
    epsilon = 1.0e-12
    direction_a = first_b - first_a
    direction_b = second_b - second_a
    offset = first_a - second_a
    aa = direction_a.dot(direction_a)
    bb = direction_b.dot(direction_b)
    ab = direction_a.dot(direction_b)
    ac = direction_a.dot(offset)
    bc = direction_b.dot(offset)
    denominator = aa * bb - ab * ab
    first_parameter = 0.0
    second_parameter = 0.0
    if aa <= epsilon and bb <= epsilon:
        return first_a.copy(), second_a.copy()
    if aa <= epsilon:
        second_parameter = max(0.0, min(1.0, bc / bb))
    elif bb <= epsilon:
        first_parameter = max(0.0, min(1.0, -ac / aa))
    else:
        if denominator > epsilon:
            first_parameter = max(
                0.0, min(1.0, (ab * bc - ac * bb) / denominator)
            )
        second_parameter = (ab * first_parameter + bc) / bb
        if second_parameter < 0.0:
            second_parameter = 0.0
            first_parameter = max(0.0, min(1.0, -ac / aa))
        elif second_parameter > 1.0:
            second_parameter = 1.0
            first_parameter = max(0.0, min(1.0, (ab - ac) / aa))
    return (
        first_a + direction_a * first_parameter,
        second_a + direction_b * second_parameter,
    )


def segment_triangle_distance(
    start: list[float], end: list[float], triangle: list[list[float]]
) -> float:
    first = Vector(start)
    second = Vector(end)
    target = [Vector(point) for point in triangle]
    direction = second - first
    if direction.length > 1.0e-12:
        point = intersect_ray_tri(
            target[0], target[1], target[2], direction, first, True
        )
        if point is not None:
            parameter = (point - first).dot(direction) / direction.length_squared
            if -TOLERANCE_MM <= parameter <= 1.0 + TOLERANCE_MM:
                return 0.0
    minimum = min(
        (point - closest_point_on_tri(point, *target)).length
        for point in (first, second)
    )
    for edge_start, edge_end in ((0, 1), (1, 2), (2, 0)):
        point_a, point_b = closest_segment_points(
            first, second, target[edge_start], target[edge_end]
        )
        minimum = min(minimum, (point_a - point_b).length)
    return float(minimum)


def collect_cutter_triangles(
    cutter: bpy.types.Object,
) -> list[list[list[float]]]:
    evaluated = cutter.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix = cutter.matrix_world
        return [
            [
                [float(value) for value in matrix @ mesh.vertices[index].co]
                for index in triangle.vertices
            ]
            for triangle in mesh.loop_triangles
        ]
    finally:
        evaluated.to_mesh_clear()


def clearance_audit(
    geometry: dict[str, Any],
    cutter_triangles: list[list[list[float]]],
    cutter_aabbs: list[tuple[list[float], list[float]]],
) -> dict[str, Any]:
    minimum = math.inf
    witness = None
    samples = geometry["samples"]
    for component in ("c20", "c9"):
        key = f"{component}_point_mm"
        for segment_index, (start, end) in enumerate(
            zip(samples, samples[1:], strict=False)
        ):
            first = start[key]
            second = end[key]
            segment_box = aabb([first, second])
            for triangle_index, (triangle, triangle_box) in enumerate(
                zip(cutter_triangles, cutter_aabbs, strict=True)
            ):
                expanded = (
                    [value - minimum if math.isfinite(minimum) else -math.inf for value in triangle_box[0]],
                    [value + minimum if math.isfinite(minimum) else math.inf for value in triangle_box[1]],
                )
                if math.isfinite(minimum) and not aabb_overlaps(segment_box, expanded):
                    continue
                distance = segment_triangle_distance(first, second, triangle)
                if distance < minimum:
                    minimum = distance
                    witness = {
                        "component": component.upper(),
                        "segment_index": segment_index,
                        "cutter_triangle_index": triangle_index,
                        "distance_mm": distance,
                    }
    return {
        "minimum_boundary_segment_to_cutter_distance_mm": minimum,
        "witness": witness,
        "passes_1_7_mm": minimum >= MINIMUM_CLEARANCE_MM - TOLERANCE_MM,
        "adaptive_sample_spacing_max_mm": ADAPTIVE_SPACING_MM,
        "method": (
            "exact segment/triangle finite-feature distance; adaptive spacing "
            "reserved as a redundant selected-member audit"
        ),
    }


def ordered_parameter_values(axes: dict[str, list[float]]) -> list[dict[str, float]]:
    values = [
        {
            "requested_empty_chord_width_mm": width,
            "chord_orientation_degrees": orientation,
            "c20_signed_local_normal_depth_mm": depth20,
            "c9_signed_local_normal_depth_mm": depth9,
            "c20_to_c9_displacement_allocation": allocation,
        }
        for width, orientation, depth20, depth9, allocation in product(
            axes["requested_empty_chord_width_mm"],
            axes["chord_orientation_degrees"],
            axes["c20_signed_local_normal_depth_mm"],
            axes["c9_signed_local_normal_depth_mm"],
            axes["c20_to_c9_displacement_allocation"],
        )
    ]
    return sorted(
        values,
        key=lambda record: (
            record["requested_empty_chord_width_mm"],
            abs(record["c20_signed_local_normal_depth_mm"])
            + abs(record["c9_signed_local_normal_depth_mm"]),
            abs(record["chord_orientation_degrees"]),
            record["chord_orientation_degrees"],
            abs(record["c20_signed_local_normal_depth_mm"]),
            record["c20_signed_local_normal_depth_mm"],
            abs(record["c9_signed_local_normal_depth_mm"]),
            record["c9_signed_local_normal_depth_mm"],
            abs(record["c20_to_c9_displacement_allocation"] - 0.5),
            record["c20_to_c9_displacement_allocation"],
        ),
    )


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--start-member", type=int, default=0)
    parser.add_argument("--max-members", type=int, default=None)
    parser.add_argument(
        "--diagnostic-allow-immutable-face",
        action="append",
        type=int,
        default=[],
    )
    parser.add_argument(
        "--diagnostic-max-immutable-hits",
        type=int,
        default=None,
    )
    return parser.parse_args(argv)


def main() -> None:
    args = arguments()
    family = exact.load_json(FAMILY_PATH)
    aggregate = exact.load_json(exact.AGGREGATE_PATH)
    verified_inputs = dict(family["verified_inputs"])
    verified_inputs.update(
        {
            label: {"path": str(path.relative_to(ROOT)), "sha256": expected}
            for label, (path, expected) in FROZEN_HASHES.items()
        }
    )
    for label, record in sorted(verified_inputs.items()):
        path = ROOT / record["path"]
        actual = exact.sha_file(path)
        if actual != record["sha256"]:
            raise RuntimeError(
                f"{OPERATION}: V27_LOCAL_GAP_INPUT_HASH_MISMATCH; "
                f"input={label}; path={path}; expected={record['sha256']}; "
                f"actual={actual}"
            )
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
    mesh = source.data
    selected_faces = {
        component: [
            int(face_id)
            for face_id in aggregate["aggregate_mask"]["source_face_ids"][
                component
            ]
        ]
        for component in ("C20", "C9")
    }
    immutable_faces = sorted(
        {
            int(face_id)
            for component in ("C20", "C9")
            for face_id in aggregate["aggregate_mask"][
                "immutable_complement_source_face_ids"
            ][component]
        }
    )
    relevant_faces = sorted(
        set(immutable_faces)
        | {face_id for values in selected_faces.values() for face_id in values}
    )
    face_triangles = {
        face_id: exact.polygon_triangles(mesh, face_id)
        for face_id in relevant_faces
    }
    face_triangle_aabbs = {
        face_id: [aabb(triangle) for triangle in triangles]
        for face_id, triangles in face_triangles.items()
    }
    face_aabbs = {
        face_id: aabb(
            [point for triangle in triangles for point in triangle]
        )
        for face_id, triangles in face_triangles.items()
    }
    face_spatial_index = build_spatial_index(face_aabbs)
    selected_face_component = {
        face_id: component
        for component, face_ids in selected_faces.items()
        for face_id in face_ids
    }
    immutable_face_set = set(immutable_faces)
    negative = exact.load_json(
        ROOT / aggregate["verified_inputs"]["negative_space_authority"]["path"]
    )
    keepout_cells = exact.collect_keepout_cells(negative)
    terminal = exact.load_json(
        ROOT / aggregate["verified_inputs"]["terminal_authority"]["path"]
    )
    terminal_records = [
        terminal["selection"][component][side]
        for component in ("C20", "C9")
        for side in ("LOWER", "UPPER")
    ]
    cutter_triangles = collect_cutter_triangles(cutter)
    cutter_aabbs = [aabb(triangle) for triangle in cutter_triangles]

    pair_records = family["finite_family"]["ordered_chain_pairs"]
    pair_order = sorted(
        pair_records,
        key=lambda pair: (
            min(
                pair["correspondence"][0]["source_separation_mm"],
                pair["correspondence"][-1]["source_separation_mm"],
            )
            < 12.0 - TOLERANCE_MM,
            abs(
                min(
                    pair["correspondence"][0]["source_separation_mm"],
                    pair["correspondence"][-1]["source_separation_mm"],
                )
                - 12.0
            ),
            abs(
                sum(
                    record["source_separation_mm"]
                    for record in pair["correspondence"]
                )
                / len(pair["correspondence"])
                - 12.0
            ),
            max(
                record["source_separation_mm"]
                for record in pair["correspondence"]
            ),
            pair["pair_id"],
        ),
    )
    parameter_order = ordered_parameter_values(
        family["finite_family"]["parameter_grid"]["axes"]
    )
    evaluation_order = {
        "major_order": "PARAMETER_THEN_PAIR",
        "pair_order": [
            {
                "pair_id": pair["pair_id"],
                "mean_source_separation_mm": (
                    sum(
                        record["source_separation_mm"]
                        for record in pair["correspondence"]
                    )
                    / len(pair["correspondence"])
                ),
                "minimum_endpoint_source_separation_mm": min(
                    pair["correspondence"][0]["source_separation_mm"],
                    pair["correspondence"][-1]["source_separation_mm"],
                ),
                "maximum_source_separation_mm": max(
                    record["source_separation_mm"]
                    for record in pair["correspondence"]
                ),
            }
            for pair in pair_order
        ],
        "parameter_order": parameter_order,
        "complete_member_count": len(pair_order) * len(parameter_order),
        "fingerprint": exact.stable_hash(
            {
                "major_order": "PARAMETER_THEN_PAIR",
                "pair_ids": [pair["pair_id"] for pair in pair_order],
                "parameters": parameter_order,
            }
        ),
    }

    rejection_counts: Counter[str] = Counter()
    first_counterexamples: dict[str, Any] = {}
    immutable_witness_counts: Counter[int] = Counter()
    collision_cache: dict[
        tuple[Any, ...], tuple[dict[str, set[int]], set[int]]
    ] = {}
    collision_cache_hits = 0
    evaluated_count = 0
    selected = None
    best_immutable_counterexample = None
    stopped_by_limit = False
    diagnostic_allowed_immutable = set(
        args.diagnostic_allow_immutable_face
    )
    if (
        diagnostic_allowed_immutable
        and args.diagnostic_max_immutable_hits is not None
    ):
        raise RuntimeError(
            f"{OPERATION}: choose either explicit diagnostic immutable faces "
            "or --diagnostic-max-immutable-hits, not both"
        )
    if diagnostic_allowed_immutable and args.max_members != 1:
        raise RuntimeError(
            f"{OPERATION}: diagnostic immutable bypass requires "
            "--max-members 1; it may inspect only one exact member"
        )
    if (
        args.diagnostic_max_immutable_hits is not None
        and args.diagnostic_max_immutable_hits < 0
    ):
        raise RuntimeError(
            f"{OPERATION}: --diagnostic-max-immutable-hits must be "
            f"non-negative; actual={args.diagnostic_max_immutable_hits}"
        )
    diagnostic_mode = bool(diagnostic_allowed_immutable) or (
        args.diagnostic_max_immutable_hits is not None
    )
    if args.start_member < 0:
        raise RuntimeError(
            f"{OPERATION}: --start-member must be non-negative; "
            f"actual={args.start_member}"
        )
    for parameter_rank, parameters in enumerate(parameter_order):
        for pair_rank, pair in enumerate(pair_order):
            member_index = parameter_rank * len(pair_order) + pair_rank
            if member_index < args.start_member:
                continue
            if args.max_members is not None and evaluated_count >= args.max_members:
                stopped_by_limit = True
                break
            evaluated_count += 1
            geometry, early_reason = member_geometry(pair, parameters)
            reasons = []
            if early_reason is not None:
                reasons.append(early_reason)
            removals = {"C20": set(), "C9": set()}
            immutable_hits = set()
            terminal_hits = set()
            keepout_hits = set()
            clearance = None
            if not reasons and geometry is not None:
                allocation_key = parameters[
                    "c20_to_c9_displacement_allocation"
                ]
                if all(
                    sample["applied_delta_mm"] <= TOLERANCE_MM
                    for sample in geometry["samples"]
                ):
                    allocation_key = "NO_CHORD_DISPLACEMENT"
                collision_key = (
                    pair["pair_id"],
                    parameters["requested_empty_chord_width_mm"],
                    parameters["chord_orientation_degrees"],
                    parameters["c20_signed_local_normal_depth_mm"],
                    parameters["c9_signed_local_normal_depth_mm"],
                    allocation_key,
                )
                cached_collision = collision_cache.get(collision_key)
                if cached_collision is not None:
                    collision_cache_hits += 1
                    removals = {
                        component: set(face_ids)
                        for component, face_ids in cached_collision[0].items()
                    }
                    immutable_hits = set(cached_collision[1])
                else:
                    for prism in geometry["prisms"]:
                        for face_id in spatial_candidates(
                            face_spatial_index, prism["aabb_mm"]
                        ):
                            if face_id in selected_face_component:
                                if positive_area_face_intersection(
                                    face_triangles[face_id],
                                    face_triangle_aabbs[face_id],
                                    prism,
                                ):
                                    removals[
                                        selected_face_component[face_id]
                                    ].add(face_id)
                            elif face_id in immutable_face_set:
                                if positive_area_face_intersection(
                                    face_triangles[face_id],
                                    face_triangle_aabbs[face_id],
                                    prism,
                                ):
                                    immutable_hits.add(face_id)
                    collision_cache[collision_key] = (
                        {
                            component: set(face_ids)
                            for component, face_ids in removals.items()
                        },
                        set(immutable_hits),
                    )
                if not removals["C20"]:
                    reasons.append("NO_C20_AGGREGATE_REMOVAL")
                if not removals["C9"]:
                    reasons.append("NO_C9_AGGREGATE_REMOVAL")
                if immutable_hits:
                    immutable_witness_counts.update(immutable_hits)
                    if args.diagnostic_max_immutable_hits is not None:
                        blocking_immutable_hits = (
                            set()
                            if len(immutable_hits)
                            <= args.diagnostic_max_immutable_hits
                            else immutable_hits
                        )
                    else:
                        blocking_immutable_hits = (
                            immutable_hits - diagnostic_allowed_immutable
                        )
                    if blocking_immutable_hits:
                        reasons.append("IMMUTABLE_INTERSECTION")
                    if removals["C20"] and removals["C9"]:
                        candidate = {
                            "member_index": member_index,
                            "pair_rank": pair_rank,
                            "parameter_rank": parameter_rank,
                            "pair_id": pair["pair_id"],
                            "c20_chain_id": pair["c20_chain_id"],
                            "c9_chain_id": pair["c9_chain_id"],
                            "parameters": parameters,
                            "minimum_chord_mm": geometry["minimum_chord_mm"],
                            "removal_counts": {
                                component: len(face_ids)
                                for component, face_ids in removals.items()
                            },
                            "immutable_hit_count": len(immutable_hits),
                            "immutable_source_face_ids": sorted(immutable_hits),
                        }
                        candidate["fingerprint"] = exact.stable_hash(candidate)
                        if (
                            best_immutable_counterexample is None
                            or (
                                candidate["immutable_hit_count"],
                                -sum(candidate["removal_counts"].values()),
                                candidate["member_index"],
                            )
                            < (
                                best_immutable_counterexample[
                                    "immutable_hit_count"
                                ],
                                -sum(
                                    best_immutable_counterexample[
                                        "removal_counts"
                                    ].values()
                                ),
                                best_immutable_counterexample["member_index"],
                            )
                        ):
                            best_immutable_counterexample = candidate
            if not reasons and geometry is not None:
                for record in terminal_records:
                    coordinates = record["exact_source_coordinates_mm"]
                    for prism in geometry["prisms"]:
                        if any(
                            exact.clip_segment(
                                list(start), list(end), prism["half_spaces"]
                            )[0]
                            for start, end in zip(
                                coordinates, coordinates[1:], strict=False
                            )
                        ):
                            terminal_hits.add(record["chain_id"])
                            break
                if terminal_hits:
                    reasons.append("TERMINAL_CONFLICT")
            if not reasons and geometry is not None:
                for prism in geometry["prisms"]:
                    for cell in keepout_cells:
                        intersects, _ = exact.convex_cells_intersect(
                            prism["half_spaces"], cell["half_spaces"]
                        )
                        if intersects:
                            keepout_hits.add(cell["cell_id"])
                if keepout_hits:
                    reasons.append("NEGATIVE_SPACE_CONFLICT")
            if not reasons and geometry is not None:
                clearance = clearance_audit(
                    geometry, cutter_triangles, cutter_aabbs
                )
                if not clearance["passes_1_7_mm"]:
                    reasons.append("CUTTER_CLEARANCE_FAILED")
            for reason in reasons:
                rejection_counts[reason] += 1
                first_counterexamples.setdefault(
                    reason,
                    {
                        "member_index": member_index,
                        "pair_rank": pair_rank,
                        "parameter_rank": parameter_rank,
                        "pair_id": pair["pair_id"],
                        "parameters": parameters,
                        "minimum_chord_mm": (
                            geometry["minimum_chord_mm"]
                            if geometry is not None
                            else None
                        ),
                        "removal_counts": {
                            component: len(face_ids)
                            for component, face_ids in removals.items()
                        },
                        "immutable_face_ids": sorted(immutable_hits)[:24],
                        "terminal_chain_ids": sorted(terminal_hits),
                        "negative_space_cell_ids": sorted(keepout_hits)[:24],
                        "clearance": clearance,
                    },
                )
            if not reasons and geometry is not None:
                selected = {
                    "member_index": member_index,
                    "pair_rank": pair_rank,
                    "parameter_rank": parameter_rank,
                    "pair_id": pair["pair_id"],
                    "c20_chain_id": pair["c20_chain_id"],
                    "c9_chain_id": pair["c9_chain_id"],
                    "parameters": parameters,
                    "geometry": geometry,
                    "removed_authorized_source_face_ids": {
                        component: sorted(face_ids)
                        for component, face_ids in removals.items()
                    },
                    "immutable_source_face_ids_intersected": [],
                    "diagnostically_allowed_immutable_source_face_ids": sorted(
                        immutable_hits
                        if args.diagnostic_max_immutable_hits is not None
                        else immutable_hits & diagnostic_allowed_immutable
                    ),
                    "terminal_chain_ids_intersected": [],
                    "negative_space_cell_ids_intersected": [],
                    "clearance": clearance,
                }
                selected["fingerprint"] = exact.stable_hash(selected)
                break
        if selected is not None or stopped_by_limit:
            break

    complete = selected is not None or (
        args.start_member == 0 and not stopped_by_limit
    )
    if selected is not None and diagnostic_mode:
        status = "V27_LOCAL_GAP_SPECIFIC_REVIEWED_BARRIER_IDENTIFIED"
    elif selected is not None:
        status = "V27_LOCAL_FLEX_GAP_SOLVED"
    elif complete:
        status = "V27_NO_VALID_LOCAL_12MM_FLEX_GAP"
    else:
        status = "V27_LOCAL_GAP_EVALUATION_CHECKPOINTED"
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": (
            "read-only exact V27 Stage 2b member evaluation; no source/model "
            "mutation, candidate geometry emission, image work, Blend save, "
            "Gate B/D, or promotion"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": verified_inputs,
        "source_scene": {
            "blend": str(blend_path),
            "source_object": SOURCE_OBJECT,
            "cutter_object": CUTTER_OBJECT,
            "cutter_triangle_count": len(cutter_triangles),
        },
        "family_fingerprint": family["finite_family"]["fingerprint"],
        "evaluation_order": evaluation_order,
        "evaluation": {
            "complete": complete,
            "start_member": args.start_member,
            "max_members": args.max_members,
            "diagnostic_allowed_immutable_source_face_ids": sorted(
                diagnostic_allowed_immutable
            ),
            "diagnostic_max_immutable_hit_count": (
                args.diagnostic_max_immutable_hits
            ),
            "evaluated_member_count": evaluated_count,
            "selected_first_complete_pass": selected is not None,
            "rejection_counts": dict(sorted(rejection_counts.items())),
            "first_counterexamples": first_counterexamples,
            "best_immutable_counterexample": best_immutable_counterexample,
            "immutable_witness_frequency": [
                {"source_face_id": face_id, "member_count": count}
                for face_id, count in sorted(
                    immutable_witness_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "collision_cache_entry_count": len(collision_cache),
            "collision_cache_hit_count": collision_cache_hits,
        },
        "selection": selected,
        "invariants": {
            "frozen_hashes_match": True,
            "frozen_family_fingerprint_matches": (
                family["finite_family"]["fingerprint"]
                == "6b0ee763889e4bbac7af1d638ec0f1e14b709098fcfbdcb12c910d7dc5a458a9"
            ),
            "evaluation_order_fingerprinted_before_member_evaluation": True,
            "minimum_width_axis_begins_at_12_mm": (
                parameter_order[0]["requested_empty_chord_width_mm"] == 12
            ),
            "no_floor_used_as_geometry_or_seed": True,
            "no_candidate_geometry_emitted": True,
            "diagnostic_does_not_reclassify_immutable_faces": True,
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
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "family_fingerprint": result["family_fingerprint"],
        "evaluation_order_fingerprint": evaluation_order["fingerprint"],
        "complete_member_count": evaluation_order["complete_member_count"],
        "start_member": args.start_member,
        "evaluated_member_count": evaluated_count,
        "selected_member_index": (
            selected["member_index"] if selected is not None else None
        ),
        "selected_member_fingerprint": (
            selected["fingerprint"] if selected is not None else None
        ),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
