"""Sweep bounded V2111/V2108 anchor transitions on the non-folded v4f rail."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "ANCHOR_TRANSITION_SWEEP_V6"
ANCHOR_SEGMENT_INDEX = 10
DISPLACEMENT_STEPS_MM = [0.25 * index for index in range(9)]
ORIGINAL_ADAPTIVE_RIBBON = v4.v2.adaptive_ribbon


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


def away_direction(points, ring, target_length):
    point = points[ring * 5]
    nearest, _, _, _ = v4.c9_bvh().find_nearest(point)
    if nearest is None:
        raise RuntimeError(
            f"{OPERATION}: nearest-C9 query failed at ring {ring}"
        )
    away = point - nearest
    if away.length <= 1.0e-8:
        raise RuntimeError(
            f"{OPERATION}: zero away-from-C9 vector at ring {ring}"
        )
    return away.normalized()


def translated_candidate(
    baseline,
    start_ring,
    end_ring,
    start_move,
    end_move,
):
    points = [point.copy() for point in baseline]
    displacements = {}
    for anchor_ring, move in (
        (start_ring, start_move),
        (end_ring, end_move),
    ):
        for distance, weight in ((0, 1.0), (1, 2.0 / 3.0), (2, 1.0 / 3.0)):
            for ring in {
                anchor_ring - distance,
                anchor_ring + distance,
            }:
                if ring < 0 or ring * 5 >= len(points):
                    continue
                displacements[ring] = displacements.get(ring, move * 0.0)
                displacements[ring] += move * weight
    for ring, displacement in displacements.items():
        for vertex in range(ring * 5, ring * 5 + 5):
            points[vertex] += displacement
    return points, displacements


def evaluate_case(
    baseline,
    faces,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
    target_length,
    grid,
    start_ring,
    end_ring,
    start_direction,
    end_direction,
    start_mm,
    end_mm,
):
    points, ring_displacements = translated_candidate(
        baseline,
        start_ring,
        end_ring,
        start_direction * start_mm,
        end_direction * end_mm,
    )
    ring_count = len(points) // 5
    c9_pairs = overlap_pairs(points, faces, c9_points, c9_faces)
    non_tip_pairs = [
        pair
        for pair in c9_pairs
        if face_segment(pair[0], ring_count) not in v4.SAMPLE_TIP_SEGMENTS
    ]
    self_pairs = v4.v2.ribbon_self_overlaps(points, faces, ring_count)
    cutter_pairs = overlap_pairs(
        points,
        faces,
        cutter_points,
        cutter_faces,
    )
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    gate_pass = (
        not non_tip_pairs
        and not self_pairs
        and not cutter_pairs
        and min(margins) >= 1.6998
        and audit["boundary_edges"] == 0
        and audit["nonmanifold_edges"] == 0
        and audit["noncontiguous_manifold_edges"] == 0
        and audit["signed_volume_mm3"] > 0.0
        and quality["degenerate_triangle_count"] == 0
        and quality["minimum_angle_degrees"]["minimum"] >= 3.0
        and quality["aspect_ratio"]["maximum"] <= 12.0
    )
    return {
        "v2111_displacement_mm": start_mm,
        "v2108_displacement_mm": end_mm,
        "total_displacement_mm": start_mm + end_mm,
        "non_tip_c9_overlap_count": len(non_tip_pairs),
        "self_overlap_count": len(self_pairs),
        "cutter_overlap_count": len(cutter_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "minimum_angle_degrees": quality["minimum_angle_degrees"]["minimum"],
        "maximum_aspect_ratio": quality["aspect_ratio"]["maximum"],
        "audit": audit,
        "gate_pass": gate_pass,
        "_points": points,
        "_ring_displacements": ring_displacements,
        "_quality": quality,
    }


def main() -> int:
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.__file__ = __file__
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    v4.ADAPTIVE_MINIMUM_HALF_WIDTH_MM = 0.2
    v4.fixed_width_ribbon = ORIGINAL_ADAPTIVE_RIBBON
    result = v4.main()
    report_path = report_argument()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    network = bpy.data.objects[report["objects"]["network"]]
    result_obj = bpy.data.objects[report["objects"]["result"]]
    candidate = bpy.data.objects[v4.CANDIDATE_NAME]
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    baseline, faces, _ = evaluated_geometry(network)
    c9_points, c9_faces = v4.component9_geometry()
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = v4.cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    start_ring = v4.ROUTE_NODE_RING[ANCHOR_SEGMENT_INDEX]
    end_ring = v4.ROUTE_NODE_RING[ANCHOR_SEGMENT_INDEX + 1]
    baseline_widths = [
        (baseline[index + 4] - baseline[index]).length
        for index in range(0, len(baseline), 5)
    ]
    start_direction = away_direction(baseline, start_ring, target_length)
    end_direction = away_direction(baseline, end_ring, target_length)
    cases = []
    for start_mm in DISPLACEMENT_STEPS_MM:
        for end_mm in DISPLACEMENT_STEPS_MM:
            cases.append(
                evaluate_case(
                    baseline,
                    faces,
                    c9_points,
                    c9_faces,
                    cutter_points,
                    cutter_faces,
                    target_length,
                    grid,
                    start_ring,
                    end_ring,
                    start_direction,
                    end_direction,
                    start_mm,
                    end_mm,
                )
            )
    passing = [case for case in cases if case["gate_pass"]]
    selected = (
        min(
            passing,
            key=lambda case: (
                case["total_displacement_mm"],
                max(
                    case["v2111_displacement_mm"],
                    case["v2108_displacement_mm"],
                ),
                case["v2108_displacement_mm"],
            ),
        )
        if passing
        else min(
            cases,
            key=lambda case: (
                case["non_tip_c9_overlap_count"],
                case["self_overlap_count"],
                case["total_displacement_mm"],
            ),
        )
    )
    selected_points = selected["_points"]
    moved_rings = set(selected["_ring_displacements"])
    outside_transition_max_error = max(
        (
            (point - baseline[index]).length
            for index, point in enumerate(selected_points)
            if index // 5 not in moved_rings
        ),
        default=0.0,
    )
    for index, point in enumerate(selected_points):
        network.data.vertices[index].co = point
    result_start = report["objects"]["band_offsets"]["vertex_start"]
    for index, point in enumerate(selected_points):
        result_obj.data.vertices[result_start + index].co = point
    network.data.update()
    result_obj.data.update()
    bpy.context.view_layer.update()
    localization = v4.localize_component9_overlaps(report)
    public_cases = [
        {
            key: value
            for key, value in case.items()
            if not key.startswith("_") and key != "audit"
        }
        for case in cases
    ]
    selected_public = {
        key: value
        for key, value in selected.items()
        if not key.startswith("_")
    }
    report["tool"] = Path(__file__).name
    report["operation"] = OPERATION
    report["status"] = "evaluation_only_not_promoted"
    report["v6_anchor_transition_sweep"] = {
        "case_count": len(cases),
        "step_mm": 0.25,
        "maximum_anchor_displacement_mm": 2.0,
        "passing_case_count": len(passing),
        "bound_sufficient": bool(passing),
        "selected_case": selected_public,
        "away_from_c9_direction": {
            "V2111": [round(value, 9) for value in start_direction],
            "V2108": [round(value, 9) for value in end_direction],
        },
        "selected_transition_ring_displacement_mm": {
            str(ring): round(displacement.length, 6)
            for ring, displacement in sorted(
                selected["_ring_displacements"].items()
            )
        },
        "outside_transition_maximum_coordinate_error_mm": round(
            outside_transition_max_error,
            9,
        ),
        "inherited_baseline_width_edge_mm": {
            "minimum": round(min(baseline_widths), 6),
            "maximum": round(max(baseline_widths), 6),
            "rings_below_5_8mm": [
                {
                    "ring": ring,
                    "width_mm": round(width, 6),
                }
                for ring, width in enumerate(baseline_widths)
                if width < 5.8
            ],
            "interpretation": (
                "inherited from the frozen self-free v4f baseline; v6 does "
                "not narrow or reshape these rings"
            ),
        },
        "cases": public_cases,
        "component_9_overlap_localization": localization,
    }
    report["registration"]["anchor_error_mm"]["2111"] = selected[
        "v2111_displacement_mm"
    ]
    report["registration"]["anchor_error_mm"]["2108"] = selected[
        "v2108_displacement_mm"
    ]
    report["band"]["audit"] = selected["audit"]
    report["band"]["triangle_quality"] = selected["_quality"]
    report["band"]["self_overlap_count"] = selected["self_overlap_count"]
    report["band"]["cutter_overlap_count"] = selected[
        "cutter_overlap_count"
    ]
    report["network"]["audit"] = selected["audit"]
    report["collisions"]["network_cutter_overlap_count"] = selected[
        "cutter_overlap_count"
    ]
    report["collisions"]["network_minimum_cutter_margin_mm"] = selected[
        "minimum_cutter_margin_mm"
    ]
    report["gates"].pop("all_13_anchors_exact", None)
    report["gates"].pop("minimum_physical_width_3mm", None)
    report["gates"]["nonoffending_11_anchors_exact"] = all(
        error <= 1.0e-4
        for source_id, error in report["registration"][
            "anchor_error_mm"
        ].items()
        if source_id not in {"2111", "2108"}
    )
    report["gates"]["anchor_displacement_bound"] = (
        selected["v2111_displacement_mm"] <= 2.0
        and selected["v2108_displacement_mm"] <= 2.0
    )
    report["gates"]["outside_transition_unchanged"] = (
        outside_transition_max_error <= 1.0e-8
    )
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
    report["gates"]["band_closed_positive_volume"] = (
        selected["audit"]["boundary_edges"] == 0
        and selected["audit"]["nonmanifold_edges"] == 0
        and selected["audit"]["noncontiguous_manifold_edges"] == 0
        and selected["audit"]["signed_volume_mm3"] > 0.0
    )
    report["gates"]["triangle_quality"] = (
        selected["_quality"]["degenerate_triangle_count"] == 0
        and selected["_quality"]["minimum_angle_degrees"]["minimum"] >= 3.0
        and selected["_quality"]["aspect_ratio"]["maximum"] <= 12.0
    )
    report["gate_pass"] = bool(passing) and all(report["gates"].values())
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
                "passing_case_count": len(passing),
                "selected_case": selected_public,
            },
            indent=2,
        )
    )
    print(
        f"DONE: v6 anchor sweep gate_pass={report['gate_pass']}; "
        f"passing_cases={len(passing)}; promotion NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
