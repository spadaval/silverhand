#!/usr/bin/env python3
"""Historical V27 evidence: partition the rejected micro-repair charts."""

from __future__ import annotations

from collections import defaultdict, deque
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import solve_v27_c9_split_surface_family as split_family  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402
from v27_historical_guard import require_historical_rerun  # noqa: E402


OPERATION = "BUILD_V27_C9_DIRECTIONAL_CHART_AUTHORITY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
MASK_AUTHORITY = V27 / "v27_c9_proximal_mask_boundary_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_directional_chart_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_directional_chart_authority_receipt.json"
EXPECTED_MASK_SHA256 = (
    "fcc3e370988a4f92b1c3d7932faaec8280b75899e29135c49df7d9dea28dee63"
)
MINIMUM_DIRECTION_DOT = 0.9659258262890683


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def connected_components(face_ids, adjacency):
    remaining = set(face_ids)
    components = []
    while remaining:
        seed = min(remaining)
        queue = deque([seed])
        remaining.remove(seed)
        component = []
        while queue:
            face_id = queue.popleft()
            component.append(face_id)
            for neighbor in sorted(adjacency[face_id] & remaining):
                remaining.remove(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda values: (min(values), len(values)))


def spherical_kmeans(face_ids, vectors, cluster_count):
    ordered = sorted(face_ids)
    centers = [vectors[ordered[0]].copy()]
    while len(centers) < cluster_count:
        candidate = max(
            ordered,
            key=lambda face_id: (
                min(
                    1.0 - vectors[face_id].dot(center)
                    for center in centers
                ),
                -face_id,
            ),
        )
        centers.append(vectors[candidate].copy())
    assignments = {}
    for _ in range(100):
        updated = {
            face_id: max(
                range(cluster_count),
                key=lambda index: (
                    vectors[face_id].dot(centers[index]),
                    -index,
                ),
            )
            for face_id in ordered
        }
        new_centers = []
        for index in range(cluster_count):
            members = [
                vectors[face_id]
                for face_id in ordered
                if updated[face_id] == index
            ]
            if not members:
                new_centers.append(centers[index])
                continue
            center = sum(members, Vector())
            new_centers.append(center.normalized())
        if updated == assignments and all(
            (new - old).length <= 1.0e-9
            for new, old in zip(new_centers, centers, strict=True)
        ):
            assignments = updated
            centers = new_centers
            break
        assignments = updated
        centers = new_centers
    return assignments, centers


