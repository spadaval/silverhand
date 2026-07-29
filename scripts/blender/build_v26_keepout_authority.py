#!/usr/bin/env python3
"""Build the exact read-only V26 negative-space keepout authority.

This script consumes the already checkpointed V26 joint and cell authorities.
It does not open, mutate, or save a Blend.  Blender is used only as a
repeatability runner during validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


OPERATION = "BUILD_V26_NEGATIVE_SPACE_AUTHORITY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V26"
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
JOINT_AUTHORITY = EVIDENCE / "v26_joint_authority.json"
CELL_AUTHORITY = EVIDENCE / "v26_cell_authority.json"
OUTPUT = EVIDENCE / "v26_negative_space_authority.json"

INSET_MM = 0.25
APERTURE_HALF_DEPTH_MM = 12.0
ROUTE_HALF_WIDTH_MM = 0.6
ROUTE_HALF_DEPTH_MM = 12.0
ENVELOPE_EXTENSION_MM = 2.0
FLEX_GAP_MINIMUM_MM = 12.0
COINCIDENT_BOUNDARY_TOLERANCE_MM = 0.00001
GEOMETRY_ROUND_DIGITS = 12


def canonical_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def stable_hash(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rounded(values):
    return [round(float(value), GEOMETRY_ROUND_DIGITS) for value in values]


def cross_2d(first, second):
    return float(first[0] * second[1] - first[1] * second[0])


def unit(vector, label):
    length = float(np.linalg.norm(vector))
    if length <= 1e-12:
        raise RuntimeError(
            f"{OPERATION}: cannot normalize {label}; vector length is {length}"
        )
    return np.asarray(vector, dtype=float) / length


def face_normal(points, face):
    first = np.asarray(points[face[0]], dtype=float)
    normal = np.zeros(3, dtype=float)
    for index in range(1, len(face) - 1):
        normal += np.cross(
            np.asarray(points[face[index]], dtype=float) - first,
            np.asarray(points[face[index + 1]], dtype=float) - first,
        )
    return unit(normal, f"face {face}")


def source_geometry(joint):
    coordinates = {}
    faces = {}
    for mask in joint["masks"].values():
        for source_id, point in mask.get("vertex_coordinates_mm", {}).items():
            source_id = int(source_id)
            existing = coordinates.get(source_id)
            value = tuple(float(component) for component in point)
            if existing is not None and existing != value:
                raise RuntimeError(
                    f"{OPERATION}: source vertex {source_id} has conflicting "
                    "checkpointed coordinates"
                )
            coordinates[source_id] = value
        for record in mask.get("faces", []):
            source_id = int(record["source_face_id"])
            vertices = tuple(
                int(vertex) for vertex in record["loop_source_vertex_ids"]
            )
            existing = faces.get(source_id)
            if existing is not None and existing != vertices:
                raise RuntimeError(
                    f"{OPERATION}: source face {source_id} has conflicting "
                    "checkpointed topology"
                )
            faces[source_id] = vertices
    return coordinates, faces


def directed_boundary_edge(edge, candidate_faces, faces):
    first, second = (int(value) for value in edge["vertex_ids"])
    for face_id in sorted(int(value) for value in edge["adjacent_face_ids"]):
        if face_id not in candidate_faces:
            continue
        face = faces[face_id]
        for index, vertex in enumerate(face):
            following = face[(index + 1) % len(face)]
            if {vertex, following} == {first, second}:
                return (vertex, following)
    return (min(first, second), max(first, second))


def order_directed_loop(edge_records, candidate_faces, faces, label):
    directed = [
        directed_boundary_edge(record, candidate_faces, faces)
        for record in edge_records
    ]
    outgoing = defaultdict(list)
    for first, second in directed:
        outgoing[first].append(second)
    if all(len(values) == 1 for values in outgoing.values()):
        start = min(outgoing)
        result = [start]
        current = start
        while True:
            current = outgoing[current][0]
            if current == start:
                break
            if current in result or len(result) > len(directed):
                break
            result.append(current)
        if len(result) == len(directed):
            return result

    adjacency = defaultdict(set)
    for record in edge_records:
        first, second = (int(value) for value in record["vertex_ids"])
        adjacency[first].add(second)
        adjacency[second].add(first)
    if any(len(values) != 2 for values in adjacency.values()):
        raise RuntimeError(
            f"{OPERATION}: {label} is not a simple closed loop; vertex "
            f"degrees are {dict(sorted((k, len(v)) for k, v in adjacency.items()))}"
        )
    start = min(adjacency)
    result = [start]
    previous = None
    current = start
    while True:
        choices = sorted(adjacency[current] - ({previous} if previous else set()))
        following = choices[0]
        if following == start:
            break
        result.append(following)
        previous, current = current, following
    if len(result) != len(edge_records):
        raise RuntimeError(
            f"{OPERATION}: {label} ordered {len(result)} vertices for "
            f"{len(edge_records)} edges"
        )
    return result


def biconnected_edge_components(edge_records):
    edge_by_pair = {}
    adjacency = defaultdict(list)
    for record in edge_records:
        edge = tuple(sorted(int(value) for value in record["vertex_ids"]))
        edge_by_pair[edge] = record
        adjacency[edge[0]].append(edge[1])
        adjacency[edge[1]].append(edge[0])
    discovery = {}
    low = {}
    stack = []
    components = []
    counter = 0

    def visit(vertex, parent):
        nonlocal counter
        counter += 1
        discovery[vertex] = low[vertex] = counter
        for neighbor in sorted(adjacency[vertex]):
            edge = tuple(sorted((vertex, neighbor)))
            if neighbor == parent:
                continue
            if neighbor not in discovery:
                stack.append(edge)
                visit(neighbor, vertex)
                low[vertex] = min(low[vertex], low[neighbor])
                if low[neighbor] >= discovery[vertex]:
                    component = []
                    while stack:
                        popped = stack.pop()
                        component.append(edge_by_pair[popped])
                        if popped == edge:
                            break
                    components.append(component)
            elif discovery[neighbor] < discovery[vertex]:
                stack.append(edge)
                low[vertex] = min(low[vertex], discovery[neighbor])

    for vertex in sorted(adjacency):
        if vertex not in discovery:
            visit(vertex, None)
            if stack:
                components.append([edge_by_pair[edge] for edge in stack])
                stack.clear()
    return sorted(
        (component for component in components if len(component) >= 3),
        key=lambda component: (
            min(min(record["vertex_ids"]) for record in component),
            len(component),
        ),
    )


def plane_frame(loop_points, source_normal_hint=None):
    points = np.asarray(loop_points, dtype=float)
    origin = points.mean(axis=0)
    _, _, vh = np.linalg.svd(points - origin, full_matrices=False)
    normal = unit(vh[-1], "least-squares plane normal")
    winding = np.zeros(3)
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        winding += np.cross(point - origin, following - origin)
    if np.dot(normal, winding) < 0:
        normal = -normal
    if source_normal_hint is not None and np.dot(normal, source_normal_hint) < 0:
        normal = -normal
    tangent_u = unit(points[0] - origin, "plane tangent u")
    tangent_u = unit(
        tangent_u - normal * np.dot(tangent_u, normal),
        "projected plane tangent u",
    )
    tangent_v = unit(np.cross(normal, tangent_u), "plane tangent v")
    projected = np.asarray(
        [
            [np.dot(point - origin, tangent_u), np.dot(point - origin, tangent_v)]
            for point in points
        ]
    )
    signed_area = 0.5 * sum(
        cross_2d(projected[index], projected[(index + 1) % len(projected)])
        for index in range(len(projected))
    )
    if signed_area < 0:
        tangent_v = -tangent_v
        normal = -normal
        projected[:, 1] *= -1
        signed_area = -signed_area
    return origin, tangent_u, tangent_v, normal, projected, float(signed_area)


def intersect_lines(first_point, first_direction, second_point, second_direction):
    cross = cross_2d(first_direction, second_direction)
    if abs(cross) <= 1e-12:
        raise RuntimeError(
            f"{OPERATION}: inward polygon offset encountered parallel edges"
        )
    amount = cross_2d(second_point - first_point, second_direction) / cross
    return first_point + first_direction * amount


def inset_polygon(points, distance):
    result = []
    count = len(points)
    for index in range(count):
        previous = points[(index - 1) % count]
        current = points[index]
        following = points[(index + 1) % count]
        incoming = unit(current - previous, "polygon incoming edge")
        outgoing = unit(following - current, "polygon outgoing edge")
        incoming_normal = np.asarray([-incoming[1], incoming[0]])
        outgoing_normal = np.asarray([-outgoing[1], outgoing[0]])
        result.append(
            intersect_lines(
                previous + incoming_normal * distance,
                incoming,
                current + outgoing_normal * distance,
                outgoing,
            )
        )
    result = np.asarray(result)
    area = 0.5 * sum(
        cross_2d(result[index], result[(index + 1) % count])
        for index in range(count)
    )
    if area <= 1e-10:
        raise RuntimeError(
            f"{OPERATION}: {distance} mm inward offset collapsed a polygon"
        )
    return result


def point_in_triangle(point, first, second, third):
    def cross(a, b, c):
        first_vector = b - a
        second_vector = c - a
        return float(
            first_vector[0] * second_vector[1]
            - first_vector[1] * second_vector[0]
        )

    values = (
        cross(first, second, point),
        cross(second, third, point),
        cross(third, first, point),
    )
    return min(values) >= -1e-10


def triangulate_ccw(points):
    remaining = list(range(len(points)))
    triangles = []
    while len(remaining) > 3:
        ear = None
        for position, current in enumerate(remaining):
            previous = remaining[position - 1]
            following = remaining[(position + 1) % len(remaining)]
            incoming = points[current] - points[previous]
            outgoing = points[following] - points[current]
            if (
                incoming[0] * outgoing[1]
                - incoming[1] * outgoing[0]
                <= 1e-12
            ):
                continue
            if any(
                point_in_triangle(
                    points[other],
                    points[previous],
                    points[current],
                    points[following],
                )
                for other in remaining
                if other not in {previous, current, following}
            ):
                continue
            ear = (position, (previous, current, following))
            break
        if ear is None:
            try:
                from mathutils import Vector
                from mathutils.geometry import tessellate_polygon
            except ImportError as error:
                raise RuntimeError(
                    f"{OPERATION}: deterministic ear clipping found no valid "
                    "ear and Blender tessellation is unavailable"
                ) from error
            vectors = [Vector((float(point[0]), float(point[1]), 0.0)) for point in points]
            index_by_coordinate = {
                (round(vector.x, 12), round(vector.y, 12)): index
                for index, vector in enumerate(vectors)
            }
            tessellated = tessellate_polygon([vectors])
            if not tessellated:
                raise RuntimeError(
                    f"{OPERATION}: deterministic ear clipping and Blender "
                    f"tessellation both failed for {len(points)} vertices"
                )
            return [
                tuple(
                    int(vertex)
                    if isinstance(vertex, int)
                    else index_by_coordinate[
                        (round(vertex.x, 12), round(vertex.y, 12))
                    ]
                    for vertex in triangle
                )
                for triangle in tessellated
            ]
        position, triangle = ear
        triangles.append(triangle)
        remaining.pop(position)
    triangles.append(tuple(remaining))
    return triangles


def convex_mesh_record(record_id, points, faces, source):
    points = [np.asarray(point, dtype=float) for point in points]
    centroid = sum(points, np.zeros(3)) / len(points)
    oriented_faces = []
    planes = []
    for face in faces:
        face = list(face)
        normal = face_normal(points, face)
        face_center = sum((points[index] for index in face), np.zeros(3)) / len(face)
        if np.dot(normal, centroid - face_center) > 0:
            face.reverse()
            normal = -normal
        offset = float(np.dot(normal, points[face[0]]))
        oriented_faces.append(face)
        planes.append(
            {
                "normal": rounded(normal),
                "offset_mm": round(offset, GEOMETRY_ROUND_DIGITS),
                "inside_test": "dot(normal, point) <= offset_mm + tolerance_mm",
            }
        )
    result = {
        "cell_id": record_id,
        "vertices_mm": [rounded(point) for point in points],
        "faces": oriented_faces,
        "half_spaces": planes,
        "source": source,
    }
    result["fingerprint"] = stable_hash(result)
    return result


def clip_polygon_against_half_space(points, normal, offset, tolerance=0.0):
    """Clip a 3D polygon against one convex-cell half-space."""
    if not points:
        return []
    result = []
    previous = np.asarray(points[-1], dtype=float)
    previous_distance = float(np.dot(normal, previous) - offset - tolerance)
    for raw_current in points:
        current = np.asarray(raw_current, dtype=float)
        current_distance = float(np.dot(normal, current) - offset - tolerance)
        previous_inside = previous_distance <= 0.0
        current_inside = current_distance <= 0.0
        if previous_inside != current_inside:
            amount = previous_distance / (previous_distance - current_distance)
            result.append(previous + (current - previous) * amount)
        if current_inside:
            result.append(current)
        previous = current
        previous_distance = current_distance
    return result


def classify_triangle_against_convex_cell(triangle, cell, tolerance=0.0):
    """Return DISJOINT, BOUNDARY_ONLY, or INTERIOR_OVERLAP."""
    clipped = [np.asarray(point, dtype=float) for point in triangle]
    planes = [
        (
            np.asarray(record["normal"], dtype=float),
            float(record["offset_mm"]),
        )
        for record in cell["half_spaces"]
    ]
    for normal, offset in planes:
        clipped = clip_polygon_against_half_space(
            clipped,
            normal,
            offset,
            tolerance,
        )
        if not clipped:
            return "DISJOINT"
    centroid = sum(clipped, np.zeros(3)) / len(clipped)
    strict_inside = all(
        float(np.dot(normal, centroid) - offset) < -1e-9
        for normal, offset in planes
    )
    return "INTERIOR_OVERLAP" if strict_inside else "BOUNDARY_ONLY"


def construction_audit(cells):
    maximum_residual = -float("inf")
    vertex_plane_test_count = 0
    for cell in cells:
        for point in cell["vertices_mm"]:
            point = np.asarray(point, dtype=float)
            for plane in cell["half_spaces"]:
                residual = float(
                    np.dot(np.asarray(plane["normal"]), point)
                    - float(plane["offset_mm"])
                )
                maximum_residual = max(maximum_residual, residual)
                vertex_plane_test_count += 1
                if residual > 1e-8:
                    raise RuntimeError(
                        f"{OPERATION}: convex half-space audit failed for "
                        f"{cell['cell_id']}; residual={residual:.12g} mm"
                    )
        face = cell["faces"][0]
        boundary_triangle = [
            cell["vertices_mm"][index] for index in face[:3]
        ]
        if (
            classify_triangle_against_convex_cell(
                boundary_triangle,
                cell,
                tolerance=1e-8,
            )
            != "BOUNDARY_ONLY"
        ):
            raise RuntimeError(
                f"{OPERATION}: boundary-contact classifier self-test failed "
                f"for {cell['cell_id']}"
            )
    return {
        "convex_cell_count": len(cells),
        "vertex_plane_test_count": vertex_plane_test_count,
        "maximum_vertex_half_space_residual_mm": round(
            maximum_residual,
            GEOMETRY_ROUND_DIGITS,
        ),
        "required_maximum_residual_mm": 1e-8,
        "boundary_triangle_classifier_self_test_count": len(cells),
        "boundary_triangle_classifier_expected_result": "BOUNDARY_ONLY",
        "status": "DONE",
    }


def triangular_prism(record_id, triangle, normal, low, high, source):
    normal = unit(normal, f"{record_id} extrusion normal")
    points = [np.asarray(point, dtype=float) for point in triangle]
    base = [point + normal * low for point in points]
    top = [point + normal * high for point in points]
    return convex_mesh_record(
        record_id,
        [*base, *top],
        [
            [0, 2, 1],
            [3, 4, 5],
            [0, 1, 4, 3],
            [1, 2, 5, 4],
            [2, 0, 3, 5],
        ],
        source,
    )


def merge_cell_meshes(cells):
    vertices = []
    faces = []
    for cell in cells:
        offset = len(vertices)
        vertices.extend(cell["vertices_mm"])
        faces.extend([[offset + index for index in face] for face in cell["faces"]])
    return {"vertices_mm": vertices, "faces": faces}


def loop_prism_union(
    record_id,
    vertex_ids,
    coordinates,
    source_face_ids,
    faces,
    low,
    high,
    source,
):
    points = [np.asarray(coordinates[vertex], dtype=float) for vertex in vertex_ids]
    normals = []
    for face_id in source_face_ids:
        if face_id in faces:
            normals.append(
                face_normal(coordinates, faces[face_id])
            )
    hint = unit(sum(normals, np.zeros(3)), f"{record_id} source normal") if normals else None
    origin, tangent_u, tangent_v, normal, projected, source_area = plane_frame(
        points,
        hint,
    )
    inset = inset_polygon(projected, INSET_MM)
    triangles = triangulate_ccw(inset)
    inset_world = [
        origin + tangent_u * point[0] + tangent_v * point[1] for point in inset
    ]
    cells = []
    for index, triangle in enumerate(triangles):
        cells.append(
            triangular_prism(
                f"{record_id}_CELL_{index:03d}",
                [inset_world[item] for item in triangle],
                normal,
                low,
                high,
                {
                    **source,
                    "inset_loop_vertex_indices": list(triangle),
                },
            )
        )
    merged = merge_cell_meshes(cells)
    result = {
        "keepout_id": record_id,
        "kind": "TRIANGULATED_PRISM_UNION",
        "source": source,
        "ordered_source_vertex_ids": vertex_ids,
        "exact_source_coordinates_mm": [rounded(point) for point in points],
        "least_squares_plane": {
            "origin_mm": rounded(origin),
            "tangent_u": rounded(tangent_u),
            "tangent_v": rounded(tangent_v),
            "normal": rounded(normal),
            "source_projected_area_mm2": round(source_area, GEOMETRY_ROUND_DIGITS),
        },
        "inward_boundary_offset_mm": INSET_MM,
        "inset_vertices_2d_mm": [rounded(point) for point in inset],
        "extrusion_low_mm": round(low, GEOMETRY_ROUND_DIGITS),
        "extrusion_high_mm": round(high, GEOMETRY_ROUND_DIGITS),
        "cells": cells,
        "triangle_mesh": merged,
    }
    result["fingerprint"] = stable_hash(result)
    return result


def route_prism(record_id, record, coordinates, faces):
    first, second = (int(value) for value in record["vertex_ids"])
    start = np.asarray(coordinates[first], dtype=float)
    end = np.asarray(coordinates[second], dtype=float)
    tangent = unit(end - start, f"{record_id} tangent")
    normals = [
        face_normal(coordinates, faces[int(face_id)])
        for face_id in record["adjacent_face_ids"]
        if int(face_id) in faces
    ]
    if not normals:
        raise RuntimeError(
            f"{OPERATION}: {record_id} has no checkpointed adjacent source face"
        )
    normal = unit(sum(normals, np.zeros(3)), f"{record_id} source normal")
    width = unit(np.cross(normal, tangent), f"{record_id} tangent-normal")
    normal = unit(np.cross(tangent, width), f"{record_id} orthogonal normal")
    points = []
    for endpoint in (start, end):
        for width_sign, depth_sign in (
            (-1, -1),
            (1, -1),
            (1, 1),
            (-1, 1),
        ):
            points.append(
                endpoint
                + width * width_sign * ROUTE_HALF_WIDTH_MM
                + normal * depth_sign * ROUTE_HALF_DEPTH_MM
            )
    return convex_mesh_record(
        record_id,
        points,
        [
            [0, 3, 2, 1],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ],
        {
            "source_edge_id": int(record["edge_id"]),
            "source_vertex_ids": [first, second],
            "adjacent_source_face_ids": [
                int(value) for value in record["adjacent_face_ids"]
            ],
            "exact_source_coordinates_mm": [rounded(start), rounded(end)],
            "frame": {
                "edge_tangent": rounded(tangent),
                "surface_tangent_normal": rounded(width),
                "source_surface_normal": rounded(normal),
            },
            "half_width_mm": ROUTE_HALF_WIDTH_MM,
            "half_depth_mm": ROUTE_HALF_DEPTH_MM,
        },
    )


def box_record(record_id, center, axes, half_extents, source):
    points = []
    for x, y, z in (
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ):
        points.append(
            center
            + axes[0] * x * half_extents[0]
            + axes[1] * y * half_extents[1]
            + axes[2] * z * half_extents[2]
        )
    return convex_mesh_record(
        record_id,
        points,
        [
            [0, 3, 2, 1],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ],
        source,
    )


def central_opening_keepout(joint, reconstruction_points):
    authority = joint["negative_space"]
    source = authority["central_opening"]
    points = [
        np.asarray(point, dtype=float)
        for point in authority["central_opening_points_mm"]
    ]
    faces = [tuple(int(index) for index in face) for face in authority["central_opening_faces"]]
    source_vertex_count = len(source["source_vertex_ids"])
    if len(points) != source_vertex_count + 1:
        raise RuntimeError(
            f"{OPERATION}: central-opening authority has {len(points)} points "
            f"for {source_vertex_count} source vertices; expected one shared "
            "interior fan point"
        )
    center_index = source_vertex_count
    center = points[center_index]
    inset_points = list(points)
    for index in range(source_vertex_count):
        inset_points[index] = (
            points[index]
            + unit(center - points[index], f"central opening inset vertex {index}")
            * INSET_MM
        )

    group = authority["source_open_routes"]["groups"][0]
    edge_id_by_pair = {
        tuple(sorted(map(int, pair))): int(edge_id)
        for edge_id, pair in zip(group["edge_ids"], group["edge_vertex_ids"])
    }
    local_to_source = {
        local_id: int(source_id)
        for local_id, source_id in enumerate(source["source_vertex_ids"])
    }
    cells = []
    for index, face in enumerate(faces):
        boundary = [vertex for vertex in face if vertex != center_index]
        if len(boundary) != 2:
            raise RuntimeError(
                f"{OPERATION}: central-opening fan face {index} does not have "
                "exactly one boundary edge"
            )
        source_edge = tuple(
            sorted(local_to_source[vertex] for vertex in boundary)
        )
        if source_edge not in edge_id_by_pair:
            raise RuntimeError(
                f"{OPERATION}: central-opening fan face {index} source edge "
                f"{source_edge} is absent from exact source-open authority"
            )
        triangle = [inset_points[vertex] for vertex in face]
        normal = face_normal(triangle, (0, 1, 2))
        projections = [
            float(np.dot(point - triangle[0], normal))
            for point in reconstruction_points
        ]
        low = min(projections) - ENVELOPE_EXTENSION_MM
        high = max(projections) + ENVELOPE_EXTENSION_MM
        cells.append(
            triangular_prism(
                f"CENTRAL_OPENING_FAN_CELL_{index:03d}",
                triangle,
                normal,
                low,
                high,
                {
                    "source_group": "exact_source_open_edges.groups[0]",
                    "source_group_status": group["status"],
                    "source_edge_id": edge_id_by_pair[source_edge],
                    "source_edge_vertex_ids": list(source_edge),
                    "source_fan_face": list(face),
                    "source_fan_coordinates_mm": [
                        rounded(points[vertex]) for vertex in face
                    ],
                    "inward_boundary_offset_mm": INSET_MM,
                    "inset_method": (
                        "each exact articulated boundary vertex moves 0.25 mm "
                        "toward the persisted shared interior fan point"
                    ),
                    "extrusion_low_mm": round(low, GEOMETRY_ROUND_DIGITS),
                    "extrusion_high_mm": round(high, GEOMETRY_ROUND_DIGITS),
                    "envelope_extension_mm": ENVELOPE_EXTENSION_MM,
                },
            )
        )
    result = {
        "kind": "ARTICULATED_TRIANGULAR_PRISM_UNION",
        "source_group_status": group["status"],
        "source_boundary_fingerprint": source["fingerprint"],
        "source_vertex_ids": source["source_vertex_ids"],
        "exact_source_coordinates_mm": source["coordinates_mm"],
        "source_edge_vertex_ids": source["edge_vertex_ids"],
        "persisted_shared_interior_point_mm": rounded(center),
        "inward_boundary_offset_mm": INSET_MM,
        "decomposition": (
            "the persisted nonplanar articulated fan is retained exactly; "
            "each boundary triangle becomes one convex swept-prism cell"
        ),
        "cells": cells,
        "triangle_mesh": merge_cell_meshes(cells),
    }
    result["fingerprint"] = stable_hash(result)
    return result


def flex_gap_keepout(joint, coordinates):
    named = {
        int(source_id): np.asarray(point, dtype=float)
        for source_id, point in joint["named_controls"].items()
    }
    upper = (named[2074] + named[1257]) * 0.5
    lower = (named[2119] + named[1295]) * 0.5
    chord = unit(lower - upper, "flex-gap chord axis")
    authority_points = np.asarray(
        [
            point
            for mask_name in (
                "C20_INNER_BOWL_REPLACEABLE_BASE",
                "C9_PROXIMAL_REPLACEABLE_BASE",
            )
            for point in joint["masks"][mask_name]["vertex_coordinates_mm"].values()
        ],
        dtype=float,
    )
    centered = authority_points - authority_points.mean(axis=0)
    covariance = centered.T @ centered
    values, vectors = np.linalg.eigh(covariance)
    candidates = [
        vectors[:, index] - chord * np.dot(vectors[:, index], chord)
        for index in reversed(np.argsort(values))
    ]
    transverse = unit(
        next(vector for vector in candidates if np.linalg.norm(vector) > 1e-8),
        "flex-gap transverse axis",
    )
    depth = unit(np.cross(chord, transverse), "flex-gap depth axis")
    center = (upper + lower) * 0.5
    projections = authority_points - center
    transverse_half = (
        max(abs(float(np.dot(point, transverse))) for point in projections)
        + ENVELOPE_EXTENSION_MM
    )
    depth_half = (
        max(abs(float(np.dot(point, depth))) for point in projections)
        + ENVELOPE_EXTENSION_MM
    )
    landmark_separation = float(np.linalg.norm(lower - upper))
    if landmark_separation < FLEX_GAP_MINIMUM_MM:
        raise RuntimeError(
            f"{OPERATION}: flex-gap landmark separation is "
            f"{landmark_separation:.9f} mm, below {FLEX_GAP_MINIMUM_MM} mm"
        )
    return box_record(
        "FLEX_GAP_MINIMUM_CORE",
        center,
        (chord, transverse, depth),
        (FLEX_GAP_MINIMUM_MM * 0.5, transverse_half, depth_half),
        {
            "construction": (
                "12 mm chordwise slab centered between the exact averaged "
                "C20/C9 upper and lower registration witnesses; transverse "
                "axes cover both maximum reconstruction masks plus 2 mm"
            ),
            "upper_source_vertex_ids": [2074, 1257],
            "lower_source_vertex_ids": [2119, 1295],
            "upper_midpoint_mm": rounded(upper),
            "lower_midpoint_mm": rounded(lower),
            "landmark_separation_mm": round(
                landmark_separation,
                GEOMETRY_ROUND_DIGITS,
            ),
            "minimum_chordwise_width_mm": FLEX_GAP_MINIMUM_MM,
            "envelope_extension_mm": ENVELOPE_EXTENSION_MM,
            "frame": {
                "center_mm": rounded(center),
                "chord_axis": rounded(chord),
                "transverse_axis": rounded(transverse),
                "depth_axis": rounded(depth),
                "half_extents_mm": rounded(
                    (
                        FLEX_GAP_MINIMUM_MM * 0.5,
                        transverse_half,
                        depth_half,
                    )
                ),
            },
        },
    )


def build_authority():
    joint = json.loads(JOINT_AUTHORITY.read_text(encoding="utf-8"))
    cell = json.loads(CELL_AUTHORITY.read_text(encoding="utf-8"))
    coordinates, faces = source_geometry(joint)
    c20_faces = set(
        joint["masks"]["C20_INNER_BOWL_REPLACEABLE_BASE"]["face_ids"]
    )
    seam = joint["negative_space"]["full_inner_bowl_seam"]

    aperture_loops = []
    for index, group in enumerate(seam["boundary_groups"]):
        if group["status"] != "closed":
            continue
        records_by_edge = {
            int(record["edge_id"]): record
            for record in seam["boundary_edge_records"]
        }
        records = [records_by_edge[int(edge_id)] for edge_id in group["edge_ids"]]
        ordered = order_directed_loop(
            records,
            c20_faces,
            faces,
            f"aperture group {index}",
        )
        adjacent_faces = sorted(
            {
                int(face_id)
                for record in records
                for face_id in record["adjacent_face_ids"]
            }
        )
        aperture_loops.append(
            loop_prism_union(
                f"C20_APERTURE_LOOP_{index:02d}",
                ordered,
                coordinates,
                adjacent_faces,
                faces,
                -APERTURE_HALF_DEPTH_MM,
                APERTURE_HALF_DEPTH_MM,
                {
                    "authority": "exact_full_inner_bowl_seam",
                    "source_group_index": index,
                    "source_status": group["status"],
                    "source_edge_ids": [int(value) for value in group["edge_ids"]],
                    "source_edge_vertex_ids": group["edge_vertex_ids"],
                    "extrusion_half_depth_mm": APERTURE_HALF_DEPTH_MM,
                },
            )
        )

    route_records_by_edge = {
        int(record["edge_id"]): record
        for record in seam["boundary_edge_records"]
    }
    routes = []
    route_groups = []
    for index, group in enumerate(seam["boundary_groups"]):
        if group["status"] != "open":
            continue
        group_cells = []
        for edge_id in group["edge_ids"]:
            record = route_records_by_edge[int(edge_id)]
            group_cells.append(
                route_prism(
                    f"C20_SOURCE_OPEN_ROUTE_{index:02d}_EDGE_{int(edge_id):05d}",
                    record,
                    coordinates,
                    faces,
                )
            )
        route_groups.append(
            {
                "route_id": f"C20_SOURCE_OPEN_ROUTE_{index:02d}",
                "source_group_index": index,
                "source_status": group["status"],
                "source_edge_ids": [int(value) for value in group["edge_ids"]],
                "source_endpoint_vertex_ids": [
                    int(value) for value in group["endpoint_vertex_ids"]
                ],
                "cell_ids": [record["cell_id"] for record in group_cells],
                "fingerprint": stable_hash(group_cells),
            }
        )
        routes.extend(group_cells)

    reconstruction_points = np.asarray(
        [
            point
            for mask_name in (
                "C20_INNER_BOWL_REPLACEABLE_BASE",
                "C9_PROXIMAL_REPLACEABLE_BASE",
            )
            for point in joint["masks"][mask_name]["vertex_coordinates_mm"].values()
        ],
        dtype=float,
    )
    central_opening = central_opening_keepout(joint, reconstruction_points)

    flex_gap = flex_gap_keepout(joint, coordinates)
    tip = joint["negative_space"]["tip_gap_witness"]
    all_cells = [
        *[
            prism
            for aperture in aperture_loops
            for prism in aperture["cells"]
        ],
        *routes,
        *central_opening["cells"],
        flex_gap,
    ]
    authority = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": "V26_NEGATIVE_SPACE_AUTHORITY_CHECKPOINTED",
        "scope": {
            "read_only": True,
            "candidate_construction_or_search": False,
            "mutation_authority": False,
            "mutation_started": False,
            "geometry_emitted_to_blend": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        },
        "inputs": {
            "implementation_code": str(Path(__file__).resolve()),
            "implementation_code_sha256": sha_file(Path(__file__).resolve()),
            "joint_authority": str(JOINT_AUTHORITY),
            "joint_authority_sha256": sha_file(JOINT_AUTHORITY),
            "cell_authority": str(CELL_AUTHORITY),
            "cell_authority_sha256": sha_file(CELL_AUTHORITY),
            "cell_authority_semantic_fingerprint": cell["fingerprint"],
            "input_blend": joint["input_blend"],
            "input_blend_sha256": joint["input_blend_sha256"],
        },
        "tolerances": {
            "closed_loop_inward_offset_mm": INSET_MM,
            "aperture_extrusion_half_depth_mm": APERTURE_HALF_DEPTH_MM,
            "source_open_route_half_width_mm": ROUTE_HALF_WIDTH_MM,
            "source_open_route_half_depth_mm": ROUTE_HALF_DEPTH_MM,
            "envelope_extension_mm": ENVELOPE_EXTENSION_MM,
            "minimum_flex_gap_chordwise_width_mm": FLEX_GAP_MINIMUM_MM,
            "declared_boundary_coincidence_mm": (
                COINCIDENT_BOUNDARY_TOLERANCE_MM
            ),
            "candidate_interior_tolerance_mm": 0.0,
        },
        "aperture_keepouts": aperture_loops,
        "source_open_route_keepouts": {
            "groups": route_groups,
            "cells": routes,
            "triangle_mesh": merge_cell_meshes(routes),
        },
        "central_opening_keepouts": central_opening,
        "flex_gap_keepout": flex_gap,
        "c_tip_witness": {
            "source_vertex_ids": tip["source_vertex_ids"],
            "exact_coordinates_mm": tip["coordinates_mm"],
            "source_distance_mm": tip["distance_mm"],
            "required_candidate_minimum_distance_mm": round(
                float(tip["distance_mm"]) - 2.0,
                GEOMETRY_ROUND_DIGITS,
            ),
            "candidate_contract": (
                "every future candidate vertex and adaptive interior sample "
                "must remain at least the required distance from the opposite "
                "B0 tip; this scalar witness supplements prism intersections"
            ),
        },
        "future_candidate_triangle_overlap_api": {
            "implementation": {
                "module": "scripts/blender/build_v26_keepout_authority.py",
                "convex_cell_function": (
                    "classify_triangle_against_convex_cell"
                ),
                "half_space_clip_function": (
                    "clip_polygon_against_half_space"
                ),
            },
            "input": (
                "candidate triangle exact 3x3 mm coordinate array; keepout "
                "record cell half_spaces; declared coincident source IDs"
            ),
            "algorithm": [
                "clip the candidate triangle polygon against every convex-cell half-space",
                "classify empty clipped polygon as DISJOINT",
                "classify positive-area or positive-depth clipped polygon as INTERIOR_OVERLAP",
                "classify zero-area contact as BOUNDARY_ONLY only when every contact point belongs to a declared coincident retained vertex/edge within 0.00001 mm",
                "union classifications across every convex cell in the keepout",
            ],
            "half_space_inside_test": (
                "dot(normal, point) <= offset_mm + tolerance_mm"
            ),
            "required_result": "zero INTERIOR_OVERLAP",
            "boundary_exception": (
                "declared coincident retained boundary vertices/edges only; "
                "candidate interiors receive no tolerance"
            ),
            "prohibited_substitutions": [
                "point_to_edge_distance",
                "vertex_only_containment",
                "edge_midpoint_sampling",
                "BVH_overlap_without_boundary_contact_classification",
            ],
        },
        "construction_audit": construction_audit(all_cells),
        "summary": {
            "aperture_loop_count": len(aperture_loops),
            "aperture_convex_cell_count": sum(
                len(record["cells"]) for record in aperture_loops
            ),
            "source_open_route_count": len(route_groups),
            "source_open_route_edge_prism_count": len(routes),
            "central_opening_source_boundary_edge_count": len(
                central_opening["source_edge_vertex_ids"]
            ),
            "central_opening_convex_cell_count": len(
                central_opening["cells"]
            ),
            "flex_gap_convex_cell_count": 1,
        },
    }
    authority["geometry_fingerprint"] = stable_hash(
        {
            "apertures": aperture_loops,
            "source_open_routes": routes,
            "central_opening": central_opening,
            "flex_gap": flex_gap,
        }
    )
    authority["fingerprint"] = stable_hash(authority)
    return authority


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    if "--" in __import__("sys").argv:
        arguments = __import__("sys").argv[
            __import__("sys").argv.index("--") + 1 :
        ]
    else:
        arguments = __import__("sys").argv[1:]
    return parser.parse_args(arguments)


def main():
    args = parse_args()
    authority = build_authority()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(authority, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(
        "DONE "
        f"{OPERATION}: {args.output}; "
        f"fingerprint={authority['fingerprint']}; "
        f"summary={authority['summary']}"
    )


if __name__ == "__main__":
    main()
