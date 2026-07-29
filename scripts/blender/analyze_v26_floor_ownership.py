"""Classify V26 source exposure and single-floor ownership without mutation.

Run with the V24 evidence Blend open:

    blender -b INPUT.blend --python analyze_v26_floor_ownership.py -- \
        --report OUTPUT/v26_floor_ownership_authority.json

The output is diagnostic authority only.  It emits no geometry and grants no
candidate or mutation authority.
"""

from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
import json
from math import ceil, pi
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import preflight_open_bay_joint_v26 as v26  # noqa: E402


OPERATION = "V26_FLOOR_OWNERSHIP_AUTHORITY"
EXPECTED_BLEND_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
EXPECTED_JOINT_SHA256 = (
    "e4a01b2d0e0f5d7997983d43af90cf2f2cd2bec81c859645b7e6961b8a55bbef"
)
EXPECTED_CELL_SHA256 = (
    "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca"
)
EXPOSURE_SPACING_MM = 1.0
OWNERSHIP_SPACING_MM = 2.0
EXPOSURE_THRESHOLD = 0.75
FLEX_GAP_WIDTH_MM = 12.0
RAY_EPSILON_MM = 0.0001
MAX_OUTWARD_RAY_MM = 160.0
ROOT = SCRIPT_DIR.parent.parent
AUTHORITY_DIR = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
JOINT_PATH = AUTHORITY_DIR / "v26_joint_authority.json"
CELL_PATH = AUTHORITY_DIR / "v26_cell_authority.json"


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value):
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def argument(name):
    try:
        return sys.argv[sys.argv.index(name) + 1]
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks required {name} PATH"
        ) from error


def vector_record(point):
    return [round(float(value), 9) for value in point]


def triangles(face):
    return [
        (face[0], face[index], face[index + 1])
        for index in range(1, len(face) - 1)
    ]


def barycentric_samples(points, triangle, spacing):
    first, second, third = (points[index] for index in triangle)
    divisions = max(
        1,
        int(
            ceil(
                max(
                    (first - second).length,
                    (second - third).length,
                    (third - first).length,
                )
                / spacing
            )
        ),
    )
    result = []
    for first_weight in range(divisions + 1):
        for second_weight in range(divisions + 1 - first_weight):
            third_weight = divisions - first_weight - second_weight
            weights = (
                first_weight / divisions,
                second_weight / divisions,
                third_weight / divisions,
            )
            point = (
                first * weights[0]
                + second * weights[1]
                + third * weights[2]
            )
            result.append((point, weights, divisions))
    return result


def face_samples(points, face, spacing):
    records = []
    seen = set()
    for triangle_index, triangle in enumerate(triangles(face)):
        for point, weights, divisions in barycentric_samples(
            points, triangle, spacing
        ):
            key = tuple(round(float(value), 8) for value in point)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "point": point,
                    "triangle_index": triangle_index,
                    "barycentric": [round(value, 9) for value in weights],
                    "divisions": divisions,
                }
            )
    return records


def iterative_hits(tree, origin, direction, maximum_distance):
    hits = []
    travelled = 0.0
    cursor = origin.copy()
    for _ in range(64):
        remaining = maximum_distance - travelled
        if remaining <= RAY_EPSILON_MM:
            break
        location, normal, face_id, distance = tree.ray_cast(
            cursor, direction, remaining
        )
        if location is None:
            break
        total = travelled + distance
        hits.append((location.copy(), normal.copy(), int(face_id), total))
        advance = distance + RAY_EPSILON_MM
        cursor += direction * advance
        travelled += advance
    return hits


def unobstructed_to_cutter(
    source_tree,
    source_face_id,
    excluded_faces,
    sample,
    cutter_point,
):
    delta = cutter_point - sample
    distance = delta.length
    if distance <= RAY_EPSILON_MM:
        return True, None, None
    direction = delta / distance
    for location, _, face_id, hit_distance in iterative_hits(
        source_tree,
        sample + direction * RAY_EPSILON_MM,
        direction,
        max(0.0, distance - 2.0 * RAY_EPSILON_MM),
    ):
        if face_id in excluded_faces:
            continue
        return False, face_id, (location, hit_distance)
    return True, None, None


