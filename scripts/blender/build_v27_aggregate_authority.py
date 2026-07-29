#!/usr/bin/env python3
"""Build the read-only V27 aggregate reconstruction-mask authority.

The builder consumes only frozen V26 JSON authorities and their identified
source Blend. It emits no geometry, opens no Blend, and performs no mutation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


OPERATION = "BUILD_V27_AGGREGATE_AUTHORITY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
RESULT = "V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED"
ROOT = Path(__file__).resolve().parents[2]
V26 = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
V27 = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v27"
)
OUTPUT = V27 / "v27_aggregate_authority.json"
RECEIPT = V27 / "v27_aggregate_authority_receipt.json"
MAXIMUM_BATCH_CELL_COUNT = 12
INTERSECTION_TOLERANCE_MM = 1e-7

FROZEN_INPUTS = {
    "exposure_cell_authority": (
        V26 / "v26_exposure_cell_authority.json",
        "bba29d185676ed6dadaa77c81b37ae8d05f149886a3151887b2804c88bc9b0a5",
    ),
    "terminal_authority": (
        V26 / "v26_terminal_authority.json",
        "159cbf3a3ddacf0a6628d7f4d2f5bf5a69161727176095871ef3899e7d807c1d",
    ),
    "cutter_authority": (
        V26 / "v26_cutter_authority.json",
        "52baafbc473c0e85952b80c4db56bb5620310fb82aa7b23bd55f529e83b78d45",
    ),
    "negative_space_authority": (
        V26 / "v26_negative_space_authority.json",
        "4ba0184076e0f635fc64eaa82da59993dfa4b75b8c8edd82efa5139db0f8f2bd",
    ),
    "floor_ownership_authority": (
        V26 / "v26_floor_ownership_authority.json",
        "02b758bddee0be121c9c1e93cef13b781b4e8241bda862ec6c8d389aaf653ab9",
    ),
    "floor_ownership_summary": (
        V26 / "v26_floor_ownership_summary.json",
        "2a054e9290869a6b647b4da1fa52f98e6537c8bca2a3b12546374ff788c982a9",
    ),
    "cell_authority": (
        V26 / "v26_cell_authority.json",
        "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca",
    ),
    "joint_authority": (
        V26 / "v26_joint_authority.json",
        "e4a01b2d0e0f5d7997983d43af90cf2f2cd2bec81c859645b7e6961b8a55bbef",
    ),
}

SELECTED_CELL_IDS = [
    "EXPOSURE_CELL_C20_000",
    "EXPOSURE_CELL_C20_002",
    "EXPOSURE_CELL_C20_003",
    "EXPOSURE_CELL_C20_004",
    "EXPOSURE_CELL_C20_005",
    "EXPOSURE_CELL_C20_006",
    "EXPOSURE_CELL_C20_008",
    "EXPOSURE_CELL_C20_010",
    "EXPOSURE_CELL_C20_012",
    "EXPOSURE_CELL_C20_013",
    "EXPOSURE_CELL_C20_017",
    "EXPOSURE_CELL_C20_018",
    "EXPOSURE_CELL_C20_020",
    "EXPOSURE_CELL_C20_021",
    "EXPOSURE_CELL_C20_022",
    "EXPOSURE_CELL_C20_023",
    "EXPOSURE_CELL_C20_028",
    "EXPOSURE_CELL_C20_029",
    "EXPOSURE_CELL_C9_000",
    "EXPOSURE_CELL_C9_001",
    "EXPOSURE_CELL_C9_002",
    "EXPOSURE_CELL_C9_003",
    "EXPOSURE_CELL_C9_004",
]

TERMINAL_IDS = {
    ("C20", "UPPER"): "C20_CHAIN_17929_5618",
    ("C20", "LOWER"): "C20_CHAIN_3151_8123",
    ("C9", "UPPER"): "C9_CHAIN_2821_2823",
    ("C9", "LOWER"): "C9_CHAIN_15240_5360",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise RuntimeError(
            f"{OPERATION}: cannot hash frozen input {path}: {error}"
        ) from error
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{OPERATION}: cannot read {label} at {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeError(
            f"{OPERATION}: {label} at {path} is {type(value).__name__}, "
            "expected a JSON object"
        )
    return value


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
    ).encode("utf-8") + b"\n"
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


def dot(first: list[float], second: list[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(first, second, strict=True))


def clip_polygon_to_half_space(
    polygon: list[list[float]],
    normal: list[float],
    offset: float,
) -> list[list[float]]:
    if not polygon:
        return []
    result: list[list[float]] = []
    previous = polygon[-1]
    previous_distance = dot(normal, previous) - offset
    previous_inside = previous_distance <= INTERSECTION_TOLERANCE_MM
    for current in polygon:
        current_distance = dot(normal, current) - offset
        current_inside = current_distance <= INTERSECTION_TOLERANCE_MM
        if current_inside != previous_inside:
            denominator = previous_distance - current_distance
            if abs(denominator) > 1e-15:
                fraction = previous_distance / denominator
                result.append(
                    [
                        previous[index]
                        + fraction * (current[index] - previous[index])
                        for index in range(3)
                    ]
                )
        if current_inside:
            result.append(current)
        previous = current
        previous_distance = current_distance
        previous_inside = current_inside
    return result


def triangle_intersects_convex_cell(
    triangle: list[list[float]], half_spaces: list[dict[str, Any]]
) -> bool:
    polygon = triangle
    for half_space in half_spaces:
        polygon = clip_polygon_to_half_space(
            polygon,
            [float(value) for value in half_space["normal"]],
            float(half_space["offset_mm"]),
        )
        if not polygon:
            return False
    return True


def cell_sort_key(cell_id: str) -> tuple[str, int]:
    component = "C20" if "_C20_" in cell_id else "C9"
    return component, int(cell_id.rsplit("_", 1)[1])


def build_boundary_components(
    component: str, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    edge_records = {
        tuple(record["vertex_ids"]): record for record in records
    }
    vertex_to_edges: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for edge in edge_records:
        vertex_to_edges[edge[0]].add(edge)
        vertex_to_edges[edge[1]].add(edge)
    unvisited = set(edge_records)
    components = []
    while unvisited:
        seed = min(unvisited)
        pending = [seed]
        selected_edges = set()
        while pending:
            edge = pending.pop()
            if edge not in unvisited:
                continue
            unvisited.remove(edge)
            selected_edges.add(edge)
            for vertex in edge:
                pending.extend(sorted(vertex_to_edges[vertex] & unvisited))
        vertices = sorted({vertex for edge in selected_edges for vertex in edge})
        degrees = {
            vertex: sum(vertex in edge for edge in selected_edges)
            for vertex in vertices
        }
        ordered_vertices: list[int] = []
        simple_loop = bool(vertices) and all(degree == 2 for degree in degrees.values())
        simple_path = (
            bool(vertices)
            and list(degrees.values()).count(1) == 2
            and all(degree in {1, 2} for degree in degrees.values())
        )
        if simple_loop or simple_path:
            adjacency: dict[int, list[int]] = defaultdict(list)
            for first, second in selected_edges:
                adjacency[first].append(second)
                adjacency[second].append(first)
            start = (
                min(vertex for vertex, degree in degrees.items() if degree == 1)
                if simple_path
                else min(vertices)
            )
            previous = None
            current = start
            ordered_vertices = [start]
            while True:
                choices = sorted(
                    value for value in adjacency[current] if value != previous
                )
                if not choices:
                    break
                following = choices[0]
                if following == start:
                    ordered_vertices.append(start)
                    break
                ordered_vertices.append(following)
                previous, current = current, following
        payload = {
            "component": component,
            "edge_vertex_pairs": [list(edge) for edge in sorted(selected_edges)],
            "immutable_incident_face_ids": sorted(
                {
                    face
                    for edge in selected_edges
                    for face in edge_records[edge]["immutable_incident_face_ids"]
                }
            ),
            "is_simple_loop": simple_loop,
            "is_simple_path": simple_path,
            "ordered_vertex_ids": ordered_vertices,
            "vertex_degrees": {
                str(vertex): degrees[vertex] for vertex in sorted(degrees)
            },
        }
        payload["fingerprint"] = stable_hash(payload)
        components.append(payload)
    components.sort(key=lambda value: value["edge_vertex_pairs"])
    for index, component_record in enumerate(components):
        component_record["boundary_id"] = (
            f"AGGREGATE_BOUNDARY_{component}_{index:03d}"
        )
    return components


def strongly_connected_components(
    nodes: list[str], edges: list[dict[str, Any]]
) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge["source"]].append(edge["target"])
    for node in adjacency:
        adjacency[node] = sorted(set(adjacency[node]))
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for following in adjacency.get(node, []):
            if following not in indices:
                visit(following)
                lowlinks[node] = min(lowlinks[node], lowlinks[following])
            elif following in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[following])
        if lowlinks[node] == indices[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            result.append(sorted(component))

    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return sorted(result, key=lambda values: values[0])


def flatten_keepouts(negative: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for aperture in negative["aperture_keepouts"]:
        for cell in aperture["cells"]:
            result.append(
                {
                    "cell_id": cell["cell_id"],
                    "kind": "APERTURE",
                    "source_identifier": aperture["keepout_id"],
                    "source_edge_ids": aperture["source"]["source_edge_ids"],
                    "half_spaces": cell["half_spaces"],
                }
            )
    for cell in negative["source_open_route_keepouts"]["cells"]:
        result.append(
            {
                "cell_id": cell["cell_id"],
                "kind": "SOURCE_OPEN_ROUTE",
                "source_identifier": str(cell["source"]["source_edge_id"]),
                "source_edge_ids": [cell["source"]["source_edge_id"]],
                "half_spaces": cell["half_spaces"],
            }
        )
    for cell in negative["central_opening_keepouts"]["cells"]:
        result.append(
            {
                "cell_id": cell["cell_id"],
                "kind": "CENTRAL_OPENING",
                "source_identifier": str(cell["source"]["source_edge_id"]),
                "source_edge_ids": [cell["source"]["source_edge_id"]],
                "half_spaces": cell["half_spaces"],
            }
        )
    flex = negative["flex_gap_keepout"]
    result.append(
        {
            "cell_id": flex["cell_id"],
            "kind": "FLEX_GAP",
            "source_identifier": flex["cell_id"],
            "source_edge_ids": [],
            "half_spaces": flex["half_spaces"],
        }
    )
    return sorted(result, key=lambda value: (value["kind"], value["cell_id"]))


def build_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    verified_inputs = {}
    for label, (path, expected) in FROZEN_INPUTS.items():
        actual = sha_file(path)
        if actual != expected:
            raise RuntimeError(
                f"{OPERATION}: V27_INPUT_AUTHORITY_HASH_MISMATCH for {label} "
                f"at {path}; expected {expected}, measured {actual}. Revise the "
                "V27 frozen-input contract deliberately before continuing."
            )
        verified_inputs[label] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual,
        }

    exposure = load_json(FROZEN_INPUTS["exposure_cell_authority"][0], "exposure")
    terminals = load_json(FROZEN_INPUTS["terminal_authority"][0], "terminals")
    negative = load_json(
        FROZEN_INPUTS["negative_space_authority"][0], "negative space"
    )
    floor_summary = load_json(
        FROZEN_INPUTS["floor_ownership_summary"][0], "floor summary"
    )
    cell_authority = load_json(FROZEN_INPUTS["cell_authority"][0], "cells")
    joint = load_json(FROZEN_INPUTS["joint_authority"][0], "joint")

    blend_path = Path(joint["input_blend"])
    if not blend_path.is_absolute():
        blend_path = ROOT / blend_path
    expected_blend_hash = joint["input_blend_sha256"]
    measured_blend_hash = sha_file(blend_path)
    if measured_blend_hash != expected_blend_hash:
        raise RuntimeError(
            f"{OPERATION}: V27_SOURCE_SCENE_OR_OBJECT_IDENTITY_MISMATCH for "
            f"{blend_path}; expected Blend SHA-256 {expected_blend_hash}, "
            f"measured {measured_blend_hash}."
        )
    verified_inputs["input_blend"] = {
        "path": str(blend_path.relative_to(ROOT)),
        "sha256": measured_blend_hash,
    }

    if exposure["seed_covering_subset"]["selected_cell_ids"] != SELECTED_CELL_IDS:
        raise RuntimeError(
            f"{OPERATION}: frozen exposure selected-cell list differs from the "
            "V27 23-cell contract; mask expansion/relabeling is not authorized"
        )
    cell_by_id = {cell["name"]: cell for cell in exposure["exposure_cells"]}
    missing_cells = sorted(set(SELECTED_CELL_IDS) - set(cell_by_id))
    if missing_cells:
        raise RuntimeError(
            f"{OPERATION}: selected exposure cells are missing: {missing_cells}"
        )
    selected_cells = [cell_by_id[cell_id] for cell_id in SELECTED_CELL_IDS]

    face_owner: dict[tuple[str, int], str] = {}
    duplicate_faces = []
    for cell in selected_cells:
        for source_face_id in cell["source_face_ids"]:
            key = (cell["component"], int(source_face_id))
            if key in face_owner:
                duplicate_faces.append(
                    {
                        "component": key[0],
                        "source_face_id": key[1],
                        "first_cell": face_owner[key],
                        "second_cell": cell["name"],
                    }
                )
            face_owner[key] = cell["name"]
    if duplicate_faces:
        raise RuntimeError(
            f"{OPERATION}: V27_CELL_OWNERSHIP_NOT_UNIQUE; first duplicate is "
            f"{duplicate_faces[0]}"
        )

    aggregate_faces = {
        component: sorted(
            face_id
            for (owner_component, face_id), _cell in face_owner.items()
            if owner_component == component
        )
        for component in ("C20", "C9")
    }
    maximum_masks = {
        component: set(
            int(value)
            for value in cell_authority["maximum_masks"][component]["face_ids"]
        )
        for component in ("C20", "C9")
    }
    immutable_complement = {
        component: sorted(maximum_masks[component] - set(aggregate_faces[component]))
        for component in ("C20", "C9")
    }
    outside_maximum = {
        component: sorted(set(aggregate_faces[component]) - maximum_masks[component])
        for component in ("C20", "C9")
    }
    if any(outside_maximum.values()):
        raise RuntimeError(
            f"{OPERATION}: V27_AGGREGATE_MASK_EXPANSION_REQUIRED; selected faces "
            f"outside maximum masks are {outside_maximum}"
        )
    frozen_ambiguous = {
        component: set(
            int(value)
            for value in exposure["immutable_complements"][component][
                "ambiguous_source_face_ids"
            ]
        )
        for component in ("C20", "C9")
    }
    ambiguous_overlap = {
        component: sorted(
            set(aggregate_faces[component]) & frozen_ambiguous[component]
        )
        for component in ("C20", "C9")
    }
    if any(ambiguous_overlap.values()):
        raise RuntimeError(
            f"{OPERATION}: V27_AGGREGATE_MASK_INCLUDES_IMMUTABLE_FACE; overlaps "
            f"are {ambiguous_overlap}"
        )

    boundary_records_by_component: dict[str, dict[tuple[int, int], dict[str, Any]]] = {
        "C20": {},
        "C9": {},
    }
    cell_boundary_refs: dict[str, list[tuple[str, tuple[int, int]]]] = defaultdict(
        list
    )
    for cell in selected_cells:
        component = cell["component"]
        mask_faces = set(aggregate_faces[component])
        for record in cell["boundary_edge_records"]:
            edge = tuple(sorted(int(value) for value in record["vertex_ids"]))
            selected_incident = sorted(
                set(int(value) for value in record["selected_incident_face_ids"])
                & mask_faces
            )
            outside_incident = sorted(
                set(int(value) for value in record["complement_incident_face_ids"])
                - mask_faces
            )
            if not selected_incident:
                continue
            if record["complement_incident_face_ids"] and not outside_incident:
                continue
            existing = boundary_records_by_component[component].setdefault(
                edge,
                {
                    "component": component,
                    "vertex_ids": list(edge),
                    "source_edge_ids": set(),
                    "selected_incident_face_ids": set(),
                    "immutable_incident_face_ids": set(),
                    "barrier_reasons": set(),
                    "incident_cell_ids": set(),
                },
            )
            if record["source_edge_id"] is not None:
                existing["source_edge_ids"].add(int(record["source_edge_id"]))
            existing["selected_incident_face_ids"].update(selected_incident)
            existing["immutable_incident_face_ids"].update(outside_incident)
            existing["barrier_reasons"].update(record["barrier_reasons"])
            existing["incident_cell_ids"].add(cell["name"])
            cell_boundary_refs[cell["name"]].append((component, edge))

    boundary_components = []
    boundary_edge_records = []
    edge_to_boundary = {}
    for component in ("C20", "C9"):
        normalized = []
        for edge, record in sorted(boundary_records_by_component[component].items()):
            normalized_record = {
                key: sorted(value) if isinstance(value, set) else value
                for key, value in record.items()
            }
            normalized.append(normalized_record)
        components = build_boundary_components(component, normalized)
        boundary_components.extend(components)
        for component_record in components:
            for edge in component_record["edge_vertex_pairs"]:
                edge_to_boundary[(component, tuple(edge))] = component_record[
                    "boundary_id"
                ]
        boundary_edge_records.extend(normalized)

    cell_boundary_dependencies = {}
    for cell in selected_cells:
        references = sorted(
            {
                edge_to_boundary[(component, edge)]
                for component, edge in cell_boundary_refs[cell["name"]]
                if (component, edge) in edge_to_boundary
            }
        )
        cell_boundary_dependencies[cell["name"]] = references

    terminal_incidences = []
    terminal_hard_stops = []
    all_exposure_owner = {
        (cell["component"], int(face_id)): cell["name"]
        for cell in exposure["exposure_cells"]
        for face_id in cell["source_face_ids"]
    }
    for component, side in sorted(TERMINAL_IDS):
        terminal = terminals["selection"][component][side]
        chain_id = TERMINAL_IDS[(component, side)]
        if terminal["chain_id"] != chain_id:
            raise RuntimeError(
                f"{OPERATION}: terminal {component} {side} expected {chain_id}, "
                f"measured {terminal['chain_id']}"
            )
        candidate_faces = [
            int(value) for value in terminal["candidate_incident_face_ids"]
        ]
        selected_candidate_faces = [
            value for value in candidate_faces if (component, value) in face_owner
        ]
        incidence = {
            "terminal_id": chain_id,
            "component": component,
            "side": side,
            "source_edge_ids": [int(value) for value in terminal["source_edge_ids"]],
            "ordered_boundary_vertex_ids": [
                int(value) for value in terminal["ordered_boundary_vertex_ids"]
            ],
            "exact_source_coordinates_mm": terminal[
                "exact_source_coordinates_mm"
            ],
            "candidate_incident_face_ids": candidate_faces,
            "aggregate_candidate_face_ids": selected_candidate_faces,
            "candidate_face_cell_ids": [
                {
                    "source_face_id": value,
                    "exposure_cell_id": all_exposure_owner.get((component, value)),
                    "aggregate_selected": (component, value) in face_owner,
                }
                for value in candidate_faces
            ],
            "retained_incident_face_ids": [
                int(value) for value in terminal["retained_incident_face_ids"]
            ],
            "minimum_incident_triangle_distance_mm": terminal[
                "minimum_incident_triangle_distance_mm"
            ],
            "complete_aggregate_incidence": (
                len(selected_candidate_faces) == len(candidate_faces)
            ),
        }
        incidence["fingerprint"] = stable_hash(incidence)
        terminal_incidences.append(incidence)
        if not incidence["complete_aggregate_incidence"]:
            terminal_hard_stops.append(
                {
                    "code": "V27_NO_BOUNDARY_COINCIDENT_TERMINAL_CONSTRUCTION",
                    "operation": "derive exact terminal incidence",
                    "terminal_id": chain_id,
                    "candidate_incident_face_ids": candidate_faces,
                    "aggregate_candidate_face_ids": selected_candidate_faces,
                    "missing_cell_ids": sorted(
                        {
                            all_exposure_owner[(component, value)]
                            for value in candidate_faces
                            if (component, value) not in face_owner
                        }
                    ),
                    "actionable_reason": (
                        "the frozen 23-cell aggregate mask excludes one or more "
                        "terminal candidate incident faces; do not widen the mask "
                        "without revising the V27 contract"
                    ),
                }
            )

    keepouts = flatten_keepouts(negative)
    keepout_incidences = []
    for cell in selected_cells:
        topology = {
            int(record["source_face_id"]): [
                int(value) for value in record["loop_source_vertex_ids"]
            ]
            for record in cell["face_topology"]
        }
        coordinates = {
            int(vertex): [float(value) for value in point]
            for vertex, point in cell["source_vertex_coordinates_mm"].items()
        }
        boundary_source_edges = {
            int(record["source_edge_id"])
            for record in cell["boundary_edge_records"]
            if record["source_edge_id"] is not None
        }
        for keepout in keepouts:
            intersecting_faces = []
            for face_id, vertices in topology.items():
                points = [coordinates[vertex] for vertex in vertices]
                for index in range(1, len(points) - 1):
                    triangle = [points[0], points[index], points[index + 1]]
                    if triangle_intersects_convex_cell(
                        triangle, keepout["half_spaces"]
                    ):
                        intersecting_faces.append(face_id)
                        break
            shared_source_edges = sorted(
                boundary_source_edges & set(keepout["source_edge_ids"])
            )
            if intersecting_faces or shared_source_edges:
                keepout_incidences.append(
                    {
                        "exposure_cell_id": cell["name"],
                        "keepout_cell_id": keepout["cell_id"],
                        "keepout_kind": keepout["kind"],
                        "source_identifier": keepout["source_identifier"],
                        "intersecting_source_face_ids": sorted(intersecting_faces),
                        "shared_source_edge_ids": shared_source_edges,
                        "relation": "KEEP_OUT_INCIDENCE",
                    }
                )
    keepout_incidences.sort(
        key=lambda value: (
            cell_sort_key(value["exposure_cell_id"]),
            value["keepout_kind"],
            value["keepout_cell_id"],
        )
    )

    floor = load_json(
        FROZEN_INPUTS["floor_ownership_authority"][0], "full floor authority"
    )
    all_gap_conflicts = []
    for record in floor["ownership"]["gap_source_floors_requiring_removal"]:
        owners = sorted(
            {
                face_owner[(component, int(face_id))]
                for component in ("C20", "C9")
                for face_id in record["face_ids"]
                if (component, int(face_id)) in face_owner
            },
            key=cell_sort_key,
        )
        all_gap_conflicts.append(
            {
                "conflict_id": f"GAP_FLOOR_{int(record['lattice_index']):05d}",
                "kind": "SOURCE_FLOOR_INSIDE_REQUIRED_FLEX_GAP",
                "lattice_index": int(record["lattice_index"]),
                "station_mm": record["station_mm"],
                "source_face_ids": [int(value) for value in record["face_ids"]],
                "exposure_cell_ids": owners,
                "aggregate_mask_touched": bool(owners),
            }
        )
    all_inversion_conflicts = []
    for record in floor["ownership"]["samples"]:
        if record["ordered_cutter_floor_exterior_valid"]:
            continue
        face_ids = sorted(
            {
                int(item["source_face_id"])
                for item in record["ordered_atomic_intersections"]
            }
        )
        owners = sorted(
            {
                face_owner[(component, face_id)]
                for component in ("C20", "C9")
                for face_id in face_ids
                if (component, face_id) in face_owner
            },
            key=cell_sort_key,
        )
        all_inversion_conflicts.append(
            {
                "conflict_id": (
                    f"LAYER_INVERSION_{int(record['lattice_index']):05d}"
                ),
                "kind": "CUTTER_FLOOR_EXTERIOR_LAYER_ORDER_INVERTED",
                "lattice_index": int(record["lattice_index"]),
                "station_mm": record["station_mm"],
                "source_face_ids": face_ids,
                "first_retained_exterior_face_id": int(
                    record["first_retained_exterior_intersection"][
                        "source_face_id"
                    ]
                ),
                "exposure_cell_ids": owners,
                "aggregate_mask_touched": bool(owners),
            }
        )
    all_floor_conflicts = sorted(
        all_gap_conflicts + all_inversion_conflicts,
        key=lambda value: (value["kind"], value["lattice_index"]),
    )
    floor_conflicts = [
        value for value in all_floor_conflicts if value["aggregate_mask_touched"]
    ]
    floor_conflict_exclusions = [
        value
        for value in all_floor_conflicts
        if not value["aggregate_mask_touched"]
    ]

    nodes: dict[str, dict[str, Any]] = {}
    for cell in selected_cells:
        nodes[cell["name"]] = {
            "node_id": cell["name"],
            "kind": "EXPOSURE_CELL",
            "component": cell["component"],
            "source_face_count": len(cell["source_face_ids"]),
        }
    for terminal in terminal_incidences:
        node_id = f"TERMINAL::{terminal['terminal_id']}"
        nodes[node_id] = {
            "node_id": node_id,
            "kind": "TERMINAL",
            "source_identifier": terminal["terminal_id"],
        }
    for boundary in boundary_components:
        node_id = f"BOUNDARY::{boundary['boundary_id']}"
        nodes[node_id] = {
            "node_id": node_id,
            "kind": "IMMUTABLE_COMPLEMENT_BOUNDARY",
            "source_identifier": boundary["boundary_id"],
        }
    for incidence in keepout_incidences:
        node_id = f"KEEPOUT::{incidence['keepout_cell_id']}"
        nodes.setdefault(
            node_id,
            {
                "node_id": node_id,
                "kind": incidence["keepout_kind"],
                "source_identifier": incidence["keepout_cell_id"],
            },
        )
    for conflict in floor_conflicts:
        node_id = f"FLOOR::{conflict['conflict_id']}"
        nodes[node_id] = {
            "node_id": node_id,
            "kind": "FLOOR_CONFLICT",
            "source_identifier": conflict["conflict_id"],
        }

    edges = []

    def add_edge(source: str, target: str, kind: str, identifier: str) -> None:
        edges.append(
            {
                "source": source,
                "target": target,
                "dependency_kind": kind,
                "source_identifier": identifier,
            }
        )

    for index, first in enumerate(selected_cells):
        first_edges = {
            tuple(sorted(record["vertex_ids"]))
            for record in first["boundary_edge_records"]
        }
        first_vertices = set(first["source_vertex_ids"])
        for second in selected_cells[index + 1 :]:
            if first["component"] != second["component"]:
                continue
            shared_edges = sorted(
                first_edges
                & {
                    tuple(sorted(record["vertex_ids"]))
                    for record in second["boundary_edge_records"]
                }
            )
            shared_vertices = sorted(
                first_vertices & set(second["source_vertex_ids"])
            )
            if shared_edges:
                identifier = stable_hash(shared_edges)
                kind = "SHARED_BOUNDARY_EDGE"
            elif shared_vertices:
                identifier = stable_hash(shared_vertices)
                kind = "SHARED_BOUNDARY_VERTEX"
            else:
                continue
            add_edge(first["name"], second["name"], kind, identifier)
            add_edge(second["name"], first["name"], kind, identifier)

    for cell_id, boundary_ids in sorted(
        cell_boundary_dependencies.items(), key=lambda item: cell_sort_key(item[0])
    ):
        for boundary_id in boundary_ids:
            add_edge(
                f"BOUNDARY::{boundary_id}",
                cell_id,
                "IMMUTABLE_BOUNDARY_INCIDENCE",
                boundary_id,
            )
    for terminal in terminal_incidences:
        for cell_id in sorted(
            {
                face_owner[(terminal["component"], face_id)]
                for face_id in terminal["aggregate_candidate_face_ids"]
            },
            key=cell_sort_key,
        ):
            add_edge(
                f"TERMINAL::{terminal['terminal_id']}",
                cell_id,
                "TERMINAL_INCIDENCE",
                terminal["terminal_id"],
            )
    for incidence in keepout_incidences:
        add_edge(
            f"KEEPOUT::{incidence['keepout_cell_id']}",
            incidence["exposure_cell_id"],
            (
                "GAP_INCIDENCE"
                if incidence["keepout_kind"] == "FLEX_GAP"
                else "KEEPOUT_INCIDENCE"
            ),
            incidence["keepout_cell_id"],
        )
    for conflict in floor_conflicts:
        for cell_id in conflict["exposure_cell_ids"]:
            add_edge(
                f"FLOOR::{conflict['conflict_id']}",
                cell_id,
                "FLOOR_CONFLICT_INCIDENCE",
                conflict["conflict_id"],
            )
    edges = sorted(
        {
            (
                edge["source"],
                edge["target"],
                edge["dependency_kind"],
                edge["source_identifier"],
            ): edge
            for edge in edges
        }.values(),
        key=lambda value: (
            value["source"],
            value["dependency_kind"],
            value["target"],
            value["source_identifier"],
        ),
    )

    sccs = strongly_connected_components(sorted(nodes), edges)
    node_to_scc = {
        node: index for index, members in enumerate(sccs) for node in members
    }
    condensed_edges = sorted(
        {
            (node_to_scc[edge["source"]], node_to_scc[edge["target"]])
            for edge in edges
            if node_to_scc[edge["source"]] != node_to_scc[edge["target"]]
        }
    )
    cell_sccs = []
    for scc_index, members in enumerate(sccs):
        cell_members = sorted(
            [member for member in members if member in SELECTED_CELL_IDS],
            key=cell_sort_key,
        )
        if cell_members:
            cell_sccs.append(
                {
                    "scc_index": scc_index,
                    "cell_ids": cell_members,
                    "cell_count": len(cell_members),
                }
            )
    oversized_sccs = [
        value
        for value in cell_sccs
        if value["cell_count"] > MAXIMUM_BATCH_CELL_COUNT
    ]
    scc_hard_stops = []
    if oversized_sccs:
        scc_hard_stops.append(
            {
                "code": "V27_DEPENDENCY_SCC_EXCEEDS_BATCH_BOUND",
                "operation": "condense aggregate dependency graph",
                "maximum_batch_cell_count": MAXIMUM_BATCH_CELL_COUNT,
                "oversized_sccs": oversized_sccs,
                "actionable_reason": (
                    "revise the reconstruction contract; an SCC may not be "
                    "split or the 12-cell recovery bound raised implicitly"
                ),
            }
        )

    batches = []
    if not oversized_sccs:
        current: list[str] = []
        current_sccs: list[int] = []
        for record in sorted(
            cell_sccs, key=lambda value: cell_sort_key(value["cell_ids"][0])
        ):
            if current and len(current) + record["cell_count"] > 12:
                batches.append(
                    {
                        "batch_index": len(batches),
                        "cell_ids": current,
                        "cell_count": len(current),
                        "scc_indices": current_sccs,
                    }
                )
                current = []
                current_sccs = []
            current.extend(record["cell_ids"])
            current_sccs.append(record["scc_index"])
        if current:
            batches.append(
                {
                    "batch_index": len(batches),
                    "cell_ids": current,
                    "cell_count": len(current),
                    "scc_indices": current_sccs,
                }
            )
    for batch in batches:
        batch["fingerprint"] = stable_hash(batch)

    no_floor = floor_summary["ownership"]["non_gap_zero_floor"]
    no_floor_exclusion = {
        "authority": "v26_floor_ownership_summary.json",
        "sample_count": int(no_floor["count"]),
        "first_lattice_index": int(no_floor["first"]["lattice_index"]),
        "last_lattice_index": int(no_floor["last"]["lattice_index"]),
        "mask_derivation_uses_source_face_membership_only": True,
        "no_floor_samples_used_as_faces_or_seeds": False,
        "excluded": True,
    }
    if no_floor_exclusion["sample_count"] != 12523:
        raise RuntimeError(
            f"{OPERATION}: V27_NEGATIVE_SPACE_OR_NO_FLOOR_CONFLICT; expected "
            f"12,523 excluded NO_FLOOR samples, measured "
            f"{no_floor_exclusion['sample_count']}"
        )

    hard_stops = terminal_hard_stops + scc_hard_stops
    mask_payload = {
        "selected_cell_ids": SELECTED_CELL_IDS,
        "cell_count": len(SELECTED_CELL_IDS),
        "source_face_ids": aggregate_faces,
        "source_face_count": {
            component: len(values) for component, values in aggregate_faces.items()
        },
        "immutable_complement_source_face_ids": immutable_complement,
        "immutable_complement_source_face_count": {
            component: len(values)
            for component, values in immutable_complement.items()
        },
        "unique_face_ownership": True,
        "immutable_overlap": ambiguous_overlap,
        "outside_maximum_mask": outside_maximum,
    }
    mask_payload["fingerprint"] = stable_hash(mask_payload)
    graph_payload = {
        "nodes": [nodes[node] for node in sorted(nodes)],
        "edges": edges,
        "strongly_connected_components": [
            {"scc_index": index, "node_ids": members}
            for index, members in enumerate(sccs)
        ],
        "condensed_edges": [
            {"source_scc": first, "target_scc": second}
            for first, second in condensed_edges
        ],
        "cell_sccs": cell_sccs,
        "batches": batches,
        "maximum_batch_cell_count": MAXIMUM_BATCH_CELL_COUNT,
    }
    graph_payload["fingerprint"] = stable_hash(graph_payload)

    authority = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": RESULT,
        "promotion": "NOT_PROMOTED",
        "scope": (
            "read-only exact aggregate mask and dependency authority; no gap "
            "solve, candidate geometry, mutation, image work, or Blend save"
        ),
        "code_sha256": sha_file(Path(__file__)),
        "verified_inputs": verified_inputs,
        "aggregate_mask": mask_payload,
        "aggregate_boundary": {
            "edge_records": boundary_edge_records,
            "components": boundary_components,
            "cell_boundary_dependencies": cell_boundary_dependencies,
        },
        "terminal_incidences": terminal_incidences,
        "negative_space_incidences": keepout_incidences,
        "floor_conflicts": floor_conflicts,
        "floor_conflict_exclusions": floor_conflict_exclusions,
        "floor_conflict_accounting": {
            "full_authority_record_count": len(all_floor_conflicts),
            "aggregate_mask_touched_record_count": len(floor_conflicts),
            "aggregate_mask_excluded_record_count": len(
                floor_conflict_exclusions
            ),
            "gap_floor_record_count": len(all_gap_conflicts),
            "layer_inversion_record_count": len(all_inversion_conflicts),
            "all_records_accounted_for": (
                len(all_floor_conflicts)
                == len(floor_conflicts) + len(floor_conflict_exclusions)
                == 98
            ),
        },
        "no_floor_exclusion": no_floor_exclusion,
        "dependency_graph": graph_payload,
        "hard_stops": hard_stops,
        "invariants": {
            "frozen_authority_hashes_match": True,
            "input_blend_hash_matches": True,
            "selected_cell_count_is_23": len(SELECTED_CELL_IDS) == 23,
            "face_ownership_is_unique": True,
            "aggregate_mask_excludes_frozen_ambiguous_faces": not any(
                ambiguous_overlap.values()
            ),
            "aggregate_mask_is_inside_maximum_masks": not any(
                outside_maximum.values()
            ),
            "terminal_record_count_is_4": len(terminal_incidences) == 4,
            "all_terminal_incidences_complete": not terminal_hard_stops,
            "no_floor_sample_count_is_12523": (
                no_floor_exclusion["sample_count"] == 12523
            ),
            "no_floor_is_excluded": True,
            "all_cell_sccs_fit_batch_bound": not oversized_sccs,
            "all_batches_fit_batch_bound": all(
                batch["cell_count"] <= 12 for batch in batches
            ),
        },
        "safety": {
            "candidate_construction_started": False,
            "mutation_started": False,
            "geometry_emitted": False,
            "flex_gap_solve_started": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        },
    }
    semantic_payload = dict(authority)
    semantic_payload.pop("code_sha256")
    authority["semantic_fingerprint"] = stable_hash(semantic_payload)

    receipt = {
        "operation": OPERATION,
        "status": RESULT,
        "aggregate_mask_fingerprint": mask_payload["fingerprint"],
        "dependency_graph_fingerprint": graph_payload["fingerprint"],
        "semantic_fingerprint": authority["semantic_fingerprint"],
        "selected_cell_count": len(SELECTED_CELL_IDS),
        "aggregate_source_face_count": mask_payload["source_face_count"],
        "aggregate_boundary_component_count": len(boundary_components),
        "terminal_incidence_count": len(terminal_incidences),
        "complete_terminal_incidence_count": sum(
            value["complete_aggregate_incidence"] for value in terminal_incidences
        ),
        "negative_space_incidence_count": len(keepout_incidences),
        "floor_conflict_count": len(floor_conflicts),
        "floor_conflict_exclusion_count": len(floor_conflict_exclusions),
        "full_floor_conflict_record_count": len(all_floor_conflicts),
        "no_floor_excluded_sample_count": no_floor_exclusion["sample_count"],
        "cell_scc_count": len(cell_sccs),
        "maximum_cell_scc_size": max(
            (value["cell_count"] for value in cell_sccs), default=0
        ),
        "batch_cell_counts": [value["cell_count"] for value in batches],
        "hard_stop_codes": sorted({value["code"] for value in hard_stops}),
        "safety": authority["safety"],
    }
    return authority, receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    arguments = parser.parse_args()
    authority, receipt = build_authority()
    atomic_write_json(arguments.output, authority)
    receipt["authority_path"] = str(arguments.output)
    receipt["authority_sha256"] = sha_file(arguments.output)
    atomic_write_json(arguments.receipt, receipt)
    print(
        json.dumps(
            {
                "status": authority["status"],
                "output": str(arguments.output),
                "output_sha256": receipt["authority_sha256"],
                "receipt": str(arguments.receipt),
                "hard_stop_codes": receipt["hard_stop_codes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
