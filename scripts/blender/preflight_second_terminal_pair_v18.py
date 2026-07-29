"""Read-only bounded preflight for a second Repair 014 terminal pair."""

from __future__ import annotations

from collections import defaultdict
from heapq import heappop, heappush
import json
from math import acos, cos, radians, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_connection_aware_network_v12 as v12  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402


OPERATION = "SECOND_TERMINAL_PAIR_PREFLIGHT_V18"
V13_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_distinct_cage_terminals_v13/build_report.json"
)
MAPPING_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_full_recon_map/mapping.json"
)
BRANCH_A_UPPER = 5702
BRANCH_A_LOWER = 1784
ENDPOINT_EXCLUSION_MM = 6.0
PAD_LONG_MM = 10.0
PAD_SHORT_MM = 7.0
SCARF_CAPACITY_MM = 6.0
SECTION_RADIUS_MM = 3.0
BOUNDARY_TRACK_DISTANCE_MM = 6.0
MIDPOINT_OFFSETS_MM = (0.0, 2.0, 4.0, 6.0, 8.0)
DIRECTION_ANGLES_DEGREES = (0, 180, 210, 240)


def point_segment_distance(point, first, second):
    delta = second - first
    denominator = delta.length_squared
    if denominator <= 1.0e-12:
        return (point - first).length
    factor = max(0.0, min(1.0, (point - first).dot(delta) / denominator))
    return (point - first.lerp(second, factor)).length


def polyline_length(nodes):
    return sum((second - first).length for first, second in zip(nodes, nodes[1:]))


def sampled_nodes(nodes, spacing=1.5):
    return v12.sampled_path(nodes) if spacing == 1.5 else nodes


def boundary_distances(adjacency, points, seeds):
    distances = {vertex: float("inf") for vertex in adjacency}
    queue = []
    for seed in seeds:
        distances[seed] = 0.0
        heappush(queue, (0.0, seed))
    while queue:
        distance, vertex = heappop(queue)
        if distance != distances[vertex]:
            continue
        for neighbor in adjacency[vertex]:
            candidate = distance + (points[vertex] - points[neighbor]).length
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heappush(queue, (candidate, neighbor))
    return distances


def face_normal(points, face):
    origin = points[face[0]]
    result = Vector((0.0, 0.0, 0.0))
    for index in range(1, len(face) - 1):
        result += (points[face[index]] - origin).cross(
            points[face[index + 1]] - origin
        )
    return result


def vertex_measurement(
    source_id,
    terminal_source_ids,
    terminal_face_ids,
    staged_points,
    staged_faces,
    boundary_adjacency,
    geodesic,
    target_length,
):
    incident = [
        face_id
        for face_id in terminal_face_ids
        if source_id in staged_faces[face_id]
    ]
    normal = sum(
        (face_normal(staged_points, staged_faces[face_id]) for face_id in incident),
        Vector((0.0, 0.0, 0.0)),
    )
    if normal.length <= 1.0e-8:
        raise RuntimeError(
            f"{OPERATION}: candidate V{source_id} has no usable terminal normal"
        )
    normal.normalize()
    _, _, _, radial = v4.radial_coordinates(
        staged_points[source_id],
        target_length,
    )
    if normal.dot(radial) < 0.0:
        normal.negate()
    neighbors = sorted(boundary_adjacency[source_id])
    if len(neighbors) >= 2:
        tangent = staged_points[neighbors[-1]] - staged_points[neighbors[0]]
    elif neighbors:
        tangent = staged_points[neighbors[0]] - staged_points[source_id]
    else:
        raise RuntimeError(
            f"{OPERATION}: candidate V{source_id} has no boundary neighbor"
        )
    tangent -= normal * tangent.dot(normal)
    if tangent.length <= 1.0e-8:
        raise RuntimeError(
            f"{OPERATION}: candidate V{source_id} boundary tangent collapsed"
        )
    tangent.normalize()
    transverse = normal.cross(tangent).normalized()
    nearby = [
        staged_points[vertex] - staged_points[source_id]
        for vertex in terminal_source_ids
        if (staged_points[vertex] - staged_points[source_id]).length <= 16.0
    ]
    tangent_values = [vector.dot(tangent) for vector in nearby]
    transverse_values = [vector.dot(transverse) for vector in nearby]
    long_capacity = max(tangent_values) - min(tangent_values)
    short_capacity = max(transverse_values) - min(transverse_values)
    return {
        "source_vertex_id": source_id,
        "coordinate_mm": [
            round(value, 8) for value in staged_points[source_id]
        ],
        "incident_retained_terminal_face_ids": incident,
        "area_weighted_outward_normal": [
            round(value, 8) for value in normal
        ],
        "dominant_open_boundary_neighbors": neighbors,
        "unit_boundary_tangent": [
            round(value, 8) for value in tangent
        ],
        "branch_a_geodesic_distance_mm": round(geodesic[source_id], 6),
        "pad_long_capacity_mm": round(long_capacity, 6),
        "pad_short_capacity_mm": round(short_capacity, 6),
        "scarf_capacity_mm": round(long_capacity, 6),
        "pad_10x7_capacity_gate": (
            long_capacity >= PAD_LONG_MM and short_capacity >= PAD_SHORT_MM
        ),
        "scarf_6mm_capacity_gate": long_capacity >= SCARF_CAPACITY_MM,
        "_normal": normal,
        "_tangent": tangent,
    }


