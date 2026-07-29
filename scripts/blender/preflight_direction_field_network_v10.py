"""Evaluate bounded local-normal translation directions for Repair 014 v10."""

from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
from math import cos, radians, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_broad_constituent_network_v9 as v9  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "DIRECTION_FIELD_PREFLIGHT_V10"
DIRECTION_DEGREES = list(range(0, 360, 30))
OFFSETS_MM = [0.5 * index for index in range(17)]
ROLLS_DEGREES = list(range(0, 360, 15))
MAXIMUM_COMBINATION_CANDIDATES = 24
CURRENT_DIRECTION_DEGREES = 0
SELECTED_COMBINATION = None
PREFLIGHT = {}


def argument_path(name: str) -> Path:
    try:
        index = sys.argv.index(name)
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks {name} PATH"
        ) from error


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directed_candidate_geometry(
    source_samples: list[Vector],
    offset_mm: float,
    roll_degrees: int,
) -> tuple[list[Vector], list[tuple[int, ...]], list[Vector]]:
    tangents = v8.centered_tangents(source_samples)
    away = v9.away_directions(source_samples)
    angle = radians(CURRENT_DIRECTION_DEGREES)
    directions = []
    for ring, (tangent, raw_away) in enumerate(zip(tangents, away)):
        first = raw_away - tangent * raw_away.dot(tangent)
        if first.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: normal-plane C9 axis collapsed at ring {ring}"
            )
        first.normalize()
        second = tangent.cross(first)
        if second.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: normal-plane side axis collapsed at ring {ring}"
            )
        second.normalize()
        directions.append((first * cos(angle) + second * sin(angle)).normalized())
    shifted = [
        point + direction * offset_mm
        for point, direction in zip(source_samples, directions)
    ]
    shifted_tangents = v8.centered_tangents(shifted)
    frames = v8.minimum_twist_frames(
        shifted,
        shifted_tangents,
        v9.GLOBAL_ROUTE["target_length_mm"],
    )
    points = []
    for point, tangent, frame in zip(shifted, shifted_tangents, frames):
        width, thickness = v8.rotated_frame(
            frame[0],
            tangent,
            roll_degrees,
        )
        points.extend(v8.ring_points(point, width, thickness))
    faces = v4.v2.base.positive_faces(
        points,
        v8.closed_faces(len(shifted)),
    )
    return points, faces, shifted


def dominates(first: dict, second: dict) -> bool:
    not_worse = all(
        (
            first["c9_overlap_count"] <= second["c9_overlap_count"],
            first["cutter_overlap_count"] <= second["cutter_overlap_count"],
            first["self_overlap_count"] <= second["self_overlap_count"],
            first["minimum_cutter_margin_mm"]
            >= second["minimum_cutter_margin_mm"],
        )
    )
    strictly_better = any(
        (
            first["c9_overlap_count"] < second["c9_overlap_count"],
            first["cutter_overlap_count"] < second["cutter_overlap_count"],
            first["self_overlap_count"] < second["self_overlap_count"],
            first["minimum_cutter_margin_mm"]
            > second["minimum_cutter_margin_mm"],
        )
    )
    return not_worse and strictly_better


def pareto_frontier(records: list[dict]) -> list[dict]:
    frontier = []
    for record in records:
        if any(dominates(existing, record) for existing in frontier):
            continue
        frontier = [
            existing
            for existing in frontier
            if not dominates(record, existing)
        ]
        frontier.append(record)
    return sorted(
        frontier,
        key=lambda record: (
            record["c9_overlap_count"],
            record["cutter_overlap_count"],
            record["self_overlap_count"],
            -record["minimum_cutter_margin_mm"],
            record["offset_mm"],
            record["direction_degrees"],
            record["roll_degrees"],
        ),
    )


