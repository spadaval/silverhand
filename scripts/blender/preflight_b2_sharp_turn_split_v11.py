"""Compare minimal B2 splits at V2111 and V2108 for Repair 014 v11."""

from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_broad_constituent_network_v9 as v9  # noqa: E402
import preflight_direction_field_network_v10 as v10  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "B2_SHARP_TURN_SPLIT_V11"
FIXED_B0 = (180, 8.0, 120)
FIXED_B1 = (0, 8.0, 165)
SPLITS = (
    ("split_at_V2111", 10),
    ("split_at_V2108", 11),
)
MAXIMUM_RETAINED_CANDIDATES = 24


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def evaluate(
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
):
    v10.CURRENT_DIRECTION_DEGREES = direction
    record = v9.evaluate_candidate(
        name,
        samples,
        offset,
        roll,
        target_length,
        grid,
        c9_points,
        c9_faces,
        cutter_points,
        cutter_faces,
    )
    record["direction_degrees"] = direction
    return record


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def least_bad(records):
    return min(
        records,
        key=lambda record: (
            record["c9_overlap_count"],
            record["cutter_overlap_count"],
            record["self_overlap_count"],
            max(0.0, 1.7 - record["minimum_cutter_margin_mm"]),
            max(
                0.0,
                3.0
                - record["triangle_quality"]["minimum_angle_degrees"][
                    "minimum"
                ],
            ),
            max(
                0.0,
                record["triangle_quality"]["aspect_ratio"]["maximum"] - 12.0,
            ),
            record["offset_mm"],
        ),
    )


