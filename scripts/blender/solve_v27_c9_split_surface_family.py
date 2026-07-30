#!/usr/bin/env python3
"""Historical V27 evidence: exhaust the rejected split-surface family."""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import product
import json
import math
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_v27_c9_landing as landing  # noqa: E402
import analyze_v27_c9_landing_surface as surface  # noqa: E402
import audit_v26_cutter_authority as cutter_audit  # noqa: E402
import solve_v27_flex_gap as exact  # noqa: E402
from v27_historical_guard import require_historical_rerun  # noqa: E402


OPERATION = "SOLVE_V27_C9_SPLIT_SURFACE_FAMILY"
MISSION = "R014-JOINT-C9-C20-ELBOW-V27"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
SPLIT_AUTHORITY = V27 / "v27_c9_split_incidence_authority.json"
LANDING_AUTHORITY = V27 / "v27_c9_landing_authority.json"
AGGREGATE_AUTHORITY = V27 / "v27_aggregate_authority.json"
DEFAULT_OUTPUT = V27 / "v27_c9_split_surface_family_authority.json"
DEFAULT_RECEIPT = V27 / "v27_c9_split_surface_family_authority_receipt.json"
EXPECTED_HASHES = {
    "split_authority": (
        SPLIT_AUTHORITY,
        "1e0b9da47116bb23e45cbfc5ef1259cd1733a4aeb1d2bbfadc1bf7724a63ab72",
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
BLEND_WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]
ROTATION_DEGREES = [-30, -15, 0, 15, 30]
EXTRA_OFFSETS_MM = [0, 1, 2, 4, 6, 8]
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


def point_record(point: Vector) -> list[float]:
    return [float(value) for value in point]


def cutter_context(cutter: bpy.types.Object) -> dict[str, Any]:
    evaluated = cutter.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    try:
        evaluated_mesh.calc_loop_triangles()
        matrix = cutter.matrix_world
        points = [matrix @ vertex.co for vertex in evaluated_mesh.vertices]
        triangles = [
            tuple(int(value) for value in triangle.vertices)
            for triangle in evaluated_mesh.loop_triangles
        ]
    finally:
        evaluated.to_mesh_clear()
    signed_volume = sum(
        points[first].dot(points[second].cross(points[third]))
        for first, second, third in triangles
    ) / 6.0
    orientation_sign = 1.0 if signed_volume >= 0.0 else -1.0
    return {
        "points": points,
        "triangles": triangles,
        "tree": BVHTree.FromPolygons(points, triangles, all_triangles=True),
        "orientation_sign": orientation_sign,
    }


def nearest_frame(point: Vector, context: dict[str, Any]) -> dict[str, Any]:
    location, normal, triangle_id, distance = context["tree"].find_nearest(point)
    if location is None:
        raise RuntimeError(
            f"{OPERATION}: cutter nearest query failed; point={point_record(point)}"
        )
    outward = (normal * context["orientation_sign"]).normalized()
    signed = float(distance)
    if (point - location).dot(outward) < 0.0:
        signed = -signed
    return {
        "signed_margin_mm": signed,
        "nearest_point": location,
        "outward": outward,
        "triangle_id": int(triangle_id),
    }


def triangle_records(
    mesh: bpy.types.Mesh,
    face_records: list[dict[str, Any]],
    coordinates: dict[str, Vector],
    virtual_ids: dict[str, int],
) -> list[dict[str, Any]]:
    records = []
    for face in face_records:
        symbols = face["candidate_symbolic_vertex_ids"]
        if len(symbols) != 3:
            raise RuntimeError(
                f"{OPERATION}: non-triangle reconstruction face; "
                f"face={face['source_face_id']}; vertices={symbols}"
            )
        records.append(
            {
                "triangle_id": int(face["source_face_id"]),
                "face_id": int(face["source_face_id"]),
                "vertex_ids": tuple(virtual_ids[symbol] for symbol in symbols),
                "points": tuple(coordinates[symbol] for symbol in symbols),
            }
        )
    return records


def reconstructed_normal(
    mesh: bpy.types.Mesh,
    face_records: list[dict[str, Any]],
    source_vertex_id: int,
) -> Vector:
    normal = Vector()
    for face in face_records:
        if source_vertex_id not in face["source_vertex_ids"]:
            continue
        points = tuple(
            mesh.vertices[index].co.copy() for index in face["source_vertex_ids"]
        )
        normal += surface.triangle_area_normal(points)
    if normal.length <= TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: reconstructed normal is degenerate; "
            f"vertex={source_vertex_id}"
        )
    return normal.normalized()