def point_segment_distance(point, first, second):
    delta = second - first
    denominator = delta.length_squared
    if denominator <= 1.0e-18:
        return (point - first).length
    fraction = max(
        0.0, min(1.0, (point - first).dot(delta) / denominator)
    )
    return (point - (first + delta * fraction)).length


def segment_near_open_route(sample, cutter_point, route_edges):
    # Conservative deterministic witness: both endpoints and the midpoint of
    # the source-radial segment are checked against every exact route edge.
    probes = (sample, sample.lerp(cutter_point, 0.5), cutter_point)
    for edge_id, first, second in route_edges:
        if min(
            point_segment_distance(probe, first, second) for probe in probes
        ) <= 0.6:
            return edge_id
    return None


def face_normal(points, face):
    return v26.face_normal(points, face)


def exposure_authority(context, joint, cells, source_tree, cutter_tree):
    points = context["staged_points"]
    faces = context["staged_faces"]
    adjacency = v26.face_adjacency(faces)
    exterior = set(
        joint["masks"]["C20_EXTERIOR_CAGE_IMMUTABLE"]["face_ids"]
    )
    c9_immutable = set(
        joint["masks"]["C9_IMMUTABLE_COMPLEMENT"]["face_ids"]
    )
    route_edges = [
        (
            record["edge_id"],
            points[record["vertex_ids"][0]],
            points[record["vertex_ids"][1]],
        )
        for record in joint["negative_space"]["source_open_routes"][
            "edge_records"
        ]
    ]
    result = {}
    for cell in cells:
        cell_faces = []
        for face_id in cell["face_ids"]:
            normal = face_normal(points, faces[face_id])
            samples = []
            unobstructed_count = 0
            sign_count = 0
            prism_exit_count = 0
            for sample_index, sample_record in enumerate(
                face_samples(points, faces[face_id], EXPOSURE_SPACING_MM)
            ):
                sample = sample_record.pop("point")
                cutter_point, cutter_normal, cutter_face_id, distance = (
                    cutter_tree.find_nearest(sample)
                )
                if cutter_point is None:
                    raise RuntimeError(
                        f"{OPERATION}: nearest cutter query failed for "
                        f"source face {face_id}, sample {sample_index}"
                    )
                excluded = set(adjacency[face_id]) | {face_id}
                clear, occluder_face, occluder = unobstructed_to_cutter(
                    source_tree,
                    face_id,
                    excluded,
                    sample,
                    cutter_point,
                )
                cutter_vector = (cutter_point - sample).normalized()
                normal_dot = normal.dot(cutter_vector)
                sign_agrees = normal_dot > 0.0
                route_edge = segment_near_open_route(
                    sample, cutter_point, route_edges
                )
                unobstructed_count += int(clear)
                sign_count += int(sign_agrees)
                prism_exit_count += int(route_edge is not None)
                samples.append(
                    {
                        "sample_index": sample_index,
                        "point_mm": vector_record(sample),
                        **sample_record,
                        "nearest_cutter_point_mm": vector_record(cutter_point),
                        "nearest_cutter_face_id": int(cutter_face_id),
                        "cutter_distance_mm": round(float(distance), 9),
                        "first_hit_id": (
                            f"CUTTER:{int(cutter_face_id)}"
                            if clear
                            else f"SOURCE:{occluder_face}"
                        ),
                        "unobstructed_first_hit_on_cutter": clear,
                        "occluder_source_face_id": occluder_face,
                        "occluder_point_mm": (
                            vector_record(occluder[0]) if occluder else None
                        ),
                        "source_normal_cutter_vector_dot": round(
                            normal_dot, 9
                        ),
                        "normal_sign_agrees": sign_agrees,
                        "immutable_open_route_edge_id": route_edge,
                    }
                )
            count = len(samples)
            clear_ratio = unobstructed_count / count
            sign_ratio = sign_count / count
            immutable_class = face_id in exterior or (
                cell["component"] == "C9" and face_id in c9_immutable
            )
            reasons = []
            if clear_ratio < EXPOSURE_THRESHOLD:
                reasons.append("CUTTER_FIRST_HIT_RATIO_BELOW_0.75")
            if sign_ratio < EXPOSURE_THRESHOLD:
                reasons.append("NORMAL_SIGN_RATIO_BELOW_0.75")
            if prism_exit_count:
                reasons.append("IMMUTABLE_OPEN_ROUTE_PRISM_EXIT")
            if immutable_class:
                reasons.append("IMMUTABLE_EXTERIOR_RIM_OR_OPENING_CLASS")
            classification = (
                "WEARER_FACING" if not reasons else "EXTERIOR_OR_AMBIGUOUS"
            )
            cell_faces.append(
                {
                    "source_face_id": face_id,
                    "station_mm": round(
                        v4.radial_coordinates(
                            sum(
                                (points[index] for index in faces[face_id]),
                                Vector(),
                            )
                            / len(faces[face_id]),
                            float(
                                bpy.data.objects[v4.CANDIDATE_NAME][
                                    "target_length_mm"
                                ]
                            ),
                        )[0]
                        * float(
                            bpy.data.objects[v4.CANDIDATE_NAME][
                                "target_length_mm"
                            ]
                        ),
                        9,
                    ),
                    "sample_count": count,
                    "unobstructed_cutter_ratio": round(clear_ratio, 9),
                    "normal_sign_agreement_ratio": round(sign_ratio, 9),
                    "immutable_prism_exit_sample_count": prism_exit_count,
                    "classification": classification,
                    "class_reasons": reasons,
                    "samples": samples,
                }
            )
        result[cell["name"]] = {
            "component": cell["component"],
            "source_cell_fingerprint": cell["fingerprint"],
            "face_count": len(cell_faces),
            "wearer_facing_face_ids": [
                record["source_face_id"]
                for record in cell_faces
                if record["classification"] == "WEARER_FACING"
            ],
            "ambiguous_face_ids": [
                record["source_face_id"]
                for record in cell_faces
                if record["classification"] != "WEARER_FACING"
            ],
            "faces": cell_faces,
        }
    return result


