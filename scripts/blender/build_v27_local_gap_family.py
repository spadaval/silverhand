#!/usr/bin/env python3
"""Build the read-only V27 Stage 2b local flex-gap family authority."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable

import bpy


OPERATION = "BUILD_V27_LOCAL_GAP_FAMILY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
RESULT = "V27_LOCAL_GAP_FAMILY_CHECKPOINTED"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
AGGREGATE_PATH = V27 / "v27_aggregate_authority.json"
AGGREGATE_RECEIPT_PATH = V27 / "v27_aggregate_authority_receipt.json"
DEFAULT_OUTPUT = V27 / "v27_local_gap_family_authority.json"
DEFAULT_RECEIPT = V27 / "v27_local_gap_family_authority_receipt.json"
SOURCE_OBJECT = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
TOLERANCE_MM = 1e-7
K_SHORTEST = 3

FROZEN_HASHES = {
    "aggregate_authority": (
        AGGREGATE_PATH,
        "43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338",
    ),
    "aggregate_receipt": (
        AGGREGATE_RECEIPT_PATH,
        "f4d1e3190999bd22bb9477953bd541f41c0d65b2dba86f729d854920ca0dc938",
    ),
}

PARAMETER_AXES = {
    "requested_empty_chord_width_mm": [12, 14, 16, 18],
    "chord_orientation_degrees": [-30, -20, -10, 0, 10, 20, 30],
    "c20_signed_local_normal_depth_mm": [-12, -8, -4, -2, 0, 2, 4, 8, 12],
    "c9_signed_local_normal_depth_mm": [-12, -8, -4, -2, 0, 2, 4, 8, 12],
    "c20_to_c9_displacement_allocation": [0, 0.25, 0.5, 0.75, 1.0],
}


class FrameDegenerate(RuntimeError):
    """Reject one local chain or pair whose source-led frame is undefined."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{OPERATION}: cannot read JSON authority {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeError(
            f"{OPERATION}: authority {path} is {type(value).__name__}, "
            "expected object"
        )
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode()
        + b"\n"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def add(left: Iterable[float], right: Iterable[float]) -> list[float]:
    return [a + b for a, b in zip(left, right, strict=True)]


def sub(left: Iterable[float], right: Iterable[float]) -> list[float]:
    return [a - b for a, b in zip(left, right, strict=True)]


def scale(vector: Iterable[float], amount: float) -> list[float]:
    return [value * amount for value in vector]