def boundary_tangent(
    mesh: bpy.types.Mesh,
    face_records: list[dict[str, Any]],
    source_vertex_id: int,
    normal: Vector,
) -> Vector:
    center = mesh.vertices[source_vertex_id].co
    neighbors = sorted(
        {
            int(vertex_id)
            for face in face_records
            if source_vertex_id in face["source_vertex_ids"]
            for vertex_id in face["source_vertex_ids"]
            if int(vertex_id) != source_vertex_id
        }
    )
    vectors = [mesh.vertices[index].co - center for index in neighbors]
    tangent = max(vectors, key=lambda value: value.length).copy()
    tangent -= normal * tangent.dot(normal)
    if tangent.length <= TOLERANCE_MM:
        raise RuntimeError(
            f"{OPERATION}: boundary tangent is degenerate; "
            f"vertex={source_vertex_id}; neighbors={neighbors}"
        )
    return tangent.normalized()


def candidate_metrics(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> dict[str, Any]:
    minimum_dot = 1.0
    maximum_aspect = 0.0
    edge_ratios = []
    seen_edges = set()
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
            edge = tuple(sorted((after["vertex_ids"][first], after["vertex_ids"][second])))
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            before_length = (before["points"][first] - before["points"][second]).length
            after_length = (after["points"][first] - after["points"][second]).length
            edge_ratios.append(
                math.inf
                if before_length <= TOLERANCE_MM
                else after_length / before_length
            )
    return {
        "minimum_normal_dot": minimum_dot,
        "minimum_edge_ratio": min(edge_ratios),
        "maximum_edge_ratio": max(edge_ratios),
        "maximum_triangle_aspect_ratio": maximum_aspect,
    }


def keepout_hits(
    records: list[dict[str, Any]], cells: list[dict[str, Any]]
) -> set[str]:
    hits = set()
    for record in records:
        triangle = [point_record(point) for point in record["points"]]
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

    split = exact.load_json(SPLIT_AUTHORITY)
    landing_authority = exact.load_json(LANDING_AUTHORITY)
    aggregate = exact.load_json(AGGREGATE_AUTHORITY)
    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = Path(split["source_scene"]["blend"]).resolve()
    if blend_path != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}; "
            f"actual={blend_path}"
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
    if not landing.matrix_is_identity(source.matrix_world):
        raise RuntimeError(f"{OPERATION}: source object matrix is not identity")

    mesh = source.data
    authority = split["reconstruction_authority"]
    face_records = authority["face_records"]
    split_records = authority["split_records"]
    split_ids = [int(record["source_vertex_id"]) for record in split_records]
    endpoint_targets = {
        int(vertex_id): Vector(coordinate)
        for vertex_id, coordinate in zip(
            landing.TARGET_VERTEX_IDS,
            landing_authority["selection"]["moved_endpoint_coordinates_mm"],
            strict=True,
        )
    }
    symbols = sorted(
        {
            symbol
            for face in face_records
            for symbol in face["candidate_symbolic_vertex_ids"]
        }
    )
    virtual_ids = {symbol: len(mesh.vertices) + index for index, symbol in enumerate(symbols)}
    source_coordinates = {
        f"VSRC_{vertex.index}": vertex.co.copy() for vertex in mesh.vertices
    }
    for vertex_id, point in endpoint_targets.items():
        source_coordinates[f"VSRC_{vertex_id}"] = point
    for record in split_records:
        source_coordinates[record["reconstructed_symbolic_vertex_id"]] = Vector(
            record["source_coordinate_mm"]
        )

    context = cutter_context(cutter)
    frames = {}
    for record in split_records:
        vertex_id = int(record["source_vertex_id"])
        point = Vector(record["source_coordinate_mm"])
        nearest = nearest_frame(point, context)
        source_normal = reconstructed_normal(mesh, face_records, vertex_id)
        if source_normal.dot(nearest["outward"]) < 0.0:
            source_normal.negate()
        tangent = boundary_tangent(mesh, face_records, vertex_id, source_normal)
        frames[vertex_id] = {
            "point": point,
            "nearest": nearest,
            "source_normal": source_normal,
            "tangent": tangent,
        }

    direction_modes = []
    for blend, rotation in product(BLEND_WEIGHTS, ROTATION_DEGREES):
        directions = {}
        required = {}
        valid = True
        for vertex_id in split_ids:
            frame = frames[vertex_id]
            direction = (
                frame["nearest"]["outward"] * (1.0 - blend)
                + frame["source_normal"] * blend
            )
            if direction.length <= TOLERANCE_MM:
                valid = False
                break
            direction.normalize()
            direction.rotate(
                Quaternion(frame["tangent"], math.radians(rotation))
            )
            outward_rate = direction.dot(frame["nearest"]["outward"])
            if outward_rate <= 0.05:
                valid = False
                break
            directions[vertex_id] = direction
            required[vertex_id] = max(
                0.0,
                (
                    MINIMUM_CLEARANCE_MM
                    - frame["nearest"]["signed_margin_mm"]
                )
                / outward_rate,
            )
        direction_modes.append(
            {
                "blend_weight": blend,
                "rotation_degrees": rotation,
                "valid": valid,
                "directions": directions,
                "required_displacements_mm": required,
            }
        )

    offset_tuples = sorted(
        product(EXTRA_OFFSETS_MM, repeat=3),
        key=lambda values: (sum(values), max(values), values),
    )
    member_definitions = [
        {
            "member_index": index,
            "blend_weight": mode["blend_weight"],
            "rotation_degrees": mode["rotation_degrees"],
            "extra_offsets_mm": list(offsets),
        }
        for index, (mode, offsets) in enumerate(
            (item for mode in direction_modes for item in ((mode, offsets) for offsets in offset_tuples))
        )
    ]
    family_definition = {
        "split_source_vertex_order": split_ids,
        "blend_weights": BLEND_WEIGHTS,
        "rotation_degrees": ROTATION_DEGREES,
        "extra_offsets_mm": EXTRA_OFFSETS_MM,
        "ordering": (
            "direction mode in blend/rotation declaration order, then "
            "increasing sum(extra), max(extra), tuple"
        ),
        "member_count": len(member_definitions),
        "members": member_definitions,
    }
    family_fingerprint = exact.stable_hash(family_definition)

    baseline_coordinates = dict(source_coordinates)
    baseline_records = triangle_records(
        mesh, face_records, baseline_coordinates, virtual_ids
    )
    all_coordinates = [vertex.co.copy() for vertex in mesh.vertices]
    all_coordinates.extend(
        baseline_coordinates[symbol].copy() for symbol in symbols
    )
    mesh.calc_loop_triangles()
    reconstructed_faces = {
        int(record["source_face_id"]) for record in face_records
    }
    complement_records = [
        {
            "triangle_id": int(triangle.index),
            "face_id": int(triangle.polygon_index),
            "vertex_ids": tuple(int(value) for value in triangle.vertices),
            "points": tuple(
                mesh.vertices[index].co.copy() for index in triangle.vertices
            ),
        }
        for triangle in mesh.loop_triangles
        if int(triangle.polygon_index) not in reconstructed_faces
    ]
    aggregate_negative = exact.load_json(
        ROOT / aggregate["verified_inputs"]["negative_space_authority"]["path"]
    )
    cells = exact.collect_keepout_cells(aggregate_negative)
    baseline_keepouts = keepout_hits(baseline_records, cells)
    baseline_complement = surface.overlap_audit(
        baseline_records, complement_records, all_coordinates, False
    )
    baseline_self = surface.overlap_audit(
        baseline_records, baseline_records, all_coordinates, True
    )

    counts: Counter[str] = Counter()
    first_counterexamples: dict[str, Any] = {}
    selected = None
    evaluated = 0
    for member in member_definitions:
        evaluated += 1
        mode = next(
            item
            for item in direction_modes
            if item["blend_weight"] == member["blend_weight"]
            and item["rotation_degrees"] == member["rotation_degrees"]
        )
        if not mode["valid"]:
            counts["INVALID_DIRECTION_MODE"] += 1
            continue
        candidate_coordinates = dict(source_coordinates)
        moved = {}
        for vertex_id, extra in zip(
            split_ids, member["extra_offsets_mm"], strict=True
        ):
            record = next(
                item for item in split_records
                if int(item["source_vertex_id"]) == vertex_id
            )
            displacement = mode["required_displacements_mm"][vertex_id] + extra
            point = frames[vertex_id]["point"] + mode["directions"][vertex_id] * displacement
            candidate_coordinates[record["reconstructed_symbolic_vertex_id"]] = point
            moved[vertex_id] = point
        records = triangle_records(
            mesh, face_records, candidate_coordinates, virtual_ids
        )
        vertex_margins = {
            vertex_id: nearest_frame(point, context)["signed_margin_mm"]
            for vertex_id, point in moved.items()
        }
        if min(vertex_margins.values()) < MINIMUM_CLEARANCE_MM - TOLERANCE_MM:
            reason = "SPLIT_VERTEX_CLEARANCE_FAILED"
            counts[reason] += 1
            first_counterexamples.setdefault(reason, {
                **member,
                "minimum_split_vertex_margin_mm": min(vertex_margins.values()),
            })
            continue
        metrics = candidate_metrics(baseline_records, records)
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
            first_counterexamples.setdefault(reason, {**member, **metrics})
            continue
        candidate_keepouts = keepout_hits(records, cells)
        new_keepouts = candidate_keepouts - baseline_keepouts
        if new_keepouts:
            reason = "NEGATIVE_SPACE_CONFLICT"
            counts[reason] += 1
            first_counterexamples.setdefault(reason, {
                **member,
                "new_negative_space_cell_ids": sorted(new_keepouts),
            })
            continue

        coordinate_list = [vertex.co.copy() for vertex in mesh.vertices]
        coordinate_list.extend(candidate_coordinates[symbol].copy() for symbol in symbols)
        complement = surface.overlap_delta(
            baseline_complement,
            surface.overlap_audit(records, complement_records, coordinate_list, False),
        )
        if complement["new_conflict_pair_count"]:
            reason = "SOURCE_COMPLEMENT_INTERSECTION"
            counts[reason] += 1
            first_counterexamples.setdefault(reason, {
                **member,
                "new_conflict_pair_count": complement["new_conflict_pair_count"],
            })
            continue
        self_overlap = surface.overlap_delta(
            baseline_self,
            surface.overlap_audit(records, records, coordinate_list, True),
        )
        if self_overlap["new_conflict_pair_count"]:
            reason = "SELF_INTERSECTION"
            counts[reason] += 1
            first_counterexamples.setdefault(reason, {
                **member,
                "new_conflict_pair_count": self_overlap["new_conflict_pair_count"],
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
            record["minimum_exact_clearance_mm"] for record in clearance_records
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
            reason = "CUTTER_CLEARANCE_FAILED"
            counts[reason] += 1
            first_counterexamples.setdefault(reason, {
                **member,
                "minimum_exact_clearance_mm": minimum_exact,
                "minimum_signed_margin_mm": minimum_signed,
            })
            continue
        selected = {
            **member,
            "split_vertex_coordinates_mm": {
                str(vertex_id): point_record(moved[vertex_id])
                for vertex_id in split_ids
            },
            "endpoint_coordinates_mm": {
                str(vertex_id): point_record(point)
                for vertex_id, point in endpoint_targets.items()
            },
            "surface_metrics": metrics,
            "minimum_exact_clearance_mm": minimum_exact,
            "minimum_signed_margin_mm": minimum_signed,
            "new_negative_space_cell_ids": [],
            "new_source_complement_conflict_pair_count": 0,
            "new_self_intersection_pair_count": 0,
        }
        selected["fingerprint"] = exact.stable_hash(selected)
        break

    status = (
        "V27_C9_SPLIT_SURFACE_SOLVED"
        if selected is not None
        else "V27_C9_SPLIT_SURFACE_FAMILY_EXHAUSTED"
    )
    result = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": status,
        "scope": "read-only finite five-control split-surface reconstruction",
        "code_sha256": exact.sha_file(Path(__file__).resolve()),
        "verified_inputs": verified,
        "source_scene": {
            "blend": str(blend_path),
            "source_object": source.name,
            "cutter_object": cutter.name,
        },
        "finite_family": family_definition,
        "family_fingerprint": family_fingerprint,
        "local_frames": {
            str(vertex_id): {
                "source_coordinate_mm": point_record(frames[vertex_id]["point"]),
                "source_signed_margin_mm": frames[vertex_id]["nearest"]["signed_margin_mm"],
                "cutter_outward": point_record(frames[vertex_id]["nearest"]["outward"]),
                "reconstructed_source_normal": point_record(frames[vertex_id]["source_normal"]),
                "boundary_tangent": point_record(frames[vertex_id]["tangent"]),
            }
            for vertex_id in split_ids
        },
        "baseline": {
            "negative_space_cell_ids": sorted(baseline_keepouts),
            "source_complement_conflict_pair_count": baseline_complement["candidate"]["conflict_count"] if "candidate" in baseline_complement else baseline_complement["conflict_count"],
            "self_intersection_pair_count": baseline_self["conflict_count"],
        },
        "evaluation": {
            "evaluated_member_count": evaluated,
            "rejection_counts": dict(sorted(counts.items())),
            "first_counterexamples": first_counterexamples,
        },
        "selection": selected,
        "invariants": {
            "family_defined_before_selection": True,
            "family_member_count_is_5400": len(member_definitions) == 5400,
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