def cell_face_map(cells):
    mapping = {}
    for cell in cells:
        for face_id in cell["face_ids"]:
            if face_id in mapping:
                raise RuntimeError(
                    f"{OPERATION}: source face {face_id} belongs to more "
                    "than one exact atomic cell"
                )
            mapping[face_id] = (cell["component"], cell["name"])
    return mapping


def topology_distances(context, cells, terminals):
    adjacency = v26.face_adjacency(context["staged_faces"])
    terminal_seeds = defaultdict(set)
    for record in terminals["records"]:
        terminal_seeds[record["component"]].update(
            record["candidate_incident_face_ids"]
        )
    distances = {}
    for cell in cells:
        allowed = set(cell["face_ids"])
        seeds = sorted(allowed & terminal_seeds[cell["component"]])
        distance = {seed: 0 for seed in seeds}
        queue = deque(seeds)
        while queue:
            face_id = queue.popleft()
            for neighbor in sorted(adjacency[face_id] & allowed):
                if neighbor not in distance:
                    distance[neighbor] = distance[face_id] + 1
                    queue.append(neighbor)
        distances[cell["name"]] = distance
    return distances


def gap_authority(context, joint, cutter_tree):
    controls = joint["named_controls"]
    upper = (
        Vector(controls["2074"]) + Vector(controls["1257"])
    ) * 0.5
    lower = (
        Vector(controls["2119"]) + Vector(controls["1295"])
    ) * 0.5
    upper_cutter, _, upper_face, _ = cutter_tree.find_nearest(upper)
    lower_cutter, _, lower_face, _ = cutter_tree.find_nearest(lower)
    if upper_cutter is None or lower_cutter is None:
        raise RuntimeError(
            f"{OPERATION}: failed to project exact gap registration controls "
            "onto the named cutter"
        )
    chord = lower_cutter - upper_cutter
    separation = chord.length
    if separation < FLEX_GAP_WIDTH_MM:
        raise RuntimeError(
            f"{OPERATION}: exact projected flex-boundary separation "
            f"{separation:.9f} mm is below {FLEX_GAP_WIDTH_MM:.1f} mm"
        )
    direction = chord.normalized()
    midpoint = upper_cutter.lerp(lower_cutter, 0.5)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    return {
        "upper_registration_point_mm": vector_record(upper),
        "lower_registration_point_mm": vector_record(lower),
        "upper_cutter_point_mm": vector_record(upper_cutter),
        "lower_cutter_point_mm": vector_record(lower_cutter),
        "upper_cutter_face_id": int(upper_face),
        "lower_cutter_face_id": int(lower_face),
        "projected_boundary_separation_mm": round(separation, 9),
        "minimum_width_mm": FLEX_GAP_WIDTH_MM,
        "midpoint_mm": vector_record(midpoint),
        "chord_direction": vector_record(direction),
        "half_width_mm": FLEX_GAP_WIDTH_MM / 2.0,
        "upper_station_mm": round(
            v4.radial_coordinates(upper_cutter, target_length)[0]
            * target_length,
            9,
        ),
        "lower_station_mm": round(
            v4.radial_coordinates(lower_cutter, target_length)[0]
            * target_length,
            9,
        ),
        "classification": (
            "cutter-lattice samples whose chordwise projection lies within "
            "six millimeters of the exact projected registration midpoint"
        ),
    }


