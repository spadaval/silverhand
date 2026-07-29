#!/usr/bin/env python3
"""Build the corrected read-only V26 exposure-separated cell authority.

This consumes only checkpointed JSON evidence.  It emits no geometry, opens no
Blend, and grants no terminal-search or candidate-construction authority.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


OPERATION = "BUILD_V26_EXPOSURE_CELL_AUTHORITY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V26"
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
CURRENT_AUDIT = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_current_audit/report.json"
)
V22_ATTRIBUTION = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v22/exact_overlap_attribution.json"
)
JOINT_AUTHORITY = EVIDENCE / "v26_joint_authority.json"
CELL_AUTHORITY = EVIDENCE / "v26_cell_authority.json"
FLOOR_AUTHORITY = EVIDENCE / "v26_floor_ownership_authority.json"
FLOOR_SUMMARY = EVIDENCE / "v26_floor_ownership_summary.json"
FACE_VISUAL_CLASSIFICATION = EVIDENCE / "face_visual/classification.json"
BRIDGE_VISUAL_CLASSIFICATION = (
    EVIDENCE / "face_visual/bridge_classification_round_01.json"
)
OUTPUT = EVIDENCE / "v26_exposure_cell_authority.json"
PRE_VISUAL_SEMANTIC_FINGERPRINT = (
    "b5a5caec522112542dc0220428897ece79fcb698b0f80df19739ef389eb25d94"
)
PRE_VISUAL_OUTPUT_SHA256 = (
    "e3f65cf6e71959c48e12b616022b3196dd42e28e518ab106fbfb1680caca0d2b"
)
PRE_VISUAL_STALE_PATH = EVIDENCE / (
    "v26_exposure_cell_authority.stale-"
    f"{PRE_VISUAL_SEMANTIC_FINGERPRINT[:12]}.json"
)
PRE_BRIDGE_SEMANTIC_FINGERPRINT = (
    "7047774c2f70d3bc3163f5db511e5cb3bb683d2547f7d1692f73424e69262c1c"
)
PRE_BRIDGE_OUTPUT_SHA256 = (
    "ba8850ee85608ff293605d649f9ab811a53bebdffeb738586b6e5d703a79b7cb"
)
PRE_BRIDGE_STALE_PATH = EVIDENCE / (
    "v26_exposure_cell_authority.stale-"
    f"{PRE_BRIDGE_SEMANTIC_FINGERPRINT[:12]}.json"
)

EXPECTED_HASHES = {
    "joint_authority": (
        "e4a01b2d0e0f5d7997983d43af90cf2f2cd2bec81c859645b7e6961b8a55bbef"
    ),
    "cell_authority": (
        "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca"
    ),
    "floor_authority": (
        "02b758bddee0be121c9c1e93cef13b781b4e8241bda862ec6c8d389aaf653ab9"
    ),
    "floor_summary": (
        "2a054e9290869a6b647b4da1fa52f98e6537c8bca2a3b12546374ff788c982a9"
    ),
    "face_visual_classification": (
        "d3f7dfbfff0fdaa6f50c65f6d26aa60c32567f5b3711d474ef335714a14794cf"
    ),
    "bridge_visual_classification": (
        "e38138b03abb22d411107a064aae99d53d1b82b3d28a3fb5b72ef422827f1c7f"
    ),
    "current_audit": (
        "3abe6e1b73e0790ce3eea762abe7556dd56dc78a39816f2547808fdc17d71ffd"
    ),
    "v22_attribution": (
        "d80989e71a37423ac2d3717c0384e8db23ae848fdf97ea97490a23dfa97c9624"
    ),
}
ELIGIBLE_GAP_FACES = [2921, 2922, 2999, 3000, 3001, 3002, 8687]
INTERFACE_C9_VERTICES = [1257, 1295]
MAXIMUM_SELECTED_CELLS = 12
EXPECTED_EXPOSURE_COUNTS = {
    "C20": {"WEARER_FACING": 213, "EXTERIOR_OR_AMBIGUOUS": 511},
    "C9": {"WEARER_FACING": 56, "EXTERIOR_OR_AMBIGUOUS": 182},
}
EXPECTED_VISUAL_CONCEALED = {
    1621,
    1676,
    1700,
    2243,
    2244,
    2663,
    3102,
    3103,
    8839,
    8844,
}
EXPECTED_VISUAL_IMMUTABLE = {
    1613,
    1617,
    1619,
    1623,
    1696,
    3065,
    3066,
    8699,
    8700,
}
EXPECTED_BRIDGE_CONCEALED = {
    1439,
    1574,
    1580,
    1586,
    1587,
    1589,
    1610,
    1658,
    1675,
    1677,
    1709,
    2964,
    3084,
    3089,
    3111,
    3129,
    7483,
    8779,
    8811,
    8817,
    8840,
    8843,
    8855,
}
EXPECTED_BRIDGE_IMMUTABLE = {2909, 2911}
EXPECTED_BRIDGE_UNRESOLVED = {12515}


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
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def flatten_visual_group(group):
    return {
        int(face_id)
        for face_ids in group.values()
        for face_id in face_ids
    }


def visual_overrides(authority):
    if authority.get("status") != "DONE_SOURCE_FACE_CLASSIFICATION_V26":
        raise RuntimeError(
            f"{OPERATION}: face-visual classification is not DONE; "
            f"status={authority.get('status')!r}"
        )
    classifications = authority["classifications"]
    concealed = flatten_visual_group(
        classifications["concealed_wearer_side_removable"]
    )
    immutable = flatten_visual_group(
        classifications["visible_silhouette_rim_opening_immutable"]
    )
    unresolved = {
        int(face_id) for face_id in classifications["unresolved"]
    }
    if concealed != EXPECTED_VISUAL_CONCEALED:
        raise RuntimeError(
            f"{OPERATION}: concealed/removable face contract mismatch; "
            f"expected={sorted(EXPECTED_VISUAL_CONCEALED)}, "
            f"observed={sorted(concealed)}"
        )
    if immutable != EXPECTED_VISUAL_IMMUTABLE:
        raise RuntimeError(
            f"{OPERATION}: visible immutable face contract mismatch; "
            f"expected={sorted(EXPECTED_VISUAL_IMMUTABLE)}, "
            f"observed={sorted(immutable)}"
        )
    if unresolved:
        raise RuntimeError(
            f"{OPERATION}: unresolved reviewed faces remain: "
            f"{sorted(unresolved)}"
        )
    if concealed & immutable:
        raise RuntimeError(
            f"{OPERATION}: face-visual classes overlap: "
            f"{sorted(concealed & immutable)}"
        )
    counts = authority["counts"]
    if (
        int(counts["concealed_wearer_side_removable"]),
        int(counts["visible_silhouette_rim_opening_immutable"]),
        int(counts["unresolved"]),
    ) != (10, 9, 0):
        raise RuntimeError(
            f"{OPERATION}: face-visual count contract mismatch: {counts}"
        )
    return concealed, immutable


def bridge_visual_overrides(authority):
    expected_status = "DONE_BRIDGE_SOURCE_FACE_CLASSIFICATION_ROUND_01_V26"
    if authority.get("status") != expected_status:
        raise RuntimeError(
            f"{OPERATION}: bridge visual classification is not DONE; "
            f"expected={expected_status!r}, "
            f"status={authority.get('status')!r}"
        )
    classifications = authority["classifications"]
    concealed = flatten_visual_group(
        classifications["concealed_wearer_side_removable"]
    )
    immutable = flatten_visual_group(
        classifications["visible_silhouette_rim_opening_immutable"]
    )
    unresolved = flatten_visual_group(classifications["unresolved"])
    observed = (concealed, immutable, unresolved)
    expected = (
        EXPECTED_BRIDGE_CONCEALED,
        EXPECTED_BRIDGE_IMMUTABLE,
        EXPECTED_BRIDGE_UNRESOLVED,
    )
    if observed != expected:
        raise RuntimeError(
            f"{OPERATION}: bridge visual exact-set contract mismatch; "
            f"expected={tuple(sorted(values) for values in expected)}, "
            f"observed={tuple(sorted(values) for values in observed)}"
        )
    if concealed & (immutable | unresolved) or immutable & unresolved:
        raise RuntimeError(
            f"{OPERATION}: bridge visual classes overlap; "
            f"concealed={sorted(concealed)}, immutable={sorted(immutable)}, "
            f"unresolved={sorted(unresolved)}"
        )
    counts = authority["counts"]
    if (
        int(counts["concealed_wearer_side_removable"]),
        int(counts["visible_silhouette_rim_opening_immutable"]),
        int(counts["unresolved"]),
    ) != (23, 2, 1):
        raise RuntimeError(
            f"{OPERATION}: bridge visual count contract mismatch: {counts}"
        )
    return concealed, immutable, unresolved


def preserve_pre_visual_authority(output):
    if not output.exists():
        return
    current_hash = sha_file(output)
    current = read_json(output)
    current_visual_hash = (
        current.get("source_authorities", {})
        .get("face_visual_classification", {})
        .get("sha256")
    )
    if current_visual_hash == EXPECTED_HASHES["face_visual_classification"]:
        return
    if current_hash != PRE_VISUAL_OUTPUT_SHA256:
        raise RuntimeError(
            f"{OPERATION}: existing output has an unknown pre-contract hash; "
            f"target={output}, expected={PRE_VISUAL_OUTPUT_SHA256}, "
            f"actual={current_hash}"
        )
    if PRE_VISUAL_STALE_PATH.exists():
        stale_hash = sha_file(PRE_VISUAL_STALE_PATH)
        if stale_hash != PRE_VISUAL_OUTPUT_SHA256:
            raise RuntimeError(
                f"{OPERATION}: stale-history target already exists with the "
                f"wrong hash; target={PRE_VISUAL_STALE_PATH}, "
                f"expected={PRE_VISUAL_OUTPUT_SHA256}, actual={stale_hash}"
            )
        return
    shutil.copy2(output, PRE_VISUAL_STALE_PATH)
    stale_hash = sha_file(PRE_VISUAL_STALE_PATH)
    if stale_hash != PRE_VISUAL_OUTPUT_SHA256:
        raise RuntimeError(
            f"{OPERATION}: failed to preserve byte-exact pre-visual authority; "
            f"target={PRE_VISUAL_STALE_PATH}, "
            f"expected={PRE_VISUAL_OUTPUT_SHA256}, actual={stale_hash}"
        )


def preserve_pre_bridge_authority(output):
    if not output.exists():
        return
    current_hash = sha_file(output)
    current = read_json(output)
    current_bridge_hash = (
        current.get("source_authorities", {})
        .get("bridge_visual_classification", {})
        .get("sha256")
    )
    if current_bridge_hash == EXPECTED_HASHES["bridge_visual_classification"]:
        return
    if current_hash != PRE_BRIDGE_OUTPUT_SHA256:
        raise RuntimeError(
            f"{OPERATION}: existing output has an unknown pre-bridge hash; "
            f"target={output}, expected={PRE_BRIDGE_OUTPUT_SHA256}, "
            f"actual={current_hash}"
        )
    if PRE_BRIDGE_STALE_PATH.exists():
        stale_hash = sha_file(PRE_BRIDGE_STALE_PATH)
        if stale_hash != PRE_BRIDGE_OUTPUT_SHA256:
            raise RuntimeError(
                f"{OPERATION}: pre-bridge stale target has the wrong hash; "
                f"target={PRE_BRIDGE_STALE_PATH}, "
                f"expected={PRE_BRIDGE_OUTPUT_SHA256}, actual={stale_hash}"
            )
        return
    shutil.copy2(output, PRE_BRIDGE_STALE_PATH)
    stale_hash = sha_file(PRE_BRIDGE_STALE_PATH)
    if stale_hash != PRE_BRIDGE_OUTPUT_SHA256:
        raise RuntimeError(
            f"{OPERATION}: failed to preserve byte-exact pre-bridge authority; "
            f"target={PRE_BRIDGE_STALE_PATH}, "
            f"expected={PRE_BRIDGE_OUTPUT_SHA256}, actual={stale_hash}"
        )


def edge_pairs(face):
    return [
        tuple(sorted((int(face[index]), int(face[(index + 1) % len(face)]))))
        for index in range(len(face))
    ]


def source_geometry(cells):
    faces = {}
    coordinates = {}
    component_faces = {}
    for component in ("C20", "C9"):
        component_faces[component] = set()
        for cell in cells["atomic_cells"][component]:
            for source_id, point in cell["vertex_coordinates_mm"].items():
                vertex_id = int(source_id)
                value = [float(item) for item in point]
                if vertex_id in coordinates and coordinates[vertex_id] != value:
                    raise RuntimeError(
                        f"{OPERATION}: vertex {vertex_id} has conflicting "
                        "checkpointed coordinates"
                    )
                coordinates[vertex_id] = value
            for record in cell["faces"]:
                face_id = int(record["source_face_id"])
                topology = [
                    int(value) for value in record["loop_source_vertex_ids"]
                ]
                if face_id in faces and faces[face_id] != topology:
                    raise RuntimeError(
                        f"{OPERATION}: face {face_id} has conflicting topology"
                    )
                faces[face_id] = topology
                component_faces[component].add(face_id)
    return faces, coordinates, component_faces


def all_joint_faces(joint):
    result = {}
    for mask in joint["masks"].values():
        for record in mask.get("faces", []):
            face_id = int(record["source_face_id"])
            topology = [
                int(value) for value in record["loop_source_vertex_ids"]
            ]
            if face_id in result and result[face_id] != topology:
                raise RuntimeError(
                    f"{OPERATION}: joint face {face_id} has conflicting topology"
                )
            result[face_id] = topology
    return result


def compact_exposure_projection(path):
    program = """
