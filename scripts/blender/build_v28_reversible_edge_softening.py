#!/usr/bin/env python3
"""Add and audit reversible bevel modifiers on accepted V28 physical shells."""

from __future__ import annotations

import argparse
from math import radians
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audit_v26_cutter_authority as cutter_audit  # noqa: E402
import build_v28_three_panel_physical_shells as physical  # noqa: E402
import build_v28_three_panel_scaffold as scaffold  # noqa: E402


OPERATION = "BUILD_V28_REVERSIBLE_EDGE_SOFTENING"
MISSION = "R014-JOINT-C9-C20-ELBOW-V28"
ROOT = Path(__file__).resolve().parents[2]
METHOD_ROOT = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v28"
)
PHYSICAL_REPORT = METHOD_ROOT / "v28_three_panel_physical_shells_report.json"
VISUAL_CLASSIFICATION = METHOD_ROOT / (
    "physical_shells_visual_review/classification.json"
)
EXPECTED_INPUT_BLEND_SHA256 = (
    "64366dc52290552416fa7ac478d6bc289adb8ff63fa1de6ca4c84f9e1c80bd68"
)
EXPECTED_PHYSICAL_REPORT_SHA256 = (
    "b9929b66d592ff380e56227c9514f8e71ca055b7edec838f62ed854b813463e0"
)
EXPECTED_VISUAL_CLASSIFICATION_SHA256 = (
    "81477f741591a705dbb64787d2fa3f0ec249ce43b5d1d1cce625c815ee78903a"
)
DEFAULT_OUTPUT_BLEND = ROOT / (
    "blender_files/experiments/geometry_repair/"
    "repair_014_joint_c9_c20_elbow_v28_reversible_edge_softening.blend"
)
DEFAULT_REPORT = METHOD_ROOT / "v28_reversible_edge_softening_report.json"
DEFAULT_RECEIPT = METHOD_ROOT / "v28_reversible_edge_softening_receipt.json"
COLLECTION_NAME = "EVAL_V28_REVERSIBLE_EDGE_SOFTENING"
OBJECT_SUFFIX = "_EDGE_SOFTENED"
MODIFIER_NAME = "REVERSIBLE_RIM_SOFTENING"
CUTTER_OBJECT = "CUT_CLEARANCE_ANATOMY_STRAIGHT"
DEFAULT_WIDTH_MM = 0.4
DEFAULT_SEGMENTS = 2
ANGLE_LIMIT_DEGREES = 30.0


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-blend", type=Path, default=DEFAULT_OUTPUT_BLEND)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--width-mm", type=float, default=DEFAULT_WIDTH_MM)
    parser.add_argument("--segments", type=int, default=DEFAULT_SEGMENTS)
    return parser.parse_args(argv)


def modifier_state(obj: bpy.types.Object) -> list[dict]:
    return [
        {
            "name": modifier.name,
            "type": modifier.type,
            "show_viewport": bool(modifier.show_viewport),
            "show_render": bool(modifier.show_render),
        }
        for modifier in obj.modifiers
    ]