def in_gap(point, gap):
    midpoint = Vector(gap["midpoint_mm"])
    direction = Vector(gap["chord_direction"])
    return (
        abs((point - midpoint).dot(direction))
        <= gap["half_width_mm"] + 1.0e-9
    )


def cutter_lattice(context):
    points = context["cutter_points"]
    faces = context["cutter_faces"]
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    samples = []
    seen = set()
    for cutter_face_id, face in enumerate(faces):
        normal = face_normal(points, face)
        centroid = sum((points[index] for index in face), Vector()) / len(face)
        radial = v4.radial_coordinates(centroid, target_length)[3]
        if normal.dot(radial) < 0.0:
            normal.negate()
        for triangle_index, triangle in enumerate(triangles(face)):
            for point, weights, divisions in barycentric_samples(
                points, triangle, OWNERSHIP_SPACING_MM
            ):
                key = tuple(round(float(value), 7) for value in point)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    station, angle, radius, _ = v4.radial_coordinates(
                        point, target_length
                    )
                except RuntimeError:
                    # Cutter end-cap samples on the construction axis have no
                    # angle and cannot belong to the C9/C20 station/angle
                    # footprint.
                    continue
                samples.append(
                    {
                        "point": point,
                        "normal": normal.copy(),
                        "cutter_face_id": cutter_face_id,
                        "triangle_index": triangle_index,
                        "barycentric": [
                            round(value, 9) for value in weights
                        ],
                        "divisions": divisions,
                        "station_mm": station * target_length,
                        "angle_radians": angle,
                        "radius_mm": radius,
                    }
                )
    return samples


def cell_footprints(cells, target_length):
    result = []
    for cell in cells:
        coordinates = [
            Vector(coordinate)
            for coordinate in cell["vertex_coordinates_mm"].values()
        ]
        polar = [
            v4.radial_coordinates(point, target_length)
            for point in coordinates
        ]
        angles = sorted(value[1] for value in polar)
        cyclic_gaps = [
            (
                (angles[(index + 1) % len(angles)] - angles[index])
                % (2.0 * pi),
                index,
            )
            for index in range(len(angles))
        ]
        _, gap_index = max(cyclic_gaps)
        start = angles[(gap_index + 1) % len(angles)]
        span = (angles[gap_index] - start) % (2.0 * pi)
        minimum_radius = min(value[2] for value in polar)
        angular_margin = OWNERSHIP_SPACING_MM / minimum_radius
        result.append(
            {
                "cell_id": cell["name"],
                "component": cell["component"],
                "station_range_mm": cell["station_range_mm"],
                "angle_start_radians": round(start, 12),
                "angle_span_radians": round(span, 12),
                "angular_margin_radians": round(angular_margin, 12),
            }
        )
    return result


def inside_footprint(sample, footprint):
    station_min, station_max = footprint["station_range_mm"]
    if not (
        station_min - OWNERSHIP_SPACING_MM
        <= sample["station_mm"]
        <= station_max + OWNERSHIP_SPACING_MM
    ):
        return False
    relative = (
        sample["angle_radians"] - footprint["angle_start_radians"]
    ) % (2.0 * pi)
    margin = footprint["angular_margin_radians"]
    return (
        relative <= footprint["angle_span_radians"] + margin
        or relative >= 2.0 * pi - margin
    )