def public_measurement(measurement):
    return {
        key: value
        for key, value in measurement.items()
        if not key.startswith("_")
    }


def route_record(
    nodes,
    route_kind,
    angle_degrees,
    offset_mm,
    upper_id,
    lower_id,
    upper_allowed,
    lower_allowed,
    open_bvh,
    c9_bvh,
    cutter_bvh,
    target_length,
    grid,
    boundary_tree,
    branch_a_first,
    branch_a_second,
):
    route_length = polyline_length(nodes)
    direct_length = (nodes[-1] - nodes[0]).length
    dense = sampled_nodes(nodes)
    minimum_branch_a_distance = min(
        point_segment_distance(point, branch_a_first, branch_a_second)
        for point in dense
    )
    maximum_boundary_distance = max(
        boundary_tree.find(point)[2] for point in dense
    )
    branch_a_crossing = minimum_branch_a_distance < SECTION_RADIUS_MM * 2.0
    outside_aperture = (
        maximum_boundary_distance <= BOUNDARY_TRACK_DISTANCE_MM
    )
    maximum_turn = 0.0
    if len(nodes) == 3:
        first = (nodes[1] - nodes[0]).normalized()
        second = (nodes[2] - nodes[1]).normalized()
        maximum_turn = (
            acos(max(-1.0, min(1.0, first.dot(second))))
            * 180.0
            / 3.141592653589793
        )
    split_used = len(nodes) == 3 and maximum_turn > 45.0
    if branch_a_crossing or not outside_aperture:
        return {
            "route_kind": route_kind,
            "direction_angle_degrees": angle_degrees,
            "midpoint_offset_mm": offset_mm,
            "maximum_turn_degrees": round(maximum_turn, 6),
            "maximum_one_split_used": split_used,
            "straight_gap_mm": round(direct_length, 6),
            "routed_centerline_length_mm": round(route_length, 6),
            "route_direct_length_ratio": round(
                route_length / max(direct_length, 1.0e-8),
                6,
            ),
            "minimum_distance_to_branch_a_mm": round(
                minimum_branch_a_distance,
                6,
            ),
            "maximum_distance_to_dominant_boundary_mm": round(
                maximum_boundary_distance,
                6,
            ),
            "c9_overlap_count": None,
            "cutter_overlap_count": None,
            "minimum_cutter_margin_mm": None,
            "retained_or_unrelated_crossing_count": None,
            "T_CAGE_2_T_CAGE_3_or_unrelated_overlap_count": None,
            "estimated_self_overlap_count": None,
            "outside_dominant_aperture": outside_aperture,
            "branch_a_crossing": branch_a_crossing,
            "collision_metrics_evaluated": False,
            "gate_pass": False,
            "_upper_id": upper_id,
            "_lower_id": lower_id,
        }
    try:
        points, faces, samples, _ = v12.connector_geometry(
            nodes,
            120,
            target_length,
        )
    except RuntimeError:
        return None
    tree = BVHTree.FromPolygons(points, faces, all_triangles=False)
    open_pairs = tree.overlap(open_bvh)
    allowed = upper_allowed | lower_allowed
    unrelated = [pair for pair in open_pairs if pair[1] not in allowed]
    c9_pairs = tree.overlap(c9_bvh)
    cutter_pairs = tree.overlap(cutter_bvh)
    self_pairs = v4.v2.ribbon_self_overlaps(points, faces, len(samples))
    margins = v4.v2.point_margins(points, target_length, grid)
    passed = all(
        (
            not unrelated,
            not c9_pairs,
            not cutter_pairs,
            not self_pairs,
            min(margins) >= 1.6998,
            outside_aperture,
            not branch_a_crossing,
        )
    )
    return {
        "route_kind": route_kind,
        "direction_angle_degrees": angle_degrees,
        "midpoint_offset_mm": offset_mm,
        "maximum_turn_degrees": round(maximum_turn, 6),
        "maximum_one_split_used": split_used,
        "straight_gap_mm": round(direct_length, 6),
        "routed_centerline_length_mm": round(route_length, 6),
        "route_direct_length_ratio": round(
            route_length / max(direct_length, 1.0e-8),
            6,
        ),
        "minimum_distance_to_branch_a_mm": round(
            minimum_branch_a_distance,
            6,
        ),
        "maximum_distance_to_dominant_boundary_mm": round(
            maximum_boundary_distance,
            6,
        ),
        "c9_overlap_count": len(c9_pairs),
        "cutter_overlap_count": len(cutter_pairs),
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "retained_or_unrelated_crossing_count": len(unrelated),
        "T_CAGE_2_T_CAGE_3_or_unrelated_overlap_count": len(unrelated),
        "estimated_self_overlap_count": len(self_pairs),
        "outside_dominant_aperture": outside_aperture,
        "branch_a_crossing": branch_a_crossing,
        "collision_metrics_evaluated": True,
        "gate_pass": passed,
        "_upper_id": upper_id,
        "_lower_id": lower_id,
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    context = v17.baseline_context()
    v13_report = json.loads(V13_REPORT_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    terminals = {
        terminal["terminal_id"]: set(terminal["source_vertex_ids"])
        for terminal in v13_report["terminals"]
    }
    dominant_ids = set(
        mapping["exact_source_open_edges"]["groups"][0]["vertex_ids"]
    )
    upper_ids = sorted(terminals["T_CAGE_1"] & dominant_ids)
    lower_ids = sorted(terminals["T_CAGE_0"] & dominant_ids)
    if (len(upper_ids), len(lower_ids)) != (98, 68):
        raise RuntimeError(
            f"{OPERATION}: resolved candidate counts "
            f"{len(upper_ids)}×{len(lower_ids)}, expected 98×68"
        )
    staged_points = context["staged_points"]
    staged_faces = context["staged_faces"]
    retained_faces = set(context["retained_face_ids"])
    terminal_face_ids = {
        terminal_id: {
            face_id
            for face_id in retained_faces
            if set(staged_faces[face_id]) <= source_ids
        }
        for terminal_id, source_ids in terminals.items()
    }
    boundary_adjacency = defaultdict(set)
    for first, second in mapping["exact_source_open_edges"]["groups"][0][
        "edge_vertex_ids"
    ]:
        boundary_adjacency[first].add(second)
        boundary_adjacency[second].add(first)
    upper_seeds = [
        vertex
        for vertex in upper_ids
        if (staged_points[vertex] - staged_points[BRANCH_A_UPPER]).length
        <= ENDPOINT_EXCLUSION_MM
    ]
    lower_seeds = [
        vertex
        for vertex in lower_ids
        if (staged_points[vertex] - staged_points[BRANCH_A_LOWER]).length
        <= ENDPOINT_EXCLUSION_MM
    ]
    upper_geodesic = boundary_distances(
        boundary_adjacency,
        staged_points,
        upper_seeds,
    )
    lower_geodesic = boundary_distances(
        boundary_adjacency,
        staged_points,
        lower_seeds,
    )
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    upper_measurements = {
        source_id: vertex_measurement(
            source_id,
            terminals["T_CAGE_1"],
            terminal_face_ids["T_CAGE_1"],
            staged_points,
            staged_faces,
            boundary_adjacency,
            upper_geodesic,
            target_length,
        )
        for source_id in upper_ids
    }
    lower_measurements = {
        source_id: vertex_measurement(
            source_id,
            terminals["T_CAGE_0"],
            terminal_face_ids["T_CAGE_0"],
            staged_points,
            staged_faces,
            boundary_adjacency,
            lower_geodesic,
            target_length,
        )
        for source_id in lower_ids
    }
    branch_a_first = staged_points[BRANCH_A_UPPER]
    branch_a_second = staged_points[BRANCH_A_LOWER]
    branch_a_midpoint = branch_a_first.lerp(branch_a_second, 0.5)
    removed = set(
        mapping["reconstruction_scope"]["rebuild_face_ids"]
    )
    open_face_by_source = {
        source_face_id: open_face_id
        for open_face_id, source_face_id in enumerate(
            face_id
            for face_id in range(len(staged_faces))
            if face_id not in removed
        )
    }
    landing_faces = {}
    for source_id in [*upper_ids, *lower_ids]:
        terminal_id = (
            "T_CAGE_1" if source_id in upper_measurements else "T_CAGE_0"
        )
        landing_faces[source_id] = {
            open_face_by_source[face_id]
            for face_id in terminal_face_ids[terminal_id]
            if any(
                (staged_points[vertex] - staged_points[source_id]).length
                <= ENDPOINT_EXCLUSION_MM
                for vertex in staged_faces[face_id]
            )
        }
    open_bvh = BVHTree.FromPolygons(
        context["open_points"],
        context["open_faces"],
        all_triangles=False,
    )
    c9_bvh = BVHTree.FromPolygons(
        context["c9_points"],
        context["c9_faces"],
        all_triangles=False,
    )
    cutter_bvh = BVHTree.FromPolygons(
        context["cutter_points"],
        context["cutter_faces"],
        all_triangles=False,
    )
    grid, _ = v4.cutter_grid(context["cutter"])
    boundary_tree = KDTree(len(dominant_ids))
    for insertion_index, source_id in enumerate(sorted(dominant_ids)):
        boundary_tree.insert(staged_points[source_id], insertion_index)
    boundary_tree.balance()
    staged_rejection_counts = defaultdict(int)
    staged_eligible_pair_count = 0
    for upper_id in upper_ids:
        upper = upper_measurements[upper_id]
        upper_point = staged_points[upper_id]
        for lower_id in lower_ids:
            lower = lower_measurements[lower_id]
            lower_point = staged_points[lower_id]
            midpoint = upper_point.lerp(lower_point, 0.5)
            reasons = []
            if (upper_point - branch_a_first).length < ENDPOINT_EXCLUSION_MM:
                reasons.append("upper_endpoint_exclusion")
            if (lower_point - branch_a_second).length < ENDPOINT_EXCLUSION_MM:
                reasons.append("lower_endpoint_exclusion")
            if (midpoint - branch_a_midpoint).length <= ENDPOINT_EXCLUSION_MM:
                reasons.append("midpoint_not_beyond_footprint_containment")
            if not upper["pad_10x7_capacity_gate"]:
                reasons.append("upper_pad_10x7_capacity")
            if not lower["pad_10x7_capacity_gate"]:
                reasons.append("lower_pad_10x7_capacity")
            if not upper["scarf_6mm_capacity_gate"]:
                reasons.append("upper_scarf_capacity")
            if not lower["scarf_6mm_capacity_gate"]:
                reasons.append("lower_scarf_capacity")
            if reasons:
                for reason in reasons:
                    staged_rejection_counts[reason] += 1
            else:
                staged_eligible_pair_count += 1
    staging_path = report_path.with_name("preflight_staging.json")
    staging_path.write_text(
        json.dumps(
            {
                "operation": OPERATION,
                "status": "ENDPOINT_AND_CAPACITY_STAGING_COMPLETE",
                "upper_source_vertex_ids": upper_ids,
                "lower_source_vertex_ids": lower_ids,
                "pair_count": len(upper_ids) * len(lower_ids),
                "route_eligible_pair_count": staged_eligible_pair_count,
                "staged_rejection_counts": dict(
                    sorted(staged_rejection_counts.items())
                ),
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    pair_records = []
    feasible = []
    rejection_counts = defaultdict(int)
    for upper_id in upper_ids:
        upper = upper_measurements[upper_id]
        upper_point = staged_points[upper_id]
        for lower_id in lower_ids:
            lower = lower_measurements[lower_id]
            lower_point = staged_points[lower_id]
            midpoint = upper_point.lerp(lower_point, 0.5)
            midpoint_separation = (midpoint - branch_a_midpoint).length
            reasons = []
            if (upper_point - branch_a_first).length < ENDPOINT_EXCLUSION_MM:
                reasons.append("upper_endpoint_exclusion")
            if (lower_point - branch_a_second).length < ENDPOINT_EXCLUSION_MM:
                reasons.append("lower_endpoint_exclusion")
            if midpoint_separation <= ENDPOINT_EXCLUSION_MM:
                reasons.append("midpoint_not_beyond_footprint_containment")
            if not upper["pad_10x7_capacity_gate"]:
                reasons.append("upper_pad_10x7_capacity")
            if not lower["pad_10x7_capacity_gate"]:
                reasons.append("lower_pad_10x7_capacity")
            if not upper["scarf_6mm_capacity_gate"]:
                reasons.append("upper_scarf_capacity")
            if not lower["scarf_6mm_capacity_gate"]:
                reasons.append("lower_scarf_capacity")
            base = {
                "upper_source_vertex_id": upper_id,
                "lower_source_vertex_id": lower_id,
                "straight_gap_mm": round((lower_point - upper_point).length, 6),
                "midpoint_separation_from_branch_a_mm": round(
                    midpoint_separation,
                    6,
                ),
                "minimum_endpoint_geodesic_separation_mm": round(
                    min(
                        upper["branch_a_geodesic_distance_mm"],
                        lower["branch_a_geodesic_distance_mm"],
                    ),
                    6,
                ),
            }
            if reasons:
                for reason in reasons:
                    rejection_counts[reason] += 1
                pair_records.append(
                    {
                        **base,
                        "status": "REJECTED_BEFORE_ROUTE",
                        "reasons": reasons,
                        "selected_route": None,
                    }
                )
                continue
            direction = lower_point - upper_point
            direction.normalize()
            midpoint_normal = (
                upper["_normal"] + lower["_normal"]
            )
            midpoint_normal -= direction * midpoint_normal.dot(direction)
            if midpoint_normal.length <= 1.0e-8:
                midpoint_normal = upper["_tangent"] - direction * upper[
                    "_tangent"
                ].dot(direction)
            midpoint_normal.normalize()
            second_axis = direction.cross(midpoint_normal).normalized()
            route_attempts = []
            for offset in MIDPOINT_OFFSETS_MM:
                angles = (0,) if offset == 0.0 else DIRECTION_ANGLES_DEGREES
                for angle_degrees in angles:
                    if offset == 0.0:
                        nodes = [upper_point, lower_point]
                        route_kind = "direct"
                    else:
                        angle = radians(angle_degrees)
                        displacement = (
                            midpoint_normal * cos(angle)
                            + second_axis * sin(angle)
                        ) * offset
                        nodes = [
                            upper_point,
                            midpoint + displacement,
                            lower_point,
                        ]
                        route_kind = "one_bend"
                    record = route_record(
                        nodes,
                        route_kind,
                        angle_degrees,
                        offset,
                        upper_id,
                        lower_id,
                        landing_faces[upper_id],
                        landing_faces[lower_id],
                        open_bvh,
                        c9_bvh,
                        cutter_bvh,
                        target_length,
                        grid,
                        boundary_tree,
                        branch_a_first,
                        branch_a_second,
                    )
                    if record:
                        route_attempts.append(record)
            passing_routes = [
                record for record in route_attempts if record["gate_pass"]
            ]
            selected_route = (
                min(
                    passing_routes,
                    key=lambda record: (
                        record["routed_centerline_length_mm"],
                        record["route_direct_length_ratio"],
                        record["route_kind"],
                        record["midpoint_offset_mm"],
                        record["direction_angle_degrees"],
                    ),
                )
                if passing_routes
                else None
            )
            if selected_route is None:
                rejection_counts["no_bounded_route_passed"] += 1
                best_failed_route = min(
                    route_attempts,
                    key=lambda record: (
                        not record["outside_dominant_aperture"],
                        record["branch_a_crossing"],
                        (
                            record["T_CAGE_2_T_CAGE_3_or_unrelated_overlap_count"]
                            if record[
                                "T_CAGE_2_T_CAGE_3_or_unrelated_overlap_count"
                            ]
                            is not None
                            else 10**9
                        ),
                        (
                            record["c9_overlap_count"]
                            if record["c9_overlap_count"] is not None
                            else 10**9
                        ),
                        (
                            record["cutter_overlap_count"]
                            if record["cutter_overlap_count"] is not None
                            else 10**9
                        ),
                        (
                            record["estimated_self_overlap_count"]
                            if record["estimated_self_overlap_count"] is not None
                            else 10**9
                        ),
                        -(
                            record["minimum_cutter_margin_mm"]
                            if record["minimum_cutter_margin_mm"] is not None
                            else -10**9
                        ),
                        record["routed_centerline_length_mm"],
                        record["route_direct_length_ratio"],
                        record["route_kind"],
                        record["midpoint_offset_mm"],
                        record["direction_angle_degrees"],
                    ),
                )
                pair_records.append(
                    {
                        **base,
                        "status": "REJECTED_NO_ROUTE",
                        "reasons": ["no_bounded_route_passed"],
                        "route_attempt_count": len(route_attempts),
                        "selected_route": None,
                        "best_failed_route": {
                            key: value
                            for key, value in best_failed_route.items()
                            if not key.startswith("_")
                        },
                    }
                )
                continue
            record = {
                **base,
                "status": "FEASIBLE",
                "reasons": [],
                "route_attempt_count": len(route_attempts),
                "selected_route": {
                    key: value
                    for key, value in selected_route.items()
                    if not key.startswith("_")
                },
            }
            pair_records.append(record)
            feasible.append(record)
        progress_path = report_path.with_name("preflight_progress.json")
        progress_path.write_text(
            json.dumps(
                {
                    "operation": OPERATION,
                    "status": "ROUTE_PREFIX_CHECKPOINT",
                    "completed_upper_source_vertex_ids": upper_ids[
                        : upper_ids.index(upper_id) + 1
                    ],
                    "completed_pair_count": len(pair_records),
                    "feasible_pair_count": len(feasible),
                    "rejection_counts": dict(sorted(rejection_counts.items())),
                    "pair_records": pair_records,
                    "geometry_emitted": False,
                    "blend_saved": False,
                },
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
    feasible.sort(
        key=lambda record: (
            -record["midpoint_separation_from_branch_a_mm"],
            -record["minimum_endpoint_geodesic_separation_mm"],
            -record["selected_route"]["minimum_cutter_margin_mm"],
            record["selected_route"]["routed_centerline_length_mm"],
            record["selected_route"]["route_direct_length_ratio"],
            record["upper_source_vertex_id"],
            record["lower_source_vertex_id"],
        )
    )
    selected = feasible[0] if feasible else None
    separations = sorted(
        record["midpoint_separation_from_branch_a_mm"]
        for record in feasible
    )
    quartile_threshold = (
        separations[int(0.75 * (len(separations) - 1))]
        if separations
        else None
    )
    farthest_quartile_gate = bool(
        selected
        and selected["midpoint_separation_from_branch_a_mm"]
        >= quartile_threshold
    )
    status = (
        "FEASIBLE_SECOND_TERMINAL_PAIR_SELECTED"
        if selected and farthest_quartile_gate
        else "NO_FEASIBLE_SECOND_TERMINAL_PAIR"
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "read_only": True,
        "geometry_emitted": False,
        "blend_saved": False,
        "authorities": {
            "v13_report": str(V13_REPORT_PATH),
            "mapping": str(MAPPING_PATH),
            "baseline_checks": context["checks"],
        },
        "candidate_universe": {
            "definition": {
                "dominant_open_group": (
                    "mapping.json $.exact_source_open_edges.groups[0].vertex_ids"
                ),
                "upper": (
                    "v13/build_report.json T_CAGE_1 $.source_vertex_ids "
                    "INTERSECT dominant_open_group"
                ),
                "lower": (
                    "v13/build_report.json T_CAGE_0 $.source_vertex_ids "
                    "INTERSECT dominant_open_group"
                ),
            },
            "upper_source_vertex_ids": upper_ids,
            "lower_source_vertex_ids": lower_ids,
            "upper_count": len(upper_ids),
            "lower_count": len(lower_ids),
            "pair_count": len(pair_records),
            "V5702_in_upper": BRANCH_A_UPPER in upper_ids,
            "V1784_in_lower": BRANCH_A_LOWER in lower_ids,
        },
        "branch_a": {
            "upper_source_vertex_id": BRANCH_A_UPPER,
            "lower_source_vertex_id": BRANCH_A_LOWER,
            "midpoint_mm": [round(value, 8) for value in branch_a_midpoint],
            "endpoint_exclusion_mm": ENDPOINT_EXCLUSION_MM,
        },
        "candidate_measurements": {
            "upper": [
                public_measurement(upper_measurements[source_id])
                for source_id in upper_ids
            ],
            "lower": [
                public_measurement(lower_measurements[source_id])
                for source_id in lower_ids
            ],
        },
        "bounded_route_search": {
            "section_width_range_mm": [4.5, 6.0],
            "section_thickness_mm": 2.4,
            "direction_angles_degrees": list(DIRECTION_ANGLES_DEGREES),
            "midpoint_offsets_mm": list(MIDPOINT_OFFSETS_MM),
            "maximum_bends": 1,
            "maximum_route_pieces": 2,
            "pair_records": pair_records,
        },
        "results": {
            "evaluated_pair_count": len(pair_records),
            "feasible_pair_count": len(feasible),
            "rejection_counts": dict(sorted(rejection_counts.items())),
            "farthest_quartile_midpoint_separation_threshold_mm": (
                round(quartile_threshold, 6)
                if quartile_threshold is not None
                else None
            ),
            "selected_pair": selected,
            "selected_pair_farthest_quartile_gate": farthest_quartile_gate,
        },
        "gate_pass": bool(selected and farthest_quartile_gate),
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "evaluated_pair_count": len(pair_records),
                "feasible_pair_count": len(feasible),
                "selected_pair": selected,
                "geometry_emitted": False,
                "blend_saved": False,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v18 second-terminal-pair preflight status={status}; "
        "geometry_emitted=False; blend_saved=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
