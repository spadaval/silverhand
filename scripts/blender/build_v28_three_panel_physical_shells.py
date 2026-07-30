#!/usr/bin/env python3
"""Create three closed outward-thickness shells from the accepted V28 scaffold."""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audit_v26_cutter_authority as cutter_audit  # noqa: E402
import build_v28_three_panel_scaffold as scaffold  # noqa: E402


OPERATION = "BUILD_V28_THREE_PANEL_PHYSICAL_SHELLS"
MISSION = "R014-JOINT-C9-C20-ELBOW-V28"
ROOT = Path(__file__).resolve().parents[2]
METHOD_ROOT = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v28"
)
SCOPE_AUTHORITY = METHOD_ROOT / "v28_wearable_panel_scope_authority.json"
SCAFFOLD_REPORT = METHOD_ROOT / "v28_three_panel_scaffold_report.json"
VISUAL_CLASSIFICATION = METHOD_ROOT / (
    "scaffold_visual_review_fit_derived/classification.json"
)
EXPECTED_INPUT_BLEND_SHA256 = (
    "e27c5632d0c5d7b60cb99f4eac87b46a143cc4a36e1caf1b36bbbea366b28c9a"
)
EXPECTED_SCOPE_SHA256 = (
    "4a35c5953c7a0e61233d8e3f9db218454315ab4143b7c9da981f42405927c7d3"
)
EXPECTED_SCAFFOLD_REPORT_SHA256 = (
    "bc8f809cb67de2e169374f82af3efb9575ead70bd9cf587d85d9d2865bef4b82"
)
EXPECTED_VISUAL_CLASSIFICATION_SHA256 = (
    "86645d3d8775ef60105464767ae7e06416088f9d8e02b05c7ee3c8f36bc46227"
)
DEFAULT_OUTPUT_BLEND = ROOT / (
    "blender_files/experiments/geometry_repair/"
    "repair_014_joint_c9_c20_elbow_v28_three_panel_physical_shells.blend"
)
DEFAULT_REPORT = METHOD_ROOT / "v28_three_panel_physical_shells_report.json"
DEFAULT_RECEIPT = METHOD_ROOT / "v28_three_panel_physical_shells_receipt.json"
COLLECTION_NAME = "EVAL_V28_THREE_PANEL_PHYSICAL_SHELLS"
OBJECT_SUFFIX = "_PHYSICAL_SHELL"
DEFAULT_THICKNESS_MM = 1.6


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-blend", type=Path, default=DEFAULT_OUTPUT_BLEND)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument(
        "--thickness-mm",
        type=float,
        default=DEFAULT_THICKNESS_MM,
    )
    return parser.parse_args(argv)


def boundary_edges(faces: list[tuple[int, ...]]) -> list[tuple[int, int]]:
    counts = Counter()
    for face in faces:
        for first, second in zip(face, face[1:] + face[:1]):
            counts[tuple(sorted((first, second)))] += 1
    return sorted(edge for edge, count in counts.items() if count == 1)


