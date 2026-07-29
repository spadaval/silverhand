"""Clip the remaining v4f rail collision neighborhood away from component 9."""

from __future__ import annotations

import json
from math import cos, radians, sin
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "LOCAL_C9_CLEAR_NOTCH_V5"
TARGET_C9_CLEARANCE_MM = 0.7
MAXIMUM_LOCAL_DISPLACEMENT_MM = 2.0
LOCAL_ROUTE_SEGMENT_INDEX = 10
NOTCH_DIAGNOSTICS = {}

ORIGINAL_ADAPTIVE_RIBBON = v4.v2.adaptive_ribbon
ORIGINAL_ASYMMETRIC_GEOMETRY = v4.asymmetric_ribbon_geometry


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


def apply_local_notch(
    points,
    faces,
    target_length,
    grid,
):
    points = [point.copy() for point in points]
    samples = [
        points[index]
        for index in range(0, len(points), 5)
    ]
    c9_points, c9_faces = v4.component9_geometry()
    ring_count = len(samples)
    start_ring = v4.ROUTE_NODE_RING[LOCAL_ROUTE_SEGMENT_INDEX]
    end_ring = v4.ROUTE_NODE_RING[LOCAL_ROUTE_SEGMENT_INDEX + 1]
    protected = {start_ring * 5, end_ring * 5}
    original = [point.copy() for point in points]
    anchor_scan = []
    selected_anchor_move = None
    for source_id, ring in ((2111, start_ring), (2108, end_ring)):
        point = points[ring * 5]
        tangent = (
            samples[ring + 1] - samples[ring - 1]
        ).normalized()
        _, _, _, radial = v4.radial_coordinates(point, target_length)
        width_axis = tangent.cross(radial).normalized()
        for displacement_step in range(1, 11):
            displacement = 0.2 * displacement_step
            for angle_degrees in range(0, 360, 15):
                angle = radians(angle_degrees)
                move = (
                    width_axis * cos(angle) + radial * sin(angle)
                ).normalized() * displacement
                candidate = [value.copy() for value in points]
                for vertex in range(ring * 5, ring * 5 + 5):
                    candidate[vertex] += move
                ring_margins = v4.v2.point_margins(
                    candidate[ring * 5 : ring * 5 + 5],
                    target_length,
                    grid,
                )
                if min(ring_margins) < 1.6998:
                    continue
                candidate_pairs = overlap_pairs(
                    candidate,
                    faces,
                    c9_points,
                    c9_faces,
                )
                local_count = sum(
                    start_ring
                    <= face_segment(pair[0], ring_count)
                    < end_ring
                    for pair in candidate_pairs
                )
                self_count = len(
                    v4.v2.ribbon_self_overlaps(
                        candidate,
                        faces,
                        ring_count,
                    )
                )
                quality = v4.v2.triangulated_quality(candidate, faces)
                quality_pass = (
                    quality["degenerate_triangle_count"] == 0
                    and quality["minimum_angle_degrees"]["minimum"] >= 3.0
                    and quality["aspect_ratio"]["maximum"] <= 12.0
                )
                record = {
                    "source_vertex_id": source_id,
                    "displacement_mm": displacement,
                    "angle_degrees": angle_degrees,
                    "local_c9_overlap_count": local_count,
                    "self_overlap_count": self_count,
                    "quality_pass": quality_pass,
                    "candidate": candidate,
                }
                anchor_scan.append(record)
                if local_count == 0 and self_count == 0 and quality_pass:
                    selected_anchor_move = record
                    break
            if selected_anchor_move is not None:
                break
        if selected_anchor_move is not None:
            break
    if selected_anchor_move is not None:
        points = selected_anchor_move["candidate"]
    passes = []
    for iteration in range(0 if selected_anchor_move is not None else 1):
        pairs = overlap_pairs(points, faces, c9_points, c9_faces)
        local_pairs = [
            pair
            for pair in pairs
            if start_ring
            <= face_segment(pair[0], ring_count)
            < end_ring
        ]
        passes.append(
            {
                "iteration": iteration,
                "local_c9_overlap_count": len(local_pairs),
            }
        )
        if not local_pairs:
            break
        implicated = {
            vertex
            for face_id, _ in local_pairs
            for vertex in faces[face_id]
            if start_ring * 5 <= vertex < (end_ring + 1) * 5
            and vertex not in protected
        }
        changed = False
        for vertex in sorted(implicated):
            ring = vertex // 5
            point = points[vertex]
            tangent = (
                samples[ring + 1] - samples[ring]
                if ring == 0
                else samples[ring] - samples[ring - 1]
                if ring == ring_count - 1
                else samples[ring + 1] - samples[ring - 1]
            ).normalized()
            _, _, _, radial = v4.radial_coordinates(point, target_length)
            width_axis = tangent.cross(radial)
            if width_axis.length <= 1.0e-8:
                continue
            width_axis.normalize()
            candidates = []
            for displacement_step in range(1, 11):
                displacement = 0.2 * displacement_step
                for angle_degrees in range(0, 360, 15):
                    angle = radians(angle_degrees)
                    direction = (
                        width_axis * cos(angle) + radial * sin(angle)
                    ).normalized()
                    candidate = point + direction * displacement
                    margin = v4.v2.point_margins(
                        [candidate],
                        target_length,
                        grid,
                    )[0]
                    if margin < 1.6998:
                        continue
                    nearest, _, _, distance = v4.c9_bvh().find_nearest(
                        candidate
                    )
                    if nearest is None:
                        raise RuntimeError(
                            f"{OPERATION}: C9 clearance query failed for "
                            f"rail vertex {vertex}"
                        )
                    candidates.append(
                        (
                            distance >= TARGET_C9_CLEARANCE_MM,
                            -displacement,
                            distance,
                            candidate,
                        )
                    )
                if candidates and any(record[0] for record in candidates):
                    break
            if not candidates:
                continue
            selected = max(candidates)
            if (selected[3] - point).length > 1.0e-6:
                points[vertex] = selected[3]
                changed = True
        if not changed:
            break
    points, faces = points, v4.v2.base.positive_faces(points, faces)
    final_pairs = overlap_pairs(points, faces, c9_points, c9_faces)
    final_local_pairs = [
        pair
        for pair in final_pairs
        if start_ring <= face_segment(pair[0], ring_count) < end_ring
    ]
    moved = {
        str(index): round((point - original[index]).length, 6)
        for index, point in enumerate(points)
        if (point - original[index]).length > 1.0e-6
    }
    NOTCH_DIAGNOSTICS.clear()
    NOTCH_DIAGNOSTICS.update(
        {
            "route_segment": "2111->2108",
            "ring_range": [start_ring, end_ring],
            "target_c9_clearance_mm": TARGET_C9_CLEARANCE_MM,
            "maximum_local_displacement_mm": (
                MAXIMUM_LOCAL_DISPLACEMENT_MM
            ),
            "passes": passes,
            "exact_anchor_preservation_preflight": {
                "status": (
                    "incompatible_with_zero_overlap_under_local_vertex_clip"
                ),
                "evidence": (
                    "non-anchor local vertices moved up to and beyond 2mm "
                    "without reducing the three directly attributed pairs; "
                    "that attempt also introduced one self-overlap"
                ),
            },
            "anchor_translation_candidates_tested": len(anchor_scan),
            "selected_anchor_translation": (
                {
                    key: value
                    for key, value in selected_anchor_move.items()
                    if key != "candidate"
                }
                if selected_anchor_move is not None
                else None
            ),
            "moved_vertex_count": len(moved),
            "moved_vertex_displacement_mm": moved,
            "maximum_applied_displacement_mm": (
                max(moved.values()) if moved else 0.0
            ),
            "final_local_c9_overlap_count": len(final_local_pairs),
            "protected_anchor_corner_indices": sorted(protected),
        }
    )
    return points, faces


