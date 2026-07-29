"""Build terminal-only fan saddles on the proven Repair 014 v14 route."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import build_connection_aware_network_v12 as v12  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "SURFACE_FOLLOWING_FAN_SADDLES_V15"
TARGET_FAN_WIDTH_MM = 10.0
TARGET_LANDING_MM = 8.0
MIDSPAN_MINIMUM_WIDTH_MM = 4.5
MIDSPAN_SHOULDER_WIDTH_MM = 6.0
THICKNESS_MM = 2.4
MINIMUM_EMBED_MM = 1.5
AUTHORITY_BLEND_SHA256 = (
    "daff708f7decc737b82a3b4683366ee631324c958153f1054866709bcf08890a"
)
EXPECTED_RETAINED_FINGERPRINT = (
    "0a127654f1551f4935686df4827201ee3064151c2ecb49005854fc52d5965359"
)
V14_OBJECTS = (
    "EVAL_REPAIR_014_TERMINAL_BRIDGE_V14_AFTER",
    "EVAL_REPAIR_014_TERMINAL_BRIDGE_V14_NETWORK",
)
BASELINE_REPAIR_014_OBJECTS = {
    "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER",
    "EVAL_REPAIR_014_COORDINATED_INTERFACE_BEFORE",
    "EVAL_REPAIR_014_OPEN_CAGE_AFTER",
    "EVAL_REPAIR_014_OPEN_CAGE_BEFORE",
}
V14_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_upper_lower_terminal_bridge_v14/build_report.json"
)

# Search the review target first. Equal returned roll values preserve this order
# in v14's stable selection. Alternate rolls are fallbacks, not optimization.
CANDIDATES = [
    (width, embed, 120)
    for width in (10.0, 9.0, 11.0)
    for embed in (5.0, 4.0, 3.0)
]


def fan_width(distance_to_end: float, landing: float, fan_width_mm: float) -> float:
    """Two-stage terminal ramp ending in the retained 4.5 mm midspan."""
    plateau = min(2.5, landing * 0.32)
    first_shoulder = landing * 0.58
    second_shoulder = landing * 0.82
    if distance_to_end <= plateau:
        return fan_width_mm
    if distance_to_end <= first_shoulder:
        factor = (distance_to_end - plateau) / (first_shoulder - plateau)
        return fan_width_mm + factor * (8.0 - fan_width_mm)
    if distance_to_end <= second_shoulder:
        factor = (
            (distance_to_end - first_shoulder)
            / (second_shoulder - first_shoulder)
        )
        return 8.0 + factor * (MIDSPAN_SHOULDER_WIDTH_MM - 8.0)
    if distance_to_end <= landing:
        factor = (
            (distance_to_end - second_shoulder)
            / (landing - second_shoulder)
        )
        return (
            MIDSPAN_SHOULDER_WIDTH_MM
            + factor
            * (MIDSPAN_MINIMUM_WIDTH_MM - MIDSPAN_SHOULDER_WIDTH_MM)
        )
    return MIDSPAN_MINIMUM_WIDTH_MM


def saddle_geometry(
    upper_point,
    lower_point,
    fan_width_mm,
    embed_mm,
    roll_degrees,
    target_length,
):
    direction = lower_point - upper_point
    if direction.length <= 1.0e-8:
        raise RuntimeError(f"{OPERATION}: V5702-to-V1784 route is degenerate")
    direction.normalize()
    v14_start = upper_point - direction * v12.END_EMBED_MM
    v14_end = lower_point + direction * v12.END_EMBED_MM
    start = upper_point - direction * embed_mm
    end = lower_point + direction * embed_mm
    samples = v12.sampled_path([start, v14_start, v14_end, end])
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(samples, tangents, target_length)
    cumulative = [0.0]
    for first, second in zip(samples, samples[1:]):
        cumulative.append(cumulative[-1] + (second - first).length)
    total_length = cumulative[-1]
    landing = min(TARGET_LANDING_MM, total_length * 0.5)
    points = []
    widths = []
    for point, tangent, frame, distance in zip(
        samples,
        tangents,
        frames,
        cumulative,
    ):
        width_axis, thickness_axis = v8.rotated_frame(
            frame[0],
            tangent,
            roll_degrees,
        )
        distance_to_end = min(distance, total_length - distance)
        width = fan_width(distance_to_end, landing, fan_width_mm)
        widths.append(width)
        c20 = point + width_axis * width
        outer0 = point + thickness_axis * THICKNESS_MM
        outer1 = c20 + thickness_axis * THICKNESS_MM
        points.extend(
            (
                point.copy(),
                outer0,
                outer0.lerp(outer1, 0.5),
                outer1,
                c20,
            )
        )
    faces = v4.v2.base.positive_faces(points, v8.closed_faces(len(samples)))
    return points, faces, samples, widths, landing


def candidate(
    upper_point,
    lower_point,
    midpoint_offset,
    midpoint_angle,
    candidate_spec,
    target_length,
    grid,
    upper_geometry,
    lower_geometry,
    allowed_open_faces,
    open_points,
    open_faces,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    del midpoint_offset, midpoint_angle
    fan_width_mm, embed_mm, roll_degrees = candidate_spec
    points, faces, samples, widths, landing = saddle_geometry(
        upper_point,
        lower_point,
        fan_width_mm,
        embed_mm,
        roll_degrees,
        target_length,
    )
    upper_pairs = overlap_pairs(points, faces, *upper_geometry)
    lower_pairs = overlap_pairs(points, faces, *lower_geometry)
    full_pairs = overlap_pairs(points, faces, open_points, open_faces)
    unrelated_pairs = [
        pair for pair in full_pairs if pair[1] not in allowed_open_faces
    ]
    c9_pairs = overlap_pairs(points, faces, c9_points, c9_faces)
    cutter_pairs = overlap_pairs(points, faces, cutter_points, cutter_faces)
    self_pairs = v4.v2.ribbon_self_overlaps(points, faces, len(samples))
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    passed = all(
        (
            upper_pairs,
            lower_pairs,
            not unrelated_pairs,
            not c9_pairs,
            not cutter_pairs,
            not self_pairs,
            min(margins) >= 1.6998,
            audit["connected_components"] == 1,
            audit["boundary_edges"] == 0,
            audit["nonmanifold_edges"] == 0,
            audit["noncontiguous_manifold_edges"] == 0,
            audit["signed_volume_mm3"] > 0.0,
            min(widths) >= MIDSPAN_MINIMUM_WIDTH_MM - 1.0e-4,
            max(widths) <= fan_width_mm + 1.0e-4,
            quality["degenerate_triangle_count"] == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
        )
    )
    return {
        "midpoint_offset_mm": 0.0,
        "midpoint_angle_degrees": 0,
        "roll_degrees": roll_degrees,
        "ring_count": len(samples),
        "minimum_width_mm": round(min(widths), 6),
        "maximum_width_mm": round(max(widths), 6),
        "thickness_mm": THICKNESS_MM,
        "terminal_embed_mm": embed_mm,
        "target_terminal_landing_mm": TARGET_LANDING_MM,
        "realized_terminal_landing_mm": round(landing, 6),
        "width_profile_mm": [round(width, 6) for width in widths],
        "upper_terminal_overlap_count": len(upper_pairs),
        "lower_terminal_overlap_count": len(lower_pairs),
        "full_open_overlap_count": len(full_pairs),
        "unrelated_full_open_overlap_count": len(unrelated_pairs),
        "T_CAGE_2_overlap_count": 0 if not unrelated_pairs else None,
        "T_CAGE_3_overlap_count": 0 if not unrelated_pairs else None,
        "c9_overlap_count": len(c9_pairs),
        "cutter_overlap_count": len(cutter_pairs),
        "self_overlap_count": len(self_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "audit": audit,
        "triangle_quality": quality,
        "gate_pass": passed,
        "_points": points,
        "_faces": faces,
    }


def prepare_v14_authority() -> dict:
    blend_path = Path(bpy.data.filepath).resolve()
    blend_sha = v14.v10.sha256_file(blend_path)
    if blend_sha != AUTHORITY_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: authority Blend '{blend_path}' has SHA-256 "
            f"'{blend_sha}', expected '{AUTHORITY_BLEND_SHA256}'"
        )
    authority = json.loads(V14_REPORT_PATH.read_text(encoding="utf-8"))
    if not authority["gate_pass"]:
        raise RuntimeError(
            f"{OPERATION}: v14 authority report '{V14_REPORT_PATH}' did not pass"
        )
    if (
        authority["preservation"]["retained_fingerprint_after"]
        != EXPECTED_RETAINED_FINGERPRINT
    ):
        raise RuntimeError(
            f"{OPERATION}: v14 report retained fingerprint is "
            f"'{authority['preservation']['retained_fingerprint_after']}', "
            f"expected '{EXPECTED_RETAINED_FINGERPRINT}'"
        )
    missing = [name for name in V14_OBJECTS if name not in bpy.data.objects]
    if missing:
        raise RuntimeError(
            f"{OPERATION}: authority Blend lacks documented v14 additions "
            f"{missing}"
        )
    for name in V14_OBJECTS:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    remaining = {
        obj.name
        for obj in bpy.data.objects
        if obj.name.startswith("EVAL_REPAIR_014")
    }
    unexpected = sorted(remaining - BASELINE_REPAIR_014_OBJECTS)
    missing_baseline = sorted(BASELINE_REPAIR_014_OBJECTS - remaining)
    if unexpected:
        raise RuntimeError(
            f"{OPERATION}: unexpected Repair 014 evaluation additions remain "
            f"after removing v14 objects: {unexpected}"
        )
    if missing_baseline:
        raise RuntimeError(
            f"{OPERATION}: recovered authority lacks baseline Repair 014 "
            f"objects: {missing_baseline}"
        )

    staged = bpy.data.objects[v4.v2.base.STAGED_NAME]
    open_cage = bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    staged_points, staged_faces, staged_materials = v14.evaluated_geometry(staged)
    open_points, open_faces, open_materials = v14.evaluated_geometry(open_cage)
    mapping = json.loads(v4.v2.MAPPING_PATH.read_text(encoding="utf-8"))
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
    retained_points = [
        staged_points[source_id].copy()
        for source_id in retained_source_ids
    ]
    retained_fingerprint = v4.v2.fingerprint(
        retained_source_ids,
        retained_points,
    )
    removed_faces = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    (
        rebuilt_open_points,
        rebuilt_open_faces,
        rebuilt_open_materials,
        _,
        _,
    ) = v4.v2.remap_retained(
        staged_points,
        staged_faces,
        staged_materials,
        removed_faces,
    )
    open_lineage_exact = all(
        (
            rebuilt_open_faces == open_faces,
            rebuilt_open_materials == open_materials,
            all(
                (first - second).length <= 1.0e-4
                for first, second in zip(rebuilt_open_points, open_points)
            ),
        )
    )
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    tip_gap = (
        staged_points[centerline_ids[0]]
        - staged_points[centerline_ids[-1]]
    ).length
    c9_points, c9_faces = v4.component9_geometry()
    c9_fingerprint = v4.v2.fingerprint(range(len(c9_points)), c9_points)
    checks = {
        "retained_face_count": len(retained_face_ids),
        "retained_fingerprint": retained_fingerprint,
        "retained_fingerprint_exact": (
            retained_fingerprint == EXPECTED_RETAINED_FINGERPRINT
        ),
        "open_lineage_and_materials_exact": open_lineage_exact,
        "component_9_vertex_count": len(c9_points),
        "component_9_face_count": len(c9_faces),
        "component_9_fingerprint": c9_fingerprint,
        "component_9_unchanged": authority["preservation"][
            "component_9_unchanged"
        ],
        "central_bowl_open": authority["preservation"]["central_bowl_open"],
        "tip_gap_mm": round(tip_gap, 6),
        "tip_gap_exact": (
            abs(tip_gap - authority["preservation"]["tip_gap_mm"]) <= 1.0e-6
        ),
        "hard_control_error_mm": authority["preservation"][
            "hard_control_error_mm"
        ],
        "hard_controls_exact": all(
            value <= 1.0e-4
            for value in authority["preservation"][
                "hard_control_error_mm"
            ].values()
        ),
        "unexpected_eval_objects_after_removal": unexpected,
        "baseline_eval_objects_after_removal": sorted(remaining),
    }
    if not all(
        (
            checks["retained_face_count"] == 1409,
            checks["retained_fingerprint_exact"],
            checks["open_lineage_and_materials_exact"],
            checks["component_9_unchanged"],
            checks["central_bowl_open"],
            checks["tip_gap_exact"],
            checks["hard_controls_exact"],
            not unexpected,
            not missing_baseline,
        )
    ):
        raise RuntimeError(
            f"{OPERATION}: recovered v14 baseline proof failed: {checks}"
        )
    return {
        "input_blend": str(blend_path),
        "input_blend_sha256": blend_sha,
        "authority_report": str(V14_REPORT_PATH),
        "removed_objects_in_memory": list(V14_OBJECTS),
        "checks_before_construction": checks,
    }


def main() -> int:
    report_path = Path(v14.argument("--report")).resolve()
    authority_recovery = prepare_v14_authority()
    v14.OPERATION = OPERATION
    v14.UPPER_SEED = 5702
    v14.LOWER_SEED = 1784
    v14.ENDPOINT_RADIUS_MM = 0.001
    v14.MAXIMUM_ENDPOINTS_PER_TERMINAL = 1
    v14.ROLLS_DEGREES = CANDIDATES
    v14.MIDPOINT_OFFSETS_MM = ()
    v14.candidate = candidate
    v4.v2.EXPECTED_BLEND_SHA256 = AUTHORITY_BLEND_SHA256
    result = v14.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["tool"] = Path(__file__).name
    report["operation"] = OPERATION
    report["authority_recovery"] = authority_recovery
    report["status"] = (
        "evaluation_only_surface_following_fan_saddles_machine_pass"
        if report["gate_pass"]
        else "evaluation_only_surface_following_fan_saddles_machine_failed"
    )
    report["terminal_treatment"] = {
        "construction_scope": "terminal transition rings and faces only",
        "centerline": "exact straight V5702-to-V1784 v14 route",
        "midspan_width_range_mm": [4.5, 6.0],
        "thickness_mm": THICKNESS_MM,
        "target_fan_width_mm": TARGET_FAN_WIDTH_MM,
        "target_landing_mm": TARGET_LANDING_MM,
        "minimum_required_embed_mm": MINIMUM_EMBED_MM,
        "shoulder_form": "two-stage surface-following mitered fan ramp",
        "open_center_preserved": True,
    }
    report["bounded_search"] = {
        "fan_widths_mm": [9.0, 10.0, 11.0],
        "terminal_embeds_mm": [3.0, 4.0, 5.0],
        "rolls_degrees": [120],
        "candidate_count": len(CANDIDATES),
        "preferred_first": {
            "fan_width_mm": 10.0,
            "terminal_embed_mm": 5.0,
            "roll_degrees": 120,
        },
    }
    report["graph"]["nodes"][1] = "FAN_SADDLES_V15"
    report["graph"]["edges"] = [
        ["T_CAGE_1", "FAN_SADDLES_V15"],
        ["FAN_SADDLES_V15", "T_CAGE_0"],
    ]
    report["qualitative_review"] = "NOT_REQUESTED_NO_IMAGE_WORK"
    report["promotion"] = "NOT_PROMOTED"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"DONE: v15 terminal-only fan saddles gate_pass={report['gate_pass']}; "
        "promotion=NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