def orient_closed_shell(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    mesh = bmesh.new()
    vertices = [mesh.verts.new(point) for point in points]
    mesh.verts.ensure_lookup_table()
    for face in faces:
        mesh.faces.new(tuple(vertices[index] for index in face))
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    mesh.verts.index_update()
    mesh.faces.index_update()
    result_points = [vertex.co.copy() for vertex in mesh.verts]
    result_faces = [
        tuple(vertex.index for vertex in face.verts) for face in mesh.faces
    ]
    mesh.free()
    return result_points, result_faces


def physical_shell(
    inner_points: list[Vector],
    inner_faces: list[tuple[int, ...]],
    axis: Vector,
    frame_center: Vector,
    thickness_mm: float,
) -> tuple[list[Vector], list[tuple[int, ...]], dict]:
    outer_points = []
    thicknesses = []
    for vertex_id, point in enumerate(inner_points):
        station = (point - frame_center).dot(axis)
        axis_point = frame_center + axis * station
        radial = point - axis_point
        if radial.length <= 1.0e-7:
            raise RuntimeError(
                f"{OPERATION}: scaffold vertex lies on construction axis; "
                f"vertex_id={vertex_id}; point={list(point)}"
            )
        outer = point + radial.normalized() * thickness_mm
        outer_points.append(outer)
        thicknesses.append((outer - point).length)
    count = len(inner_points)
    faces = [tuple(face) for face in inner_faces]
    faces.extend(tuple(vertex + count for vertex in face) for face in inner_faces)
    rim_edges = boundary_edges(inner_faces)
    faces.extend(
        (first, second, second + count, first + count)
        for first, second in rim_edges
    )
    points, faces = orient_closed_shell(
        [point.copy() for point in inner_points] + outer_points,
        faces,
    )
    if any(
        (points[index] - inner_points[index]).length > 1.0e-7
        for index in range(count)
    ):
        raise RuntimeError(
            f"{OPERATION}: inner scaffold vertices changed while orienting shell"
        )
    return points, faces, {
        "inner_vertex_count": count,
        "outer_vertex_count": count,
        "rim_edge_count": len(rim_edges),
        "minimum_vertex_pair_thickness_mm": min(thicknesses),
        "maximum_vertex_pair_thickness_mm": max(thicknesses),
    }


def topology_metrics(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> dict:
    edge_counts = Counter()
    adjacency = {index: set() for index in range(len(points))}
    for face in faces:
        for first, second in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((first, second)))
            edge_counts[edge] += 1
            adjacency[first].add(second)
            adjacency[second].add(first)
    unseen = set(adjacency)
    components = 0
    while unseen:
        components += 1
        queue = deque([unseen.pop()])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    signed_volume = 0.0
    triangle_count = 0
    for face in faces:
        for fan_id in range(1, len(face) - 1):
            first = points[face[0]]
            second = points[face[fan_id]]
            third = points[face[fan_id + 1]]
            signed_volume += first.dot(second.cross(third)) / 6.0
            triangle_count += 1
    boundary_count = sum(count == 1 for count in edge_counts.values())
    non_manifold_count = sum(count != 2 for count in edge_counts.values())
    return {
        "vertex_count": len(points),
        "face_count": len(faces),
        "triangle_count": triangle_count,
        "edge_count": len(edge_counts),
        "connected_component_count": components,
        "boundary_edge_count": boundary_count,
        "non_manifold_edge_count": non_manifold_count,
        "signed_volume_mm3": float(signed_volume),
        "closed_positive_volume_gate_pass": (
            components == 1
            and boundary_count == 0
            and non_manifold_count == 0
            and signed_volume > 0.0
        ),
    }


def main() -> None:
    args = arguments()
    if args.thickness_mm <= 0.0:
        raise RuntimeError(
            f"{OPERATION}: thickness must be positive; "
            f"received={args.thickness_mm}"
        )
    input_blend = Path(bpy.data.filepath).resolve()
    input_hash = scaffold.sha_file(input_blend)
    authorities = {
        "scope": (
            SCOPE_AUTHORITY,
            EXPECTED_SCOPE_SHA256,
        ),
        "scaffold_report": (
            SCAFFOLD_REPORT,
            EXPECTED_SCAFFOLD_REPORT_SHA256,
        ),
        "visual_classification": (
            VISUAL_CLASSIFICATION,
            EXPECTED_VISUAL_CLASSIFICATION_SHA256,
        ),
    }
    mismatches = {}
    for name, (path, expected) in authorities.items():
        actual = scaffold.sha_file(path)
        if actual != expected:
            mismatches[name] = {
                "path": str(path),
                "expected": expected,
                "actual": actual,
            }
    if input_hash != EXPECTED_INPUT_BLEND_SHA256 or mismatches:
        raise RuntimeError(
            f"{OPERATION}: accepted scaffold authority mismatch; "
            f"input_blend={input_blend}; expected_blend_sha256="
            f"{EXPECTED_INPUT_BLEND_SHA256}; actual_blend_sha256={input_hash}; "
            f"authority_mismatches={mismatches}"
        )
    visual = json.loads(VISUAL_CLASSIFICATION.read_text(encoding="utf-8"))
    if visual["result"] != "ACCEPT_FOR_NEXT_DISPOSABLE_ITERATION":
        raise RuntimeError(
            f"{OPERATION}: scaffold visual review is not accepted; "
            f"result={visual['result']}"
        )
    scope = json.loads(SCOPE_AUTHORITY.read_text(encoding="utf-8"))
    report_authority = json.loads(SCAFFOLD_REPORT.read_text(encoding="utf-8"))
    axis = Vector(scope["construction_frame"]["axis"]).normalized()
    frame_center = Vector(scope["construction_frame"]["center_mm"])
    source = scaffold.require_mesh(scope["source_scene"]["source_object"])
    fit_reference = scaffold.require_mesh(
        scope["source_scene"]["fit_reference_object"]
    )
    cutter = scaffold.require_mesh(scope["source_scene"]["cutter_object"])
    source_before = scaffold.mesh_fingerprint(source)
    fit_before = scaffold.mesh_fingerprint(fit_reference)
    cutter_before = scaffold.mesh_fingerprint(cutter)

    panel_payloads = []
    candidate_triangles = []
    scaffold_before = {}
    for panel in report_authority["panels"]:
        inner = scaffold.require_mesh(panel["object_name"])
        scaffold_before[inner.name] = scaffold.mesh_fingerprint(inner)
        inner_points = [vertex.co.copy() for vertex in inner.data.vertices]
        inner_faces = [
            tuple(int(index) for index in polygon.vertices)
            for polygon in inner.data.polygons
        ]
        points, faces, thickness = physical_shell(
            inner_points,
            inner_faces,
            axis,
            frame_center,
            args.thickness_mm,
        )
        topology = topology_metrics(points, faces)
        panel_id = panel["panel_id"]
        candidate_triangles.extend(
            scaffold.triangle_records(panel_id, points, faces)
        )
        panel_payloads.append(
            {
                "panel_id": panel_id,
                "source_scaffold_object": inner.name,
                "object_name": f"{inner.name}{OBJECT_SUFFIX}",
                "points": points,
                "faces": faces,
                "thickness": thickness,
                "topology": topology,
            }
        )

    internal_overlaps = {
        payload["panel_id"]: scaffold.nonadjacent_overlaps(
            payload["points"],
            payload["faces"],
        )
        for payload in panel_payloads
    }
    cross_panel_overlaps = {}
    for first_id, first in enumerate(panel_payloads):
        for second in panel_payloads[first_id + 1 :]:
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
        for payload in panel_payloads
    )
    geometry_gate = (
        topology_gate
        and intersection_gate
        and clearance_result["vertex_edge_and_triangle_interior_gate_pass"]
    )
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": (
            "V28_THREE_PANEL_PHYSICAL_SHELLS_GEOMETRY_PASS"
            if geometry_gate
            else "V28_THREE_PANEL_PHYSICAL_SHELLS_GEOMETRY_REJECT"
        ),
        "code_sha256": scaffold.sha_file(Path(__file__).resolve()),
        "input": {
            "blend": str(input_blend),
            "blend_sha256": input_hash,
            "scope_authority_sha256": EXPECTED_SCOPE_SHA256,
            "scaffold_report_sha256": EXPECTED_SCAFFOLD_REPORT_SHA256,
            "visual_classification_sha256": (
                EXPECTED_VISUAL_CLASSIFICATION_SHA256
            ),
        },
        "construction": {
            "panel_count": len(panel_payloads),
            "thickness_mm": args.thickness_mm,
            "thickness_direction": (
                "outward from neutral construction axis; accepted inner "
                "scaffold surface preserved exactly"
            ),
            "edge_treatment": "square closed staging edges",
            "source_detail_integrated": False,
            "closure_hardware_integrated": False,
            "promotion": "NOT_PROMOTED",
        },
        "panels": [
            {
                "panel_id": payload["panel_id"],
                "source_scaffold_object": payload["source_scaffold_object"],
                "object_name": payload["object_name"],
                "thickness": payload["thickness"],
                "topology": payload["topology"],
            }
            for payload in panel_payloads
        ],
        "surface_intersections": {
            "per_panel_nonadjacent_overlap_pairs": internal_overlaps,
            "cross_panel_overlap_pairs": cross_panel_overlaps,
            "surface_intersection_gate_pass": intersection_gate,
        },
        "clearance": clearance_result,
        "invariants": {
            "source_mesh_fingerprint_before": source_before,
            "fit_reference_mesh_fingerprint_before": fit_before,
            "cutter_mesh_fingerprint_before": cutter_before,
            "scaffold_mesh_fingerprints_before": scaffold_before,
        },
        "cutter_provenance_fingerprint": provenance["provenance_fingerprint"],
        "output_blend": str(args.output_blend.resolve()),
        "mutation": {"started": False, "output_saved": False},
    }
    scaffold.atomic_json(args.report.resolve(), report)
    if not geometry_gate:
        raise RuntimeError(
            f"{OPERATION}: physical shells rejected before mutation; "
            f"report={args.report.resolve()}; topology_gate={topology_gate}; "
            f"surface_intersection_gate={intersection_gate}; "
            f"clearance_reject_count={clearance_result['reject_count']}; "
            "actionable_reason=inspect the named failed gate before changing "
            "thickness or topology"
        )

    if bpy.data.collections.get(COLLECTION_NAME) is not None:
        raise RuntimeError(
            f"{OPERATION}: output collection already exists; "
            f"collection={COLLECTION_NAME}; actionable_reason=start from the "
            "exact accepted scaffold Blend"
        )
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    for payload in panel_payloads:
        mesh = bpy.data.meshes.new(f"{payload['object_name']}_MESH")
        mesh.from_pydata(payload["points"], [], payload["faces"])
        mesh.update()
        obj = bpy.data.objects.new(payload["object_name"], mesh)
        obj["status"] = "EVALUATION_PHYSICAL_SHELL"
        obj["mission"] = MISSION
        obj["thickness_mm"] = args.thickness_mm
        obj["minimum_clearance_contract_mm"] = 1.7
        obj["source_scaffold_object"] = payload["source_scaffold_object"]
        collection.objects.link(obj)

    invariant_after = {
        "source_mesh_fingerprint_after": scaffold.mesh_fingerprint(source),
        "fit_reference_mesh_fingerprint_after": scaffold.mesh_fingerprint(
            fit_reference
        ),
        "cutter_mesh_fingerprint_after": scaffold.mesh_fingerprint(cutter),
        "scaffold_mesh_fingerprints_after": {
            name: scaffold.mesh_fingerprint(scaffold.require_mesh(name))
            for name in scaffold_before
        },
    }
    invariant_pass = (
        invariant_after["source_mesh_fingerprint_after"] == source_before
        and invariant_after["fit_reference_mesh_fingerprint_after"] == fit_before
        and invariant_after["cutter_mesh_fingerprint_after"] == cutter_before
        and invariant_after["scaffold_mesh_fingerprints_after"]
        == scaffold_before
    )
    if not invariant_pass:
        raise RuntimeError(
            f"{OPERATION}: immutable input changed during construction; "
            f"invariants_after={invariant_after}; output not saved"
        )
    report["invariants"].update(invariant_after)
    report["invariants"]["immutable_input_gate_pass"] = True
    report["mutation"]["started"] = True
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
        f"minimum_signed_clearance_mm="
        f"{clearance_result['minimum_signed_adaptive_sample_margin_mm']:.6f}; "
        f"panel_count={len(panel_payloads)}"
    )


if __name__ == "__main__":
    main()
