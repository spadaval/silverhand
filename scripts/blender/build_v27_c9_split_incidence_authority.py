#!/usr/bin/env python3
"""Materialize the read-only C9 landing split-incidence topology authority."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402


OPERATION = "BUILD_V27_C9_SPLIT_INCIDENCE_AUTHORITY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
VISUAL_CLASSIFICATION = (
    V27 / "c9_expansion_face_visual/classification.json"
)
BOUNDARY_AUTHORITY = V27 / "v27_c9_landing_boundary_authority.json"
LANDING_AUTHORITY = V27 / "v27_c9_landing_authority.json"
AGGREGATE_AUTHORITY = V27 / "v27_aggregate_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_split_incidence_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_split_incidence_authority_receipt.json"
EXPECTED_HASHES = {
    "visual_classification": (
        VISUAL_CLASSIFICATION,
        "462cb09cb55aba274612363f6af8d2f7be23b966b88e1d1df867bcc37cfeb48c",
    ),
    "boundary_authority": (
        BOUNDARY_AUTHORITY,
        "83b7c5ed527f241a8e4e31b5e125ec395fd8c8ebe9cdc8bcce419bddd53079f6",
    ),
    "landing_authority": (
        LANDING_AUTHORITY,
        "c2529003261cf0f086c6de01bb700474fc6dfa3c016e03671cf928effa79dfc6",
    ),
    "aggregate_authority": (
        AGGREGATE_AUTHORITY,
        "43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338",
    ),
}
LANDING_FACE_IDS = [2227, 2228, 2230, 2231, 2232, 2235, 2239, 2240, 2243, 2244, 2245]
PRESELECTED_EXPANSION_FACE_IDS = [2229, 2283]
CONDITIONAL_EXPANSION_FACE_IDS = [2222, 2224, 2226, 2284]
VISIBLE_IMMUTABLE_FACE_IDS = [2220, 2221, 2225, 2233]
SPLIT_SOURCE_VERTEX_IDS = [1537, 1539, 1542]
BARRIER_EDGE_IDS = [10392, 12914, 12919]


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def symbolic_vertex(vertex_id: int, reconstructed: bool) -> str:
    if reconstructed and vertex_id in SPLIT_SOURCE_VERTEX_IDS:
        return f"VNEW_C9_INNER_SPLIT_FROM_{vertex_id}"
    return f"VSRC_{vertex_id}"


def main() -> None:
    args = arguments()
    verified_inputs = {}
    for label, (path, expected) in sorted(EXPECTED_HASHES.items()):
        actual = exact.sha_file(path)
        if actual != expected:
            raise RuntimeError(
                f"{OPERATION}: V27_C9_SPLIT_INPUT_HASH_MISMATCH; "
                f"input={label}; path={path}; expected={expected}; "
                f"actual={actual}"
            )
        verified_inputs[label] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual,
        }

    visual = exact.load_json(VISUAL_CLASSIFICATION)
    boundary = exact.load_json(BOUNDARY_AUTHORITY)
    landing_authority = exact.load_json(LANDING_AUTHORITY)
    aggregate = exact.load_json(AGGREGATE_AUTHORITY)
    if visual["summary"]["keep_immutable_face_ids"] != VISIBLE_IMMUTABLE_FACE_IDS:
        raise RuntimeError(
            f"{OPERATION}: visible immutable set mismatch; "
            f"expected={VISIBLE_IMMUTABLE_FACE_IDS}; "
            f"actual={visual['summary']['keep_immutable_face_ids']}"
        )
    if (
        visual["summary"]["conditional_expansion_candidate_face_ids"]
        != CONDITIONAL_EXPANSION_FACE_IDS
    ):
        raise RuntimeError(
            f"{OPERATION}: conditional expansion set mismatch; "
            f"expected={CONDITIONAL_EXPANSION_FACE_IDS}; "
            "actual="
            f"{visual['summary']['conditional_expansion_candidate_face_ids']}"
        )
    if (
        boundary["boundary"]["failing_vertex_ids"]
        != [1542, 1539, 1537]
    ):
        raise RuntimeError(
            f"{OPERATION}: failing boundary set mismatch; "
            f"actual={boundary['boundary']['failing_vertex_ids']}"
        )

    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = Path(landing_authority["source_scene"]["blend"]).resolve()
    if blend_path != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}; "
            f"actual={blend_path}"
        )
    source = bpy.data.objects.get(landing.SOURCE_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: source mesh {landing.SOURCE_OBJECT!r} is missing"
        )
    if not landing.matrix_is_identity(source.matrix_world):
        raise RuntimeError(
            f"{OPERATION}: source object matrix is not identity"
        )
    mesh = source.data

    reconstructed_faces = sorted(
        set(LANDING_FACE_IDS)
        | set(PRESELECTED_EXPANSION_FACE_IDS)
        | set(CONDITIONAL_EXPANSION_FACE_IDS)
    )
    visible_faces = set(VISIBLE_IMMUTABLE_FACE_IDS)
    selected_c9 = set(aggregate["aggregate_mask"]["source_face_ids"]["C9"])
    immutable_c9 = set(
        aggregate["aggregate_mask"][
            "immutable_complement_source_face_ids"
        ]["C9"]
    )
    if not set(PRESELECTED_EXPANSION_FACE_IDS) <= selected_c9:
        raise RuntimeError(
            f"{OPERATION}: preselected expansion faces are not all aggregate "
            f"selected; faces={PRESELECTED_EXPANSION_FACE_IDS}"
        )
    if not (
        set(CONDITIONAL_EXPANSION_FACE_IDS) | visible_faces
    ) <= immutable_c9:
        raise RuntimeError(
            f"{OPERATION}: reviewed ambiguous face sets do not remain within "
            "the frozen C9 immutable complement"
        )

    vertex_face_incidence: dict[int, set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        for vertex_id in polygon.vertices:
            vertex_face_incidence[int(vertex_id)].add(int(polygon.index))

    face_records = []
    for face_id in reconstructed_faces:
        source_vertices = [
            int(value) for value in mesh.polygons[face_id].vertices
        ]
        face_records.append(
            {
                "source_face_id": face_id,
                "source_vertex_ids": source_vertices,
                "candidate_symbolic_vertex_ids": [
                    symbolic_vertex(vertex_id, True)
                    for vertex_id in source_vertices
                ],
                "source_material_index": int(
                    mesh.polygons[face_id].material_index
                ),
                "winding_preserved": True,
                "authority_kind": (
                    "ORIGINAL_11_FACE_LANDING"
                    if face_id in LANDING_FACE_IDS
                    else "PRESELECTED_WEARER_SIDE_EXPANSION"
                    if face_id in PRESELECTED_EXPANSION_FACE_IDS
                    else "VISUALLY_REVIEWED_CONDITIONAL_INNER_EXPANSION"
                ),
            }
        )

    visible_records = []
    for face_id in VISIBLE_IMMUTABLE_FACE_IDS:
        source_vertices = [
            int(value) for value in mesh.polygons[face_id].vertices
        ]
        visible_records.append(
            {
                "source_face_id": face_id,
                "source_vertex_ids": source_vertices,
                "candidate_symbolic_vertex_ids": [
                    symbolic_vertex(vertex_id, False)
                    for vertex_id in source_vertices
                ],
                "source_material_index": int(
                    mesh.polygons[face_id].material_index
                ),
                "coordinates_topology_winding_and_material_immutable": True,
            }
        )

    split_records = []
    for vertex_id in SPLIT_SOURCE_VERTEX_IDS:
        incident = vertex_face_incidence[vertex_id]
        reconstruction_incident = sorted(incident & set(reconstructed_faces))
        visible_incident = sorted(incident & visible_faces)
        unaccounted = sorted(
            incident - set(reconstructed_faces) - visible_faces
        )
        if unaccounted or not reconstruction_incident or not visible_incident:
            raise RuntimeError(
                f"{OPERATION}: V27_C9_SPLIT_INCIDENCE_PARTITION_FAILED; "
                f"vertex={vertex_id}; reconstruction={reconstruction_incident}; "
                f"visible={visible_incident}; unaccounted={unaccounted}"
            )
        split_records.append(
            {
                "source_vertex_id": vertex_id,
                "source_coordinate_mm": [
                    float(value) for value in mesh.vertices[vertex_id].co
                ],
                "visible_symbolic_vertex_id": symbolic_vertex(vertex_id, False),
                "reconstructed_symbolic_vertex_id": symbolic_vertex(
                    vertex_id, True
                ),
                "reconstructed_incident_face_ids": reconstruction_incident,
                "visible_immutable_incident_face_ids": visible_incident,
                "unaccounted_incident_face_ids": [],
                "source_signed_cutter_margin_mm": next(
                    record["nearest_cutter"]["signed_distance_mm"]
                    for record in boundary["boundary"]["records"]
                    if record["vertex_id"] == vertex_id
                ),
            }
        )

    symbolic_edge_counts: Counter[tuple[str, str]] = Counter()
    symbolic_edge_sources: dict[tuple[str, str], set[int]] = defaultdict(set)
    for record in face_records:
        symbols = record["candidate_symbolic_vertex_ids"]
        source_vertices = record["source_vertex_ids"]
        for index, (first, second) in enumerate(
            zip(symbols, symbols[1:] + symbols[:1], strict=True)
        ):
            edge = tuple(sorted((first, second)))
            symbolic_edge_counts[edge] += 1
            source_edge_vertices = {
                source_vertices[index],
                source_vertices[(index + 1) % len(source_vertices)],
            }
            matching = [
                int(mesh_edge.index)
                for mesh_edge in mesh.edges
                if set(int(value) for value in mesh_edge.vertices)
                == source_edge_vertices
            ]
            if len(matching) != 1:
                raise RuntimeError(
                    f"{OPERATION}: source edge resolution failed; "
                    f"face={record['source_face_id']}; "
                    f"vertices={sorted(source_edge_vertices)}; matches={matching}"
                )
            symbolic_edge_sources[edge].add(matching[0])

    barrier_records = []
    for edge_id in BARRIER_EDGE_IDS:
        edge = mesh.edges[edge_id]
        vertex_ids = [int(value) for value in edge.vertices]
        barrier_records.append(
            {
                "source_edge_id": edge_id,
                "source_vertex_ids": vertex_ids,
                "source_coordinates_mm": [
                    [float(value) for value in mesh.vertices[vertex_id].co]
                    for vertex_id in vertex_ids
                ],
                "split_vertex_incidence": sorted(
                    set(vertex_ids) & set(SPLIT_SOURCE_VERTEX_IDS)
                ),
                "must_remain_exact": True,
            }
        )
    if any(record["split_vertex_incidence"] for record in barrier_records):
        raise RuntimeError(
            f"{OPERATION}: V27_C9_SPLIT_TOUCHES_EXACT_BARRIER_EDGE; "
            f"records={barrier_records}"
        )

    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": "V27_C9_SPLIT_INCIDENCE_AUTHORITY_CHECKPOINTED",
        "scope": (
            "read-only symbolic topology partition; no mesh mutation, "
            "candidate geometry, Blend save, image work, Gate B/D, or "
            "promotion"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": verified_inputs,
        "source_scene": {
            "blend": str(blend_path),
            "source_object": source.name,
            "source_matrix_identity": True,
        },
        "reconstruction_authority": {
            "source_face_ids": reconstructed_faces,
            "source_face_count": len(reconstructed_faces),
            "face_records": face_records,
            "preselected_expansion_face_ids": PRESELECTED_EXPANSION_FACE_IDS,
            "conditional_expansion_face_ids": (
                CONDITIONAL_EXPANSION_FACE_IDS
            ),
            "protected_visible_face_ids": VISIBLE_IMMUTABLE_FACE_IDS,
            "split_source_vertex_ids": SPLIT_SOURCE_VERTEX_IDS,
            "split_records": split_records,
            "symbolic_boundary_edges": [
                {
                    "symbolic_vertex_ids": list(edge),
                    "source_edge_ids": sorted(symbolic_edge_sources[edge]),
                }
                for edge, count in sorted(symbolic_edge_counts.items())
                if count == 1
            ],
            "symbolic_boundary_edge_count": sum(
                count == 1 for count in symbolic_edge_counts.values()
            ),
            "barrier_records": barrier_records,
            "protected_source_open_route": {
                "incident_source_face_id": 2283,
                "constraint": (
                    "remain empty and unchanged; never bridge, fill, or narrow"
                ),
            },
            "candidate_endpoint_target": {
                "source_vertex_ids": list(landing.TARGET_VERTEX_IDS),
                "moved_coordinates_mm": landing_authority["selection"][
                    "moved_endpoint_coordinates_mm"
                ],
                "minimum_exact_edge_cutter_clearance_mm": (
                    landing_authority["selection"][
                        "exact_minimum_cutter_distance_mm"
                    ]
                ),
            },
        },
        "protected_visible_complement": {
            "face_records": visible_records,
            "face_count": len(visible_records),
            "may_reference_coordinates_as_boundary_constraints": True,
            "may_reassign_faces_to_split_vertices": False,
        },
        "invariants": {
            "all_input_hashes_match": True,
            "source_matrix_is_identity": True,
            "reconstruction_face_count_is_17": len(reconstructed_faces) == 17,
            "visible_face_count_is_4": len(visible_records) == 4,
            "split_vertex_count_is_3": len(split_records) == 3,
            "every_split_incidence_is_partitioned": True,
            "barrier_edges_do_not_use_split_vertices": True,
            "protected_route_remains_constraint_only": True,
            "source_mesh_not_mutated": True,
            "candidate_geometry_not_emitted": True,
        },
        "safety": {
            "mutation_started": False,
            "candidate_geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
            "gate_b_run": False,
            "gate_d_run": False,
        },
    }
    result["reconstruction_authority"]["fingerprint"] = exact.stable_hash(
        result["reconstruction_authority"]
    )
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": result["status"],
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "reconstruction_authority_fingerprint": result[
            "reconstruction_authority"
        ]["fingerprint"],
        "reconstruction_face_count": len(reconstructed_faces),
        "protected_visible_face_ids": VISIBLE_IMMUTABLE_FACE_IDS,
        "split_source_vertex_ids": SPLIT_SOURCE_VERTEX_IDS,
        "symbolic_boundary_edge_count": result["reconstruction_authority"][
            "symbolic_boundary_edge_count"
        ],
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
