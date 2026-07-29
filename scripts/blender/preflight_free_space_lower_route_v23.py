"""Read-only bounded free-space preflight for Repair 014 v23."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from heapq import heappop, heappush
import json
from math import acos, ceil, degrees, floor, radians, sqrt
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
import build_elevated_surface_saddles_v20 as v20  # noqa: E402


OPERATION = "FREE_SPACE_LOWER_ROUTE_V23"
NO_ROUTE = "NO_SAFE_FREE_SPACE_LOWER_ROUTE_V23"
VISIBLE_DECISION = "VISIBLE_C20_RECONSTRUCTION_DECISION_REQUIRED_V23"
NO_VISIBLE = "NO_BOUNDED_VISIBLE_C20_REPLACEMENT_V23"
V22_ATTRIBUTION_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v22/exact_overlap_attribution.json"
)
V22_ATTRIBUTION_SHA256 = (
    "d80989e71a37423ac2d3717c0384e8db23ae848fdf97ea97490a23dfa97c9624"
)
LANDING_FACE_IDS = (2741, 4711)
ENDPOINT_SOURCE_IDS = (1892, 1893, 1894, 3054)
WIDTHS_MM = (6.0, 5.25, 4.5)
THICKNESS_MM = 2.4
GAPS_MM = (0.4, 0.6, 0.8)
LATTICE_MM = 4.0
TRANSVERSE_MM = 24.0
CHORD_DISTANCE_LIMIT_MM = 28.0
DEPARTURE_DEFLECTIONS = (0, -15, 15, -30, 30)
DEPARTURE_ROLLS = (0, -15, 15, -30, 30, -45, 45)


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value):
    return sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def merge_geometries(geometries):
    points = []
    faces = []
    for source_points, source_faces in geometries:
        offset = len(points)
        points.extend(point.copy() for point in source_points)
        faces.extend(
            tuple(offset + index for index in face)
            for face in source_faces
        )
    return points, faces


def local_geometry(points, faces, face_ids):
    vertex_ids = sorted(
        {
            vertex
            for face_id in face_ids
            for vertex in faces[face_id]
        }
    )
    remap = {
        source_id: local_id
        for local_id, source_id in enumerate(vertex_ids)
    }
    return (
        [points[source_id].copy() for source_id in vertex_ids],
        [
            tuple(remap[vertex] for vertex in faces[face_id])
            for face_id in face_ids
        ],
        vertex_ids,
    )


def face_catalog(context, face_ids):
    records = []
    for face_id in sorted(face_ids):
        face = context["staged_faces"][face_id]
        records.append(
            {
                "source_face_id": face_id,
                "loop_source_vertex_ids": list(face),
                "coordinates_mm": [
                    [
                        float(value)
                        for value in context["staged_points"][vertex]
                    ]
                    for vertex in face
                ],
                "material_index": context["staged_materials"][face_id],
            }
        )
    return records


def boundary_edges(face_ids, faces):
    counts = Counter()
    for face_id in face_ids:
        face = faces[face_id]
        for first, second in zip(face, (*face[1:], face[0])):
            counts[tuple(sorted((first, second)))] += 1
    return sorted(edge for edge, count in counts.items() if count == 1)


def area_weighted_centroid(points, faces, face_ids):
    total = 0.0
    weighted = Vector()
    for face_id in face_ids:
        face = faces[face_id]
        origin = points[face[0]]
        for index in range(1, len(face) - 1):
            second = points[face[index]]
            third = points[face[index + 1]]
            area = 0.5 * (second - origin).cross(third - origin).length
            weighted += (origin + second + third) / 3.0 * area
            total += area
    if total <= 1.0e-12:
        raise RuntimeError(f"{OPERATION}: landing centroid area collapsed")
    return weighted / total


def point_in_triangle(point, a, b, c, normal):
    signs = []
    for first, second in ((a, b), (b, c), (c, a)):
        signs.append((second - first).cross(point - first).dot(normal))
    return all(value >= -1.0e-5 for value in signs) or all(
        value <= 1.0e-5 for value in signs
    )


def landing_footprint_gate(center, context):
    tangent = Vector(
        (-0.451645434, 0.836417615, -0.310518861)
    ).normalized()
    normal = Vector((0.685143352, 0.548078537, 0.479779691)).normalized()
    across = normal.cross(tangent).normalized()
    triangles = [
        tuple(context["staged_points"][vertex] for vertex in face)
        for face in (
            context["staged_faces"][LANDING_FACE_IDS[0]],
            context["staged_faces"][LANDING_FACE_IDS[1]],
        )
    ]
    samples = [
        center + tangent * along + across * transverse
        for along in (-5.0, 0.0, 5.0)
        for transverse in (-3.5, 0.0, 3.5)
    ]
    gate = all(
        any(
            point_in_triangle(sample, *triangle, normal)
            for triangle in triangles
        )
        for sample in samples
    )
    return gate


def endpoint_candidates(context):
    points = context["staged_points"]
    e0 = points[1894].copy()
    e1 = e0.lerp(
        points[1893],
        1.5 / (points[1893] - e0).length,
    )
    e2 = e0.lerp(
        points[3054],
        1.5 / (points[3054] - e0).length,
    )
    e3 = area_weighted_centroid(
        points,
        context["staged_faces"],
        LANDING_FACE_IDS,
    )
    return [
        {"endpoint_id": "E0", "coordinate_mm": list(e0), "accepted": True},
        {"endpoint_id": "E1", "coordinate_mm": list(e1), "accepted": True},
        {"endpoint_id": "E2", "coordinate_mm": list(e2), "accepted": True},
        {
            "endpoint_id": "E3",
            "coordinate_mm": list(e3),
            "accepted": landing_footprint_gate(e3, context),
            "rejection_reason": (
                None
                if landing_footprint_gate(e3, context)
                else "10x7 footprint does not remain inside F2741/F4711"
            ),
        },
    ]


def b2b_portal(corridor):
    record = corridor["core"]["B2b"]
    samples = record["_samples"]
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(
        samples,
        tangents,
        corridor["target_length"],
    )
    width_axis, normal = v8.rotated_frame(
        frames[-1][0],
        tangents[-1],
        record["roll_degrees"],
    )
    return {
        "source_control_id": 2119,
        "center_mm": [float(value) for value in samples[-1]],
        "ordered_ring_vertices_mm": [
            [float(value) for value in point]
            for point in record["_points"][-5:]
        ],
        "tangent": [float(value) for value in tangents[-1]],
        "parallel_transport_normal": [float(value) for value in normal],
        "parallel_transport_binormal": [
            float(value) for value in width_axis
        ],
        "roll_degrees": record["roll_degrees"],
        "section_mm": [6.0, 2.4],
        "preceding_centerline_samples_mm": [
            [float(value) for value in point] for point in samples[-3:-1]
        ],
        "_center": samples[-1].copy(),
        "_tangent": tangents[-1].copy(),
        "_normal": normal.copy(),
        "_binormal": width_axis.copy(),
    }


def opening_keepout(context):
    group = context["mapping"]["exact_source_open_edges"]["groups"][0]
    edge_ids = [tuple(edge) for edge in group["edge_vertex_ids"]]
    vertex_ids = sorted(group["vertex_ids"])
    centroid = sum(
        (context["staged_points"][vertex] for vertex in vertex_ids),
        Vector(),
    ) / len(vertex_ids)
    points = [
        context["staged_points"][vertex].copy() for vertex in vertex_ids
    ]
    local = {
        source_id: local_id
        for local_id, source_id in enumerate(vertex_ids)
    }
    center_id = len(points)
    points.append(centroid)
    faces = [
        (local[first], local[second], center_id)
        for first, second in edge_ids
    ]
    record = {
        "source_vertex_ids": vertex_ids,
        "edge_vertex_ids": [list(edge) for edge in edge_ids],
        "coordinates_mm": [
            [float(value) for value in context["staged_points"][vertex]]
            for vertex in vertex_ids
        ],
    }
    return points, faces, {**record, "fingerprint": stable_hash(record)}


def obstacle_context(context, corridor, attribution):
    target_length = corridor["target_length"]
    c9_class = attribution["component_9_classification"]
    proximal = set(c9_class["proximal_wearer_facing"]["incident_face_ids"])
    c9_component_faces = set(
        v22.c9_source_context(
            context,
            target_length,
            corridor["grid"],
        )["component_face_ids"]
    )
    nonprox_c9 = sorted(c9_component_faces - proximal)
    c20_catalog = v22.face_catalog(
        context["retained_face_ids"],
        context["staged_points"],
        context["staged_faces"],
        context["staged_materials"],
        target_length,
    )
    exterior_c20 = sorted(
        int(face_id)
        for face_id, record in c20_catalog.items()
        if record["orientation"] == "exterior_facing"
        and int(face_id) not in LANDING_FACE_IDS
    )
    c20_points, c20_faces, c20_vertices = local_geometry(
        context["staged_points"],
        context["staged_faces"],
        exterior_c20,
    )
    c9_points, c9_faces, c9_vertices = local_geometry(
        context["staged_points"],
        context["staged_faces"],
        nonprox_c9,
    )
    terminals = v20.terminal_context(context)
    branch_a = v17.candidate(
        1.5,
        context["staged_points"][5702],
        context["staged_points"][1784],
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
        corridor["grid"],
    )
    branch_points, branch_faces = merge_geometries(
        (
            (branch_a["_upper_points"], branch_a["_upper_faces"]),
            (branch_a["_bridge_points"], branch_a["_bridge_faces"]),
            (branch_a["_lower_points"], branch_a["_lower_faces"]),
        )
    )
    b2b = corridor["core"]["B2b"]
    b2b_samples = b2b["_samples"]
    retained_b2b_rings = len(b2b_samples)
    cumulative = 0.0
    for index in range(len(b2b_samples) - 1, 0, -1):
        cumulative += (
            b2b_samples[index] - b2b_samples[index - 1]
        ).length
        if cumulative >= 6.0:
            retained_b2b_rings = index
            break
    b2b_point_limit = retained_b2b_rings * 5
    b2b_faces = [
        face
        for face in b2b["_faces"]
        if max(face) < b2b_point_limit
    ]
    v12_points, v12_faces = merge_geometries(
        (
            (
                corridor["core"]["B0"]["_points"],
                corridor["core"]["B0"]["_faces"],
            ),
            (
                corridor["core"]["B1"]["_points"],
                corridor["core"]["B1"]["_faces"],
            ),
            (
                corridor["core"]["B2a"]["_points"],
                corridor["core"]["B2a"]["_faces"],
            ),
            (corridor["turn"]["_points"], corridor["turn"]["_faces"]),
            (b2b["_points"][:b2b_point_limit], b2b_faces),
        )
    )
    opening_points, opening_faces, opening_record = opening_keepout(context)
    catalogs = {
        "C20_EXTERIOR": {
            "source_face_ids": exterior_c20,
            "source_vertex_ids": c20_vertices,
            "face_records": face_catalog(context, exterior_c20),
        },
        "C9_NONPROXIMAL": {
            "source_face_ids": nonprox_c9,
            "source_vertex_ids": c9_vertices,
            "face_records": face_catalog(context, nonprox_c9),
        },
        "CUTTER": {
            "vertex_count": len(context["cutter_points"]),
            "face_count": len(context["cutter_faces"]),
            "fingerprint": stable_hash(
                {
                    "points": [
                        [float(value) for value in point]
                        for point in context["cutter_points"]
                    ],
                    "faces": [list(face) for face in context["cutter_faces"]],
                }
            ),
        },
        "BRANCH_A": {
            "vertex_count": len(branch_points),
            "face_count": len(branch_faces),
            "fingerprint": stable_hash(
                {
                    "points": [
                        [float(value) for value in point]
                        for point in branch_points
                    ],
                    "faces": [list(face) for face in branch_faces],
                }
            ),
        },
        "V12_IMMUTABLE_EXCEPT_B2B_SCARF": {
            "vertex_count": len(v12_points),
            "face_count": len(v12_faces),
            "fingerprint": stable_hash(
                {
                    "points": [
                        [float(value) for value in point]
                        for point in v12_points
                    ],
                    "faces": [list(face) for face in v12_faces],
                }
            ),
        },
        "CENTRAL_OPENING_KEEP_OUT": opening_record,
    }
    for key in ("C20_EXTERIOR", "C9_NONPROXIMAL"):
        catalogs[key]["fingerprint"] = stable_hash(catalogs[key])
    return {
        "catalogs": catalogs,
        "trees": {
            "C20_EXTERIOR": BVHTree.FromPolygons(
                c20_points, c20_faces, all_triangles=False
            ),
            "C9_NONPROXIMAL": BVHTree.FromPolygons(
                c9_points, c9_faces, all_triangles=False
            ),
            "BRANCH_A": BVHTree.FromPolygons(
                branch_points, branch_faces, all_triangles=False
            ),
            "V12_IMMUTABLE": BVHTree.FromPolygons(
                v12_points, v12_faces, all_triangles=False
            ),
            "OPENING": BVHTree.FromPolygons(
                opening_points, opening_faces, all_triangles=False
            ),
        },
        "source": {
            "C20_EXTERIOR": (c20_points, c20_faces, exterior_c20),
            "C9_NONPROXIMAL": (c9_points, c9_faces, nonprox_c9),
            "BRANCH_A": (branch_points, branch_faces, None),
            "V12_IMMUTABLE": (v12_points, v12_faces, None),
            "OPENING": (opening_points, opening_faces, None),
        },
    }


def search_frame(start, end, normal):
    chord = end - start
    length = chord.length
    u = chord.normalized()
    first = normal - u * normal.dot(u)
    fallback = False
    if first.length <= 1.0e-8:
        first = Vector((0.685143352, 0.548078537, 0.479779691))
        first -= u * first.dot(u)
        fallback = True
    first.normalize()
    second = u.cross(first).normalized()
    return u, first, second, length, fallback


def ring_points(center, tangent, roll_degrees, width, target_length):
    _, _, _, radial = v4.radial_coordinates(center, target_length)
    normal = radial - tangent * radial.dot(tangent)
    if normal.length <= 1.0e-8:
        return None
    normal.normalize()
    width_axis = normal.cross(tangent).normalized()
    rotation = Quaternion(tangent, radians(roll_degrees))
    width_axis = (rotation @ width_axis).normalized()
    normal = tangent.cross(width_axis).normalized()
    c20 = center + width_axis * width
    outward_c9 = center + normal * THICKNESS_MM
    outward_c20 = c20 + normal * THICKNESS_MM
    return [
        center.copy(),
        outward_c9,
        outward_c9.lerp(outward_c20, 0.5),
        outward_c20,
        c20,
    ]


def point_clearance(point, tree):
    nearest = tree.find_nearest(point)
    return float("inf") if nearest is None else nearest[3]


def segment_gate(
    first,
    second,
    roll,
    width,
    obstacles,
    corridor,
    ignore_c20=False,
):
    delta = second - first
    length = delta.length
    if length <= 1.0e-8:
        return False, "degenerate_edge"
    tangent = delta.normalized()
    steps = max(1, int(ceil(length / 2.0)))
    for index in range(steps + 1):
        center = first.lerp(second, index / steps)
        ring = ring_points(
            center,
            tangent,
            roll,
            width,
            corridor["target_length"],
        )
        if ring is None:
            return False, "frame_collapse"
        margins = v4.v2.point_margins(
            ring,
            corridor["target_length"],
            corridor["grid"],
        )
        if min(margins) < 1.7:
            return False, "cutter"
        for name, tree in obstacles["trees"].items():
            if ignore_c20 and name == "C20_EXTERIOR":
                continue
            if any(point_clearance(point, tree) < 0.4 for point in ring):
                return False, name
    return True, None


def lattice_nodes(start, end, normal):
    u, first, second, chord, fallback = search_frame(start, end, normal)
    l_min = -4.0
    l_max = chord + 4.0
    l_values = [
        l_min + LATTICE_MM * index
        for index in range(
            int(floor((l_max - l_min) / LATTICE_MM)) + 1
        )
    ]
    if l_values[-1] < l_max - 1.0e-6:
        l_values.append(l_max)
    transverse = [
        -TRANSVERSE_MM + LATTICE_MM * index for index in range(13)
    ]
    nodes = {}
    for li, longitudinal in enumerate(l_values):
        for ai, a_value in enumerate(transverse):
            for bi, b_value in enumerate(transverse):
                if sqrt(a_value * a_value + b_value * b_value) > (
                    CHORD_DISTANCE_LIMIT_MM + 1.0e-6
                ):
                    continue
                nodes[(li, ai, bi)] = (
                    start
                    + u * longitudinal
                    + first * a_value
                    + second * b_value
                )
    return nodes, {
        "u": list(u),
        "first_transverse": list(first),
        "second_transverse": list(second),
        "chord_length_mm": chord,
        "normal_projection_fallback": fallback,
        "longitudinal_bounds_mm": [l_min, l_max],
        "transverse_bounds_mm": [-24.0, 24.0],
        "lattice_spacing_mm": LATTICE_MM,
        "node_count": len(nodes),
    }


NEIGHBORS = [
    (x, y, z)
    for x in (-1, 0, 1)
    for y in (-1, 0, 1)
    for z in (-1, 0, 1)
    if (x, y, z) != (0, 0, 0)
]


def turn_degrees(first, second):
    return degrees(
        acos(
            max(
                -1.0,
                min(1.0, first.normalized().dot(second.normalized())),
            )
        )
    )


def astar(
    nodes,
    start,
    end,
    start_tangent,
    end_tangent,
    roll,
    width,
    obstacles,
    corridor,
    ignore_c20=False,
):
    initial = []
    for key, point in nodes.items():
        delta = point - start
        if 2.0 <= delta.length <= 7.0 and turn_degrees(
            start_tangent,
            delta,
        ) <= 45.0:
            gate, _ = segment_gate(
                start,
                point,
                roll,
                width,
                obstacles,
                corridor,
                ignore_c20,
            )
            if gate:
                initial.append((key, delta.normalized()))
    queue = []
    best = {}
    parent = {}
    counter = 0
    for key, direction in initial:
        cost = (nodes[key] - start).length
        state = (key, tuple(round(value, 6) for value in direction), roll)
        best[state] = cost
        heappush(queue, (cost + (end - nodes[key]).length, counter, state))
        counter += 1
        parent[state] = None
    rejection_counts = Counter()
    for key, point in nodes.items():
        delta = point - start
        if 2.0 <= delta.length <= 7.0 and turn_degrees(
            start_tangent,
            delta,
        ) <= 45.0:
            gate, reason = segment_gate(
                start,
                point,
                roll,
                width,
                obstacles,
                corridor,
                ignore_c20,
            )
            if not gate:
                rejection_counts[f"initial_{reason}"] += 1
    goal = None
    while queue:
        _, _, state = heappop(queue)
        key, direction_values, state_roll = state
        current = nodes[key]
        cost = best[state]
        incoming = Vector(direction_values)
        delta_to_end = end - current
        if 2.0 <= delta_to_end.length <= 7.0 and turn_degrees(
            incoming,
            delta_to_end,
        ) <= 45.0 and turn_degrees(
            delta_to_end,
            end_tangent,
        ) <= 45.0:
            gate, reason = segment_gate(
                current,
                end,
                state_roll,
                width,
                obstacles,
                corridor,
                ignore_c20,
            )
            if gate:
                goal = state
                break
            rejection_counts[reason] += 1
        li, ai, bi = key
        for offset in NEIGHBORS:
            following_key = (
                li + offset[0],
                ai + offset[1],
                bi + offset[2],
            )
            if following_key not in nodes:
                continue
            following = nodes[following_key]
            outgoing = following - current
            if turn_degrees(incoming, outgoing) > 45.0:
                continue
            for roll_delta in (-15, 0, 15):
                following_roll = state_roll + roll_delta
                if not -180 <= following_roll <= 180:
                    continue
                gate, reason = segment_gate(
                    current,
                    following,
                    following_roll,
                    width,
                    obstacles,
                    corridor,
                    ignore_c20,
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
                heuristic = (end - following).length
                heappush(
                    queue,
                    (
                        following_cost + heuristic,
                        counter,
                        following_state,
                    ),
                )
                counter += 1
    if goal is None:
        return None, {
            "expanded_state_count": len(best),
            "edge_rejection_counts": dict(sorted(rejection_counts.items())),
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
    }


def de_boor(control, sample_count):
    degree = 3
    count = len(control)
    knots = (
        [0.0] * (degree + 1)
        + [
            index / (count - degree)
            for index in range(1, count - degree)
        ]
        + [1.0] * (degree + 1)
    )
    result = []
    for sample in range(sample_count + 1):
        t = sample / sample_count
        if t >= 1.0:
            result.append(control[-1].copy())
            continue
        span = max(
            degree,
            min(
                count - 1,
                next(
                    index
                    for index in range(degree, count)
                    if knots[index] <= t < knots[index + 1]
                ),
            ),
        )
        work = [
            control[span - degree + index].copy()
            for index in range(degree + 1)
        ]
        for level in range(1, degree + 1):
            for index in range(degree, level - 1, -1):
                left = knots[span - degree + index]
                right = knots[span + 1 + index - level]
                alpha = 0.0 if right == left else (t - left) / (right - left)
                work[index] = work[index - 1].lerp(work[index], alpha)
        result.append(work[degree])
    return result


def fit_spline(polyline):
    cumulative = [0.0]
    for first, second in zip(polyline, polyline[1:]):
        cumulative.append(cumulative[-1] + (second - first).length)
    total = cumulative[-1]
    controls = [polyline[0]]
    for fraction in (0.25, 0.5, 0.75):
        target = total * fraction
        index = next(
            index
            for index in range(1, len(cumulative))
            if cumulative[index] >= target
        )
        local = (
            (target - cumulative[index - 1])
            / (cumulative[index] - cumulative[index - 1])
        )
        controls.append(polyline[index - 1].lerp(polyline[index], local))
    controls.append(polyline[-1])
    samples = de_boor(controls, max(2, int(ceil(total / 2.0))))
    maximum_error = max(
        min((point - source).length for source in polyline)
        for point in samples
    )
    tangents = [
        (second - first).normalized()
        for first, second in zip(samples, samples[1:])
    ]
    maximum_turn = max(
        (
            turn_degrees(first, second)
            for first, second in zip(tangents, tangents[1:])
        ),
        default=0.0,
    )
    return {
        "control_points": controls,
        "samples": samples,
        "maximum_fit_error_mm": maximum_error,
        "maximum_sample_turn_degrees": maximum_turn,
        "length_mm": sum(
            (second - first).length
            for first, second in zip(samples, samples[1:])
        ),
    }


def sweep_samples(samples, rolls, width, target_length):
    points = []
    for index, center in enumerate(samples):
        tangent = (
            samples[index + 1] - center
            if index == 0
            else center - samples[index - 1]
            if index == len(samples) - 1
            else samples[index + 1] - samples[index - 1]
        ).normalized()
        roll = rolls[
            min(
                len(rolls) - 1,
                int(round(index * (len(rolls) - 1) / (len(samples) - 1))),
            )
        ]
        ring = ring_points(center, tangent, roll, width, target_length)
        points.extend(ring)
    faces = v4.v2.base.positive_faces(
        points,
        v8.closed_faces(len(samples)),
    )
    return points, faces


def exact_collision_record(
    route_id,
    spline,
    rolls,
    width,
    obstacles,
    context,
    corridor,
):
    points, faces = sweep_samples(
        spline["samples"],
        rolls,
        width,
        corridor["target_length"],
    )
    collisions = {}
    for name, geometry in obstacles["source"].items():
        pairs = v14.overlap_pairs(points, faces, geometry[0], geometry[1])
        collisions[name] = {
            "pair_count": len(pairs),
            "pairs": [list(pair) for pair in pairs],
            "source_face_ids": (
                sorted(
                    {
                        geometry[2][pair[1]]
                        for pair in pairs
                    }
                )
                if geometry[2] is not None
                else None
            ),
        }
    cutter_pairs = v14.overlap_pairs(
        points,
        faces,
        context["cutter_points"],
        context["cutter_faces"],
    )
    self_pairs = v4.v2.ribbon_self_overlaps(
        points,
        faces,
        len(spline["samples"]),
    )
    margins = v4.v2.point_margins(
        points,
        corridor["target_length"],
        corridor["grid"],
    )
    quality = v4.v2.triangulated_quality(points, faces)
    audit = v4.v2.base.audit_geometry(points, faces)
    gate = all(
        (
            all(record["pair_count"] == 0 for record in collisions.values()),
            not cutter_pairs,
            not self_pairs,
            min(margins) >= 1.7,
            spline["maximum_fit_error_mm"] <= 0.5,
            spline["maximum_sample_turn_degrees"] <= 30.0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
        )
    )
    return {
        "route_id": route_id,
        "width_mm": width,
        "thickness_mm": THICKNESS_MM,
        "control_points_mm": [
            [float(value) for value in point]
            for point in spline["control_points"]
        ],
        "sample_points_mm": [
            [float(value) for value in point] for point in spline["samples"]
        ],
        "maximum_fit_error_mm": round(
            spline["maximum_fit_error_mm"], 6
        ),
        "maximum_sample_turn_degrees": round(
            spline["maximum_sample_turn_degrees"], 6
        ),
        "spline_length_mm": round(spline["length_mm"], 6),
        "collisions": collisions,
        "cutter_overlap_pairs": [list(pair) for pair in cutter_pairs],
        "self_overlap_pairs": [list(pair) for pair in self_pairs],
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "triangle_quality": quality,
        "audit": audit,
        "gate_pass": gate,
        "_points": points,
        "_faces": faces,
    }


def visible_fallback(records, obstacles, context, target_length):
    candidates = []
    exterior_face_ids = obstacles["source"]["C20_EXTERIOR"][2]
    for record in records:
        hits = record["collisions"]["C20_EXTERIOR"]["source_face_ids"] or []
        other_clear = all(
            record["collisions"][name]["pair_count"] == 0
            for name in (
                "C9_NONPROXIMAL",
                "BRANCH_A",
                "V12_IMMUTABLE",
                "OPENING",
            )
        ) and not record["cutter_overlap_pairs"] and not record[
            "self_overlap_pairs"
        ] and record["minimum_cutter_margin_mm"] >= 1.7
        if not hits or not other_clear:
            continue
        islands = v22.connected_face_islands(
            hits,
            context["staged_faces"],
        )
        island_records = []
        for island in islands:
            vertices = sorted(
                {
                    vertex
                    for face_id in island
                    for vertex in context["staged_faces"][face_id]
                }
            )
            edges = boundary_edges(island, context["staged_faces"])
            area = 0.0
            stations = []
            for face_id in island:
                face = context["staged_faces"][face_id]
                origin = context["staged_points"][face[0]]
                for index in range(1, len(face) - 1):
                    area += 0.5 * (
                        context["staged_points"][face[index]] - origin
                    ).cross(
                        context["staged_points"][face[index + 1]] - origin
                    ).length
                for vertex in face:
                    stations.append(
                        v4.radial_coordinates(
                            context["staged_points"][vertex],
                            target_length,
                        )[0]
                        * target_length
                    )
            island_records.append(
                {
                    "face_ids": island,
                    "vertex_ids": vertices,
                    "face_records": face_catalog(context, island),
                    "boundary_edges": [list(edge) for edge in edges],
                    "area_mm2": round(area, 6),
                    "station_bounds_mm": [
                        round(min(stations), 6),
                        round(max(stations), 6),
                    ],
                    "zero_ring_mask": island,
                    "one_ring_mask": sorted(
                        set(island)
                        | {
                            face_id
                            for face_id in exterior_face_ids
                            if any(
                                len(
                                    set(context["staged_faces"][face_id])
                                    & set(context["staged_faces"][seed])
                                )
                                >= 2
                                for seed in island
                            )
                        }
                    ),
                }
            )
        candidates.append(
            {
                "route_id": record["route_id"],
                "island_count": len(islands),
                "islands": island_records,
            }
        )
    single = [record for record in candidates if record["island_count"] == 1]
    selected = (
        min(
            single,
            key=lambda record: (
                len(record["islands"][0]["face_ids"]),
                record["islands"][0]["area_mm2"],
                len(record["islands"][0]["vertex_ids"]),
                record["route_id"],
            ),
        )
        if single
        else None
    )
    return candidates, selected


def main():
    report_path = Path(v14.argument("--report")).resolve()
    context = v17.baseline_context()
    if sha_file(V22_ATTRIBUTION_PATH) != V22_ATTRIBUTION_SHA256:
        raise RuntimeError(
            f"{OPERATION}: v22 attribution hash mismatch"
        )
    attribution = json.loads(V22_ATTRIBUTION_PATH.read_text(encoding="utf-8"))
    corridor = v22.v21.reconstruct_v12_core(context)
    portal = b2b_portal(corridor)
    endpoints = endpoint_candidates(context)
    obstacles = obstacle_context(context, corridor, attribution)
    landing = {
        "source_face_ids": list(LANDING_FACE_IDS),
        "face_records": face_catalog(context, LANDING_FACE_IDS),
        "immutable_boundary_edges": [
            list(edge)
            for edge in boundary_edges(
                LANDING_FACE_IDS,
                context["staged_faces"],
            )
        ],
        "tangent": [-0.451645434, 0.836417615, -0.310518861],
        "normal": [0.685143352, 0.548078537, 0.479779691],
        "endpoint_candidates": endpoints,
    }
    route_path = report_path.with_name("route_preflight.json")
    allowlist_path = report_path.with_name("joint_allowlist_preflight.json")
    route_initial = {
        "operation": OPERATION,
        "status": "PORTALS_AND_OBSTACLES_CHECKPOINTED_SEARCH_PENDING",
        "authorities": {
            "input_blend_sha256": context["blend_sha"],
            "retained_cage_fingerprint": context["checks"][
                "retained_fingerprint"
            ],
            "component_9_fingerprint": context["checks"][
                "component_9_fingerprint"
            ],
            "v12_corridor_fingerprint": stable_hash(corridor["public"]),
            "branch_a_fingerprint": attribution["immutable_complements"][
                "branch_a_fingerprint"
            ],
            "v22_attribution_sha256": V22_ATTRIBUTION_SHA256,
        },
        "start_portal": public(portal),
        "end_portal": landing,
        "obstacle_catalogs": obstacles["catalogs"],
        "search_contract": {
            "lattice_spacing_mm": LATTICE_MM,
            "longitudinal_padding_mm": 4.0,
            "transverse_bounds_mm": [-24.0, 24.0],
            "maximum_chord_distance_mm": 28.0,
            "direction_bin_degrees": 15,
            "maximum_edge_turn_degrees": 45,
            "roll_bin_degrees": 15,
            "maximum_roll_change_per_edge_degrees": 15,
            "edge_lengths_mm": [4.0, 4.0 * sqrt(2), 4.0 * sqrt(3)],
            "width_passes_mm": list(WIDTHS_MM),
            "thickness_mm": THICKNESS_MM,
            "departure_deflections_degrees": list(DEPARTURE_DEFLECTIONS),
            "departure_roll_knots_degrees": list(DEPARTURE_ROLLS),
            "scarf_length_mm": 6.0,
            "spline_maximum_interior_controls": 3,
            "spline_fit_tolerance_mm": 0.5,
            "spline_sample_spacing_mm": 2.0,
        },
        "search_records": [],
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    route_path.write_text(
        json.dumps(route_initial, indent=2) + "\n",
        encoding="utf-8",
    )
    allowlist_path.write_text(
        json.dumps(
            {
                "operation": OPERATION,
                "status": "SEARCH_PENDING_NO_ALLOWLIST",
                "selected_route_id": None,
                "C9_base_mask": [],
                "C9_transition_ring": [],
                "C20_T0_mask": list(LANDING_FACE_IDS),
                "visible_C20_fallback": None,
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
                    "landing_boundary": stable_hash(landing),
                },
                "mutation_authority": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    search_records = []
    exact_records = []
    fallback_exact_records = []
    fallback_search_records = []
    start = portal["_center"]
    base_tangent = portal["_tangent"]
    scarf_end = start + base_tangent * 6.0
    accepted_endpoints = [
        endpoint for endpoint in endpoints if endpoint["accepted"]
    ]
    for endpoint in accepted_endpoints:
        end = Vector(endpoint["coordinate_mm"])
        nodes, frame_record = lattice_nodes(
            start,
            end,
            portal["_normal"],
        )
        toward_b2b = Vector(
            (-0.451645434, 0.836417615, -0.310518861)
        )
        if toward_b2b.dot(start - end) < 0.0:
            toward_b2b.negate()
        arrival_tangent = -toward_b2b.normalized()
        for width in WIDTHS_MM:
            for deflection in DEPARTURE_DEFLECTIONS:
                departure = (
                    Quaternion(
                        portal["_normal"],
                        radians(deflection),
                    )
                    @ base_tangent
                ).normalized()
                for roll in DEPARTURE_ROLLS:
                    route_id = (
                        f"{endpoint['endpoint_id']}_W{width:.2f}_"
                        f"D{deflection:+03d}_R{roll:+03d}"
                    )
                    polyline, search_metrics = astar(
                        nodes,
                        scarf_end,
                        end,
                        departure,
                        arrival_tangent,
                        roll,
                        width,
                        obstacles,
                        corridor,
                    )
                    record = {
                        "route_id": route_id,
                        "endpoint_id": endpoint["endpoint_id"],
                        "width_mm": width,
                        "departure_deflection_degrees": deflection,
                        "departure_roll_degrees": roll,
                        "search_frame": frame_record,
                        **search_metrics,
                        "polyline_found": polyline is not None,
                        "polyline_points_mm": (
                            [
                                [float(value) for value in point]
                                for point in polyline["points"]
                            ]
                            if polyline
                            else None
                        ),
                        "fitted_spline": None,
                        "rejection_reason": (
                            None if polyline else "astar_no_path"
                        ),
                    }
                    if polyline:
                        spline = fit_spline(polyline["points"])
                        exact = exact_collision_record(
                            route_id,
                            spline,
                            polyline["rolls"],
                            width,
                            obstacles,
                            context,
                            corridor,
                        )
                        exact_records.append(exact)
                        record["fitted_spline"] = public(exact)
                        record["rejection_reason"] = (
                            None
                            if exact["gate_pass"]
                            else "exact_spline_gate_failed"
                        )
                    search_records.append(record)
            route_initial["search_records"] = search_records
            route_initial["status"] = "WIDTH_PASS_PREFIX_CHECKPOINT"
            route_path.write_text(
                json.dumps(route_initial, indent=2) + "\n",
                encoding="utf-8",
            )
    clean = [record for record in exact_records if record["gate_pass"]]
    channel_records = []
    if clean:
        for record in clean:
            for gap in GAPS_MM:
                channel_records.append(
                    {
                        "route_id": record["route_id"],
                        "gap_mm": gap,
                        "status": "REJECTED_NO_FLOORLESS_CHANNEL_CONSTRUCTION",
                        "C9_base_mask": [],
                        "C9_transition_ring": [],
                        "layer_order_samples": [],
                        "gate_pass": False,
                        "reason": (
                            "a floorless rimmed channel cannot be certified "
                            "from a route with zero attributed proximal C9 "
                            "interface in this preflight"
                        ),
                    }
                )
    if not clean:
        for endpoint in accepted_endpoints:
            end = Vector(endpoint["coordinate_mm"])
            nodes, frame_record = lattice_nodes(
                start,
                end,
                portal["_normal"],
            )
            toward_b2b = Vector(
                (-0.451645434, 0.836417615, -0.310518861)
            )
            if toward_b2b.dot(start - end) < 0.0:
                toward_b2b.negate()
            arrival_tangent = -toward_b2b.normalized()
            for width in WIDTHS_MM:
                for deflection in DEPARTURE_DEFLECTIONS:
                    departure = (
                        Quaternion(
                            portal["_normal"],
                            radians(deflection),
                        )
                        @ base_tangent
                    ).normalized()
                    for roll in DEPARTURE_ROLLS:
                        route_id = (
                            f"FALLBACK_{endpoint['endpoint_id']}_"
                            f"W{width:.2f}_D{deflection:+03d}_R{roll:+03d}"
                        )
                        polyline, fallback_metrics = astar(
                            nodes,
                            scarf_end,
                            end,
                            departure,
                            arrival_tangent,
                            roll,
                            width,
                            obstacles,
                            corridor,
                            ignore_c20=True,
                        )
                        fallback_search_records.append(
                            {
                                "route_id": route_id,
                                "exterior_C20_relaxed": True,
                                **fallback_metrics,
                                "polyline_found": polyline is not None,
                                "rejection_reason": (
                                    None if polyline else "astar_no_path"
                                ),
                            }
                        )
                        if not polyline:
                            continue
                        spline = fit_spline(polyline["points"])
                        exact = exact_collision_record(
                            route_id,
                            spline,
                            polyline["rolls"],
                            width,
                            obstacles,
                            context,
                            corridor,
                        )
                        fallback_exact_records.append(exact)
    fallback, fallback_selected = visible_fallback(
        fallback_exact_records,
        obstacles,
        context,
        corridor["target_length"],
    )
    if fallback_selected:
        status = VISIBLE_DECISION
    elif fallback:
        status = NO_VISIBLE
    else:
        status = NO_ROUTE
    route_final = {
        **route_initial,
        "status": status,
        "search_records": search_records,
        "exact_spline_records": [public(record) for record in exact_records],
        "clean_spline_count": len(clean),
        "channel_preflight_records": channel_records,
        "fallback_exact_spline_records": [
            public(record) for record in fallback_exact_records
        ],
        "fallback_search_records": fallback_search_records,
        "visible_fallback_classification": fallback,
        "selected_complete_route_channel_pair": None,
        "hard_stop": {
            "operation": "immutable_B2b_scarf_departure",
            "target": "first 6 mm tangent-continuous 6/5.25/4.5 x 2.4 span",
            "reason": (
                "every exact route tuple is blocked by the cutter before an "
                "A* state can be initialized"
            ),
            "initial_cutter_rejection_count": sum(
                record["edge_rejection_counts"].get("initial_cutter", 0)
                for record in search_records
            ),
            "exterior_C20_relaxed_fallback_run": True,
            "visible_island_classification_possible": False,
            "fallback_reason": (
                "relaxing exterior C20 does not affect the immutable scarf "
                "cutter blocker, so no otherwise-passing fallback spline "
                "exists to attribute to a visible island"
            ),
        },
    }
    route_path.write_text(
        json.dumps(route_final, indent=2) + "\n",
        encoding="utf-8",
    )
    allowlist = {
        "operation": OPERATION,
        "status": status,
        "selected_route_id": None,
        "C9_base_mask": [],
        "C9_transition_ring": [],
        "C20_T0_mask": list(LANDING_FACE_IDS),
        "visible_C20_fallback": fallback_selected,
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
            "landing_boundary": stable_hash(landing),
        },
        "mutation_authority": False,
    }
    allowlist_path.write_text(
        json.dumps(allowlist, indent=2) + "\n",
        encoding="utf-8",
    )
    rejection_counts = Counter(
        record["rejection_reason"] for record in search_records
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "route_preflight": str(route_path),
        "route_preflight_sha256": sha_file(route_path),
        "joint_allowlist_preflight": str(allowlist_path),
        "joint_allowlist_preflight_sha256": sha_file(allowlist_path),
        "candidate_counts": {
            "accepted_endpoint_count": len(accepted_endpoints),
            "astar_tuple_count": len(search_records),
            "astar_polyline_count": sum(
                record["polyline_found"] for record in search_records
            ),
            "exact_spline_count": len(exact_records),
            "clean_spline_count": len(clean),
            "channel_pair_pass_count": 0,
            "fallback_spline_count": len(fallback_exact_records),
            "fallback_astar_tuple_count": len(fallback_search_records),
            "fallback_visible_candidate_count": len(fallback),
        },
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "selected_result": fallback_selected,
        "hard_stop": route_final["hard_stop"],
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
        f"DONE: v23 route preflight status={status}; "
        "mutation_started=False; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