def projected_cell_triangles(context, cells, target_length):
    result = []
    points = context["staged_points"]
    faces = context["staged_faces"]
    for cell in cells:
        projected = []
        for face_id in cell["face_ids"]:
            for triangle in triangles(faces[face_id]):
                polar = [
                    v4.radial_coordinates(points[index], target_length)
                    for index in triangle
                ]
                station_values = [
                    value[0] * target_length for value in polar
                ]
                projected.append(
                    {
                        "source_face_id": face_id,
                        "source_vertex_ids": list(triangle),
                        "station_bounds_mm": [
                            round(min(station_values), 9),
                            round(max(station_values), 9),
                        ],
                        "station_angle_radius": [
                            [
                                round(value[0] * target_length, 9),
                                round(value[1], 12),
                                round(value[2], 9),
                            ]
                            for value in polar
                        ],
                    }
                )
        result.append(
            {
                "cell_id": cell["name"],
                "component": cell["component"],
                "triangles": projected,
                "fingerprint": stable_hash(projected),
            }
        )
    return result


def wrapped_angle_difference(first, second):
    return (first - second + pi) % (2.0 * pi) - pi


def origin_triangle_distance_2d(vertices):
    def cross(first, second):
        return first[0] * second[1] - first[1] * second[0]

    signs = []
    for first, second in zip(vertices, (*vertices[1:], vertices[0])):
        edge = (second[0] - first[0], second[1] - first[1])
        toward_origin = (-first[0], -first[1])
        signs.append(cross(edge, toward_origin))
    if all(value >= -1.0e-9 for value in signs) or all(
        value <= 1.0e-9 for value in signs
    ):
        return 0.0
    distances = []
    for first, second in zip(vertices, (*vertices[1:], vertices[0])):
        delta = (second[0] - first[0], second[1] - first[1])
        denominator = delta[0] ** 2 + delta[1] ** 2
        if denominator <= 1.0e-18:
            distances.append((first[0] ** 2 + first[1] ** 2) ** 0.5)
            continue
        fraction = max(
            0.0,
            min(
                1.0,
                -(first[0] * delta[0] + first[1] * delta[1])
                / denominator,
            ),
        )
        point = (
            first[0] + delta[0] * fraction,
            first[1] + delta[1] * fraction,
        )
        distances.append((point[0] ** 2 + point[1] ** 2) ** 0.5)
    return min(distances)


def inside_projected_cell(sample, cell_projection):
    for triangle in cell_projection["triangles"]:
        station_min, station_max = triangle["station_bounds_mm"]
        if not (
            station_min - OWNERSHIP_SPACING_MM * 0.5
            <= sample["station_mm"]
            <= station_max + OWNERSHIP_SPACING_MM * 0.5
        ):
            continue
        vertices = [
            (
                station - sample["station_mm"],
                wrapped_angle_difference(
                    angle, sample["angle_radians"]
                )
                * ((radius + sample["radius_mm"]) * 0.5),
            )
            for station, angle, radius in triangle["station_angle_radius"]
        ]
        if origin_triangle_distance_2d(vertices) <= (
            OWNERSHIP_SPACING_MM * 0.5 + 1.0e-9
        ):
            return True
    return False