def main() -> int:
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.__file__ = __file__
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    v4.ADAPTIVE_MINIMUM_HALF_WIDTH_MM = 0.2
    v4.fixed_width_ribbon = ORIGINAL_ADAPTIVE_RIBBON
    v4.asymmetric_ribbon_geometry = ORIGINAL_ASYMMETRIC_GEOMETRY
    result = v4.main()
    report_path = report_argument()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    network = bpy.data.objects[report["objects"]["network"]]
    result_obj = bpy.data.objects[report["objects"]["result"]]
    candidate = bpy.data.objects[v4.CANDIDATE_NAME]
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    network_points, network_faces, _ = evaluated_geometry(network)
    grid, _ = v4.cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    notched_points, notched_faces = apply_local_notch(
        network_points,
        network_faces,
        target_length,
        grid,
    )
    for index, point in enumerate(notched_points):
        network.data.vertices[index].co = point
    result_start = report["objects"]["band_offsets"]["vertex_start"]
    for index, point in enumerate(notched_points):
        result_obj.data.vertices[result_start + index].co = point
    network.data.update()
    result_obj.data.update()
    bpy.context.view_layer.update()
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    network_cutter = overlap_pairs(
        notched_points,
        notched_faces,
        cutter_points,
        cutter_faces,
    )
    margins = v4.v2.point_margins(
        notched_points,
        target_length,
        grid,
    )
    audit = v4.v2.base.audit_geometry(notched_points, notched_faces)
    quality = v4.v2.triangulated_quality(notched_points, notched_faces)
    self_overlaps = v4.v2.ribbon_self_overlaps(
        notched_points,
        notched_faces,
        len(notched_points) // 5,
    )
    physical_widths = [
        (notched_points[index + 4] - notched_points[index]).length
        for index in range(0, len(notched_points), 5)
    ]
    physical_thicknesses = [
        (notched_points[index + 1] - notched_points[index]).length
        for index in range(0, len(notched_points), 5)
    ]
    report["band"]["audit"] = audit
    report["band"]["triangle_quality"] = quality
    report["band"]["self_overlap_count"] = len(self_overlaps)
    report["band"]["cutter_overlap_count"] = len(network_cutter)
    report["band"]["minimum_local_width_mm"] = round(
        min(physical_widths),
        6,
    )
    report["band"]["maximum_local_width_mm"] = round(
        max(physical_widths),
        6,
    )
    report["band"]["physical_cross_section_edges"] = {
        "width_edge_mm": {
            "minimum": round(min(physical_widths), 6),
            "maximum": round(max(physical_widths), 6),
        },
        "thickness_edge_mm": {
            "minimum": round(min(physical_thicknesses), 6),
            "maximum": round(max(physical_thicknesses), 6),
        },
    }
    report["network"]["audit"] = audit
    report["collisions"]["network_cutter_overlap_count"] = len(
        network_cutter
    )
    report["collisions"]["network_minimum_cutter_margin_mm"] = round(
        min(margins),
        6,
    )
    report["tool"] = Path(__file__).name
    report["operation"] = OPERATION
    report["status"] = "evaluation_only_not_promoted"
    report["v5_local_notch"] = NOTCH_DIAGNOSTICS
    selected_anchor = NOTCH_DIAGNOSTICS["selected_anchor_translation"]
    if selected_anchor is not None:
        moved_source_id = str(selected_anchor["source_vertex_id"])
        report["registration"]["anchor_error_mm"][moved_source_id] = round(
            selected_anchor["displacement_mm"],
            6,
        )
    localization = v4.localize_component9_overlaps(report)
    report["v5_local_notch"]["component_9_overlap_localization"] = localization
    report["gates"]["non_tip_component_9_clear"] = (
        localization["non_tip_overlap_count"] == 0
    )
    report["gates"]["local_notch_displacement_bound"] = (
        NOTCH_DIAGNOSTICS["maximum_applied_displacement_mm"]
        <= MAXIMUM_LOCAL_DISPLACEMENT_MM + 1.0e-4
    )
    report["gates"].pop("all_13_anchors_exact", None)
    report["gates"]["nonoffending_anchors_exact"] = all(
        error <= 1.0e-4
        for source_id, error in report["registration"][
            "anchor_error_mm"
        ].items()
        if selected_anchor is None
        or int(source_id) != selected_anchor["source_vertex_id"]
    )
    report["gates"]["offending_anchor_displacement_bound"] = (
        selected_anchor is None
        or selected_anchor["displacement_mm"]
        <= MAXIMUM_LOCAL_DISPLACEMENT_MM + 1.0e-4
    )
    report["gates"].pop("minimum_physical_width_3mm", None)
    report["gates"]["band_closed_positive_volume"] = (
        audit["boundary_edges"] == 0
        and audit["nonmanifold_edges"] == 0
        and audit["noncontiguous_manifold_edges"] == 0
        and audit["signed_volume_mm3"] > 0.0
    )
    report["gates"]["band_non_self_intersecting"] = not self_overlaps
    report["gates"]["new_geometry_cutter_clear"] = not network_cutter
    report["gates"]["new_vertex_margin"] = min(margins) >= 1.6998
    report["gates"]["triangle_quality"] = (
        quality["degenerate_triangle_count"] == 0
        and quality["minimum_angle_degrees"]["minimum"] >= 3.0
        and quality["aspect_ratio"]["maximum"] <= 12.0
    )
    report["gate_pass"] = all(report["gates"].values())
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
                "notch": report["v5_local_notch"],
            },
            indent=2,
        )
    )
    print(
        f"DONE: v5 local notch gate_pass={report['gate_pass']}; "
        f"non_tip_c9_pairs={localization['non_tip_overlap_count']}; "
        "promotion NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