def evaluated_geometry(
    obj: bpy.types.Object,
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    try:
        matrix = evaluated.matrix_world.copy()
        points = [matrix @ vertex.co for vertex in mesh.vertices]
        faces = [
            tuple(int(index) for index in polygon.vertices)
            for polygon in mesh.polygons
        ]
        return points, faces
    finally:
        evaluated.to_mesh_clear()


def main() -> None:
    args = arguments()
    if args.width_mm <= 0.0:
        raise RuntimeError(
            f"{OPERATION}: bevel width must be positive; "
            f"received={args.width_mm}"
        )
    if args.segments < 1:
        raise RuntimeError(
            f"{OPERATION}: bevel segments must be at least one; "
            f"received={args.segments}"
        )
    input_blend = Path(bpy.data.filepath).resolve()
    input_hash = scaffold.sha_file(input_blend)
    physical_report_hash = scaffold.sha_file(PHYSICAL_REPORT)
    visual_hash = scaffold.sha_file(VISUAL_CLASSIFICATION)
    mismatches = {}
    for name, expected, actual in (
        ("input_blend", EXPECTED_INPUT_BLEND_SHA256, input_hash),
        (
            "physical_report",
            EXPECTED_PHYSICAL_REPORT_SHA256,
            physical_report_hash,
        ),
        (
            "visual_classification",
            EXPECTED_VISUAL_CLASSIFICATION_SHA256,
            visual_hash,
        ),
    ):
        if actual != expected:
            mismatches[name] = {"expected": expected, "actual": actual}
    if mismatches:
        raise RuntimeError(
            f"{OPERATION}: accepted physical-shell authority mismatch; "
            f"mismatches={mismatches}"
        )
    visual = json.loads(VISUAL_CLASSIFICATION.read_text(encoding="utf-8"))
    if visual["result"] != "ACCEPT_FOR_NEXT_DISPOSABLE_ITERATION":
        raise RuntimeError(
            f"{OPERATION}: physical-shell visual review is not accepted; "
            f"result={visual['result']}"
        )
    report_authority = json.loads(PHYSICAL_REPORT.read_text(encoding="utf-8"))
    if bpy.data.collections.get(COLLECTION_NAME) is not None:
        raise RuntimeError(
            f"{OPERATION}: output collection already exists; "
            f"collection={COLLECTION_NAME}; actionable_reason=start from the "
            "exact accepted physical-shell Blend"
        )
    accepted_before = {}
    accepted_objects = []
    for panel in report_authority["panels"]:
        obj = scaffold.require_mesh(panel["object_name"])
        accepted_objects.append(obj)
        accepted_before[obj.name] = {
            "mesh_fingerprint": scaffold.mesh_fingerprint(obj),
            "mesh_datablock": obj.data.name,
            "modifier_state": modifier_state(obj),
        }

    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    duplicates = []
    for source in accepted_objects:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = f"{source.name}{OBJECT_SUFFIX}"
        duplicate.data.name = f"{duplicate.name}_MESH"
        for existing in list(duplicate.modifiers):
            duplicate.modifiers.remove(existing)
        modifier = duplicate.modifiers.new(MODIFIER_NAME, "BEVEL")
        modifier.width = args.width_mm
        modifier.segments = args.segments
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = radians(ANGLE_LIMIT_DEGREES)
        modifier.affect = "EDGES"
        modifier.offset_type = "OFFSET"
        modifier.profile = 0.5
        modifier.use_clamp_overlap = True
        duplicate["status"] = "EVALUATION_EDGE_SOFTENED"
        duplicate["mission"] = MISSION
        duplicate["source_physical_shell"] = source.name
        duplicate["bevel_width_mm"] = args.width_mm
        duplicate["bevel_segments"] = args.segments
        collection.objects.link(duplicate)
        duplicates.append(duplicate)
    bpy.context.view_layer.update()

    payloads = []
    candidate_triangles = []
    for duplicate in duplicates:
        points, faces = evaluated_geometry(duplicate)
        topology = physical.topology_metrics(points, faces)
        panel_id = duplicate["source_physical_shell"]
        candidate_triangles.extend(
            scaffold.triangle_records(panel_id, points, faces)
        )
        payloads.append(
            {
                "panel_id": panel_id,
                "object": duplicate,
                "points": points,
                "faces": faces,
                "topology": topology,
            }
        )

    internal_overlaps = {
        payload["panel_id"]: scaffold.nonadjacent_overlaps(
            payload["points"],
            payload["faces"],
        )
        for payload in payloads
    }
    cross_panel_overlaps = {}
    for first_id, first in enumerate(payloads):
        for second in payloads[first_id + 1 :]:
            key = f"{first['panel_id']}::{second['panel_id']}"
            cross_panel_overlaps[key] = scaffold.nonadjacent_overlaps(
                first["points"],
                first["faces"],
                second["points"],
                second["faces"],
            )
    intersection_gate = not any(internal_overlaps.values()) and not any(
        cross_panel_overlaps.values()
    )
    cutter = scaffold.require_mesh(CUTTER_OBJECT)
    provenance, cutter_points, cutter_faces, orientation_sign = (
        cutter_audit.evaluated_cutter_provenance(cutter)
    )
    clearance = cutter_audit.clearance_contract(
        candidate_triangles,
        cutter_points,
        cutter_faces,
        orientation_sign,
    )
    clearance_result = scaffold.clearance_summary(clearance)
    topology_gate = all(
        payload["topology"]["closed_positive_volume_gate_pass"]
        for payload in payloads
    )
    geometry_gate = (
        topology_gate
        and intersection_gate
        and clearance_result["vertex_edge_and_triangle_interior_gate_pass"]
    )
    accepted_after = {
        obj.name: {
            "mesh_fingerprint": scaffold.mesh_fingerprint(obj),
            "mesh_datablock": obj.data.name,
            "modifier_state": modifier_state(obj),
        }
        for obj in accepted_objects
    }
    accepted_unchanged = accepted_after == accepted_before
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": (
            "V28_REVERSIBLE_EDGE_SOFTENING_GEOMETRY_PASS"
            if geometry_gate and accepted_unchanged
            else "V28_REVERSIBLE_EDGE_SOFTENING_GEOMETRY_REJECT"
        ),
        "code_sha256": scaffold.sha_file(Path(__file__).resolve()),
        "input": {
            "blend": str(input_blend),
            "blend_sha256": input_hash,
            "physical_report_sha256": physical_report_hash,
            "visual_classification_sha256": visual_hash,
        },
        "construction": {
            "base_meshes_duplicated": True,
            "accepted_physical_shells_preserved": accepted_unchanged,
            "modifier_applied": False,
            "modifier_type": "BEVEL",
            "width_mm": args.width_mm,
            "segments": args.segments,
            "limit_method": "ANGLE",
            "angle_limit_degrees": ANGLE_LIMIT_DEGREES,
            "affect": "EDGES",
            "profile": 0.5,
            "clamp_overlap": True,
            "promotion": "NOT_PROMOTED",
        },
        "panels": [
            {
                "source_physical_shell": payload["panel_id"],
                "object_name": payload["object"].name,
                "base_mesh_datablock": payload["object"].data.name,
                "modifier_state": modifier_state(payload["object"]),
                "topology": payload["topology"],
            }
            for payload in payloads
        ],
        "surface_intersections": {
            "per_panel_nonadjacent_overlap_pairs": internal_overlaps,
            "cross_panel_overlap_pairs": cross_panel_overlaps,
            "surface_intersection_gate_pass": intersection_gate,
        },
        "clearance": clearance_result,
        "accepted_inputs": {
            "before": accepted_before,
            "after": accepted_after,
            "unchanged_gate_pass": accepted_unchanged,
        },
        "cutter_provenance_fingerprint": provenance["provenance_fingerprint"],
        "output_blend": str(args.output_blend.resolve()),
        "mutation": {"started": True, "output_saved": False},
    }
    scaffold.atomic_json(args.report.resolve(), report)
    if not (geometry_gate and accepted_unchanged):
        raise RuntimeError(
            f"{OPERATION}: evaluated edge softening rejected before save; "
            f"report={args.report.resolve()}; topology_gate={topology_gate}; "
            f"surface_intersection_gate={intersection_gate}; "
            f"clearance_reject_count={clearance_result['reject_count']}; "
            f"accepted_inputs_unchanged={accepted_unchanged}; "
            "actionable_reason=reduce only the explicit bevel width or inspect "
            "the named failed gate"
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
        f"width_mm={args.width_mm}; "
        f"minimum_signed_clearance_mm="
        f"{clearance_result['minimum_signed_adaptive_sample_margin_mm']:.6f}"
    )


if __name__ == "__main__":
    main()