def ownership_authority(
    context,
    joint,
    cells,
    exposure,
    source_tree,
    gap,
):
    face_map = cell_face_map(cells)
    distances = topology_distances(
        context, cells, json.loads(CELL_PATH.read_text(encoding="utf-8"))[
            "terminal_boundary_coincidence"
        ]
    )
    retained = set(
        joint["masks"]["C20_EXTERIOR_CAGE_IMMUTABLE"]["face_ids"]
    )
    wearer_faces = {
        face_id
        for cell in exposure.values()
        for face_id in cell["wearer_facing_face_ids"]
    }
    records = []
    duplicate_pairs = set()
    no_floor = []
    gap_source_floors = []
    lattice = cutter_lattice(context)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    footprints = cell_footprints(cells, target_length)
    projected_cells = projected_cell_triangles(
        context, cells, target_length
    )
    atomic_station_min = min(
        cell["station_range_mm"][0] for cell in cells
    )
    atomic_station_max = max(
        cell["station_range_mm"][1] for cell in cells
    )
    for raw_index, sample in enumerate(lattice):
        matching_footprints = [
            cell
            for cell in projected_cells
            if inside_projected_cell(sample, cell)
        ]
        if not matching_footprints:
            continue
        origin = sample["point"] + sample["normal"] * RAY_EPSILON_MM
        hits = iterative_hits(
            source_tree, origin, sample["normal"], MAX_OUTWARD_RAY_MM
        )
        atomic_hits = []
        exterior_hits = []
        seen_atomic = set()
        for location, _, face_id, distance in hits:
            if face_id in face_map:
                key = (face_id, round(distance, 5))
                if key not in seen_atomic:
                    seen_atomic.add(key)
                    component, cell_id = face_map[face_id]
                    atomic_hits.append(
                        {
                            "distance_mm": round(distance, 9),
                            "point_mm": vector_record(location),
                            "source_face_id": face_id,
                            "component": component,
                            "cell_id": cell_id,
                            "wearer_facing": face_id in wearer_faces,
                            "topology_distance_to_retained_boundary": (
                                distances[cell_id].get(face_id)
                            ),
                        }
                    )
            if face_id in retained:
                exterior_hits.append(
                    {
                        "distance_mm": round(distance, 9),
                        "source_face_id": face_id,
                        "point_mm": vector_record(location),
                    }
                )
        # Collapse edge-coincident hits on one surface, but never collapse
        # different components; those are the exact duplicate-floor evidence.
        clusters = []
        for hit in atomic_hits:
            matched = next(
                (
                    cluster
                    for cluster in clusters
                    if cluster["component"] == hit["component"]
                    and abs(cluster["distance_mm"] - hit["distance_mm"])
                    <= 0.001
                ),
                None,
            )
            if matched is None:
                clusters.append({**hit, "coincident_face_ids": [hit["source_face_id"]]})
            else:
                matched["coincident_face_ids"].append(hit["source_face_id"])
                matched["coincident_face_ids"].sort()
        gap_sample = in_gap(sample["point"], gap)
        eligible = [hit for hit in clusters if hit["wearer_facing"]]
        owner = None
        owner_reason = None
        if gap_sample:
            owner = "FLEX_GAP_NONE"
            owner_reason = "numeric_12mm_flex_gap_precedence"
            if clusters:
                gap_source_floors.append(
                    {
                        "lattice_index": len(records),
                        "station_mm": round(sample["station_mm"], 9),
                        "face_ids": sorted(
                            {
                                face_id
                                for hit in clusters
                                for face_id in hit["coincident_face_ids"]
                            }
                        ),
                    }
                )
        elif not eligible:
            no_floor.append(len(records))
        elif len(eligible) == 1:
            owner = eligible[0]["component"]
            owner_reason = "single_exposed_source_boundary_owner"
        else:
            ordered = sorted(
                eligible,
                key=lambda hit: (
                    (
                        hit["topology_distance_to_retained_boundary"]
                        if hit["topology_distance_to_retained_boundary"]
                        is not None
                        else 10**9
                    ),
                    min(hit["coincident_face_ids"]),
                    hit["component"],
                ),
            )
            owner = ordered[0]["component"]
            owner_reason = (
                "shorter_topology_distance_then_lower_minimum_source_face_id"
            )
            components = {hit["component"] for hit in eligible}
            if {"C9", "C20"} <= components:
                for c9_hit in (
                    hit for hit in eligible if hit["component"] == "C9"
                ):
                    for c20_hit in (
                        hit for hit in eligible if hit["component"] == "C20"
                    ):
                        for c9_face in c9_hit["coincident_face_ids"]:
                            for c20_face in c20_hit["coincident_face_ids"]:
                                duplicate_pairs.add(
                                    (
                                        c9_face,
                                        c20_face,
                                        round(sample["station_mm"], 6),
                                    )
                                )
        first_exterior = exterior_hits[0] if exterior_hits else None
        order_valid = (
            owner == "FLEX_GAP_NONE"
            or not eligible
            or first_exterior is None
            or eligible[0]["distance_mm"] < first_exterior["distance_mm"]
        )
        records.append(
            {
                "lattice_index": len(records),
                "source_lattice_index": raw_index,
                "cutter_point_mm": vector_record(sample["point"]),
                "outward_cutter_normal": vector_record(sample["normal"]),
                "cutter_face_id": sample["cutter_face_id"],
                "cutter_triangle_index": sample["triangle_index"],
                "barycentric": sample["barycentric"],
                "divisions": sample["divisions"],
                "station_mm": round(sample["station_mm"], 9),
                "angle_radians": round(sample["angle_radians"], 9),
                "footprint_cell_ids": [
                    cell["cell_id"] for cell in matching_footprints
                ],
                "inside_numeric_flex_gap": gap_sample,
                "ordered_atomic_intersections": clusters,
                "first_retained_exterior_intersection": first_exterior,
                "declared_owner": owner,
                "owner_reason": owner_reason,
                "ordered_cutter_floor_exterior_valid": order_valid,
            }
        )
    # Analyze owner changes along deterministic angular bins.  The bin width
    # corresponds to no more than 2 mm at the mean cutter radius.
    radii = [
        v4.radial_coordinates(
            Vector(record["cutter_point_mm"]),
            float(bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]),
        )[2]
        for record in records
    ]
    mean_radius = sum(radii) / len(radii)
    angle_step = OWNERSHIP_SPACING_MM / mean_radius
    station_rays = defaultdict(list)
    for record in records:
        angular_bin = int(round(record["angle_radians"] / angle_step))
        station_rays[angular_bin].append(record)
    ray_records = []
    branched = False
    first_changes = []
    last_changes = []
    for angular_bin in sorted(station_rays):
        ordered = sorted(
            station_rays[angular_bin],
            key=lambda record: (
                record["station_mm"],
                record["lattice_index"],
            ),
        )
        changes = []
        previous = None
        for record in ordered:
            owner = record["declared_owner"]
            if owner is None or owner == "FLEX_GAP_NONE":
                continue
            if previous is not None and owner != previous:
                changes.append(
                    {
                        "station_mm": record["station_mm"],
                        "from": previous,
                        "to": owner,
                        "lattice_index": record["lattice_index"],
                    }
                )
            previous = owner
        branched = branched or len(changes) > 1
        if changes:
            first_changes.append(changes[0]["station_mm"])
            last_changes.append(changes[-1]["station_mm"])
        ray_records.append(
            {
                "angular_bin": angular_bin,
                "sample_count": len(ordered),
                "owner_changes": changes,
            }
        )
    return {
        "lattice_contract": {
            "maximum_spacing_mm": OWNERSHIP_SPACING_MM,
            "source": "named cutter world-space faces",
            "ray": "outward consistently radialized cutter face normal",
            "maximum_ray_mm": MAX_OUTWARD_RAY_MM,
            "atomic_station_range_mm": [
                atomic_station_min,
                atomic_station_max,
            ],
            "exact_atomic_cell_station_angle_footprints": footprints,
            "projected_source_triangle_footprints": projected_cells,
            "projected_footprint_inclusion_tolerance_mm": (
                OWNERSHIP_SPACING_MM * 0.5
            ),
        },
        "flex_gap": gap,
        "sample_count": len(records),
        "samples": records,
        "duplicate_c9_c20_floor_pairs": [
            {
                "C9_source_face_id": c9_face,
                "C20_source_face_id": c20_face,
                "station_mm": station,
            }
            for c9_face, c20_face, station in sorted(duplicate_pairs)
        ],
        "non_gap_no_floor_lattice_indices": no_floor,
        "gap_source_floors_requiring_removal": gap_source_floors,
        "station_ray_ownership": ray_records,
        "ownership_seam": {
            "branches_or_changes_more_than_once": branched,
            "first_owner_change_station_mm": (
                min(first_changes) if first_changes else None
            ),
            "last_owner_change_station_mm": (
                max(last_changes) if last_changes else None
            ),
        },
    }


