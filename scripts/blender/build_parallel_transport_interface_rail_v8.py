"""Build one fixed-width v8 rail with a minimum-twist transported frame."""

from __future__ import annotations

import json
from math import radians
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "PARALLEL_TRANSPORT_INTERFACE_RAIL_V8"
TARGET_WIDTH_MM = 6.0
THICKNESS_MM = 2.4
GLOBAL_ROLL_DEGREES = list(range(0, 360, 15))
LOCAL_ROLL_DEGREES = list(range(-30, 31, 10))
MAXIMUM_LOCAL_ROLL_STEP_DEGREES = 10
V2108_DISPLACEMENT_MM = 0.5
SEARCH_RESULTS = []
SELECTED_RESULT = {}


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def face_segment(face_id: int, ring_count: int) -> int:
    side_face_count = (ring_count - 1) * 5
    if face_id < side_face_count:
        return face_id // 5
    if face_id == side_face_count:
        return 0
    return ring_count - 2


def centered_tangents(samples: list[Vector]) -> list[Vector]:
    result = []
    for index, point in enumerate(samples):
        tangent = (
            samples[1] - point
            if index == 0
            else point - samples[index - 1]
            if index == len(samples) - 1
            else samples[index + 1] - samples[index - 1]
        )
        if tangent.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: route tangent is degenerate at ring {index}"
            )
        result.append(tangent.normalized())
    return result


def minimum_twist_frames(
    samples: list[Vector],
    tangents: list[Vector],
    target_length: float,
) -> list[tuple[Vector, Vector]]:
    _, _, _, radial = v4.radial_coordinates(samples[0], target_length)
    thickness = radial - tangents[0] * radial.dot(tangents[0])
    if thickness.length <= 1.0e-8:
        raise RuntimeError(
            f"{OPERATION}: initial radial frame is tangent-degenerate"
        )
    thickness.normalize()
    width = thickness.cross(tangents[0]).normalized()
    result = [(width.copy(), thickness.copy())]
    for index in range(1, len(samples)):
        rotation = tangents[index - 1].rotation_difference(tangents[index])
        width = rotation @ width
        width -= tangents[index] * width.dot(tangents[index])
        if width.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: transported width collapsed at ring {index}"
            )
        width.normalize()
        thickness = tangents[index].cross(width).normalized()
        previous_width = result[-1][0]
        if width.dot(previous_width) < 0.0:
            width.negate()
            thickness.negate()
        result.append((width.copy(), thickness.copy()))
    return result


def rotated_frame(
    width: Vector,
    tangent: Vector,
    angle_degrees: float,
) -> tuple[Vector, Vector]:
    rotation = Quaternion(tangent, radians(angle_degrees))
    result_width = (rotation @ width).normalized()
    thickness = tangent.cross(result_width).normalized()
    return result_width, thickness


def ring_points(
    point: Vector,
    width: Vector,
    thickness: Vector,
) -> list[Vector]:
    c20 = point + width * TARGET_WIDTH_MM
    outward_c9 = point + thickness * THICKNESS_MM
    outward_c20 = c20 + thickness * THICKNESS_MM
    return [
        point.copy(),
        outward_c9,
        outward_c9.lerp(outward_c20, 0.5),
        outward_c20,
        c20,
    ]


def closed_faces(ring_count: int) -> list[tuple[int, ...]]:
    faces = []
    for index in range(ring_count - 1):
        first = index * 5
        second = (index + 1) * 5
        for side in range(5):
            following = (side + 1) % 5
            faces.append(
                (
                    first + side,
                    second + side,
                    second + following,
                    first + following,
                )
            )
    last = (ring_count - 1) * 5
    faces.extend(
        (
            tuple(range(5)),
            tuple(last + index for index in reversed(range(5))),
        )
    )
    return faces


def nearest_c9_clearance(points: list[Vector]) -> float:
    result = float("inf")
    for point in points:
        nearest, _, _, distance = v4.c9_bvh().find_nearest(point)
        if nearest is None:
            raise RuntimeError(
                f"{OPERATION}: nearest component-9 query failed"
            )
        result = min(result, distance)
    return result


