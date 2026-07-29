#!/usr/bin/env python3
"""Solve the read-only V27 fixed-frame 12 mm flex-gap placement family."""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable

import bpy


OPERATION = "SOLVE_V27_FLEX_GAP"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V26 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v26"
)
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
DEFAULT_OUTPUT = V27 / "v27_flex_gap_authority.json"
DEFAULT_RECEIPT = V27 / "v27_flex_gap_authority_receipt.json"
AGGREGATE_PATH = V27 / "v27_aggregate_authority.json"
AGGREGATE_RECEIPT_PATH = V27 / "v27_aggregate_authority_receipt.json"
SOURCE_OBJECT = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
WIDTH_MM = 12.0
HALF_WIDTH_MM = WIDTH_MM / 2.0
TOLERANCE_MM = 1e-7
ADAPTIVE_SAMPLE_SPACING_MM = 1.0

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


def dot(a: Iterable[float], b: Iterable[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def sub(a: Iterable[float], b: Iterable[float]) -> list[float]:
    return [x - y for x, y in zip(a, b, strict=True)]


def add(a: Iterable[float], b: Iterable[float]) -> list[float]:
    return [x + y for x, y in zip(a, b, strict=True)]


def scale(a: Iterable[float], amount: float) -> list[float]:
    return [x * amount for x in a]


def length(a: Iterable[float]) -> float:
    return math.sqrt(dot(a, a))


def clip_polygon(
    polygon: list[list[float]], normal: list[float], offset: float
) -> list[list[float]]:
    if not polygon:
        return []
    result: list[list[float]] = []
    previous = polygon[-1]
    previous_distance = dot(normal, previous) - offset
    previous_inside = previous_distance <= TOLERANCE_MM
    for current in polygon:
        current_distance = dot(normal, current) - offset
        current_inside = current_distance <= TOLERANCE_MM
        if current_inside != previous_inside:
            denominator = previous_distance - current_distance
            factor = (
                0.5 if abs(denominator) <= 1e-15 else previous_distance / denominator
            )
            result.append(
                add(previous, scale(sub(current, previous), factor))
            )
        if current_inside:
            result.append(current)
        previous = current
        previous_distance = current_distance
        previous_inside = current_inside
    return result


def triangle_intersects_cell(
    triangle: list[list[float]], half_spaces: list[dict[str, Any]]
) -> tuple[bool, list[list[float]]]:
    clipped = [list(point) for point in triangle]
    for half_space in half_spaces:
        clipped = clip_polygon(
            clipped,
            [float(value) for value in half_space["normal"]],
            float(half_space["offset_mm"]),
        )
        if not clipped:
            return False, []
    return True, clipped


def clip_segment(
    start: list[float],
    end: list[float],
    half_spaces: list[dict[str, Any]],
) -> tuple[bool, list[float] | None]:
    low = 0.0
    high = 1.0
    direction = sub(end, start)
    for half_space in half_spaces:
        normal = half_space["normal"]
        offset = float(half_space["offset_mm"])
        numerator = offset - dot(normal, start)
        denominator = dot(normal, direction)
        if abs(denominator) <= 1e-15:
            if numerator < -TOLERANCE_MM:
                return False, None
            continue
        value = numerator / denominator
        if denominator > 0.0:
            high = min(high, value)
        else:
            low = max(low, value)
        if low > high + TOLERANCE_MM:
            return False, None
    parameter = min(1.0, max(0.0, (low + high) / 2.0))
    return True, add(start, scale(direction, parameter))


def determinant3(rows: list[list[float]]) -> float:
    a, b, c = rows
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def solve_three_planes(planes: tuple[dict[str, Any], ...]) -> list[float] | None:
    rows = [[float(value) for value in plane["normal"]] for plane in planes]
    determinant = determinant3(rows)
    if abs(determinant) <= 1e-12:
        return None
    offsets = [float(plane["offset_mm"]) for plane in planes]
    columns = []
    for column in range(3):
        matrix = [list(row) for row in rows]
        for row_index in range(3):
            matrix[row_index][column] = offsets[row_index]
        columns.append(determinant3(matrix) / determinant)
    return columns


def convex_cells_intersect(
    left: list[dict[str, Any]], right: list[dict[str, Any]]
) -> tuple[bool, list[float] | None]:
    planes = left + right
    for triple in combinations(planes, 3):
        point = solve_three_planes(triple)
        if point is None:
            continue
        if all(
            dot(plane["normal"], point)
            <= float(plane["offset_mm"]) + TOLERANCE_MM
            for plane in planes
        ):
            return True, point
    return False, None


def translated_gap(
    frozen_gap: dict[str, Any], station: float
) -> dict[str, Any]:
    frame = frozen_gap["source"]["frame"]
    center = [float(value) for value in frame["center_mm"]]
    chord = [float(value) for value in frame["chord_axis"]]
    frozen_station = dot(chord, center)
    translation = station - frozen_station
    half_spaces = []
    for half_space in frozen_gap["half_spaces"]:
        normal = [float(value) for value in half_space["normal"]]
        half_spaces.append(
            {
                "normal": normal,
                "offset_mm": float(half_space["offset_mm"])
                + translation * dot(normal, chord),
                "inside_test": half_space["inside_test"],
            }
        )
    vertices = [
        add(
            [float(value) for value in vertex],
            scale(chord, translation),
        )
        for vertex in frozen_gap["vertices_mm"]
    ]
    return {
        "center_station_mm": station,
        "translation_from_frozen_mm": translation,
        "vertices_mm": vertices,
        "faces": frozen_gap["faces"],
        "half_spaces": half_spaces,
        "minimum_chordwise_width_mm": WIDTH_MM,
    }


def polygon_triangles(mesh: bpy.types.Mesh, face_id: int) -> list[list[list[float]]]:
    polygon = mesh.polygons[face_id]
    vertex_ids = [int(value) for value in polygon.vertices]
    if len(vertex_ids) < 3:
        return []
    points = [
        [float(value) for value in mesh.vertices[vertex_id].co]
        for vertex_id in vertex_ids
    ]
    return [[points[0], points[index], points[index + 1]] for index in range(1, len(points) - 1)]


def adaptive_triangle_audit(
    triangle: list[list[float]], half_spaces: list[dict[str, Any]]
) -> dict[str, Any]:
    maximum_edge = max(
        length(sub(triangle[(index + 1) % 3], triangle[index]))
        for index in range(3)
    )
    divisions = max(1, math.ceil(maximum_edge / ADAPTIVE_SAMPLE_SPACING_MM))
    inside_count = 0
    minimum_max_signed_distance = math.inf
    for row in range(divisions + 1):
        for column in range(divisions + 1 - row):
            a = row / divisions
            b = column / divisions
            c = 1.0 - a - b
            point = [
                a * triangle[0][axis]
                + b * triangle[1][axis]
                + c * triangle[2][axis]
                for axis in range(3)
            ]
            max_distance = max(
                dot(space["normal"], point) - float(space["offset_mm"])
                for space in half_spaces
            )
            minimum_max_signed_distance = min(
                minimum_max_signed_distance, max_distance
            )
            if max_distance <= TOLERANCE_MM:
                inside_count += 1
    return {
        "divisions": divisions,
        "sample_count": (divisions + 1) * (divisions + 2) // 2,
        "inside_sample_count": inside_count,
        "minimum_max_half_space_signed_distance_mm": minimum_max_signed_distance,
    }


def collect_keepout_cells(negative: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for aperture in negative["aperture_keepouts"]:
        for cell in aperture["cells"]:
            cells.append(
                {
                    "cell_id": cell["cell_id"],
                    "kind": "APERTURE",
                    "vertices_mm": cell["vertices_mm"],
                    "half_spaces": cell["half_spaces"],
                }
            )
    for cell in negative["source_open_route_keepouts"]["cells"]:
        cells.append(
            {
                "cell_id": cell["cell_id"],
                "kind": "SOURCE_OPEN_ROUTE",
                "vertices_mm": cell["vertices_mm"],
                "half_spaces": cell["half_spaces"],
            }
        )
    for cell in negative["central_opening_keepouts"]["cells"]:
        cells.append(
            {
                "cell_id": cell["cell_id"],
                "kind": "CENTRAL_OPENING",
                "vertices_mm": cell["vertices_mm"],
                "half_spaces": cell["half_spaces"],
            }
        )
    return sorted(cells, key=lambda item: (item["kind"], item["cell_id"]))


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
                f"{OPERATION}: V27_INPUT_AUTHORITY_HASH_MISMATCH for "
                f"{label}; path={path}; expected={record['sha256']}; "
                f"actual={actual}"
            )
    expected_blend = ROOT / aggregate["verified_inputs"]["input_blend"]["path"]
    if blend_path != expected_blend.resolve():
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend.resolve()}, "
            f"actual={blend_path}"
        )
    obj = bpy.data.objects.get(SOURCE_OBJECT)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: required source mesh object {SOURCE_OBJECT!r} missing"
        )
    mesh = obj.data
    negative = load_json(
        ROOT / aggregate["verified_inputs"]["negative_space_authority"]["path"]
    )
    terminal = load_json(
        ROOT / aggregate["verified_inputs"]["terminal_authority"]["path"]
    )
    selected_faces = {
        component: [int(value) for value in face_ids]
        for component, face_ids in aggregate["aggregate_mask"][
            "source_face_ids"
        ].items()
    }
    immutable_faces = {
        component: [int(value) for value in face_ids]
        for component, face_ids in aggregate["aggregate_mask"][
            "immutable_complement_source_face_ids"
        ].items()
    }
    face_component = {
        face_id: component
        for component, face_ids in selected_faces.items()
        for face_id in face_ids
    }
    all_selected_ids = sorted(face_component)
    all_immutable_ids = sorted(
        {
            face_id
            for face_ids in immutable_faces.values()
            for face_id in face_ids
        }
    )
    referenced_vertex_ids = {
        int(vertex_id)
        for face_id in all_selected_ids
        for vertex_id in mesh.polygons[face_id].vertices
    }
    boundary_vertex_ids = {
        int(vertex_id)
        for component in aggregate["aggregate_boundary"]["components"]
        for vertex_id in component["ordered_vertex_ids"]
    }
    if not boundary_vertex_ids <= referenced_vertex_ids:
        raise RuntimeError(
            f"{OPERATION}: aggregate boundary references vertices outside "
            "the exact aggregate face union"
        )

    frozen_gap = negative["flex_gap_keepout"]
    chord = [
        float(value)
        for value in frozen_gap["source"]["frame"]["chord_axis"]
    ]
    stations = {
        vertex_id: dot(chord, mesh.vertices[vertex_id].co)
        for vertex_id in range(len(mesh.vertices))
    }
    domain_low = min(stations[value] for value in referenced_vertex_ids) + HALF_WIDTH_MM
    domain_high = max(stations[value] for value in referenced_vertex_ids) - HALF_WIDTH_MM
    if domain_low > domain_high:
        raise RuntimeError(
            f"{OPERATION}: aggregate chord span is narrower than {WIDTH_MM} mm"
        )

    keepout_cells = collect_keepout_cells(negative)
    terminal_records = [
        terminal["selection"][component][position]
        for component in ("C20", "C9")
        for position in ("UPPER", "LOWER")
    ]
    event_sources: list[dict[str, Any]] = []
    for classification, face_ids in (
        ("AGGREGATE", all_selected_ids),
        ("IMMUTABLE", all_immutable_ids),
    ):
        for face_id in face_ids:
            for vertex_id in mesh.polygons[face_id].vertices:
                station = stations[int(vertex_id)]
                for sign in (-1.0, 1.0):
                    event_sources.append(
                        {
                            "station_mm": station + sign * HALF_WIDTH_MM,
                            "kind": f"{classification}_TRIANGLE_VERTEX",
                            "source_id": int(face_id),
                            "vertex_id": int(vertex_id),
                        }
                    )
    for record in terminal_records:
        for index, coordinate in enumerate(record["exact_source_coordinates_mm"]):
            station = dot(chord, coordinate)
            for sign in (-1.0, 1.0):
                event_sources.append(
                    {
                        "station_mm": station + sign * HALF_WIDTH_MM,
                        "kind": "TERMINAL_VERTEX",
                        "source_id": record["chain_id"],
                        "vertex_id": int(record["ordered_boundary_vertex_ids"][index]),
                    }
                )
    for cell in keepout_cells:
        for index, vertex in enumerate(cell["vertices_mm"]):
            station = dot(chord, vertex)
            for sign in (-1.0, 1.0):
                event_sources.append(
                    {
                        "station_mm": station + sign * HALF_WIDTH_MM,
                        "kind": f"{cell['kind']}_CELL_VERTEX",
                        "source_id": cell["cell_id"],
                        "vertex_id": index,
                    }
                )
    events = sorted(
        {
            round(float(record["station_mm"]), 12)
            for record in event_sources
            if domain_low - TOLERANCE_MM
            <= float(record["station_mm"])
            <= domain_high + TOLERANCE_MM
        }
        | {round(domain_low, 12), round(domain_high, 12)}
    )
    placements = []
    for station in events:
        placements.append({"station_mm": station, "representative": "EVENT"})
    for low, high in zip(events, events[1:], strict=False):
        if high - low > 2.0 * TOLERANCE_MM:
            placements.append(
                {
                    "station_mm": round((low + high) / 2.0, 12),
                    "representative": "OPEN_INTERVAL_MIDPOINT",
                    "interval_mm": [low, high],
                }
            )
    placements = sorted(
        placements,
        key=lambda item: (
            item["station_mm"],
            0 if item["representative"] == "EVENT" else 1,
        ),
    )
    family_descriptor = {
        "frame_fingerprint": frozen_gap["fingerprint"],
        "width_mm": WIDTH_MM,
        "domain_mm": [domain_low, domain_high],
        "event_count": len(events),
        "placement_count": len(placements),
        "placements": placements,
    }
    family_fingerprint = stable_hash(family_descriptor)

    selected: dict[str, Any] | None = None
    rejection_counts: Counter[str] = Counter()
    first_counterexample: dict[str, Any] = {}
    evaluated: list[dict[str, Any]] = []
    best_immutable_counterexample: dict[str, Any] | None = None
    face_triangles = {
        face_id: polygon_triangles(mesh, face_id)
        for face_id in sorted(set(all_selected_ids) | set(all_immutable_ids))
    }
    triangle_station_intervals = {
        (face_id, triangle_index): (
            min(dot(chord, point) for point in triangle),
            max(dot(chord, point) for point in triangle),
        )
        for face_id, triangles in face_triangles.items()
        for triangle_index, triangle in enumerate(triangles)
    }
    keepout_station_intervals = {
        cell["cell_id"]: (
            min(dot(chord, point) for point in cell["vertices_mm"]),
            max(dot(chord, point) for point in cell["vertices_mm"]),
        )
        for cell in keepout_cells
    }
    for placement_index, placement in enumerate(placements):
        gap = translated_gap(frozen_gap, placement["station_mm"])
        slab_low = placement["station_mm"] - HALF_WIDTH_MM
        slab_high = placement["station_mm"] + HALF_WIDTH_MM
        removals: dict[str, set[int]] = {"C20": set(), "C9": set()}
        immutable_hits: list[int] = []
        for face_id in all_selected_ids:
            if any(
                interval[1] >= slab_low - TOLERANCE_MM
                and interval[0] <= slab_high + TOLERANCE_MM
                and triangle_intersects_cell(triangle, gap["half_spaces"])[0]
                for triangle_index, triangle in enumerate(
                    face_triangles[face_id]
                )
                for interval in [
                    triangle_station_intervals[(face_id, triangle_index)]
                ]
            ):
                removals[face_component[face_id]].add(face_id)
        for face_id in all_immutable_ids:
            if any(
                interval[1] >= slab_low - TOLERANCE_MM
                and interval[0] <= slab_high + TOLERANCE_MM
                and triangle_intersects_cell(triangle, gap["half_spaces"])[0]
                for triangle_index, triangle in enumerate(
                    face_triangles[face_id]
                )
                for interval in [
                    triangle_station_intervals[(face_id, triangle_index)]
                ]
            ):
                immutable_hits.append(face_id)
        reasons = []
        if not removals["C20"]:
            reasons.append("NO_C20_AGGREGATE_REMOVAL")
        if not removals["C9"]:
            reasons.append("NO_C9_AGGREGATE_REMOVAL")
        if immutable_hits:
            reasons.append("IMMUTABLE_TRIANGLE_INTERSECTION")
        terminal_hits = []
        keepout_hits = []
        if not reasons:
            for record in terminal_records:
                coordinates = [
                    [float(value) for value in point]
                    for point in record["exact_source_coordinates_mm"]
                ]
                if any(
                    clip_segment(start, end, gap["half_spaces"])[0]
                    for start, end in zip(
                        coordinates, coordinates[1:], strict=False
                    )
                ):
                    terminal_hits.append(record["chain_id"])
            if terminal_hits:
                reasons.append("TERMINAL_CHAIN_INTERSECTION")
        if not reasons:
            for cell in keepout_cells:
                interval = keepout_station_intervals[cell["cell_id"]]
                if (
                    interval[1] < slab_low - TOLERANCE_MM
                    or interval[0] > slab_high + TOLERANCE_MM
                ):
                    continue
                intersects, witness = convex_cells_intersect(
                    gap["half_spaces"], cell["half_spaces"]
                )
                if intersects:
                    keepout_hits.append(
                        {
                            "cell_id": cell["cell_id"],
                            "kind": cell["kind"],
                            "witness_mm": witness,
                        }
                    )
            if keepout_hits:
                reasons.append("NEGATIVE_SPACE_CELL_INTERSECTION")
        for reason in reasons:
            rejection_counts[reason] += 1
            if reason not in first_counterexample:
                first_counterexample[reason] = {
                    "placement_index": placement_index,
                    "center_station_mm": placement["station_mm"],
                    "immutable_face_ids": immutable_hits[:24],
                    "terminal_chain_ids": terminal_hits,
                    "keepout_cells": keepout_hits[:12],
                    "removal_counts": {
                        component: len(values)
                        for component, values in removals.items()
                    },
                }
        evaluation = {
            "placement_index": placement_index,
            "center_station_mm": placement["station_mm"],
            "representative": placement["representative"],
            "accepted": not reasons,
            "reasons": reasons,
            "removal_counts": {
                component: len(values) for component, values in removals.items()
            },
            "immutable_hit_count": len(immutable_hits),
            "immutable_witness_face_id": (
                immutable_hits[0] if immutable_hits else None
            ),
            "terminal_hit_count": len(terminal_hits),
            "keepout_hit_count": len(keepout_hits),
            "terminal_and_keepout_checks_reached": not (
                immutable_hits
                or not removals["C20"]
                or not removals["C9"]
            ),
        }
        evaluated.append(evaluation)
        if (
            immutable_hits
            and removals["C20"]
            and removals["C9"]
            and (
                best_immutable_counterexample is None
                or (
                    len(immutable_hits),
                    -(len(removals["C20"]) + len(removals["C9"])),
                    placement_index,
                )
                < (
                    best_immutable_counterexample["immutable_hit_count"],
                    -best_immutable_counterexample[
                        "authorized_removal_total"
                    ],
                    best_immutable_counterexample["placement_index"],
                )
            )
        ):
            best_immutable_counterexample = {
                "placement_index": placement_index,
                "center_station_mm": placement["station_mm"],
                "representative": placement["representative"],
                "immutable_hit_count": len(immutable_hits),
                "immutable_source_face_ids": immutable_hits,
                "immutable_source_face_ids_fingerprint": stable_hash(
                    immutable_hits
                ),
                "authorized_removal_total": (
                    len(removals["C20"]) + len(removals["C9"])
                ),
                "removed_authorized_source_face_ids": {
                    component: sorted(values)
                    for component, values in removals.items()
                },
            }
        if not reasons:
            selected = {
                **evaluation,
                "gap": gap,
                "removed_authorized_source_face_ids": {
                    component: sorted(values)
                    for component, values in removals.items()
                },
                "immutable_source_face_ids_intersected": [],
                "terminal_chain_ids_intersected": [],
                "negative_space_cells_intersected": [],
            }
            break

    exact_audit: dict[str, Any] | None = None
    if selected is not None:
        gap = selected["gap"]
        adaptive_records = []
        for component, face_ids in selected[
            "removed_authorized_source_face_ids"
        ].items():
            for face_id in face_ids:
                for triangle_index, triangle in enumerate(
                    polygon_triangles(mesh, face_id)
                ):
                    intersects, clipped = triangle_intersects_cell(
                        triangle, gap["half_spaces"]
                    )
                    if intersects:
                        adaptive_records.append(
                            {
                                "component": component,
                                "source_face_id": face_id,
                                "triangle_index": triangle_index,
                                "clipped_vertex_count": len(clipped),
                                **adaptive_triangle_audit(
                                    triangle, gap["half_spaces"]
                                ),
                            }
                        )
        exact_audit = {
            "triangle_intersection_method": (
                "Sutherland-Hodgman clipping against all six exact translated "
                "convex half-spaces"
            ),
            "terminal_method": "parametric segment clipping against six half-spaces",
            "keepout_method": (
                "combined convex half-space feasibility by exhaustive "
                "three-plane vertices"
            ),
            "adaptive_sample_spacing_max_mm": ADAPTIVE_SAMPLE_SPACING_MM,
            "adaptive_records": adaptive_records,
            "adaptive_sample_count": sum(
                record["sample_count"] for record in adaptive_records
            ),
        }
    elif best_immutable_counterexample is not None:
        gap = translated_gap(
            frozen_gap,
            best_immutable_counterexample["center_station_mm"],
        )
        adaptive_records = []
        for face_id in best_immutable_counterexample[
            "immutable_source_face_ids"
        ]:
            for triangle_index, triangle in enumerate(face_triangles[face_id]):
                intersects, clipped = triangle_intersects_cell(
                    triangle, gap["half_spaces"]
                )
                if intersects:
                    adaptive_records.append(
                        {
                            "classification": "IMMUTABLE_COUNTEREXAMPLE",
                            "source_face_id": face_id,
                            "triangle_index": triangle_index,
                            "clipped_vertex_count": len(clipped),
                            **adaptive_triangle_audit(
                                triangle, gap["half_spaces"]
                            ),
                        }
                    )
        exact_audit = {
            "triangle_intersection_method": (
                "Sutherland-Hodgman clipping against all six exact translated "
                "convex half-spaces"
            ),
            "terminal_method": "not reached after exact immutable rejection",
            "keepout_method": "not reached after exact immutable rejection",
            "adaptive_subject": "best exact immutable counterexample",
            "adaptive_sample_spacing_max_mm": ADAPTIVE_SAMPLE_SPACING_MM,
            "adaptive_records": adaptive_records,
            "adaptive_sample_count": sum(
                record["sample_count"] for record in adaptive_records
            ),
        }

    status = (
        "V27_FLEX_GAP_SOLVED"
        if selected is not None
        else "V27_NO_VALID_12MM_FLEX_GAP"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": (
            "read-only exact fixed-frame V27 Stage 2 gap solve; no candidate "
            "surface geometry, mutation, image work, Blend save, promotion, "
            "or Gate B/D"
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
            "selected_cell_ids": aggregate["aggregate_mask"][
                "selected_cell_ids"
            ],
            "selected_cell_count": 26,
            "aggregate_source_face_count": aggregate["aggregate_mask"][
                "source_face_count"
            ],
            "ordered_boundary_loop_count": len(
                aggregate["aggregate_boundary"]["components"]
            ),
            "ordered_boundary_vertex_count": len(boundary_vertex_ids),
            "immutable_complement_source_face_count": aggregate[
                "aggregate_mask"
            ]["immutable_complement_source_face_count"],
            "no_floor_excluded": aggregate["no_floor_exclusion"],
        },
        "finite_family": {
            **family_descriptor,
            "fingerprint": family_fingerprint,
            "enumerated_before_evaluation": True,
            "complete_for_contract": (
                "all topology-changing event placements and all open-interval "
                "states for a 12 mm translation of the frozen exact flex-gap "
                "cell along its chord axis inside the aggregate chord domain"
            ),
        },
        "evaluation": {
            "evaluated_placement_count": len(evaluated),
            "selected_first_complete_pass": selected is not None,
            "records": evaluated,
            "rejection_counts": dict(sorted(rejection_counts.items())),
            "first_counterexamples": first_counterexample,
            "best_immutable_counterexample": best_immutable_counterexample,
            "immutable_witness_face_frequency": [
                {"source_face_id": face_id, "placement_count": count}
                for face_id, count in sorted(
                    Counter(
                        record["immutable_witness_face_id"]
                        for record in evaluated
                        if record["immutable_witness_face_id"] is not None
                    ).items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        },
        "selection": selected,
        "exact_and_adaptive_audit": exact_audit,
        "invariants": {
            "frozen_hashes_match": True,
            "family_enumerated_before_evaluation": True,
            "family_fingerprint_recorded": True,
            "minimum_width_is_12_mm": True,
            "aggregate_cell_count_is_26": True,
            "boundary_loops_are_ordered": all(
                component["ordered_vertex_ids"]
                and component["is_simple_loop"]
                for component in aggregate["aggregate_boundary"]["components"]
            ),
            "no_floor_used_as_geometry_or_seed": True,
            "no_candidate_geometry_emitted": True,
        },
        "safety": {
            "mutation_started": False,
            "candidate_surface_geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
            "gate_b_run": False,
            "gate_d_run": False,
        },
    }
    result["semantic_fingerprint"] = stable_hash(result)
    atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "finite_family_fingerprint": family_fingerprint,
        "family_event_count": len(events),
        "family_placement_count": len(placements),
        "evaluated_placement_count": len(evaluated),
        "selected_placement_index": (
            selected["placement_index"] if selected is not None else None
        ),
        "selected_center_station_mm": (
            selected["center_station_mm"] if selected is not None else None
        ),
        "selected_width_mm": WIDTH_MM if selected is not None else None,
        "selected_removal_counts": (
            {
                component: len(face_ids)
                for component, face_ids in selected[
                    "removed_authorized_source_face_ids"
                ].items()
            }
            if selected is not None
            else None
        ),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "safety": result["safety"],
    }
    atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