def main():
    require_historical_rerun(OPERATION)
    args = arguments()
    actual_hash = exact.sha_file(MASK_AUTHORITY)
    if actual_hash != EXPECTED_MASK_SHA256:
        raise RuntimeError(
            f"{OPERATION}: mask authority hash mismatch; "
            f"expected={EXPECTED_MASK_SHA256}; actual={actual_hash}; "
            f"path={MASK_AUTHORITY}"
        )
    mask_authority = exact.load_json(MASK_AUTHORITY)
    mask = set(
        int(value)
        for value in mask_authority["necessary_clearance_closure"][
            "source_face_ids"
        ]
    )
    source = bpy.data.objects.get(landing.SOURCE_OBJECT)
    cutter = bpy.data.objects.get(landing.CUTTER_OBJECT)
    if source is None or source.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: source mesh missing; object={landing.SOURCE_OBJECT}"
        )
    if cutter is None or cutter.type != "MESH":
        raise RuntimeError(
            f"{OPERATION}: cutter mesh missing; object={landing.CUTTER_OBJECT}"
        )
    mesh = source.data
    context = split_family.cutter_context(cutter)
    vectors = {}
    face_edges = {}
    edge_faces = defaultdict(set)
    for face_id in sorted(mask):
        polygon = mesh.polygons[face_id]
        vertex_ids = [int(value) for value in polygon.vertices]
        centroid = sum(
            (mesh.vertices[value].co for value in vertex_ids), Vector()
        ) / len(vertex_ids)
        vectors[face_id] = split_family.nearest_frame(
            centroid, context
        )["outward"]
        edges = {
            tuple(sorted((first, second)))
            for first, second in zip(
                vertex_ids, vertex_ids[1:] + vertex_ids[:1], strict=True
            )
        }
        face_edges[face_id] = edges
        for edge in edges:
            edge_faces[edge].add(face_id)
    adjacency = {face_id: set() for face_id in mask}
    for faces in edge_faces.values():
        if len(faces) == 2:
            first, second = sorted(faces)
            adjacency[first].add(second)
            adjacency[second].add(first)

    candidates = []
    selection = None
    for cluster_count in range(2, 33):
        assignments, centers = spherical_kmeans(
            mask, vectors, cluster_count
        )
        chart_faces = []
        for cluster_id in range(cluster_count):
            members = {
                face_id
                for face_id, assignment in assignments.items()
                if assignment == cluster_id
            }
            chart_faces.extend(connected_components(members, adjacency))
        charts = []
        face_chart = {}
        for chart_id, faces in enumerate(chart_faces):
            direction = sum(
                (vectors[face_id] for face_id in faces), Vector()
            ).normalized()
            minimum_dot = min(
                vectors[face_id].dot(direction) for face_id in faces
            )
            for face_id in faces:
                face_chart[face_id] = chart_id
            charts.append(
                {
                    "chart_id": chart_id,
                    "source_face_ids": faces,
                    "face_count": len(faces),
                    "mean_exit_direction": split_family.point_record(
                        direction
                    ),
                    "minimum_face_direction_dot": minimum_dot,
                }
            )
        seam_edges = []
        external_edges = []
        for edge, faces in sorted(edge_faces.items()):
            if len(faces) == 1:
                external_edges.append(list(edge))
                continue
            first, second = sorted(faces)
            if face_chart[first] != face_chart[second]:
                seam_edges.append(
                    {
                        "source_vertex_ids": list(edge),
                        "first_face_id": first,
                        "second_face_id": second,
                        "first_chart_id": face_chart[first],
                        "second_chart_id": face_chart[second],
                    }
                )
        passes = all(
            chart["minimum_face_direction_dot"]
            >= MINIMUM_DIRECTION_DOT
            for chart in charts
        )
        candidate = {
            "requested_cluster_count": cluster_count,
            "connected_chart_count": len(charts),
            "charts": charts,
            "seam_edges": seam_edges,
            "seam_edge_count": len(seam_edges),
            "external_boundary_edges": external_edges,
            "external_boundary_edge_count": len(external_edges),
            "passes_direction_coherence": passes,
        }
        candidate["fingerprint"] = exact.stable_hash(candidate)
        candidates.append(candidate)
        if passes:
            selection = candidate
            break
    status = (
        "V27_C9_DIRECTIONAL_CHARTS_SELECTED"
        if selection is not None
        else "V27_C9_DIRECTIONAL_CHART_PARTITION_EXHAUSTED"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": "read-only directional partition of the final 253-face C9 proximal mask",
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_input": {
            "path": str(MASK_AUTHORITY.relative_to(ROOT)),
            "sha256": actual_hash,
        },
        "contract": {
            "minimum_face_direction_dot": MINIMUM_DIRECTION_DOT,
            "external_boundary_remains_exact": True,
            "internal_chart_seams_may_split_and_move": True,
            "seams_must_be_local_junctions_or_negative_space": True,
            "global_backing_carrier_forbidden": True,
        },
        "candidates": candidates,
        "selection": selection,
        "safety": {
            "source_mesh_not_mutated": True,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        },
    }
    result["semantic_fingerprint"] = exact.stable_hash(result)
    exact.atomic_json(args.output.resolve(), result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(args.output.resolve()),
        "authority_sha256": exact.sha_file(args.output.resolve()),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "selection_fingerprint": (
            selection["fingerprint"] if selection is not None else None
        ),
        "requested_cluster_count": (
            selection["requested_cluster_count"]
            if selection is not None
            else None
        ),
        "connected_chart_count": (
            selection["connected_chart_count"]
            if selection is not None
            else None
        ),
        "seam_edge_count": (
            selection["seam_edge_count"]
            if selection is not None
            else None
        ),
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
