#!/usr/bin/env python3
"""Select a bounded V26 review batch from exact ambiguous face paths.

The selector is JSON-only.  It never opens Blender, reads or generates images,
constructs geometry, or changes the exposure-cell builder or its authorities.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from fractions import Fraction
from hashlib import sha256
import itertools
import json
from pathlib import Path


OPERATION = "V26_AMBIGUOUS_BRIDGE_PATH_SELECTOR"
MISSION = "R014-JOINT-C9-C20-ELBOW-V26"
ROUND_INDEX = 4
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
AUTHORITY_DIR = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
DEFAULT_CELL_AUTHORITY = AUTHORITY_DIR / "v26_cell_authority.json"
DEFAULT_EXPOSURE_AUTHORITY = AUTHORITY_DIR / "v26_exposure_cell_authority.json"
EXPECTED_CELL_SHA256 = (
    "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca"
)
EXPECTED_EXPOSURE_SHA256 = (
    "1ea6ea406fa5057d08822ccb0121728394b546d4836bc444896855f0f0a2f7a6"
)
MAXIMUM_BATCH_FACE_COUNT = 26
EXPECTED_REVIEWED_COUNTS = {
    "base": 19,
    "bridge_round_01": 26,
    "bridge_round_02": 25,
    "bridge_round_03": 23,
    "total": 93,
}
NON_TRAVERSABLE_BARRIER_REASONS = {
    "C20_CLOSED_APERTURE_ROUTE",
    "C20_DETERMINISTIC_FLEX_CUT_CHAIN",
    "C20_NAMED_RIDGE_OR_DEPTH_BREAK",
    "C20_SOURCE_OPEN_OR_APERTURE_ROUTE",
    "C9_DETERMINISTIC_FLEX_CUT_CHAIN",
    "SOURCE_OPEN_ROUTE",
}


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


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cell-authority",
        type=Path,
        default=DEFAULT_CELL_AUTHORITY,
    )
    parser.add_argument(
        "--exposure-authority",
        type=Path,
        default=DEFAULT_EXPOSURE_AUTHORITY,
    )
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    return parser.parse_args()


def face_topology(cell_authority):
    faces = {}
    components = {}
    materials = {}
    for component in ("C9", "C20"):
        for atomic_cell in cell_authority["atomic_cells"][component]:
            for record in atomic_cell["faces"]:
                face_id = record["source_face_id"]
                if face_id in faces:
                    raise RuntimeError(
                        f"{OPERATION}: duplicate source face {face_id} in "
                        "cell authority"
                    )
                faces[face_id] = tuple(record["loop_source_vertex_ids"])
                components[face_id] = component
                materials[face_id] = record["material_index"]
    edge_faces = defaultdict(list)
    for face_id, vertices in faces.items():
        for first, second in zip(vertices, (*vertices[1:], vertices[0])):
            edge_faces[tuple(sorted((first, second)))].append(face_id)
    for edge in edge_faces:
        edge_faces[edge].sort()
    return faces, components, materials, edge_faces


def blocked_edges(cell_authority):
    blocked = {}
    for record in cell_authority["barriers"]["inventory"]:
        reasons = set(record["barrier_reasons"])
        forbidden = sorted(reasons & NON_TRAVERSABLE_BARRIER_REASONS)
        if not forbidden:
            continue
        edge = tuple(sorted(record["vertex_ids"]))
        blocked[edge] = {
            "source_edge_id": record["source_edge_id"],
            "barrier_reasons": forbidden,
        }
    return blocked


def classification_face_ids(classification):
    result = set()
    for groups in classification["classifications"].values():
        if isinstance(groups, dict):
            for face_ids in groups.values():
                result.update(face_ids)
        else:
            result.update(groups)
    return result


def reviewed_face_authority(exposure_authority):
    sources = exposure_authority["source_authorities"]
    source_keys = {
        "base": "face_visual_classification",
        "bridge_round_01": "bridge_visual_classification",
        "bridge_round_02": "bridge_visual_classification_round_02",
        "bridge_round_03": "bridge_visual_classification_round_03",
    }
    contracts = {
        "base": (
            set(
                exposure_authority["contract_revision"][
                    "concealed_wearer_side_removable_face_ids"
                ]
            )
            | set(
                exposure_authority["contract_revision"][
                    "visible_silhouette_rim_opening_immutable_face_ids"
                ]
            )
        ),
    }
    records = {}
    for label, source_key in source_keys.items():
        source = sources[source_key]
        path = ROOT / source["path"]
        actual_sha = sha_file(path)
        if actual_sha != source["sha256"]:
            raise RuntimeError(
                f"{OPERATION}: reviewed classification hash mismatch for "
                f"'{path}'; actual={actual_sha}; expected={source['sha256']}"
            )
        classification = json.loads(path.read_text(encoding="utf-8"))
        face_ids = classification_face_ids(classification)
        if label == "base":
            if face_ids != contracts["base"]:
                raise RuntimeError(
                    f"{OPERATION}: base reviewed faces disagree with current "
                    "exposure contract"
                )
        else:
            contract = exposure_authority["contract_revision"][
                f"bridge_classification_round_{label[-2:]}"
            ]
            contract_ids = {
                face_id
                for key, values in contract.items()
                if key.endswith("_face_ids")
                for face_id in values
            }
            if face_ids != contract_ids:
                raise RuntimeError(
                    f"{OPERATION}: {label} reviewed faces disagree with "
                    "current exposure contract"
                )
        if len(face_ids) != EXPECTED_REVIEWED_COUNTS[label]:
            raise RuntimeError(
                f"{OPERATION}: {label} reviewed face count is "
                f"{len(face_ids)}, expected={EXPECTED_REVIEWED_COUNTS[label]}"
            )
        records[label] = {
            "path": str(path),
            "sha256": actual_sha,
            "status": classification["status"],
            "source_face_ids": sorted(face_ids),
            "source_face_count": len(face_ids),
        }
    overlaps = {}
    for first, second in itertools.combinations(sorted(records), 2):
        overlap = set(records[first]["source_face_ids"]) & set(
            records[second]["source_face_ids"]
        )
        if overlap:
            overlaps[f"{first}__{second}"] = sorted(overlap)
    if overlaps:
        raise RuntimeError(
            f"{OPERATION}: reviewed classification rounds overlap: {overlaps}"
        )
    excluded = {
        face_id
        for record in records.values()
        for face_id in record["source_face_ids"]
    }
    if len(excluded) != EXPECTED_REVIEWED_COUNTS["total"]:
        raise RuntimeError(
            f"{OPERATION}: reviewed exclusion count is {len(excluded)}, "
            f"expected={EXPECTED_REVIEWED_COUNTS['total']}"
        )
    return {
        "classification_authorities": records,
        "excluded_source_face_ids": sorted(excluded),
        "excluded_source_face_count": len(excluded),
        "every_visible_or_unresolved_reviewed_face_is_a_hard_barrier": True,
    }


def exact_graph(cell_authority, exposure_authority):
    faces, components, materials, edge_faces = face_topology(cell_authority)
    blocked = blocked_edges(cell_authority)
    reviewed = reviewed_face_authority(exposure_authority)
    reviewed_ids = set(reviewed["excluded_source_face_ids"])
    ambiguous = {
        component: (
            set(
                exposure_authority["immutable_complements"][component][
                    "ambiguous_source_face_ids"
                ]
            )
            - reviewed_ids
        )
        for component in ("C9", "C20")
    }
    required_ids = set(
        exposure_authority["seed_covering_subset"]["selected_cell_ids"]
    )
    required_cells = {
        record["name"]: {
            "component": record["component"],
            "source_face_ids": set(record["source_face_ids"]),
        }
        for record in exposure_authority["exposure_cells"]
        if record["name"] in required_ids
    }
    if set(required_cells) != required_ids:
        raise RuntimeError(
            f"{OPERATION}: missing required exposure cells: "
            f"{sorted(required_ids - set(required_cells))}"
        )
    face_required_cells = defaultdict(set)
    for cell_id, record in required_cells.items():
        for face_id in record["source_face_ids"]:
            face_required_cells[face_id].add(cell_id)

    graphs = {
        component: {face_id: set() for face_id in ambiguous[component]}
        for component in ("C9", "C20")
    }
    transitions = {}
    touches = defaultdict(set)
    touch_edges = defaultdict(list)
    for edge, incident in sorted(edge_faces.items()):
        if len(incident) != 2 or edge in blocked:
            continue
        first, second = incident
        if components[first] != components[second]:
            continue
        component = components[first]
        if materials[first] != materials[second]:
            continue
        if first in ambiguous[component] and second in ambiguous[component]:
            graphs[component][first].add(second)
            graphs[component][second].add(first)
            transitions[(component, min(first, second), max(first, second))] = {
                "vertex_ids": list(edge),
                "source_face_ids": [min(first, second), max(first, second)],
            }
        for ambiguous_face, endpoint_face in ((first, second), (second, first)):
            if ambiguous_face not in ambiguous[component]:
                continue
            for cell_id in sorted(face_required_cells[endpoint_face]):
                if required_cells[cell_id]["component"] != component:
                    continue
                touches[(component, ambiguous_face)].add(cell_id)
                touch_edges[(component, ambiguous_face, cell_id)].append(
                    {
                        "vertex_ids": list(edge),
                        "ambiguous_source_face_id": ambiguous_face,
                        "required_cell_source_face_id": endpoint_face,
                    }
                )
    return {
        "faces": faces,
        "components": components,
        "materials": materials,
        "graphs": graphs,
        "transitions": transitions,
        "touches": touches,
        "touch_edges": touch_edges,
        "required_cells": required_cells,
        "reviewed": reviewed,
        "ambiguous": ambiguous,
        "blocked_edges": blocked,
    }


def all_shortest_paths(graph, starts, goals):
    distances = {}
    queue = deque()
    for face_id in sorted(starts):
        distances[face_id] = 0
        queue.append(face_id)
    while queue:
        face_id = queue.popleft()
        for neighbor in sorted(graph[face_id]):
            if neighbor in distances:
                continue
            distances[neighbor] = distances[face_id] + 1
            queue.append(neighbor)
    reachable_goals = sorted(set(goals) & set(distances))
    if not reachable_goals:
        return []
    minimum_distance = min(distances[goal] for goal in reachable_goals)
    minimum_goals = {
        goal for goal in reachable_goals if distances[goal] == minimum_distance
    }
    paths = []

    def walk(path):
        face_id = path[-1]
        if len(path) - 1 == minimum_distance:
            if face_id in minimum_goals:
                paths.append(tuple(path))
            return
        for neighbor in sorted(graph[face_id]):
            if distances.get(neighbor) != distances[face_id] + 1:
                continue
            walk((*path, neighbor))

    for start in sorted(starts):
        walk((start,))
    return sorted(set(paths))


def enumerate_paths(context):
    path_records = {}
    for component in ("C9", "C20"):
        graph = context["graphs"][component]
        cell_ids = sorted(
            cell_id
            for cell_id, record in context["required_cells"].items()
            if record["component"] == component
        )
        boundary_nodes = {
            cell_id: {
                face_id
                for face_id in graph
                if cell_id in context["touches"][(component, face_id)]
            }
            for cell_id in cell_ids
        }
        for first_cell, second_cell in itertools.combinations(cell_ids, 2):
            if not boundary_nodes[first_cell] or not boundary_nodes[second_cell]:
                continue
            for path in all_shortest_paths(
                graph,
                boundary_nodes[first_cell],
                boundary_nodes[second_cell],
            ):
                reverse = tuple(reversed(path))
                canonical = min(path, reverse)
                key = (component, canonical)
                record = path_records.setdefault(
                    key,
                    {
                        "component": component,
                        "path_source_face_ids": list(canonical),
                        "supported_required_cell_pairs": set(),
                    },
                )
                record["supported_required_cell_pairs"].add(
                    (first_cell, second_cell)
                )
    records = []
    for (component, path), record in path_records.items():
        endpoint_cells = sorted(
            context["touches"][(component, path[0])]
            | context["touches"][(component, path[-1])]
        )
        transitions = []
        for first, second in zip(path, path[1:]):
            key = (component, min(first, second), max(first, second))
            transitions.append(context["transitions"][key])
        endpoint_witnesses = {
            str(face_id): {
                cell_id: sorted(
                    context["touch_edges"][(component, face_id, cell_id)],
                    key=lambda witness: (
                        witness["vertex_ids"],
                        witness["required_cell_source_face_id"],
                    ),
                )
                for cell_id in sorted(
                    context["touches"][(component, face_id)]
                )
            }
            for face_id in (path[0], path[-1])
        }
        pairs = sorted(record["supported_required_cell_pairs"])
        result = {
            "component": component,
            "ambiguous_face_count": len(path),
            "path_source_face_ids": list(path),
            "endpoint_required_cell_ids": endpoint_cells,
            "endpoint_required_cell_count": len(endpoint_cells),
            "supported_required_cell_pairs": [list(pair) for pair in pairs],
            "exact_source_edge_transitions": transitions,
            "endpoint_touch_witnesses": endpoint_witnesses,
            "all_path_faces_currently_exterior_or_ambiguous": True,
            "crosses_named_topology_barrier": False,
            "crosses_material_boundary": False,
            "crosses_source_open_route": False,
        }
        result["fingerprint"] = stable_hash(result)
        records.append(result)
    return sorted(
        records,
        key=lambda record: (
            record["ambiguous_face_count"],
            -record["endpoint_required_cell_count"],
            record["endpoint_required_cell_ids"],
            record["component"],
            record["path_source_face_ids"],
        ),
    )


def connectivity_pairs(record):
    return {
        tuple(pair)
        for pair in itertools.combinations(
            record["endpoint_required_cell_ids"],
            2,
        )
    }


def bounded_batch(paths):
    selected = []
    selected_faces = set()
    connected_pairs = set()
    remaining = list(paths)
    while remaining:
        candidates = []
        for record in remaining:
            path_faces = set(record["path_source_face_ids"])
            new_faces = path_faces - selected_faces
            if len(selected_faces | path_faces) > MAXIMUM_BATCH_FACE_COUNT:
                continue
            new_pairs = connectivity_pairs(record) - connected_pairs
            if not new_pairs:
                continue
            efficiency = (
                Fraction(len(new_pairs), len(new_faces))
                if new_faces
                else Fraction(10**9, 1)
            )
            rank = (
                record["ambiguous_face_count"],
                -record["endpoint_required_cell_count"],
                record["endpoint_required_cell_ids"],
                record["component"],
                record["path_source_face_ids"],
            )
            candidates.append(
                (
                    -efficiency,
                    rank,
                    record,
                    new_faces,
                    new_pairs,
                )
            )
        if not candidates:
            break
        _, _, chosen, new_faces, new_pairs = min(
            candidates,
            key=lambda item: (item[0], item[1]),
        )
        selection = {
            **chosen,
            "selection_step": len(selected) + 1,
            "new_unique_face_ids": sorted(new_faces),
            "new_required_cell_pairs": [
                list(pair) for pair in sorted(new_pairs)
            ],
            "new_connectivity_per_new_face": (
                f"{len(new_pairs)}/{len(new_faces)}"
                if new_faces
                else "infinite"
            ),
        }
        selected.append(selection)
        selected_faces.update(new_faces)
        connected_pairs.update(new_pairs)
        remaining.remove(chosen)
    return selected, selected_faces, connected_pairs


def merge_summary(cell_ids, pairs):
    parents = {cell_id: cell_id for cell_id in cell_ids}

    def find(cell_id):
        while parents[cell_id] != cell_id:
            parents[cell_id] = parents[parents[cell_id]]
            cell_id = parents[cell_id]
        return cell_id

    def union(first, second):
        first_root = find(first)
        second_root = find(second)
        if first_root == second_root:
            return
        keep, discard = sorted((first_root, second_root))
        parents[discard] = keep

    for first, second in sorted(pairs):
        union(first, second)
    groups = defaultdict(list)
    for cell_id in sorted(cell_ids):
        groups[find(cell_id)].append(cell_id)
    merged = sorted(
        (group for group in groups.values() if len(group) > 1),
        key=lambda group: (group[0], group),
    )
    return {
        "connected_required_cell_pairs": [
            list(pair) for pair in sorted(pairs)
        ],
        "possible_merge_groups": merged,
        "possible_required_cell_count_reduction": sum(
            len(group) - 1 for group in merged
        ),
    }


def text_report(report):
    lines = [
        f"# V26 ambiguous bridge-path review batch round {ROUND_INDEX:02d}",
        "",
        f"Status: `{report['status']}`",
        "",
        f"Unique faces: `{report['batch_unique_face_count']}`",
        "",
        f"Face IDs: `{report['batch_source_face_ids']}`",
        "",
        "| Step | Component | Path faces | Endpoint required cells |",
        "|---:|---|---|---|",
    ]
    for record in report["selected_paths"]:
        lines.append(
            f"| {record['selection_step']} | {record['component']} | "
            f"{record['path_source_face_ids']} | "
            f"{record['endpoint_required_cell_ids']} |"
        )
    lines.extend(
        [
            "",
            (
                "Possible merge groups: "
                f"`{report['expected_possible_merges']['possible_merge_groups']}`"
            ),
            "",
            "No image, Blender, model, candidate, or builder work performed.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    arguments = parse_arguments()
    cell_path = arguments.cell_authority.resolve()
    exposure_path = arguments.exposure_authority.resolve()
    hashes = {
        "cell": sha_file(cell_path),
        "exposure": sha_file(exposure_path),
    }
    expected = {
        "cell": EXPECTED_CELL_SHA256,
        "exposure": EXPECTED_EXPOSURE_SHA256,
    }
    if hashes != expected:
        raise RuntimeError(
            f"{OPERATION}: source authority mismatch; "
            f"actual={hashes}; expected={expected}"
        )
    cell_authority = json.loads(cell_path.read_text(encoding="utf-8"))
    exposure_authority = json.loads(
        exposure_path.read_text(encoding="utf-8")
    )
    context = exact_graph(cell_authority, exposure_authority)
    paths = enumerate_paths(context)
    selected, selected_faces, connected_pairs = bounded_batch(paths)
    selected_face_ids = sorted(selected_faces)
    if len(selected_face_ids) > MAXIMUM_BATCH_FACE_COUNT:
        raise RuntimeError(
            f"{OPERATION}: selected {len(selected_face_ids)} unique faces, "
            f"maximum={MAXIMUM_BATCH_FACE_COUNT}"
        )
    selected_components = {
        component: sorted(
            face_id
            for face_id in selected_face_ids
            if context["components"][face_id] == component
        )
        for component in ("C9", "C20")
    }
    touched_cells = sorted(
        {
            cell_id
            for record in selected
            for cell_id in record["endpoint_required_cell_ids"]
        }
    )
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "round_index": ROUND_INDEX,
        "status": (
            "V26_AMBIGUOUS_BRIDGE_PATH_BATCH_CHECKPOINTED"
            if paths
            else "NO_LEGAL_AMBIGUOUS_BRIDGE_PATHS_V26_ROUND_04"
        ),
        "input": {
            "cell_authority": {
                "path": str(cell_path),
                "sha256": hashes["cell"],
                "fingerprint": cell_authority["fingerprint"],
            },
            "exposure_authority": {
                "path": str(exposure_path),
                "sha256": hashes["exposure"],
                "semantic_fingerprint": exposure_authority[
                    "semantic_fingerprint"
                ],
            },
            "source_authorities": exposure_authority["source_authorities"],
        },
        "contract": {
            "adjacency": "exact shared source edge from cell authority loops",
            "path_faces": "current EXTERIOR_OR_AMBIGUOUS only",
            "reviewed_faces": "hard barriers",
            "minimum_distinct_endpoint_required_cells": 2,
            "path_ranking": (
                "ambiguous face count ascending; endpoint required cell count "
                "descending; endpoint cell IDs; component; path face IDs"
            ),
            "batch_selection": (
                "maximum new required-cell pair connectivity per new unique "
                "face, then path ranking"
            ),
            "maximum_unique_face_count": MAXIMUM_BATCH_FACE_COUNT,
            "non_traversable_barrier_reasons": sorted(
                NON_TRAVERSABLE_BARRIER_REASONS
            ),
        },
        "reviewed_face_barriers": context["reviewed"],
        "enumerated_unique_shortest_path_count": len(paths),
        "enumerated_paths": paths,
        "selected_path_count": len(selected),
        "selected_paths": selected,
        "batch_unique_face_count": len(selected_face_ids),
        "batch_source_face_ids": selected_face_ids,
        "batch_source_face_ids_by_component": selected_components,
        "batch_touched_required_cell_ids": touched_cells,
        "expected_possible_merges": merge_summary(
            touched_cells,
            connected_pairs,
        ),
        "graph_summary": {
            component: {
                "current_unreviewed_ambiguous_face_count": len(
                    context["graphs"][component]
                ),
                "traversable_ambiguous_adjacency_count": sum(
                    len(neighbors)
                    for neighbors in context["graphs"][component].values()
                )
                // 2,
            }
            for component in ("C9", "C20")
        },
        "safety": {
            "images_read": False,
            "images_generated": False,
            "blender_or_model_opened": False,
            "candidate_construction_started": False,
            "exposure_builder_modified": False,
            "mutation_started": False,
        },
    }
    report["semantic_fingerprint"] = stable_hash(report)
    atomic_text(
        arguments.json.resolve(),
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    atomic_text(arguments.text.resolve(), text_report(report))
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "status": report["status"],
                "enumerated_unique_shortest_path_count": len(paths),
                "selected_path_count": len(selected),
                "batch_unique_face_count": len(selected_face_ids),
                "batch_source_face_ids_by_component": selected_components,
                "json": str(arguments.json.resolve()),
                "text": str(arguments.text.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