def main() -> int:
    report_path = report_argument()
    blend_path = Path(bpy.data.filepath).resolve()
    input_sha = v10.sha256_file(blend_path)
    expected_sha = v4.v2.EXPECTED_BLEND_SHA256
    if input_sha != expected_sha:
        raise RuntimeError(
            f"{OPERATION}: input Blend '{blend_path}' has SHA-256 "
            f"'{input_sha}', expected clean open-cage '{expected_sha}'"
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
    route_samples, route_node_ring, _ = v4.obstacle_following_sample_route(
        route,
        target_length,
        grid,
        extend_ends=False,
    )
    v9.GLOBAL_ROUTE.clear()
    v9.GLOBAL_ROUTE.update(
        {
            "target_length_mm": target_length,
            "source_samples": route_samples,
            "source_node_ring": route_node_ring,
        }
    )
    c9_points, c9_faces = v4.component9_geometry()
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    open_points, open_faces, _ = evaluated_geometry(
        bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    )
    original_geometry = v9.candidate_geometry
    v9.candidate_geometry = v10.directed_candidate_geometry
    try:
        b0_range = [route_node_ring[0], route_node_ring[6] + 2]
        b1_range = [route_node_ring[6] - 2, route_node_ring[7] + 2]
        b0 = evaluate(
            "B0",
            route_samples[b0_range[0] : b0_range[1] + 1],
            *FIXED_B0,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
        )
        b1 = evaluate(
            "B1",
            route_samples[b1_range[0] : b1_range[1] + 1],
            *FIXED_B1,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
        )
        preserved_contacts = {
            "B0_cage_overlap_count": len(
                overlap_pairs(
                    b0["_points"],
                    b0["_faces"],
                    open_points,
                    open_faces,
                )
            ),
            "B0_B1_overlap_count": len(
                overlap_pairs(
                    b0["_points"],
                    b0["_faces"],
                    b1["_points"],
                    b1["_faces"],
                )
            ),
        }
        split_results = {}
        complete = []
        for split_name, split_node in SPLITS:
            ranges = {
                "B2a": [
                    route_node_ring[7] - 2,
                    min(
                        len(route_samples) - 1,
                        route_node_ring[split_node] + 2,
                    ),
                ],
                "B2b": [
                    max(0, route_node_ring[split_node] - 2),
                    route_node_ring[12],
                ],
            }
            passing = {}
            summaries = {}
            for part_name in ("B2a", "B2b"):
                first, last = ranges[part_name]
                local_samples = route_samples[first : last + 1]
                records = []
                for direction in v10.DIRECTION_DEGREES:
                    for offset in v10.OFFSETS_MM:
                        for roll in v10.ROLLS_DEGREES:
                            records.append(
                                evaluate(
                                    part_name,
                                    local_samples,
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
                            )
                passing[part_name] = sorted(
                    (
                        record
                        for record in records
                        if record["gate_pass"]
                    ),
                    key=lambda record: (
                        record["offset_mm"],
                        record["direction_degrees"],
                        record["roll_degrees"],
                    ),
                )
                frontier = v10.pareto_frontier(records)
                summaries[part_name] = {
                    "sample_ring_range": ranges[part_name],
                    "evaluated_count": len(records),
                    "admissible_count": len(passing[part_name]),
                    "admissible_direction_degrees": sorted(
                        {
                            record["direction_degrees"]
                            for record in passing[part_name]
                        }
                    ),
                    "pareto_frontier_count": len(frontier),
                    "pareto_frontier": [
                        public(record) for record in frontier
                    ],
                    "least_bad": public(least_bad(records)),
                }
            combinations = []
            internal_lap_count = 0
            b1_and_internal_lap_count = 0
            for first, second in product(
                passing["B2a"][:MAXIMUM_RETAINED_CANDIDATES],
                passing["B2b"][:MAXIMUM_RETAINED_CANDIDATES],
            ):
                b2a_b2b = overlap_pairs(
                    first["_points"],
                    first["_faces"],
                    second["_points"],
                    second["_faces"],
                )
                if not b2a_b2b:
                    continue
                internal_lap_count += 1
                b1_b2a = overlap_pairs(
                    b1["_points"],
                    b1["_faces"],
                    first["_points"],
                    first["_faces"],
                )
                if not b1_b2a:
                    continue
                b1_and_internal_lap_count += 1
                if (
                    b0["gate_pass"]
                    and b1["gate_pass"]
                    and preserved_contacts["B0_cage_overlap_count"] > 0
                    and preserved_contacts["B0_B1_overlap_count"] > 0
                ):
                    combinations.append(
                        {
                            "records": (first, second),
                            "B1_B2a_overlap_count": len(b1_b2a),
                            "B2a_B2b_overlap_count": len(b2a_b2b),
                        }
                    )
            split_results[split_name] = {
                "split_source_vertex_id": centerline_ids[split_node],
                "sample_ring_ranges": ranges,
                "parts": summaries,
                "internal_lap_combination_count": internal_lap_count,
                "B1_and_internal_lap_combination_count": (
                    b1_and_internal_lap_count
                ),
                "passing_contact_combination_count": len(combinations),
            }
            for combination in combinations:
                complete.append(
                    {
                        "split_name": split_name,
                        "split_node": split_node,
                        **combination,
                    }
                )
    finally:
        v9.candidate_geometry = original_geometry
    selected = (
        min(
            complete,
            key=lambda item: (
                sum(
                    record["offset_mm"] for record in item["records"]
                ),
                0 if item["split_name"] == "split_at_V2111" else 1,
                sum(
                    record["direction_degrees"]
                    for record in item["records"]
                ),
                sum(record["roll_degrees"] for record in item["records"]),
            ),
        )
        if complete
        else None
    )
    geometry_emitted = selected is not None
    if geometry_emitted:
        selected_ranges = split_results[selected["split_name"]][
            "sample_ring_ranges"
        ]
        records_and_nodes = (
            (b0, b0_range, 0, 6),
            (b1, b1_range, 6, 7),
            (
                selected["records"][0],
                selected_ranges["B2a"],
                7,
                selected["split_node"],
            ),
            (
                selected["records"][1],
                selected_ranges["B2b"],
                selected["split_node"],
                12,
            ),
        )
        combined_points = []
        combined_faces = []
        combined_samples = []
        combined_node_ring = {}
        for record, ring_range, first_node, last_node in records_and_nodes:
            vertex_offset = len(combined_points)
            ring_offset = len(combined_samples)
            combined_points.extend(
                point.copy() for point in record["_points"]
            )
            combined_faces.extend(
                tuple(vertex_offset + index for index in face)
                for face in record["_faces"]
            )
            combined_samples.extend(
                point.copy() for point in record["_samples"]
            )
            for node in range(first_node, last_node + 1):
                if node not in combined_node_ring:
                    combined_node_ring[node] = (
                        ring_offset
                        + route_node_ring[node]
                        - ring_range[0]
                    )
        geometry = {
            "points": combined_points,
            "faces": combined_faces,
            "samples": combined_samples,
            "node_ring": combined_node_ring,
            "exact_rings": set(),
            "half_widths": [3.0] * len(combined_samples),
            "width_reduction_passes": [
                {
                    "iteration": 0,
                    "adaptive_width_used": False,
                    "minimum_width_mm": 6.0,
                }
            ],
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
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": (
            "evaluation_only_split_network_machine_pass"
            if geometry_emitted
            else "preflight_no_complete_split_network"
        ),
        "input_blend": str(blend_path),
        "input_blend_sha256": input_sha,
        "preserved_candidates": {
            "B0": public(b0),
            "B1": public(b1),
            "contacts": preserved_contacts,
        },
        "split_comparison": split_results,
        "complete_selection_count": len(complete),
        "selected_split": (
            {
                "split_name": selected["split_name"],
                "B2a": public(selected["records"][0]),
                "B2b": public(selected["records"][1]),
                "B1_B2a_overlap_count": selected[
                    "B1_B2a_overlap_count"
                ],
                "B2a_B2b_overlap_count": selected[
                    "B2a_B2b_overlap_count"
                ],
            }
            if selected
            else None
        ),
        "geometry_emitted": geometry_emitted,
        "gates": {
            "preserved_B0_machine_valid": b0["gate_pass"],
            "preserved_B1_machine_valid": b1["gate_pass"],
            "preserved_B0_cage_landing": (
                preserved_contacts["B0_cage_overlap_count"] > 0
            ),
            "preserved_B0_B1_lap": (
                preserved_contacts["B0_B1_overlap_count"] > 0
            ),
            "complete_split_graph_exists": geometry_emitted,
            "geometry_not_emitted_without_complete_graph": (
                geometry_emitted or selected is None
            ),
        },
        "gate_pass": geometry_emitted,
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
                "geometry_emitted": geometry_emitted,
                "preserved_contacts": preserved_contacts,
                "split_admissible_counts": {
                    split_name: {
                        part: data["parts"][part]["admissible_count"]
                        for part in ("B2a", "B2b")
                    }
                    for split_name, data in split_results.items()
                },
                "complete_selection_count": len(complete),
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v11 B2 split preflight geometry_emitted="
        f"{geometry_emitted}; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
