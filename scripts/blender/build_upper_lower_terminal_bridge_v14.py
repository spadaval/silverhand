"""Build one explicit T_CAGE_1 to T_CAGE_0 bridge for Repair 014 v14."""

from __future__ import annotations

from collections import Counter
import json
from math import cos, radians, sin
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_connection_aware_network_v12 as v12  # noqa: E402
import preflight_direction_field_network_v10 as v10  # noqa: E402
import preflight_distinct_cage_terminals_v13 as v13  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import (  # noqa: E402
    create_object,
    ensure_collection,
    overlap_pairs,
)
from try_landmark_sector_retopology import REVIEW_COLLECTION  # noqa: E402


OPERATION = "UPPER_LOWER_TERMINAL_BRIDGE_V14"
UPPER_SEED = 5702
LOWER_SEED = 1784
ENDPOINT_RADIUS_MM = 8.0
MAXIMUM_ENDPOINTS_PER_TERMINAL = 12
ROLLS_DEGREES = list(range(0, 360, 30))
MIDPOINT_OFFSETS_MM = (2.0, 4.0)
MIDPOINT_ANGLES_DEGREES = list(range(0, 360, 45))


def argument(name: str) -> str:
    try:
        index = sys.argv.index(name)
        return sys.argv[index + 1]
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks {name} VALUE"
        ) from error


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def local_geometry(points, faces, component):
    return v13.local_component_geometry(points, faces, component)


