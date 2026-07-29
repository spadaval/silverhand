"""Evaluate one face-aware ring-4 clearance reconstruction.

The exact outer transition, source-open route, and reviewed landmark chains
remain frozen. Only non-frozen ring-4 vertices may move. Violating vertices
are first placed at the 1.7 mm floor; cutter-overlapping sector triangles then
drive coordinated outward motion with bounded Laplacian regularization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    distribution,
    edge_ratio_distribution,
    evaluated_geometry,
    point_margins,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
    negative_orientation_locators,
    radial_coordinates,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    violation_clusters,
)
from try_boundary_preserving_cutter_reconstruction import (  # noqa: E402
    edge_faces,
    expand_face_rings,
    removed_open_boundary_edges,
    transition_edges,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    REVIEW_COLLECTION,
    clamp_to_reserved_wall,
    create_object,
    ensure_collection,
    mesh_audit,
    ordered_boundary_groups,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    audit_noncontiguous,
    validate_base,
)


OPERATION = "FACE_AWARE_SECTOR_RECONSTRUCTION"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
LANDMARKS_PATH = Path(
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_visual_landmarks/landmarks.json"
)
SECTOR_RINGS = 4
FLOOR_OFFSET_MM = 1.7
MAXIMUM_ITERATIONS = 120
OUTWARD_STEP_MM = 0.25
REGULARIZATION_FACTOR = 0.12


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-base-sha256",
        default=EXPECTED_BASE_SHA256,
    )
    parser.add_argument(
        "--required-base-shape-key",
        default=EXPECTED_BASE_SHAPE_KEY,
    )
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(sys.argv[separator + 1 :])


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_landmarks() -> tuple[dict, set[int], set[int]]:
    path = (Path.cwd() / LANDMARKS_PATH).resolve()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{OPERATION}: cannot read landmark authority '{path}': {error}"
        ) from error
    boundary = document.get("recommended_authored_patch_boundary")
    if not isinstance(boundary, dict):
        raise RuntimeError(
            f"{OPERATION}: landmark authority '{path}' has no recommended "
            "authored patch boundary"
        )
    if boundary.get("topology_rings") != SECTOR_RINGS:
        raise RuntimeError(
            f"{OPERATION}: landmark authority selects rings "
            f"{boundary.get('topology_rings')}, expected {SECTOR_RINGS}"
        )
    frozen_vertices = set()
    frozen_edges = set()
    for landmark in boundary.get("preserve_exactly", []):
        frozen_vertices.update(landmark.get("vertex_chain", []))
        frozen_edges.update(landmark.get("edge_chain", []))
    return document, frozen_vertices, frozen_edges


def geometry_fingerprint(points: list[Vector], ids: list[int]) -> str:
    digest = hashlib.sha256()
    for index in ids:
        digest.update(struct.pack("<Qddd", index, *points[index]))
    return digest.hexdigest()


def topology_record(
    before_obj: bpy.types.Object,
    after_obj: bpy.types.Object,
) -> dict:
    before = mesh_audit(before_obj)
    after = mesh_audit(after_obj)
    before_winding = audit_noncontiguous(before_obj)
    after_winding = audit_noncontiguous(after_obj)
    return {
        "before": before,
        "after": after,
        "connected_component_delta": (
            after["connected_components"] - before["connected_components"]
        ),
        "boundary_edge_delta": (
            after["boundary_edges"] - before["boundary_edges"]
        ),
        "nonmanifold_edge_delta": (
            after["nonmanifold_edges"] - before["nonmanifold_edges"]
        ),
        "noncontiguous_manifold_edge_delta": (
            after_winding["noncontiguous_manifold_edges"]
            - before_winding["noncontiguous_manifold_edges"]
        ),
    }


def sector_overlap_faces(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
    sector_faces: set[int],
) -> tuple[list[tuple[int, int]], set[int]]:
    overlaps = overlap_pairs(
        points,
        faces,
        cutter_points,
        cutter_faces,
    )
    return overlaps, {
        first for first, _ in overlaps if first in sector_faces
    }


def orientation_safe(
    source: bpy.types.Object,
    before: list[Vector],
    after: list[Vector],
    faces: list[tuple[int, ...]],
) -> bool:
    return (
        negative_orientation_locators(
            source,
            before,
            after,
            faces,
        )["count"]
        == 0
    )


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    repair_base = validate_base(
        candidate,
        args.required_base_sha256,
        args.required_base_shape_key,
    )
    landmarks, landmark_vertices, landmark_edge_ids = load_landmarks()
    vertex_component, components = connected_components(source)
    component = set(components[20])
    before, faces, material_indices = evaluated_geometry(candidate)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    clusters = violation_clusters(component, before_margins, neighbors)
    cluster = set(clusters[1])
    linked_faces = edge_faces(faces)
    component_faces = {
        index
        for index, face in enumerate(faces)
        if vertex_component[face[0]] == 20
    }
    core_faces = {
        index
        for index in component_faces
        if any(vertex in cluster for vertex in faces[index])
    }
    sector_faces = expand_face_rings(
        core_faces,
        component_faces,
        linked_faces,
        SECTOR_RINGS,
    )
    sector_vertices = {
        vertex
        for face_index in sector_faces
        for vertex in faces[face_index]
    }
    transition_groups = ordered_boundary_groups(
        transition_edges(sector_faces, linked_faces)
    )
    open_groups = ordered_boundary_groups(
        removed_open_boundary_edges(sector_faces, linked_faces)
    )
    if (
        len(transition_groups) != 1
        or transition_groups[0][1]
        or len(open_groups) != 1
        or open_groups[0][1]
    ):
        raise RuntimeError(
            f"{OPERATION}: ring-4 boundary topology changed; transition="
            f"{[(len(v), c) for v, c in transition_groups]}, open="
            f"{[(len(v), c) for v, c in open_groups]}"
        )
    outer_chain = transition_groups[0][0]
    open_chain = open_groups[0][0]
    frozen_vertices = (
        set(outer_chain) | set(open_chain) | landmark_vertices
    )
    movable = sector_vertices - frozen_vertices
    if cluster - movable:
        conflicts = sorted(cluster - movable)
        raise RuntimeError(
            f"{OPERATION}: cluster vertices {conflicts} are frozen by outer, "
            "open, or reviewed landmark authority and cannot clear"
        )
    edge_by_id = {
        edge.index: tuple(edge.vertices) for edge in source.data.edges
    }
    invalid_edges = sorted(
        edge_id
        for edge_id in landmark_edge_ids
        if edge_id not in edge_by_id
    )
    if invalid_edges:
        raise RuntimeError(
            f"{OPERATION}: frozen landmark edge IDs {invalid_edges} are "
            "missing from immutable source"
        )

    after = [point.copy() for point in before]
    for index in movable:
        if before_margins[index] < FLOOR_OFFSET_MM - TOLERANCE_MM:
            after[index] = clamp_to_reserved_wall(
                after[index],
                target_length,
                grid,
                FLOOR_OFFSET_MM,
            )
    before_overlaps, before_sector_overlap_faces = sector_overlap_faces(
        before,
        faces,
        cutter_points,
        cutter_faces,
        sector_faces,
    )
    history = []
    converged = False
    blocker = None
    for iteration in range(MAXIMUM_ITERATIONS + 1):
        overlaps, overlapping_sector_faces = sector_overlap_faces(
            after,
            faces,
            cutter_points,
            cutter_faces,
            sector_faces,
        )
        margins = point_margins(after, target_length, grid)
        cluster_failures = [
            index
            for index in cluster
            if margins[index] < FLOOR_OFFSET_MM - TOLERANCE_MM
        ]
        reversals = negative_orientation_locators(
            source,
            before,
            after,
            faces,
        )
        history.append(
            {
                "iteration": iteration,
                "global_overlaps": len(overlaps),
                "sector_overlap_faces": len(overlapping_sector_faces),
                "cluster_reserved_failures": len(cluster_failures),
                "negative_orientation_locators": reversals["count"],
            }
        )
        if (
            not cluster_failures
            and len(overlapping_sector_faces)
            <= len(before_sector_overlap_faces)
            and len(overlaps) <= len(before_overlaps)
            and reversals["count"] == 0
        ):
            converged = True
            break
        if iteration == MAXIMUM_ITERATIONS:
            blocker = (
                f"{OPERATION}: deterministic {MAXIMUM_ITERATIONS}-iteration "
                "limit reached without satisfying overlap/orientation gates"
            )
            break
        pushed_vertices = {
            vertex
            for face_index in overlapping_sector_faces
            for vertex in faces[face_index]
            if vertex in movable
        }
        if not pushed_vertices:
            blocker = (
                f"{OPERATION}: {len(overlapping_sector_faces)} overlapping "
                "ring-4 faces have no movable vertices after frozen controls"
            )
            break
        tentative = [point.copy() for point in after]
        for index in pushed_vertices:
            direction = radial_coordinates(
                tentative[index],
                target_length,
            )[3]
            tentative[index] += direction * OUTWARD_STEP_MM
        displacements = {
            index: tentative[index] - before[index] for index in movable
        }
        regularized = [point.copy() for point in tentative]
        for index in movable:
            local = [
                displacements[neighbor]
                for neighbor in neighbors[index]
                if neighbor in movable
            ]
            if not local:
                continue
            average = sum(local, Vector()) / len(local)
            regularized[index] = before[index] + displacements[index].lerp(
                average,
                REGULARIZATION_FACTOR,
            )
            regularized[index] = clamp_to_reserved_wall(
                regularized[index],
                target_length,
                grid,
                FLOOR_OFFSET_MM,
            )
        if orientation_safe(source, before, regularized, faces):
            after = regularized
        elif orientation_safe(source, before, tentative, faces):
            after = tentative
        else:
            blocker = (
                f"{OPERATION}: iteration {iteration + 1} outward face "
                "correction violates strict source-normal orientation"
            )
            break

    after_margins = point_margins(after, target_length, grid)
    after_overlaps, after_sector_overlap_faces = sector_overlap_faces(
        after,
        faces,
        cutter_points,
        cutter_faces,
        sector_faces,
    )
    orientations = negative_orientation_locators(
        source,
        before,
        after,
        faces,
    )
    cluster_failures = [
        index
        for index in cluster
        if after_margins[index] < FLOOR_OFFSET_MM - TOLERANCE_MM
    ]
    unchanged_ids = sorted(set(range(len(before))) - movable)
    before_fp = geometry_fingerprint(before, unchanged_ids)
    after_fp = geometry_fingerprint(after, unchanged_ids)
    frozen_displacements = {
        index: (after[index] - before[index]).length
        for index in sorted(frozen_vertices & sector_vertices)
        if (after[index] - before[index]).length > TOLERANCE_MM
    }
    affected = {
        index
        for index in movable
        if (after[index] - before[index]).length > TOLERANCE_MM
    }
    collection = ensure_collection(REVIEW_COLLECTION)
    before_obj = create_object(
        f"{args.prefix}_BEFORE",
        before,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    after_obj = create_object(
        f"{args.prefix}_AFTER",
        after,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    topology = topology_record(before_obj, after_obj)
    gate_pass = all(
        (
            converged,
            not cluster_failures,
            len(after_sector_overlap_faces)
            <= len(before_sector_overlap_faces),
            len(after_overlaps) <= len(before_overlaps),
            orientations["count"] == 0,
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edge_delta"] == 0,
            before_fp == after_fp,
            not frozen_displacements,
        )
    )
    displacements = [
        (after[index] - before[index]).length for index in affected
    ]
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if gate_pass
            else "evaluation_only_infeasible"
        ),
        "repair_base": repair_base,
        "landmarks": {
            "path": str(LANDMARKS_PATH),
            "sha256": sha256_file(LANDMARKS_PATH),
            "status": landmarks["status"],
            "frozen_landmark_vertex_ids": sorted(landmark_vertices),
            "frozen_landmark_edge_ids": sorted(landmark_edge_ids),
        },
        "selection": {
            "component": 20,
            "cluster": 1,
            "sector_rings": SECTOR_RINGS,
            "sector_face_ids": sorted(sector_faces),
            "sector_vertex_ids": sorted(sector_vertices),
            "outer_transition_vertex_ids": outer_chain,
            "source_open_vertex_ids": open_chain,
            "frozen_vertex_ids": sorted(frozen_vertices),
            "movable_vertex_ids": sorted(movable),
            "floor_offset_mm": FLOOR_OFFSET_MM,
        },
        "solver": {
            "maximum_iterations": MAXIMUM_ITERATIONS,
            "outward_step_mm": OUTWARD_STEP_MM,
            "regularization_factor": REGULARIZATION_FACTOR,
            "history": history,
            "converged": converged,
            "blocker": blocker,
        },
        "clearance": {
            "cluster_reserved_failure_ids": cluster_failures,
            "before_sector_overlap_faces": len(
                before_sector_overlap_faces
            ),
            "after_sector_overlap_faces": len(after_sector_overlap_faces),
            "before_global_overlaps": len(before_overlaps),
            "after_global_overlaps": len(after_overlaps),
        },
        "distortion": {
            "affected_vertex_count": len(affected),
            "displacement_mm": (
                distribution(displacements) if displacements else None
            ),
            "affected_edge_ratio": edge_ratio_distribution(
                before,
                after,
                [tuple(edge.vertices) for edge in source.data.edges],
                affected,
            ),
            "negative_orientation": orientations,
        },
        "topology": topology,
        "preservation": {
            "outside_fingerprint_before": before_fp,
            "outside_fingerprint_after": after_fp,
            "outside_fingerprint_equal": before_fp == after_fp,
            "frozen_vertex_displacements_mm": frozen_displacements,
        },
        "gate_pass": gate_pass,
        "objects": {"before": before_obj.name, "after": after_obj.name},
        "qualitative_review": "PENDING",
        "promotion": "NOT_PROMOTED",
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: face-aware ring-4 reconstruction gate_pass={gate_pass}; "
        "promotion remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
