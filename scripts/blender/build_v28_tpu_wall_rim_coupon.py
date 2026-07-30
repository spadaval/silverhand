#!/usr/bin/env python3
"""Build the curved V28 TPU wall/rim physical-test coupon."""

from __future__ import annotations

import argparse
from math import cos, radians, sin
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_v28_reversible_edge_softening as edge_softening  # noqa: E402
import build_v28_three_panel_physical_shells as physical  # noqa: E402
import build_v28_three_panel_scaffold as scaffold  # noqa: E402


OPERATION = "BUILD_V28_TPU_WALL_RIM_COUPON"
MISSION = "R014-JOINT-C9-C20-ELBOW-V28"
ROOT = Path(__file__).resolve().parents[2]
METHOD_ROOT = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v28"
)
EDGE_REPORT = METHOD_ROOT / "v28_reversible_edge_softening_report.json"
EDGE_VISUAL = METHOD_ROOT / "edge_softening_visual_review/classification.json"
EXPECTED_INPUT_BLEND_SHA256 = (
    "e8f35c4b3f58d44b85d03caa41f1e1cd9a5a3b3fe25ab569c524a2f9c895a913"
)
EXPECTED_EDGE_REPORT_SHA256 = (
    "ef58b832ffa2a5d7cbefd7615e600a9b33963eca7d2586e8b369faaa04073867"
)
EXPECTED_EDGE_VISUAL_SHA256 = (
    "8e34120b287dff35538909ba314b7e657b923415e29176554d4bce04c736321b"
)
DEFAULT_OUTPUT_BLEND = ROOT / (
    "blender_files/experiments/geometry_repair/"
    "repair_014_joint_c9_c20_elbow_v28_tpu_wall_rim_coupon.blend"
)
DEFAULT_REPORT = METHOD_ROOT / "v28_tpu_wall_rim_coupon_report.json"
DEFAULT_RECEIPT = METHOD_ROOT / "v28_tpu_wall_rim_coupon_receipt.json"
COLLECTION_NAME = "PHYSICAL_TEST_V28_TPU_COUPON"
OBJECT_NAME = "TEST_V28_TPU_WALL_RIM_COUPON"
MODIFIER_NAME = "REVERSIBLE_RIM_SOFTENING"
INNER_RADIUS_MM = 30.0
WALL_THICKNESS_MM = 1.6
AXIAL_LENGTH_MM = 30.0
ARC_DEGREES = 70.0
ANGULAR_SAMPLES = 48
BEVEL_WIDTH_MM = 0.4
BEVEL_SEGMENTS = 2
ANGLE_LIMIT_DEGREES = 30.0


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-blend", type=Path, default=DEFAULT_OUTPUT_BLEND)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def base_coupon() -> tuple[list[Vector], list[tuple[int, ...]]]:
    outer_radius = INNER_RADIUS_MM + WALL_THICKNESS_MM
    half_length = AXIAL_LENGTH_MM * 0.5
    half_arc = radians(ARC_DEGREES) * 0.5
    points = []
    for index in range(ANGULAR_SAMPLES):
        angle = -half_arc + 2.0 * half_arc * index / (ANGULAR_SAMPLES - 1)
        for radius, z in (
            (INNER_RADIUS_MM, -half_length),
            (INNER_RADIUS_MM, half_length),
            (outer_radius, -half_length),
            (outer_radius, half_length),
        ):
            points.append(
                Vector((radius * cos(angle), radius * sin(angle), z))
            )
    faces = []
    for index in range(ANGULAR_SAMPLES - 1):
        current = index * 4
        following = (index + 1) * 4
        inner_bottom, inner_top, outer_bottom, outer_top = range(
            current,
            current + 4,
        )
        next_inner_bottom, next_inner_top, next_outer_bottom, next_outer_top = (
            range(following, following + 4)
        )
        faces.extend(
            [
                (
                    inner_bottom,
                    next_inner_bottom,
                    next_inner_top,
                    inner_top,
                ),
                (
                    outer_bottom,
                    outer_top,
                    next_outer_top,
                    next_outer_bottom,
                ),
                (
                    inner_bottom,
                    outer_bottom,
                    next_outer_bottom,
                    next_inner_bottom,
                ),
                (
                    inner_top,
                    next_inner_top,
                    next_outer_top,
                    outer_top,
                ),
            ]
        )
    for index in (0, ANGULAR_SAMPLES - 1):
        start = index * 4
        faces.append((start, start + 1, start + 3, start + 2))
    return physical.orient_closed_shell(points, faces)


def dimensions(points: list[Vector]) -> list[float]:
    return [
        float(
            max(point[axis] for point in points)
            - min(point[axis] for point in points)
        )
        for axis in range(3)
    ]


