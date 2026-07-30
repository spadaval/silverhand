#!/usr/bin/env python3
"""Prove whether the fixed 11-face C9 landing boundary can clear the cutter."""

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


OPERATION = "ANALYZE_V27_C9_LANDING_BOUNDARY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
SURFACE_AUTHORITY = V27 / "v27_c9_landing_surface_authority.json"
EXPECTED_SURFACE_AUTHORITY_SHA256 = (
    "a1fbd4f844e423823a4852e0b6ecdaa9927069f0a013dc859d13d344891961e4"
)
DEFAULT_OUTPUT = V27 / "v27_c9_landing_boundary_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_landing_boundary_authority_receipt.json"


def ordered_loop(edges: list[tuple[int, int]]) -> list[int]:
    adjacency: dict[int, list[int]] = defaultdict(list)
    for first, second in edges:
        adjacency[first].append(second)
        adjacency[second].append(first)
    branched = {
        vertex_id: sorted(neighbors)
        for vertex_id, neighbors in adjacency.items()
        if len(neighbors) != 2
    }
    if branched:
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_BOUNDARY_NOT_SIMPLE; "
            f"degrees={branched}"
        )
    start = min(adjacency)
    loop = [start]
    previous = None
    current = start
    while True:
        choices = sorted(
            neighbor
            for neighbor in adjacency[current]
            if neighbor != previous
        )
        following = choices[0]
        if following == start:
            break
        if following in loop:
            raise RuntimeError(
                f"{OPERATION}: V27_C9_LANDING_BOUNDARY_REPEATS_VERTEX; "
                f"vertex={following}; partial_loop={loop}"
            )
        loop.append(following)
        previous, current = current, following
    if len(loop) != len(adjacency):
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_BOUNDARY_DISCONNECTED; "
            f"ordered={loop}; vertices={sorted(adjacency)}"
        )
    return loop


def main() -> None:
    actual_surface_hash = exact.sha_file(SURFACE_AUTHORITY)
    if actual_surface_hash != EXPECTED_SURFACE_AUTHORITY_SHA256:
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_BOUNDARY_INPUT_HASH_MISMATCH; "
            f"input={SURFACE_AUTHORITY}; "
            f"expected={EXPECTED_SURFACE_AUTHORITY_SHA256}; "
            f"actual={actual_surface_hash}"
        )
    surface = exact.load_json(SURFACE_AUTHORITY)
    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = Path(surface["source_scene"]["blend"]).resolve()
    if blend_path != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}; "
            f"actual={blend_path}"
        )
    source = bpy.data.objects.get(landing.SOURCE_OBJECT)
    cutter = bpy.data.objects.get(landing.CUTTER_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: source mesh {landing.SOURCE_OBJECT!r} is missing"
        )
    if cutter is None or cutter.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: cutter mesh {landing.CUTTER_OBJECT!r} is missing"
        )
    if not landing.matrix_is_identity(source.matrix_world):
        raise RuntimeError(
            f"{OPERATION}: source object matrix is not identity"
        )

    mesh = source.data
    face_mask = set(surface["candidate"]["landing_face_ids"])
    edge_counts: Counter[tuple[int, int]] = Counter()
    for face_id in sorted(face_mask):
        vertices = [int(value) for value in mesh.polygons[face_id].vertices]
        for first, second in zip(
            vertices, vertices[1:] + vertices[:1], strict=True
        ):
            edge_counts[tuple(sorted((first, second)))] += 1
    boundary_edges = sorted(
        edge for edge, count in edge_counts.items() if count == 1
    )
    loop = ordered_loop(boundary_edges)

    _, _, _, cutter_tree = landing.cutter_geometry(cutter)
    moved_coordinates = {
        vertex_id: coordinates
        for vertex_id, coordinates in zip(
            landing.TARGET_VERTEX_IDS,
            surface["candidate"]["moved_endpoint_coordinates_mm"],
            strict=True,
        )
    }
    vertex_face_incidence: dict[int, list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        for vertex_id in polygon.vertices:
            vertex_face_incidence[int(vertex_id)].append(int(polygon.index))

    records = []
    for vertex_id in loop:
        point = [
            float(value)
            for value in moved_coordinates.get(
                vertex_id, mesh.vertices[vertex_id].co
            )
        ]
        nearest = landing.nearest_cutter_record(cutter_tree, point)
        outside_incident = sorted(
            set(vertex_face_incidence[vertex_id]) - face_mask
        )
        records.append(
            {
                "vertex_id": vertex_id,
                "source_coordinate_mm": [
                    float(value) for value in mesh.vertices[vertex_id].co
                ],
                "candidate_coordinate_mm": point,
                "nearest_cutter": nearest,
                "passes_1_7_mm": (
                    nearest["signed_distance_mm"]
                    >= landing.MINIMUM_CLEARANCE_MM
                ),
                "outside_landing_mask_incident_face_ids": outside_incident,
            }
        )

    failing = [
        record for record in records if not record["passes_1_7_mm"]
    ]
    status = (
        "V27_C9_LANDING_FIXED_BOUNDARY_CLEAR"
        if not failing
        else "V27_C9_LANDING_MASK_EXPANSION_REQUIRED"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": (
            "read-only necessary fixed-boundary clearance test; no "
            "triangulation can satisfy the surface clearance gate when a "
            "retained boundary vertex itself is below 1.7 mm"
        ),
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": {
            "direct_surface_authority": {
                "path": str(SURFACE_AUTHORITY.relative_to(ROOT)),
                "sha256": actual_surface_hash,
            }
        },
        "source_scene": {
            "blend": str(blend_path),
            "source_object": source.name,
            "cutter_object": cutter.name,
        },
        "landing_face_ids": sorted(face_mask),
        "boundary": {
            "ordered_vertex_ids": loop,
            "ordered_edge_vertex_ids": [
                [loop[index], loop[(index + 1) % len(loop)]]
                for index in range(len(loop))
            ],
            "records": records,
            "failing_vertex_count": len(failing),
            "failing_vertex_ids": [
                record["vertex_id"] for record in failing
            ],
            "minimum_signed_margin_mm": min(
                record["nearest_cutter"]["signed_distance_mm"]
                for record in records
            ),
            "minimum_unsigned_distance_mm": min(
                record["nearest_cutter"]["unsigned_distance_mm"]
                for record in records
            ),
            "required_adjacent_face_ids_for_any_boundary_motion": sorted(
                {
                    face_id
                    for record in failing
                    for face_id in record[
                        "outside_landing_mask_incident_face_ids"
                    ]
                }
            ),
        },
        "invariants": {
            "surface_authority_hash_matches": True,
            "source_matrix_is_identity": True,
            "landing_boundary_is_one_simple_loop": True,
            "source_mesh_not_mutated": True,
            "candidate_geometry_not_emitted": True,
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
    result["semantic_fingerprint"] = exact.stable_hash(result)
    output = DEFAULT_OUTPUT.resolve()
    receipt_path = DEFAULT_RECEIPT.resolve()
    exact.atomic_json(output, result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(output),
        "authority_sha256": exact.sha_file(output),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "boundary_vertex_count": len(loop),
        "failing_vertex_count": len(failing),
        "failing_vertex_ids": result["boundary"]["failing_vertex_ids"],
        "minimum_signed_margin_mm": result["boundary"][
            "minimum_signed_margin_mm"
        ],
        "required_adjacent_face_ids_for_any_boundary_motion": result[
            "boundary"
        ]["required_adjacent_face_ids_for_any_boundary_motion"],
        "safety": result["safety"],
    }
    exact.atomic_json(receipt_path, receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