def main():
    report_path = Path(argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path = report_path.with_name(
        "v26_floor_ownership_progress.json"
    )
    context = v17.baseline_context()
    evidence = {
        "input_blend_sha256": context["blend_sha"],
        "joint_authority_sha256": sha_file(JOINT_PATH),
        "cell_authority_sha256": sha_file(CELL_PATH),
        "code_sha256": sha_file(Path(__file__)),
    }
    expected = {
        "input_blend_sha256": EXPECTED_BLEND_SHA256,
        "joint_authority_sha256": EXPECTED_JOINT_SHA256,
        "cell_authority_sha256": EXPECTED_CELL_SHA256,
    }
    actual_without_code = {
        key: evidence[key] for key in expected
    }
    if actual_without_code != expected:
        raise RuntimeError(
            f"{OPERATION}: authority mismatch; actual={actual_without_code}; "
            f"expected={expected}"
        )
    joint = json.loads(JOINT_PATH.read_text(encoding="utf-8"))
    cell_authority = json.loads(CELL_PATH.read_text(encoding="utf-8"))
    cells = (
        cell_authority["atomic_cells"]["C20"]
        + cell_authority["atomic_cells"]["C9"]
    )
    checkpoint = {
        "operation": OPERATION,
        "status": "EXPENSIVE_SOURCE_RAY_CLASSIFICATION_STARTING",
        "evidence": evidence,
        "exact_atomic_cell_ids": [cell["name"] for cell in cells],
        "candidate_construction_started": False,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(progress_path, checkpoint)
    source_tree = BVHTree.FromPolygons(
        context["staged_points"],
        context["staged_faces"],
        all_triangles=False,
    )
    cutter_tree = BVHTree.FromPolygons(
        context["cutter_points"],
        context["cutter_faces"],
        all_triangles=False,
    )
    exposure = exposure_authority(
        context, joint, cells, source_tree, cutter_tree
    )
    checkpoint["status"] = "EXPOSURE_CLASSIFICATION_CHECKPOINTED"
    checkpoint["wearer_facing_face_count"] = sum(
        len(record["wearer_facing_face_ids"])
        for record in exposure.values()
    )
    checkpoint["ambiguous_face_count"] = sum(
        len(record["ambiguous_face_ids"]) for record in exposure.values()
    )
    checkpoint["exposure_fingerprint"] = stable_hash(exposure)
    atomic_json(progress_path, checkpoint)
    gap = gap_authority(context, joint, cutter_tree)
    ownership = ownership_authority(
        context, joint, cells, exposure, source_tree, gap
    )
    failures = []
    if ownership["non_gap_no_floor_lattice_indices"]:
        failures.append("NON_GAP_ZERO_FLOOR")
    if ownership["duplicate_c9_c20_floor_pairs"]:
        failures.append("C9_C20_DUPLICATE_FLOOR")
    if ownership["gap_source_floors_requiring_removal"]:
        failures.append("SOURCE_FLOOR_INSIDE_REQUIRED_FLEX_GAP")
    if ownership["ownership_seam"][
        "branches_or_changes_more_than_once"
    ]:
        failures.append("OWNERSHIP_SEAM_BRANCH_OR_MULTIPLE_CHANGE")
    if any(
        not sample["ordered_cutter_floor_exterior_valid"]
        for sample in ownership["samples"]
    ):
        failures.append("CUTTER_FLOOR_EXTERIOR_LAYER_ORDER_INVERTED")
    report = {
        "operation": OPERATION,
        "status": (
            "V26_FLOOR_OWNERSHIP_SOURCE_CONFLICTS"
            if failures
            else "V26_FLOOR_OWNERSHIP_AUTHORITY_COMPLETE"
        ),
        "scope": (
            "read-only exact atomic-cell exposure and current-source floor "
            "ownership; no candidate authority"
        ),
        "evidence": evidence,
        "contract": {
            "exposure_maximum_spacing_mm": EXPOSURE_SPACING_MM,
            "exposure_minimum_unobstructed_ratio": EXPOSURE_THRESHOLD,
            "exposure_minimum_normal_sign_ratio": EXPOSURE_THRESHOLD,
            "ownership_maximum_spacing_mm": OWNERSHIP_SPACING_MM,
            "minimum_empty_flex_gap_mm": FLEX_GAP_WIDTH_MM,
        },
        "exact_atomic_cell_ids": [cell["name"] for cell in cells],
        "exposure": exposure,
        "ownership": ownership,
        "failure_classes": failures,
        "source_face_ownership_is_unique": (
            len(cell_face_map(cells))
            == sum(len(cell["face_ids"]) for cell in cells)
        ),
        "candidate_construction_started": False,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "promotion": "NOT_PROMOTED",
    }
    report["semantic_fingerprint"] = stable_hash(report)
    atomic_json(report_path, report)
    checkpoint.update(
        {
            "status": "DONE",
            "report_sha256": sha_file(report_path),
            "semantic_fingerprint": report["semantic_fingerprint"],
            "failure_classes": failures,
            "ownership_sample_count": ownership["sample_count"],
        }
    )
    atomic_json(progress_path, checkpoint)
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_path),
                "report_sha256": sha_file(report_path),
                "failure_classes": failures,
                "ownership_sample_count": ownership["sample_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
