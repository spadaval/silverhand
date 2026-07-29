"""Build or safely stop the bounded Repair 014 full authored frame v21."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from math import acos, ceil, degrees
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_broad_constituent_network_v9 as v9  # noqa: E402
import build_connection_aware_network_v12 as v12  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import preflight_b2_sharp_turn_split_v11 as v11  # noqa: E402
import preflight_direction_field_network_v10 as v10  # noqa: E402


OPERATION = "FULL_AUTHORED_FRAME_V21"
SAFE_STOP = "NO_SAFE_FULL_AUTHORED_FRAME_V21"
ALLOWLIST = (5753, 5772, 2741, 4711)
UPPER_ALLOWLIST = (5753, 5772)
LOWER_ALLOWLIST = (2741, 4711)
UPPER_ID = 3895
LOWER_ID = 1894
UPPER_TANGENT = Vector((-0.28337011, -0.28198797, 0.91661561))
LOWER_TANGENT = Vector((-0.45164543, 0.83641762, -0.31051886))
UPPER_NORMAL = Vector((0.35936415, 0.85492766, 0.37410706))
LOWER_NORMAL = Vector((0.68514335, 0.54807854, 0.47977969))
HANDLE_LENGTHS_MM = (8.0, 16.0, 24.0)
MIDPOINT_VARIANTS_MM = (0.0, 8.0, -8.0, 16.0, -16.0)
MAX_SAMPLE_SPACING_MM = 4.0
V12_SPECS = {
    "B0": (210, 8.0, 90),
    "B1": (210, 8.0, 75),
    "B2a": (240, 7.0, 0),
    "B2b": (150, 4.5, 0),
}
V12_EXPECTED_MARGIN = {
    "B0": 2.652826,
    "B1": 7.059058,
    "B2a": 2.088698,
    "B2b": 2.339150,
}


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def stable_hash(value):
    encoded = json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def point_record(point):
    return [float(value) for value in point]


def authority_and_mask(context):
    staged_points = context["staged_points"]
    staged_faces = context["staged_faces"]
    staged_materials = context["staged_materials"]
    retained_faces = set(context["retained_face_ids"])
    missing = sorted(set(ALLOWLIST) - retained_faces)
    if missing:
        raise RuntimeError(
            f"{OPERATION}: allowlisted source faces are not retained: {missing}"
        )
    v13_path = (
        SCRIPT_DIR.parent.parent
        / "_validation/experiments/geometry_repair/component_20_methods"
        / "repair_014_distinct_cage_terminals_v13/build_report.json"
    )
    v13_report = json.loads(v13_path.read_text(encoding="utf-8"))
    terminals = {
        terminal["terminal_id"]: set(terminal["source_vertex_ids"])
        for terminal in v13_report["terminals"]
    }
    membership = {
        "V3895_in_T_CAGE_1": UPPER_ID in terminals["T_CAGE_1"],
        "V1894_in_T_CAGE_0": LOWER_ID in terminals["T_CAGE_0"],
    }
    allowlist_records = [
        {
            "source_face_id": face_id,
            "loop": list(staged_faces[face_id]),
            "coordinates_mm": [
                point_record(staged_points[vertex])
                for vertex in staged_faces[face_id]
            ],
            "material_index": staged_materials[face_id],
        }
        for face_id in ALLOWLIST
    ]
    boundary_counts = Counter()
    for face_id in ALLOWLIST:
        face = staged_faces[face_id]
        for first, second in zip(face, (*face[1:], face[0])):
            boundary_counts[tuple(sorted((first, second)))] += 1
    boundary_edges = sorted(
        edge for edge, count in boundary_counts.items() if count == 1
    )
    complement_face_ids = sorted(retained_faces - set(ALLOWLIST))
    complement_vertex_ids = sorted(
        {
            vertex
            for face_id in complement_face_ids
            for vertex in staged_faces[face_id]
        }
    )
    complement = {
        "vertex_ids": complement_vertex_ids,
        "coordinates_mm": [
            point_record(staged_points[vertex])
            for vertex in complement_vertex_ids
        ],
        "face_ids": complement_face_ids,
        "faces": [
            list(staged_faces[face_id]) for face_id in complement_face_ids
        ],
        "materials": [
            staged_materials[face_id] for face_id in complement_face_ids
        ],
    }
    branch_a = {
        "source_vertex_ids": [5702, 1784],
        "coordinates_mm": [
            point_record(context["staged_points"][source_id])
            for source_id in (5702, 1784)
        ],
    }
    checkpoint = {
        "authority_blend_sha256": context["blend_sha"],
        "authority_report_sha256": context["report_sha"],
        "baseline_checks": context["checks"],
        "allowlist_source_face_ids": list(ALLOWLIST),
        "allowlist_records": allowlist_records,
        "allowlist_fingerprint": stable_hash(allowlist_records),
        "allowlist_boundary_edges": [list(edge) for edge in boundary_edges],
        "immutable_complement_face_count": len(complement_face_ids),
        "immutable_complement_vertex_count": len(complement_vertex_ids),
        "immutable_complement_fingerprint": stable_hash(complement),
        "terminal_membership": membership,
        "branch_a": branch_a,
        "tip_gap_mm": context["checks"]["tip_gap_mm"],
        "hard_control_error_mm": context["checks"][
            "hard_control_error_mm"
        ],
    }
    checkpoint["gate_pass"] = all(
        (
            context["checks"]["retained_fingerprint_exact"],
            context["checks"]["component_9_fingerprint_exact"],
            context["checks"]["open_lineage_and_materials_exact"],
            context["checks"]["tip_gap_exact"],
            all(membership.values()),
            all(
                value <= 1.0e-4
                for value in checkpoint["hard_control_error_mm"].values()
            ),
        )
    )
    if not checkpoint["gate_pass"]:
        raise RuntimeError(
            f"{OPERATION}: authority/mask gate failed: {checkpoint}"
        )
    return checkpoint


def reconstruct_v12_core(context):
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    grid, _ = v4.cutter_grid(context["cutter"])
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    route = [
        context["staged_points"][source_id] for source_id in centerline_ids
    ]
    route_samples, node_ring, _ = v4.obstacle_following_sample_route(
        route,
        target_length,
        grid,
        extend_ends=False,
    )
    ranges = {
        "B0": [node_ring[0], node_ring[6] + 2],
        "B1": [node_ring[6] - 2, node_ring[7] + 2],
        "B2a": [node_ring[7] - 2, node_ring[11] + 2],
        "B2b": [node_ring[11] - 2, node_ring[12]],
    }
    v9.GLOBAL_ROUTE.clear()
    v9.GLOBAL_ROUTE.update({"target_length_mm": target_length})
    original_geometry = v9.candidate_geometry
    v9.candidate_geometry = v10.directed_candidate_geometry
    core = {}
    try:
        for name in ("B0", "B1", "B2a", "B2b"):
            first, last = ranges[name]
            direction, offset, roll = V12_SPECS[name]
            core[name] = v11.evaluate(
                name,
                route_samples[first : last + 1],
                direction,
                offset,
                roll,
                target_length,
                grid,
                context["c9_points"],
                context["c9_faces"],
                context["cutter_points"],
                context["cutter_faces"],
            )
    finally:
        v9.candidate_geometry = original_geometry
    turn = v12.connector_candidate(
        core["B2a"],
        core["B2b"],
        0.0,
        0,
        60,
        target_length,
        grid,
        context["c9_points"],
        context["c9_faces"],
        context["cutter_points"],
        context["cutter_faces"],
    )
    exact = all(
        (
            core[name]["gate_pass"],
            abs(
                core[name]["minimum_cutter_margin_mm"]
                - V12_EXPECTED_MARGIN[name]
            )
            <= 1.0e-6,
            core[name]["direction_degrees"] == V12_SPECS[name][0],
            core[name]["offset_mm"] == V12_SPECS[name][1],
            core[name]["roll_degrees"] == V12_SPECS[name][2],
        )
        for name in core
    ) and all(
        (
            turn is not None,
            turn["gate_pass"],
            abs(turn["gap_mm"] - 9.879956) <= 1.0e-6,
            turn["roll_degrees"] == 60,
            turn["end_embed_mm"] == 1.5,
            abs(turn["minimum_cutter_margin_mm"] - 4.617902) <= 1.0e-6,
        )
    )
    if not exact:
        observed = {
            "constituents": {
                name: public(record) for name, record in core.items()
            },
            "turn": public(turn) if turn is not None else None,
        }
        raise RuntimeError(
            f"{OPERATION}: exact v12 corridor recovery failed: {observed}"
        )
    return {
        "core": core,
        "turn": turn,
        "target_length": target_length,
        "grid": grid,
        "public": {
            "constituents": {
                name: public(record) for name, record in core.items()
            },
            "turn_bridge": public(turn),
            "gate_pass": exact,
        },
    }


def hermite_point(first, second, first_derivative, second_derivative, t):
    t2 = t * t
    t3 = t2 * t
    return (
        first * (2.0 * t3 - 3.0 * t2 + 1.0)
        + first_derivative * (t3 - 2.0 * t2 + t)
        + second * (-2.0 * t3 + 3.0 * t2)
        + second_derivative * (t3 - t2)
    )


def approach_samples(
    first,
    second,
    first_tangent,
    second_tangent,
    handle_mm,
    midpoint_displacement,
    bisector,
):
    estimate = (
        (second - first).length
        + 2.0 * handle_mm
        + abs(midpoint_displacement) * 2.0
    )
    steps = max(8, int(ceil(estimate / MAX_SAMPLE_SPACING_MM)))
    samples = []
    for index in range(steps + 1):
        t = index / steps
        point = hermite_point(
            first,
            second,
            first_tangent * handle_mm,
            second_tangent * handle_mm,
            t,
        )
        if midpoint_displacement:
            point += (
                bisector
                * midpoint_displacement
                * (4.0 * t * (1.0 - t))
            )
        samples.append(point)
    return samples


def sweep_geometry(samples, target_length):
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(samples, tangents, target_length)
    points = []
    for point, (_, thickness) in zip(samples, frames):
        _, _, _, radial = v4.radial_coordinates(point, target_length)
        outward = radial - tangents[len(points) // 5] * radial.dot(
            tangents[len(points) // 5]
        )
        if outward.length <= 1.0e-8:
            outward = thickness.copy()
        outward.normalize()
        width = outward.cross(tangents[len(points) // 5]).normalized()
        points.extend(v8.ring_points(point, width, outward))
    faces = v4.v2.base.positive_faces(
        points,
        v8.closed_faces(len(samples)),
    )
    return points, faces


def curve_metrics(samples):
    lengths = [
        (second - first).length
        for first, second in zip(samples, samples[1:])
    ]
    tangents = [
        (second - first).normalized()
        for first, second in zip(samples, samples[1:])
    ]
    turns = [
        degrees(
            acos(
                max(-1.0, min(1.0, first.dot(second)))
            )
        )
        for first, second in zip(tangents, tangents[1:])
    ]
    binormals = []
    for first, second in zip(tangents, tangents[1:]):
        cross = first.cross(second)
        if cross.length > 1.0e-8:
            binormals.append(cross.normalized())
    inflections = sum(
        first.dot(second) < 0.0
        for first, second in zip(binormals, binormals[1:])
    )
    return {
        "curve_length_mm": round(sum(lengths), 6),
        "maximum_sample_spacing_mm": round(max(lengths), 6),
        "maximum_sample_turn_degrees": round(max(turns or [0.0]), 6),
        "estimated_inflection_count": inflections,
    }


def approach_record(
    name,
    first,
    second,
    first_tangent,
    second_tangent,
    first_normal,
    second_normal,
    handle_mm,
    midpoint_displacement,
    allowed_open_faces,
    context,
    target_length,
    grid,
):
    bisector = first_normal.normalized() + second_normal.normalized()
    if bisector.length <= 1.0e-8:
        bisector = first_normal.copy()
    bisector.normalize()
    samples = approach_samples(
        first,
        second,
        first_tangent,
        second_tangent,
        handle_mm,
        midpoint_displacement,
        bisector,
    )
    points, faces = sweep_geometry(samples, target_length)
    c9 = v14.overlap_pairs(
        points,
        faces,
        context["c9_points"],
        context["c9_faces"],
    )
    cutter = v14.overlap_pairs(
        points,
        faces,
        context["cutter_points"],
        context["cutter_faces"],
    )
    source = v14.overlap_pairs(
        points,
        faces,
        context["open_points"],
        context["open_faces"],
    )
    unrelated = [
        pair for pair in source if pair[1] not in allowed_open_faces
    ]
    self_pairs = v4.v2.ribbon_self_overlaps(
        points,
        faces,
        len(samples),
    )
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    curve = curve_metrics(samples)
    gate = all(
        (
            not c9,
            not cutter,
            not unrelated,
            not self_pairs,
            min(margins) >= 1.7,
            curve["maximum_sample_spacing_mm"] <= 4.0,
            curve["maximum_sample_turn_degrees"] <= 60.0,
            curve["estimated_inflection_count"] <= 1,
        )
    )
    return {
        "name": name,
        "handle_length_mm": handle_mm,
        "midpoint_displacement_mm": midpoint_displacement,
        "sample_count": len(samples),
        **curve,
        "c9_overlap_count": len(c9),
        "cutter_overlap_count": len(cutter),
        "named_landing_overlap_count": len(source) - len(unrelated),
        "unrelated_source_overlap_count": len(unrelated),
        "self_overlap_count": len(self_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "audit": audit,
        "triangle_quality": quality,
        "gate_pass": gate,
        "_points": points,
        "_faces": faces,
        "_samples": samples,
    }


def source_to_open_faces(context):
    removed = set(
        context["mapping"]["reconstruction_scope"]["rebuild_face_ids"]
    )
    return {
        source_face_id: open_face_id
        for open_face_id, source_face_id in enumerate(
            face_id
            for face_id in range(len(context["staged_faces"]))
            if face_id not in removed
        )
    }


def search_approach(
    name,
    first,
    second,
    first_tangent,
    second_tangent,
    first_normal,
    second_normal,
    allowed_open_faces,
    context,
    corridor,
):
    records = []
    for handle_mm in HANDLE_LENGTHS_MM:
        for midpoint_displacement in MIDPOINT_VARIANTS_MM:
            records.append(
                approach_record(
                    name,
                    first,
                    second,
                    first_tangent,
                    second_tangent,
                    first_normal,
                    second_normal,
                    handle_mm,
                    midpoint_displacement,
                    allowed_open_faces,
                    context,
                    corridor["target_length"],
                    corridor["grid"],
                )
            )
    passing = [record for record in records if record["gate_pass"]]
    selected = (
        min(
            passing,
            key=lambda record: (
                record["curve_length_mm"],
                -record["minimum_cutter_margin_mm"],
                record["handle_length_mm"],
                abs(record["midpoint_displacement_mm"]),
                record["midpoint_displacement_mm"],
            ),
        )
        if passing
        else None
    )
    return records, selected


def failure_summary(records):
    return {
        "variant_count": len(records),
        "passing_count": sum(record["gate_pass"] for record in records),
        "variants_with_c9_overlap": sum(
            record["c9_overlap_count"] > 0 for record in records
        ),
        "minimum_c9_overlap_count": min(
            record["c9_overlap_count"] for record in records
        ),
        "variants_with_cutter_overlap": sum(
            record["cutter_overlap_count"] > 0 for record in records
        ),
        "variants_with_unrelated_source_overlap": sum(
            record["unrelated_source_overlap_count"] > 0
            for record in records
        ),
        "minimum_unrelated_source_overlap_count": min(
            record["unrelated_source_overlap_count"] for record in records
        ),
        "variants_with_self_overlap": sum(
            record["self_overlap_count"] > 0 for record in records
        ),
        "minimum_cutter_margin_range_mm": [
            min(record["minimum_cutter_margin_mm"] for record in records),
            max(record["minimum_cutter_margin_mm"] for record in records),
        ],
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    context = v17.baseline_context()
    checkpoint = authority_and_mask(context)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    authority_path = report_path.with_name("authority_mask_checkpoint.json")
    authority_path.write_text(
        json.dumps(
            {
                "operation": OPERATION,
                "status": "AUTHORITY_AND_MASK_CHECKPOINT_PASS",
                **checkpoint,
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    corridor = reconstruct_v12_core(context)
    open_face_by_source = source_to_open_faces(context)
    upper_allowed = {
        open_face_by_source[source_face_id]
        for source_face_id in UPPER_ALLOWLIST
    }
    lower_allowed = {
        open_face_by_source[source_face_id]
        for source_face_id in LOWER_ALLOWLIST
    }
    b0_samples = corridor["core"]["B0"]["_samples"]
    b2b_samples = corridor["core"]["B2b"]["_samples"]
    upper_first = context["staged_points"][UPPER_ID]
    upper_second = b0_samples[0]
    upper_tangent = UPPER_TANGENT.normalized()
    if upper_tangent.dot(upper_second - upper_first) < 0.0:
        upper_tangent.negate()
    upper_band_tangent = (b0_samples[1] - b0_samples[0]).normalized()
    _, _, _, upper_band_normal = v4.radial_coordinates(
        upper_second,
        corridor["target_length"],
    )
    lower_first = b2b_samples[-1]
    lower_second = context["staged_points"][LOWER_ID]
    lower_band_tangent = (b2b_samples[-1] - b2b_samples[-2]).normalized()
    lower_tangent = LOWER_TANGENT.normalized()
    if lower_tangent.dot(lower_second - lower_first) < 0.0:
        lower_tangent.negate()
    _, _, _, lower_band_normal = v4.radial_coordinates(
        lower_first,
        corridor["target_length"],
    )
    upper_records, upper_selected = search_approach(
        "UPPER_APPROACH_V21",
        upper_first,
        upper_second,
        upper_tangent,
        upper_band_tangent,
        UPPER_NORMAL,
        upper_band_normal,
        upper_allowed,
        context,
        corridor,
    )
    progress_path = report_path.with_name("approach_search_checkpoint.json")
    progress_path.write_text(
        json.dumps(
            {
                "operation": OPERATION,
                "status": "UPPER_APPROACH_SEARCH_COMPLETE",
                "upper_records": [public(record) for record in upper_records],
                "upper_selected": (
                    public(upper_selected) if upper_selected else None
                ),
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lower_records, lower_selected = search_approach(
        "LOWER_APPROACH_V21",
        lower_first,
        lower_second,
        lower_band_tangent,
        lower_tangent,
        lower_band_normal,
        LOWER_NORMAL,
        lower_allowed,
        context,
        corridor,
    )
    progress_path.write_text(
        json.dumps(
            {
                "operation": OPERATION,
                "status": "BOTH_APPROACH_SEARCHES_COMPLETE",
                "upper_records": [public(record) for record in upper_records],
                "upper_selected": (
                    public(upper_selected) if upper_selected else None
                ),
                "lower_records": [public(record) for record in lower_records],
                "lower_selected": (
                    public(lower_selected) if lower_selected else None
                ),
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    blockers = []
    upper_failure = failure_summary(upper_records)
    lower_failure = failure_summary(lower_records)
    if upper_selected is None:
        blockers.append(
            {
                "operation": "bounded_upper_approach_search",
                "target": "V3895->B0 first ring",
                "reason": (
                    "all 15 Hermite 6x2.4 envelopes overlap non-allowlisted "
                    "source faces; 6 also overlap the cutter"
                ),
                "measurements": upper_failure,
            }
        )
    if lower_selected is None:
        blockers.append(
            {
                "operation": "bounded_lower_approach_search",
                "target": "B2b final ring->V1894",
                "reason": (
                    "all 15 Hermite 6x2.4 envelopes overlap unchanged C9 and "
                    "non-allowlisted source faces; 6 also overlap the cutter"
                ),
                "measurements": lower_failure,
            }
        )
    if not blockers:
        blockers.append(
            {
                "operation": "evaluation_copy_topology_replacement",
                "target": list(ALLOWLIST),
                "reason": (
                    "approaches passed but topology/full-frame implementation "
                    "is not yet emitted without a complete downstream gate"
                ),
            }
        )
    status = SAFE_STOP
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "authority_and_mask_checkpoint": checkpoint,
        "v12_corridor_recovery": corridor["public"],
        "approach_search": {
            "variant_contract": {
                "handle_lengths_mm": list(HANDLE_LENGTHS_MM),
                "midpoint_displacements_mm": list(MIDPOINT_VARIANTS_MM),
                "variants_per_approach": 15,
                "section_mm": [6.0, 2.4],
                "maximum_sample_spacing_mm": MAX_SAMPLE_SPACING_MM,
                "maximum_inflections": 1,
                "maximum_sample_turn_degrees": 60.0,
            },
            "upper": {
                "start": "V3895",
                "end": "B0 first ring corresponding to V2074",
                "records": [public(record) for record in upper_records],
                "selected": (
                    public(upper_selected) if upper_selected else None
                ),
                "failure_summary": upper_failure,
            },
            "lower": {
                "start": "B2b final ring corresponding to V2119",
                "end": "V1894",
                "records": [public(record) for record in lower_records],
                "selected": (
                    public(lower_selected) if lower_selected else None
                ),
                "failure_summary": lower_failure,
            },
        },
        "blockers": blockers,
        "topology_replacement": {
            "authorized_face_ids": list(ALLOWLIST),
            "mutation_started": False,
            "reason": "stopped at pre-mutation approach gate",
        },
        "gate_pass": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "upper_passing_count": sum(
                    record["gate_pass"] for record in upper_records
                ),
                "lower_passing_count": sum(
                    record["gate_pass"] for record in lower_records
                ),
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v21 full authored frame status={status}; "
        "mutation_started=False; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