[
  .exposure | to_entries[] as $cell |
  $cell.value.faces[] |
  {
    old_cell_id: $cell.key,
    component: $cell.value.component,
    source_face_id,
    classification,
    class_reasons,
    sample_count,
    unobstructed_cutter_ratio,
    normal_sign_agreement_ratio,
    immutable_prism_exit_sample_count
  }
]
"""
    try:
        completed = subprocess.run(
            ["jq", "-c", program, str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            f"{OPERATION}: jq is required to project the 315 MiB exposure "
            "ledger without loading it into Python memory"
        ) from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"{OPERATION}: jq exposure projection failed for {path}: "
            f"{error.stderr.strip()}"
        ) from error
    return json.loads(completed.stdout)


def exposure_records(compact_records):
    records = {}
    source_cells = {}
    for record in compact_records:
        face_id = int(record["source_face_id"])
        compact = {
            "source_face_id": face_id,
            "component": record["component"],
            "classification": record["classification"],
            "class_reasons": record["class_reasons"],
            "sample_count": int(record["sample_count"]),
            "unobstructed_cutter_ratio": float(
                record["unobstructed_cutter_ratio"]
            ),
            "normal_sign_agreement_ratio": float(
                record["normal_sign_agreement_ratio"]
            ),
            "immutable_prism_exit_sample_count": int(
                record["immutable_prism_exit_sample_count"]
            ),
        }
        compact["compact_exposure_record_fingerprint"] = stable_hash(compact)
        if face_id in records:
            raise RuntimeError(
                f"{OPERATION}: face {face_id} has duplicate exposure records"
            )
        records[face_id] = compact
        source_cells[face_id] = record["old_cell_id"]
    return records, source_cells


def adjacency_and_edges(faces, face_ids):
    edge_faces = defaultdict(list)
    for face_id in sorted(face_ids):
        for edge in edge_pairs(faces[face_id]):
            edge_faces[edge].append(face_id)
    adjacency = {face_id: set() for face_id in face_ids}
    for adjacent in edge_faces.values():
        for face_id in adjacent:
            adjacency[face_id].update(set(adjacent) - {face_id})
    return adjacency, edge_faces


def connected_components(face_ids, adjacency, blocked_pairs):
    remaining = set(face_ids)
    result = []
    while remaining:
        start = min(remaining)
        queue = deque([start])
        component = set()
        while queue:
            face_id = queue.popleft()
            if face_id not in remaining:
                continue
            remaining.remove(face_id)
            component.add(face_id)
            for neighbor in sorted(adjacency[face_id]):
                if neighbor not in remaining:
                    continue
                pair = tuple(sorted((face_id, neighbor)))
                if pair not in blocked_pairs:
                    queue.append(neighbor)
        result.append(sorted(component))
    return result


def boundary_components(edge_records):
    edge_by_vertices = {
        tuple(record["vertex_ids"]): record for record in edge_records
    }
    vertex_edges = defaultdict(set)
    for edge in edge_by_vertices:
        vertex_edges[edge[0]].add(edge)
        vertex_edges[edge[1]].add(edge)
    remaining = set(edge_by_vertices)
    result = []
    while remaining:
        seed = min(remaining)
        queue = deque([seed])
        connected = set()
        while queue:
            edge = queue.popleft()
            if edge not in remaining:
                continue
            remaining.remove(edge)
            connected.add(edge)
            for vertex in edge:
                queue.extend(sorted(vertex_edges[vertex] & remaining))
        degrees = defaultdict(int)
        for first, second in connected:
            degrees[first] += 1
            degrees[second] += 1
        endpoints = sorted(vertex for vertex, degree in degrees.items() if degree == 1)
        ordered_vertices = []
        if all(degree <= 2 for degree in degrees.values()):
            start = endpoints[0] if endpoints else min(degrees)
            current = start
            ordered_vertices = [current]
            used = set()
            while True:
                choices = sorted(
                    edge
                    for edge in vertex_edges[current] & connected
                    if edge not in used
                )
                if not choices:
                    break
                edge = choices[0]
                used.add(edge)
                following = edge[1] if edge[0] == current else edge[0]
                ordered_vertices.append(following)
                current = following
                if current == start:
                    break
            if len(used) != len(connected):
                ordered_vertices = []
        record = {
            "edge_vertex_pairs": [list(edge) for edge in sorted(connected)],
            "vertex_degrees": {
                str(vertex): degrees[vertex] for vertex in sorted(degrees)
            },
            "is_simple_path": bool(endpoints) and len(endpoints) == 2,
            "is_simple_loop": not endpoints and all(
                degree == 2 for degree in degrees.values()
            ),
            "ordered_vertex_ids": ordered_vertices,
        }
        record["fingerprint"] = stable_hash(record)
        result.append(record)
    return sorted(
        result,
        key=lambda record: (
            min(min(edge) for edge in record["edge_vertex_pairs"]),
            len(record["edge_vertex_pairs"]),
        ),
    )


def classify_seed_faces(face_ids, component, exposure, cell_by_face):
    records = []
    for face_id in sorted(set(int(value) for value in face_ids)):
        record = exposure.get(face_id)
        if record is None:
            state = "OUTSIDE_MAXIMUM_AUTHORITY"
            cell_id = None
            exposure_class = None
        elif record["component"] != component:
            state = "COMPONENT_MISMATCH"
            cell_id = None
            exposure_class = record["classification"]
        elif record["classification"] != "WEARER_FACING":
            state = "AMBIGUOUS_IMMUTABLE"
            cell_id = None
            exposure_class = record["classification"]
        else:
            state = "ELIGIBLE_MAPPED"
            cell_id = cell_by_face.get(face_id)
            exposure_class = record["classification"]
            if cell_id is None:
                state = "ELIGIBLE_UNCOVERED"
        records.append(
            {
                "source_face_id": face_id,
                "exposure_class": exposure_class,
                "mapping_state": state,
                "exposure_cell_id": cell_id,
            }
        )
    return records


def seed_summary(name, component, source_kind, records):
    states = defaultdict(list)
    for record in records:
        states[record["mapping_state"]].append(record["source_face_id"])
    eligible_cells = sorted(
        {
            record["exposure_cell_id"]
            for record in records
            if record["mapping_state"] == "ELIGIBLE_MAPPED"
        }
    )
    result = {
        "name": name,
        "component": component,
        "source_kind": source_kind,
        "face_records": records,
        "eligible_face_ids": states["ELIGIBLE_MAPPED"],
        "ambiguous_immutable_face_ids": states["AMBIGUOUS_IMMUTABLE"],
        "outside_maximum_authority_face_ids": states[
            "OUTSIDE_MAXIMUM_AUTHORITY"
        ],
        "eligible_uncovered_face_ids": states["ELIGIBLE_UNCOVERED"],
        "exposure_cell_ids": eligible_cells,
    }
    result["fingerprint"] = stable_hash(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    paths = {
        "joint_authority": JOINT_AUTHORITY,
        "cell_authority": CELL_AUTHORITY,
        "floor_authority": FLOOR_AUTHORITY,
        "floor_summary": FLOOR_SUMMARY,
        "face_visual_classification": FACE_VISUAL_CLASSIFICATION,
        "bridge_visual_classification": BRIDGE_VISUAL_CLASSIFICATION,
        "current_audit": CURRENT_AUDIT,
        "v22_attribution": V22_ATTRIBUTION,
    }
    hashes = {name: sha_file(path) for name, path in paths.items()}
    mismatches = {
        name: {"expected": EXPECTED_HASHES[name], "actual": value}
        for name, value in hashes.items()
        if value != EXPECTED_HASHES[name]
    }
    if mismatches:
        raise RuntimeError(
            f"{OPERATION}: source authority hash mismatch: {mismatches}"
        )

    joint = read_json(JOINT_AUTHORITY)
    old_cells = read_json(CELL_AUTHORITY)
    audit = read_json(CURRENT_AUDIT)
    v22 = read_json(V22_ATTRIBUTION)
    floor_summary = read_json(FLOOR_SUMMARY)
    face_visual = read_json(FACE_VISUAL_CLASSIFICATION)
    visual_concealed, visual_immutable = visual_overrides(face_visual)
    bridge_visual = read_json(BRIDGE_VISUAL_CLASSIFICATION)
    (
        bridge_concealed,
        bridge_immutable,
        bridge_unresolved,
    ) = bridge_visual_overrides(bridge_visual)
    compact_exposure = compact_exposure_projection(FLOOR_AUTHORITY)

    faces, coordinates, component_faces = source_geometry(old_cells)
    joint_faces = all_joint_faces(joint)
    exposure, old_cell_by_face = exposure_records(compact_exposure)
    base_exposure_labels = {
        face_id: record["classification"]
        for face_id, record in exposure.items()
    }
    reviewed_faces = (
        visual_concealed
        | visual_immutable
        | bridge_concealed
        | bridge_immutable
        | bridge_unresolved
    )
    missing_reviewed = reviewed_faces - set(exposure)
    if missing_reviewed:
        raise RuntimeError(
            f"{OPERATION}: reviewed faces are outside exposure authority: "
            f"{sorted(missing_reviewed)}"
        )
    unexpected_base_classes = {
        face_id: exposure[face_id]["classification"]
        for face_id in reviewed_faces
        if exposure[face_id]["classification"] != "EXTERIOR_OR_AMBIGUOUS"
    }
    if unexpected_base_classes:
        raise RuntimeError(
            f"{OPERATION}: reviewed override faces do not have the expected "
            f"ambiguous base class: {unexpected_base_classes}"
        )
    for face_id in sorted(reviewed_faces):
        record = exposure[face_id]
        record["base_classification"] = record["classification"]
        if face_id in visual_concealed:
            record["face_visual_contract"] = (
                "CONCEALED_WEARER_SIDE_REMOVABLE"
            )
            record["classification"] = "WEARER_FACING"
            record["class_reasons"] = [
                "REVIEWED_CONCEALED_WEARER_SIDE_REMOVABLE"
            ]
        elif face_id in visual_immutable:
            record["face_visual_contract"] = (
                "VISIBLE_SILHOUETTE_RIM_OPENING_IMMUTABLE"
            )
            record["classification"] = "EXTERIOR_OR_AMBIGUOUS"
            record["class_reasons"] = [
                "REVIEWED_VISIBLE_SILHOUETTE_RIM_OPENING_IMMUTABLE"
            ]
        elif face_id in bridge_concealed:
            record["bridge_visual_contract_round_01"] = (
                "CONCEALED_WEARER_SIDE_REMOVABLE"
            )
            record["classification"] = "WEARER_FACING"
            record["class_reasons"] = [
                "BRIDGE_ROUND_01_CONCEALED_WEARER_SIDE_REMOVABLE"
            ]
        elif face_id in bridge_immutable:
            record["bridge_visual_contract_round_01"] = (
                "VISIBLE_SILHOUETTE_RIM_OPENING_IMMUTABLE"
            )
            record["classification"] = "EXTERIOR_OR_AMBIGUOUS"
            record["class_reasons"] = [
                "BRIDGE_ROUND_01_VISIBLE_IMMUTABLE"
            ]
        elif face_id in bridge_unresolved:
            record["bridge_visual_contract_round_01"] = (
                "UNRESOLVED_IMMUTABLE"
            )
            record["classification"] = "EXTERIOR_OR_AMBIGUOUS"
            record["class_reasons"] = [
                "BRIDGE_ROUND_01_UNRESOLVED_IMMUTABLE"
            ]
        record["post_visual_contract_fingerprint"] = stable_hash(record)
    changed_exposure_labels = {
        face_id
        for face_id, record in exposure.items()
        if record["classification"] != base_exposure_labels[face_id]
    }
    expected_changed_labels = visual_concealed | bridge_concealed
    if changed_exposure_labels != expected_changed_labels:
        raise RuntimeError(
            f"{OPERATION}: visual contract changed the wrong exposure labels; "
            f"expected={sorted(expected_changed_labels)}, "
            f"observed={sorted(changed_exposure_labels)}"
        )
    if set(exposure) != set(faces):
        raise RuntimeError(
            f"{OPERATION}: exposure/topology face mismatch; "
            f"missing exposure={sorted(set(faces) - set(exposure))}, "
            f"missing topology={sorted(set(exposure) - set(faces))}"
        )

    barrier_inventory = old_cells["barriers"]["inventory"]
    inventory_by_edge = {
        tuple(sorted(int(value) for value in record["vertex_ids"])): record
        for record in barrier_inventory
    }
    new_cells = []
    global_cell_by_face = {}
    exposure_seams = []
    immutable_complements = {}
    ordinal = {"C20": 0, "C9": 0}

    for component in ("C20", "C9"):
        maximum = component_faces[component]
        adjacency, edge_faces = adjacency_and_edges(faces, maximum)
        existing_barrier_face_pairs = set()
        for edge, adjacent in edge_faces.items():
            if edge not in inventory_by_edge:
                continue
            for first in adjacent:
                for second in adjacent:
                    if first < second:
                        existing_barrier_face_pairs.add((first, second))

        wearer = {
            face_id
            for face_id in maximum
            if exposure[face_id]["classification"] == "WEARER_FACING"
        }
        ambiguous = maximum - wearer
        exposure_barrier_pairs = set()
        for edge, adjacent in edge_faces.items():
            classes = {
                exposure[face_id]["classification"] for face_id in adjacent
            }
            if len(classes) <= 1:
                continue
            for first in adjacent:
                for second in adjacent:
                    if first < second:
                        exposure_barrier_pairs.add((first, second))
            exposure_seams.append(
                {
                    "component": component,
                    "vertex_ids": list(edge),
                    "source_edge_id": inventory_by_edge.get(edge, {}).get(
                        "source_edge_id"
                    ),
                    "adjacent_source_face_ids": sorted(adjacent),
                    "adjacent_exposure_classes": {
                        str(face_id): exposure[face_id]["classification"]
                        for face_id in sorted(adjacent)
                    },
                }
            )

        components = connected_components(
            wearer,
            adjacency,
            existing_barrier_face_pairs | exposure_barrier_pairs,
        )
        for cell_faces in sorted(components, key=lambda item: min(item)):
            name = f"EXPOSURE_CELL_{component}_{ordinal[component]:03d}"
            ordinal[component] += 1
            selected = set(cell_faces)
            vertex_ids = sorted(
                {vertex for face_id in cell_faces for vertex in faces[face_id]}
            )
            boundary_edges = []
            for edge, adjacent in sorted(edge_faces.items()):
                selected_adjacent = sorted(selected & set(adjacent))
                if not selected_adjacent:
                    continue
                if len(selected_adjacent) == len(adjacent) and len(adjacent) == 2:
                    continue
                other = sorted(set(adjacent) - selected)
                inventory = inventory_by_edge.get(edge)
                reasons = []
                if inventory:
                    reasons.extend(inventory["barrier_reasons"])
                if any(face_id in ambiguous for face_id in other):
                    reasons.append("EXPOSURE_CLASS_SEAM")
                if len(adjacent) == 1:
                    reasons.append("MAXIMUM_MASK_OPEN_BOUNDARY")
                boundary_edges.append(
                    {
                        "vertex_ids": list(edge),
                        "source_edge_id": (
                            inventory.get("source_edge_id") if inventory else None
                        ),
                        "selected_incident_face_ids": selected_adjacent,
                        "complement_incident_face_ids": other,
                        "barrier_reasons": sorted(set(reasons)),
                    }
                )
            complement = sorted(maximum - selected)
            record = {
                "name": name,
                "component": component,
                "source_face_ids": cell_faces,
                "source_vertex_ids": vertex_ids,
                "source_vertex_coordinates_mm": {
                    str(vertex): coordinates[vertex] for vertex in vertex_ids
                },
                "face_topology": [
                    {
                        "source_face_id": face_id,
                        "loop_source_vertex_ids": faces[face_id],
                        "exposure_evidence": exposure[face_id],
                        "prior_atomic_cell_id": old_cell_by_face[face_id],
                    }
                    for face_id in cell_faces
                ],
                "boundary_edge_records": boundary_edges,
                "boundary_components": boundary_components(boundary_edges),
                "complement_source_face_ids": complement,
                "complement_fingerprint": stable_hash(complement),
            }
            record["boundary_fingerprint"] = stable_hash(boundary_edges)
            record["fingerprint"] = stable_hash(record)
            new_cells.append(record)
            for face_id in cell_faces:
                if face_id in global_cell_by_face:
                    raise RuntimeError(
                        f"{OPERATION}: face {face_id} belongs to multiple cells"
                    )
                global_cell_by_face[face_id] = name

        immutable_complements[component] = {
            "ambiguous_source_face_ids": sorted(ambiguous),
            "ambiguous_face_count": len(ambiguous),
            "fingerprint": stable_hash(sorted(ambiguous)),
        }

    exposure_seams = sorted(
        exposure_seams,
        key=lambda record: (record["component"], record["vertex_ids"]),
    )
    for record in exposure_seams:
        record["fingerprint"] = stable_hash(record)

    observed_counts = {}
    for component in ("C20", "C9"):
        observed_counts[component] = {
            classification: sum(
                1
                for face_id in component_faces[component]
                if exposure[face_id]["classification"] == classification
            )
            for classification in (
                "WEARER_FACING",
                "EXTERIOR_OR_AMBIGUOUS",
            )
        }
    if observed_counts != EXPECTED_EXPOSURE_COUNTS:
        raise RuntimeError(
            f"{OPERATION}: exposure count mismatch; "
            f"expected={EXPECTED_EXPOSURE_COUNTS}, observed={observed_counts}"
        )

    barrier_cell_adjacency = []
    for component in ("C20", "C9"):
        _, edge_faces = adjacency_and_edges(
            faces, component_faces[component]
        )
        for edge, adjacent in sorted(edge_faces.items()):
            cell_ids = sorted(
                {
                    global_cell_by_face[face_id]
                    for face_id in adjacent
                    if face_id in global_cell_by_face
                }
            )
            if len(cell_ids) < 2:
                continue
            inventory = inventory_by_edge.get(edge)
            record = {
                "component": component,
                "cell_ids": cell_ids,
                "vertex_ids": list(edge),
                "source_edge_id": (
                    inventory.get("source_edge_id") if inventory else None
                ),
                "adjacent_source_face_ids": sorted(adjacent),
                "barrier_reasons": (
                    sorted(inventory["barrier_reasons"]) if inventory else []
                ),
            }
            record["fingerprint"] = stable_hash(record)
            barrier_cell_adjacency.append(record)

    visual_groups = face_visual["classifications"][
        "concealed_wearer_side_removable"
    ]
    gap_c20_faces = sorted(
        set(ELIGIBLE_GAP_FACES)
        | {int(face_id) for face_id in visual_groups["flex_gap_c20"]}
    )
    gap_c9_faces = sorted(
        int(face_id) for face_id in visual_groups["flex_gap_c9"]
    )
    seed_sets = []
    seed_sets.append(
        seed_summary(
            "ELIGIBLE_FLEX_GAP_C20_REMOVAL_SEEDS",
            "C20",
            (
                "seven exact authority-review faces plus reviewed concealed "
                "C20 flex-gap faces"
            ),
            classify_seed_faces(
                gap_c20_faces, "C20", exposure, global_cell_by_face
            ),
        )
    )
    seed_sets.append(
        seed_summary(
            "ELIGIBLE_FLEX_GAP_C9_REMOVAL_SEEDS",
            "C9",
            "reviewed concealed C9 flex-gap faces",
            classify_seed_faces(
                gap_c9_faces, "C9", exposure, global_cell_by_face
            ),
        )
    )

    for cluster in audit["component_20"]["clusters"]:
        vertex_ids = sorted(
            int(value) for value in cluster["vertex_margin_mm"].keys()
        )
        incident_faces = sorted(
            face_id
            for face_id, topology in joint_faces.items()
            if set(topology) & set(vertex_ids)
        )
        records = classify_seed_faces(
            incident_faces, "C20", exposure, global_cell_by_face
        )
        seed = seed_summary(
            f"C20_MAJOR_CLUSTER_{cluster['cluster']}_INCIDENT_SEEDS",
            "C20",
            "durable current-audit failure vertices and exact joint topology",
            records,
        )
        seed["failure_vertex_ids"] = vertex_ids
        seed["failure_vertex_margins_mm"] = cluster["vertex_margin_mm"]
        seed["incident_source_face_ids"] = incident_faces
        seed["vertex_count"] = len(vertex_ids)
        seed["incident_face_count"] = len(incident_faces)
        seed["fingerprint"] = stable_hash(seed)
        seed_sets.append(seed)
    c20_seed_counts = [
        (
            seed["vertex_count"],
            seed["incident_face_count"],
        )
        for seed in seed_sets
        if seed["name"].startswith("C20_MAJOR_CLUSTER_")
    ]
    if c20_seed_counts != [(87, 240), (31, 87)]:
        raise RuntimeError(
            f"{OPERATION}: durable C20 seed count mismatch; "
            f"observed={c20_seed_counts}"
        )

    proximal = v22["component_9_classification"]["proximal_wearer_facing"]
    proximal_faces = [int(value) for value in proximal["incident_face_ids"]]
    c9_records = classify_seed_faces(
        proximal_faces, "C9", exposure, global_cell_by_face
    )
    c9_seed = seed_summary(
        "C9_PROXIMAL_FAILURE_SEEDS",
        "C9",
        "exact V22 proximal collision-cluster incident faces",
        c9_records,
    )
    c9_seed["failure_vertex_ids"] = proximal["vertex_ids"]
    c9_seed["minimum_cutter_margin_mm"] = proximal[
        "minimum_cutter_margin_mm"
    ]
    c9_seed["fingerprint"] = stable_hash(c9_seed)
    seed_sets.append(c9_seed)
    if (
        len(c9_seed["failure_vertex_ids"]),
        len(proximal_faces),
    ) != (86, 238):
        raise RuntimeError(
            f"{OPERATION}: durable C9 proximal seed count mismatch; "
            f"vertices={len(c9_seed['failure_vertex_ids'])}, "
            f"faces={len(proximal_faces)}"
        )

    interface_faces = sorted(
        face_id
        for face_id, topology in joint_faces.items()
        if set(topology) & set(INTERFACE_C9_VERTICES)
    )
    interface_seed = seed_summary(
        "C9_INTERFACE_WITNESS_INCIDENT_SEEDS",
        "C9",
        "faces incident to exact C9 V1257/V1295 registration witnesses",
        classify_seed_faces(
            interface_faces, "C9", exposure, global_cell_by_face
        ),
    )
    interface_seed["interface_vertex_ids"] = INTERFACE_C9_VERTICES
    interface_seed["incident_source_face_ids"] = interface_faces
    interface_seed["fingerprint"] = stable_hash(interface_seed)
    seed_sets.append(interface_seed)

    required_cells = sorted(
        {
            cell_id
            for seed in seed_sets
            for cell_id in seed["exposure_cell_ids"]
        }
    )
    eligible_uncovered = sorted(
        {
            face_id
            for seed in seed_sets
            for face_id in seed["eligible_uncovered_face_ids"]
        }
    )
    eligible_faces = sorted(
        {
            face_id
            for seed in seed_sets
            for face_id in seed["eligible_face_ids"]
        }
    )
    mapped_faces = sorted(
        face_id for face_id in eligible_faces if face_id in global_cell_by_face
    )
    subset_exists = (
        bool(required_cells)
        and len(required_cells) <= MAXIMUM_SELECTED_CELLS
        and not eligible_uncovered
        and eligible_faces == mapped_faces
    )

    no_floor_count = int(
        floor_summary["ownership"]["declared_owner_counts"]["NO_FLOOR"]
    )
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": (
            "EXPOSURE_CELL_AUTHORITY_READY_V26"
            if subset_exists
            else "NO_SEED_COVERING_EXPOSURE_CELL_SUBSET_V26"
        ),
        "scope": (
            "read-only exposure-separated source cell graph and seed mapping; "
            "no terminal search, flex-gap placement, candidate geometry, "
            "mutation, Blend save, image work, or promotion"
        ),
        "source_authorities": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": hashes[name]}
            for name, path in paths.items()
        },
        "contract_revision": {
            "face_visual_classification_status": face_visual["status"],
            "concealed_wearer_side_removable_face_ids": sorted(
                visual_concealed
            ),
            "visible_silhouette_rim_opening_immutable_face_ids": sorted(
                visual_immutable
            ),
            "changed_base_exposure_label_face_ids": sorted(
                changed_exposure_labels
            ),
            "unchanged_reviewed_immutable_face_ids": sorted(visual_immutable),
            "all_unreviewed_exposure_labels_unchanged": all(
                exposure[face_id]["classification"]
                == base_exposure_labels[face_id]
                for face_id in set(exposure) - reviewed_faces
            ),
            "pre_visual_authority_history": {
                "path": str(PRE_VISUAL_STALE_PATH.relative_to(ROOT)),
                "sha256": PRE_VISUAL_OUTPUT_SHA256,
                "semantic_fingerprint": PRE_VISUAL_SEMANTIC_FINGERPRINT,
                "reason": "superseded by reviewed face-visual contract",
            },
            "bridge_classification_round_01": {
                "status": bridge_visual["status"],
                "concealed_wearer_side_removable_face_ids": sorted(
                    bridge_concealed
                ),
                "visible_immutable_face_ids": sorted(bridge_immutable),
                "unresolved_immutable_face_ids": sorted(bridge_unresolved),
                "additive_to_prior_visual_contract": True,
            },
            "pre_bridge_round_01_authority_history": {
                "path": str(PRE_BRIDGE_STALE_PATH.relative_to(ROOT)),
                "sha256": PRE_BRIDGE_OUTPUT_SHA256,
                "semantic_fingerprint": PRE_BRIDGE_SEMANTIC_FINGERPRINT,
                "reason": (
                    "superseded by reviewed bridge classification round 01"
                ),
            },
        },
        "code_sha256": sha_file(Path(__file__).resolve()),
        "barrier_contract": {
            "prior_barrier_edge_count": len(barrier_inventory),
            "exposure_class_seam_edge_count": len(exposure_seams),
            "exposure_class_seams": exposure_seams,
            "ambiguous_faces_are_immutable": True,
            "fingerprint": stable_hash(exposure_seams),
        },
        "barrier_separated_cell_graph": {
            "cell_ids": sorted(set(global_cell_by_face.values())),
            "barrier_adjacency_records": barrier_cell_adjacency,
            "barrier_adjacency_fingerprint": stable_hash(
                barrier_cell_adjacency
            ),
        },
        "exposure_cells": sorted(
            new_cells,
            key=lambda record: (
                record["component"],
                min(record["source_face_ids"]),
            ),
        ),
        "immutable_complements": immutable_complements,
        "seed_sets": seed_sets,
        "seed_covering_subset": {
            "exists": subset_exists,
            "maximum_cell_count": MAXIMUM_SELECTED_CELLS,
            "selected_cell_ids": required_cells,
            "selected_cell_count": len(required_cells),
            "eligible_seed_face_ids": eligible_faces,
            "eligible_seed_face_count": len(eligible_faces),
            "mapped_seed_face_ids": mapped_faces,
            "eligible_uncovered_face_ids": eligible_uncovered,
            "ambiguous_seed_faces_remain_immutable": True,
        },
        "no_floor_exclusion": {
            "excluded_from_all_seed_sets": True,
            "reason": (
                "NO_FLOOR is intentional openness outside selected local-cell "
                "footprints, not reconstruction demand"
            ),
            "non_gap_no_floor_sample_count": no_floor_count,
            "compact_evidence_fingerprint": stable_hash(
                {
                    "floor_authority_sha256": hashes["floor_authority"],
                    "floor_summary_sha256": hashes["floor_summary"],
                    "count": no_floor_count,
                }
            ),
        },
        "invariants": {
            "observed_exposure_counts": observed_counts,
            "all_cells_are_nonempty": all(
                record["source_face_ids"] for record in new_cells
            ),
            "all_cell_faces_are_wearer_facing": all(
                face["exposure_evidence"]["classification"] == "WEARER_FACING"
                for cell in new_cells
                for face in cell["face_topology"]
            ),
            "cell_face_membership_is_unique": len(global_cell_by_face)
            == sum(len(cell["source_face_ids"]) for cell in new_cells),
            "wearer_facing_partition_is_complete": set(global_cell_by_face)
            == {
                face_id
                for face_id, record in exposure.items()
                if record["classification"] == "WEARER_FACING"
            },
            "ambiguous_faces_in_no_cell": not (
                set(global_cell_by_face)
                & {
                    face_id
                    for face_id, record in exposure.items()
                    if record["classification"]
                    == "EXTERIOR_OR_AMBIGUOUS"
                }
            ),
            "no_floor_samples_are_not_seeds": True,
            "exactly_ten_visual_labels_changed_to_wearer_facing": (
                visual_concealed <= changed_exposure_labels
                and len(visual_concealed) == 10
            ),
            "nine_visible_reviewed_faces_remain_immutable": all(
                exposure[face_id]["classification"]
                == "EXTERIOR_OR_AMBIGUOUS"
                for face_id in visual_immutable
            ),
            "exactly_twenty_three_bridge_labels_changed_to_wearer_facing": (
                bridge_concealed <= changed_exposure_labels
                and len(bridge_concealed) == 23
            ),
            "two_bridge_visible_faces_remain_immutable": all(
                exposure[face_id]["classification"]
                == "EXTERIOR_OR_AMBIGUOUS"
                for face_id in bridge_immutable
            ),
            "unresolved_bridge_face_remains_immutable": all(
                exposure[face_id]["classification"]
                == "EXTERIOR_OR_AMBIGUOUS"
                for face_id in bridge_unresolved
            ),
            "exactly_thirty_three_additive_labels_changed": (
                changed_exposure_labels == expected_changed_labels
                and len(changed_exposure_labels) == 33
            ),
        },
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "terminal_search_started": False,
        "flex_gap_placement_started": False,
        "candidate_construction_started": False,
        "promotion": "NOT_REQUESTED",
    }
    report["semantic_fingerprint"] = stable_hash(report)
    if arguments.output.resolve() == OUTPUT.resolve():
        preserve_pre_visual_authority(arguments.output)
        preserve_pre_bridge_authority(arguments.output)
    atomic_json(arguments.output, report)
    print(
        f"DONE {OPERATION}: {len(new_cells)} wearer-facing cells; "
        f"seed-covering subset exists={subset_exists}; "
        f"selected cells={len(required_cells)}; output={arguments.output}"
    )


if __name__ == "__main__":
    main()
