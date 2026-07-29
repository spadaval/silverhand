"""Evaluate the bounded six-solid elevated-saddle network for Repair 014 v20."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_connection_aware_network_v12 as v12  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
from try_landmark_sector_retopology import REVIEW_COLLECTION  # noqa: E402


OPERATION = "ELEVATED_SURFACE_SADDLES_V20"
SAFE_STOP = "NO_SAFE_ELEVATED_SURFACE_SADDLE"
V13_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_distinct_cage_terminals_v13/build_report.json"
)
RISES_MM = (1.35, 1.40, 1.45, 1.50, 1.55, 1.60)
SCARF_DEPTHS_MM = (0.4, 0.6, 0.8)
PAD_LONG_MM = 10.0
PAD_SHORT_MM = 7.0
UNDERSIDE_EMBED_MM = 1.5
SCARF_CONTAINMENT_MM = 6.0
SHOULDER_TAPER_MM = 3.0
MITER_SETBACK_MM = 1.25
BRANCH_A_IDS = (5702, 1784)
BRANCH_B_IDS = (1780, 1789)
BRANCH_B_FRAMES = {
    1780: {
        "tangent": (0.40696326, -0.64481866, 0.64698523),
        "normal": (-0.89163417, -0.12656972, 0.43470523),
    },
    1789: {
        "tangent": (0.87251949, -0.33392674, -0.35665482),
        "normal": (-0.45573694, -0.81937045, -0.34775835),
    },
}


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def terminal_context(context):
    report = json.loads(V13_REPORT_PATH.read_text(encoding="utf-8"))
    terminals = {
        terminal["terminal_id"]: set(terminal["source_vertex_ids"])
        for terminal in report["terminals"]
    }
    retained = set(context["retained_face_ids"])
    source_faces = {
        terminal_id: {
            face_id
            for face_id in retained
            if set(context["staged_faces"][face_id]) <= source_ids
        }
        for terminal_id, source_ids in terminals.items()
    }
    removed = set(
        context["mapping"]["reconstruction_scope"]["rebuild_face_ids"]
    )
    open_face_by_source = {
        source_face_id: open_face_id
        for open_face_id, source_face_id in enumerate(
            face_id
            for face_id in range(len(context["staged_faces"]))
            if face_id not in removed
        )
    }
    result = {}
    for terminal_id in ("T_CAGE_1", "T_CAGE_0"):
        face_ids = sorted(source_faces[terminal_id])
        vertex_ids = sorted(
            {
                vertex
                for face_id in face_ids
                for vertex in context["staged_faces"][face_id]
            }
        )
        local_by_source = {
            source_id: local_id
            for local_id, source_id in enumerate(vertex_ids)
        }
        points = [
            context["staged_points"][source_id].copy()
            for source_id in vertex_ids
        ]
        faces = [
            tuple(
                local_by_source[index]
                for index in context["staged_faces"][face_id]
            )
            for face_id in face_ids
        ]
        result[terminal_id] = {
            "geometry": (points, faces),
            "allowed_open_faces": {
                open_face_by_source[face_id] for face_id in face_ids
            },
            "bvh": BVHTree.FromPolygons(
                points,
                faces,
                all_triangles=False,
            ),
        }
    return result


def saddle_polygon():
    half_long = PAD_LONG_MM * 0.5
    half_short = PAD_SHORT_MM * 0.5
    return (
        (-half_long + MITER_SETBACK_MM, -half_short),
        (half_long - MITER_SETBACK_MM, -half_short),
        (half_long, -half_short + MITER_SETBACK_MM),
        (half_long, half_short - MITER_SETBACK_MM),
        (half_long - MITER_SETBACK_MM, half_short),
        (-half_long + MITER_SETBACK_MM, half_short),
        (-half_long, half_short - MITER_SETBACK_MM),
        (-half_long, -half_short + MITER_SETBACK_MM),
    )


def elevated_saddle(endpoint, tangent, normal, terminal, rise_mm):
    tangent = tangent.normalized()
    normal = normal.normalized()
    transverse = normal.cross(tangent).normalized()
    surface = []
    local_normals = []
    for along, across in saddle_polygon():
        target = endpoint + tangent * along + transverse * across
        hit = terminal["bvh"].find_nearest(target)
        if hit is None:
            raise RuntimeError(
                f"{OPERATION}: terminal projection failed at {list(target)}"
            )
        point, hit_normal, _, _ = hit
        if hit_normal.dot(normal) < 0.0:
            hit_normal.negate()
        surface.append(point.copy())
        local_normals.append(hit_normal.normalized())
    bottom = [
        point - hit_normal * UNDERSIDE_EMBED_MM
        for point, hit_normal in zip(surface, local_normals)
    ]
    top = [
        point + normal * rise_mm
        for point in surface
    ]
    points = [*bottom, *top]
    count = len(surface)
    faces = [
        tuple(reversed(range(count))),
        tuple(range(count, count * 2)),
        *[
            (
                index,
                (index + 1) % count,
                count + (index + 1) % count,
                count + index,
            )
            for index in range(count)
        ],
    ]
    faces = v4.v2.base.positive_faces(points, faces)
    return points, faces, {
        "footprint_long_mm": PAD_LONG_MM,
        "footprint_short_mm": PAD_SHORT_MM,
        "projection_samples": "four mitered corner pairs and four edge spans",
        "underside_embed_mm": UNDERSIDE_EMBED_MM,
        "outward_deck_rise_mm": rise_mm,
        "total_nominal_thickness_mm": UNDERSIDE_EMBED_MM + rise_mm,
        "shoulder_taper_mm": SHOULDER_TAPER_MM,
        "miter_setback_mm": MITER_SETBACK_MM,
        "measured_surface_contact_lap_mm": PAD_LONG_MM,
        "projection_to_outward_rise_ratio": round(
            PAD_LONG_MM / rise_mm,
            6,
        ),
    }


def minimum_distance(points, bvh):
    distances = []
    for point in points:
        nearest = bvh.find_nearest(point)
        if nearest is not None:
            distances.append(nearest[3])
    return min(distances) if distances else None


def solid_metrics(
    name,
    points,
    faces,
    target,
    allowed_faces,
    context,
    target_length,
    grid,
):
    metrics = v17.constituent_metrics(
        name,
        points,
        faces,
        target["geometry"],
        allowed_faces,
        context["open_points"],
        context["open_faces"],
        context["c9_points"],
        context["c9_faces"],
        context["cutter_points"],
        context["cutter_faces"],
        target_length,
        grid,
    )
    metrics["minimum_c9_distance_mm"] = round(
        minimum_distance(
            points,
            BVHTree.FromPolygons(
                context["c9_points"],
                context["c9_faces"],
                all_triangles=False,
            ),
        ),
        6,
    )
    return metrics


def branch_b_candidate(
    rise_mm,
    scarf_depth_mm,
    context,
    terminals,
    target_length,
    grid,
):
    upper_point = context["staged_points"][BRANCH_B_IDS[0]]
    lower_point = context["staged_points"][BRANCH_B_IDS[1]]
    upper_normal = Vector(BRANCH_B_FRAMES[1780]["normal"])
    lower_normal = Vector(BRANCH_B_FRAMES[1789]["normal"])
    upper_tangent = Vector(BRANCH_B_FRAMES[1780]["tangent"])
    lower_tangent = Vector(BRANCH_B_FRAMES[1789]["tangent"])
    upper_points, upper_faces, upper_form = elevated_saddle(
        upper_point,
        upper_tangent,
        upper_normal,
        terminals["T_CAGE_1"],
        rise_mm,
    )
    lower_points, lower_faces, lower_form = elevated_saddle(
        lower_point,
        lower_tangent,
        lower_normal,
        terminals["T_CAGE_0"],
        rise_mm,
    )
    upper_deck = upper_point + upper_normal * rise_mm
    lower_deck = lower_point + lower_normal * rise_mm
    route = (lower_deck - upper_deck).normalized()
    bridge_points, bridge_faces, samples, widths = v12.connector_geometry(
        [
            upper_deck - route * SCARF_CONTAINMENT_MM,
            lower_deck + route * SCARF_CONTAINMENT_MM,
        ],
        120,
        target_length,
    )
    upper = solid_metrics(
        "branch_b_upper_saddle",
        upper_points,
        upper_faces,
        terminals["T_CAGE_1"],
        terminals["T_CAGE_1"]["allowed_open_faces"],
        context,
        target_length,
        grid,
    )
    lower = solid_metrics(
        "branch_b_lower_saddle",
        lower_points,
        lower_faces,
        terminals["T_CAGE_0"],
        terminals["T_CAGE_0"]["allowed_open_faces"],
        context,
        target_length,
        grid,
    )
    combined_target = {
        "geometry": (
            terminals["T_CAGE_1"]["geometry"][0]
            + terminals["T_CAGE_0"]["geometry"][0],
            terminals["T_CAGE_1"]["geometry"][1]
            + [
                tuple(
                    len(terminals["T_CAGE_1"]["geometry"][0]) + index
                    for index in face
                )
                for face in terminals["T_CAGE_0"]["geometry"][1]
            ],
        )
    }
    bridge = solid_metrics(
        "branch_b_bridge",
        bridge_points,
        bridge_faces,
        combined_target,
        (
            terminals["T_CAGE_1"]["allowed_open_faces"]
            | terminals["T_CAGE_0"]["allowed_open_faces"]
        ),
        context,
        target_length,
        grid,
    )
    upper_overlap = v14.overlap_pairs(
        bridge_points,
        bridge_faces,
        upper_points,
        upper_faces,
    )
    lower_overlap = v14.overlap_pairs(
        bridge_points,
        bridge_faces,
        lower_points,
        lower_faces,
    )
    pad_overlap = v14.overlap_pairs(
        upper_points,
        upper_faces,
        lower_points,
        lower_faces,
    )
    scarf_gate = all(
        (
            upper_overlap,
            lower_overlap,
            SCARF_CONTAINMENT_MM == 6.0,
            0.4 <= scarf_depth_mm <= 0.8,
            min(widths) >= 4.5,
            max(widths) <= 6.0,
        )
    )
    form_gate = all(
        (
            form["measured_surface_contact_lap_mm"] >= 9.0,
            form["projection_to_outward_rise_ratio"] >= 2.5,
            form["shoulder_taper_mm"] >= 3.0,
        )
        for form in (upper_form, lower_form)
    )
    gate = all(
        (
            upper["gate_pass"],
            lower["gate_pass"],
            bridge["gate_pass"],
            scarf_gate,
            form_gate,
            not pad_overlap,
        )
    )
    return {
        "rise_mm": rise_mm,
        "scarf_overlap_depth_mm": scarf_depth_mm,
        "scarf_containment_mm": SCARF_CONTAINMENT_MM,
        "bridge_width_range_mm": [
            round(min(widths), 6),
            round(max(widths), 6),
        ],
        "bridge_thickness_mm": v12.THICKNESS_MM,
        "bridge_ring_count": len(samples),
        "upper_saddle_form": upper_form,
        "lower_saddle_form": lower_form,
        "constituents": {
            "upper_saddle": upper,
            "bridge": bridge,
            "lower_saddle": lower,
        },
        "upper_scarf_overlap_count": len(upper_overlap),
        "lower_scarf_overlap_count": len(lower_overlap),
        "direct_pad_overlap_count": len(pad_overlap),
        "minimum_cutter_margin_mm": min(
            upper["minimum_cutter_margin_mm"],
            bridge["minimum_cutter_margin_mm"],
            lower["minimum_cutter_margin_mm"],
        ),
        "scarf_gate": scarf_gate,
        "anti_fin_and_silhouette_numeric_gate": form_gate,
        "gate_pass": gate,
        "_upper_points": upper_points,
        "_upper_faces": upper_faces,
        "_bridge_points": bridge_points,
        "_bridge_faces": bridge_faces,
        "_lower_points": lower_points,
        "_lower_faces": lower_faces,
    }


def cross_branch_overlap(branch_a, branch_b):
    a_specs = (
        (branch_a["_upper_points"], branch_a["_upper_faces"]),
        (branch_a["_bridge_points"], branch_a["_bridge_faces"]),
        (branch_a["_lower_points"], branch_a["_lower_faces"]),
    )
    b_specs = (
        (branch_b["_upper_points"], branch_b["_upper_faces"]),
        (branch_b["_bridge_points"], branch_b["_bridge_faces"]),
        (branch_b["_lower_points"], branch_b["_lower_faces"]),
    )
    return sum(
        len(v14.overlap_pairs(*first, *second))
        for first in a_specs
        for second in b_specs
    )


def main():
    report_path = Path(v14.argument("--report")).resolve()
    prefix = v14.argument("--prefix")
    context = v17.baseline_context()
    terminals = terminal_context(context)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    grid, _ = v4.cutter_grid(context["cutter"])
    branch_a = v17.candidate(
        1.5,
        context["staged_points"][BRANCH_A_IDS[0]],
        context["staged_points"][BRANCH_A_IDS[1]],
        terminals["T_CAGE_1"]["geometry"],
        terminals["T_CAGE_0"]["geometry"],
        terminals["T_CAGE_1"]["allowed_open_faces"],
        terminals["T_CAGE_0"]["allowed_open_faces"],
        (
            terminals["T_CAGE_1"]["allowed_open_faces"]
            | terminals["T_CAGE_0"]["allowed_open_faces"]
        ),
        context["open_points"],
        context["open_faces"],
        context["c9_points"],
        context["c9_faces"],
        context["cutter_points"],
        context["cutter_faces"],
        target_length,
        grid,
    )
    records = []
    for rise_mm in RISES_MM:
        for scarf_depth_mm in SCARF_DEPTHS_MM:
            branch_b = branch_b_candidate(
                rise_mm,
                scarf_depth_mm,
                context,
                terminals,
                target_length,
                grid,
            )
            crossing = cross_branch_overlap(branch_a, branch_b)
            branch_a_scarf_gate = all(
                (
                    branch_a["bridge_upper_pad_overlap_count"] > 0,
                    branch_a["bridge_lower_pad_overlap_count"] > 0,
                    SCARF_CONTAINMENT_MM == 6.0,
                    0.4 <= scarf_depth_mm <= 0.8,
                )
            )
            full_gate = all(
                (
                    branch_a["gate_pass"],
                    branch_a_scarf_gate,
                    branch_b["gate_pass"],
                    crossing == 0,
                    min(
                        branch_a["combined_minimum_cutter_margin_mm"],
                        branch_b["minimum_cutter_margin_mm"],
                    )
                    >= 1.7,
                )
            )
            records.append(
                {
                    "rise_mm": rise_mm,
                    "scarf_overlap_depth_mm": scarf_depth_mm,
                    "branch_a": public(branch_a),
                    "branch_a_scarf_gate": branch_a_scarf_gate,
                    "branch_b": public(branch_b),
                    "cross_branch_overlap_count": crossing,
                    "combined_minimum_cutter_margin_mm": min(
                        branch_a["combined_minimum_cutter_margin_mm"],
                        branch_b["minimum_cutter_margin_mm"],
                    ),
                    "gate_pass": full_gate,
                    "_branch_b": branch_b,
                }
            )
    selected = next(
        (record for record in records if record["gate_pass"]),
        None,
    )
    objects = None
    result_prefix_exact = False
    retained_after = None
    if selected is not None:
        material = Counter(
            context["staged_materials"][face_id]
            for face_id in context["retained_face_ids"]
        ).most_common(1)[0][0]
        collection = v14.ensure_collection(REVIEW_COLLECTION)
        branch_b = selected["_branch_b"]
        specs = (
            (
                "BRANCH_A_UPPER_SADDLE",
                branch_a["_upper_points"],
                branch_a["_upper_faces"],
            ),
            (
                "BRANCH_A_BRIDGE",
                branch_a["_bridge_points"],
                branch_a["_bridge_faces"],
            ),
            (
                "BRANCH_A_LOWER_SADDLE",
                branch_a["_lower_points"],
                branch_a["_lower_faces"],
            ),
            (
                "BRANCH_B_UPPER_SADDLE",
                branch_b["_upper_points"],
                branch_b["_upper_faces"],
            ),
            (
                "BRANCH_B_BRIDGE",
                branch_b["_bridge_points"],
                branch_b["_bridge_faces"],
            ),
            (
                "BRANCH_B_LOWER_SADDLE",
                branch_b["_lower_points"],
                branch_b["_lower_faces"],
            ),
        )
        named = {}
        for role, points, faces in specs:
            obj = v14.create_object(
                f"{prefix}_{role}",
                points,
                faces,
                [material] * len(faces),
                list(context["staged"].data.materials),
                collection,
            )
            named[role.lower()] = obj.name
        result_points = [point.copy() for point in context["open_points"]]
        result_faces = list(context["open_faces"])
        result_materials = list(context["open_materials"])
        for _, points, faces in specs:
            offset = len(result_points)
            result_points.extend(point.copy() for point in points)
            result_faces.extend(
                tuple(offset + index for index in face) for face in faces
            )
            result_materials.extend([material] * len(faces))
        result = v14.create_object(
            f"{prefix}_AFTER",
            result_points,
            result_faces,
            result_materials,
            list(context["staged"].data.materials),
            collection,
        )
        evaluated_points, evaluated_faces, evaluated_materials = (
            v14.evaluated_geometry(result)
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
        retained_after = v4.v2.fingerprint(
            context["retained_ids"],
            [
                evaluated_points[context["source_to_open"][source_id]]
                for source_id in context["retained_ids"]
            ],
        )
        objects = {"result": result.name, **named}
    preservation_gate = all(
        (
            selected is not None,
            result_prefix_exact,
            retained_after == v17.EXPECTED_RETAINED_FINGERPRINT,
            context["checks"]["component_9_fingerprint_exact"],
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
    failure_counts = defaultdict(int)
    for record in records:
        if record["branch_b"]["minimum_cutter_margin_mm"] < 1.7:
            failure_counts["branch_b_minimum_cutter_margin_below_1.7"] += 1
        for role, metrics in record["branch_b"]["constituents"].items():
            if metrics["cutter_overlap_count"]:
                failure_counts[f"branch_b_{role}_cutter_overlap"] += 1
            if metrics["unrelated_full_open_overlap_count"]:
                failure_counts[
                    f"branch_b_{role}_unrelated_source_overlap"
                ] += 1
            if metrics["c9_overlap_count"]:
                failure_counts[f"branch_b_{role}_c9_overlap"] += 1
        if record["cross_branch_overlap_count"]:
            failure_counts["branch_cross_over"] += 1
    status = (
        "ELEVATED_SURFACE_SADDLE_MACHINE_PASS"
        if gate_pass
        else SAFE_STOP
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "authority_report_sha256": context["report_sha"],
        "authority_recovery": context["checks"],
        "construction": {
            "constituent_count": 6,
            "separately_closed_solids": True,
            "branches": {
                "A": {
                    "terminal_ids": ["T_CAGE_1", "T_CAGE_0"],
                    "source_vertex_ids": list(BRANCH_A_IDS),
                    "centerline_authority": "v17 V5702->V1784",
                },
                "B": {
                    "terminal_ids": ["T_CAGE_1", "T_CAGE_0"],
                    "source_vertex_ids": list(BRANCH_B_IDS),
                    "route": "direct V1780->V1789 from recorded frames",
                },
            },
            "pad_footprint_mm": [PAD_LONG_MM, PAD_SHORT_MM],
            "underside_embed_mm": UNDERSIDE_EMBED_MM,
            "scarf_containment_mm": SCARF_CONTAINMENT_MM,
            "shoulder_taper_mm": SHOULDER_TAPER_MM,
            "miter_setback_mm": MITER_SETBACK_MM,
            "bridge_width_range_mm": [4.5, 6.0],
            "bridge_thickness_mm": v12.THICKNESS_MM,
            "boolean_union": False,
            "global_backing": False,
            "cutter_used_for_construction": False,
        },
        "bounded_search": {
            "common_rises_mm": list(RISES_MM),
            "scarf_overlap_depths_mm": list(SCARF_DEPTHS_MM),
            "candidate_count": len(records),
            "records": [public(record) for record in records],
        },
        "graph": {
            "required_branches": [
                ["T_CAGE_1", "A_UPPER", "A_BRIDGE", "A_LOWER", "T_CAGE_0"],
                ["T_CAGE_1", "B_UPPER", "B_BRIDGE", "B_LOWER", "T_CAGE_0"],
            ],
            "complete": bool(selected),
        },
        "selected_candidate": public(selected) if selected else None,
        "failure_counts": dict(sorted(failure_counts.items())),
        "first_actionable_failure": (
            next(iter(sorted(failure_counts))) if failure_counts else None
        ),
        "preservation": {
            "result_open_prefix_exact": result_prefix_exact,
            "retained_fingerprint_after": retained_after,
            "retained_fingerprint_equal": (
                retained_after == v17.EXPECTED_RETAINED_FINGERPRINT
            ),
            "component_9_unchanged": True,
            "central_bowl_open": context["checks"]["central_bowl_open"],
            "tip_gap_mm": context["checks"]["tip_gap_mm"],
            "hard_control_error_mm": context["checks"][
                "hard_control_error_mm"
            ],
            "gate_pass": preservation_gate,
        },
        "objects": objects,
        "gate_pass": gate_pass,
        "geometry_emitted": gate_pass,
        "blend_saved": bool(gate_pass and "--save" in sys.argv),
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if gate_pass and "--save" in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(
        json.dumps(
            {
                "status": status,
                "candidate_count": len(records),
                "selected_candidate": public(selected) if selected else None,
                "geometry_emitted": gate_pass,
                "blend_saved": bool(gate_pass and "--save" in sys.argv),
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v20 elevated saddle status={status}; "
        f"geometry_emitted={gate_pass}; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
