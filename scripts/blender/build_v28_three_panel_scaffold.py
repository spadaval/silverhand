#!/usr/bin/env python3
"""Build and audit the disposable V28 three-panel scaffold.

The generated objects are open, zero-thickness evaluation surfaces. They are
not printable or promoted geometry. Cutter intersections supply section
measurements only; no cutter or source topology is copied.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import cos, pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_cross_section as section  # noqa: E402
import analyze_v27_c9_landing as landing  # noqa: E402
import audit_v26_cutter_authority as cutter_audit  # noqa: E402


OPERATION = "BUILD_V28_THREE_PANEL_SCAFFOLD"
MISSION = "R014-JOINT-C9-C20-ELBOW-V28"
ROOT = Path(__file__).resolve().parents[2]
METHOD_ROOT = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v28"
)
SCOPE_AUTHORITY = METHOD_ROOT / "v28_wearable_panel_scope_authority.json"
EXPECTED_SCOPE_SHA256 = (
    "4a35c5953c7a0e61233d8e3f9db218454315ab4143b7c9da981f42405927c7d3"
)
EXTERIOR_CLASSIFICATION = METHOD_ROOT / (
    "exterior_removal_review/classification.json"
)
EXPECTED_EXTERIOR_CLASSIFICATION_SHA256 = (
    "fa02e9d18ecd124bf334db8d23e2e1576d495f9f21046d54e787a3980cc0c597"
)
DEFAULT_OUTPUT_BLEND = ROOT / (
    "blender_files/experiments/geometry_repair/"
    "repair_014_joint_c9_c20_elbow_v28_three_panel_scaffold.blend"
)
DEFAULT_REPORT = METHOD_ROOT / "v28_three_panel_scaffold_report.json"
DEFAULT_RECEIPT = METHOD_ROOT / "v28_three_panel_scaffold_receipt.json"
COLLECTION_NAME = "EVAL_V28_THREE_PANEL_SCAFFOLD"
PANEL_PREFIX = "EVAL_V28_PANEL_ZONE_"
SECTION_COUNT = 5
ARC_POINT_COUNT = 64
OPENING_DEGREES = 40.0
SHARED_BOUNDARY_INSET_MM = 2.0
DEFAULT_RADIAL_ALLOWANCE_MM = 4.0


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-blend", type=Path, default=DEFAULT_OUTPUT_BLEND)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument(
        "--radial-allowance-mm",
        type=float,
        default=DEFAULT_RADIAL_ALLOWANCE_MM,
    )
    return parser.parse_args(argv)


def sha_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def mesh_fingerprint(obj: bpy.types.Object) -> str:
    payload = {
        "name": obj.name,
        "matrix_world": [
            [float(value) for value in row] for row in obj.matrix_world
        ],
        "vertices": [
            [float(value) for value in vertex.co] for vertex in obj.data.vertices
        ],
        "faces": [
            [int(vertex_id) for vertex_id in polygon.vertices]
            for polygon in obj.data.polygons
        ],
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def require_mesh(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = None if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: required mesh unavailable; object={name}; "
            f"actual_type={actual}"
        )
    return obj


def section_points(
    fit_triangles: list[tuple[Vector, Vector, Vector]],
    origin: Vector,
    normal: Vector,
) -> list[Vector]:
    points = []
    coplanar = 0
    malformed = 0
    for triangle in fit_triangles:
        intersections, is_coplanar = section.triangle_section(
            triangle,
            origin,
            normal,
        )
        if is_coplanar:
            coplanar += 1
        elif len(intersections) == 2:
            points.extend(intersections)
        elif intersections:
            malformed += 1
    points = section.unique_points(points)
    if coplanar or malformed or len(points) < 8:
        raise RuntimeError(
            f"{OPERATION}: fit-reference section is not a clean usable point cloud; "
            f"origin={list(origin)}; unique_points={len(points)}; "
            f"coplanar_triangles={coplanar}; malformed_crossings={malformed}; "
            "actionable_reason=move the station slightly or inspect fit-reference "
            "section topology"
        )
    return points


def enclosing_ellipse(
    points: list[Vector],
    origin: Vector,
    axis_x: Vector,
    axis_y: Vector,
    allowance_mm: float,
) -> dict:
    projected = [
        ((point - origin).dot(axis_x), (point - origin).dot(axis_y))
        for point in points
    ]
    center_x = sum(point[0] for point in projected) / len(projected)
    center_y = sum(point[1] for point in projected) / len(projected)
    radius_x = max(abs(point[0] - center_x) for point in projected)
    radius_y = max(abs(point[1] - center_y) for point in projected)
    if min(radius_x, radius_y) <= 1.0e-6:
        raise RuntimeError(
            f"{OPERATION}: degenerate cutter section ellipse; "
            f"radius_x={radius_x}; radius_y={radius_y}"
        )
    enclosure_scale = max(
        (
            ((point[0] - center_x) / radius_x) ** 2
            + ((point[1] - center_y) / radius_y) ** 2
        )
        ** 0.5
        for point in projected
    )
    radius_x = radius_x * enclosure_scale + allowance_mm
    radius_y = radius_y * enclosure_scale + allowance_mm
    center = origin + axis_x * center_x + axis_y * center_y
    return {
        "center": center,
        "center_offset_mm": [float(center_x), float(center_y)],
        "radius_mm": [float(radius_x), float(radius_y)],
        "enclosure_scale": float(enclosure_scale),
        "source_point_count": len(points),
    }


def arc_points(
    ellipse: dict,
    axis_x: Vector,
    axis_y: Vector,
) -> list[Vector]:
    gap = OPENING_DEGREES * pi / 180.0
    start = gap * 0.5
    span = 2.0 * pi - gap
    center = ellipse["center"]
    radius_x, radius_y = ellipse["radius_mm"]
    return [
        center
        + axis_x * (radius_x * cos(start + span * index / (ARC_POINT_COUNT - 1)))
        + axis_y * (radius_y * sin(start + span * index / (ARC_POINT_COUNT - 1)))
        for index in range(ARC_POINT_COUNT)
    ]


def panel_geometry(rings: list[list[Vector]]) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices = [point.copy() for ring in rings for point in ring]
    faces = []
    for ring_id in range(len(rings) - 1):
        current = ring_id * ARC_POINT_COUNT
        following = (ring_id + 1) * ARC_POINT_COUNT
        for point_id in range(ARC_POINT_COUNT - 1):
            faces.append(
                (
                    current + point_id,
                    current + point_id + 1,
                    following + point_id + 1,
                    following + point_id,
                )
            )
    return vertices, faces


def triangle_records(
    panel_id: str,
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
) -> list[dict]:
    records = []
    for face_id, face in enumerate(faces):
        for fan_id in range(1, len(face) - 1):
            ids = (face[0], face[fan_id], face[fan_id + 1])
            records.append(
                {
                    "triangle_id": f"{panel_id}:face_{face_id}:fan_{fan_id - 1}",
                    "source_fixture": {
                        "kind": "authored_v28_scaffold_triangle",
                        "panel_id": panel_id,
                        "face_id": face_id,
                        "vertex_ids": list(ids),
                    },
                    "points": tuple(vertices[index] for index in ids),
                }
            )
    return records


def nonadjacent_overlaps(
    first_vertices: list[Vector],
    first_faces: list[tuple[int, ...]],
    second_vertices: list[Vector] | None = None,
    second_faces: list[tuple[int, ...]] | None = None,
) -> list[tuple[int, int]]:
    first_tree = BVHTree.FromPolygons(
        first_vertices,
        first_faces,
        all_triangles=False,
    )
    if second_vertices is not None and second_faces is not None:
        second_tree = BVHTree.FromPolygons(
            second_vertices,
            second_faces,
            all_triangles=False,
        )
        return sorted(first_tree.overlap(second_tree))
    face_sets = [set(face) for face in first_faces]
    return sorted(
        (first, second)
        for first, second in first_tree.overlap(first_tree)
        if first < second and face_sets[first].isdisjoint(face_sets[second])
    )


def clearance_summary(clearance: dict) -> dict:
    records = clearance["triangle_records"]
    minimum_exact = min(
        record["minimum_triangle_to_cutter"]["distance_mm"] for record in records
    )
    minimum_signed = min(
        record["minimum_signed_sample_margin_mm"]
        for record in records
        if record["minimum_signed_sample_margin_mm"] is not None
    )
    maximum_spacing = max(
        max(
            (
                step["maximum_edge_step_mm"]
                for step in record["adaptive_samples"]["refinement_history"]
            ),
            default=0.0,
        )
        for record in records
    )
    maximum_variation = max(
        max(
            (
                step["maximum_adjacent_signed_margin_variation_mm"]
                for step in record["adaptive_samples"]["refinement_history"]
            ),
            default=0.0,
        )
        for record in records
    )
    rejected = [
        {
            "triangle_id": record["candidate_triangle_id"],
            "rejection_reasons": record["rejection_reasons"],
            "minimum_exact_distance_mm": record[
                "minimum_triangle_to_cutter"
            ]["distance_mm"],
            "minimum_signed_sample_margin_mm": record[
                "minimum_signed_sample_margin_mm"
            ],
        }
        for record in records
        if not record["clearance_pass"]
    ]
    return {
        "triangle_count": len(records),
        "pass_count": clearance["fixture_pass_count"],
        "reject_count": clearance["fixture_reject_count"],
        "intersection_pair_count": len(clearance["intersection_pairs"]),
        "minimum_exact_triangle_to_cutter_distance_mm": float(minimum_exact),
        "minimum_signed_adaptive_sample_margin_mm": float(minimum_signed),
        "maximum_initial_or_refined_edge_spacing_mm": float(maximum_spacing),
        "maximum_adjacent_signed_margin_variation_mm": float(maximum_variation),
        "vertex_edge_and_triangle_interior_gate_pass": not rejected,
        "rejected_triangles": rejected,
    }


def main() -> None:
    args = arguments()
    if args.radial_allowance_mm < 1.7:
        raise RuntimeError(
            f"{OPERATION}: radial allowance is below the clearance contract; "
            f"received={args.radial_allowance_mm}; minimum=1.7"
        )
    scope_hash = sha_file(SCOPE_AUTHORITY)
    if scope_hash != EXPECTED_SCOPE_SHA256:
        raise RuntimeError(
            f"{OPERATION}: V28 scope authority hash mismatch; "
            f"path={SCOPE_AUTHORITY}; expected={EXPECTED_SCOPE_SHA256}; "
            f"actual={scope_hash}"
        )
    scope = json.loads(SCOPE_AUTHORITY.read_text(encoding="utf-8"))
    exterior_hash = sha_file(EXTERIOR_CLASSIFICATION)
    if exterior_hash != EXPECTED_EXTERIOR_CLASSIFICATION_SHA256:
        raise RuntimeError(
            f"{OPERATION}: exterior classification hash mismatch; "
            f"path={EXTERIOR_CLASSIFICATION}; "
            f"expected={EXPECTED_EXTERIOR_CLASSIFICATION_SHA256}; "
            f"actual={exterior_hash}"
        )
    exterior = json.loads(EXTERIOR_CLASSIFICATION.read_text(encoding="utf-8"))
    reference_face_ids = set(
        scope["source_reference_scope"]["source_face_ids"]
    )
    retained_face_ids = set(
        exterior["classification"]["final_retained_exterior_face_ids"]
    )
    safe_removal_face_ids = exterior["classification"]["safe_removal_face_ids"]
    if retained_face_ids != reference_face_ids or safe_removal_face_ids:
        raise RuntimeError(
            f"{OPERATION}: exterior review does not preserve the exact current "
            f"source scope; retained_missing="
            f"{sorted(reference_face_ids - retained_face_ids)}; "
            f"retained_extra={sorted(retained_face_ids - reference_face_ids)}; "
            f"safe_removal={safe_removal_face_ids}"
        )
    expected_blend = Path(scope["source_scene"]["blend"]).resolve()
    actual_blend = Path(bpy.data.filepath).resolve()
    if actual_blend != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}; "
            f"actual={actual_blend}"
        )
    source = require_mesh(scope["source_scene"]["source_object"])
    fit_reference = require_mesh(scope["source_scene"]["fit_reference_object"])
    cutter = require_mesh(scope["source_scene"]["cutter_object"])
    if bpy.data.collections.get(COLLECTION_NAME) is not None or any(
        obj.name.startswith(PANEL_PREFIX) for obj in bpy.data.objects
    ):
        raise RuntimeError(
            f"{OPERATION}: scaffold objects already exist in input scene; "
            f"collection={COLLECTION_NAME}; actionable_reason=run from the "
            "verified V24 source Blend or explicitly archive the prior result"
        )

    source_before = mesh_fingerprint(source)
    fit_reference_before = mesh_fingerprint(fit_reference)
    cutter_before = mesh_fingerprint(cutter)
    axis = Vector(scope["construction_frame"]["axis"]).normalized()
    frame_center = Vector(scope["construction_frame"]["center_mm"])
    axis_x, axis_y = section.plane_basis(axis)
    evaluated_fit_triangles = section.evaluated_triangles(fit_reference)
    provenance, cutter_points, cutter_faces, orientation_sign = (
        cutter_audit.evaluated_cutter_provenance(cutter)
    )

    panel_payloads = []
    candidate_triangles = []
    panel_count = len(scope["panels"])
    for panel_index, panel in enumerate(scope["panels"]):
        lower, upper = panel["station_interval_mm"]
        if panel_index:
            lower += SHARED_BOUNDARY_INSET_MM
        if panel_index < panel_count - 1:
            upper -= SHARED_BOUNDARY_INSET_MM
        if upper <= lower:
            raise RuntimeError(
                f"{OPERATION}: seam inset collapsed panel interval; "
                f"panel={panel['panel_id']}; lower={lower}; upper={upper}"
            )
        stations = [
            lower + (upper - lower) * index / (SECTION_COUNT - 1)
            for index in range(SECTION_COUNT)
        ]
        ellipses = []
        rings = []
        for station in stations:
            origin = frame_center + axis * station
            cloud = section_points(
                evaluated_fit_triangles,
                origin,
                axis,
            )
            ellipse = enclosing_ellipse(
                cloud,
                origin,
                axis_x,
                axis_y,
                args.radial_allowance_mm,
            )
            ellipses.append(
                {
                    key: value
                    for key, value in ellipse.items()
                    if key != "center"
                }
            )
            rings.append(arc_points(ellipse, axis_x, axis_y))
        vertices, faces = panel_geometry(rings)
        panel_id = panel["panel_id"]
        candidate_triangles.extend(
            triangle_records(panel_id, vertices, faces)
        )
        panel_payloads.append(
            {
                "panel_id": panel_id,
                "object_name": f"{PANEL_PREFIX}{panel_index}_SCAFFOLD",
                "station_interval_after_seam_inset_mm": [lower, upper],
                "stations_mm": stations,
                "cross_sections": ellipses,
                "vertices": vertices,
                "faces": faces,
            }
        )

    internal_overlaps = {
        payload["panel_id"]: nonadjacent_overlaps(
            payload["vertices"],
            payload["faces"],
        )
        for payload in panel_payloads
    }
    cross_panel_overlaps = {}
    for first_id, first in enumerate(panel_payloads):
        for second in panel_payloads[first_id + 1 :]:
            key = f"{first['panel_id']}::{second['panel_id']}"
            cross_panel_overlaps[key] = nonadjacent_overlaps(
                first["vertices"],
                first["faces"],
                second["vertices"],
                second["faces"],
            )
    surface_intersection_gate_pass = not any(
        internal_overlaps.values()
    ) and not any(cross_panel_overlaps.values())

    clearance = cutter_audit.clearance_contract(
        candidate_triangles,
        cutter_points,
        cutter_faces,
        orientation_sign,
    )
    clearance_result = clearance_summary(clearance)
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": (
            "V28_THREE_PANEL_SCAFFOLD_GEOMETRY_PASS"
            if (
                clearance_result["vertex_edge_and_triangle_interior_gate_pass"]
                and surface_intersection_gate_pass
            )
            else "V28_THREE_PANEL_SCAFFOLD_GEOMETRY_REJECT"
        ),
        "code_sha256": sha_file(Path(__file__).resolve()),
        "verified_scope_authority": {
            "path": str(SCOPE_AUTHORITY.relative_to(ROOT)),
            "sha256": scope_hash,
        },
        "verified_exterior_classification": {
            "path": str(EXTERIOR_CLASSIFICATION.relative_to(ROOT)),
            "sha256": exterior_hash,
            "result": exterior["result"],
            "retained_face_count": len(retained_face_ids),
            "safe_removal_face_count": len(safe_removal_face_ids),
        },
        "input_blend": str(actual_blend),
        "output_blend": str(args.output_blend.resolve()),
        "construction": {
            "panel_count": panel_count,
            "cross_sections_per_panel": SECTION_COUNT,
            "arc_points_per_section": ARC_POINT_COUNT,
            "opening_degrees": OPENING_DEGREES,
            "opening_is_provisional_neutral_engineering_hypothesis": True,
            "shared_boundary_inset_per_side_mm": SHARED_BOUNDARY_INSET_MM,
            "nominal_axial_seam_mm": SHARED_BOUNDARY_INSET_MM * 2.0,
            "radial_allowance_mm": args.radial_allowance_mm,
            "source_topology_copied": False,
            "fit_reference_topology_copied": False,
            "cutter_topology_copied": False,
            "cross_sections_measured_from": fit_reference.name,
            "cutter_use": "clearance and collision audit only",
            "zero_thickness_evaluation_surfaces": True,
        },
        "panels": [
            {
                key: value
                for key, value in payload.items()
                if key not in {"vertices", "faces"}
            }
            | {
                "vertex_count": len(payload["vertices"]),
                "quad_count": len(payload["faces"]),
            }
            for payload in panel_payloads
        ],
        "clearance": clearance_result,
        "surface_intersections": {
            "per_panel_nonadjacent_overlap_pairs": internal_overlaps,
            "cross_panel_overlap_pairs": cross_panel_overlaps,
            "surface_intersection_gate_pass": surface_intersection_gate_pass,
        },
        "source_mesh_fingerprint_before": source_before,
        "fit_reference_mesh_fingerprint_before": fit_reference_before,
        "cutter_mesh_fingerprint_before": cutter_before,
        "cutter_provenance_fingerprint": provenance["provenance_fingerprint"],
        "mutation": {
            "started": False,
            "output_saved": False,
        },
    }
    atomic_json(args.report.resolve(), report)
    if not (
        clearance_result["vertex_edge_and_triangle_interior_gate_pass"]
        and surface_intersection_gate_pass
    ):
        raise RuntimeError(
            f"{OPERATION}: scaffold geometry rejected before mutation; "
            f"report={args.report.resolve()}; "
            f"rejected_triangles={clearance_result['reject_count']}; "
            f"internal_overlap_pairs="
            f"{sum(len(value) for value in internal_overlaps.values())}; "
            f"cross_panel_overlap_pairs="
            f"{sum(len(value) for value in cross_panel_overlaps.values())}; "
            f"minimum_exact_mm={clearance_result['minimum_exact_triangle_to_cutter_distance_mm']}; "
            f"minimum_signed_mm={clearance_result['minimum_signed_adaptive_sample_margin_mm']}; "
            "actionable_reason=increase the explicit radial allowance or revise "
            "the coarse section placement"
        )

    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    for payload in panel_payloads:
        mesh = bpy.data.meshes.new(f"{payload['object_name']}_MESH")
        mesh.from_pydata(payload["vertices"], [], payload["faces"])
        mesh.update()
        obj = bpy.data.objects.new(payload["object_name"], mesh)
        obj["status"] = "EVALUATION_ONLY"
        obj["mission"] = MISSION
        obj["radial_allowance_mm"] = args.radial_allowance_mm
        obj["opening_degrees"] = OPENING_DEGREES
        obj["minimum_clearance_contract_mm"] = 1.7
        collection.objects.link(obj)
    if mesh_fingerprint(source) != source_before:
        raise RuntimeError(
            f"{OPERATION}: source mesh changed during scaffold construction; "
            f"object={source.name}; output not saved"
        )
    if mesh_fingerprint(cutter) != cutter_before:
        raise RuntimeError(
            f"{OPERATION}: cutter mesh changed during scaffold construction; "
            f"object={cutter.name}; output not saved"
        )
    if mesh_fingerprint(fit_reference) != fit_reference_before:
        raise RuntimeError(
            f"{OPERATION}: fit-reference mesh changed during scaffold "
            f"construction; object={fit_reference.name}; output not saved"
        )

    args.output_blend.resolve().parent.mkdir(parents=True, exist_ok=True)
    report["mutation"]["started"] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    report["mutation"]["output_saved"] = True
    report["output_blend_sha256"] = sha_file(args.output_blend.resolve())
    report["source_mesh_fingerprint_after"] = mesh_fingerprint(source)
    report["fit_reference_mesh_fingerprint_after"] = mesh_fingerprint(
        fit_reference
    )
    report["cutter_mesh_fingerprint_after"] = mesh_fingerprint(cutter)
    atomic_json(args.report.resolve(), report)
    receipt = {
        "operation": OPERATION,
        "status": "DONE",
        "report": str(args.report.resolve()),
        "report_sha256": sha_file(args.report.resolve()),
        "output_blend": str(args.output_blend.resolve()),
        "output_blend_sha256": report["output_blend_sha256"],
        "scope_authority_sha256": scope_hash,
        "exterior_classification_sha256": exterior_hash,
    }
    atomic_json(args.receipt.resolve(), receipt)
    print(
        f"DONE {OPERATION}: output={args.output_blend.resolve()}; "
        f"report={args.report.resolve()}; "
        f"minimum_signed_clearance_mm="
        f"{clearance_result['minimum_signed_adaptive_sample_margin_mm']:.6f}"
    )


if __name__ == "__main__":
    main()
