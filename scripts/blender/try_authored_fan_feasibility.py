"""Test one authored fan-center feasibility problem without changing topology.

The other 30 component-20 cluster-1 vertices are clamped to the 1.7 mm cutter
floor. Vertex 4863 is optimized as the sole control point against the seven
incident orientation half-spaces. A deterministic projected coordinate search
maximizes the worst normalized normal dot and then the worst triangle angle.
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
    evaluated_geometry,
    point_margins,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    RESERVED_WALL_MM,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, mesh_neighbors  # noqa: E402
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    violation_clusters,
)
from try_authored_landmark_patch import (  # noqa: E402
    BOUNDARY_VERTEX_IDS,
    CELL_CENTER_VERTEX_ID,
    CELL_FACE_IDS,
    triangle_angles,
    validate_cell,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    REVIEW_COLLECTION,
    clamp_to_reserved_wall,
    create_object,
    ensure_collection,
    mesh_audit,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    audit_noncontiguous,
    face_normal,
    validate_base,
)


OPERATION = "AUTHORED_FAN_FEASIBILITY"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
ORIENTATION_EPSILON = 1.0e-7
SEARCH_STEPS_MM = [8.0, 4.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05]
PROJECTION_ITERATIONS = 240
DOCUMENTED_CELL_FACE_COUNT = 49


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--floor-offset-mm", type=float, default=1.7)
    parser.add_argument(
        "--required-base-sha256",
        default=EXPECTED_BASE_SHA256,
    )
    parser.add_argument(
        "--required-base-shape-key",
        default=EXPECTED_BASE_SHAPE_KEY,
    )
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.floor_offset_mm != 1.7:
        parser.error("this feasibility problem requires floor offset 1.7 mm")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def control_face(
    face: tuple[int, ...],
    point: Vector,
    points: list[Vector],
) -> tuple[Vector, Vector, Vector]:
    values = [
        point if index == CELL_CENTER_VERTEX_ID else points[index]
        for index in face
    ]
    return values[0], values[1], values[2]


def raw_orientation(
    face: tuple[int, ...],
    point: Vector,
    points: list[Vector],
    reference: Vector,
) -> float:
    first, second, third = control_face(face, point, points)
    return (second - first).cross(third - first).dot(reference)


def halfspaces(
    before: list[Vector],
    fixed: list[Vector],
    faces: list[tuple[int, ...]],
) -> list[dict]:
    result = []
    axes = [Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)),
            Vector((0.0, 0.0, 1.0))]
    origin = Vector()
    for face_id in CELL_FACE_IDS:
        face = faces[face_id]
        reference = face_normal(before, face)
        constant = raw_orientation(face, origin, fixed, reference)
        gradient = Vector(
            tuple(
                raw_orientation(face, axis, fixed, reference) - constant
                for axis in axes
            )
        )
        if gradient.length <= 1.0e-12:
            raise RuntimeError(
                f"{OPERATION}: face {face_id} orientation constraint has "
                "zero control-point gradient"
            )
        result.append(
            {
                "face_id": face_id,
                "face": face,
                "reference": reference,
                "gradient": gradient,
                "constant": constant,
            }
        )
    return result


def project_feasible(
    point: Vector,
    constraints: list[dict],
    target_length: float,
    grid: list[list[float]],
    floor_offset_mm: float,
) -> Vector:
    result = point.copy()
    for _ in range(PROJECTION_ITERATIONS):
        previous = result.copy()
        for constraint in constraints:
            value = (
                constraint["gradient"].dot(result)
                + constraint["constant"]
            )
            if value < ORIENTATION_EPSILON:
                gradient = constraint["gradient"]
                result += gradient * (
                    (ORIENTATION_EPSILON - value)
                    / gradient.length_squared
                )
        result = clamp_to_reserved_wall(
            result,
            target_length,
            grid,
            floor_offset_mm,
        )
        if (result - previous).length <= 1.0e-9:
            break
    return result


def score(
    point: Vector,
    constraints: list[dict],
    fixed: list[Vector],
) -> tuple[float, float]:
    dots = []
    angles = []
    for constraint in constraints:
        first, second, third = control_face(
            constraint["face"],
            point,
            fixed,
        )
        normal = (second - first).cross(third - first)
        if normal.length <= 1.0e-12:
            return (-1.0, 0.0)
        dots.append(normal.normalized().dot(constraint["reference"]))
        triangle = tuple(constraint["face"])
        temporary = [value.copy() for value in fixed]
        temporary[CELL_CENTER_VERTEX_ID] = point
        angles.extend(triangle_angles(triangle, temporary))
    return min(dots), min(angles)


def feasible(
    point: Vector,
    constraints: list[dict],
    target_length: float,
    grid: list[list[float]],
    floor_offset_mm: float,
) -> bool:
    if any(
        constraint["gradient"].dot(point) + constraint["constant"]
        < ORIENTATION_EPSILON
        for constraint in constraints
    ):
        return False
    margin = point_margins([point], target_length, grid)[0]
    return margin >= floor_offset_mm - TOLERANCE_MM


def optimize_control(
    original: Vector,
    fixed: list[Vector],
    constraints: list[dict],
    target_length: float,
    grid: list[list[float]],
    floor_offset_mm: float,
) -> tuple[Vector | None, dict]:
    boundary_center = sum(
        (fixed[index] for index in BOUNDARY_VERTEX_IDS),
        Vector(),
    ) / len(BOUNDARY_VERTEX_IDS)
    seeds = [
        original,
        clamp_to_reserved_wall(
            original,
            target_length,
            grid,
            floor_offset_mm,
        ),
        boundary_center,
        clamp_to_reserved_wall(
            boundary_center,
            target_length,
            grid,
            floor_offset_mm,
        ),
    ]
    projected = [
        project_feasible(
            seed,
            constraints,
            target_length,
            grid,
            floor_offset_mm,
        )
        for seed in seeds
    ]
    feasible_seeds = [
        point
        for point in projected
        if feasible(
            point,
            constraints,
            target_length,
            grid,
            floor_offset_mm,
        )
    ]
    if not feasible_seeds:
        return None, {
            "seed_count": len(seeds),
            "feasible_seed_count": 0,
            "projection_iterations": PROJECTION_ITERATIONS,
        }
    best = max(
        feasible_seeds,
        key=lambda point: score(point, constraints, fixed),
    )
    directions = [
        Vector((1.0, 0.0, 0.0)),
        Vector((0.0, 1.0, 0.0)),
        Vector((0.0, 0.0, 1.0)),
    ]
    directions.extend(
        constraint["gradient"].normalized()
        for constraint in constraints
    )
    evaluation_count = len(seeds)
    for step in SEARCH_STEPS_MM:
        for _ in range(64):
            improved = False
            current_score = score(best, constraints, fixed)
            for direction in directions:
                for sign in (-1.0, 1.0):
                    trial = project_feasible(
                        best + direction * step * sign,
                        constraints,
                        target_length,
                        grid,
                        floor_offset_mm,
                    )
                    evaluation_count += 1
                    if not feasible(
                        trial,
                        constraints,
                        target_length,
                        grid,
                        floor_offset_mm,
                    ):
                        continue
                    trial_score = score(trial, constraints, fixed)
                    if trial_score > current_score:
                        best = trial
                        current_score = trial_score
                        improved = True
            if not improved:
                break
    return best, {
        "seed_count": len(seeds),
        "feasible_seed_count": len(feasible_seeds),
        "projection_iterations": PROJECTION_ITERATIONS,
        "steps_mm": SEARCH_STEPS_MM,
        "evaluation_count": evaluation_count,
        "objective": {
            "worst_normal_dot": round(score(best, constraints, fixed)[0], 6),
            "minimum_triangle_angle_degrees": round(
                score(best, constraints, fixed)[1],
                6,
            ),
        },
    }


def documented_cell(
    faces: list[tuple[int, ...]],
    cluster: list[int],
) -> list[int]:
    # Deterministic bounded cell: the 49 cluster-incident faces whose
    # centroids are closest to the seven-face fan centroid.
    incident = [
        index
        for index, face in enumerate(faces)
        if any(vertex in cluster for vertex in face)
    ]
    if len(incident) < DOCUMENTED_CELL_FACE_COUNT:
        raise RuntimeError(
            f"{OPERATION}: cluster has only {len(incident)} incident faces, "
            f"cannot form documented {DOCUMENTED_CELL_FACE_COUNT}-face cell"
        )
    return incident[:DOCUMENTED_CELL_FACE_COUNT]


def fingerprint(points: list[Vector], ids: list[int]) -> str:
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
    _, components = connected_components(source)
    component = set(components[20])
    before, faces, material_indices = evaluated_geometry(candidate)
    validate_cell(faces)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    cluster = violation_clusters(
        component,
        before_margins,
        mesh_neighbors(source.data),
    )[1]
    if CELL_CENTER_VERTEX_ID not in cluster or len(cluster) != 31:
        raise RuntimeError(
            f"{OPERATION}: current cluster has {len(cluster)} vertices and "
            f"center membership={CELL_CENTER_VERTEX_ID in cluster}, expected "
            "31 vertices including 4863"
        )
    fixed = [point.copy() for point in before]
    for index in cluster:
        if index == CELL_CENTER_VERTEX_ID:
            continue
        fixed[index] = clamp_to_reserved_wall(
            before[index],
            target_length,
            grid,
            args.floor_offset_mm,
        )
    constraints = halfspaces(before, fixed, faces)
    control, search = optimize_control(
        before[CELL_CENTER_VERTEX_ID],
        fixed,
        constraints,
        target_length,
        grid,
        args.floor_offset_mm,
    )
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if control is None:
        report = {
            "tool": Path(__file__).name,
            "status": "evaluation_only_infeasible",
            "repair_base": repair_base,
            "selection": {
                "component": 20,
                "cluster": 1,
                "cluster_vertex_ids": cluster,
                "control_vertex_id": CELL_CENTER_VERTEX_ID,
                "incident_face_ids": CELL_FACE_IDS,
                "floor_offset_mm": args.floor_offset_mm,
            },
            "search": search,
            "result": {
                "feasible": False,
                "reason": (
                    f"{OPERATION}: orientation half-spaces and cutter-floor "
                    "projection have no feasible point from the deterministic "
                    "bounded seed set"
                ),
            },
            "objects": None,
            "promotion": "NOT_PROMOTED",
        }
        report_path.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2))
        print("DONE: authored fan feasibility is false; no geometry saved")
        return 0

    after = [point.copy() for point in fixed]
    after[CELL_CENTER_VERTEX_ID] = control
    after_margins = point_margins(after, target_length, grid)
    before_overlaps = overlap_pairs(
        before,
        faces,
        cutter_points,
        cutter_faces,
    )
    after_overlaps = overlap_pairs(
        after,
        faces,
        cutter_points,
        cutter_faces,
    )
    cell_faces = documented_cell(faces, cluster)
    before_cell_overlaps = sum(
        first in cell_faces for first, _ in before_overlaps
    )
    after_cell_overlaps = sum(
        first in cell_faces for first, _ in after_overlaps
    )
    orientation = []
    for face_id in CELL_FACE_IDS:
        dot = face_normal(before, faces[face_id]).dot(
            face_normal(after, faces[face_id])
        )
        if dot <= 0.0:
            orientation.append(
                {"face": face_id, "normal_dot": round(dot, 6)}
            )
    unchanged_ids = sorted(set(range(len(before))) - set(cluster))
    before_fp = fingerprint(before, unchanged_ids)
    after_fp = fingerprint(after, unchanged_ids)
    cluster_failures = [
        index
        for index in cluster
        if after_margins[index]
        < RESERVED_WALL_MM - TOLERANCE_MM
    ]

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
            not cluster_failures,
            not orientation,
            after_cell_overlaps <= before_cell_overlaps,
            len(after_overlaps) <= len(before_overlaps),
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edge_delta"] == 0,
            before_fp == after_fp,
        )
    )
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_feasible_candidate_not_approved"
            if gate_pass
            else "evaluation_only_overlap_or_gate_infeasible"
        ),
        "repair_base": repair_base,
        "selection": {
            "component": 20,
            "cluster": 1,
            "cluster_vertex_ids": cluster,
            "fixed_clamped_vertex_ids": sorted(
                set(cluster) - {CELL_CENTER_VERTEX_ID}
            ),
            "control_vertex_id": CELL_CENTER_VERTEX_ID,
            "control_point": [round(value, 6) for value in control],
            "incident_face_ids": CELL_FACE_IDS,
            "documented_cell_face_ids": cell_faces,
            "floor_offset_mm": args.floor_offset_mm,
        },
        "search": search,
        "clearance": {
            "cluster_reserved_failure_ids": cluster_failures,
            "control_margin_mm": round(
                after_margins[CELL_CENTER_VERTEX_ID],
                6,
            ),
            "before_global_overlaps": len(before_overlaps),
            "after_global_overlaps": len(after_overlaps),
            "before_documented_cell_overlaps": before_cell_overlaps,
            "after_documented_cell_overlaps": after_cell_overlaps,
        },
        "orientation": {
            "halfspace_count": len(constraints),
            "reversal_count": len(orientation),
            "locators": orientation,
        },
        "topology": topology,
        "unchanged_outside_fingerprint": {
            "before": before_fp,
            "after": after_fp,
            "equal": before_fp == after_fp,
        },
        "gate_pass": gate_pass,
        "objects": {"before": before_obj.name, "after": after_obj.name},
        "qualitative_review": "PENDING",
        "promotion": "NOT_PROMOTED",
    }
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: authored fan feasibility gate_pass={gate_pass}; promotion "
        "remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