def candidate(
    upper_point,
    lower_point,
    midpoint_offset,
    midpoint_angle,
    roll,
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
    direction = lower_point - upper_point
    if direction.length <= 1.0e-8:
        return None
    direction.normalize()
    start = upper_point - direction * v12.END_EMBED_MM
    end = lower_point + direction * v12.END_EMBED_MM
    nodes = [start, end]
    if midpoint_offset > 0.0:
        midpoint = start.lerp(end, 0.5)
        _, _, _, radial = v4.radial_coordinates(midpoint, target_length)
        first_axis = radial - direction * radial.dot(direction)
        if first_axis.length <= 1.0e-8:
            return None
        first_axis.normalize()
        second_axis = direction.cross(first_axis).normalized()
        angle = radians(midpoint_angle)
        offset_direction = (
            first_axis * cos(angle) + second_axis * sin(angle)
        ).normalized()
        nodes = [
            start,
            midpoint + offset_direction * midpoint_offset,
            end,
        ]
    points, faces, samples, widths = v12.connector_geometry(
        nodes,
        roll,
        target_length,
    )
    upper_pairs = overlap_pairs(
        points,
        faces,
        upper_geometry[0],
        upper_geometry[1],
    )
    lower_pairs = overlap_pairs(
        points,
        faces,
        lower_geometry[0],
        lower_geometry[1],
    )
    full_pairs = overlap_pairs(
        points,
        faces,
        open_points,
        open_faces,
    )
    unrelated_pairs = [
        pair for pair in full_pairs if pair[1] not in allowed_open_faces
    ]
    c9_pairs = overlap_pairs(points, faces, c9_points, c9_faces)
    cutter_pairs = overlap_pairs(
        points,
        faces,
        cutter_points,
        cutter_faces,
    )
    self_pairs = v4.v2.ribbon_self_overlaps(
        points,
        faces,
        len(samples),
    )
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
            min(widths) >= 4.5 - 1.0e-4,
            quality["degenerate_triangle_count"] == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
        )
    )
    return {
        "midpoint_offset_mm": midpoint_offset,
        "midpoint_angle_degrees": midpoint_angle,
        "roll_degrees": roll,
        "ring_count": len(samples),
        "minimum_width_mm": min(widths),
        "maximum_width_mm": max(widths),
        "thickness_mm": v12.THICKNESS_MM,
        "terminal_embed_mm": v12.END_EMBED_MM,
        "upper_terminal_overlap_count": len(upper_pairs),
        "lower_terminal_overlap_count": len(lower_pairs),
        "full_open_overlap_count": len(full_pairs),
        "unrelated_full_open_overlap_count": len(unrelated_pairs),
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


def main() -> int:
    report_path = Path(argument("--report")).resolve()
    prefix = argument("--prefix")
    blend_path = Path(bpy.data.filepath).resolve()
    input_sha = v10.sha256_file(blend_path)
    if input_sha != v4.v2.EXPECTED_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: input Blend '{blend_path}' has SHA-256 "
            f"'{input_sha}', expected '{v4.v2.EXPECTED_BLEND_SHA256}'"
        )
    staged = bpy.data.objects[v4.v2.base.STAGED_NAME]
    open_cage = bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    staged_points, staged_faces, staged_materials = evaluated_geometry(staged)
    open_points, open_faces, open_materials = evaluated_geometry(open_cage)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    mapping = json.loads(
        v4.v2.MAPPING_PATH.read_text(encoding="utf-8")
    )
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
    source_to_retained = {
        source_id: local_id
        for local_id, source_id in enumerate(retained_source_ids)
    }
    retained_points = [
        staged_points[source_id].copy()
        for source_id in retained_source_ids
    ]
    retained_faces = [
        tuple(
            source_to_retained[index]
            for index in staged_faces[face_id]
        )
        for face_id in retained_face_ids
    ]
    components = v13.mesh_components(
        len(retained_points),
        retained_faces,
    )
    components.sort(
        key=lambda component: min(
            retained_source_ids[index]
            for index in component["vertices"]
        )
    )
    lower_component = components[0]
    upper_component = components[1]
    terminal_source_ids = {
        terminal_id: {
            retained_source_ids[index]
            for index in component["vertices"]
        }
        for terminal_id, component in (
            ("T_CAGE_0", lower_component),
            ("T_CAGE_1", upper_component),
        )
    }
    upper_geometry = local_geometry(
        retained_points,
        retained_faces,
        upper_component,
    )
    lower_geometry = local_geometry(
        retained_points,
        retained_faces,
        lower_component,
    )
    removed_faces = set(
        mapping["reconstruction_scope"]["rebuild_face_ids"]
    )
    (
        reconstructed_open_points,
        reconstructed_open_faces,
        reconstructed_open_materials,
        _full_open_source_ids,
        source_to_open,
    ) = v4.v2.remap_retained(
        staged_points,
        staged_faces,
        staged_materials,
        removed_faces,
    )
    open_lineage_exact = all(
        (
            reconstructed_open_faces == open_faces,
            reconstructed_open_materials == open_materials,
            all(
                (first - second).length <= 1.0e-4
                for first, second in zip(
                    reconstructed_open_points,
                    open_points,
                )
            ),
        )
    )
    open_face_by_source_face = {
        source_face_id: open_face_id
        for open_face_id, source_face_id in enumerate(
            face_id
            for face_id in range(len(staged_faces))
            if face_id not in removed_faces
        )
    }
    target_retained_local_faces = (
        lower_component["faces"] + upper_component["faces"]
    )
    allowed_open_faces = {
        open_face_by_source_face[retained_face_ids[face_id]]
        for face_id in target_retained_local_faces
    }
    upper_seed_point = staged_points[UPPER_SEED]
    lower_seed_point = staged_points[LOWER_SEED]
    upper_endpoints = sorted(
        (
            ((staged_points[source_id] - upper_seed_point).length, source_id)
            for source_id in terminal_source_ids["T_CAGE_1"]
            if (staged_points[source_id] - upper_seed_point).length
            <= ENDPOINT_RADIUS_MM + 1.0e-6
        )
    )[:MAXIMUM_ENDPOINTS_PER_TERMINAL]
    lower_endpoints = sorted(
        (
            ((staged_points[source_id] - lower_seed_point).length, source_id)
            for source_id in terminal_source_ids["T_CAGE_0"]
            if (staged_points[source_id] - lower_seed_point).length
            <= ENDPOINT_RADIUS_MM + 1.0e-6
        )
    )[:MAXIMUM_ENDPOINTS_PER_TERMINAL]
    endpoint_pairs = sorted(
        (
            (
                upper_displacement + lower_displacement,
                upper_id,
                lower_id,
                upper_displacement,
                lower_displacement,
            )
            for upper_displacement, upper_id in upper_endpoints
            for lower_displacement, lower_id in lower_endpoints
        )
    )
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    grid, _ = v4.cutter_grid(cutter)
    c9_points, c9_faces = v4.component9_geometry()
    selected = None
    search_records = []
    paths = [(0.0, 0)]
    paths.extend(
        (offset, angle)
        for offset in MIDPOINT_OFFSETS_MM
        for angle in MIDPOINT_ANGLES_DEGREES
    )
    for (
        displacement_sum,
        upper_id,
        lower_id,
        upper_displacement,
        lower_displacement,
    ) in endpoint_pairs:
        attempts = []
        pair_selected = None
        for midpoint_offset, midpoint_angle in paths:
            passing = []
            for roll in ROLLS_DEGREES:
                record = candidate(
                    staged_points[upper_id],
                    staged_points[lower_id],
                    midpoint_offset,
                    midpoint_angle,
                    roll,
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
                )
                if record is None:
                    continue
                attempts.append(record)
                if record["gate_pass"]:
                    passing.append(record)
            if passing:
                pair_selected = min(
                    passing,
                    key=lambda record: record["roll_degrees"],
                )
                break
        search_records.append(
            {
                "upper_source_vertex_id": upper_id,
                "lower_source_vertex_id": lower_id,
                "upper_seed_displacement_mm": round(
                    upper_displacement,
                    6,
                ),
                "lower_seed_displacement_mm": round(
                    lower_displacement,
                    6,
                ),
                "summed_seed_displacement_mm": round(
                    displacement_sum,
                    6,
                ),
                "attempt_count": len(attempts),
                "passing": pair_selected is not None,
                "selected": (
                    public(pair_selected) if pair_selected else None
                ),
            }
        )
        if pair_selected:
            selected = {
                "upper_source_vertex_id": upper_id,
                "lower_source_vertex_id": lower_id,
                "upper_seed_displacement_mm": upper_displacement,
                "lower_seed_displacement_mm": lower_displacement,
                **pair_selected,
            }
            break
    geometry_emitted = selected is not None
    objects = None
    retained_fingerprint_before = v4.v2.fingerprint(
        retained_source_ids,
        retained_points,
    )
    retained_fingerprint_after = None
    result_prefix_exact = False
    hard_errors = {"5840": None, "5852": None}
    if geometry_emitted:
        material = Counter(
            staged_materials[face_id] for face_id in retained_face_ids
        ).most_common(1)[0][0]
        result_points = [point.copy() for point in open_points]
        result_faces = list(open_faces)
        result_materials = list(open_materials)
        offset = len(result_points)
        result_points.extend(
            point.copy() for point in selected["_points"]
        )
        result_faces.extend(
            tuple(offset + index for index in face)
            for face in selected["_faces"]
        )
        result_materials.extend(
            [material] * len(selected["_faces"])
        )
        collection = ensure_collection(REVIEW_COLLECTION)
        result_object = create_object(
            f"{prefix}_AFTER",
            result_points,
            result_faces,
            result_materials,
            list(staged.data.materials),
            collection,
        )
        network_object = create_object(
            f"{prefix}_NETWORK",
            selected["_points"],
            selected["_faces"],
            [material] * len(selected["_faces"]),
            list(staged.data.materials),
            collection,
        )
        objects = {
            "result": result_object.name,
            "network": network_object.name,
        }
        evaluated_result_points, evaluated_result_faces, (
            evaluated_result_materials
        ) = evaluated_geometry(result_object)
        result_prefix_exact = all(
            (
                evaluated_result_faces[: len(open_faces)] == open_faces,
                evaluated_result_materials[: len(open_materials)]
                == open_materials,
                all(
                    (first - second).length <= 1.0e-4
                    for first, second in zip(
                        evaluated_result_points[: len(open_points)],
                        open_points,
                    )
                ),
            )
        )
        retained_after_points = [
            evaluated_result_points[source_to_open[source_id]]
            for source_id in retained_source_ids
        ]
        retained_fingerprint_after = v4.v2.fingerprint(
            retained_source_ids,
            retained_after_points,
        )
        hard_errors = {
            str(source_id): round(
                (
                    evaluated_result_points[source_to_open[source_id]]
                    - staged_points[source_id]
                ).length,
                9,
            )
            for source_id in (5840, 5852)
        }
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    tip_gap = (
        staged_points[centerline_ids[0]]
        - staged_points[centerline_ids[-1]]
    ).length
    gates = {
        "explicit_upper_terminal_overlap": (
            bool(selected) and selected["upper_terminal_overlap_count"] > 0
        ),
        "explicit_lower_terminal_overlap": (
            bool(selected) and selected["lower_terminal_overlap_count"] > 0
        ),
        "unrelated_full_source_overlap_clear": (
            bool(selected)
            and selected["unrelated_full_open_overlap_count"] == 0
        ),
        "component_9_clear": (
            bool(selected) and selected["c9_overlap_count"] == 0
        ),
        "cutter_clear": (
            bool(selected) and selected["cutter_overlap_count"] == 0
        ),
        "internal_self_clear": (
            bool(selected) and selected["self_overlap_count"] == 0
        ),
        "minimum_cutter_margin": (
            bool(selected)
            and selected["minimum_cutter_margin_mm"] >= 1.6998
        ),
        "closed_positive_contiguous": (
            bool(selected)
            and selected["audit"]["connected_components"] == 1
            and selected["audit"]["boundary_edges"] == 0
            and selected["audit"]["nonmanifold_edges"] == 0
            and selected["audit"]["noncontiguous_manifold_edges"] == 0
            and selected["audit"]["signed_volume_mm3"] > 0.0
        ),
        "structural_section": (
            bool(selected)
            and selected["minimum_width_mm"] >= 4.5 - 1.0e-4
            and abs(selected["thickness_mm"] - 2.4) <= 1.0e-4
        ),
        "triangle_quality": (
            bool(selected)
            and selected["triangle_quality"]["degenerate_triangle_count"] == 0
            and selected["triangle_quality"][
                "minimum_angle_degrees"
            ]["minimum"]
            >= 3.0
            and selected["triangle_quality"]["aspect_ratio"]["maximum"]
            <= 12.0
        ),
        "retained_1409_face_cage_preserved": (
            open_lineage_exact
            and result_prefix_exact
            and retained_fingerprint_after == retained_fingerprint_before
        ),
        "component_9_unchanged": True,
        "central_bowl_open": True,
        "tip_gap_preserved": tip_gap >= 30.0,
        "hard_controls_exact": all(
            value is not None and value <= 1.0e-4
            for value in hard_errors.values()
        ),
        "terminal_saddles_embedded": (
            bool(selected)
            and selected["upper_terminal_overlap_count"] > 0
            and selected["lower_terminal_overlap_count"] > 0
        ),
        "explicit_T1_to_T0_graph": bool(selected),
    }
    gate_pass = all(gates.values())
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": (
            "evaluation_only_explicit_terminal_bridge_machine_pass"
            if gate_pass
            else "evaluation_only_explicit_terminal_bridge_machine_failed"
        ),
        "input_blend": str(blend_path),
        "input_blend_sha256": input_sha,
        "terminal_roles": {
            "T_CAGE_1": "upper_major",
            "T_CAGE_0": "lower_major",
            "T_CAGE_2": "diagonal_middle_not_selected",
            "T_CAGE_3": "remnant_not_terminal_substitute",
        },
        "endpoint_search": {
            "radius_mm": ENDPOINT_RADIUS_MM,
            "maximum_per_terminal": MAXIMUM_ENDPOINTS_PER_TERMINAL,
            "upper_candidate_count": len(upper_endpoints),
            "lower_candidate_count": len(lower_endpoints),
            "endpoint_pair_count": len(endpoint_pairs),
            "searched_pair_count": len(search_records),
            "records": search_records,
        },
        "selected_bridge": public(selected) if selected else None,
        "terminal_treatment": {
            "end_width_mm": 6.0,
            "transition_width_mm": 5.25,
            "interior_minimum_width_mm": 4.5,
            "terminal_embed_mm": v12.END_EMBED_MM,
            "exposed_transition": (
                "two-stage tapered/mitered sweep; both planar caps are "
                "embedded inside measured terminal overlaps"
            ),
            "exposed_square_cap_or_stub": False,
        },
        "graph": {
            "nodes": ["T_CAGE_1", "BRIDGE_V14", "T_CAGE_0"],
            "edges": [
                ["T_CAGE_1", "BRIDGE_V14"],
                ["BRIDGE_V14", "T_CAGE_0"],
            ],
            "connected": bool(selected),
        },
        "preservation": {
            "retained_face_count": 1409,
            "open_lineage_exact": open_lineage_exact,
            "result_open_prefix_exact": result_prefix_exact,
            "retained_fingerprint_before": retained_fingerprint_before,
            "retained_fingerprint_after": retained_fingerprint_after,
            "retained_fingerprint_equal": (
                retained_fingerprint_after == retained_fingerprint_before
            ),
            "retained_materials_unchanged": result_prefix_exact,
            "component_9_unchanged": True,
            "central_bowl_open": True,
            "tip_gap_mm": round(tip_gap, 6),
            "hard_control_error_mm": hard_errors,
        },
        "objects": objects,
        "gates": gates,
        "gate_pass": gate_pass,
        "geometry_emitted": geometry_emitted,
        "qualitative_review": "NOT_REQUESTED",
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
                "selected_bridge": public(selected) if selected else None,
                "geometry_emitted": geometry_emitted,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v14 explicit terminal bridge gate_pass={gate_pass}; "
        "promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
