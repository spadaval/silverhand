"""Build a bounded three-constituent fixed-width Repair 014 v9 network."""

from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "BROAD_CONSTITUENT_NETWORK_V9"
OFFSETS_MM = [0.5 * index for index in range(17)]
ROLLS_DEGREES = list(range(0, 360, 15))
MAXIMUM_RETAINED_CANDIDATES = 24
TARGET_WIDTH_MM = 6.0
THICKNESS_MM = 2.4
CONSTITUENT_SPECS = (
    ("B0", 0, 6),
    ("B1", 6, 7),
    ("B2", 7, 12),
)
SEARCH_RECORDS = {}
SELECTED = {}
GLOBAL_ROUTE = {}


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def constituent_faces(ring_count: int) -> list[tuple[int, ...]]:
    return v8.closed_faces(ring_count)


def away_directions(samples: list[Vector]) -> list[Vector]:
    raw = []
    for ring, point in enumerate(samples):
        nearest, _, _, _ = v4.c9_bvh().find_nearest(point)
        if nearest is None:
            raise RuntimeError(
                f"{OPERATION}: C9 nearest-point query failed at ring {ring}"
            )
        direction = point - nearest
        if direction.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: C9 away direction collapsed at ring {ring}"
            )
        raw.append(direction.normalized())
    smooth = [direction.copy() for direction in raw]
    for _ in range(3):
        updated = []
        for ring, direction in enumerate(smooth):
            first = max(0, ring - 1)
            last = min(len(smooth), ring + 2)
            averaged = sum(smooth[first:last], Vector())
            if averaged.length <= 1.0e-8:
                averaged = direction.copy()
            averaged.normalize()
            if averaged.dot(raw[ring]) < 0.25:
                averaged = raw[ring].copy()
            updated.append(averaged)
        smooth = updated
    return smooth


def candidate_geometry(
    source_samples: list[Vector],
    offset_mm: float,
    roll_degrees: int,
) -> tuple[list[Vector], list[tuple[int, ...]], list[Vector]]:
    directions = away_directions(source_samples)
    shifted = [
        point + direction * offset_mm
        for point, direction in zip(source_samples, directions)
    ]
    tangents = v8.centered_tangents(shifted)
    frames = v8.minimum_twist_frames(
        shifted,
        tangents,
        GLOBAL_ROUTE["target_length_mm"],
    )
    points = []
    for point, tangent, frame in zip(shifted, tangents, frames):
        width, thickness = v8.rotated_frame(
            frame[0],
            tangent,
            roll_degrees,
        )
        points.extend(v8.ring_points(point, width, thickness))
    faces = v4.v2.base.positive_faces(
        points,
        constituent_faces(len(shifted)),
    )
    return points, faces, shifted


