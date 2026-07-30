#!/usr/bin/env python3
"""Historical V27 evidence: exhaust the rejected harmonic micro-repair."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Vector
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import analyze_v27_c9_landing_surface as surface  # noqa: E402
import audit_v26_cutter_authority as cutter_audit  # noqa: E402
import solve_v27_c9_split_surface_family as split_family  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402
from v27_historical_guard import require_historical_rerun  # noqa: E402


OPERATION = "SOLVE_V27_C9_PROXIMAL_SURFACE_FAMILY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
MASK_AUTHORITY = V27 / "v27_c9_proximal_mask_boundary_authority.json"
AGGREGATE_AUTHORITY = V27 / "v27_aggregate_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_proximal_surface_family_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_proximal_surface_family_authority_receipt.json"
EXPECTED_HASHES = {
    "mask_authority": (
        MASK_AUTHORITY,
        "fcc3e370988a4f92b1c3d7932faaec8280b75899e29135c49df7d9dea28dee63",
    ),
    "aggregate_authority": (
        AGGREGATE_AUTHORITY,
        "43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338",
    ),
}
TARGET_CLEARANCES_MM = [1.7, 2.0, 2.5, 3.0, 4.0]
HARMONIC_WEIGHTS = [1_000_000, 128, 64, 32, 16, 8, 4, 2, 1]
MINIMUM_CLEARANCE_MM = 1.7
MINIMUM_EDGE_RATIO = 0.5
MAXIMUM_EDGE_RATIO = 2.0
MAXIMUM_ASPECT_RATIO = 12.0
TOLERANCE_MM = 1.0e-7


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def triangle_records(
    triangles: list[dict[str, Any]], coordinates: list[Vector]
) -> list[dict[str, Any]]:
    return [
        {
            **record,
            "points": tuple(
                coordinates[vertex_id] for vertex_id in record["vertex_ids"]
            ),
        }
        for record in triangles
    ]


def surface_metrics(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> dict[str, float]:
    minimum_dot = 1.0
    maximum_aspect = 0.0
    edge_ratios: dict[tuple[int, int], float] = {}
    for before, after in zip(baseline, candidate, strict=True):
        before_normal = surface.triangle_area_normal(before["points"])
        after_normal = surface.triangle_area_normal(after["points"])
        normal_dot = (
            -1.0
            if min(before_normal.length, after_normal.length) <= TOLERANCE_MM
            else before_normal.normalized().dot(after_normal.normalized())
        )
        minimum_dot = min(minimum_dot, normal_dot)
        maximum_aspect = max(
            maximum_aspect,
            surface.triangle_quality(after["points"])["aspect_ratio"],
        )
        for first, second in ((0, 1), (1, 2), (2, 0)):
            ids = tuple(sorted((
                after["vertex_ids"][first],
                after["vertex_ids"][second],
            )))
            if ids in edge_ratios:
                continue
            before_length = (
                before["points"][first] - before["points"][second]
            ).length
            after_length = (
                after["points"][first] - after["points"][second]
            ).length
            edge_ratios[ids] = (
                float("inf")
                if before_length <= TOLERANCE_MM
                else after_length / before_length
            )
    return {
        "minimum_normal_dot": minimum_dot,
        "minimum_edge_ratio": min(edge_ratios.values()),
        "maximum_edge_ratio": max(edge_ratios.values()),
        "maximum_triangle_aspect_ratio": maximum_aspect,
    }


def sampled_minimum_margin(
    records: list[dict[str, Any]], context: dict[str, Any]
) -> float:
    minimum = float("inf")
    for record in records:
        first, second, third = record["points"]
        samples = (
            first,
            second,
            third,
            (first + second) * 0.5,
            (second + third) * 0.5,
            (third + first) * 0.5,
            (first + second + third) / 3.0,
        )
        minimum = min(
            minimum,
            *(
                split_family.nearest_frame(point, context)[
                    "signed_margin_mm"
                ]
                for point in samples
            ),
        )
    return minimum


def keepout_hits(
    records: list[dict[str, Any]], cells: list[dict[str, Any]]
) -> set[str]:
    hits = set()
    for record in records:
        triangle = [
            split_family.point_record(point) for point in record["points"]
        ]
        for cell in cells:
            intersects, _ = exact.triangle_intersects_cell(
                triangle, cell["half_spaces"]
            )
            if intersects:
                hits.add(cell["cell_id"])
    return hits


def main() -> None:
    require_historical_rerun(OPERATION)
    args = arguments()
    verified = {}
    for label, (path, expected) in EXPECTED_HASHES.items():
        actual = exact.sha_file(path)
        if actual != expected:
            raise RuntimeError(
                f"{OPERATION}: input hash mismatch; input={label}; "
                f"path={path}; expected={expected}; actual={actual}"
            )
        verified[label] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual,
        }
    mask_authority = exact.load_json(MASK_AUTHORITY)
    closure = mask_authority["necessary_clearance_closure"]
    if not closure["passes_fixed_boundary_clearance"]:
        raise RuntimeError(
            f"{OPERATION}: fixed boundary is not clear; "
            f"authority={MASK_AUTHORITY}"
        )
    mask = set(int(value) for value in closure["source_face_ids"])
    boundary_ids = {
        int(value)
        for edge in closure["boundary_edges"]
        for value in edge
    }
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
    if not landing.matrix_is_identity(source.matrix_world):
        raise RuntimeError(f"{OPERATION}: source object matrix is not identity")
    mesh = source.data
    original = [vertex.co.copy() for vertex in mesh.vertices]
    mesh.calc_loop_triangles()
    patch_triangles = [
        {
            "triangle_id": int(triangle.index),
            "face_id": int(triangle.polygon_index),
            "vertex_ids": tuple(int(value) for value in triangle.vertices),
        }
        for triangle in mesh.loop_triangles
        if int(triangle.polygon_index) in mask
    ]
    complement_triangles = [
        {
            "triangle_id": int(triangle.index),
            "face_id": int(triangle.polygon_index),
            "vertex_ids": tuple(int(value) for value in triangle.vertices),
        }
        for triangle in mesh.loop_triangles
        if int(triangle.polygon_index) not in mask
    ]
    baseline_patch = triangle_records(patch_triangles, original)
    complement_records = triangle_records(complement_triangles, original)
    patch_vertex_ids = sorted(
        {
            vertex_id
            for triangle in patch_triangles
            for vertex_id in triangle["vertex_ids"]
        }
    )
    interior_ids = sorted(set(patch_vertex_ids) - boundary_ids)
    local_index = {
        vertex_id: index for index, vertex_id in enumerate(interior_ids)
    }
    adjacency = {vertex_id: set() for vertex_id in patch_vertex_ids}
    for triangle in patch_triangles:
        first, second, third = triangle["vertex_ids"]
        for start, end in ((first, second), (second, third), (third, first)):
            adjacency[start].add(end)
            adjacency[end].add(start)
    laplacian = np.zeros((len(interior_ids), len(interior_ids)))
    for vertex_id in interior_ids:
        row = local_index[vertex_id]
        laplacian[row, row] = len(adjacency[vertex_id])
        for neighbor in adjacency[vertex_id]:
            if neighbor in local_index:
                laplacian[row, local_index[neighbor]] -= 1.0

    context = split_family.cutter_context(cutter)
    frames = {
        vertex_id: split_family.nearest_frame(original[vertex_id], context)
        for vertex_id in interior_ids
    }
    aggregate = exact.load_json(AGGREGATE_AUTHORITY)
    negative = exact.load_json(
        ROOT / aggregate["verified_inputs"]["negative_space_authority"]["path"]
    )
    cells = exact.collect_keepout_cells(negative)
    baseline_keepouts = keepout_hits(baseline_patch, cells)
    baseline_complement = surface.overlap_audit(
        baseline_patch, complement_records, original, False
    )
    baseline_self = surface.overlap_audit(
        baseline_patch, baseline_patch, original, True
    )

    family_definition = {
        "target_clearances_mm": TARGET_CLEARANCES_MM,
        "harmonic_weights": HARMONIC_WEIGHTS,
        "ordering": "target clearance declaration order, then harmonic weight declaration order",
        "member_count": len(TARGET_CLEARANCES_MM) * len(HARMONIC_WEIGHTS),
        "mask_face_count": len(mask),
        "boundary_vertex_count": len(boundary_ids),
        "interior_vertex_count": len(interior_ids),
    }
    family_fingerprint = exact.stable_hash(family_definition)
    counts: Counter[str] = Counter()
    first_counterexamples: dict[str, Any] = {}
    best_sampled_counterexample = None
    selected = None
    evaluated = 0
    for target_clearance in TARGET_CLEARANCES_MM:
        direct = np.zeros((len(interior_ids), 3))
        for vertex_id in interior_ids:
            frame = frames[vertex_id]
            if frame["signed_margin_mm"] >= target_clearance:
                continue
            target = (
                frame["nearest_point"]
                + frame["outward"] * target_clearance
            )
            direct[local_index[vertex_id], :] = np.asarray(
                target - original[vertex_id]
            )
        for weight in HARMONIC_WEIGHTS:
            member_index = evaluated
            evaluated += 1
            system = laplacian + np.eye(len(interior_ids)) * weight
            displacement = np.linalg.solve(system, direct * weight)
            candidate = [point.copy() for point in original]
            for vertex_id in interior_ids:
                candidate[vertex_id] += Vector(
                    displacement[local_index[vertex_id], :].tolist()
                )
            records = triangle_records(patch_triangles, candidate)
            minimum_sampled = sampled_minimum_margin(records, context)
            if minimum_sampled < MINIMUM_CLEARANCE_MM - TOLERANCE_MM:
                reason = "SAMPLED_CUTTER_CLEARANCE_FAILED"
                counts[reason] += 1
                counterexample = {
                    "member_index": member_index,
                    "target_clearance_mm": target_clearance,
                    "harmonic_weight": weight,
                    "minimum_sampled_margin_mm": minimum_sampled,
                }
                first_counterexamples.setdefault(reason, counterexample)
                if (
                    best_sampled_counterexample is None
                    or minimum_sampled
                    > best_sampled_counterexample["minimum_sampled_margin_mm"]
                ):
                    best_sampled_counterexample = counterexample
                continue
            metrics = surface_metrics(baseline_patch, records)
            if metrics["minimum_normal_dot"] <= 0.0:
                reason = "ORIENTATION_FAILED"
            elif metrics["minimum_edge_ratio"] < MINIMUM_EDGE_RATIO:
                reason = "EDGE_COLLAPSE_FAILED"
            elif metrics["maximum_edge_ratio"] > MAXIMUM_EDGE_RATIO:
                reason = "EDGE_STRETCH_FAILED"
            elif metrics["maximum_triangle_aspect_ratio"] > MAXIMUM_ASPECT_RATIO:
                reason = "TRIANGLE_QUALITY_FAILED"
            else:
                reason = ""
            if reason:
                counts[reason] += 1
                first_counterexamples.setdefault(reason, {
                    "member_index": member_index,
                    "target_clearance_mm": target_clearance,
                    "harmonic_weight": weight,
                    **metrics,
                })
                continue
            candidate_keepouts = keepout_hits(records, cells)
            new_keepouts = candidate_keepouts - baseline_keepouts
            if new_keepouts:
                reason = "NEGATIVE_SPACE_CONFLICT"
                counts[reason] += 1
                first_counterexamples.setdefault(reason, {
                    "member_index": member_index,
                    "target_clearance_mm": target_clearance,
                    "harmonic_weight": weight,
                    "new_negative_space_cell_ids": sorted(new_keepouts),
                })
                continue
            complement = surface.overlap_delta(
                baseline_complement,
                surface.overlap_audit(
                    records, complement_records, candidate, False
                ),
            )
            if complement["new_conflict_pair_count"]:
                reason = "SOURCE_COMPLEMENT_INTERSECTION"
                counts[reason] += 1
                first_counterexamples.setdefault(reason, {
                    "member_index": member_index,
                    "target_clearance_mm": target_clearance,
                    "harmonic_weight": weight,
                    "new_conflict_pair_count": complement[
                        "new_conflict_pair_count"
                    ],
                })
                continue
            self_overlap = surface.overlap_delta(
                baseline_self,
                surface.overlap_audit(records, records, candidate, True),
            )
            if self_overlap["new_conflict_pair_count"]:
                reason = "SELF_INTERSECTION"
                counts[reason] += 1
                first_counterexamples.setdefault(reason, {
                    "member_index": member_index,
                    "target_clearance_mm": target_clearance,
                    "harmonic_weight": weight,
                    "new_conflict_pair_count": self_overlap[
                        "new_conflict_pair_count"
                    ],
                })
                continue
            clearance = cutter_audit.clearance_contract(
                [
                    {
                        "triangle_id": record["triangle_id"],
                        "source_fixture": f"source_face_{record['face_id']}",
                        "points": record["points"],
                    }
                    for record in records
                ],
                context["points"],
                context["triangles"],
                context["orientation_sign"],
            )
            clearance_records = clearance["triangle_records"]
            minimum_exact = min(
                record["minimum_exact_clearance_mm"]
                for record in clearance_records
            )
            minimum_signed = min(
                sample["signed_margin_mm"]
                for record in clearance_records
                for sample in record["adaptive_signed_samples"]["samples"]
            )
            if (
                not clearance["adaptive_sampling_converged"]
                or minimum_exact < MINIMUM_CLEARANCE_MM - TOLERANCE_MM
                or minimum_signed < MINIMUM_CLEARANCE_MM - TOLERANCE_MM
            ):
                reason = "ADAPTIVE_CUTTER_CLEARANCE_FAILED"
                counts[reason] += 1
                first_counterexamples.setdefault(reason, {
                    "member_index": member_index,
                    "target_clearance_mm": target_clearance,
                    "harmonic_weight": weight,
                    "minimum_exact_clearance_mm": minimum_exact,
                    "minimum_signed_margin_mm": minimum_signed,
                })
                continue
            moved = {
                str(vertex_id): split_family.point_record(candidate[vertex_id])
                for vertex_id in interior_ids
                if (candidate[vertex_id] - original[vertex_id]).length
                > TOLERANCE_MM
            }
            selected = {
                "member_index": member_index,
                "target_clearance_mm": target_clearance,
                "harmonic_weight": weight,
                "moved_vertex_coordinates_mm": moved,
                "moved_vertex_count": len(moved),
                "surface_metrics": metrics,
                "minimum_sampled_margin_mm": minimum_sampled,
                "minimum_exact_clearance_mm": minimum_exact,
                "minimum_signed_margin_mm": minimum_signed,
                "new_negative_space_cell_ids": [],
                "new_source_complement_conflict_pair_count": 0,
                "new_self_intersection_pair_count": 0,
            }
            selected["fingerprint"] = exact.stable_hash(selected)
            break
        if selected is not None:
            break

    status = (
        "V27_C9_PROXIMAL_SURFACE_SOLVED"
        if selected is not None
        else "V27_C9_PROXIMAL_SURFACE_FAMILY_EXHAUSTED"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": "read-only finite harmonic reconstruction of the 253-face proximal C9 mask",
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": verified,
        "source_scene": {
            "blend": str(Path(bpy.data.filepath).resolve()),
            "source_object": source.name,
            "cutter_object": cutter.name,
        },
        "finite_family": family_definition,
        "family_fingerprint": family_fingerprint,
        "evaluation": {
            "evaluated_member_count": evaluated,
            "rejection_counts": dict(sorted(counts.items())),
            "first_counterexamples": first_counterexamples,
            "best_sampled_clearance_counterexample": (
                best_sampled_counterexample
            ),
        },
        "selection": selected,
        "invariants": {
            "fixed_boundary_vertex_count_is_71": len(boundary_ids) == 71,
            "source_mesh_not_mutated": True,
            "candidate_geometry_not_emitted": True,
        },
        "safety": {
            "mutation_started": False,
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
        "family_fingerprint": family_fingerprint,
        "evaluated_member_count": evaluated,
        "rejection_counts": dict(sorted(counts.items())),
        "selection_fingerprint": (
            selected["fingerprint"] if selected is not None else None
        ),
        "safety": result["safety"],
    }
    exact.atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
