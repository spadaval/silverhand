"""Search local bridges between admissible Repair 014 broad constituents."""

from __future__ import annotations

from itertools import product
import json
from math import ceil, cos, radians, sin
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_broad_constituent_network_v9 as v9  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import preflight_b2_sharp_turn_split_v11 as v11  # noqa: E402
import preflight_direction_field_network_v10 as v10  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "CONNECTION_AWARE_NETWORK_V12"
MAXIMUM_BROAD_COMBINATIONS = 24
CONNECTOR_ROLLS = list(range(0, 360, 30))
MIDPOINT_OFFSETS_MM = (2.0, 4.0)
MIDPOINT_ANGLES_DEGREES = list(range(0, 360, 45))
END_EMBED_MM = 1.5
CONNECTOR_INTERIOR_WIDTH_MM = 4.5
CONNECTOR_END_WIDTH_MM = 6.0
THICKNESS_MM = 2.4


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def endpoint_pair(first, second):
    first_points = first["_points"][-5:]
    second_points = second["_points"][:5]
    return min(
        (
            ((a - b).length, a.copy(), b.copy())
            for a in first_points
            for b in second_points
        ),
        key=lambda item: item[0],
    )


def sampled_path(nodes):
    result = [nodes[0].copy()]
    for first, second in zip(nodes, nodes[1:]):
        steps = max(1, int(ceil((second - first).length / 1.5)))
        result.extend(
            first.lerp(second, step / steps)
            for step in range(1, steps + 1)
        )
    return result


def connector_geometry(nodes, roll_degrees, target_length):
    samples = sampled_path(nodes)
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(samples, tangents, target_length)
    points = []
    widths = []
    for ring, (point, tangent, frame) in enumerate(
        zip(samples, tangents, frames)
    ):
        width_axis, thickness_axis = v8.rotated_frame(
            frame[0],
            tangent,
            roll_degrees,
        )
        distance_to_end = min(ring, len(samples) - 1 - ring)
        width = (
            CONNECTOR_END_WIDTH_MM
            if distance_to_end == 0
            else 5.25
            if distance_to_end == 1
            else CONNECTOR_INTERIOR_WIDTH_MM
        )
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
    faces = v4.v2.base.positive_faces(
        points,
        v8.closed_faces(len(samples)),
    )
    return points, faces, samples, widths