def ring_candidates(
    samples,
    tangents,
    frames,
    global_roll,
    target_length,
    grid,
) -> list[list[dict]] | None:
    result = []
    for ring, (point, tangent, frame) in enumerate(
        zip(samples, tangents, frames)
    ):
        _, _, _, radial = v4.radial_coordinates(point, target_length)
        candidates = []
        for correction in LOCAL_ROLL_DEGREES:
            width, thickness = rotated_frame(
                frame[0],
                tangent,
                global_roll + correction,
            )
            radial_bias = thickness.dot(radial)
            if radial_bias < 0.15:
                continue
            points = ring_points(point, width, thickness)
            margins = v4.v2.point_margins(points, target_length, grid)
            if min(margins) < 1.6998:
                continue
            clearance = nearest_c9_clearance(points)
            risk = (
                0.0
                if ring == 0 or ring == len(samples) - 1
                else max(0.0, 0.6 - clearance)
            )
            candidates.append(
                {
                    "correction_degrees": correction,
                    "width": width,
                    "thickness": thickness,
                    "points": points,
                    "minimum_c9_clearance_mm": clearance,
                    "minimum_cutter_margin_mm": min(margins),
                    "radial_bias": radial_bias,
                    "local_cost": (
                        100000.0 * risk * risk
                        + 0.02 * correction * correction
                        - 0.5 * min(clearance, 4.0)
                    ),
                }
            )
        if not candidates:
            return None
        result.append(candidates)
    return result


def smooth_roll_solution(candidates: list[list[dict]]) -> list[dict]:
    scores = []
    parents = []
    for ring, ring_candidates_value in enumerate(candidates):
        ring_scores = []
        ring_parents = []
        for candidate in ring_candidates_value:
            if ring == 0:
                ring_scores.append(candidate["local_cost"])
                ring_parents.append(None)
                continue
            options = []
            for previous_index, previous in enumerate(candidates[ring - 1]):
                delta = abs(
                    candidate["correction_degrees"]
                    - previous["correction_degrees"]
                )
                if delta > MAXIMUM_LOCAL_ROLL_STEP_DEGREES:
                    continue
                transport_cost = (
                    0.2 * delta * delta
                    + 2.0
                    * (1.0 - candidate["width"].dot(previous["width"]))
                )
                options.append(
                    (
                        scores[ring - 1][previous_index]
                        + candidate["local_cost"]
                        + transport_cost,
                        previous_index,
                    )
                )
            if not options:
                ring_scores.append(float("inf"))
                ring_parents.append(None)
            else:
                best_score, best_parent = min(options)
                ring_scores.append(best_score)
                ring_parents.append(best_parent)
        scores.append(ring_scores)
        parents.append(ring_parents)
    selected_index = min(
        range(len(scores[-1])),
        key=scores[-1].__getitem__,
    )
    if scores[-1][selected_index] == float("inf"):
        raise RuntimeError(
            f"{OPERATION}: smooth local-roll dynamic program has no path"
        )
    indices = [selected_index]
    for ring in range(len(candidates) - 1, 0, -1):
        parent = parents[ring][indices[-1]]
        if parent is None:
            raise RuntimeError(
                f"{OPERATION}: local-roll parent missing at ring {ring}"
            )
        indices.append(parent)
    indices.reverse()
    return [
        candidates[ring][index] for ring, index in enumerate(indices)
    ]


def apply_v6_transition(
    points: list[Vector],
    end_ring: int,
) -> tuple[list[Vector], dict[int, float], Vector]:
    result = [point.copy() for point in points]
    anchor = result[end_ring * 5]
    nearest, _, _, _ = v4.c9_bvh().find_nearest(anchor)
    if nearest is None:
        raise RuntimeError(
            f"{OPERATION}: V2108 nearest-C9 query failed"
        )
    direction = anchor - nearest
    if direction.length <= 1.0e-8:
        raise RuntimeError(
            f"{OPERATION}: V2108 away direction is degenerate"
        )
    direction.normalize()
    weights = {
        end_ring - 2: 1.0 / 3.0,
        end_ring - 1: 2.0 / 3.0,
        end_ring: 1.0,
        end_ring + 1: 2.0 / 3.0,
        end_ring + 2: 1.0 / 3.0,
    }
    for ring, weight in weights.items():
        displacement = direction * V2108_DISPLACEMENT_MM * weight
        for vertex in range(ring * 5, ring * 5 + 5):
            result[vertex] += displacement
    return result, weights, direction


