"""Apply one explicit, reversible shallow-clearance patch as a shape key.

This tool does not choose a component or approve its appearance. It applies a
reviewed component mask, refuses displacements beyond an explicit cap, records
geometry evidence, and leaves qualitative approval pending.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    RESERVED_WALL_MM,
    SOURCE_NAME,
    connected_components,
    geometry_fingerprint,
    percentile,
    polygon_indices,
    sample_grid,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
    negative_orientation_locators,
    radial_coordinates,
)


GEOMETRIC_TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--shape-key", required=True)
    parser.add_argument("--relative-key", required=True)
    parser.add_argument(
        "--maximum-displacement-mm",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--reserved-margin-mm",
        type=float,
        default=RESERVED_WALL_MM,
    )
    parser.add_argument("--diffusion-iterations", type=int, default=6)
    parser.add_argument("--diffusion-factor", type=float, default=0.65)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(arguments)
    if args.maximum_displacement_mm <= 0.0:
        parser.error("--maximum-displacement-mm must be positive")
    if args.reserved_margin_mm < 0.0:
        parser.error("--reserved-margin-mm must not be negative")
    if args.diffusion_iterations < 0:
        parser.error("--diffusion-iterations must not be negative")
    if not 0.0 <= args.diffusion_factor <= 1.0:
        parser.error("--diffusion-factor must be between 0 and 1")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: {role} '{name}' has type/state "
            f"'{actual}', expected MESH"
        )
    return obj


def evaluated_geometry(
    obj: bpy.types.Object,
) -> tuple[list[Vector], list[tuple[int, ...]], list[int]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return (
            [
                evaluated.matrix_world @ vertex.co
                for vertex in mesh.vertices
            ],
            [tuple(polygon.vertices) for polygon in mesh.polygons],
            [polygon.material_index for polygon in mesh.polygons],
        )
    finally:
        evaluated.to_mesh_clear()


def point_margins(
    points: list[Vector],
    target_length: float,
    grid: list[list[float]],
) -> list[float]:
    result = []
    for point in points:
        normalized, angle, radius, _ = radial_coordinates(
            point,
            target_length,
        )
        result.append(radius - sample_grid(grid, normalized, angle))
    return result


def diffuse_component_displacement(
    required: list[float],
    component_mask: list[bool],
    neighbors: list[list[int]],
    iterations: int,
    factor: float,
) -> list[float]:
    displacement = [
        required[index] if component_mask[index] else 0.0
        for index in range(len(required))
    ]
    for _ in range(iterations):
        updated = displacement[:]
        for index, active in enumerate(component_mask):
            if not active:
                continue
            local = [
                displacement[neighbor]
                for neighbor in neighbors[index]
                if component_mask[neighbor]
            ]
            if local:
                updated[index] = max(
                    required[index],
                    sum(local) / len(local) * factor,
                )
        displacement = updated
    return displacement


def overlap_count(
    first_points: list[Vector],
    first_faces: list[tuple[int, ...]],
    second: bpy.types.Object,
) -> int:
    second_points, second_faces, _ = evaluated_geometry(second)
    first_tree = BVHTree.FromPolygons(
        first_points,
        first_faces,
        all_triangles=False,
    )
    second_tree = BVHTree.FromPolygons(
        second_points,
        second_faces,
        all_triangles=False,
    )
    return len(first_tree.overlap(second_tree))


def distribution(values: list[float]) -> dict:
    return {
        "minimum": round(min(values), 6),
        "median": round(percentile(values, 0.5), 6),
        "p95": round(percentile(values, 0.95), 6),
        "maximum": round(max(values), 6),
    }


def edge_ratio_distribution(
    before: list[Vector],
    after: list[Vector],
    edges: list[tuple[int, int]],
    affected: set[int],
) -> dict:
    ratios = []
    for first, second in edges:
        if first not in affected and second not in affected:
            continue
        original = (before[first] - before[second]).length
        if original <= 1.0e-9:
            continue
        ratios.append((after[first] - after[second]).length / original)
    return distribution(ratios)


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    if candidate.data.shape_keys is None:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: candidate '{candidate.name}' has no "
            "shape keys"
        )
    keys = candidate.data.shape_keys.key_blocks
    relative_key = keys.get(args.relative_key)
    if relative_key is None:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: relative key "
            f"'{args.relative_key}' is missing from '{candidate.name}'"
        )
    if keys.get(args.shape_key) is not None:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: shape key '{args.shape_key}' already "
            "exists; choose a new checkpoint or restore the pre-repair file"
        )
    if relative_key.value < 1.0 - GEOMETRIC_TOLERANCE_MM:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: relative key '{relative_key.name}' "
            f"has value {relative_key.value}, expected 1.0"
        )

    vertex_component, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: component {args.component} is "
            f"outside 0..{len(components) - 1}"
        )
    component_indices = components[args.component]
    component_mask = [
        vertex_component[index] == args.component
        for index in range(len(source.data.vertices))
    ]

    before, faces, material_indices = evaluated_geometry(candidate)
    source_faces = polygon_indices(source)
    if faces != source_faces:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: evaluated topology for "
            f"'{candidate.name}' does not match '{source.name}'"
        )
    target_length = float(candidate["target_length_mm"])
    grid, _ = cutter_grid(cutter)
    before_margins = point_margins(before, target_length, grid)
    violating = [
        index
        for index in component_indices
        if (
            before_margins[index]
            < args.reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
        )
    ]
    if not violating:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: component {args.component} has no "
            f"vertices below {args.reserved_margin_mm} mm reserved margin"
        )
    required = [
        (
            max(0.0, args.reserved_margin_mm - before_margins[index])
            if component_mask[index]
            else 0.0
        )
        for index in range(len(before))
    ]
    maximum_required = max(required[index] for index in component_indices)
    if (
        maximum_required
        > args.maximum_displacement_mm + GEOMETRIC_TOLERANCE_MM
    ):
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: component {args.component} requires "
            f"{maximum_required:.6f} mm displacement, exceeding explicit "
            f"cap {args.maximum_displacement_mm:.6f} mm"
        )

    field = diffuse_component_displacement(
        required,
        component_mask,
        mesh_neighbors(candidate.data),
        args.diffusion_iterations,
        args.diffusion_factor,
    )
    after = [point.copy() for point in before]
    for index in component_indices:
        _, _, _, direction = radial_coordinates(
            before[index],
            target_length,
        )
        after[index] += direction * field[index]

    repair = candidate.shape_key_add(name=args.shape_key, from_mix=False)
    repair.relative_key = relative_key
    inverse = candidate.matrix_world.inverted()
    for index, point in enumerate(after):
        repair.data[index].co = inverse @ point
    repair.value = 1.0

    group_name = f"MASK_{args.shape_key}"
    if candidate.vertex_groups.get(group_name) is not None:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: vertex group '{group_name}' already "
            "exists; restore the pre-repair file"
        )
    group = candidate.vertex_groups.new(name=group_name)
    affected = {
        index
        for index in component_indices
        if field[index] > GEOMETRIC_TOLERANCE_MM
    }
    for index in affected:
        group.add(
            [index],
            field[index] / maximum_required,
            "REPLACE",
        )

    candidate["latest_clearance_patch"] = repair.name
    candidate["latest_clearance_patch_component"] = args.component
    candidate["latest_clearance_patch_role"] = (
        "bounded shallow-clearance patch"
    )
    candidate["latest_clearance_patch_status"] = (
        "candidate_not_approved"
    )
    candidate["latest_clearance_patch_maximum_displacement_mm"] = (
        args.maximum_displacement_mm
    )
    candidate["latest_clearance_patch_reserved_margin_mm"] = (
        args.reserved_margin_mm
    )
    bpy.context.view_layer.update()
    evaluated_after, after_faces, after_material_indices = (
        evaluated_geometry(candidate)
    )
    if after_faces != faces:
        raise RuntimeError(
            f"BOUNDED_CLEARANCE_PATCH: applying '{repair.name}' changed "
            "evaluated face topology"
        )
    after_margins = point_margins(evaluated_after, target_length, grid)
    orientations = negative_orientation_locators(
        source,
        before,
        evaluated_after,
        faces,
    )
    component_displacements = [
        (evaluated_after[index] - before[index]).length
        for index in component_indices
    ]
    edges = [tuple(edge.vertices) for edge in source.data.edges]
    before_overlaps = overlap_count(before, faces, cutter)
    after_overlaps = overlap_count(evaluated_after, faces, cutter)

    report = {
        "tool": Path(__file__).name,
        "status": "bounded_clearance_patch_candidate_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "patch": {
            "shape_key": repair.name,
            "relative_key": relative_key.name,
            "vertex_group": group.name,
            "component": args.component,
            "component_vertices": len(component_indices),
            "initial_violating_vertices": len(violating),
            "affected_vertices": len(affected),
            "reserved_margin_mm": args.reserved_margin_mm,
            "maximum_displacement_cap_mm": (
                args.maximum_displacement_mm
            ),
            "diffusion_iterations": args.diffusion_iterations,
            "diffusion_factor": args.diffusion_factor,
        },
        "topology": {
            "source_vertices": len(source.data.vertices),
            "candidate_vertices": len(candidate.data.vertices),
            "source_faces": len(source.data.polygons),
            "candidate_faces": len(candidate.data.polygons),
            "face_indices_unchanged": after_faces == source_faces,
            "material_assignments_unchanged": (
                after_material_indices == material_indices
            ),
        },
        "clearance": {
            "before_vertices_below_cutter": sum(
                margin < -GEOMETRIC_TOLERANCE_MM
                for margin in before_margins
            ),
            "after_vertices_below_cutter": sum(
                margin < -GEOMETRIC_TOLERANCE_MM
                for margin in after_margins
            ),
            "before_vertices_below_reserved_margin": sum(
                margin
                < args.reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
                for margin in before_margins
            ),
            "after_vertices_below_reserved_margin": sum(
                margin
                < args.reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
                for margin in after_margins
            ),
            "before_triangle_overlaps": before_overlaps,
            "after_triangle_overlaps": after_overlaps,
            "component_after_vertices_below_cutter": sum(
                after_margins[index] < -GEOMETRIC_TOLERANCE_MM
                for index in component_indices
            ),
            "component_after_vertices_below_reserved_margin": sum(
                after_margins[index]
                < args.reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
                for index in component_indices
            ),
            "component_minimum_before_margin_mm": round(
                min(before_margins[index] for index in component_indices),
                6,
            ),
            "component_minimum_after_margin_mm": round(
                min(after_margins[index] for index in component_indices),
                6,
            ),
        },
        "distortion": {
            "component_displacement_mm": distribution(
                component_displacements
            ),
            "affected_edge_ratio": edge_ratio_distribution(
                before,
                evaluated_after,
                edges,
                affected,
            ),
            "negative_orientation_locators": orientations,
        },
        "fingerprints": {
            "before": geometry_fingerprint(
                before,
                faces,
                material_indices,
            ),
            "after": geometry_fingerprint(
                evaluated_after,
                after_faces,
                after_material_indices,
            ),
        },
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
        f"DONE: created reversible shape key '{repair.name}' on "
        f"component {args.component}; qualitative review remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
