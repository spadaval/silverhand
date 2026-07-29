"""Persist exact V25 authored-tail authority and bounded search contract.

This stage is deliberately read-only. Candidate generation is added only after
the authority and A0-A3 boundary have been independently checkpointed.
"""

from __future__ import annotations

from collections import Counter, deque
from hashlib import sha256
from heapq import heappop, heappush
import json
from math import ceil, sqrt
from pathlib import Path
import sys

from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_joint_c9_c20_elbow_v22 as v22  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import preflight_b2b_exit_v24 as v24  # noqa: E402
import preflight_free_space_lower_route_v23 as v23  # noqa: E402


OPERATION = "AUTHORED_TAIL_RECONSTRUCTION_PREFLIGHT_V25"
AUTHORITY_BLEND_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
EXPECTED_V12_SHA256 = (
    "02c02b716c081c3a71826ccac84a154179f5b6a926471aa41d321dc4c6512bbb"
)
WIDTHS_MM = (6.0, 5.25, 4.5)
ADVANCES_MM = (4.0, 8.0, 12.0)
OFFSETS_MM = (-12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0)
ROLLS_DEGREES = (0, -15, 15, -30, 30, -45, 45, -60, 60)
PROGRESS_INTERVAL = 250


def stable_hash(value):
    return sha256(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def point_list(points):
    return [[float(value) for value in point] for point in points]


def geometry_fingerprint(record):
    return stable_hash(
        {
            "points": point_list(record["_points"]),
            "faces": [list(face) for face in record["_faces"]],
        }
    )


def nearest_distance(points, tree):
    distances = []
    for point in points:
        nearest = tree.find_nearest(point)
        if nearest is not None:
            distances.append(nearest[3])
    return min(distances) if distances else None


def constituent_authority(
    name,
    record,
    corridor,
    c9_tree,
    source_tree,
):
    samples = record["_samples"]
    points = record["_points"]
    faces = record["_faces"]
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(
        samples,
        tangents,
        corridor["target_length"],
    )
    margins = v24.v4.v2.point_margins(
        points,
        corridor["target_length"],
        corridor["grid"],
    )
    cumulative = [0.0]
    for first, second in zip(samples, samples[1:]):
        cumulative.append(cumulative[-1] + (second - first).length)
    rings = []
    for ring_index, (center, tangent, frame) in enumerate(
        zip(samples, tangents, frames)
    ):
        width_axis, normal = v8.rotated_frame(
            frame[0],
            tangent,
            record["roll_degrees"],
        )
        start = ring_index * 5
        ring_points = points[start : start + 5]
        face_ids = [
            face_id
            for face_id, face in enumerate(faces)
            if any(start <= vertex < start + 5 for vertex in face)
        ]
        rings.append(
            {
                "ring_id": f"R{ring_index}",
                "center_mm": [float(value) for value in center],
                "ordered_ring_vertices_mm": point_list(ring_points),
                "tangent": [float(value) for value in tangent],
                "parallel_transport_normal": [float(value) for value in normal],
                "parallel_transport_binormal": [
                    float(value) for value in width_axis
                ],
                "roll_degrees": record["roll_degrees"],
                "cumulative_arclength_mm": round(
                    cumulative[ring_index],
                    6,
                ),
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
                "minimum_cutter_margin_mm": round(
                    min(margins[start : start + 5]),
                    6,
                ),
                "minimum_c9_distance_mm": round(
                    nearest_distance(ring_points, c9_tree),
                    6,
                ),
                "minimum_source_distance_mm": round(
                    nearest_distance(ring_points, source_tree),
                    6,
                ),
                "related_face_ids": face_ids,
                "material_indices": [0],
            }
        )
    start_cap = [
        face_id
        for face_id, face in enumerate(faces)
        if all(vertex < 5 for vertex in face)
    ]
    end_start = (len(samples) - 1) * 5
    end_cap = [
        face_id
        for face_id, face in enumerate(faces)
        if all(vertex >= end_start for vertex in face)
    ]
    return {
        "name": name,
        "fingerprint": geometry_fingerprint(record),
        "centerline_samples_mm": point_list(samples),
        "rings": rings,
        "vertex_count": len(points),
        "face_count": len(faces),
        "faces": [
            {
                "local_face_id": face_id,
                "loop": list(face),
                "material_index": 0,
            }
            for face_id, face in enumerate(faces)
        ],
        "start_cap_face_ids": start_cap,
        "end_cap_face_ids": end_cap,
        "minimum_cutter_margin_mm": record["minimum_cutter_margin_mm"],
    }


def related_rings(face, ring_count):
    return sorted(
        {
            min(vertex // 5, ring_count - 1)
            for vertex in face
        }
    )


def prefix_fingerprint(record, anchor_index):
    point_limit = (anchor_index + 1) * 5
    faces = [
        list(face)
        for face in record["_faces"]
        if max(face) < point_limit
    ]
    payload = {
        "anchor_ring_index": anchor_index,
        "points": point_list(record["_points"][:point_limit]),
        "faces": faces,
    }
    return stable_hash(payload)


def resolve_anchors(context, corridor, authority):
    b2a = corridor["core"]["B2a"]
    bridge = corridor["turn"]
    pairs = v14.overlap_pairs(
        b2a["_points"],
        b2a["_faces"],
        bridge["_points"],
        bridge["_faces"],
    )
    ring_count = len(b2a["_samples"])
    face_rings = {
        face_id: related_rings(face, ring_count)
        for face_id, face in enumerate(b2a["_faces"])
    }
    bridge_touch_rings = sorted(
        {
            ring
            for face_id, _ in pairs
            for ring in face_rings[face_id]
        }
    )
    cumulative = [
        ring["cumulative_arclength_mm"]
        for ring in authority["constituents"]["B2a"]["rings"]
    ]
    source_v2111 = context["staged_points"][2111]
    v2111_ring = min(
        range(ring_count),
        key=lambda index: (
            b2a["_samples"][index] - source_v2111
        ).length,
    )
    eligible = []
    for anchor in range(ring_count):
        suffix = cumulative[-1] - cumulative[anchor]
        if suffix > 12.0 + 1.0e-6 or anchor < v2111_ring:
            continue
        scarf_start = anchor
        while (
            scarf_start > 0
            and cumulative[anchor] - cumulative[scarf_start] < 6.0
        ):
            scarf_start -= 1
        if cumulative[anchor] - cumulative[scarf_start] < 6.0 - 1.0e-6:
            continue
        scarf_face_ids = {
            face_id
            for face_id, rings in face_rings.items()
            if max(rings) >= scarf_start and max(rings) <= anchor
        }
        scarf_bridge_pairs = [
            list(pair) for pair in pairs if pair[0] in scarf_face_ids
        ]
        if scarf_bridge_pairs:
            continue
        eligible.append(
            {
                "ring_index": anchor,
                "scarf_start_ring_index": scarf_start,
                "scarf_length_mm": round(
                    cumulative[anchor] - cumulative[scarf_start],
                    6,
                ),
                "replaced_suffix_arclength_mm": round(suffix, 6),
                "prefix_fingerprint": prefix_fingerprint(b2a, anchor),
            }
        )
    if not eligible:
        raise RuntimeError(
            f"{OPERATION}: A0 cannot be resolved without touching the "
            f"bridge, B1, or V2111-side retained interval; "
            f"bridge_touch_rings={bridge_touch_rings}, "
            f"v2111_ring={v2111_ring}"
        )
    a0 = max(eligible, key=lambda record: record["ring_index"])
    by_index = {record["ring_index"]: record for record in eligible}
    anchors = []
    resolution_ledger = []
    for offset in range(4):
        ring_index = a0["ring_index"] - offset
        anchor_id = f"A{offset}"
        ring_id = f"R{ring_index}"
        if ring_index in by_index:
            record = {
                **by_index[ring_index],
                "anchor_id": anchor_id,
                "ring_id": ring_id,
            }
            anchors.append(record)
            resolution_ledger.append(
                {**record, "eligible_for_search": True}
            )
        else:
            suffix = cumulative[-1] - cumulative[ring_index]
            resolution_ledger.append(
                {
                    "anchor_id": anchor_id,
                    "ring_id": ring_id,
                    "ring_index": ring_index,
                    "replaced_suffix_arclength_mm": round(suffix, 6),
                    "eligible_for_search": False,
                    "rejection_reason": (
                        "replaced_B2a_suffix_exceeds_12mm"
                        if suffix > 12.0 + 1.0e-6
                        else "bridge_free_6mm_scarf_not_available"
                    ),
                }
            )
    return {
        "B2A_BRIDGE_OVERLAP_PAIRS": [list(pair) for pair in pairs],
        "BRIDGE_TOUCH_B2A_RINGS": bridge_touch_rings,
        "BRIDGE_TOUCH_B2B_RINGS": [
            int(ring["ring_id"][1:])
            for ring in authority["constituents"]["B2b"]["rings"]
            if ring["turn_bridge_overlap_pairs"]
        ],
        "LAST_BRIDGE_FREE_B2A_RING": f"R{a0['ring_index']}",
        "EARLIEST_ALLOWED_B2A_ANCHOR": (
            anchors[-1]["ring_id"] if anchors else None
        ),
        "V2111_NEAREST_B2A_RING": f"R{v2111_ring}",
        "ordered_anchors": anchors,
        "anchor_resolution_ledger": resolution_ledger,
    }


def bezier_point(control, parameter):
    inverse = 1.0 - parameter
    return (
        control[0] * inverse**3
        + control[1] * (3.0 * inverse**2 * parameter)
        + control[2] * (3.0 * inverse * parameter**2)
        + control[3] * parameter**3
    )


def exact_scarf_samples(samples, anchor_index):
    selected = [samples[anchor_index].copy()]
    remaining = 6.0
    for index in range(anchor_index, 0, -1):
        first = samples[index]
        second = samples[index - 1]
        length = (second - first).length
        if length >= remaining:
            selected.append(first.lerp(second, remaining / length))
            remaining = 0.0
            break
        selected.append(second.copy())
        remaining -= length
    if remaining > 1.0e-6:
        return None
    selected.reverse()
    return selected


def expanded_box_contains(point, minimum, maximum):
    return all(
        minimum[index] - 1.0e-6 <= point[index] <= maximum[index] + 1.0e-6
        for index in range(3)
    )


def prism_contains(point, start, frame):
    delta = point - start
    longitudinal = delta.dot(Vector(frame["u"]))
    first = delta.dot(Vector(frame["first_transverse"]))
    second = delta.dot(Vector(frame["second_transverse"]))
    return all(
        (
            -4.0 - 1.0e-6
            <= longitudinal
            <= frame["chord_length_mm"] + 4.0 + 1.0e-6,
            abs(first) <= 24.0 + 1.0e-6,
            abs(second) <= 24.0 + 1.0e-6,
            sqrt(first * first + second * second) <= 28.0 + 1.0e-6,
        )
    )


def build_anchor_obstacles(context, corridor, attribution, anchor):
    obstacles = v23.obstacle_context(context, corridor, attribution)
    b2a = corridor["core"]["B2a"]
    point_limit = (anchor["scarf_start_ring_index"] + 1) * 5
    prefix_faces = [
        face for face in b2a["_faces"] if max(face) < point_limit
    ]
    v12_points, v12_faces = v23.merge_geometries(
        (
            (
                corridor["core"]["B0"]["_points"],
                corridor["core"]["B0"]["_faces"],
            ),
            (
                corridor["core"]["B1"]["_points"],
                corridor["core"]["B1"]["_faces"],
            ),
            (b2a["_points"][:point_limit], prefix_faces),
        )
    )
    obstacles["trees"]["V12_IMMUTABLE"] = BVHTree.FromPolygons(
        v12_points,
        v12_faces,
        all_triangles=False,
    )
    obstacles["source"]["V12_IMMUTABLE"] = (
        v12_points,
        v12_faces,
        None,
    )
    obstacles["catalogs"]["V12_IMMUTABLE_EXCEPT_B2A_SCARF"] = {
        "anchor_id": anchor["anchor_id"],
        "vertex_count": len(v12_points),
        "face_count": len(v12_faces),
        "fingerprint": stable_hash(
            {
                "points": point_list(v12_points),
                "faces": [list(face) for face in v12_faces],
            }
        ),
        "retired": {
            "B2a_suffix_from_ring": anchor["ring_id"],
            "turn_bridge": True,
            "B2b": True,
        },
    }
    proximal = attribution["component_9_classification"][
        "proximal_wearer_facing"
    ]["incident_face_ids"]
    prox_points, prox_faces, _ = v23.local_geometry(
        context["staged_points"],
        context["staged_faces"],
        proximal,
    )
    obstacles["source"]["C9_PROXIMAL"] = (
        prox_points,
        prox_faces,
        proximal,
    )
    return obstacles


def old_tail_bounds(corridor):
    points = [
        point
        for record in (
            corridor["turn"],
            corridor["core"]["B2b"],
        )
        for point in record["_points"]
    ]
    minimum = Vector(
        tuple(min(point[index] for point in points) - 12.0 for index in range(3))
    )
    maximum = Vector(
        tuple(max(point[index] for point in points) + 12.0 for index in range(3))
    )
    return minimum, maximum


def escape_candidate(
    candidate,
    anchor,
    endpoint,
    corridor,
    obstacles,
    bounds,
):
    b2a = corridor["core"]["B2a"]
    center = b2a["_samples"][anchor["ring_index"]]
    authority_ring = anchor["_authority_ring"]
    tangent = Vector(authority_ring["tangent"]).normalized()
    normal = Vector(authority_ring["parallel_transport_normal"]).normalized()
    binormal = Vector(
        authority_ring["parallel_transport_binormal"]
    ).normalized()
    radial = sqrt(
        candidate["normal_offset_mm"] ** 2
        + candidate["binormal_offset_mm"] ** 2
    )
    if radial > 12.0 + 1.0e-6:
        return None, "radial_offset_exceeds_12mm", {}
    end = (
        center
        + tangent * candidate["advance_mm"]
        + normal * candidate["normal_offset_mm"]
        + binormal * candidate["binormal_offset_mm"]
    )
    chord = end - center
    if not 6.0 - 1.0e-6 <= chord.length <= 18.0 + 1.0e-6:
        return None, "escape_chord_outside_6_18mm", {}
    handle = min(6.0, chord.length / 3.0)
    end_tangent = chord.normalized()
    controls = [
        center,
        center + tangent * handle,
        end - end_tangent * handle,
        end,
    ]
    control_length = sum(
        (second - first).length
        for first, second in zip(controls, controls[1:])
    )
    sample_count = max(4, int(ceil(control_length / 2.0)) + 1)
    samples = [
        bezier_point(controls, index / (sample_count - 1))
        for index in range(sample_count)
    ]
    endpoint_vector = Vector(endpoint["coordinate_mm"])
    _, prism = v23.lattice_nodes(center, endpoint_vector, normal)
    if any(
        not (
            expanded_box_contains(point, bounds[0], bounds[1])
            or prism_contains(point, center, prism)
        )
        for point in samples
    ):
        return None, "escape_outside_old_tail_or_v23_domain", {}
    for first, second in zip(samples, samples[1:]):
        gate, reason = v23.segment_gate(
            first,
            second,
            candidate["roll_degrees"],
            candidate["width_mm"],
            obstacles,
            corridor,
        )
        if not gate:
            return None, reason, {}
    sample_tangent = (samples[-1] - samples[-2]).normalized()
    metrics = {
        "control_points_mm": point_list(controls),
        "sample_points_mm": point_list(samples),
        "sample_count": len(samples),
        "chord_length_mm": round(chord.length, 6),
        "control_polygon_length_mm": round(control_length, 6),
        "anchor_tangent_deflection_degrees": 0.0,
        "escape_end_tangent_deflection_degrees": round(
            v23.turn_degrees(sample_tangent, end_tangent),
            6,
        ),
        "search_prism": prism,
    }
    return {
        "samples": samples,
        "end": end,
        "end_tangent": sample_tangent,
        "controls": controls,
    }, None, metrics


def exact_candidate(
    candidate_id,
    scarf,
    escape,
    route,
    corridor,
    obstacles,
    context,
):
    combined = [
        *scarf,
        *escape["samples"][1:],
        *route["points"][1:],
    ]
    spline = v23.fit_spline(combined)
    rolls = [candidate_id["roll_degrees"]] * len(spline["samples"])
    exact = v23.exact_collision_record(
        candidate_id["tuple_id"],
        spline,
        rolls,
        candidate_id["width_mm"],
        obstacles,
        context,
        corridor,
    )
    points = exact["_points"]
    faces = exact["_faces"]
    t0_points, t0_faces, _ = v23.local_geometry(
        context["staged_points"],
        context["staged_faces"],
        [2741, 4711],
    )
    t0_pairs = v14.overlap_pairs(points, faces, t0_points, t0_faces)
    hard_collision_names = (
        "C20_EXTERIOR",
        "C9_NONPROXIMAL",
        "BRANCH_A",
        "V12_IMMUTABLE",
        "OPENING",
    )
    hard_clear = all(
        exact["collisions"][name]["pair_count"] == 0
        for name in hard_collision_names
    )
    proximal_hits = exact["collisions"]["C9_PROXIMAL"][
        "source_face_ids"
    ] or []
    geometry_clear = all(
        (
            hard_clear,
            not exact["cutter_overlap_pairs"],
            not exact["self_overlap_pairs"],
            exact["minimum_cutter_margin_mm"] >= 1.7,
            exact["maximum_fit_error_mm"] <= 0.5,
            exact["maximum_sample_turn_degrees"] <= 30.0,
            exact["triangle_quality"]["minimum_angle_degrees"]["minimum"]
            >= 3.0,
            exact["triangle_quality"]["aspect_ratio"]["maximum"] <= 12.0,
            bool(t0_pairs),
        )
    )
    exact["T0_overlap_pairs"] = [list(pair) for pair in t0_pairs]
    exact["C9_proximal_face_ids"] = proximal_hits
    exact["otherwise_clean_except_proximal_C9"] = geometry_clear
    exact["C20_only_gate_pass"] = geometry_clear and not proximal_hits
    exact["paired_channel_preflight_eligible"] = (
        geometry_clear and bool(proximal_hits)
    )
    return exact


def cached_roll_evolving_astar(
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

    def edge_gate(first_key, second_key, first, second, edge_roll):
        cache_key = (first_key, second_key, edge_roll)
        if cache_key not in edge_cache:
            edge_cache[cache_key] = v23.segment_gate(
                first,
                second,
                edge_roll,
                width,
                obstacles,
                corridor,
            )
        return edge_cache[cache_key]

    initial = []
    rejection_counts = Counter()
    for key, point in nodes.items():
        delta = point - start
        if not 2.0 <= delta.length <= 7.0:
            continue
        if v23.turn_degrees(start_tangent, delta) > 45.0:
            continue
        gate, reason = edge_gate(
            ("START",),
            key,
            start,
            point,
            roll,
        )
        if gate:
            initial.append((key, delta.normalized()))
        else:
            rejection_counts[f"initial_{reason}"] += 1
    queue = []
    best = {}
    parent = {}
    serial = 0
    for key, direction in initial:
        cost = (nodes[key] - start).length
        state = (key, tuple(round(value, 6) for value in direction), roll)
        best[state] = cost
        parent[state] = None
        heappush(
            queue,
            (cost + (end - nodes[key]).length, serial, cost, state),
        )
        serial += 1
    goal = None
    while queue:
        _, _, queued_cost, state = heappop(queue)
        if queued_cost > best.get(state, float("inf")) + 1.0e-9:
            continue
        key, direction_values, state_roll = state
        current = nodes[key]
        incoming = Vector(direction_values)
        cost = best[state]
        delta_to_end = end - current
        if (
            2.0 <= delta_to_end.length <= 7.0
            and v23.turn_degrees(incoming, delta_to_end) <= 45.0
            and v23.turn_degrees(delta_to_end, end_tangent) <= 45.0
        ):
            gate, reason = edge_gate(
                key,
                ("END",),
                current,
                end,
                state_roll,
            )
            if gate:
                goal = state
                break
            rejection_counts[reason] += 1
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
            for roll_delta in (-15, 0, 15):
                following_roll = state_roll + roll_delta
                if not -180 <= following_roll <= 180:
                    continue
                gate, reason = edge_gate(
                    key,
                    following_key,
                    current,
                    following,
                    following_roll,
                )
                if not gate:
                    rejection_counts[reason] += 1
                    continue
                direction = outgoing.normalized()
                following_state = (
                    following_key,
                    tuple(round(value, 6) for value in direction),
                    following_roll,
                )
                following_cost = cost + outgoing.length
                if following_cost >= best.get(
                    following_state,
                    float("inf"),
                ):
                    continue
                best[following_state] = following_cost
                parent[following_state] = state
                heappush(
                    queue,
                    (
                        following_cost + (end - following).length,
                        serial,
                        following_cost,
                        following_state,
                    ),
                )
                serial += 1
    if goal is None:
        return None, {
            "expanded_state_count": len(best),
            "edge_rejection_counts": dict(sorted(rejection_counts.items())),
            "roll_evolution": "V23-equivalent ±15 degrees per 4 mm edge",
            "memoized_edge_gate_count": len(edge_cache),
        }
    states = []
    current = goal
    while current is not None:
        states.append(current)
        current = parent[current]
    states.reverse()
    points = [start, *[nodes[state[0]] for state in states], end]
    rolls = [roll, *[state[2] for state in states], states[-1][2]]
    return {
        "points": points,
        "rolls": rolls,
        "length_mm": sum(
            (second - first).length
            for first, second in zip(points, points[1:])
        ),
    }, {
        "expanded_state_count": len(best),
        "edge_rejection_counts": dict(sorted(rejection_counts.items())),
        "roll_evolution": "V23-equivalent ±15 degrees per 4 mm edge",
        "memoized_edge_gate_count": len(edge_cache),
    }


def validate_cached_astar(
    report_path,
    context,
    corridor,
    attribution,
):
    obstacles = v23.obstacle_context(context, corridor, attribution)
    portal = v23.b2b_portal(corridor)
    path = report_path.with_name("v25_cached_astar_equivalence.json")
    payload = {
        "operation": OPERATION,
        "status": "CACHED_ASTAR_EQUIVALENCE_IN_PROGRESS",
        "current_case_id": None,
        "current_phase": None,
        "case_count": 3,
        "cases": [],
        "all_cases_match": False,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    atomic_json(path, payload)
    cases = []
    for endpoint in [
        record
        for record in v23.endpoint_candidates(context)
        if record["accepted"]
    ]:
        start = portal["_center"]
        end = Vector(endpoint["coordinate_mm"])
        full_nodes, frame = v23.lattice_nodes(
            start,
            end,
            portal["_normal"],
        )
        near_keys = sorted(
            key
            for key, point in full_nodes.items()
            if 2.0 <= (point - start).length <= 7.0
        )[:12]
        nodes = {key: full_nodes[key] for key in near_keys}
        toward = Vector((-0.451645434, 0.836417615, -0.310518861))
        if toward.dot(start - end) < 0:
            toward.negate()
        arrival = -toward.normalized()
        case_id = f"B2B_{endpoint['endpoint_id']}_W6_R0_N12"
        payload["current_case_id"] = case_id
        payload["current_phase"] = "ORIGINAL_V23_ASTAR_PENDING"
        atomic_json(path, payload)
        original_route, original_metrics = v23.astar(
            nodes,
            start,
            end,
            portal["_tangent"],
            arrival,
            0,
            6.0,
            obstacles,
            corridor,
        )
        payload["current_phase"] = "CACHED_ASTAR_PENDING"
        payload["original_partial"] = {
            "polyline_found": original_route is not None,
            **original_metrics,
        }
        atomic_json(path, payload)
        cached_route, cached_metrics = cached_roll_evolving_astar(
            nodes,
            start,
            end,
            portal["_tangent"],
            arrival,
            0,
            6.0,
            obstacles,
            corridor,
        )
        original_public = {
            "polyline_found": original_route is not None,
            "expanded_state_count": original_metrics[
                "expanded_state_count"
            ],
            "edge_rejection_counts": original_metrics[
                "edge_rejection_counts"
            ],
            "points_mm": (
                point_list(original_route["points"])
                if original_route is not None
                else None
            ),
            "rolls": (
                original_route["rolls"]
                if original_route is not None
                else None
            ),
        }
        cached_public = {
            "polyline_found": cached_route is not None,
            "expanded_state_count": cached_metrics[
                "expanded_state_count"
            ],
            "edge_rejection_counts": cached_metrics[
                "edge_rejection_counts"
            ],
            "points_mm": (
                point_list(cached_route["points"])
                if cached_route is not None
                else None
            ),
            "rolls": (
                cached_route["rolls"]
                if cached_route is not None
                else None
            ),
        }
        cases.append(
            {
                "case_id": case_id,
                "node_count": len(nodes),
                "search_frame": frame,
                "original": original_public,
                "cached": cached_public,
                "match": original_public == cached_public,
                "cached_memoized_edge_gate_count": cached_metrics[
                    "memoized_edge_gate_count"
                ],
            }
        )
        payload["cases"] = cases
        payload["current_phase"] = "CASE_CHECKPOINTED"
        payload.pop("original_partial", None)
        atomic_json(path, payload)
    payload["status"] = "CACHED_ASTAR_EQUIVALENCE_CHECKPOINTED"
    payload["current_case_id"] = None
    payload["current_phase"] = None
    payload["case_count"] = len(cases)
    payload["all_cases_match"] = all(case["match"] for case in cases)
    atomic_json(path, payload)
    if not payload["all_cases_match"]:
        raise RuntimeError(
            f"{OPERATION}: cached roll-evolving A* differs from original "
            f"V23 helper; evidence={path}"
        )
    return path


def progress_template(contract_sha, authority_sha):
    return {
        "operation": OPERATION,
        "status": "SEARCH_IN_PROGRESS",
        "contract_sha256": contract_sha,
        "authority_sha256": authority_sha,
        "completed_tuple_ids": [],
        "next_tuple_id": None,
        "accepted_escape_ids": [],
        "accepted_escape_records": [],
        "accepted_route_ids": [],
        "accepted_route_records": [],
        "first_proximal_C9_contacts": [],
        "rejection_counts_by_exact_obstacle": {},
        "latest_exact_overlap_arrays": {},
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }


def load_progress(path, contract_sha, authority_sha):
    if not path.exists():
        return progress_template(contract_sha, authority_sha)
    progress = json.loads(path.read_text(encoding="utf-8"))
    if (
        progress.get("contract_sha256") == contract_sha
        and progress.get("authority_sha256") == authority_sha
    ):
        return progress
    stale = path.with_name(
        f"{path.stem}.stale-"
        f"{progress.get('contract_sha256', 'unknown')[:12]}.json"
    )
    path.replace(stale)
    return progress_template(contract_sha, authority_sha)


def tuple_records(authority):
    for anchor in authority["ordered_anchors"]:
        for endpoint in ("E0", "E1", "E2"):
            for width in WIDTHS_MM:
                for advance in ADVANCES_MM:
                    for normal in OFFSETS_MM:
                        for binormal in OFFSETS_MM:
                            for roll in ROLLS_DEGREES:
                                values = {
                                    "anchor_id": anchor["anchor_id"],
                                    "endpoint_id": endpoint,
                                    "width_mm": width,
                                    "advance_mm": advance,
                                    "normal_offset_mm": normal,
                                    "binormal_offset_mm": binormal,
                                    "roll_degrees": roll,
                                }
                                values["tuple_id"] = (
                                    f"{anchor['anchor_id']}_{endpoint}_"
                                    f"W{width:.2f}_A{advance:.0f}_"
                                    f"N{normal:+.0f}_B{binormal:+.0f}_"
                                    f"R{roll:+03d}"
                                )
                                yield values


def deduplicate_portals(escape_records):
    groups = {}
    order = []
    for record in escape_records:
        payload = {
            "anchor_id": record["anchor_id"],
            "width_mm": record["width_mm"],
            "advance_mm": record["advance_mm"],
            "normal_offset_mm": record["normal_offset_mm"],
            "binormal_offset_mm": record["binormal_offset_mm"],
            "roll_degrees": record["roll_degrees"],
            "sample_points_mm": record["sample_points_mm"],
        }
        portal_sha = stable_hash(payload)
        if portal_sha not in groups:
            groups[portal_sha] = {
                "portal_id": f"P_{portal_sha[:16]}",
                "portal_sha256": portal_sha,
                **payload,
                "aliases": [],
                "accepted_endpoint_ids": [],
            }
            order.append(portal_sha)
        group = groups[portal_sha]
        group["aliases"].append(
            {
                "tuple_id": record["tuple_id"],
                "endpoint_id": record["endpoint_id"],
            }
        )
        if record["endpoint_id"] not in group["accepted_endpoint_ids"]:
            group["accepted_endpoint_ids"].append(record["endpoint_id"])
    return [groups[key] for key in order]


def run_search(
    report_path,
    context,
    corridor,
    attribution,
    authority,
    contract_path,
    authority_path,
    escape_only=False,
):
    contract_sha = sha_file(contract_path)
    authority_sha = sha_file(authority_path)
    progress_path = report_path.with_name("v25_progress.json")
    progress = load_progress(
        progress_path,
        contract_sha,
        authority_sha,
    )
    progress.setdefault("routed_escape_ids", [])
    completed = set(progress["completed_tuple_ids"])
    rejections = Counter(progress["rejection_counts_by_exact_obstacle"])
    endpoint_map = {
        record["endpoint_id"]: record
        for record in v23.endpoint_candidates(context)
        if record["accepted"]
    }
    anchor_map = {
        record["anchor_id"]: dict(record)
        for record in authority["ordered_anchors"]
    }
    for anchor in anchor_map.values():
        anchor["_authority_ring"] = authority["constituents"]["B2a"][
            "rings"
        ][anchor["ring_index"]]
    obstacle_map = {
        anchor_id: build_anchor_obstacles(
            context,
            corridor,
            attribution,
            anchor,
        )
        for anchor_id, anchor in anchor_map.items()
    }
    bounds = old_tail_bounds(corridor)
    b0_tip = context["staged_points"][2074]
    selected = None
    processed_since_write = 0
    last_batch = None
    route_attempt_count = 0
    for candidate in tuple_records(authority):
        tuple_id = candidate["tuple_id"]
        if tuple_id in completed:
            continue
        batch = (
            candidate["anchor_id"],
            candidate["endpoint_id"],
            candidate["width_mm"],
        )
        if last_batch is not None and batch != last_batch:
            progress["rejection_counts_by_exact_obstacle"] = dict(
                sorted(rejections.items())
            )
            atomic_json(progress_path, progress)
            processed_since_write = 0
        last_batch = batch
        anchor = anchor_map[candidate["anchor_id"]]
        endpoint = endpoint_map[candidate["endpoint_id"]]
        obstacles = obstacle_map[candidate["anchor_id"]]
        escape, reason, escape_metrics = escape_candidate(
            candidate,
            anchor,
            endpoint,
            corridor,
            obstacles,
            bounds,
        )
        if escape is None:
            rejections[reason] += 1
        elif min(
            (point - b0_tip).length for point in escape["samples"]
        ) < context["checks"]["tip_gap_mm"] - 2.0:
            reason = "C_tip_gap_minus_2mm"
            rejections[reason] += 1
        else:
            escape_record = {
                **candidate,
                **escape_metrics,
            }
            progress["accepted_escape_ids"].append(tuple_id)
            progress["accepted_escape_records"].append(escape_record)
            progress["rejection_counts_by_exact_obstacle"] = dict(
                sorted(rejections.items())
            )
            progress["next_tuple_id"] = tuple_id
            atomic_json(progress_path, progress)
        completed.add(tuple_id)
        progress["completed_tuple_ids"].append(tuple_id)
        progress["next_tuple_id"] = None
        processed_since_write += 1
        if processed_since_write >= PROGRESS_INTERVAL:
            progress["rejection_counts_by_exact_obstacle"] = dict(
                sorted(rejections.items())
            )
            atomic_json(progress_path, progress)
            processed_since_write = 0
    portals = deduplicate_portals(progress["accepted_escape_records"])
    portal_path = report_path.with_name("v25_portal_dedup.json")
    atomic_json(
        portal_path,
        {
            "operation": OPERATION,
            "status": "CANONICAL_PORTALS_CHECKPOINTED",
            "contract_sha256": contract_sha,
            "authority_sha256": authority_sha,
            "accepted_tuple_count": len(progress["accepted_escape_ids"]),
            "unique_portal_count": len(portals),
            "alias_count": sum(
                len(record["aliases"]) for record in portals
            ),
            "portals": portals,
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
        },
    )
    shard_contract_path = report_path.with_name(
        "v25_route_shard_contract.json"
    )
    equivalence_path = report_path.with_name(
        "v25_cached_astar_equivalence.json"
    )
    capsule_validation_path = report_path.with_name(
        "v25_capsule_prefilter_validation.json"
    )
    atomic_json(
        shard_contract_path,
        {
            "operation": OPERATION,
            "status": "ROUTE_SHARDS_CHECKPOINTED",
            "authority_sha256": authority_sha,
            "contract_sha256": contract_sha,
            "portal_dedup_sha256": sha_file(portal_path),
            "cached_astar_equivalence_sha256": sha_file(
                equivalence_path
            ),
            "capsule_prefilter_validation_sha256": sha_file(
                capsule_validation_path
            ),
            "shard_count": 3,
            "assignment": "ordered_portal_index modulo shard_count",
            "ordered_portal_ids": [
                portal["portal_id"] for portal in portals
            ],
            "shards": {
                str(shard): [
                    portal["portal_id"]
                    for index, portal in enumerate(portals)
                    if index % 3 == shard
                ]
                for shard in range(3)
            },
            "merge_semantics": (
                "concatenate shard route records in original ordered portal "
                "index then E0,E1,E2 order; any exact passing route is a "
                "positive result; all constant-roll failures leave the full "
                "roll-evolving route contract pending"
            ),
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
        },
    )
    if not escape_only:
        routed = set(progress["routed_escape_ids"])
        for portal in portals:
            pending = [
                endpoint_id
                for endpoint_id in portal["accepted_endpoint_ids"]
                if f"{portal['portal_id']}:{endpoint_id}" not in routed
            ]
            if not pending:
                continue
            samples = [
                Vector(point) for point in portal["sample_points_mm"]
            ]
            escape = {
                "samples": samples,
                "end": samples[-1],
                "end_tangent": (samples[-1] - samples[-2]).normalized(),
            }
            anchor = anchor_map[portal["anchor_id"]]
            obstacles = obstacle_map[portal["anchor_id"]]
            portal_routes = []
            for endpoint_id in pending:
                endpoint = endpoint_map[endpoint_id]
                route_id = f"{portal['portal_id']}:{endpoint_id}"
                tuple_id = next(
                    alias["tuple_id"]
                    for alias in portal["aliases"]
                    if alias["endpoint_id"] == endpoint_id
                )
                candidate = {
                    "tuple_id": tuple_id,
                    "anchor_id": portal["anchor_id"],
                    "endpoint_id": endpoint_id,
                    "width_mm": portal["width_mm"],
                    "advance_mm": portal["advance_mm"],
                    "normal_offset_mm": portal["normal_offset_mm"],
                    "binormal_offset_mm": portal["binormal_offset_mm"],
                    "roll_degrees": portal["roll_degrees"],
                }
                end = Vector(endpoint["coordinate_mm"])
                nodes, search_frame = v23.lattice_nodes(
                    escape["end"],
                    end,
                    Vector((0.685143352, 0.548078537, 0.479779691)),
                )
                toward = Vector(
                    (-0.451645434, 0.836417615, -0.310518861)
                )
                if toward.dot(escape["end"] - end) < 0:
                    toward.negate()
                arrival = -toward.normalized()
                progress["status"] = "CONSTANT_ROLL_ROUTE_PENDING"
                progress["current_route_id"] = route_id
                progress["current_route_tuple_alias"] = tuple_id
                atomic_json(progress_path, progress)
                route_attempt_count += 1
                route, route_metrics = v24.cached_constant_roll_astar(
                    nodes,
                    escape["end"],
                    end,
                    escape["end_tangent"],
                    arrival,
                    candidate["roll_degrees"],
                    candidate["width_mm"],
                    obstacles,
                    corridor,
                )
                progress["current_route_id"] = None
                progress["current_route_tuple_alias"] = None
                portal_routes.append(
                    {
                        "route_id": route_id,
                        "tuple_alias": tuple_id,
                        "endpoint_id": endpoint_id,
                        "search_frame": search_frame,
                        **route_metrics,
                        "polyline_found": route is not None,
                    }
                )
                if route is None:
                    rejections[
                        "constant_roll_no_path_full_pending"
                    ] += 1
                else:
                    scarf = exact_scarf_samples(
                        corridor["core"]["B2a"]["_samples"],
                        anchor["ring_index"],
                    )
                    exact = exact_candidate(
                        candidate,
                        scarf,
                        escape,
                        route,
                        corridor,
                        obstacles,
                        context,
                    )
                    public_exact = public(exact)
                    progress["accepted_route_ids"].append(tuple_id)
                    progress["accepted_route_records"].append(
                        {
                            **candidate,
                            "portal_id": portal["portal_id"],
                            "route_id": route_id,
                            "constant_roll_positive_screen": True,
                            "search_frame": search_frame,
                            "route_metrics": route_metrics,
                            "polyline_points_mm": point_list(
                                route["points"]
                            ),
                            "exact": public_exact,
                        }
                    )
                    progress["latest_exact_overlap_arrays"] = {
                        name: record["pairs"]
                        for name, record in exact["collisions"].items()
                    }
                    if exact["C9_proximal_face_ids"]:
                        progress["first_proximal_C9_contacts"].append(
                            {
                                "tuple_id": tuple_id,
                                "portal_id": portal["portal_id"],
                                "source_face_ids": exact[
                                    "C9_proximal_face_ids"
                                ],
                                "pairs": exact["collisions"][
                                    "C9_PROXIMAL"
                                ]["pairs"],
                            }
                        )
                        atomic_json(progress_path, progress)
                    if exact["C20_only_gate_pass"]:
                        selected = {
                            "type": "C20_ONLY",
                            "tuple_id": tuple_id,
                            "portal_id": portal["portal_id"],
                            "exact": public_exact,
                        }
                    elif exact["paired_channel_preflight_eligible"]:
                        selected = {
                            "type": (
                                "C20_TAIL_PLUS_PROXIMAL_C9_CHANNEL"
                            ),
                            "tuple_id": tuple_id,
                            "portal_id": portal["portal_id"],
                            "exact": public_exact,
                        }
                    else:
                        rejections["exact_route_gate"] += 1
                progress["routed_escape_ids"].append(route_id)
                routed.add(route_id)
                progress["rejection_counts_by_exact_obstacle"] = dict(
                    sorted(rejections.items())
                )
                atomic_json(progress_path, progress)
                if selected is not None:
                    break
            progress.setdefault(
                "constant_roll_portal_route_records",
                [],
            ).append(
                {
                    "portal_id": portal["portal_id"],
                    "route_records": portal_routes,
                }
            )
            progress["rejection_counts_by_exact_obstacle"] = dict(
                sorted(rejections.items())
            )
            atomic_json(progress_path, progress)
            if selected is not None:
                break
    progress["rejection_counts_by_exact_obstacle"] = dict(
        sorted(rejections.items())
    )
    if escape_only:
        progress["status"] = "ESCAPE_PREFLIGHT_COMPLETE_ROUTE_PENDING"
    elif selected is not None:
        progress["status"] = "COMPLETE_PAIR_SELECTED"
    else:
        progress["status"] = (
            "CONSTANT_ROLL_SUBSET_COMPLETE_FULL_ROUTE_PENDING"
        )
    atomic_json(progress_path, progress)
    return {
        "status": progress["status"],
        "selected": selected,
        "progress_path": progress_path,
        "portal_path": portal_path,
        "shard_contract_path": shard_contract_path,
        "unique_portal_count": len(portals),
        "completed_tuple_count": len(progress["completed_tuple_ids"]),
        "accepted_escape_count": len(progress["accepted_escape_ids"]),
        "route_attempt_count": route_attempt_count,
        "accepted_route_count": len(progress["accepted_route_ids"]),
        "first_proximal_C9_contact_count": len(
            progress["first_proximal_C9_contacts"]
        ),
        "rejection_counts": dict(sorted(rejections.items())),
        "obstacle_catalogs_by_anchor": {
            anchor_id: obstacles["catalogs"]
            for anchor_id, obstacles in obstacle_map.items()
        },
    }


def inscribed_capsule_path(
    nodes,
    start,
    end,
    obstacles,
    corridor,
):
    radius = 1.2
    point_cache = {}
    edge_cache = {}
    rejections = Counter()

    def point_gate(point):
        key = tuple(round(value, 6) for value in point)
        if key not in point_cache:
            cutter_margin = v24.v4.v2.point_margins(
                [point],
                corridor["target_length"],
                corridor["grid"],
            )[0]
            if cutter_margin < 1.7 + radius:
                point_cache[key] = (False, "capsule_cutter")
            else:
                result = (True, None)
                for name, tree in obstacles["trees"].items():
                    if v23.point_clearance(point, tree) < radius:
                        result = (False, f"capsule_{name}")
                        break
                point_cache[key] = result
        return point_cache[key]

    def edge_gate(first_key, second_key, first, second):
        key = (first_key, second_key)
        if key in edge_cache:
            return edge_cache[key]
        length = (second - first).length
        steps = max(1, int(ceil(length / 2.0)))
        result = (True, None)
        for index in range(steps + 1):
            gate, reason = point_gate(first.lerp(second, index / steps))
            if not gate:
                result = (False, reason)
                break
        edge_cache[key] = result
        return result

    queue = deque()
    parent = {}
    for key, point in nodes.items():
        distance = (point - start).length
        if not 2.0 <= distance <= 7.0:
            continue
        gate, reason = edge_gate(("START",), key, start, point)
        if gate:
            parent[key] = None
            queue.append(key)
        else:
            rejections[f"initial_{reason}"] += 1
    goal = None
    while queue:
        key = queue.popleft()
        current = nodes[key]
        end_distance = (end - current).length
        if 2.0 <= end_distance <= 7.0:
            gate, reason = edge_gate(key, ("END",), current, end)
            if gate:
                goal = key
                break
            rejections[reason] += 1
        li, ai, bi = key
        for offset in v23.NEIGHBORS:
            following_key = (
                li + offset[0],
                ai + offset[1],
                bi + offset[2],
            )
            if following_key not in nodes or following_key in parent:
                continue
            following = nodes[following_key]
            gate, reason = edge_gate(
                key,
                following_key,
                current,
                following,
            )
            if not gate:
                rejections[reason] += 1
                continue
            parent[following_key] = key
            queue.append(following_key)
    if goal is None:
        return None, {
            "visited_node_count": len(parent),
            "point_gate_count": len(point_cache),
            "edge_gate_count": len(edge_cache),
            "rejection_counts": dict(sorted(rejections.items())),
            "capsule_radius_mm": radius,
            "maximum_edge_sample_spacing_mm": 2.0,
        }
    keys = []
    current = goal
    while current is not None:
        keys.append(current)
        current = parent[current]
    keys.reverse()
    return [start, *[nodes[key] for key in keys], end], {
        "visited_node_count": len(parent),
        "point_gate_count": len(point_cache),
        "edge_gate_count": len(edge_cache),
        "rejection_counts": dict(sorted(rejections.items())),
        "capsule_radius_mm": radius,
        "maximum_edge_sample_spacing_mm": 2.0,
    }


def write_capsule_validation(report_path):
    widths = [6.0, 5.25, 4.5]
    radius = 1.2
    cases = [
        {
            "width_mm": width,
            "thickness_mm": 2.4,
            "capsule_radius_mm": radius,
            "contained_in_section": (
                radius <= width / 2.0 and radius <= 2.4 / 2.0
            ),
        }
        for width in widths
    ]
    segment_lengths = [4.0, 4.0 * sqrt(2.0), 4.0 * sqrt(3.0)]
    spacing_cases = []
    for length in segment_lengths:
        steps = max(1, int(ceil(length / 2.0)))
        spacing_cases.append(
            {
                "edge_length_mm": length,
                "sample_step_count": steps,
                "actual_spacing_mm": length / steps,
                "within_2mm": length / steps <= 2.0 + 1.0e-9,
            }
        )
    payload = {
        "operation": OPERATION,
        "status": "INSCRIBED_CAPSULE_NECESSITY_CHECKPOINTED",
        "reasoning": (
            "Every allowed rectangular section contains the same radius "
            "1.2 mm longitudinal capsule. Any passing rectangular route "
            "therefore implies a passing capsule centerline on the same "
            "lattice. Capsule graph disconnection is a necessary-failure "
            "proof; capsule success grants no rectangle result."
        ),
        "section_cases": cases,
        "edge_spacing_cases": spacing_cases,
        "cutter_center_margin_required_mm": 2.9,
        "solid_obstacle_center_distance_required_mm": 1.2,
        "all_cases_pass": all(
            case["contained_in_section"] for case in cases
        )
        and all(case["within_2mm"] for case in spacing_cases),
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    path = report_path.with_name("v25_capsule_prefilter_validation.json")
    atomic_json(path, payload)
    if not payload["all_cases_pass"]:
        raise RuntimeError(
            f"{OPERATION}: inscribed capsule validation failed: {path}"
        )
    return path


def route_shard_argument():
    option = next(
        (
            candidate
            for candidate in (
                "--route-shard",
                "--capsule-route-shard",
                "--full-route-shard",
            )
            if candidate in sys.argv
        ),
        None,
    )
    if option is None:
        return None
    index = sys.argv.index(option)
    try:
        shard_text, count_text = sys.argv[index + 1].split("/", 1)
        shard = int(shard_text)
        count = int(count_text)
    except (IndexError, ValueError) as error:
        raise RuntimeError(
            f"{OPERATION}: --route-shard requires i/n, for example 0/3"
        ) from error
    if count != 3 or not 0 <= shard < count:
        raise RuntimeError(
            f"{OPERATION}: route shard must be 0/3, 1/3, or 2/3; "
            f"observed {shard}/{count}"
        )
    return (
        (
            "full_roll"
            if option == "--full-route-shard"
            else "capsule"
            if option == "--capsule-route-shard"
            else "constant_roll"
        ),
        shard,
        count,
    )


def run_capsule_shard(
    report_path,
    context,
    corridor,
    attribution,
    shard,
    shard_count,
):
    authority_path = report_path.with_name("combined_tail_authority.json")
    contract_path = report_path.with_name("v25_search_contract.json")
    portal_path = report_path.with_name("v25_portal_dedup.json")
    shard_contract_path = report_path.with_name(
        "v25_route_shard_contract.json"
    )
    validation_path = report_path.with_name(
        "v25_capsule_prefilter_validation.json"
    )
    for path in (
        authority_path,
        contract_path,
        portal_path,
        shard_contract_path,
        validation_path,
    ):
        if not path.exists():
            raise RuntimeError(
                f"{OPERATION}: capsule shard {shard}/{shard_count} cannot "
                f"start; missing shared checkpoint: {path}"
            )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["code_sha256"] != sha_file(Path(__file__)):
        raise RuntimeError(
            f"{OPERATION}: capsule shard code hash mismatch; rerun shared "
            f"--escape-only preparation"
        )
    validation = json.loads(
        validation_path.read_text(encoding="utf-8")
    )
    if not validation.get("all_cases_pass"):
        raise RuntimeError(
            f"{OPERATION}: capsule shard blocked by failed necessity "
            f"validation: {validation_path}"
        )
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    portal_payload = json.loads(portal_path.read_text(encoding="utf-8"))
    shard_contract = json.loads(
        shard_contract_path.read_text(encoding="utf-8")
    )
    assigned = set(shard_contract["shards"][str(shard)])
    portals = [
        portal
        for portal in portal_payload["portals"]
        if portal["portal_id"] in assigned
    ]
    progress_path = report_path.with_name(
        f"v25_capsule_route_shard_{shard}_of_{shard_count}.json"
    )
    expected = {
        "authority_sha256": sha_file(authority_path),
        "contract_sha256": sha_file(contract_path),
        "portal_dedup_sha256": sha_file(portal_path),
        "shard_contract_sha256": sha_file(shard_contract_path),
        "capsule_validation_sha256": sha_file(validation_path),
    }
    progress = {}
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if any(progress.get(key) != value for key, value in expected.items()):
            stale = progress_path.with_name(
                f"{progress_path.stem}.stale-"
                f"{progress.get('contract_sha256', 'unknown')[:12]}.json"
            )
            progress_path.replace(stale)
            progress = {}
    if not progress:
        progress = {
            "operation": OPERATION,
            "status": "CAPSULE_ROUTE_SHARD_PENDING",
            "shard": shard,
            "shard_count": shard_count,
            **expected,
            "assigned_portal_ids": [
                portal["portal_id"] for portal in portals
            ],
            "completed_route_ids": [],
            "current_route_id": None,
            "route_records": [],
            "capsule_path_route_ids": [],
            "rejection_counts": {},
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
        }
        atomic_json(progress_path, progress)
    completed = set(progress["completed_route_ids"])
    rejections = Counter(progress["rejection_counts"])
    endpoint_map = {
        record["endpoint_id"]: record
        for record in v23.endpoint_candidates(context)
        if record["accepted"]
    }
    anchor_map = {
        record["anchor_id"]: dict(record)
        for record in authority["ordered_anchors"]
    }
    obstacles = {
        anchor_id: build_anchor_obstacles(
            context,
            corridor,
            attribution,
            anchor,
        )
        for anchor_id, anchor in anchor_map.items()
    }
    for portal in portals:
        samples = [
            Vector(point) for point in portal["sample_points_mm"]
        ]
        start = samples[-1]
        obstacle = obstacles[portal["anchor_id"]]
        for endpoint_id in portal["accepted_endpoint_ids"]:
            route_id = f"{portal['portal_id']}:{endpoint_id}"
            if route_id in completed:
                continue
            endpoint = endpoint_map[endpoint_id]
            end = Vector(endpoint["coordinate_mm"])
            nodes, frame = v23.lattice_nodes(
                start,
                end,
                Vector((0.685143352, 0.548078537, 0.479779691)),
            )
            progress["status"] = "CAPSULE_ROUTE_PENDING"
            progress["current_route_id"] = route_id
            atomic_json(progress_path, progress)
            path, metrics = inscribed_capsule_path(
                nodes,
                start,
                end,
                obstacle,
                corridor,
            )
            record = {
                "route_id": route_id,
                "portal_id": portal["portal_id"],
                "endpoint_id": endpoint_id,
                "search_frame": frame,
                **metrics,
                "capsule_path_found": path is not None,
                "result": (
                    "FULL_ROLL_PENDING"
                    if path is not None
                    else "inscribed_capsule_no_path"
                ),
            }
            if path is None:
                rejections["inscribed_capsule_no_path"] += 1
            else:
                record["capsule_path_points_mm"] = point_list(path)
                progress["capsule_path_route_ids"].append(route_id)
            progress["route_records"].append(record)
            progress["completed_route_ids"].append(route_id)
            completed.add(route_id)
            progress["current_route_id"] = None
            progress["rejection_counts"] = dict(sorted(rejections.items()))
            atomic_json(progress_path, progress)
    progress["status"] = "CAPSULE_ROUTE_SHARD_COMPLETE"
    atomic_json(progress_path, progress)
    print(
        json.dumps(
            {
                "status": progress["status"],
                "shard": f"{shard}/{shard_count}",
                "completed_routes": len(progress["completed_route_ids"]),
                "capsule_paths": len(progress["capsule_path_route_ids"]),
                "rejection_counts": progress["rejection_counts"],
                "progress": str(progress_path),
                "progress_sha256": sha_file(progress_path),
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
    )
    print(
        f"DONE: capsule shard {shard}/{shard_count}; "
        f"completed={len(progress['completed_route_ids'])}; "
        f"full_pending={len(progress['capsule_path_route_ids'])}"
    )
    return 0


def run_constant_roll_shard(
    report_path,
    context,
    corridor,
    attribution,
    shard,
    shard_count,
    full_roll=False,
):
    authority_path = report_path.with_name("combined_tail_authority.json")
    contract_path = report_path.with_name("v25_search_contract.json")
    portal_path = report_path.with_name("v25_portal_dedup.json")
    shard_contract_path = report_path.with_name(
        "v25_route_shard_contract.json"
    )
    equivalence_path = report_path.with_name(
        "v25_cached_astar_equivalence.json"
    )
    for path in (
        authority_path,
        contract_path,
        portal_path,
        shard_contract_path,
        *([equivalence_path] if full_roll else []),
    ):
        if not path.exists():
            raise RuntimeError(
                f"{OPERATION}: route shard {shard}/{shard_count} cannot "
                f"start; required shared checkpoint is missing: {path}"
            )
    if full_roll:
        equivalence = json.loads(
            equivalence_path.read_text(encoding="utf-8")
        )
        if not equivalence.get("all_cases_match"):
            raise RuntimeError(
                f"{OPERATION}: full-roll shard blocked because cached A* "
                f"equivalence did not pass: {equivalence_path}"
            )
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    portal_payload = json.loads(portal_path.read_text(encoding="utf-8"))
    shard_contract = json.loads(
        shard_contract_path.read_text(encoding="utf-8")
    )
    if contract["code_sha256"] != sha_file(Path(__file__)):
        raise RuntimeError(
            f"{OPERATION}: route shard code hash mismatch; rerun the shared "
            f"--escape-only preparation before launching shards"
        )
    if shard_contract["portal_dedup_sha256"] != sha_file(portal_path):
        raise RuntimeError(
            f"{OPERATION}: route shard portal checkpoint hash mismatch for "
            f"{portal_path}"
        )
    if shard_contract["shard_count"] != shard_count:
        raise RuntimeError(
            f"{OPERATION}: route shard count mismatch; checkpoint has "
            f"{shard_contract['shard_count']}, command requested {shard_count}"
        )
    assigned_ids = set(shard_contract["shards"][str(shard)])
    portals = [
        portal
        for portal in portal_payload["portals"]
        if portal["portal_id"] in assigned_ids
    ]
    progress_path = report_path.with_name(
        (
            f"v25_full_route_shard_{shard}_of_{shard_count}.json"
            if full_roll
            else f"v25_route_shard_{shard}_of_{shard_count}.json"
        )
    )
    expected = {
        "authority_sha256": sha_file(authority_path),
        "contract_sha256": sha_file(contract_path),
        "portal_dedup_sha256": sha_file(portal_path),
        "shard_contract_sha256": sha_file(shard_contract_path),
        **(
            {"cached_astar_equivalence_sha256": sha_file(equivalence_path)}
            if full_roll
            else {}
        ),
    }
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if any(progress.get(key) != value for key, value in expected.items()):
            stale = progress_path.with_name(
                f"{progress_path.stem}.stale-"
                f"{progress.get('contract_sha256', 'unknown')[:12]}.json"
            )
            progress_path.replace(stale)
            progress = {}
    else:
        progress = {}
    if not progress:
        progress = {
            "operation": OPERATION,
            "status": (
                "FULL_ROLL_SHARD_PENDING"
                if full_roll
                else "CONSTANT_ROLL_SHARD_PENDING"
            ),
            "shard": shard,
            "shard_count": shard_count,
            **expected,
            "assigned_portal_ids": [
                portal["portal_id"] for portal in portals
            ],
            "completed_route_ids": [],
            "current_route_id": None,
            "route_records": [],
            "accepted_route_records": [],
            "first_proximal_C9_contacts": [],
            "rejection_counts": {},
            "selected_result": None,
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
        }
        atomic_json(progress_path, progress)
    completed = set(progress["completed_route_ids"])
    rejections = Counter(progress["rejection_counts"])
    endpoint_map = {
        record["endpoint_id"]: record
        for record in v23.endpoint_candidates(context)
        if record["accepted"]
    }
    anchor_map = {
        record["anchor_id"]: dict(record)
        for record in authority["ordered_anchors"]
    }
    obstacles = {
        anchor_id: build_anchor_obstacles(
            context,
            corridor,
            attribution,
            anchor,
        )
        for anchor_id, anchor in anchor_map.items()
    }
    selected = progress["selected_result"]
    for portal in portals:
        samples = [
            Vector(point) for point in portal["sample_points_mm"]
        ]
        escape = {
            "samples": samples,
            "end": samples[-1],
            "end_tangent": (samples[-1] - samples[-2]).normalized(),
        }
        anchor = anchor_map[portal["anchor_id"]]
        obstacle = obstacles[portal["anchor_id"]]
        for endpoint_id in portal["accepted_endpoint_ids"]:
            route_id = f"{portal['portal_id']}:{endpoint_id}"
            if route_id in completed:
                continue
            tuple_id = next(
                alias["tuple_id"]
                for alias in portal["aliases"]
                if alias["endpoint_id"] == endpoint_id
            )
            candidate = {
                "tuple_id": tuple_id,
                "anchor_id": portal["anchor_id"],
                "endpoint_id": endpoint_id,
                "width_mm": portal["width_mm"],
                "advance_mm": portal["advance_mm"],
                "normal_offset_mm": portal["normal_offset_mm"],
                "binormal_offset_mm": portal["binormal_offset_mm"],
                "roll_degrees": portal["roll_degrees"],
            }
            endpoint = endpoint_map[endpoint_id]
            end = Vector(endpoint["coordinate_mm"])
            nodes, search_frame = v23.lattice_nodes(
                escape["end"],
                end,
                Vector((0.685143352, 0.548078537, 0.479779691)),
            )
            toward = Vector((-0.451645434, 0.836417615, -0.310518861))
            if toward.dot(escape["end"] - end) < 0:
                toward.negate()
            arrival = -toward.normalized()
            progress["status"] = (
                "FULL_ROLL_ROUTE_PENDING"
                if full_roll
                else "CONSTANT_ROLL_ROUTE_PENDING"
            )
            progress["current_route_id"] = route_id
            progress["current_route_tuple_alias"] = tuple_id
            atomic_json(progress_path, progress)
            search = (
                cached_roll_evolving_astar
                if full_roll
                else v24.cached_constant_roll_astar
            )
            route, metrics = search(
                nodes,
                escape["end"],
                end,
                escape["end_tangent"],
                arrival,
                portal["roll_degrees"],
                portal["width_mm"],
                obstacle,
                corridor,
            )
            record = {
                "route_id": route_id,
                "tuple_alias": tuple_id,
                "portal_id": portal["portal_id"],
                "endpoint_id": endpoint_id,
                "search_frame": search_frame,
                **metrics,
                "polyline_found": route is not None,
            }
            if route is None:
                rejections[
                    (
                        "roll_evolving_no_path"
                        if full_roll
                        else "constant_roll_no_path_full_pending"
                    )
                ] += 1
            else:
                scarf = exact_scarf_samples(
                    corridor["core"]["B2a"]["_samples"],
                    anchor["ring_index"],
                )
                exact = exact_candidate(
                    candidate,
                    scarf,
                    escape,
                    route,
                    corridor,
                    obstacle,
                    context,
                )
                record["polyline_points_mm"] = point_list(route["points"])
                record["exact"] = public(exact)
                progress["accepted_route_records"].append(record)
                if exact["C9_proximal_face_ids"]:
                    progress["first_proximal_C9_contacts"].append(
                        {
                            "route_id": route_id,
                            "tuple_id": tuple_id,
                            "source_face_ids": exact[
                                "C9_proximal_face_ids"
                            ],
                            "pairs": exact["collisions"]["C9_PROXIMAL"][
                                "pairs"
                            ],
                        }
                    )
                    atomic_json(progress_path, progress)
                if exact["C20_only_gate_pass"]:
                    selected = {
                        "type": "C20_ONLY",
                        "route_id": route_id,
                        "tuple_id": tuple_id,
                        "exact": public(exact),
                    }
                elif exact["paired_channel_preflight_eligible"]:
                    selected = {
                        "type": (
                            "C20_TAIL_PLUS_PROXIMAL_C9_CHANNEL"
                        ),
                        "route_id": route_id,
                        "tuple_id": tuple_id,
                        "exact": public(exact),
                    }
                else:
                    rejections["exact_route_gate"] += 1
            progress["route_records"].append(record)
            progress["completed_route_ids"].append(route_id)
            completed.add(route_id)
            progress["current_route_id"] = None
            progress["current_route_tuple_alias"] = None
            progress["rejection_counts"] = dict(sorted(rejections.items()))
            progress["selected_result"] = selected
            atomic_json(progress_path, progress)
            if selected is not None:
                break
        if selected is not None:
            break
    if selected is not None:
        progress["status"] = (
            "FULL_ROLL_POSITIVE_ROUTE_SELECTED"
            if full_roll
            else "CONSTANT_ROLL_POSITIVE_ROUTE_SELECTED"
        )
    else:
        progress["status"] = (
            "FULL_ROLL_SHARD_COMPLETE_NO_PATH"
            if full_roll
            else "CONSTANT_ROLL_SHARD_COMPLETE_FULL_ROUTE_PENDING"
        )
    atomic_json(progress_path, progress)
    print(
        json.dumps(
            {
                "status": progress["status"],
                "shard": f"{shard}/{shard_count}",
                "assigned_portals": len(portals),
                "completed_routes": len(progress["completed_route_ids"]),
                "accepted_routes": len(progress["accepted_route_records"]),
                "selected_result": selected,
                "progress": str(progress_path),
                "progress_sha256": sha_file(progress_path),
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
    )
    print(
        f"DONE: {'full-roll' if full_roll else 'constant-roll'} shard "
        f"{shard}/{shard_count} "
        f"status={progress['status']}; "
        f"completed={len(progress['completed_route_ids'])}"
    )
    return 0


def main():
    report_path = Path(v14.argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    context = v17.baseline_context()
    if context["blend_sha"] != AUTHORITY_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: authority Blend hash mismatch for "
            f"{context['blend_path']}; expected {AUTHORITY_BLEND_SHA256}, "
            f"observed {context['blend_sha']}"
        )
    attribution = json.loads(
        v23.V22_ATTRIBUTION_PATH.read_text(encoding="utf-8")
    )
    corridor = v22.v21.reconstruct_v12_core(context)
    if stable_hash(corridor["public"]) != EXPECTED_V12_SHA256:
        raise RuntimeError(
            f"{OPERATION}: reconstructed V12 corridor fingerprint mismatch"
        )
    shard_request = route_shard_argument()
    if shard_request is not None:
        if shard_request[0] == "capsule":
            return run_capsule_shard(
                report_path,
                context,
                corridor,
                attribution,
                shard_request[1],
                shard_request[2],
            )
        return run_constant_roll_shard(
            report_path,
            context,
            corridor,
            attribution,
            shard_request[1],
            shard_request[2],
            full_roll=shard_request[0] == "full_roll",
        )
    equivalence_path = validate_cached_astar(
        report_path,
        context,
        corridor,
        attribution,
    )
    capsule_validation_path = write_capsule_validation(report_path)
    c9_tree = BVHTree.FromPolygons(
        context["c9_points"],
        context["c9_faces"],
        all_triangles=False,
    )
    source_tree = BVHTree.FromPolygons(
        context["staged_points"],
        context["staged_faces"],
        all_triangles=False,
    )
    constituents = {
        name: constituent_authority(
            name,
            corridor["core"][name],
            corridor,
            c9_tree,
            source_tree,
        )
        for name in ("B0", "B1", "B2a", "B2b")
    }
    turn = constituent_authority(
        "turn_bridge",
        corridor["turn"],
        corridor,
        c9_tree,
        source_tree,
    )
    turn["geometry_fingerprint"] = turn["fingerprint"]
    turn["fingerprint"] = stable_hash(public(corridor["turn"]))
    b2a_turn = v14.overlap_pairs(
        corridor["core"]["B2a"]["_points"],
        corridor["core"]["B2a"]["_faces"],
        corridor["turn"]["_points"],
        corridor["turn"]["_faces"],
    )
    b2b_turn = v14.overlap_pairs(
        corridor["core"]["B2b"]["_points"],
        corridor["core"]["B2b"]["_faces"],
        corridor["turn"]["_points"],
        corridor["turn"]["_faces"],
    )
    b1_b2a = v14.overlap_pairs(
        corridor["core"]["B1"]["_points"],
        corridor["core"]["B1"]["_faces"],
        corridor["core"]["B2a"]["_points"],
        corridor["core"]["B2a"]["_faces"],
    )
    for ring in constituents["B2b"]["rings"]:
        related = set(ring["related_face_ids"])
        ring["turn_bridge_overlap_pairs"] = [
            list(pair) for pair in b2b_turn if pair[0] in related
        ]
    opening_points, opening_faces, opening = v23.opening_keepout(context)
    t0 = {
        "source_face_ids": [2741, 4711],
        "face_records": v23.face_catalog(context, [2741, 4711]),
        "boundary_edges": [
            list(edge)
            for edge in v23.boundary_edges(
                [2741, 4711],
                context["staged_faces"],
            )
        ],
    }
    authority = {
        "operation": OPERATION,
        "status": "COMBINED_TAIL_AUTHORITY_CHECKPOINTED",
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "constituents": constituents,
        "turn_bridge": turn,
        "contacts": {
            "B1_to_B2a": [list(pair) for pair in b1_b2a],
            "B2a_to_turn_bridge": [list(pair) for pair in b2a_turn],
            "turn_bridge_to_B2b": [
                [second, first] for first, second in b2b_turn
            ],
        },
        "adjacency_graph": [
            ["B1", "B2a"],
            ["B2a", "turn_bridge"],
            ["turn_bridge", "B2b"],
        ],
        "source_controls": {
            "B2a": [2118, 2115, 2114, 2111, 2108],
            "B2b": [2108, 2119],
            "B0_tip": 2074,
            "B2b_tip": 2119,
            "C_tip_gap_mm": context["checks"]["tip_gap_mm"],
        },
        "fingerprints": {
            "B0": constituents["B0"]["fingerprint"],
            "B1": constituents["B1"]["fingerprint"],
            "B2a_complete": constituents["B2a"]["fingerprint"],
            "turn_bridge": turn["fingerprint"],
            "B2b": constituents["B2b"]["fingerprint"],
            "v12_corridor": stable_hash(corridor["public"]),
            "source_cage": context["checks"]["retained_fingerprint"],
            "C9": context["checks"]["component_9_fingerprint"],
            "Branch_A": attribution["immutable_complements"][
                "branch_a_fingerprint"
            ],
            "T0_landing": stable_hash(t0),
            "central_opening_keep_out": stable_hash(
                {
                    "record": opening,
                    "points": point_list(opening_points),
                    "faces": [list(face) for face in opening_faces],
                }
            ),
            "B1_to_B2a_junction": stable_hash(
                [list(pair) for pair in b1_b2a]
            ),
        },
        "T0_landing": t0,
        "central_opening_keep_out": opening,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    authority.update(resolve_anchors(context, corridor, authority))
    authority["fingerprints"]["B2a_prefixes"] = {
        anchor["anchor_id"]: anchor["prefix_fingerprint"]
        for anchor in authority["ordered_anchors"]
    }
    authority_path = report_path.with_name("combined_tail_authority.json")
    atomic_json(authority_path, authority)
    authority_sha = sha_file(authority_path)
    code_sha = sha_file(Path(__file__))
    tuple_count = (
        len(authority["ordered_anchors"])
        * 3
        * len(WIDTHS_MM)
        * len(ADVANCES_MM)
        * len(OFFSETS_MM)
        * len(OFFSETS_MM)
        * len(ROLLS_DEGREES)
    )
    contract = {
        "operation": OPERATION,
        "status": "V25_SEARCH_CONTRACT_CHECKPOINTED",
        "authority_sha256": authority_sha,
        "code_sha256": code_sha,
        "cached_astar_equivalence_sha256": sha_file(equivalence_path),
        "capsule_prefilter_validation_sha256": sha_file(
            capsule_validation_path
        ),
        "ordered_anchor_ids": [
            anchor["anchor_id"] for anchor in authority["ordered_anchors"]
        ],
        "ordered_anchor_records": authority["ordered_anchors"],
        "ordered_endpoint_ids": ["E0", "E1", "E2"],
        "ordered_widths_mm": list(WIDTHS_MM),
        "ordered_advances_mm": list(ADVANCES_MM),
        "ordered_normal_offsets_mm": list(OFFSETS_MM),
        "ordered_binormal_offsets_mm": list(OFFSETS_MM),
        "ordered_roll_knots_degrees": list(ROLLS_DEGREES),
        "candidate_tuple_schema": (
            "anchor_id:endpoint_id:width_mm:advance_mm:"
            "normal_offset_mm:binormal_offset_mm:roll_degrees"
        ),
        "candidate_tuple_count": tuple_count,
        "bounds": {
            "maximum_replaced_B2a_arclength_mm": 12.0,
            "scarf_length_mm": 6.0,
            "escape_length_mm": [6.0, 18.0],
            "maximum_radial_offset_mm": 12.0,
            "anchor_tangent_deflection_degrees": 30,
            "escape_tangent_deflection_degrees": 45,
            "lattice_spacing_mm": 4.0,
            "transverse_bounds_mm": [-24.0, 24.0],
            "maximum_chord_distance_mm": 28.0,
            "minimum_cutter_margin_mm": 1.7,
            "thickness_mm": 2.4,
        },
        "obstacle_fingerprints": {
            "source_cage": authority["fingerprints"]["source_cage"],
            "C9": authority["fingerprints"]["C9"],
            "Branch_A": authority["fingerprints"]["Branch_A"],
            "central_opening_keep_out": authority["fingerprints"][
                "central_opening_keep_out"
            ],
            "v12_corridor": authority["fingerprints"]["v12_corridor"],
        },
        "resume_contract": (
            "authority, contract, code, and obstacle hashes must all match"
        ),
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    contract_path = report_path.with_name("v25_search_contract.json")
    atomic_json(contract_path, contract)
    search = run_search(
        report_path,
        context,
        corridor,
        attribution,
        authority,
        contract_path,
        authority_path,
        escape_only="--escape-only" in sys.argv,
    )
    progress = json.loads(
        search["progress_path"].read_text(encoding="utf-8")
    )
    selected = search["selected"]
    route_path = report_path.with_name("v25_route_preflight.json")
    route_payload = {
        "operation": OPERATION,
        "status": search["status"],
        "authority_sha256": authority_sha,
        "contract_sha256": sha_file(contract_path),
        "fixed_candidate_tuple_count": tuple_count,
        "completed_tuple_count": search["completed_tuple_count"],
        "accepted_escape_records": progress["accepted_escape_records"],
        "accepted_route_records": progress["accepted_route_records"],
        "first_proximal_C9_contacts": progress[
            "first_proximal_C9_contacts"
        ],
        "rejection_counts_by_exact_obstacle": search["rejection_counts"],
        "obstacle_catalogs_by_anchor": search[
            "obstacle_catalogs_by_anchor"
        ],
        "selected_complete_pair": selected,
        "hard_stop": (
            {
                "operation": "fixed_A0_authored_tail_search",
                "target": "A0_R18_to_T0_E0_E1_E2",
                "actionable_reason": (
                    "No complete authored-tail/C9-channel pair passed the "
                    "fixed 11,907-tuple contract; expansion into B1 or beyond "
                    "the 12 mm B2a suffix bound requires a new decision."
                ),
            }
            if selected is None
            and search["status"] == "NO_SAFE_AUTHORED_TAIL_ROUTE_V25"
            else None
        ),
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    atomic_json(route_path, route_payload)
    c9_mask = (
        selected["exact"]["C9_proximal_face_ids"]
        if selected is not None
        and selected["type"] == "C20_TAIL_PLUS_PROXIMAL_C9_CHANNEL"
        else []
    )
    allowlist_path = report_path.with_name(
        "v25_joint_allowlist_preflight.json"
    )
    allowlist = {
        "operation": OPERATION,
        "status": search["status"],
        "authored_C20_replacement_scope": (
            {
                "B2a_anchor": selected["tuple_id"].split("_")[0],
                "retired_B2a_suffix_from_ring": "R18",
                "retired_turn_bridge": True,
                "retired_B2b": True,
            }
            if selected is not None
            else None
        ),
        "C20_T0_mask": [2741, 4711],
        "C9_base_mask": c9_mask,
        "C9_transition_ring": [],
        "visible_C20_island": None,
        "immutable_complement_fingerprints": {
            "B0": authority["fingerprints"]["B0"],
            "B1": authority["fingerprints"]["B1"],
            "B2a_prefix_A0": authority["fingerprints"]["B2a_prefixes"][
                "A0"
            ],
            "source_cage": authority["fingerprints"]["source_cage"],
            "C9": authority["fingerprints"]["C9"],
            "Branch_A": authority["fingerprints"]["Branch_A"],
            "central_opening": authority["fingerprints"][
                "central_opening_keep_out"
            ],
        },
        "mutation_authority": False,
    }
    atomic_json(allowlist_path, allowlist)
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": search["status"],
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "combined_tail_authority": str(authority_path),
        "combined_tail_authority_sha256": authority_sha,
        "v25_search_contract": str(contract_path),
        "v25_search_contract_sha256": sha_file(contract_path),
        "v25_cached_astar_equivalence": str(equivalence_path),
        "v25_cached_astar_equivalence_sha256": sha_file(
            equivalence_path
        ),
        "v25_capsule_prefilter_validation": str(
            capsule_validation_path
        ),
        "v25_capsule_prefilter_validation_sha256": sha_file(
            capsule_validation_path
        ),
        "v25_progress": str(search["progress_path"]),
        "v25_progress_sha256": sha_file(search["progress_path"]),
        "v25_portal_dedup": str(search["portal_path"]),
        "v25_portal_dedup_sha256": sha_file(search["portal_path"]),
        "v25_route_shard_contract": str(
            search["shard_contract_path"]
        ),
        "v25_route_shard_contract_sha256": sha_file(
            search["shard_contract_path"]
        ),
        "v25_route_preflight": str(route_path),
        "v25_route_preflight_sha256": sha_file(route_path),
        "v25_joint_allowlist_preflight": str(allowlist_path),
        "v25_joint_allowlist_preflight_sha256": sha_file(allowlist_path),
        "ordered_anchors": authority["ordered_anchors"],
        "candidate_tuple_count": tuple_count,
        "completed_tuple_count": search["completed_tuple_count"],
        "accepted_escape_count": search["accepted_escape_count"],
        "unique_portal_count": search["unique_portal_count"],
        "route_attempt_count": search["route_attempt_count"],
        "accepted_route_count": search["accepted_route_count"],
        "first_proximal_C9_contact_count": search[
            "first_proximal_C9_contact_count"
        ],
        "rejection_counts": search["rejection_counts"],
        "selected_result": selected,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "gate_pass": selected is not None,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(report_path, report)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: V25 authored-tail search status={search['status']}; "
        f"completed={search['completed_tuple_count']}/{tuple_count}; "
        f"accepted_escapes={search['accepted_escape_count']}; "
        f"accepted_routes={search['accepted_route_count']}; "
        "mutation_started=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
