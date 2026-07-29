"""Build one component-20 liner from independent complete boundary cycles."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.geometry import normal as polygon_normal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from build_combined_authored_inner_bowl_liner import (  # noqa: E402
    EXPECTED_BLEND_SHA256,
    INITIAL_FLOOR_MM,
    MAPPING_PATH,
    TOLERANCE_MM,
    boundary_cycles,
    converge_triangle_clearance,
    fingerprint,
    insert_fixed_controls,
    mean_region_normal,
    plane_basis,
    point_in_polygon,
    project_new_vertices,
    projected,
    remap_combined,
    sha256_file,
    subdivide_replacement,
    tessellate_boundaries,
    topology_record,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid  # noqa: E402
from try_cutter_patch_reconstruction import (  # noqa: E402
    create_object,
    ensure_collection,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    REVIEW_COLLECTION,
    triangle_quality,
)


OPERATION = "BOUNDARY_CYCLE_INNER_BOWL_LINER"
STAGED_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
ARTICULATION_VERTEX_ID = 2008


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-blend-sha256",
        default=EXPECTED_BLEND_SHA256,
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


def cycle_edges(cycle: list[int]) -> set[tuple[int, int]]:
    return {
        tuple(sorted((first, second)))
        for first, second in zip(cycle, cycle[1:] + cycle[:1])
    }


def local_cycle_normal(
    cycle: list[int],
    points: list[Vector],
    reference: Vector,
) -> Vector:
    result = polygon_normal([points[index] for index in cycle])
    if result.length <= 1.0e-9:
        raise RuntimeError(
            f"{OPERATION}: boundary cycle with {len(cycle)} vertices has "
            "a degenerate polygon normal"
        )
    result.normalize()
    if result.dot(reference) < 0.0:
        result.negate()
    return result


def contains_cycle(
    outer: list[int],
    candidate: list[int],
    points: list[Vector],
    normal: Vector,
) -> bool:
    first, second = plane_basis(normal)
    ids = set(outer) | set(candidate)
    projected_points = {
        vertex: projected(points[vertex], first, second) for vertex in ids
    }
    centroid = (
        sum(projected_points[vertex][0] for vertex in candidate)
        / len(candidate),
        sum(projected_points[vertex][1] for vertex in candidate)
        / len(candidate),
    )
    return point_in_polygon(centroid, outer, projected_points)


def combine_replacements(
    chart_records: list[dict],
    articulation_alias_id: int,
) -> tuple[list[Vector], list[tuple[int, int, int]], list[int], list[list[int]]]:
    points = []
    faces = []
    source_ids = []
    face_ranges = []
    articulation_occurrences = 0
    for chart in chart_records:
        vertex_offset = len(points)
        face_start = len(faces)
        points.extend(point.copy() for point in chart["points"])
        chart_source_ids = list(chart["source_ids"])
        for local_id, source_id in enumerate(chart_source_ids):
            if source_id not in {
                ARTICULATION_VERTEX_ID,
                articulation_alias_id,
            }:
                continue
            articulation_occurrences += 1
            if source_id == articulation_alias_id:
                chart_source_ids[local_id] = -1
        source_ids.extend(chart_source_ids)
        faces.extend(
            tuple(vertex_offset + vertex for vertex in face)
            for face in chart["faces"]
        )
        face_ranges.append([face_start, len(faces)])
    if articulation_occurrences != 2:
        raise RuntimeError(
            f"{OPERATION}: combined charts contain "
            f"{articulation_occurrences} occurrences of "
            f"V{ARTICULATION_VERTEX_ID}; expected exactly 2"
        )
    return points, faces, source_ids, face_ranges


def component_overlap_count(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    component: set[int],
    cutter_points: list[Vector],
    cutter_faces: list[tuple[int, ...]],
) -> int:
    ids = sorted(component)
    remap = {source_id: local_id for local_id, source_id in enumerate(ids)}
    local_faces = [
        tuple(remap[vertex] for vertex in face)
        for face in faces
        if face[0] in component
    ]
    return len(
        overlap_pairs(
            [points[index] for index in ids],
            local_faces,
            cutter_points,
            cutter_faces,
        )
    )


def main() -> int:
    args = parse_args()
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha = sha256_file(blend_path)
    if actual_sha != args.required_blend_sha256:
        raise RuntimeError(
            f"{OPERATION}: staged blend '{blend_path}' has SHA-256 "
            f"{actual_sha}, expected {args.required_blend_sha256}"
        )
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    staged = require_mesh(STAGED_NAME, "coordinated staged geometry")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    staged_points, staged_faces, materials = evaluated_geometry(staged)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    rebuild_faces = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    retain_c20_faces = set(mapping["reconstruction_scope"]["retain_face_ids"])
    _, components = connected_components(source)
    component9 = set(components[9])
    component20 = set(components[20])
    component20_faces = {
        face_id
        for face_id, face in enumerate(staged_faces)
        if face[0] in component20
    }
    if rebuild_faces | retain_c20_faces != component20_faces:
        raise RuntimeError(
            f"{OPERATION}: mapped component-20 partition is not exact"
        )
    cycles, complete_boundary = boundary_cycles(staged_faces, rebuild_faces)
    source_edge_id = {
        tuple(sorted(edge.vertices)): edge.index for edge in source.data.edges
    }
    aperture_edge_sets = [
        {
            tuple(sorted(edge))
            for edge in group["edge_vertex_ids"]
        }
        for group in mapping["exact_full_inner_bowl_seam"]["boundary_groups"]
        if group["status"] == "closed"
    ]
    aperture_cycles = []
    outer_cycles = []
    unmatched_apertures = list(aperture_edge_sets)
    for cycle in cycles:
        edges = cycle_edges(cycle)
        matching = next(
            (
                aperture
                for aperture in unmatched_apertures
                if edges == aperture
            ),
            None,
        )
        if matching is None:
            outer_cycles.append(cycle)
        else:
            aperture_cycles.append(cycle)
            unmatched_apertures.remove(matching)
    if (
        len(outer_cycles) != 2
        or len(aperture_cycles) != 2
        or unmatched_apertures
    ):
        raise RuntimeError(
            f"{OPERATION}: classified {len(outer_cycles)} outer and "
            f"{len(aperture_cycles)} aperture cycles; expected 2 and 2"
        )
    shared_outer_vertices = set(outer_cycles[0]) & set(outer_cycles[1])
    articulation_aperture_indices = [
        index
        for index, aperture in enumerate(aperture_cycles)
        if ARTICULATION_VERTEX_ID in aperture
    ]
    articulation_outer_indices = [
        index
        for index, outer in enumerate(outer_cycles)
        if ARTICULATION_VERTEX_ID in outer
    ]
    if (
        shared_outer_vertices
        or len(articulation_aperture_indices) != 1
        or len(articulation_outer_indices) != 1
    ):
        boundary_degree = Counter(
            vertex for edge in complete_boundary for vertex in edge
        )
        raise RuntimeError(
            f"{OPERATION}: outer cycles share {sorted(shared_outer_vertices)}, "
            "expected none; "
            f"V{ARTICULATION_VERTEX_ID} must occur in exactly one outer and "
            "one aperture but occurs in outer indices "
            f"{articulation_outer_indices} and aperture indices "
            f"{articulation_aperture_indices}; outer cycle sizes are "
            f"{[len(cycle) for cycle in outer_cycles]}; "
            "complete-boundary degree-4 vertices are "
            f"{sorted(vertex for vertex, degree in boundary_degree.items() if degree == 4)}"
        )
    touching_outer = outer_cycles[articulation_outer_indices[0]]
    touching_aperture = aperture_cycles[articulation_aperture_indices[0]]
    if set(touching_outer) & set(touching_aperture) != {
        ARTICULATION_VERTEX_ID
    }:
        raise RuntimeError(
            f"{OPERATION}: articulated outer/aperture intersection is "
            f"{sorted(set(touching_outer) & set(touching_aperture))}, "
            f"expected only V{ARTICULATION_VERTEX_ID}"
        )
    global_normal = mean_region_normal(
        staged_points,
        staged_faces,
        rebuild_faces,
    )
    chart_specs = []
    aperture_owners: dict[int, int] = {}
    for chart_index, outer in enumerate(outer_cycles):
        normal = local_cycle_normal(outer, staged_points, global_normal)
        holes = []
        for aperture_index, aperture in enumerate(aperture_cycles):
            if contains_cycle(
                outer,
                aperture,
                staged_points,
                normal,
            ):
                holes.append(aperture)
                aperture_owners[aperture_index] = chart_index
        chart_specs.append(
            {
                "chart_index": chart_index,
                "outer": outer,
                "holes": holes,
                "normal": normal,
            }
        )
    if set(aperture_owners) != set(range(len(aperture_cycles))):
        raise RuntimeError(
            f"{OPERATION}: aperture ownership is {aperture_owners}; every "
            "aperture must belong to exactly one outer cycle"
        )
    if len(set(aperture_owners.values())) < 1:
        raise RuntimeError(
            f"{OPERATION}: aperture ownership did not resolve an outer chart"
        )
    retained_vertices = {
        vertex
        for face_id, face in enumerate(staged_faces)
        if face_id not in rebuild_faces
        for vertex in face
    }
    interface_ids = {
        record["component_20_vertex_id"]
        for record in mapping["exact_component_9_attachment_landmarks"][
            "vertex_records"
        ]
    }
    removed_only_controls = sorted(interface_ids - retained_vertices)
    control_owners: dict[int, int] = {}
    for control in removed_only_controls:
        containing = []
        for spec in chart_specs:
            if contains_cycle(
                spec["outer"],
                [control],
                staged_points,
                spec["normal"],
            ):
                containing.append(spec["chart_index"])
        if len(containing) == 1:
            control_owners[control] = containing[0]
            continue
        control_owners[control] = min(
            range(len(chart_specs)),
            key=lambda index: min(
                (staged_points[control] - staged_points[vertex]).length
                for vertex in chart_specs[index]["outer"]
            ),
        )
    old_region_vertex_ids = sorted(
        {
            vertex
            for face_id in rebuild_faces
            for vertex in staged_faces[face_id]
        }
    )
    old_to_local = {
        source_id: local_id
        for local_id, source_id in enumerate(old_region_vertex_ids)
    }
    old_region_points = [staged_points[index] for index in old_region_vertex_ids]
    old_region_faces = [
        tuple(old_to_local[vertex] for vertex in staged_faces[face_id])
        for face_id in sorted(rebuild_faces)
    ]
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    chart_records = []
    articulation_alias_id = len(staged_points)
    for spec in chart_specs:
        chart_index = spec["chart_index"]
        chart_points = list(staged_points)
        loops = [list(spec["outer"]), *[list(hole) for hole in spec["holes"]]]
        articulation_alias_used = any(
            ARTICULATION_VERTEX_ID in hole for hole in loops[1:]
        )
        if articulation_alias_used:
            first, _ = plane_basis(spec["normal"])
            chart_points.append(
                staged_points[ARTICULATION_VERTEX_ID] + first * 1.0e-5
            )
            loops = [
                loops[0],
                *[
                    [
                        (
                            articulation_alias_id
                            if vertex == ARTICULATION_VERTEX_ID
                            else vertex
                        )
                        for vertex in hole
                    ]
                    for hole in loops[1:]
                ],
            ]
        coarse = tessellate_boundaries(
            loops,
            chart_points,
            spec["normal"],
        )
        controls = sorted(
            control
            for control, owner in control_owners.items()
            if owner == chart_index
        )
        coarse = insert_fixed_controls(
            coarse,
            controls,
            chart_points,
            spec["normal"],
        )
        fixed_ids = set().union(*map(set, loops)) | set(controls)
        points, faces, source_ids = subdivide_replacement(
            coarse,
            set().union(*(cycle_edges(loop) for loop in loops)),
            chart_points,
            fixed_ids,
        )
        if articulation_alias_used:
            alias_local_ids = [
                local_id
                for local_id, source_id in enumerate(source_ids)
                if source_id == articulation_alias_id
            ]
            if len(alias_local_ids) != 1:
                raise RuntimeError(
                    f"{OPERATION}: chart {chart_index} retained "
                    f"{len(alias_local_ids)} V{ARTICULATION_VERTEX_ID} "
                    "aperture aliases; expected exactly 1"
                )
            points[alias_local_ids[0]] = staged_points[
                ARTICULATION_VERTEX_ID
            ].copy()
        new_ids = project_new_vertices(
            points,
            source_ids,
            old_region_points,
            old_region_faces,
            target_length,
            grid,
        )
        convergence = converge_triangle_clearance(
            points,
            faces,
            new_ids,
            cutter_points,
            cutter_faces,
            target_length,
        )
        overlap_count = len(
            overlap_pairs(
                points,
                faces,
                cutter_points,
                cutter_faces,
            )
        )
        normal_reversals = sum(
            (
                (points[face[1]] - points[face[0]])
                .cross(points[face[2]] - points[face[0]])
                .dot(spec["normal"])
                <= 0.0
            )
            for face in faces
        )
        chart_records.append(
            {
                "chart_index": chart_index,
                "outer_cycle_vertex_count": len(spec["outer"]),
                "outer_cycle_edge_ids": sorted(
                    source_edge_id[edge]
                    for edge in cycle_edges(spec["outer"])
                ),
                "aperture_cycle_vertex_counts": [
                    len(hole) for hole in spec["holes"]
                ],
                "exact_control_vertex_ids": controls,
                "normal": [round(value, 9) for value in spec["normal"]],
                "coarse_triangle_count": len(coarse),
                "replacement_vertex_count": len(points),
                "new_interior_vertex_count": len(new_ids),
                "replacement_triangle_count": len(faces),
                "clearance_convergence": convergence,
                "replacement_overlap_count": overlap_count,
                "normal_reversal_count": normal_reversals,
                "articulation_alias_used": articulation_alias_used,
                "points": points,
                "faces": faces,
                "source_ids": source_ids,
            }
        )
    (
        replacement_points,
        replacement_faces,
        replacement_source_ids,
        chart_face_ranges,
    ) = combine_replacements(chart_records, articulation_alias_id)
    replacement_material = Counter(
        materials[face_id] for face_id in rebuild_faces
    ).most_common(1)[0][0]
    (
        result_points,
        result_faces,
        result_materials,
        retained_source_ids,
        replacement_range,
    ) = remap_combined(
        staged_points,
        staged_faces,
        materials,
        rebuild_faces,
        replacement_points,
        replacement_faces,
        replacement_source_ids,
        replacement_material,
    )
    collection = ensure_collection(REVIEW_COLLECTION)
    before_obj = create_object(
        f"{args.prefix}_BEFORE",
        staged_points,
        staged_faces,
        materials,
        list(staged.data.materials),
        collection,
    )
    after_obj = create_object(
        f"{args.prefix}_AFTER",
        result_points,
        result_faces,
        result_materials,
        list(staged.data.materials),
        collection,
    )
    topology = topology_record(before_obj, after_obj)
    baseline_global = len(
        overlap_pairs(staged_points, staged_faces, cutter_points, cutter_faces)
    )
    after_global = len(
        overlap_pairs(result_points, result_faces, cutter_points, cutter_faces)
    )
    baseline_c9 = component_overlap_count(
        staged_points,
        staged_faces,
        component9,
        cutter_points,
        cutter_faces,
    )
    source_to_result = {
        source_id: result_id
        for result_id, source_id in enumerate(retained_source_ids)
    }
    result_c9_ids = sorted(source_to_result[index] for index in component9)
    result_c9_remap = {
        result_id: local_id
        for local_id, result_id in enumerate(result_c9_ids)
    }
    result_c9_faces = [
        tuple(
            result_c9_remap[source_to_result[vertex]]
            for vertex in face
        )
        for face in staged_faces
        if face[0] in component9
    ]
    after_c9 = len(
        overlap_pairs(
            [result_points[index] for index in result_c9_ids],
            result_c9_faces,
            cutter_points,
            cutter_faces,
        )
    )
    retained_before = [
        staged_points[source_id] for source_id in retained_source_ids
    ]
    retained_after = result_points[: len(retained_source_ids)]
    retained_before_fp = fingerprint(retained_source_ids, retained_before)
    retained_after_fp = fingerprint(retained_source_ids, retained_after)
    pair_errors = []
    for record in mapping["exact_component_9_attachment_landmarks"][
        "vertex_records"
    ]:
        c20 = record["component_20_vertex_id"]
        c9 = record["component_9_vertex_id"]
        if c20 not in source_to_result or c9 not in source_to_result:
            pair_errors.append({"missing_pair": [c20, c9]})
            continue
        before_vector = staged_points[c9] - staged_points[c20]
        after_vector = (
            result_points[source_to_result[c9]]
            - result_points[source_to_result[c20]]
        )
        error = (after_vector - before_vector).length
        if error > TOLERANCE_MM:
            pair_errors.append(
                {
                    "pair": [c20, c9],
                    "relative_vector_error_mm": round(error, 9),
                }
            )
    replacement_overlaps = overlap_pairs(
        replacement_points,
        replacement_faces,
        cutter_points,
        cutter_faces,
    )
    quality = triangle_quality(
        result_points,
        result_faces,
        tuple(replacement_range),
    )
    chart_summaries = []
    for record, face_range in zip(chart_records, chart_face_ranges):
        chart_summaries.append(
            {
                key: value
                for key, value in record.items()
                if key not in {"points", "faces", "source_ids"}
            }
            | {"combined_replacement_face_range": face_range}
        )
    gate_pass = all(
        (
            all(
                chart["clearance_convergence"]["converged"]
                for chart in chart_records
            ),
            not replacement_overlaps,
            after_global < baseline_global,
            after_c9 <= baseline_c9,
            not pair_errors,
            retained_before_fp == retained_after_fp,
            topology["connected_component_delta"] == 0,
            topology["boundary_edge_delta"] == 0,
            topology["nonmanifold_edge_delta"] == 0,
            topology["noncontiguous_manifold_edges"] == 0,
            all(chart["normal_reversal_count"] == 0 for chart in chart_records),
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
        )
    )
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_candidate_not_approved"
            if gate_pass
            else "evaluation_only_boundary_cycle_liner_failed"
        ),
        "operation": OPERATION,
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": actual_sha,
            "staged_object": STAGED_NAME,
        },
        "mapping": {
            "path": str(MAPPING_PATH),
            "sha256": sha256_file(MAPPING_PATH),
            "removed_face_count": len(rebuild_faces),
            "retained_component_20_face_count": len(retain_c20_faces),
        },
        "boundary": {
            "complete_edge_count": len(complete_boundary),
            "cycle_vertex_counts": [len(cycle) for cycle in cycles],
            "outer_cycle_vertex_counts": [
                len(cycle) for cycle in outer_cycles
            ],
            "aperture_cycle_vertex_counts": [
                len(cycle) for cycle in aperture_cycles
            ],
            "shared_outer_vertex_ids": sorted(shared_outer_vertices),
            "articulation_outer_index": articulation_outer_indices[0],
            "articulation_aperture_index": (
                articulation_aperture_indices[0]
            ),
            "aperture_owners": {
                str(aperture): owner
                for aperture, owner in sorted(aperture_owners.items())
            },
        },
        "construction": {
            "initial_floor_mm": INITIAL_FLOOR_MM,
            "articulation_split": {
                "source_vertex_id": ARTICULATION_VERTEX_ID,
                "chart_local_occurrence_count": 2,
                "coordinate_preserved_exactly": True,
                "shared_topological_vertex": False,
            },
            "removed_only_exact_interface_controls": removed_only_controls,
            "control_owners": {
                str(control): owner
                for control, owner in sorted(control_owners.items())
            },
            "charts": chart_summaries,
            "combined_replacement_vertex_count": len(replacement_points),
            "combined_replacement_triangle_count": len(replacement_faces),
        },
        "clearance": {
            "global_overlaps_before": baseline_global,
            "global_overlaps_after": after_global,
            "component_9_overlaps_before": baseline_c9,
            "component_9_overlaps_after": after_c9,
            "replacement_overlap_count": len(replacement_overlaps),
            "replacement_overlap_pairs": [
                list(pair) for pair in sorted(replacement_overlaps)
            ],
        },
        "preservation": {
            "retained_source_vertex_count": len(retained_source_ids),
            "retained_fingerprint_before": retained_before_fp,
            "retained_fingerprint_after": retained_after_fp,
            "retained_fingerprint_equal": (
                retained_before_fp == retained_after_fp
            ),
            "interface_pair_errors": pair_errors,
        },
        "topology": topology,
        "quality": {"replacement": quality},
        "gate_pass": gate_pass,
        "blocker": (
            None
            if gate_pass
            else (
                f"{OPERATION}: independent boundary-cycle construction "
                "failed one or more clearance, preservation, topology, "
                "orientation, or quality gates; inspect per-chart residuals"
            )
        ),
        "objects": {"before": before_obj.name, "after": after_obj.name},
        "images": {"generated": False, "reviewed": False},
        "qualitative_review": "PENDING" if gate_pass else "NOT_REQUESTED",
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
        f"DONE: boundary-cycle liner gate_pass={gate_pass}; "
        f"replacement_overlaps={len(replacement_overlaps)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