def public(record: dict) -> dict:
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def combined_geometry(records, route_node_ring, ranges):
    points = []
    faces = []
    samples = []
    node_ring = {}
    for record, (name, first_node, last_node) in zip(
        records,
        v9.CONSTITUENT_SPECS,
    ):
        vertex_offset = len(points)
        ring_offset = len(samples)
        points.extend(point.copy() for point in record["_points"])
        faces.extend(
            tuple(vertex_offset + index for index in face)
            for face in record["_faces"]
        )
        samples.extend(point.copy() for point in record["_samples"])
        first_global_ring = ranges[name][0]
        for node in range(first_node, last_node + 1):
            if node not in node_ring:
                node_ring[node] = (
                    ring_offset + route_node_ring[node] - first_global_ring
                )
    return {
        "points": points,
        "faces": faces,
        "samples": samples,
        "node_ring": node_ring,
        "exact_rings": set(),
        "half_widths": [3.0] * len(samples),
        "width_reduction_passes": [
            {
                "iteration": 0,
                "adaptive_width_used": False,
                "minimum_width_mm": 6.0,
            }
        ],
    }


def main() -> int:
    global CURRENT_DIRECTION_DEGREES, SELECTED_COMBINATION
    report_path = argument_path("--report")
    blend_path = Path(bpy.data.filepath).resolve()
    input_sha = sha256_file(blend_path)
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
    contract = v4.rail_only_contract()
    centerline_ids = contract["ordered_centerline_source_vertex_ids"]
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
    original_candidate_geometry = v9.candidate_geometry
    v9.candidate_geometry = directed_candidate_geometry
    ranges = {}
    all_records = {}
    passing = {}
    try:
        for piece_index, (name, first_node, last_node) in enumerate(
            v9.CONSTITUENT_SPECS
        ):
            first_ring = route_node_ring[first_node]
            last_ring = route_node_ring[last_node]
            if piece_index > 0:
                first_ring = max(0, first_ring - 2)
            if piece_index < len(v9.CONSTITUENT_SPECS) - 1:
                last_ring = min(len(route_samples) - 1, last_ring + 2)
            ranges[name] = [first_ring, last_ring]
            local_samples = route_samples[first_ring : last_ring + 1]
            records = []
            for direction_degrees in DIRECTION_DEGREES:
                CURRENT_DIRECTION_DEGREES = direction_degrees
                for offset_mm in OFFSETS_MM:
                    for roll_degrees in ROLLS_DEGREES:
                        record = v9.evaluate_candidate(
                            name,
                            local_samples,
                            offset_mm,
                            roll_degrees,
                            target_length,
                            grid,
                            c9_points,
                            c9_faces,
                            cutter_points,
                            cutter_faces,
                        )
                        record["direction_degrees"] = direction_degrees
                        records.append(record)
            all_records[name] = records
            passing[name] = [
                record for record in records if record["gate_pass"]
            ]
    finally:
        v9.candidate_geometry = original_candidate_geometry
    search = {}
    for name, _, _ in v9.CONSTITUENT_SPECS:
        frontier = pareto_frontier(all_records[name])
        least_bad = min(
            all_records[name],
            key=lambda record: (
                record["c9_overlap_count"],
                record["cutter_overlap_count"],
                record["self_overlap_count"],
                max(0.0, 1.7 - record["minimum_cutter_margin_mm"]),
                record["offset_mm"],
            ),
        )
        search[name] = {
            "sample_ring_range": ranges[name],
            "evaluated_count": len(all_records[name]),
            "admissible_count": len(passing[name]),
            "admissible_direction_degrees": sorted(
                {
                    record["direction_degrees"]
                    for record in passing[name]
                }
            ),
            "pareto_frontier_count": len(frontier),
            "pareto_frontier": [public(record) for record in frontier],
            "least_bad": public(least_bad),
        }
    combinations = []
    if all(passing[name] for name, _, _ in v9.CONSTITUENT_SPECS):
        retained = {
            name: sorted(
                passing[name],
                key=lambda record: (
                    record["offset_mm"],
                    record["direction_degrees"],
                    record["roll_degrees"],
                ),
            )[:MAXIMUM_COMBINATION_CANDIDATES]
            for name, _, _ in v9.CONSTITUENT_SPECS
        }
        for records in product(
            *(retained[name] for name, _, _ in v9.CONSTITUENT_SPECS)
        ):
            lap_01 = overlap_pairs(
                records[0]["_points"],
                records[0]["_faces"],
                records[1]["_points"],
                records[1]["_faces"],
            )
            if not lap_01:
                continue
            lap_12 = overlap_pairs(
                records[1]["_points"],
                records[1]["_faces"],
                records[2]["_points"],
                records[2]["_faces"],
            )
            if not lap_12:
                continue
            landing = overlap_pairs(
                records[0]["_points"],
                records[0]["_faces"],
                open_points,
                open_faces,
            )
            if landing:
                combinations.append(
                    {
                        "records": records,
                        "B0_cage": len(landing),
                        "B0_B1": len(lap_01),
                        "B1_B2": len(lap_12),
                    }
                )
    geometry_emitted = bool(combinations)
    PREFLIGHT.clear()
    PREFLIGHT.update(
        {
            "direction_degrees": DIRECTION_DEGREES,
            "offsets_mm": OFFSETS_MM,
            "rolls_degrees": ROLLS_DEGREES,
            "candidate_count_per_constituent": (
                len(DIRECTION_DEGREES) * len(OFFSETS_MM) * len(ROLLS_DEGREES)
            ),
            "search": search,
            "passing_contact_combination_count": len(combinations),
            "geometry_emitted": geometry_emitted,
        }
    )
    if geometry_emitted:
        SELECTED_COMBINATION = min(
            combinations,
            key=lambda item: (
                sum(record["offset_mm"] for record in item["records"]),
                sum(record["direction_degrees"] for record in item["records"]),
                sum(record["roll_degrees"] for record in item["records"]),
            ),
        )
        geometry = combined_geometry(
            SELECTED_COMBINATION["records"],
            route_node_ring,
            ranges,
        )

        def preselected_network(route, target_length, grid, *, extend_ends):
            if extend_ends:
                raise RuntimeError(
                    f"{OPERATION}: attachments are unsupported"
                )
            return geometry

        v4.fixed_width_ribbon = preselected_network
        v4.__file__ = __file__
        v4.main()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["status"] = "evaluation_only_direction_field_machine_pass"
        report["v10_direction_field_preflight"] = PREFLIGHT
        report["v10_direction_field_preflight"]["selected_contact_counts"] = {
            key: SELECTED_COMBINATION[key]
            for key in ("B0_cage", "B0_B1", "B1_B2")
        }
        report["promotion"] = "NOT_PROMOTED"
        report["qualitative_review"] = "NOT_REQUESTED"
        report_path.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        report = {
            "tool": Path(__file__).name,
            "operation": OPERATION,
            "status": "preflight_no_admissible_network",
            "input_blend": str(blend_path),
            "input_blend_sha256": input_sha,
            "partition": [
                {
                    "name": name,
                    "source_vertex_ids": centerline_ids[first : last + 1],
                }
                for name, first, last in v9.CONSTITUENT_SPECS
            ],
            "v10_direction_field_preflight": PREFLIGHT,
            "gates": {
                "all_constituents_have_admissible_direction": all(
                    passing[name] for name, _, _ in v9.CONSTITUENT_SPECS
                ),
                "passing_contact_combination_exists": False,
                "geometry_not_emitted_without_admissible_network": True,
            },
            "gate_pass": False,
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
                "admissible_counts": {
                    name: len(passing[name])
                    for name, _, _ in v9.CONSTITUENT_SPECS
                },
                "passing_contact_combination_count": len(combinations),
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v10 direction-field preflight geometry_emitted="
        f"{geometry_emitted}; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
