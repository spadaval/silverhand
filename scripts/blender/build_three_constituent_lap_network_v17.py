"""Build a three-solid local lap network for Repair 014 v17."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_connection_aware_network_v12 as v12  # noqa: E402
import build_projected_terminal_surface_pads_v16 as v16  # noqa: E402
import build_surface_following_fan_saddles_v15 as v15  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import preflight_distinct_cage_terminals_v13 as v13  # noqa: E402
from try_landmark_sector_retopology import REVIEW_COLLECTION  # noqa: E402


OPERATION = "THREE_CONSTITUENT_LOCAL_LAP_NETWORK_V17"
AUTHORITY_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
AUTHORITY_REPORT_SHA256 = (
    "588d1bff06d6adb9a906a62e85a19465694c48f584c47377c507c16fd2054de2"
)
EXPECTED_RETAINED_FINGERPRINT = v15.EXPECTED_RETAINED_FINGERPRINT
EXPECTED_C9_FINGERPRINT = v16.EXPECTED_C9_FINGERPRINT
PAD_LONG_MM = 10.0
PAD_SHORT_MM = 7.0
PAD_CONTACT_LAP_MM = 1.5
PAD_ROTATION_DEGREES = 0
BRIDGE_LAPS_MM = (1.5, 2.0, 2.5)
AUTHORITY_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_projected_terminal_surface_pads_v16/build_report.json"
)


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def constituent_metrics(
    name,
    points,
    faces,
    target_geometry,
    allowed_open_faces,
    open_points,
    open_faces,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
    target_length,
    grid,
):
    target_pairs = v14.overlap_pairs(points, faces, *target_geometry)
    full_pairs = v14.overlap_pairs(points, faces, open_points, open_faces)
    unrelated_pairs = [
        pair for pair in full_pairs if pair[1] not in allowed_open_faces
    ]
    c9_pairs = v14.overlap_pairs(points, faces, c9_points, c9_faces)
    cutter_pairs = v14.overlap_pairs(
        points,
        faces,
        cutter_points,
        cutter_faces,
    )
    self_pairs = v16.nonadjacent_self_overlaps(points, faces)
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    gate = all(
        (
            target_pairs,
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
            quality["degenerate_triangle_count"] == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
        )
    )
    return {
        "name": name,
        "target_overlap_count": len(target_pairs),
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
        "gate_pass": gate,
    }


def closed_pad(result):
    points, faces, opening_ring, metrics = result
    closed_faces = v16.oriented_faces(
        points,
        [*faces, tuple(opening_ring)],
    )
    return points, closed_faces, metrics


def candidate(
    lap_mm,
    upper_point,
    lower_point,
    upper_geometry,
    lower_geometry,
    upper_allowed_faces,
    lower_allowed_faces,
    bridge_allowed_faces,
    open_points,
    open_faces,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
    target_length,
    grid,
):
    route = lower_point - upper_point
    route.normalize()
    upper_points, upper_faces, upper_pad_metrics = closed_pad(
        v16.projected_pad(
            upper_geometry,
            upper_point,
            upper_point - route * PAD_CONTACT_LAP_MM,
            route,
            PAD_LONG_MM,
            PAD_SHORT_MM,
            PAD_CONTACT_LAP_MM,
            PAD_ROTATION_DEGREES,
            target_length,
        )
    )
    lower_points, lower_faces, lower_pad_metrics = closed_pad(
        v16.projected_pad(
            lower_geometry,
            lower_point,
            lower_point + route * PAD_CONTACT_LAP_MM,
            route,
            PAD_LONG_MM,
            PAD_SHORT_MM,
            PAD_CONTACT_LAP_MM,
            PAD_ROTATION_DEGREES,
            target_length,
        )
    )
    bridge_points, bridge_faces, bridge_samples, bridge_widths = (
        v12.connector_geometry(
            [
                upper_point - route * lap_mm,
                lower_point + route * lap_mm,
            ],
            120,
            target_length,
        )
    )
    upper = constituent_metrics(
        "upper_pad",
        upper_points,
        upper_faces,
        upper_geometry,
        upper_allowed_faces,
        open_points,
        open_faces,
        c9_points,
        c9_faces,
        cutter_points,
        cutter_faces,
        target_length,
        grid,
    )
    lower = constituent_metrics(
        "lower_pad",
        lower_points,
        lower_faces,
        lower_geometry,
        lower_allowed_faces,
        open_points,
        open_faces,
        c9_points,
        c9_faces,
        cutter_points,
        cutter_faces,
        target_length,
        grid,
    )
    bridge = constituent_metrics(
        "bridge",
        bridge_points,
        bridge_faces,
        (
            upper_geometry[0] + lower_geometry[0],
            upper_geometry[1]
            + [
                tuple(
                    len(upper_geometry[0]) + index
                    for index in face
                )
                for face in lower_geometry[1]
            ],
        ),
        bridge_allowed_faces,
        open_points,
        open_faces,
        c9_points,
        c9_faces,
        cutter_points,
        cutter_faces,
        target_length,
        grid,
    )
    bridge_upper_pairs = v14.overlap_pairs(
        bridge_points,
        bridge_faces,
        upper_points,
        upper_faces,
    )
    bridge_lower_pairs = v14.overlap_pairs(
        bridge_points,
        bridge_faces,
        lower_points,
        lower_faces,
    )
    pad_pad_pairs = v14.overlap_pairs(
        upper_points,
        upper_faces,
        lower_points,
        lower_faces,
    )
    anti_fin_gate = all(
        (
            metrics[
                "long_axis_terminal_tangent_alignment_abs_dot"
            ]
            >= 0.95,
            metrics["projected_surface_long_extent_mm"] >= 8.0,
            metrics["projection_to_outward_extent_ratio"] >= 2.5,
            metrics["measured_surface_contact_lap_mm"] >= 1.5,
        )
        for metrics in (upper_pad_metrics, lower_pad_metrics)
    )
    graph_connected = all(
        (
            upper["target_overlap_count"] > 0,
            bridge_upper_pairs,
            bridge_lower_pairs,
            lower["target_overlap_count"] > 0,
        )
    )
    passed = all(
        (
            upper["gate_pass"],
            bridge["gate_pass"],
            lower["gate_pass"],
            bridge_upper_pairs,
            bridge_lower_pairs,
            not pad_pad_pairs,
            anti_fin_gate,
            graph_connected,
        )
    )
    return {
        "bridge_terminal_lap_mm": lap_mm,
        "bridge_ring_count": len(bridge_samples),
        "bridge_minimum_width_mm": min(bridge_widths),
        "bridge_maximum_width_mm": max(bridge_widths),
        "bridge_thickness_mm": v12.THICKNESS_MM,
        "upper_pad_metrics": upper_pad_metrics,
        "lower_pad_metrics": lower_pad_metrics,
        "constituents": {
            "upper_pad": upper,
            "bridge": bridge,
            "lower_pad": lower,
        },
        "bridge_upper_pad_overlap_count": len(bridge_upper_pairs),
        "bridge_lower_pad_overlap_count": len(bridge_lower_pairs),
        "upper_lower_pad_direct_overlap_count": len(pad_pad_pairs),
        "combined_minimum_cutter_margin_mm": min(
            upper["minimum_cutter_margin_mm"],
            bridge["minimum_cutter_margin_mm"],
            lower["minimum_cutter_margin_mm"],
        ),
        "anti_fin_topology_gate": anti_fin_gate,
        "graph_connected": graph_connected,
        "gate_pass": passed,
        "_upper_points": upper_points,
        "_upper_faces": upper_faces,
        "_bridge_points": bridge_points,
        "_bridge_faces": bridge_faces,
        "_lower_points": lower_points,
        "_lower_faces": lower_faces,
    }


def baseline_context():
    blend_path = Path(bpy.data.filepath).resolve()
    blend_sha = v14.v10.sha256_file(blend_path)
    report_sha = v14.v10.sha256_file(AUTHORITY_REPORT_PATH)
    if (blend_sha, report_sha) != (
        AUTHORITY_SHA256,
        AUTHORITY_REPORT_SHA256,
    ):
        raise RuntimeError(
            f"{OPERATION}: authority hash mismatch: Blend '{blend_sha}', "
            f"report '{report_sha}'"
        )
    authority = json.loads(
        AUTHORITY_REPORT_PATH.read_text(encoding="utf-8")
    )
    if authority["geometry_emitted"] or authority["gate_pass"]:
        raise RuntimeError(
            f"{OPERATION}: v16 authority unexpectedly emitted geometry"
        )
    repair_objects = {
        obj.name
        for obj in bpy.data.objects
        if obj.name.startswith("EVAL_REPAIR_014")
    }
    if repair_objects != v15.BASELINE_REPAIR_014_OBJECTS:
        raise RuntimeError(
            f"{OPERATION}: baseline object set is {sorted(repair_objects)}"
        )
    staged = bpy.data.objects[v4.v2.base.STAGED_NAME]
    open_cage = bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    staged_points, staged_faces, staged_materials = v14.evaluated_geometry(
        staged
    )
    open_points, open_faces, open_materials = v14.evaluated_geometry(open_cage)
    cutter_points, cutter_faces, _ = v14.evaluated_geometry(cutter)
    mapping = json.loads(v4.v2.MAPPING_PATH.read_text(encoding="utf-8"))
    retained_face_ids = sorted(
        mapping["reconstruction_scope"]["retain_face_ids"]
    )
    retained_ids = sorted(
        {
            vertex
            for face_id in retained_face_ids
            for vertex in staged_faces[face_id]
        }
    )
    retained_points = [
        staged_points[index].copy() for index in retained_ids
    ]
    retained_fingerprint = v4.v2.fingerprint(
        retained_ids,
        retained_points,
    )
    removed = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    rebuilt_points, rebuilt_faces, rebuilt_materials, _, source_to_open = (
        v4.v2.remap_retained(
            staged_points,
            staged_faces,
            staged_materials,
            removed,
        )
    )
    open_exact = all(
        (
            rebuilt_faces == open_faces,
            rebuilt_materials == open_materials,
            all(
                (first - second).length <= 1.0e-4
                for first, second in zip(rebuilt_points, open_points)
            ),
        )
    )
    c9_points, c9_faces = v4.component9_geometry()
    c9_fingerprint = v4.v2.fingerprint(range(len(c9_points)), c9_points)
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    tip_gap = (
        staged_points[centerline_ids[0]]
        - staged_points[centerline_ids[-1]]
    ).length
    hard_errors = {
        str(source_id): round(
            (open_points[source_to_open[source_id]] - staged_points[source_id]).length,
            9,
        )
        for source_id in (5840, 5852)
    }
    checks = {
        "baseline_eval_objects": sorted(repair_objects),
        "retained_face_count": len(retained_face_ids),
        "retained_fingerprint": retained_fingerprint,
        "retained_fingerprint_exact": (
            retained_fingerprint == EXPECTED_RETAINED_FINGERPRINT
        ),
        "open_lineage_and_materials_exact": open_exact,
        "component_9_fingerprint": c9_fingerprint,
        "component_9_fingerprint_exact": (
            c9_fingerprint == EXPECTED_C9_FINGERPRINT
        ),
        "central_bowl_open": True,
        "tip_gap_mm": round(tip_gap, 6),
        "tip_gap_exact": abs(tip_gap - 30.588488) <= 1.0e-6,
        "hard_control_error_mm": hard_errors,
    }
    if not all(
        (
            checks["retained_face_count"] == 1409,
            checks["retained_fingerprint_exact"],
            checks["open_lineage_and_materials_exact"],
            checks["component_9_fingerprint_exact"],
            checks["tip_gap_exact"],
            all(value <= 1.0e-4 for value in hard_errors.values()),
        )
    ):
        raise RuntimeError(f"{OPERATION}: baseline proof failed: {checks}")
    return {
        "blend_path": blend_path,
        "blend_sha": blend_sha,
        "report_sha": report_sha,
        "checks": checks,
        "staged": staged,
        "staged_points": staged_points,
        "staged_faces": staged_faces,
        "staged_materials": staged_materials,
        "open_points": open_points,
        "open_faces": open_faces,
        "open_materials": open_materials,
        "cutter": cutter,
        "cutter_points": cutter_points,
        "cutter_faces": cutter_faces,
        "c9_points": c9_points,
        "c9_faces": c9_faces,
        "mapping": mapping,
        "retained_face_ids": retained_face_ids,
        "retained_ids": retained_ids,
        "retained_points": retained_points,
        "source_to_open": source_to_open,
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    prefix = v14.argument("--prefix")
    context = baseline_context()
    retained_ids = context["retained_ids"]
    source_to_retained = {
        source_id: local_id
        for local_id, source_id in enumerate(retained_ids)
    }
    retained_faces = [
        tuple(
            source_to_retained[index]
            for index in context["staged_faces"][face_id]
        )
        for face_id in context["retained_face_ids"]
    ]
    components = v13.mesh_components(
        len(context["retained_points"]),
        retained_faces,
    )
    components.sort(
        key=lambda component: min(
            retained_ids[index] for index in component["vertices"]
        )
    )
    lower_component, upper_component = components[:2]
    upper_geometry = v13.local_component_geometry(
        context["retained_points"],
        retained_faces,
        upper_component,
    )
    lower_geometry = v13.local_component_geometry(
        context["retained_points"],
        retained_faces,
        lower_component,
    )
    removed = set(
        context["mapping"]["reconstruction_scope"]["rebuild_face_ids"]
    )
    open_face_by_source_face = {
        source_face_id: open_face_id
        for open_face_id, source_face_id in enumerate(
            face_id
            for face_id in range(len(context["staged_faces"]))
            if face_id not in removed
        )
    }
    upper_allowed = {
        open_face_by_source_face[
            context["retained_face_ids"][face_id]
        ]
        for face_id in upper_component["faces"]
    }
    lower_allowed = {
        open_face_by_source_face[
            context["retained_face_ids"][face_id]
        ]
        for face_id in lower_component["faces"]
    }
    bridge_allowed = upper_allowed | lower_allowed
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    grid, _ = v4.cutter_grid(context["cutter"])
    upper_point = context["staged_points"][5702]
    lower_point = context["staged_points"][1784]
    records = [
        candidate(
            lap,
            upper_point,
            lower_point,
            upper_geometry,
            lower_geometry,
            upper_allowed,
            lower_allowed,
            bridge_allowed,
            context["open_points"],
            context["open_faces"],
            context["c9_points"],
            context["c9_faces"],
            context["cutter_points"],
            context["cutter_faces"],
            target_length,
            grid,
        )
        for lap in BRIDGE_LAPS_MM
    ]
    passing = [record for record in records if record["gate_pass"]]
    selected = passing[0] if passing else None
    objects = None
    result_prefix_exact = False
    retained_after_fingerprint = None
    if selected:
        material = Counter(
            context["staged_materials"][face_id]
            for face_id in context["retained_face_ids"]
        ).most_common(1)[0][0]
        collection = v14.ensure_collection(REVIEW_COLLECTION)
        constituent_specs = (
            (
                "UPPER_PAD",
                selected["_upper_points"],
                selected["_upper_faces"],
            ),
            (
                "BRIDGE",
                selected["_bridge_points"],
                selected["_bridge_faces"],
            ),
            (
                "LOWER_PAD",
                selected["_lower_points"],
                selected["_lower_faces"],
            ),
        )
        constituent_objects = {}
        for role, points, faces in constituent_specs:
            obj = v14.create_object(
                f"{prefix}_{role}",
                points,
                faces,
                [material] * len(faces),
                list(context["staged"].data.materials),
                collection,
            )
            constituent_objects[role.lower()] = obj.name
        result_points = [point.copy() for point in context["open_points"]]
        result_faces = list(context["open_faces"])
        result_materials = list(context["open_materials"])
        for _, points, faces in constituent_specs:
            offset = len(result_points)
            result_points.extend(point.copy() for point in points)
            result_faces.extend(
                tuple(offset + index for index in face)
                for face in faces
            )
            result_materials.extend([material] * len(faces))
        result_object = v14.create_object(
            f"{prefix}_AFTER",
            result_points,
            result_faces,
            result_materials,
            list(context["staged"].data.materials),
            collection,
        )
        evaluated_points, evaluated_faces, evaluated_materials = (
            v14.evaluated_geometry(result_object)
        )
        result_prefix_exact = all(
            (
                evaluated_faces[: len(context["open_faces"])]
                == context["open_faces"],
                evaluated_materials[: len(context["open_materials"])]
                == context["open_materials"],
                all(
                    (first - second).length <= 1.0e-4
                    for first, second in zip(
                        evaluated_points[: len(context["open_points"])],
                        context["open_points"],
                    )
                ),
            )
        )
        retained_after_fingerprint = v4.v2.fingerprint(
            retained_ids,
            [
                evaluated_points[context["source_to_open"][source_id]]
                for source_id in retained_ids
            ],
        )
        objects = {
            "result": result_object.name,
            **constituent_objects,
        }
    preservation_gate = all(
        (
            bool(selected),
            result_prefix_exact,
            retained_after_fingerprint == EXPECTED_RETAINED_FINGERPRINT,
            context["checks"]["component_9_fingerprint_exact"],
            context["checks"]["central_bowl_open"],
            context["checks"]["tip_gap_exact"],
            all(
                value <= 1.0e-4
                for value in context["checks"][
                    "hard_control_error_mm"
                ].values()
            ),
        )
    )
    gate_pass = bool(selected) and preservation_gate
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": (
            "evaluation_only_three_constituent_lap_network_machine_pass"
            if gate_pass
            else "evaluation_only_three_constituent_lap_network_machine_failed"
        ),
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "authority_report": str(AUTHORITY_REPORT_PATH),
        "authority_report_sha256": context["report_sha"],
        "authority_recovery": context["checks"],
        "construction": {
            "constituents": [
                "upper_projected_pad",
                "middle_narrow_bridge",
                "lower_projected_pad",
            ],
            "boolean_union": False,
            "shared_loft": False,
            "global_backing": False,
            "junction": "measured local overlap laps between closed solids",
        },
        "bounded_search": {
            "bridge_terminal_laps_mm": list(BRIDGE_LAPS_MM),
            "records": [public(record) for record in records],
        },
        "selected_network": public(selected) if selected else None,
        "graph": {
            "nodes": [
                "T_CAGE_1",
                "UPPER_PAD_V17",
                "BRIDGE_V17",
                "LOWER_PAD_V17",
                "T_CAGE_0",
            ],
            "edges": [
                ["T_CAGE_1", "UPPER_PAD_V17"],
                ["UPPER_PAD_V17", "BRIDGE_V17"],
                ["BRIDGE_V17", "LOWER_PAD_V17"],
                ["LOWER_PAD_V17", "T_CAGE_0"],
            ],
            "connected": bool(selected and selected["graph_connected"]),
        },
        "preservation": {
            "baseline_checks": context["checks"],
            "result_open_prefix_exact": result_prefix_exact,
            "retained_fingerprint_after": retained_after_fingerprint,
            "retained_fingerprint_equal": (
                retained_after_fingerprint == EXPECTED_RETAINED_FINGERPRINT
            ),
            "component_9_unchanged": True,
            "central_bowl_open": True,
            "tip_gap_mm": context["checks"]["tip_gap_mm"],
            "hard_control_error_mm": context["checks"][
                "hard_control_error_mm"
            ],
            "gate_pass": preservation_gate,
        },
        "objects": objects,
        "gate_pass": gate_pass,
        "geometry_emitted": selected is not None,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
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
                "gate_pass": gate_pass,
                "selected_network": public(selected) if selected else None,
                "geometry_emitted": selected is not None,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v17 three-constituent lap network gate_pass={gate_pass}; "
        "promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