def connector_candidate(
    first,
    second,
    midpoint_offset,
    midpoint_angle,
    roll,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    gap, start_surface, end_surface = endpoint_pair(first, second)
    direction = end_surface - start_surface
    if direction.length <= 1.0e-8:
        return None
    direction.normalize()
    start = start_surface - direction * END_EMBED_MM
    end = end_surface + direction * END_EMBED_MM
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
        nodes = [start, midpoint + offset_direction * midpoint_offset, end]
    points, faces, samples, widths = connector_geometry(
        nodes,
        roll,
        target_length,
    )
    c9 = overlap_pairs(points, faces, c9_points, c9_faces)
    cutter = overlap_pairs(
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
    first_contact = overlap_pairs(
        points,
        faces,
        first["_points"],
        first["_faces"],
    )
    second_contact = overlap_pairs(
        points,
        faces,
        second["_points"],
        second["_faces"],
    )
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    passed = all(
        (
            not c9,
            not cutter,
            not self_pairs,
            first_contact,
            second_contact,
            min(margins) >= 1.6998,
            audit["connected_components"] == 1,
            audit["boundary_edges"] == 0,
            audit["nonmanifold_edges"] == 0,
            audit["noncontiguous_manifold_edges"] == 0,
            audit["signed_volume_mm3"] > 0.0,
            quality["degenerate_triangle_count"] == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
            min(widths) >= CONNECTOR_INTERIOR_WIDTH_MM - 1.0e-4,
        )
    )
    return {
        "gap_mm": round(gap, 6),
        "midpoint_offset_mm": midpoint_offset,
        "midpoint_angle_degrees": midpoint_angle,
        "roll_degrees": roll,
        "ring_count": len(samples),
        "minimum_width_mm": min(widths),
        "maximum_width_mm": max(widths),
        "thickness_mm": THICKNESS_MM,
        "end_embed_mm": END_EMBED_MM,
        "first_overlap_count": len(first_contact),
        "second_overlap_count": len(second_contact),
        "c9_overlap_count": len(c9),
        "cutter_overlap_count": len(cutter),
        "self_overlap_count": len(self_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "audit": audit,
        "triangle_quality": quality,
        "gate_pass": passed,
        "_points": points,
        "_faces": faces,
        "_samples": samples,
    }


def find_connector(
    first,
    second,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    attempts = []
    paths = [(0.0, 0)]
    paths.extend(
        (offset, angle)
        for offset in MIDPOINT_OFFSETS_MM
        for angle in MIDPOINT_ANGLES_DEGREES
    )
    for midpoint_offset, midpoint_angle in paths:
        passing = []
        for roll in CONNECTOR_ROLLS:
            record = connector_candidate(
                first,
                second,
                midpoint_offset,
                midpoint_angle,
                roll,
                target_length,
                grid,
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
            return min(
                passing,
                key=lambda record: (
                    record["midpoint_offset_mm"],
                    record["midpoint_angle_degrees"],
                    record["roll_degrees"],
                ),
            ), attempts
    best = min(
        attempts,
        key=lambda record: (
            record["c9_overlap_count"],
            record["cutter_overlap_count"],
            record["self_overlap_count"],
            not record["first_overlap_count"],
            not record["second_overlap_count"],
            max(0.0, 1.7 - record["minimum_cutter_margin_mm"]),
            max(
                0.0,
                3.0
                - record["triangle_quality"]["minimum_angle_degrees"][
                    "minimum"
                ],
            ),
        ),
    )
    return None, [best]


def main() -> int:
    report_path = report_argument()
    blend_path = Path(bpy.data.filepath).resolve()
    input_sha = v10.sha256_file(blend_path)
    if input_sha != v4.v2.EXPECTED_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: input Blend '{blend_path}' has SHA-256 "
            f"'{input_sha}', expected clean open-cage "
            f"'{v4.v2.EXPECTED_BLEND_SHA256}'"
        )
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    staged_points, _, _ = evaluated_geometry(
        bpy.data.objects[v4.v2.base.STAGED_NAME]
    )
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    route = [staged_points[index] for index in centerline_ids]
    cutter = bpy.data.objects[v4.CUTTER_NAME]
    grid, _ = v4.cutter_grid(cutter)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    route_samples, node_ring, _ = v4.obstacle_following_sample_route(
        route,
        target_length,
        grid,
        extend_ends=False,
    )
    v9.GLOBAL_ROUTE.clear()
    v9.GLOBAL_ROUTE.update({"target_length_mm": target_length})
    c9_points, c9_faces = v4.component9_geometry()
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    open_points, open_faces, _ = evaluated_geometry(
        bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    )
    ranges = {
        "B0": [node_ring[0], node_ring[6] + 2],
        "B1": [node_ring[6] - 2, node_ring[7] + 2],
        "B2a": [node_ring[7] - 2, node_ring[11] + 2],
        "B2b": [node_ring[11] - 2, node_ring[12]],
    }
    candidates = {}
    original_geometry = v9.candidate_geometry
    v9.candidate_geometry = v10.directed_candidate_geometry
    try:
        for name in ("B0", "B1", "B2a", "B2b"):
            first, last = ranges[name]
            samples = route_samples[first : last + 1]
            passing = []
            for direction in v10.DIRECTION_DEGREES:
                for offset in v10.OFFSETS_MM:
                    for roll in v10.ROLLS_DEGREES:
                        record = v11.evaluate(
                            name,
                            samples,
                            direction,
                            offset,
                            roll,
                            target_length,
                            grid,
                            c9_points,
                            c9_faces,
                            cutter_points,
                            cutter_faces,
                        )
                        if record["gate_pass"]:
                            passing.append(record)
            candidates[name] = passing
    finally:
        v9.candidate_geometry = original_geometry
    broad_combinations = []
    for records in product(
        candidates["B0"],
        candidates["B1"],
        candidates["B2a"],
        candidates["B2b"],
    ):
        cage = overlap_pairs(
            records[0]["_points"],
            records[0]["_faces"],
            open_points,
            open_faces,
        )
        if not cage:
            continue
        endpoint_gaps = [
            endpoint_pair(first, second)[0]
            for first, second in zip(records, records[1:])
        ]
        broad_combinations.append(
            {
                "records": records,
                "cage_overlap_count": len(cage),
                "endpoint_gaps_mm": endpoint_gaps,
                "gap_sum_mm": sum(endpoint_gaps),
            }
        )
    ranked = sorted(
        broad_combinations,
        key=lambda item: (
            item["gap_sum_mm"],
            sum(
                record["offset_mm"] for record in item["records"]
            ),
        ),
    )
    search_records = []
    selected = None
    for combination_index, combination in enumerate(
        ranked[:MAXIMUM_BROAD_COMBINATIONS]
    ):
        connectors = []
        edge_records = []
        complete = True
        for edge, (first, second) in enumerate(
            zip(combination["records"], combination["records"][1:])
        ):
            direct = overlap_pairs(
                first["_points"],
                first["_faces"],
                second["_points"],
                second["_faces"],
            )
            if direct:
                edge_records.append(
                    {
                        "edge": edge,
                        "method": "direct_overlap",
                        "overlap_count": len(direct),
                    }
                )
                continue
            connector, attempts = find_connector(
                first,
                second,
                target_length,
                grid,
                c9_points,
                c9_faces,
                cutter_points,
                cutter_faces,
            )
            edge_records.append(
                {
                    "edge": edge,
                    "method": (
                        "local_bridge" if connector else "no_bridge"
                    ),
                    "selected": public(connector) if connector else None,
                    "attempt_count": len(attempts),
                    "best_residual": (
                        None if connector else public(attempts[0])
                    ),
                }
            )
            if connector is None:
                complete = False
                break
            connectors.append(connector)
        search_records.append(
            {
                "combination_rank": combination_index,
                "gap_sum_mm": round(combination["gap_sum_mm"], 6),
                "endpoint_gaps_mm": [
                    round(value, 6)
                    for value in combination["endpoint_gaps_mm"]
                ],
                "edges": edge_records,
                "complete": complete,
            }
        )
        if complete:
            selected = {
                "combination": combination,
                "connectors": connectors,
                "edges": edge_records,
            }
            break
    geometry_emitted = selected is not None
    base_report = None
    if geometry_emitted:
        points = []
        faces = []
        samples = []
        combined_node_ring = {}
        node_specs = ((0, 6), (6, 7), (7, 11), (11, 12))
        constituents = [
            *selected["combination"]["records"],
            *selected["connectors"],
        ]
        for constituent_index, record in enumerate(constituents):
            vertex_offset = len(points)
            ring_offset = len(samples)
            points.extend(point.copy() for point in record["_points"])
            faces.extend(
                tuple(vertex_offset + index for index in face)
                for face in record["_faces"]
            )
            samples.extend(point.copy() for point in record["_samples"])
            if constituent_index < 4:
                first_node, last_node = node_specs[constituent_index]
                for node in range(first_node, last_node + 1):
                    if node not in combined_node_ring:
                        combined_node_ring[node] = (
                            ring_offset + node_ring[node]
                            - ranges[
                                ("B0", "B1", "B2a", "B2b")[
                                    constituent_index
                                ]
                            ][0]
                        )
        geometry = {
            "points": points,
            "faces": faces,
            "samples": samples,
            "node_ring": combined_node_ring,
            "exact_rings": set(),
            "half_widths": [3.0] * len(samples),
            "width_reduction_passes": [],
        }

        def selected_network(route, target_length, grid, *, extend_ends):
            if extend_ends:
                raise RuntimeError(
                    f"{OPERATION}: attachments are unsupported"
                )
            return geometry

        v4.fixed_width_ribbon = selected_network
        v4.__file__ = __file__
        v4.main()
        base_report = json.loads(report_path.read_text(encoding="utf-8"))
    gates = {
        "retained_1409_faces_exact": (
            bool(base_report)
            and base_report["gates"]["retained_1409_faces_exact"]
        ),
        "hard_controls_exact": (
            bool(base_report) and base_report["gates"]["hard_controls_exact"]
        ),
        "central_bowl_open": (
            bool(base_report) and base_report["gates"]["central_bowl_open"]
        ),
        "tip_gap_preserved": (
            bool(base_report) and base_report["gates"]["tip_gap_preserved"]
        ),
        "component_9_unchanged": (
            bool(base_report) and base_report["gates"]["component_9_unchanged"]
        ),
        "non_tip_component_9_clear": (
            bool(base_report)
            and base_report["v4_preflight"][
                "component_9_overlap_localization"
            ]["non_tip_overlap_count"]
            == 0
        ),
        "new_geometry_cutter_clear": (
            bool(base_report)
            and base_report["collisions"]["network_cutter_overlap_count"] == 0
        ),
        "new_vertex_margin": (
            bool(base_report)
            and base_report["collisions"][
                "network_minimum_cutter_margin_mm"
            ]
            >= 1.6998
        ),
        "global_cutter_overlap_bound": (
            bool(base_report)
            and base_report["gates"]["global_cutter_overlap_bound"]
        ),
        "component_9_overlap_exact": (
            bool(base_report)
            and base_report["gates"]["component_9_overlap_exact"]
        ),
        "component_20_overlap_bound": (
            bool(base_report)
            and base_report["gates"]["component_20_overlap_bound"]
        ),
        "historical_non_tip_pairs_not_welded": (
            bool(base_report)
            and base_report["gates"]["historical_non_tip_pairs_not_welded"]
        ),
        "all_broad_constituents_machine_valid": (
            bool(selected)
            and all(
                record["gate_pass"]
                for record in selected["combination"]["records"]
            )
        ),
        "all_connectors_machine_valid": (
            bool(selected)
            and all(
                record["gate_pass"] for record in selected["connectors"]
            )
        ),
        "all_constituents_closed_positive_contiguous": (
            bool(selected)
            and all(
                record["audit"]["connected_components"] == 1
                and record["audit"]["boundary_edges"] == 0
                and record["audit"]["nonmanifold_edges"] == 0
                and record["audit"]["noncontiguous_manifold_edges"] == 0
                and record["audit"]["signed_volume_mm3"] > 0.0
                for record in (
                    *selected["combination"]["records"],
                    *selected["connectors"],
                )
            )
        ),
        "aggregate_internal_self_clear": (
            bool(selected)
            and all(
                record["self_overlap_count"] == 0
                for record in (
                    *selected["combination"]["records"],
                    *selected["connectors"],
                )
            )
        ),
        "all_constituent_triangle_quality": (
            bool(selected)
            and all(
                record["triangle_quality"]["degenerate_triangle_count"] == 0
                and record["triangle_quality"][
                    "minimum_angle_degrees"
                ]["minimum"]
                >= 3.0
                and record["triangle_quality"]["aspect_ratio"]["maximum"]
                <= 12.0
                for record in (
                    *selected["combination"]["records"],
                    *selected["connectors"],
                )
            )
        ),
        "broad_fixed_6x2_4_section": (
            bool(selected)
            and all(
                record["minimum_width_mm"] >= 5.8 - 1.0e-4
                and record["maximum_width_mm"] <= 6.2 + 1.0e-4
                and record["minimum_thickness_mm"] >= 2.4 - 1.0e-4
                and record["maximum_thickness_mm"] <= 2.4 + 1.0e-4
                for record in selected["combination"]["records"]
            )
        ),
        "complete_measured_contact_graph": bool(selected),
        "connector_structural_minimum_width": (
            bool(selected)
            and all(
                record["minimum_width_mm"]
                >= CONNECTOR_INTERIOR_WIDTH_MM - 1.0e-4
                for record in selected["connectors"]
            )
        ),
        "connector_terminal_flares_embedded": (
            bool(selected)
            and all(
                record["first_overlap_count"] > 0
                and record["second_overlap_count"] > 0
                for record in selected["connectors"]
            )
        ),
    }
    gate_pass = all(gates.values())
    registration_controls = (
        [
            {
                "source_vertex_id": int(source_id),
                "displacement_mm": displacement,
                "classification": (
                    "exact" if displacement <= 0.0001 else "relaxed"
                ),
            }
            for source_id, displacement in base_report["registration"][
                "anchor_error_mm"
            ].items()
        ]
        if base_report
        else []
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": (
            "evaluation_only_connection_network_machine_pass"
            if gate_pass
            else "evaluation_only_connection_network_machine_failed"
            if geometry_emitted
            else "preflight_no_complete_connection_network"
        ),
        "input_blend": str(blend_path),
        "input_blend_sha256": input_sha,
        "candidate_counts": {
            name: len(records) for name, records in candidates.items()
        },
        "broad_combination_count": len(broad_combinations),
        "connector_search_combination_limit": MAXIMUM_BROAD_COMBINATIONS,
        "connector_search_records": search_records,
        "selected": (
            {
                "broad": [
                    public(record)
                    for record in selected["combination"]["records"]
                ],
                "connectors": [
                    public(record) for record in selected["connectors"]
                ],
                "edges": selected["edges"],
                "cage_overlap_count": selected["combination"][
                    "cage_overlap_count"
                ],
            }
            if selected
            else None
        ),
        "validation": (
            {
                "retained_exterior": base_report["retained_exterior"],
                "hard_control_error_mm": base_report["registration"][
                    "hard_control_error_mm"
                ],
                "tip_gap_mm": base_report["band"]["tip_gap_mm"],
                "collisions": base_report["collisions"],
                "network_audit": base_report["network"]["audit"],
                "objects": base_report["objects"],
                "component_9_overlap_localization": base_report[
                    "v4_preflight"
                ]["component_9_overlap_localization"],
                "legacy_registration_controls": registration_controls,
                "exact_legacy_control_ids": [
                    record["source_vertex_id"]
                    for record in registration_controls
                    if record["classification"] == "exact"
                ],
                "relaxed_legacy_controls": [
                    record
                    for record in registration_controls
                    if record["classification"] == "relaxed"
                ],
                "constituent_minimum_cutter_margin_mm": min(
                    record["minimum_cutter_margin_mm"]
                    for record in (
                        *selected["combination"]["records"],
                        *selected["connectors"],
                    )
                ),
                "broad_width_range_mm": [
                    min(
                        record["minimum_width_mm"]
                        for record in selected["combination"]["records"]
                    ),
                    max(
                        record["maximum_width_mm"]
                        for record in selected["combination"]["records"]
                    ),
                ],
                "broad_thickness_range_mm": [
                    min(
                        record["minimum_thickness_mm"]
                        for record in selected["combination"]["records"]
                    ),
                    max(
                        record["maximum_thickness_mm"]
                        for record in selected["combination"]["records"]
                    ),
                ],
                "all_constituent_minimum_angle_degrees": min(
                    record["triangle_quality"][
                        "minimum_angle_degrees"
                    ]["minimum"]
                    for record in (
                        *selected["combination"]["records"],
                        *selected["connectors"],
                    )
                ),
                "all_constituent_maximum_aspect_ratio": max(
                    record["triangle_quality"]["aspect_ratio"]["maximum"]
                    for record in (
                        *selected["combination"]["records"],
                        *selected["connectors"],
                    )
                ),
            }
            if base_report
            else None
        ),
        "geometry_emitted": geometry_emitted,
        "gates": gates,
        "gate_pass": gate_pass,
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
                "candidate_counts": report["candidate_counts"],
                "broad_combination_count": len(broad_combinations),
                "searched_combinations": len(search_records),
                "geometry_emitted": geometry_emitted,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v12 connection-aware network geometry_emitted="
        f"{geometry_emitted}; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