def dot(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def cross(left: Iterable[float], right: Iterable[float]) -> list[float]:
    a = list(left)
    b = list(right)
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def length(vector: Iterable[float]) -> float:
    return math.sqrt(dot(vector, vector))


def normalized(vector: Iterable[float], label: str) -> list[float]:
    values = list(vector)
    magnitude = length(values)
    if magnitude <= TOLERANCE_MM:
        raise FrameDegenerate(
            f"{OPERATION}: V27_LOCAL_GAP_FRAME_DEGENERATE; {label}"
        )
    return scale(values, 1.0 / magnitude)


def centroid(points: list[list[float]]) -> list[float]:
    if not points:
        raise RuntimeError(f"{OPERATION}: cannot compute centroid of empty point set")
    return [
        sum(point[axis] for point in points) / len(points)
        for axis in range(3)
    ]


def edge_key(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def path_length(
    path: tuple[int, ...], weights: dict[tuple[int, int], float]
) -> float:
    return sum(
        weights[edge_key(left, right)]
        for left, right in zip(path, path[1:], strict=False)
    )


def shortest_path(
    graph: dict[int, tuple[int, ...]],
    weights: dict[tuple[int, int], float],
    start: int,
    goal: int,
    banned_nodes: set[int],
    banned_edges: set[tuple[int, int]],
) -> tuple[int, ...] | None:
    if start in banned_nodes or goal in banned_nodes:
        return None
    queue: list[tuple[float, tuple[int, ...], int]] = [(0.0, (start,), start)]
    best: dict[int, tuple[float, tuple[int, ...]]] = {}
    while queue:
        distance, path, node = heapq.heappop(queue)
        previous = best.get(node)
        if previous is not None and previous <= (distance, path):
            continue
        best[node] = (distance, path)
        if node == goal:
            return path
        for neighbor in graph.get(node, ()):
            if neighbor in banned_nodes or neighbor in path:
                continue
            key = edge_key(node, neighbor)
            if key in banned_edges:
                continue
            heapq.heappush(
                queue,
                (distance + weights[key], path + (neighbor,), neighbor),
            )
    return None


def yen_paths(
    graph: dict[int, tuple[int, ...]],
    weights: dict[tuple[int, int], float],
    start: int,
    goal: int,
    boundary_vertices: set[int],
) -> list[tuple[int, ...]]:
    interior_boundary = boundary_vertices - {start, goal}
    first = shortest_path(
        graph, weights, start, goal, interior_boundary, set()
    )
    if first is None:
        return []
    accepted = [first]
    candidates: list[tuple[float, tuple[int, ...]]] = []
    queued: set[tuple[int, ...]] = set()
    for _ in range(1, K_SHORTEST):
        previous = accepted[-1]
        for spur_index in range(len(previous) - 1):
            root = previous[: spur_index + 1]
            banned_edges = {
                edge_key(path[spur_index], path[spur_index + 1])
                for path in accepted
                if len(path) > spur_index + 1
                and path[: spur_index + 1] == root
            }
            banned_nodes = interior_boundary | set(root[:-1])
            spur = shortest_path(
                graph,
                weights,
                root[-1],
                goal,
                banned_nodes,
                banned_edges,
            )
            if spur is None:
                continue
            candidate = root[:-1] + spur
            if candidate in accepted or candidate in queued:
                continue
            queued.add(candidate)
            heapq.heappush(
                candidates, (path_length(candidate, weights), candidate)
            )
        if not candidates:
            break
        _, selected = heapq.heappop(candidates)
        accepted.append(selected)
    return accepted


def source_face_normal_area(
    mesh: bpy.types.Mesh, face_id: int
) -> tuple[list[float], float]:
    polygon = mesh.polygons[face_id]
    normal = [float(value) for value in polygon.normal]
    area = float(polygon.area)
    return normal, area


def path_frames(
    mesh: bpy.types.Mesh,
    path: tuple[int, ...],
    selected_incident_faces: dict[int, set[int]],
) -> list[dict[str, Any]]:
    points = [
        [float(value) for value in mesh.vertices[vertex_id].co]
        for vertex_id in path
    ]
    frames = []
    previous_normal: list[float] | None = None
    for index, (vertex_id, point) in enumerate(zip(path, points, strict=True)):
        if index == 0:
            tangent_vector = sub(points[1], point)
        elif index == len(path) - 1:
            tangent_vector = sub(point, points[index - 1])
        else:
            tangent_vector = sub(points[index + 1], points[index - 1])
        tangent = normalized(
            tangent_vector, f"path={path}; vertex={vertex_id}; zero tangent"
        )
        weighted_normal = [0.0, 0.0, 0.0]
        for face_id in sorted(selected_incident_faces[vertex_id]):
            face_normal, area = source_face_normal_area(mesh, face_id)
            weighted_normal = add(weighted_normal, scale(face_normal, area))
        normal = normalized(
            weighted_normal,
            f"path={path}; vertex={vertex_id}; zero selected-face normal",
        )
        if previous_normal is not None and dot(previous_normal, normal) <= 0.0:
            raise FrameDegenerate(
                f"{OPERATION}: V27_LOCAL_GAP_FRAME_DEGENERATE; "
                f"path={path}; opposing normals at vertex={vertex_id}"
            )
        normal = normalized(
            sub(normal, scale(tangent, dot(normal, tangent))),
            f"path={path}; vertex={vertex_id}; normal parallel to tangent",
        )
        binormal = normalized(
            cross(normal, tangent),
            f"path={path}; vertex={vertex_id}; zero chord",
        )
        if frames and dot(frames[-1]["transported_chord"], binormal) < 0.0:
            binormal = scale(binormal, -1.0)
        frames.append(
            {
                "vertex_id": vertex_id,
                "point_mm": point,
                "tangent": tangent,
                "normal": normal,
                "transported_chord": binormal,
            }
        )
        previous_normal = normal
    return frames


def cumulative_arclength(points: list[list[float]]) -> tuple[list[float], float]:
    values = [0.0]
    for start, end in zip(points, points[1:], strict=False):
        values.append(values[-1] + length(sub(end, start)))
    if values[-1] <= TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: V27_LOCAL_GAP_FRAME_DEGENERATE; zero path length"
        )
    return [value / values[-1] for value in values], values[-1]


def interpolate_frame(
    frames: list[dict[str, Any]], parameters: list[float], value: float
) -> dict[str, Any]:
    if value <= 0.0:
        frame = frames[0]
        return {
            "point_mm": list(frame["point_mm"]),
            "tangent": list(frame["tangent"]),
            "normal": list(frame["normal"]),
            "transported_chord": list(frame["transported_chord"]),
        }
    if value >= 1.0:
        frame = frames[-1]
        return {
            "point_mm": list(frame["point_mm"]),
            "tangent": list(frame["tangent"]),
            "normal": list(frame["normal"]),
            "transported_chord": list(frame["transported_chord"]),
        }
    upper = next(index for index, item in enumerate(parameters) if item >= value)
    lower = upper - 1
    span = parameters[upper] - parameters[lower]
    factor = (value - parameters[lower]) / span
    point = add(
        frames[lower]["point_mm"],
        scale(sub(frames[upper]["point_mm"], frames[lower]["point_mm"]), factor),
    )
    tangent = normalized(
        add(
            scale(frames[lower]["tangent"], 1.0 - factor),
            scale(frames[upper]["tangent"], factor),
        ),
        "interpolated tangent",
    )
    normal = normalized(
        add(
            scale(frames[lower]["normal"], 1.0 - factor),
            scale(frames[upper]["normal"], factor),
        ),
        "interpolated normal",
    )
    normal = normalized(
        sub(normal, scale(tangent, dot(normal, tangent))),
        "interpolated normal parallel to tangent",
    )
    chord = normalized(cross(normal, tangent), "interpolated chord")
    transported = add(
        scale(frames[lower]["transported_chord"], 1.0 - factor),
        scale(frames[upper]["transported_chord"], factor),
    )
    if dot(chord, transported) < 0.0:
        chord = scale(chord, -1.0)
    return {
        "point_mm": point,
        "tangent": tangent,
        "normal": normal,
        "transported_chord": chord,
    }


def segment_distance(
    first_start: list[float],
    first_end: list[float],
    second_start: list[float],
    second_end: list[float],
) -> float:
    first = sub(first_end, first_start)
    second = sub(second_end, second_start)
    offset = sub(first_start, second_start)
    aa = dot(first, first)
    bb = dot(first, second)
    cc = dot(second, second)
    dd = dot(first, offset)
    ee = dot(second, offset)
    denominator = aa * cc - bb * bb
    first_parameter = 0.0
    second_parameter = 0.0
    if aa <= TOLERANCE_MM and cc <= TOLERANCE_MM:
        return length(offset)
    if aa <= TOLERANCE_MM:
        second_parameter = min(1.0, max(0.0, ee / cc))
    elif cc <= TOLERANCE_MM:
        first_parameter = min(1.0, max(0.0, -dd / aa))
    else:
        if abs(denominator) > TOLERANCE_MM:
            first_parameter = min(
                1.0, max(0.0, (bb * ee - cc * dd) / denominator)
            )
        second_parameter = (bb * first_parameter + ee) / cc
        if second_parameter < 0.0:
            second_parameter = 0.0
            first_parameter = min(1.0, max(0.0, -dd / aa))
        elif second_parameter > 1.0:
            second_parameter = 1.0
            first_parameter = min(1.0, max(0.0, (bb - dd) / aa))
    first_point = add(first_start, scale(first, first_parameter))
    second_point = add(second_start, scale(second, second_parameter))
    return length(sub(first_point, second_point))


def pair_record(
    c20: dict[str, Any], c9: dict[str, Any], pair_index: int
) -> dict[str, Any] | None:
    parameters = sorted(
        set(c20["normalized_arclength"]) | set(c9["normalized_arclength"])
    )
    samples = []
    ruled_segments = []
    for parameter in parameters:
        frame20 = interpolate_frame(
            c20["frames"], c20["normalized_arclength"], parameter
        )
        frame9 = interpolate_frame(
            c9["frames"], c9["normalized_arclength"], parameter
        )
        chord = normalized(
            sub(frame9["point_mm"], frame20["point_mm"]),
            (
                f"pair={c20['chain_id']}/{c9['chain_id']}; "
                f"parameter={parameter}; coincident sheets"
            ),
        )
        if dot(frame20["transported_chord"], chord) < 0.0:
            frame20["transported_chord"] = scale(
                frame20["transported_chord"], -1.0
            )
        if dot(frame9["transported_chord"], scale(chord, -1.0)) < 0.0:
            frame9["transported_chord"] = scale(
                frame9["transported_chord"], -1.0
            )
        samples.append(
            {
                "normalized_arclength": parameter,
                "c20": frame20,
                "c9": frame9,
                "source_separation_mm": length(
                    sub(frame9["point_mm"], frame20["point_mm"])
                ),
                "oriented_c20_to_c9_chord": chord,
            }
        )
        ruled_segments.append((frame20["point_mm"], frame9["point_mm"]))
    for left in range(len(ruled_segments)):
        for right in range(left + 2, len(ruled_segments)):
            if segment_distance(
                *ruled_segments[left], *ruled_segments[right]
            ) <= TOLERANCE_MM:
                return None
    quads = []
    for index in range(len(samples) - 1):
        diagonal20_to9 = (
            c20["chain_id"],
            index,
            c9["chain_id"],
            index + 1,
        )
        diagonal9_to20 = (
            c9["chain_id"],
            index,
            c20["chain_id"],
            index + 1,
        )
        quads.append(
            {
                "correspondence_indices": [index, index + 1],
                "split_diagonal": (
                    "C20_i_TO_C9_j"
                    if diagonal20_to9 < diagonal9_to20
                    else "C9_i_TO_C20_j"
                ),
                "prism_rule": {
                    "transverse_extent": "selected requested empty chord width",
                    "depth_each_side_mm": (
                        "max(abs(C20 signed local normal depth), "
                        "abs(C9 signed local normal depth)) + 1.7"
                    ),
                    "role": "empty collision/removal footprint only",
                },
            }
        )
    record = {
        "pair_id": f"LOCAL_GAP_PAIR_{pair_index:06d}",
        "c20_chain_id": c20["chain_id"],
        "c9_chain_id": c9["chain_id"],
        "correspondence": samples,
        "ruled_quad_prism_definitions": quads,
        "parameter_tuple_count": parameter_tuple_count(),
        "non_crossing": True,
    }
    record["fingerprint"] = stable_hash(record)
    return record


def parameter_tuple_count() -> int:
    result = 1
    for values in PARAMETER_AXES.values():
        result *= len(values)
    return result


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def main() -> None:
    args = arguments()
    blend_path = Path(bpy.data.filepath).resolve()
    aggregate = load_json(AGGREGATE_PATH)
    verified_inputs = dict(aggregate["verified_inputs"])
    verified_inputs.update(
        {
            label: {"path": str(path.relative_to(ROOT)), "sha256": expected}
            for label, (path, expected) in FROZEN_HASHES.items()
        }
    )
    for label, record in sorted(verified_inputs.items()):
        path = ROOT / record["path"]
        actual = sha_file(path)
        if actual != record["sha256"]:
            raise RuntimeError(
                f"{OPERATION}: V27_LOCAL_GAP_INPUT_HASH_MISMATCH; "
                f"input={label}; path={path}; expected={record['sha256']}; "
                f"actual={actual}"
            )
    expected_blend = ROOT / aggregate["verified_inputs"]["input_blend"]["path"]
    if blend_path != expected_blend.resolve():
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend.resolve()}; "
            f"actual={blend_path}"
        )
    obj = bpy.data.objects.get(SOURCE_OBJECT)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: required source mesh object {SOURCE_OBJECT!r} missing"
        )
    mesh = obj.data
    mesh.calc_loop_triangles()

    selected_faces = {
        component: {
            int(face_id)
            for face_id in aggregate["aggregate_mask"]["source_face_ids"][
                component
            ]
        }
        for component in ("C20", "C9")
    }
    immutable_faces = {
        component: {
            int(face_id)
            for face_id in aggregate["aggregate_mask"][
                "immutable_complement_source_face_ids"
            ][component]
        }
        for component in ("C20", "C9")
    }
    face_component = {
        face_id: component
        for component, face_ids in selected_faces.items()
        for face_id in face_ids
    }
    boundary_records = aggregate["aggregate_boundary"]["components"]
    boundary_by_component = {
        component: [
            record
            for record in boundary_records
            if record["component"] == component
        ]
        for component in ("C20", "C9")
    }
    boundary_edge_keys = {
        edge_key(*record["vertex_ids"])
        for record in aggregate["aggregate_boundary"]["edge_records"]
    }
    boundary_vertices = {
        component: {
            int(vertex_id)
            for record in boundary_by_component[component]
            for vertex_id in record["ordered_vertex_ids"][:-1]
        }
        for component in ("C20", "C9")
    }
    boundary_loop_by_vertex = {
        component: {
            int(vertex_id): record["boundary_id"]
            for record in boundary_by_component[component]
            for vertex_id in record["ordered_vertex_ids"][:-1]
        }
        for component in ("C20", "C9")
    }

    edge_index_by_key = {
        edge_key(int(edge.vertices[0]), int(edge.vertices[1])): int(edge.index)
        for edge in mesh.edges
    }
    terminal = load_json(
        ROOT / aggregate["verified_inputs"]["terminal_authority"]["path"]
    )
    terminal_edge_keys = {
        edge_key(left, right)
        for component in ("C20", "C9")
        for side in ("LOWER", "UPPER")
        for left, right in zip(
            terminal["selection"][component][side][
                "ordered_boundary_vertex_ids"
            ],
            terminal["selection"][component][side][
                "ordered_boundary_vertex_ids"
            ][1:],
            strict=False,
        )
    }
    keepout_source_edge_ids = {
        int(source_edge_id)
        for record in aggregate["negative_space_incidences"]
        for source_edge_id in record["shared_source_edge_ids"]
    }
    keepout_intersecting_face_ids = {
        int(face_id)
        for record in aggregate["negative_space_incidences"]
        for face_id in record["intersecting_source_face_ids"]
    }

    incident_faces: dict[tuple[int, int], set[int]] = defaultdict(set)
    selected_incident_faces: dict[int, set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        face_id = int(polygon.index)
        vertex_ids = [int(value) for value in polygon.vertices]
        for left, right in zip(
            vertex_ids, vertex_ids[1:] + vertex_ids[:1], strict=True
        ):
            incident_faces[edge_key(left, right)].add(face_id)
        if face_id in face_component:
            for vertex_id in vertex_ids:
                selected_incident_faces[vertex_id].add(face_id)

    graphs: dict[str, dict[int, tuple[int, ...]]] = {}
    weights: dict[str, dict[tuple[int, int], float]] = {}
    exclusion_counts: dict[str, dict[str, int]] = {}
    for component in ("C20", "C9"):
        adjacency: dict[int, set[int]] = defaultdict(set)
        component_weights: dict[tuple[int, int], float] = {}
        exclusions: dict[str, int] = defaultdict(int)
        candidate_edges = {
            edge_key(left, right)
            for face_id in selected_faces[component]
            for left, right in zip(
                [int(value) for value in mesh.polygons[face_id].vertices],
                [
                    *[int(value) for value in mesh.polygons[face_id].vertices][1:],
                    int(mesh.polygons[face_id].vertices[0]),
                ],
                strict=True,
            )
        }
        for key in sorted(candidate_edges):
            faces = incident_faces[key]
            if key in boundary_edge_keys:
                exclusions["aggregate_boundary_edge"] += 1
                continue
            if key in terminal_edge_keys:
                exclusions["terminal_edge"] += 1
                continue
            if faces & immutable_faces[component]:
                exclusions["immutable_face_incidence"] += 1
                continue
            source_edge_id = edge_index_by_key.get(key)
            if source_edge_id in keepout_source_edge_ids:
                exclusions["negative_space_source_edge"] += 1
                continue
            left, right = key
            adjacency[left].add(right)
            adjacency[right].add(left)
            component_weights[key] = length(
                sub(mesh.vertices[left].co, mesh.vertices[right].co)
            )
        graphs[component] = {
            vertex_id: tuple(sorted(neighbors))
            for vertex_id, neighbors in adjacency.items()
        }
        weights[component] = component_weights
        exclusion_counts[component] = dict(sorted(exclusions.items()))

    terminal_centroids = {
        component: {
            side: centroid(
                [
                    [float(value) for value in point]
                    for point in terminal["selection"][component][side][
                        "exact_source_coordinates_mm"
                    ]
                ]
            )
            for side in ("LOWER", "UPPER")
        }
        for component in ("C20", "C9")
    }
    station_axes = {
        component: normalized(
            sub(
                terminal_centroids[component]["UPPER"],
                terminal_centroids[component]["LOWER"],
            ),
            f"{component} terminal-centroid station axis",
        )
        for component in ("C20", "C9")
    }

    chain_records: dict[str, list[dict[str, Any]]] = {"C20": [], "C9": []}
    endpoint_pair_counts = {"C20": 0, "C9": 0}
    reachable_pair_counts = {"C20": 0, "C9": 0}
    frame_rejection_counts = {"C20": 0, "C9": 0}
    first_frame_rejection: dict[str, str] = {}
    for component in ("C20", "C9"):
        vertices = sorted(boundary_vertices[component])
        paths_seen: set[tuple[int, ...]] = set()
        for start_index, start in enumerate(vertices):
            for goal in vertices[start_index + 1 :]:
                if (
                    boundary_loop_by_vertex[component][start]
                    == boundary_loop_by_vertex[component][goal]
                ):
                    continue
                endpoint_pair_counts[component] += 1
                paths = yen_paths(
                    graphs[component],
                    weights[component],
                    start,
                    goal,
                    boundary_vertices[component],
                )
                if paths:
                    reachable_pair_counts[component] += 1
                for path in paths:
                    start_station = dot(
                        station_axes[component], mesh.vertices[path[0]].co
                    )
                    end_station = dot(
                        station_axes[component], mesh.vertices[path[-1]].co
                    )
                    if (
                        start_station > end_station + TOLERANCE_MM
                        or (
                            abs(start_station - end_station) <= TOLERANCE_MM
                            and path[0] > path[-1]
                        )
                    ):
                        path = tuple(reversed(path))
                    if path in paths_seen:
                        continue
                    paths_seen.add(path)
                    try:
                        frames = path_frames(
                            mesh, path, selected_incident_faces
                        )
                    except FrameDegenerate as error:
                        frame_rejection_counts[component] += 1
                        first_frame_rejection.setdefault(component, str(error))
                        continue
                    normalized_lengths, total_length = cumulative_arclength(
                        [frame["point_mm"] for frame in frames]
                    )
                    record = {
                        "component": component,
                        "ordered_vertex_ids": list(path),
                        "endpoint_boundary_ids": [
                            boundary_loop_by_vertex[component][path[0]],
                            boundary_loop_by_vertex[component][path[-1]],
                        ],
                        "source_edge_ids": [
                            edge_index_by_key[edge_key(left, right)]
                            for left, right in zip(path, path[1:], strict=False)
                        ],
                        "source_edge_length_mm": total_length,
                        "normalized_arclength": normalized_lengths,
                        "frames": frames,
                        "interior_boundary_vertex_ids": sorted(
                            set(path[1:-1]) & boundary_vertices[component]
                        ),
                        "terminal_edge_used": any(
                            edge_key(left, right) in terminal_edge_keys
                            for left, right in zip(path, path[1:], strict=False)
                        ),
                        "immutable_incident_face_ids": sorted(
                            {
                                face_id
                                for left, right in zip(
                                    path, path[1:], strict=False
                                )
                                for face_id in incident_faces[
                                    edge_key(left, right)
                                ]
                                if face_id in immutable_faces[component]
                            }
                        ),
                    }
                    record["chain_id"] = (
                        f"LOCAL_GAP_{component}_CHAIN_"
                        f"{stable_hash(record)[:16].upper()}"
                    )
                    record["fingerprint"] = stable_hash(record)
                    chain_records[component].append(record)
        chain_records[component].sort(
            key=lambda record: (
                record["source_edge_length_mm"],
                record["ordered_vertex_ids"],
            )
        )

    if not chain_records["C20"]:
        raise RuntimeError(
            f"{OPERATION}: V27_LOCAL_GAP_NO_ELIGIBLE_C20_CHAIN; "
            f"eligible_edges={len(weights['C20'])}; "
            f"endpoint_pairs={endpoint_pair_counts['C20']}; "
            f"edge_exclusions={exclusion_counts['C20']}; "
            "action=review exact boundary/interior connectivity"
        )
    if not chain_records["C9"]:
        raise RuntimeError(
            f"{OPERATION}: V27_LOCAL_GAP_NO_ELIGIBLE_C9_CHAIN; "
            f"eligible_edges={len(weights['C9'])}; "
            f"endpoint_pairs={endpoint_pair_counts['C9']}; "
            f"edge_exclusions={exclusion_counts['C9']}; "
            "action=review exact boundary/interior connectivity"
        )

    pair_records = []
    pair_rejection_counts = {"endpoint_order_disagrees": 0, "crossing": 0}
    for c20 in chain_records["C20"]:
        for c9 in chain_records["C9"]:
            c20_direction = (
                c20["endpoint_boundary_ids"][0],
                c20["endpoint_boundary_ids"][1],
            )
            c9_direction = (
                c9["endpoint_boundary_ids"][0],
                c9["endpoint_boundary_ids"][1],
            )
            if c20_direction[0] == c20_direction[1] or c9_direction[0] == c9_direction[1]:
                pair_rejection_counts["endpoint_order_disagrees"] += 1
                continue
            record = pair_record(c20, c9, len(pair_records))
            if record is None:
                pair_rejection_counts["crossing"] += 1
                continue
            pair_records.append(record)
    if not pair_records:
        raise RuntimeError(f"{OPERATION}: V27_LOCAL_GAP_NO_ORDERED_CHAIN_PAIR")

    parameter_count = parameter_tuple_count()
    parameter_grid = {
        "axes": PARAMETER_AXES,
        "tuple_count_per_chain_pair": parameter_count,
        "factorized": True,
        "complete_cartesian_product": True,
        "endpoint_taper": (
            "piecewise linear; exactly zero at normalized arclength 0 and 1; "
            "full grid value throughout middle 50 percent"
        ),
        "stale_handoff_count_correction": {
            "prior_count": 5040,
            "correct_count": parameter_count,
            "reason": (
                "the authored exact signed-depth axes each contain nine values; "
                "4*7*9*9*5 = 11340"
            ),
        },
    }
    family_descriptor = {
        "chains": chain_records,
        "ordered_chain_pairs": pair_records,
        "parameter_grid": parameter_grid,
        "member_count": len(pair_records) * parameter_count,
    }
    family_fingerprint = stable_hash(family_descriptor)
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": RESULT,
        "scope": (
            "read-only V27 Stage 2b family enumeration; no member evaluation, "
            "candidate geometry, mutation, image work, Blend save, Gate B/D, "
            "or promotion"
        ),
        "code_sha256": sha_file(Path(__file__).resolve()),
        "verified_inputs": verified_inputs,
        "source_scene": {
            "blend": str(blend_path),
            "object": SOURCE_OBJECT,
            "mesh": mesh.name,
            "vertex_count": len(mesh.vertices),
            "polygon_count": len(mesh.polygons),
        },
        "aggregate_contract": {
            "selected_cell_ids": aggregate["aggregate_mask"]["selected_cell_ids"],
            "selected_face_counts": aggregate["aggregate_mask"]["source_face_count"],
            "ordered_boundary_loop_counts": {
                component: len(boundary_by_component[component])
                for component in ("C20", "C9")
            },
            "terminal_chain_ids": sorted(
                record["terminal_id"]
                for record in aggregate["terminal_incidences"]
            ),
            "no_floor_sample_count": aggregate["no_floor_exclusion"]["sample_count"],
        },
        "topology_graph": {
            "endpoint_pair_counts": endpoint_pair_counts,
            "reachable_endpoint_pair_counts": reachable_pair_counts,
            "eligible_edge_counts": {
                component: len(weights[component])
                for component in ("C20", "C9")
            },
            "edge_exclusion_counts": exclusion_counts,
            "frame_rejection_counts": frame_rejection_counts,
            "first_frame_rejection": first_frame_rejection,
            "negative_space_source_edge_ids_excluded": sorted(
                keepout_source_edge_ids
            ),
            "negative_space_intersecting_face_ids_reserved_for_exact_prism_evaluation": (
                sorted(keepout_intersecting_face_ids)
            ),
        },
        "finite_family": {
            **family_descriptor,
            "fingerprint": family_fingerprint,
            "enumerated_before_evaluation": True,
        },
        "pair_rejection_counts": pair_rejection_counts,
        "invariants": {
            "frozen_hashes_match": True,
            "aggregate_cell_count_is_26": (
                aggregate["aggregate_mask"]["cell_count"] == 26
            ),
            "aggregate_face_count_is_266": (
                sum(aggregate["aggregate_mask"]["source_face_count"].values())
                == 266
            ),
            "all_chain_interiors_exclude_boundary_vertices": all(
                not record["interior_boundary_vertex_ids"]
                for records in chain_records.values()
                for record in records
            ),
            "no_terminal_edge_used": all(
                not record["terminal_edge_used"]
                for records in chain_records.values()
                for record in records
            ),
            "no_immutable_face_incidence": all(
                not record["immutable_incident_face_ids"]
                for records in chain_records.values()
                for record in records
            ),
            "no_floor_used_as_geometry_or_seed": True,
            "family_enumerated_before_evaluation": True,
            "family_fingerprint_recorded": True,
            "no_candidate_geometry_emitted": True,
        },
        "safety": {
            "evaluation_started": False,
            "mutation_started": False,
            "candidate_surface_geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
            "gate_b_run": False,
            "gate_d_run": False,
        },
    }
    if not all(result["invariants"].values()):
        failed = [
            name for name, passed in result["invariants"].items() if not passed
        ]
        raise RuntimeError(
            f"{OPERATION}: V27_LOCAL_GAP_FAMILY_NOT_PREENUMERATED; "
            f"failed_invariants={failed}"
        )
    result["semantic_fingerprint"] = stable_hash(result)
    atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": RESULT,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "family_fingerprint": family_fingerprint,
        "chain_counts": {
            component: len(chain_records[component])
            for component in ("C20", "C9")
        },
        "ordered_chain_pair_count": len(pair_records),
        "parameter_tuple_count_per_pair": parameter_count,
        "family_member_count": len(pair_records) * parameter_count,
        "evaluation_started": False,
        "safety": result["safety"],
    }
    atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