def main() -> None:
    args = arguments()
    input_blend = Path(bpy.data.filepath).resolve()
    input_hash = scaffold.sha_file(input_blend)
    edge_report_hash = scaffold.sha_file(EDGE_REPORT)
    edge_visual_hash = scaffold.sha_file(EDGE_VISUAL)
    mismatches = {}
    for name, expected, actual in (
        ("input_blend", EXPECTED_INPUT_BLEND_SHA256, input_hash),
        ("edge_report", EXPECTED_EDGE_REPORT_SHA256, edge_report_hash),
        ("edge_visual", EXPECTED_EDGE_VISUAL_SHA256, edge_visual_hash),
    ):
        if actual != expected:
            mismatches[name] = {"expected": expected, "actual": actual}
    if mismatches:
        raise RuntimeError(
            f"{OPERATION}: accepted edge-softening authority mismatch; "
            f"mismatches={mismatches}"
        )
    visual = json.loads(EDGE_VISUAL.read_text(encoding="utf-8"))
    if visual["result"] != "ACCEPT_FOR_NEXT_DISPOSABLE_ITERATION":
        raise RuntimeError(
            f"{OPERATION}: edge-softening visual review is not accepted; "
            f"result={visual['result']}"
        )
    if bpy.data.objects.get(OBJECT_NAME) is not None:
        raise RuntimeError(
            f"{OPERATION}: coupon object already exists; object={OBJECT_NAME}; "
            "actionable_reason=start from the exact accepted edge-softening "
            "Blend"
        )
    points, faces = base_coupon()
    base_topology = physical.topology_metrics(points, faces)
    if not base_topology["closed_positive_volume_gate_pass"]:
        raise RuntimeError(
            f"{OPERATION}: base coupon is not a closed positive-volume solid; "
            f"topology={base_topology}"
        )
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    mesh = bpy.data.meshes.new(f"{OBJECT_NAME}_MESH")
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    obj["artifact_status"] = "physical-test candidate"
    obj["printable"] = True
    obj["print_ready"] = True
    obj["units"] = "millimeters"
    obj["wall_thickness_mm"] = WALL_THICKNESS_MM
    obj["bevel_width_mm"] = BEVEL_WIDTH_MM
    obj["test_scope"] = "TPU wall and rounded-rim process coupon"
    collection.objects.link(obj)
    modifier = obj.modifiers.new(MODIFIER_NAME, "BEVEL")
    modifier.width = BEVEL_WIDTH_MM
    modifier.segments = BEVEL_SEGMENTS
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = radians(ANGLE_LIMIT_DEGREES)
    modifier.affect = "EDGES"
    modifier.offset_type = "OFFSET"
    modifier.profile = 0.5
    modifier.use_clamp_overlap = True
    bpy.context.view_layer.update()

    evaluated_points, evaluated_faces = edge_softening.evaluated_geometry(obj)
    evaluated_topology = physical.topology_metrics(
        evaluated_points,
        evaluated_faces,
    )
    self_overlaps = scaffold.nonadjacent_overlaps(
        evaluated_points,
        evaluated_faces,
    )
    evaluated_dimensions = dimensions(evaluated_points)
    bed_gate = all(value <= 180.0 for value in evaluated_dimensions)
    geometry_gate = (
        evaluated_topology["closed_positive_volume_gate_pass"]
        and not self_overlaps
        and bed_gate
    )
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": (
            "V28_TPU_WALL_RIM_COUPON_GEOMETRY_PASS"
            if geometry_gate
            else "V28_TPU_WALL_RIM_COUPON_GEOMETRY_REJECT"
        ),
        "code_sha256": scaffold.sha_file(Path(__file__).resolve()),
        "input": {
            "blend": str(input_blend),
            "blend_sha256": input_hash,
            "edge_report_sha256": edge_report_hash,
            "edge_visual_classification_sha256": edge_visual_hash,
        },
        "construction": {
            "object_name": OBJECT_NAME,
            "artifact_status": "physical-test candidate",
            "inner_radius_mm": INNER_RADIUS_MM,
            "wall_thickness_mm": WALL_THICKNESS_MM,
            "axial_length_mm": AXIAL_LENGTH_MM,
            "arc_degrees": ARC_DEGREES,
            "angular_samples": ANGULAR_SAMPLES,
            "bevel": {
                "modifier_applied": False,
                "width_mm": BEVEL_WIDTH_MM,
                "segments": BEVEL_SEGMENTS,
                "profile": 0.5,
                "limit_method": "ANGLE",
                "angle_limit_degrees": ANGLE_LIMIT_DEGREES,
            },
            "test_scope": [
                "wall_printability",
                "rounded_rim_printability",
                "handling",
                "tactile_comfort",
            ],
            "excluded_claims": [
                "sleeve_fit",
                "closure",
                "panel_seams",
                "exterior_attachment",
                "elbow_motion",
                "full_panel_print_orientation",
            ],
        },
        "base_topology": base_topology,
        "evaluated_topology": evaluated_topology,
        "evaluated_dimensions_mm": evaluated_dimensions,
        "bed_limit_mm": 180.0,
        "bed_gate_pass": bed_gate,
        "self_overlap_pairs": self_overlaps,
        "self_overlap_gate_pass": not self_overlaps,
        "output_blend": str(args.output_blend.resolve()),
        "mutation": {"started": True, "output_saved": False},
    }
    scaffold.atomic_json(args.report.resolve(), report)
    if not geometry_gate:
        raise RuntimeError(
            f"{OPERATION}: coupon rejected before save; "
            f"report={args.report.resolve()}; "
            f"topology_gate="
            f"{evaluated_topology['closed_positive_volume_gate_pass']}; "
            f"self_overlap_count={len(self_overlaps)}; bed_gate={bed_gate}"
        )
    args.output_blend.resolve().parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    report["mutation"]["output_saved"] = True
    report["output_blend_sha256"] = scaffold.sha_file(
        args.output_blend.resolve()
    )
    scaffold.atomic_json(args.report.resolve(), report)
    receipt = {
        "operation": OPERATION,
        "status": "DONE",
        "report": str(args.report.resolve()),
        "report_sha256": scaffold.sha_file(args.report.resolve()),
        "output_blend": str(args.output_blend.resolve()),
        "output_blend_sha256": report["output_blend_sha256"],
    }
    scaffold.atomic_json(args.receipt.resolve(), receipt)
    print(
        f"DONE {OPERATION}: output={args.output_blend.resolve()}; "
        f"dimensions_mm={evaluated_dimensions}; "
        f"signed_volume_mm3={evaluated_topology['signed_volume_mm3']:.6f}"
    )


if __name__ == "__main__":
    main()
