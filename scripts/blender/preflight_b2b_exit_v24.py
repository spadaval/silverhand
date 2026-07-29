"""Read-only exact-ring and bounded-terminal B2b exit preflight for v24."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from heapq import heappop, heappush
import json
from math import radians
from pathlib import Path
import sys

from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_joint_c9_c20_elbow_v22 as v22  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import preflight_free_space_lower_route_v23 as v23  # noqa: E402


OPERATION = "BOUNDED_B2B_EXIT_V24"
NO_TRIM = "NO_SAFE_B2B_RING_TRIM_V24"
NO_REAUTHOR = "NO_SAFE_B2B_TERMINAL_REAUTHOR_V24"
TRIM_RINGS = (8, 7, 6, 5)
ANCHOR_RINGS = (5, 6, 7)
DEFLECTIONS = (0, -15, 15, -30, 30, -45, 45)
ROLLS = (0, -15, 15, -30, 30, -45, 45, -60, 60)
WIDTHS = (6.0, 5.25, 4.5)
ADVANCES = (4.0, 8.0, 12.0)
OFFSETS = (-8.0, -4.0, 0.0, 4.0, 8.0)


def stable_hash(value):
    return sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def nearest_distance(points, tree):
    return min(
        tree.find_nearest(point)[3]
        for point in points
        if tree.find_nearest(point) is not None
    )


def b2b_authority(context, corridor):
    record = corridor["core"]["B2b"]
    samples = record["_samples"]
    points = record["_points"]
    faces = record["_faces"]
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(
        samples,
        tangents,
        corridor["target_length"],
    )
    c9_tree = BVHTree.FromPolygons(
        context["c9_points"],
        context["c9_faces"],
        all_triangles=False,
    )
    cumulative = [0.0]
    for first, second in zip(samples, samples[1:]):
        cumulative.append(cumulative[-1] + (second - first).length)
    margins = v4.v2.point_margins(
        points,
        corridor["target_length"],
        corridor["grid"],
    )
    turn_pairs = v14.overlap_pairs(
        points,
        faces,
        corridor["turn"]["_points"],
        corridor["turn"]["_faces"],
    )
    rings = []
    for ring_index, (center, tangent, frame) in enumerate(
        zip(samples, tangents, frames)
    ):
        width_axis, normal = v8.rotated_frame(
            frame[0],
            tangent,
            record["roll_degrees"],
        )
        ring_points = points[ring_index * 5 : ring_index * 5 + 5]
        related_faces = [
            {
                "local_face_id": face_id,
                "loop": list(face),
                "material_index": 0,
            }
            for face_id, face in enumerate(faces)
            if any(
                ring_index * 5 <= vertex < ring_index * 5 + 5
                for vertex in face
            )
        ]
        rings.append(
            {
                "ring_id": f"R{ring_index}",
                "center_id": f"P{ring_index}",
                "center_mm": [float(value) for value in center],
                "ordered_ring_vertices_mm": [
                    [float(value) for value in point]
                    for point in ring_points
                ],
                "tangent": [float(value) for value in tangent],
                "parallel_transport_normal": [
                    float(value) for value in normal
                ],
                "parallel_transport_binormal": [
                    float(value) for value in width_axis
                ],
                "roll_degrees": record["roll_degrees"],
                "cumulative_arclength_mm": round(cumulative[ring_index], 6),
                "remaining_arclength_mm": round(
                    cumulative[-1] - cumulative[ring_index],
                    6,
                ),
                "section_width_mm": round(
                    (ring_points[4] - ring_points[0]).length,
                    6,
                ),
                "section_thickness_mm": round(
                    (ring_points[1] - ring_points[0]).length,
                    6,
                ),
                "related_face_records": related_faces,
                "minimum_ring_cutter_margin_mm": round(
                    min(
                        margins[
                            ring_index * 5 : ring_index * 5 + 5
                        ]
                    ),
                    6,
                ),
                "minimum_ring_c9_distance_mm": round(
                    nearest_distance(ring_points, c9_tree),
                    6,
                ),
                "turn_bridge_overlap_pairs": [
                    list(pair)
                    for pair in turn_pairs
                    if pair[0] in {
                        face_record["local_face_id"]
                        for face_record in related_faces
                    }
                ],
            }
        )
    start_cap = [
        {"face_id": index, "loop": list(face)}
        for index, face in enumerate(faces)
        if all(vertex < 5 for vertex in face)
    ]
    end_cap = [
        {"face_id": index, "loop": list(face)}
        for index, face in enumerate(faces)
        if all(vertex >= 45 for vertex in face)
    ]
    fingerprints = {
        "B2b": stable_hash(
            {
                "points": [[float(value) for value in point] for point in points],
                "faces": [list(face) for face in faces],
            }
        ),
        "turn_bridge": stable_hash(public(corridor["turn"])),
        "B0_B1_B2a": stable_hash(
            {
                name: public(corridor["core"][name])
                for name in ("B0", "B1", "B2a")
            }
        ),
    }
    result = {
        "operation": OPERATION,
        "status": "B2B_RING_AUTHORITY_CHECKPOINTED",
        "B2B_CENTERLINE": [
            [float(value) for value in sample] for sample in samples
        ],
        "B2B_RINGS": rings,
        "face_count": len(faces),
        "vertex_count": len(points),
        "faces": [
            {
                "local_face_id": face_id,
                "loop": list(face),
                "material_index": 0,
            }
            for face_id, face in enumerate(faces)
        ],
        "original_start_cap": start_cap,
        "original_end_cap": end_cap,
        "turn_bridge_overlap_pairs": [list(pair) for pair in turn_pairs],
        "minimum_cutter_margin_mm": record["minimum_cutter_margin_mm"],
        "fingerprints": fingerprints,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    return result


def prefix_record(authority, ring_index):
    point_limit = ring_index * 5
    face_ids = [
        record["local_face_id"]
        for record in authority["faces"]
        if max(record["loop"]) < point_limit
    ]
    vertex_ids = list(range(point_limit))
    payload = {
        "ring_ids": [f"R{index}" for index in range(ring_index)],
        "vertex_ids": vertex_ids,
        "coordinates_mm": [
            coordinate
            for ring in authority["B2B_RINGS"][:ring_index]
            for coordinate in ring["ordered_ring_vertices_mm"]
        ],
        "face_ids": face_ids,
        "faces": [
            authority["faces"][face_id] for face_id in face_ids
        ],
    }
    return {**payload, "fingerprint": stable_hash(payload)}


def scarf_samples(samples, portal_index):
    selected = [samples[portal_index].copy()]
    distance = 0.0
    for index in range(portal_index, 0, -1):
        segment = (samples[index] - samples[index - 1]).length
        if distance + segment >= 6.0:
            remaining = 6.0 - distance
            selected.append(
                samples[index].lerp(
                    samples[index - 1],
                    remaining / segment,
                )
            )
            break
        selected.append(samples[index - 1].copy())
        distance += segment
    selected.reverse()
    return selected


def combined_deflection(tangent, normal, binormal, first, second):
    result = Quaternion(normal, radians(first)) @ tangent
    result = Quaternion(binormal, radians(second)) @ result
    angle = v23.turn_degrees(tangent, result)
    return result.normalized(), angle


def local_portal_records(
    ring_index,
    authority,
    corridor,
    obstacles,
    context,
):
    ring = authority["B2B_RINGS"][ring_index]
    center = Vector(ring["center_mm"])
    tangent = Vector(ring["tangent"])
    normal = Vector(ring["parallel_transport_normal"])
    binormal = Vector(ring["parallel_transport_binormal"])
    records = []
    for first in DEFLECTIONS:
        for second in DEFLECTIONS:
            departure, magnitude = combined_deflection(
                tangent,
                normal,
                binormal,
                first,
                second,
            )
            if magnitude > 45.0 + 1.0e-6:
                continue
            for roll in ROLLS:
                end = center + departure * 2.0
                gate, reason = v23.segment_gate(
                    center,
                    end,
                    roll,
                    6.0,
                    obstacles,
                    corridor,
                )
                ring_points = v23.ring_points(
                    end,
                    departure,
                    roll,
                    6.0,
                    corridor["target_length"],
                )
                margin = min(
                    v4.v2.point_margins(
                        ring_points,
                        corridor["target_length"],
                        corridor["grid"],
                    )
                )
                records.append(
                    {
                        "portal_tuple_id": (
                            f"R{ring_index}_N{first:+03d}_"
                            f"B{second:+03d}_R{roll:+03d}"
                        ),
                        "normal_deflection_degrees": first,
                        "binormal_deflection_degrees": second,
                        "combined_deflection_degrees": round(magnitude, 6),
                        "roll_degrees": roll,
                        "portal_center_mm": list(center),
                        "departure_tangent": list(departure),
                        "forward_test_end_mm": list(end),
                        "minimum_cutter_margin_mm": round(margin, 6),
                        "local_gate_pass": gate,
                        "rejection_reason": reason,
                        "_departure": departure,
                    }
                )
    return records


def route_from_portal(
    candidate_id,
    center,
    departure,
    roll,
    corridor,
    obstacles,
    context,
):
    endpoints = [
        record
        for record in v23.endpoint_candidates(context)
        if record["accepted"]
    ]
    search_records = []
    exact_records = []
    for endpoint in endpoints:
        end = Vector(endpoint["coordinate_mm"])
        nodes, frame = v23.lattice_nodes(center, end, Vector((0, 0, 1)))
        toward = Vector((-0.451645434, 0.836417615, -0.310518861))
        if toward.dot(center - end) < 0:
            toward.negate()
        arrival = -toward.normalized()
        for width in WIDTHS:
            route_id = f"{candidate_id}_{endpoint['endpoint_id']}_W{width:.2f}"
            polyline, metrics = cached_constant_roll_astar(
                nodes,
                center,
                end,
                departure,
                arrival,
                roll,
                width,
                obstacles,
                corridor,
            )
            search = {
                "route_id": route_id,
                "endpoint_id": endpoint["endpoint_id"],
                "width_mm": width,
                "search_frame": frame,
                **metrics,
                "polyline_found": polyline is not None,
            }
            if polyline:
                spline = v23.fit_spline(polyline["points"])
                exact = v23.exact_collision_record(
                    route_id,
                    spline,
                    polyline["rolls"],
                    width,
                    obstacles,
                    context,
                    corridor,
                )
                exact_records.append(exact)
                search["exact_spline"] = public(exact)
            search_records.append(search)
    return search_records, exact_records


def cached_constant_roll_astar(
    nodes,
    start,
    end,
    start_tangent,
    end_tangent,
    roll,
    width,
    obstacles,
    corridor,
):
    edge_cache = {}

    def edge_gate(first_key, second_key, first, second):
        cache_key = tuple(sorted((first_key, second_key)))
        if cache_key not in edge_cache:
            edge_cache[cache_key] = v23.segment_gate(
                first,
                second,
                roll,
                width,
                obstacles,
                corridor,
            )
        return edge_cache[cache_key]

    queue = []
    best = {}
    parent = {}
    serial = 0
    rejections = Counter()
    for key, point in nodes.items():
        delta = point - start
        if not 2.0 <= delta.length <= 7.0:
            continue
        if v23.turn_degrees(start_tangent, delta) > 45.0:
            continue
        gate, reason = v23.segment_gate(
            start,
            point,
            roll,
            width,
            obstacles,
            corridor,
        )
        if not gate:
            rejections[f"initial_{reason}"] += 1
            continue
        direction = tuple(
            round(value, 6) for value in delta.normalized()
        )
        state = (key, direction)
        cost = delta.length
        best[state] = cost
        parent[state] = None
        heappush(queue, (cost + (end - point).length, serial, state))
        serial += 1
    goal = None
    while queue:
        _, _, state = heappop(queue)
        key, incoming_values = state
        current = nodes[key]
        incoming = Vector(incoming_values)
        cost = best[state]
        end_delta = end - current
        if (
            2.0 <= end_delta.length <= 7.0
            and v23.turn_degrees(incoming, end_delta) <= 45.0
            and v23.turn_degrees(end_delta, end_tangent) <= 45.0
        ):
            gate, reason = v23.segment_gate(
                current,
                end,
                roll,
                width,
                obstacles,
                corridor,
            )
            if gate:
                goal = state
                break
            rejections[reason] += 1
        li, ai, bi = key
        for offset in v23.NEIGHBORS:
            following_key = (
                li + offset[0],
                ai + offset[1],
                bi + offset[2],
            )
            if following_key not in nodes:
                continue
            following = nodes[following_key]
            outgoing = following - current
            if v23.turn_degrees(incoming, outgoing) > 45.0:
                continue
            gate, reason = edge_gate(
                key,
                following_key,
                current,
                following,
            )
            if not gate:
                rejections[reason] += 1
                continue
            direction = tuple(
                round(value, 6) for value in outgoing.normalized()
            )
            following_state = (following_key, direction)
            following_cost = cost + outgoing.length
            if following_cost >= best.get(following_state, float("inf")):
                continue
            best[following_state] = following_cost
            parent[following_state] = state
            heappush(
                queue,
                (
                    following_cost + (end - following).length,
                    serial,
                    following_state,
                ),
            )
            serial += 1
    if goal is None:
        return None, {
            "expanded_state_count": len(best),
            "edge_rejection_counts": dict(sorted(rejections.items())),
            "roll_evolution": "constant portal roll (0 change per 4 mm)",
        }
    states = []
    current = goal
    while current is not None:
        states.append(current)
        current = parent[current]
    states.reverse()
    points = [start, *[nodes[state[0]] for state in states], end]
    return {
        "points": points,
        "rolls": [roll] * len(points),
        "length_mm": sum(
            (second - first).length
            for first, second in zip(points, points[1:])
        ),
    }, {
        "expanded_state_count": len(best),
        "edge_rejection_counts": dict(sorted(rejections.items())),
        "roll_evolution": "constant portal roll (0 change per 4 mm)",
    }


def trim_candidates(authority, corridor, obstacles, context, progress_path):
    if progress_path.is_file():
        recovered = json.loads(progress_path.read_text(encoding="utf-8"))
        recovered_records = recovered.get("completed_candidates", [])
        if [record.get("candidate_id") for record in recovered_records] == [
            f"TRIM_R{ring}" for ring in TRIM_RINGS
        ]:
            return recovered_records, [
                route
                for record in recovered_records
                for route in record.get("route_records", [])
            ]
    samples = corridor["core"]["B2b"]["_samples"]
    faces = corridor["core"]["B2b"]["_faces"]
    records = []
    route_records = []
    for ring_index in TRIM_RINGS:
        prefix = prefix_record(authority, ring_index)
        retained_point_limit = (ring_index + 1) * 5
        retained_faces = [
            face_id
            for face_id, face in enumerate(faces)
            if max(face) < retained_point_limit
        ]
        removed_faces = sorted(set(range(len(faces))) - set(retained_faces))
        removed_vertices = list(range(retained_point_limit, 50))
        scarf = scarf_samples(samples, ring_index)
        scarf_length = sum(
            (second - first).length
            for first, second in zip(scarf, scarf[1:])
        )
        local = local_portal_records(
            ring_index,
            authority,
            corridor,
            obstacles,
            context,
        )
        passing = [record for record in local if record["local_gate_pass"]]
        selected_portal = (
            min(
                passing,
                key=lambda record: (
                    record["combined_deflection_degrees"],
                    abs(record["roll_degrees"]),
                    -record["minimum_cutter_margin_mm"],
                    record["portal_tuple_id"],
                ),
            )
            if passing
            else None
        )
        candidate_routes = []
        candidate_exact = []
        if selected_portal:
            candidate_routes, candidate_exact = route_from_portal(
                f"TRIM_R{ring_index}",
                Vector(selected_portal["portal_center_mm"]),
                selected_portal["_departure"],
                selected_portal["roll_degrees"],
                corridor,
                obstacles,
                context,
            )
            route_records.extend(candidate_routes)
        complete = [
            record for record in candidate_exact if record["gate_pass"]
        ]
        records.append(
            {
                "candidate_id": f"TRIM_R{ring_index}",
                "last_retained_ring": ring_index,
                "trim_distance_mm": authority["B2B_RINGS"][ring_index][
                    "remaining_arclength_mm"
                ],
                "immutable_prefix": prefix,
                "retained_face_ids": retained_faces,
                "removed_suffix_face_ids": removed_faces,
                "removed_suffix_vertex_ids": removed_vertices,
                "hidden_planar_cap_loop": list(
                    range(ring_index * 5, ring_index * 5 + 5)
                ),
                "scarf_centerline_points_mm": [list(point) for point in scarf],
                "scarf_length_mm": round(scarf_length, 6),
                "scarf_station_interval_mm": [
                    round(
                        authority["B2B_RINGS"][ring_index][
                            "cumulative_arclength_mm"
                        ]
                        - scarf_length,
                        6,
                    ),
                    authority["B2B_RINGS"][ring_index][
                        "cumulative_arclength_mm"
                    ],
                ],
                "turn_bridge_overlap_unchanged": not any(
                    pair[0] in removed_faces
                    for pair in authority["turn_bridge_overlap_pairs"]
                ),
                "portal_records": [public(record) for record in local],
                "selected_local_portal": (
                    public(selected_portal) if selected_portal else None
                ),
                "route_records": candidate_routes,
                "exact_spline_records": [
                    public(record) for record in candidate_exact
                ],
                "complete_route_count": len(complete),
                "gate_pass": bool(complete),
                "rejection_reason": (
                    None
                    if complete
                    else "no_complete_v23_route_from_trim_portal"
                    if selected_portal
                    else "no_local_2mm_portal_tuple_passed"
                ),
            }
        )
        progress_path.write_text(
            json.dumps(
                {
                    "operation": OPERATION,
                    "status": "TRIM_PREFIX_CHECKPOINT",
                    "completed_candidates": records,
                    "mutation_started": False,
                    "geometry_emitted": False,
                    "blend_saved": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return records, route_records


def terminal_candidates(
    authority,
    corridor,
    obstacles,
    context,
    terminal_progress_path,
):
    samples = corridor["core"]["B2b"]["_samples"]
    if terminal_progress_path.is_file():
        recovered = json.loads(
            terminal_progress_path.read_text(encoding="utf-8")
        )
        records = [
            record
            for record in recovered.get("completed_candidates", [])
            if record.get("checkpoint_status") == "COMPLETE"
        ]
        route_records = recovered.get("route_records", [])
    else:
        records = []
        route_records = []
    completed_ids = {
        record["candidate_id"]
        for record in records
        if record.get("checkpoint_status") == "COMPLETE"
    }

    def checkpoint(status, current_candidate):
        temporary_path = terminal_progress_path.with_suffix(
            terminal_progress_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            json.dumps(
                {
                    "operation": OPERATION,
                    "status": status,
                    "current_candidate_id": current_candidate,
                    "completed_candidate_ids": sorted(completed_ids),
                    "completed_candidates": records,
                    "route_records": route_records,
                    "mutation_started": False,
                    "geometry_emitted": False,
                    "blend_saved": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(terminal_progress_path)

    for anchor in ANCHOR_RINGS:
        ring = authority["B2B_RINGS"][anchor]
        center = Vector(ring["center_mm"])
        tangent = Vector(ring["tangent"])
        normal = Vector(ring["parallel_transport_normal"])
        binormal = Vector(ring["parallel_transport_binormal"])
        suffix = samples[anchor:]
        for advance in ADVANCES:
            for normal_offset in OFFSETS:
                for binormal_offset in OFFSETS:
                    endpoint = (
                        center
                        + tangent * advance
                        + normal * normal_offset
                        + binormal * binormal_offset
                    )
                    suffix_distance = min(
                        (endpoint - point).length for point in suffix
                    )
                    for width in WIDTHS:
                        candidate_id = (
                            f"REAUTHOR_R{anchor}_A{advance:.0f}_"
                            f"N{normal_offset:+.0f}_B{binormal_offset:+.0f}_"
                            f"W{width:.2f}"
                        )
                        if candidate_id in completed_ids:
                            continue
                        points = [
                            center,
                            center + tangent * min(4.0, advance * 0.5),
                            endpoint,
                        ]
                        length = sum(
                            (second - first).length
                            for first, second in zip(points, points[1:])
                        )
                        local_gate = all(
                            (
                                6.0 <= length <= 16.0,
                                suffix_distance <= 8.0,
                            )
                        )
                        rejection = None
                        if not local_gate:
                            rejection = "length_or_suffix_distance_bound"
                        else:
                            for first, second in zip(points, points[1:]):
                                gate, reason = v23.segment_gate(
                                    first,
                                    second,
                                    0,
                                    width,
                                    obstacles,
                                    corridor,
                                )
                                if not gate:
                                    local_gate = False
                                    rejection = reason
                                    break
                        base_record = {
                            "candidate_id": candidate_id,
                            "anchor_ring": anchor,
                            "immutable_prefix": prefix_record(
                                authority,
                                anchor,
                            ),
                            "advance_mm": advance,
                            "normal_offset_mm": normal_offset,
                            "binormal_offset_mm": binormal_offset,
                            "width_mm": width,
                            "thickness_mm": 2.4,
                            "centerline_points_mm": [
                                list(point) for point in points
                            ],
                            "centerline_length_mm": round(length, 6),
                            "minimum_original_suffix_distance_mm": round(
                                suffix_distance,
                                6,
                            ),
                            "local_gate_pass": local_gate,
                            "local_rejection_reason": rejection,
                            "route_records": [],
                            "exact_spline_records": [],
                            "complete_route_count": 0,
                            "gate_pass": False,
                            "checkpoint_status": (
                                "ROUTE_PENDING"
                                if local_gate
                                else "COMPLETE"
                            ),
                        }
                        records.append(base_record)
                        checkpoint(
                            (
                                "TERMINAL_ROUTE_PENDING"
                                if local_gate
                                else "TERMINAL_CANDIDATE_COMPLETE"
                            ),
                            candidate_id,
                        )
                        candidate_routes = []
                        exact = []
                        if local_gate:
                            departure = (endpoint - points[-2]).normalized()
                            candidate_routes, exact = route_from_portal(
                                candidate_id,
                                endpoint,
                                departure,
                                0,
                                corridor,
                                obstacles,
                                context,
                            )
                            route_records.extend(candidate_routes)
                        complete = [
                            record for record in exact if record["gate_pass"]
                        ]
                        base_record.update(
                            {
                                "route_records": candidate_routes,
                                "exact_spline_records": [
                                    public(record) for record in exact
                                ],
                                "complete_route_count": len(complete),
                                "gate_pass": bool(complete),
                                "checkpoint_status": "COMPLETE",
                            }
                        )
                        completed_ids.add(candidate_id)
                        checkpoint("TERMINAL_CANDIDATE_COMPLETE", candidate_id)
    return records, route_records


def main():
    report_path = Path(v14.argument("--report")).resolve()
    context = v17.baseline_context()
    attribution = json.loads(
        v23.V22_ATTRIBUTION_PATH.read_text(encoding="utf-8")
    )
    corridor = v22.v21.reconstruct_v12_core(context)
    authority = b2b_authority(context, corridor)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    authority_path = report_path.with_name("b2b_ring_authority.json")
    authority_path.write_text(
        json.dumps(authority, indent=2) + "\n",
        encoding="utf-8",
    )
    obstacles = v23.obstacle_context(context, corridor, attribution)
    progress_path = report_path.with_name("b2b_exit_progress.json")
    trim_records, trim_routes = trim_candidates(
        authority,
        corridor,
        obstacles,
        context,
        progress_path,
    )
    passing_trims = [
        record for record in trim_records if record["gate_pass"]
    ]
    terminal_records = []
    terminal_routes = []
    if not passing_trims:
        terminal_progress_path = report_path.with_name(
            "b2b_terminal_progress.json"
        )
        terminal_records, terminal_routes = terminal_candidates(
            authority,
            corridor,
            obstacles,
            context,
            terminal_progress_path,
        )
    passing_terminal = [
        record for record in terminal_records if record["gate_pass"]
    ]
    if passing_trims:
        status = "READ_ONLY_B2B_RING_TRIM_ROUTE_PASS_V24"
    elif passing_terminal:
        status = "READ_ONLY_B2B_TERMINAL_REAUTHOR_ROUTE_PASS_V24"
    else:
        status = NO_REAUTHOR
    exit_path = report_path.with_name("b2b_exit_preflight.json")
    exit_payload = {
        "operation": OPERATION,
        "status": status,
        "authority_sha256": sha_file(authority_path),
        "trim_candidates": trim_records,
        "terminal_subsegment_candidates": terminal_records,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    exit_path.write_text(
        json.dumps(exit_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    route_path = report_path.with_name("route_preflight_v24.json")
    route_payload = {
        "operation": OPERATION,
        "status": status,
        "reused_v23_contract": {
            "route_preflight_sha256": (
                "148405170f9c929cbd6f6d6a130686b7a45f11d2c11919733ea08c519050db2c"
            ),
            "endpoints": ["E0", "E1", "E2"],
            "E3": "REJECTED",
            "lattice_mm": 4.0,
            "widths_mm": list(WIDTHS),
            "thickness_mm": 2.4,
        },
        "trim_route_records": trim_routes,
        "terminal_route_records": terminal_routes,
        "complete_route_channel_pairs": [],
        "layer_order_sample_tables": [],
        "selected_result": None,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    route_path.write_text(
        json.dumps(route_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    allowlist_path = report_path.with_name(
        "joint_allowlist_preflight_v24.json"
    )
    allowlist = {
        "operation": OPERATION,
        "status": status,
        "selected_C20_suffix_authority": None,
        "C20_T0_mask": [2741, 4711],
        "C9_base_mask": [],
        "C9_transition_ring": [],
        "immutable_complement_fingerprints": {
            "C9": attribution["immutable_complements"][
                "C9_outside_attribution_union"
            ]["fingerprint"],
            "C20": attribution["immutable_complements"][
                "C20_outside_attribution_union"
            ]["fingerprint"],
            "v12": attribution["immutable_complements"][
                "v12_corridor_fingerprint"
            ],
            "Branch_A": attribution["immutable_complements"][
                "branch_a_fingerprint"
            ],
            "B2b": authority["fingerprints"]["B2b"],
            "turn_bridge": authority["fingerprints"]["turn_bridge"],
        },
        "mutation_authority": False,
    }
    allowlist_path.write_text(
        json.dumps(allowlist, indent=2) + "\n",
        encoding="utf-8",
    )
    rejection_counts = Counter(
        record["rejection_reason"] for record in trim_records
    )
    rejection_counts.update(
        record["local_rejection_reason"]
        for record in terminal_records
        if record["local_rejection_reason"]
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "b2b_ring_authority": str(authority_path),
        "b2b_ring_authority_sha256": sha_file(authority_path),
        "b2b_exit_preflight": str(exit_path),
        "b2b_exit_preflight_sha256": sha_file(exit_path),
        "route_preflight_v24": str(route_path),
        "route_preflight_v24_sha256": sha_file(route_path),
        "joint_allowlist_preflight_v24": str(allowlist_path),
        "joint_allowlist_preflight_v24_sha256": sha_file(allowlist_path),
        "candidate_counts": {
            "trim_count": len(trim_records),
            "locally_passing_trim_count": sum(
                record["selected_local_portal"] is not None
                for record in trim_records
            ),
            "complete_trim_route_count": len(passing_trims),
            "terminal_subsegment_count": len(terminal_records),
            "locally_passing_terminal_count": sum(
                record["local_gate_pass"] for record in terminal_records
            ),
            "complete_terminal_route_count": len(passing_terminal),
        },
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "selected_result": None,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "gate_pass": False,
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
                **report["candidate_counts"],
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v24 B2b exit preflight status={status}; "
        "mutation_started=False; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