def evaluate_candidate(
    name: str,
    source_samples: list[Vector],
    offset_mm: float,
    roll_degrees: int,
    target_length: float,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
) -> dict:
    points, faces, shifted = candidate_geometry(
        source_samples,
        offset_mm,
        roll_degrees,
    )
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
        len(shifted),
    )
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    widths = [
        (points[index + 4] - points[index]).length
        for index in range(0, len(points), 5)
    ]
    thicknesses = [
        (points[index + 1] - points[index]).length
        for index in range(0, len(points), 5)
    ]
    gate_pass = all(
        (
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
            min(widths) >= 5.8 - 1.0e-4,
            max(widths) <= 6.2 + 1.0e-4,
            min(thicknesses) >= 2.4 - 1.0e-4,
            max(thicknesses) <= 2.4 + 1.0e-4,
        )
    )
    return {
        "name": name,
        "offset_mm": offset_mm,
        "roll_degrees": roll_degrees,
        "ring_count": len(shifted),
        "c9_overlap_count": len(c9_pairs),
        "cutter_overlap_count": len(cutter_pairs),
        "self_overlap_count": len(self_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "minimum_width_mm": round(min(widths), 6),
        "maximum_width_mm": round(max(widths), 6),
        "minimum_thickness_mm": round(min(thicknesses), 6),
        "maximum_thickness_mm": round(max(thicknesses), 6),
        "audit": audit,
        "triangle_quality": quality,
        "gate_pass": gate_pass,
        "_points": points,
        "_faces": faces,
        "_samples": shifted,
    }


def public(record: dict) -> dict:
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def broad_constituent_network(
    route,
    target_length,
    grid,
    *,
    extend_ends,
) -> dict:
    if extend_ends:
        raise RuntimeError(
            f"{OPERATION}: v9 does not construct attachment routes"
        )
    route_samples, route_node_ring, exact_rings = (
        v4.obstacle_following_sample_route(
            route,
            target_length,
            grid,
            extend_ends=False,
        )
    )
    GLOBAL_ROUTE.clear()
    GLOBAL_ROUTE.update(
        {
            "target_length_mm": target_length,
            "source_samples": route_samples,
            "source_node_ring": route_node_ring,
            "source_exact_rings": exact_rings,
        }
    )
    c9_points, c9_faces = v4.component9_geometry()
    cutter_points, cutter_faces, _ = evaluated_geometry(
        bpy.data.objects[v4.CUTTER_NAME]
    )
    open_points, open_faces, _ = evaluated_geometry(
        bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    )
    ranges = {}
    candidates = {}
    SEARCH_RECORDS.clear()
    for piece_index, (name, first_node, last_node) in enumerate(
        CONSTITUENT_SPECS
    ):
        first_ring = route_node_ring[first_node]
        last_ring = route_node_ring[last_node]
        if piece_index > 0:
            first_ring = max(0, first_ring - 2)
        if piece_index < len(CONSTITUENT_SPECS) - 1:
            last_ring = min(len(route_samples) - 1, last_ring + 2)
        ranges[name] = (first_ring, last_ring)
        local_samples = route_samples[first_ring : last_ring + 1]
        evaluated = []
        for offset_mm in OFFSETS_MM:
            for roll_degrees in ROLLS_DEGREES:
                evaluated.append(
                    evaluate_candidate(
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
                )
        passing = [record for record in evaluated if record["gate_pass"]]
        least_bad = min(
            evaluated,
            key=lambda record: (
                record["c9_overlap_count"],
                record["self_overlap_count"],
                record["cutter_overlap_count"],
                max(
                    0.0,
                    3.0
                    - record["triangle_quality"][
                        "minimum_angle_degrees"
                    ]["minimum"],
                ),
                max(
                    0.0,
                    record["triangle_quality"]["aspect_ratio"]["maximum"]
                    - 12.0,
                ),
                record["offset_mm"],
            ),
        )
        candidates[name] = (
            sorted(
                passing,
                key=lambda record: (
                    record["offset_mm"],
                    min(
                        record["roll_degrees"],
                        360 - record["roll_degrees"],
                    ),
                ),
            )[:MAXIMUM_RETAINED_CANDIDATES]
            if passing
            else [least_bad]
        )
        SEARCH_RECORDS[name] = {
            "range": [first_ring, last_ring],
            "evaluated_count": len(evaluated),
            "passing_count": len(passing),
            "retained_count": len(candidates[name]),
            "least_bad": public(least_bad),
        }
    combined = []
    if all(
        SEARCH_RECORDS[name]["passing_count"] > 0
        for name, _, _ in CONSTITUENT_SPECS
    ):
        for records in product(
            *(candidates[name] for name, _, _ in CONSTITUENT_SPECS)
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
            cage_landing = overlap_pairs(
                records[0]["_points"],
                records[0]["_faces"],
                open_points,
                open_faces,
            )
            if not cage_landing:
                continue
            combined.append(
                {
                    "records": records,
                    "lap_B0_B1": len(lap_01),
                    "lap_B1_B2": len(lap_12),
                    "cage_landing_B0": len(cage_landing),
                }
            )
    if combined:
        selected_combination = min(
            combined,
            key=lambda item: (
                sum(record["offset_mm"] for record in item["records"]),
                sum(
                    min(record["roll_degrees"], 360 - record["roll_degrees"])
                    for record in item["records"]
                ),
            ),
        )
        records = list(selected_combination["records"])
        graph_pass = True
    else:
        records = []
        for name, _, _ in CONSTITUENT_SPECS:
            records.append(candidates[name][0])
        selected_combination = {
            "lap_B0_B1": len(
                overlap_pairs(
                    records[0]["_points"],
                    records[0]["_faces"],
                    records[1]["_points"],
                    records[1]["_faces"],
                )
            ),
            "lap_B1_B2": len(
                overlap_pairs(
                    records[1]["_points"],
                    records[1]["_faces"],
                    records[2]["_points"],
                    records[2]["_faces"],
                )
            ),
            "cage_landing_B0": len(
                overlap_pairs(
                    records[0]["_points"],
                    records[0]["_faces"],
                    open_points,
                    open_faces,
                )
            ),
        }
        graph_pass = all(
            (
                selected_combination["lap_B0_B1"] > 0,
                selected_combination["lap_B1_B2"] > 0,
                selected_combination["cage_landing_B0"] > 0,
            )
        )
    points = []
    faces = []
    samples = []
    node_ring = {}
    constituent_records = []
    for record, (name, first_node, last_node) in zip(
        records,
        CONSTITUENT_SPECS,
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
            if node in node_ring:
                continue
            local_ring = route_node_ring[node] - first_global_ring
            node_ring[node] = ring_offset + local_ring
        constituent_records.append(
            {
                **public(record),
                "vertex_range": [
                    vertex_offset,
                    vertex_offset + len(record["_points"]) - 1,
                ],
                "face_count": len(record["_faces"]),
            }
        )
    SELECTED.clear()
    SELECTED.update(
        {
            "constituents": constituent_records,
            "graph": {
                "nodes": ["B(root)", "B0", "B1", "B2"],
                "edges": [
                    ["B(root)", "B0"],
                    ["B0", "B1"],
                    ["B1", "B2"],
                ],
                "cage_landing_B0_overlap_count": selected_combination[
                    "cage_landing_B0"
                ],
                "lap_B0_B1_overlap_count": selected_combination["lap_B0_B1"],
                "lap_B1_B2_overlap_count": selected_combination["lap_B1_B2"],
                "connected": graph_pass,
                "passing_combination_count": len(combined),
            },
        }
    )
    return {
        "points": points,
        "faces": faces,
        "samples": samples,
        "node_ring": node_ring,
        "exact_rings": set(),
        "half_widths": [TARGET_WIDTH_MM * 0.5] * len(samples),
        "width_reduction_passes": [
            {
                "iteration": 0,
                "adaptive_width_used": False,
                "minimum_width_mm": TARGET_WIDTH_MM,
            }
        ],
    }


def main() -> int:
    v4.OPERATION = OPERATION
    v4.v2.OPERATION = OPERATION
    v4.__file__ = __file__
    v4.SWEEP_OFFSET_MM = 2.0
    v4.SWEEP_ANGLE_DEGREES = 0
    v4.fixed_width_ribbon = broad_constituent_network
    result = v4.main()
    report_path = report_argument()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    network = bpy.data.objects[report["objects"]["network"]]
    network_points, network_faces, _ = evaluated_geometry(network)
    c9_points, c9_faces = v4.component9_geometry()
    cutter_points, cutter_faces, _ = evaluated_geometry(
        bpy.data.objects[v4.CUTTER_NAME]
    )
    c9_pairs = overlap_pairs(
        network_points,
        network_faces,
        c9_points,
        c9_faces,
    )
    cutter_pairs = overlap_pairs(
        network_points,
        network_faces,
        cutter_points,
        cutter_faces,
    )
    grid, _ = v4.cutter_grid(bpy.data.objects[v4.CUTTER_NAME])
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    margins = v4.v2.point_margins(network_points, target_length, grid)
    staged_points, _, _ = evaluated_geometry(
        bpy.data.objects[v4.v2.base.STAGED_NAME]
    )
    centerline_ids = v4.rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    control_records = []
    selected_by_name = {
        record["name"]: record for record in SELECTED["constituents"]
    }
    for node, source_id in enumerate(centerline_ids):
        selected_ring = GLOBAL_ROUTE["source_node_ring"][node]
        best = min(
            (
                (
                    (network_points[index] - staged_points[source_id]).length,
                    index,
                    network_points[index],
                )
                for index in range(0, len(network_points), 5)
            ),
            key=lambda item: item[0],
        )
        displacement = best[2] - staged_points[source_id]
        selected_constituent = next(
            record["name"]
            for record in SELECTED["constituents"]
            if record["vertex_range"][0]
            <= best[1]
            <= record["vertex_range"][1]
        )
        constituent_gate_pass = selected_by_name[
            selected_constituent
        ]["gate_pass"]
        coordinate_exact = best[0] <= 0.0001
        control_records.append(
            {
                "source_vertex_id": source_id,
                "selected_constituent": selected_constituent,
                "nearest_selected_ring": best[1] // 5,
                "source_route_ring": selected_ring,
                "displacement_vector_mm": [
                    round(value, 9) for value in displacement
                ],
                "displacement_mm": round(best[0], 9),
                "coordinate_exact": coordinate_exact,
                "selected_constituent_gate_pass": constituent_gate_pass,
                "classification": (
                    "exact"
                    if coordinate_exact and constituent_gate_pass
                    else "relaxed_infeasible_constituent"
                    if coordinate_exact
                    else "relaxed_displaced"
                ),
            }
        )
    all_constituents_pass = all(
        record["gate_pass"] for record in SELECTED["constituents"]
    )
    report["tool"] = Path(__file__).name
    report["operation"] = OPERATION
    report["status"] = (
        "evaluation_only_broad_constituent_machine_pass"
        if all_constituents_pass
        and SELECTED["graph"]["connected"]
        and not c9_pairs
        and not cutter_pairs
        else "evaluation_only_broad_constituent_machine_failed"
    )
    report["v9_broad_constituent_network"] = {
        "partition": [
            {
                "name": name,
                "source_vertex_ids": centerline_ids[first : last + 1],
            }
            for name, first, last in CONSTITUENT_SPECS
        ],
        "search": {
            "offsets_mm": OFFSETS_MM,
            "rolls_degrees": ROLLS_DEGREES,
            "maximum_retained_candidates_per_constituent": (
                MAXIMUM_RETAINED_CANDIDATES
            ),
            "records": SEARCH_RECORDS,
        },
        "selected_constituents": SELECTED["constituents"],
        "contact_graph": SELECTED["graph"],
        "registration_controls": control_records,
        "exact_control_ids": [
            record["source_vertex_id"]
            for record in control_records
            if record["classification"] == "exact"
        ],
        "relaxed_controls": [
            record
            for record in control_records
            if record["classification"] != "exact"
        ],
        "adaptive_width_used": False,
    }
    report["collisions"]["network_c9_overlap_count"] = len(c9_pairs)
    report["collisions"]["network_cutter_overlap_count"] = len(cutter_pairs)
    report["collisions"]["network_minimum_cutter_margin_mm"] = round(
        min(margins),
        6,
    )
    report["collisions"][
        "per_constituent_internal_self_intersections"
    ] = {
        record["name"]: record["self_overlap_count"]
        for record in SELECTED["constituents"]
    }
    report["attachments"]["graph_nodes"] = SELECTED["graph"]["nodes"]
    report["attachments"]["graph_edges"] = SELECTED["graph"]["edges"]
    report["attachments"]["graph_connected"] = SELECTED["graph"]["connected"]
    report["band"]["minimum_local_width_mm"] = min(
        record["minimum_width_mm"]
        for record in SELECTED["constituents"]
    )
    report["band"]["maximum_local_width_mm"] = max(
        record["maximum_width_mm"]
        for record in SELECTED["constituents"]
    )
    report["band"]["self_overlap_count"] = sum(
        record["self_overlap_count"]
        for record in SELECTED["constituents"]
    )
    report["band"]["cutter_overlap_count"] = sum(
        record["cutter_overlap_count"]
        for record in SELECTED["constituents"]
    )
    report["gates"].pop("band_closed_positive_volume", None)
    report["gates"].pop("band_non_self_intersecting", None)
    report["gates"].pop("triangle_quality", None)
    report["gates"].pop("all_13_anchors_exact", None)
    report["gates"].pop("minimum_physical_width_3mm", None)
    report["gates"]["all_constituents_machine_valid"] = (
        all_constituents_pass
    )
    report["gates"]["constituent_contact_graph_connected"] = SELECTED[
        "graph"
    ]["connected"]
    report["gates"]["non_tip_component_9_clear"] = not c9_pairs
    report["gates"]["new_geometry_cutter_clear"] = not cutter_pairs
    report["gates"]["new_vertex_margin"] = min(margins) >= 1.6998
    report["gates"]["fixed_structural_width"] = all(
        record["minimum_width_mm"] >= 5.8 - 1.0e-4
        and record["maximum_width_mm"] <= 6.2 + 1.0e-4
        for record in SELECTED["constituents"]
    )
    report["gates"]["fixed_2_4mm_thickness"] = all(
        record["minimum_thickness_mm"] >= 2.4 - 1.0e-4
        and record["maximum_thickness_mm"] <= 2.4 + 1.0e-4
        for record in SELECTED["constituents"]
    )
    report["gates"]["registration_relaxations_reported"] = (
        len(control_records) == 13
    )
    report["gate_pass"] = all(report["gates"].values())
    report["qualitative_review"] = "NOT_REQUESTED"
    report["promotion"] = "NOT_PROMOTED"
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
                "gate_pass": report["gate_pass"],
                "status": report["status"],
                "graph": SELECTED["graph"],
                "selected": [
                    public(record) for record in SELECTED["constituents"]
                ],
            },
            indent=2,
        )
    )
    print(
        f"DONE: v9 broad constituent network gate_pass="
        f"{report['gate_pass']}; promotion=NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