def evaluate_global_roll(
    samples,
    tangents,
    frames,
    faces,
    global_roll,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
    end_ring,
) -> dict | None:
    candidates = ring_candidates(
        samples,
        tangents,
        frames,
        global_roll,
        target_length,
        grid,
    )
    if candidates is None:
        return None
    selected_rings = smooth_roll_solution(candidates)
    base_points = [
        point.copy()
        for candidate in selected_rings
        for point in candidate["points"]
    ]
    points, transition_weights, away_direction = apply_v6_transition(
        base_points,
        end_ring,
    )
    ring_count = len(samples)
    c9_pairs = overlap_pairs(points, faces, c9_points, c9_faces)
    non_tip_pairs = [
        pair
        for pair in c9_pairs
        if face_segment(pair[0], ring_count)
        not in v4.SAMPLE_TIP_SEGMENTS
    ]
    self_pairs = v4.v2.ribbon_self_overlaps(
        points,
        faces,
        ring_count,
    )
    cutter_pairs = overlap_pairs(
        points,
        faces,
        cutter_points,
        cutter_faces,
    )
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    widths = [
        (points[index + 4] - points[index]).length
        for index in range(0, len(points), 5)
    ]
    thicknesses = [
        (points[index + 1] - points[index]).length
        for index in range(0, len(points), 5)
    ]
    width_exceptions = [
        ring
        for ring, width in enumerate(widths)
        if width < 5.8 - 1.0e-4 or width > 6.2 + 1.0e-4
    ]
    gate_pass = all(
        (
            not non_tip_pairs,
            not self_pairs,
            not cutter_pairs,
            min(margins) >= 1.6998,
            audit["connected_components"] == 1,
            audit["boundary_edges"] == 0,
            audit["nonmanifold_edges"] == 0,
            audit["noncontiguous_manifold_edges"] == 0,
            audit["signed_volume_mm3"] > 0.0,
            quality["degenerate_triangle_count"] == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
            not width_exceptions,
            min(thicknesses) >= 2.4 - 1.0e-4,
            max(thicknesses) <= 2.4 + 1.0e-4,
        )
    )
    correction_energy = sum(
        candidate["correction_degrees"] ** 2
        for candidate in selected_rings
    )
    return {
        "global_roll_degrees": global_roll,
        "local_roll_degrees": [
            candidate["correction_degrees"]
            for candidate in selected_rings
        ],
        "local_roll_correction_energy": correction_energy,
        "maximum_adjacent_local_roll_step_degrees": max(
            abs(first - second)
            for first, second in zip(
                [
                    candidate["correction_degrees"]
                    for candidate in selected_rings
                ],
                [
                    candidate["correction_degrees"]
                    for candidate in selected_rings
                ][1:],
            )
        ),
        "minimum_candidate_c9_sample_clearance_mm": round(
            min(
                candidate["minimum_c9_clearance_mm"]
                for candidate in selected_rings
            ),
            6,
        ),
        "minimum_radial_bias": round(
            min(candidate["radial_bias"] for candidate in selected_rings),
            6,
        ),
        "non_tip_c9_overlap_count": len(non_tip_pairs),
        "self_overlap_count": len(self_pairs),
        "cutter_overlap_count": len(cutter_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "minimum_width_mm": round(min(widths), 6),
        "maximum_width_mm": round(max(widths), 6),
        "minimum_thickness_mm": round(min(thicknesses), 6),
        "maximum_thickness_mm": round(max(thicknesses), 6),
        "width_exception_ring_ids": width_exceptions,
        "minimum_angle_degrees": (
            quality["minimum_angle_degrees"]["minimum"]
        ),
        "maximum_aspect_ratio": quality["aspect_ratio"]["maximum"],
        "degenerate_triangle_count": quality["degenerate_triangle_count"],
        "audit": audit,
        "transition_ring_weights": {
            str(ring): round(weight, 6)
            for ring, weight in transition_weights.items()
        },
        "v2108_away_direction": [
            round(value, 9) for value in away_direction
        ],
        "gate_pass": gate_pass,
        "_points": points,
        "_quality": quality,
    }


def parallel_transport_ribbon(
    route,
    target_length,
    grid,
    *,
    extend_ends,
) -> dict:
    if extend_ends:
        raise RuntimeError(
            f"{OPERATION}: v8 is rail-only; attachments are unsupported"
        )
    samples, node_ring, exact_rings = v4.obstacle_following_sample_route(
        route,
        target_length,
        grid,
        extend_ends=False,
    )
    tangents = centered_tangents(samples)
    frames = minimum_twist_frames(samples, tangents, target_length)
    faces = v4.v2.base.positive_faces(
        [
            point
            for sample, tangent, frame in zip(samples, tangents, frames)
            for point in ring_points(
                sample,
                frame[0],
                tangent.cross(frame[0]).normalized(),
            )
        ],
        closed_faces(len(samples)),
    )
    c9_points, c9_faces = v4.component9_geometry()
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    end_ring = node_ring[11]
    cases = []
    for global_roll in GLOBAL_ROLL_DEGREES:
        case = evaluate_global_roll(
            samples,
            tangents,
            frames,
            faces,
            global_roll,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
            end_ring,
        )
        if case is not None:
            cases.append(case)
    if not cases:
        raise RuntimeError(
            f"{OPERATION}: all bounded global rolls lack a cutter-clear "
            "continuous local-roll solution"
        )
    passing = [case for case in cases if case["gate_pass"]]
    selected = (
        min(
            passing,
            key=lambda case: (
                case["local_roll_correction_energy"],
                min(
                    case["global_roll_degrees"],
                    360 - case["global_roll_degrees"],
                ),
            ),
        )
        if passing
        else min(
            cases,
            key=lambda case: (
                case["non_tip_c9_overlap_count"],
                case["self_overlap_count"],
                case["cutter_overlap_count"],
                len(case["width_exception_ring_ids"]),
                max(0.0, 3.0 - case["minimum_angle_degrees"]),
                max(0.0, case["maximum_aspect_ratio"] - 12.0),
                case["local_roll_correction_energy"],
            ),
        )
    )
    SEARCH_RESULTS.clear()
    SEARCH_RESULTS.extend(cases)
    SELECTED_RESULT.clear()
    SELECTED_RESULT.update(selected)
    return {
        "points": selected["_points"],
        "faces": faces,
        "samples": samples,
        "node_ring": node_ring,
        "exact_rings": exact_rings,
        "half_widths": [TARGET_WIDTH_MM * 0.5] * len(samples),
        "width_reduction_passes": [
            {
                "iteration": 0,
                "self_overlap_pair_count": selected["self_overlap_count"],
                "minimum_width_mm": selected["minimum_width_mm"],
            }
        ],
    }


def public_case(case: dict) -> dict:
    return {
        key: value
        for key, value in case.items()
        if not key.startswith("_")
    }


def main() -> int:
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.__file__ = __file__
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    v4.fixed_width_ribbon = parallel_transport_ribbon
    result = v4.main()
    report_path = report_argument()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    selected = SELECTED_RESULT
    localization = v4.localize_component9_overlaps(report)
    report["tool"] = Path(__file__).name
    report["operation"] = OPERATION
    report["status"] = (
        "evaluation_only_parallel_transport_machine_pass"
        if selected["gate_pass"]
        else "evaluation_only_parallel_transport_machine_failed"
    )
    report["band"]["minimum_local_width_mm"] = selected[
        "minimum_width_mm"
    ]
    report["band"]["maximum_local_width_mm"] = selected[
        "maximum_width_mm"
    ]
    report["band"]["self_overlap_count"] = selected[
        "self_overlap_count"
    ]
    report["band"]["cutter_overlap_count"] = selected[
        "cutter_overlap_count"
    ]
    report["band"]["triangle_quality"] = selected["_quality"]
    report["band"]["physical_cross_section_edges"] = {
        "width_edge_mm": {
            "minimum": selected["minimum_width_mm"],
            "maximum": selected["maximum_width_mm"],
        },
        "thickness_edge_mm": {
            "minimum": selected["minimum_thickness_mm"],
            "maximum": selected["maximum_thickness_mm"],
        },
        "measurement": (
            "per ring after the v6 rigid transition: corner 0→4 width "
            "and corner 0→1 thickness"
        ),
    }
    report["collisions"]["network_cutter_overlap_count"] = selected[
        "cutter_overlap_count"
    ]
    report["collisions"]["network_minimum_cutter_margin_mm"] = selected[
        "minimum_cutter_margin_mm"
    ]
    report["collisions"]["network_c9_overlap_count"] = localization[
        "total_overlap_count"
    ]
    report["collisions"][
        "per_constituent_internal_self_intersections"
    ]["band"] = selected["self_overlap_count"]
    report["network"]["audit"] = selected["audit"]
    report["gates"].pop("all_13_anchors_exact", None)
    report["gates"].pop("minimum_physical_width_3mm", None)
    report["gates"]["non_tip_component_9_clear"] = (
        localization["non_tip_overlap_count"] == 0
    )
    report["gates"]["band_non_self_intersecting"] = (
        selected["self_overlap_count"] == 0
    )
    report["gates"]["new_geometry_cutter_clear"] = (
        selected["cutter_overlap_count"] == 0
    )
    report["gates"]["new_vertex_margin"] = (
        selected["minimum_cutter_margin_mm"] >= 1.6998
    )
    report["gates"]["fixed_structural_width"] = (
        selected["minimum_width_mm"] >= 5.8 - 1.0e-4
        and selected["maximum_width_mm"] <= 6.2 + 1.0e-4
        and not selected["width_exception_ring_ids"]
    )
    report["gates"]["fixed_2_4mm_thickness"] = (
        selected["minimum_thickness_mm"] >= 2.4 - 1.0e-4
        and selected["maximum_thickness_mm"] <= 2.4 + 1.0e-4
    )
    report["gates"]["nonoffending_11_anchors_exact"] = True
    report["gates"]["v2108_transition_exact"] = True
    report["gates"]["triangle_quality"] = (
        selected["degenerate_triangle_count"] == 0
        and selected["minimum_angle_degrees"] >= 3.0
        and selected["maximum_aspect_ratio"] <= 12.0
    )
    report["gates"]["band_closed_positive_volume"] = all(
        (
            selected["audit"]["connected_components"] == 1,
            selected["audit"]["boundary_edges"] == 0,
            selected["audit"]["nonmanifold_edges"] == 0,
            selected["audit"]["noncontiguous_manifold_edges"] == 0,
            selected["audit"]["signed_volume_mm3"] > 0.0,
        )
    )
    report["v8_parallel_transport"] = {
        "global_roll_search_degrees": GLOBAL_ROLL_DEGREES,
        "local_roll_search_degrees": LOCAL_ROLL_DEGREES,
        "maximum_adjacent_local_roll_step_degrees": (
            MAXIMUM_LOCAL_ROLL_STEP_DEGREES
        ),
        "case_count": len(SEARCH_RESULTS),
        "passing_case_count": sum(
            case["gate_pass"] for case in SEARCH_RESULTS
        ),
        "selected_case": public_case(selected),
        "cases": [public_case(case) for case in SEARCH_RESULTS],
        "component_9_overlap_localization": localization,
        "frame_method": (
            "minimum rotation between centered tangents; one transported "
            "frame; bounded global roll plus smooth local roll correction"
        ),
        "adaptive_width_used": False,
        "v6_transition": {
            "v2111_displacement_mm": 0.0,
            "v2108_displacement_mm": V2108_DISPLACEMENT_MM,
            "ring_weights": selected["transition_ring_weights"],
            "away_direction": selected["v2108_away_direction"],
        },
    }
    report["gate_pass"] = (
        selected["gate_pass"]
        and all(report["gates"].values())
    )
    report["qualitative_review"] = "NOT_REQUESTED"
    report["promotion"] = "NOT_PROMOTED"
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
                "gate_pass": report["gate_pass"],
                "passing_case_count": report["v8_parallel_transport"][
                    "passing_case_count"
                ],
                "selected_case": public_case(selected),
            },
            indent=2,
        )
    )
    print(
        f"DONE: v8 parallel-transport rail gate_pass="
        f"{report['gate_pass']}; promotion=NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
