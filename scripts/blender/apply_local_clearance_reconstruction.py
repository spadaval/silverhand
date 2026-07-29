"""Apply one reviewed cutter-conforming local reconstruction as a shape key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    edge_ratio_distribution,
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
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
    negative_orientation_locators,
    radial_coordinates,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    expanded_distances,
    harmonic_displacement,
    overlap_count,
    parse_cluster_selection,
    violation_clusters,
)


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--clusters", required=True)
    parser.add_argument("--rings", type=int, required=True)
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--shape-key", required=True)
    parser.add_argument("--relative-key", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.rings <= 0:
        parser.error("--rings must be positive")
    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: {role} '{name}' has state "
            f"'{actual}', expected MESH"
        )
    return obj


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    if candidate.data.shape_keys is None:
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: candidate '{candidate.name}' "
            "has no shape keys"
        )
    keys = candidate.data.shape_keys.key_blocks
    relative_key = keys.get(args.relative_key)
    if relative_key is None:
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: relative key "
            f"'{args.relative_key}' is missing"
        )
    if keys.get(args.shape_key) is not None:
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: shape key "
            f"'{args.shape_key}' already exists"
        )
    if relative_key.value < 1.0 - TOLERANCE_MM:
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: relative key "
            f"'{relative_key.name}' has value {relative_key.value}, "
            "expected 1.0"
        )

    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: component {args.component} "
            f"is outside 0..{len(components) - 1}"
        )
    component = set(components[args.component])
    before, faces, material_indices = evaluated_geometry(candidate)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    clusters = violation_clusters(component, before_margins, neighbors)
    selected_clusters = parse_cluster_selection(
        args.clusters,
        len(clusters),
    )
    core = {
        index
        for cluster_index in selected_clusters
        for index in clusters[cluster_index]
    }
    required = [0.0] * len(before)
    for index in core:
        required[index] = max(
            0.0,
            RESERVED_WALL_MM - before_margins[index],
        )
    distances = expanded_distances(
        core,
        component,
        neighbors,
        args.rings,
    )
    field = harmonic_displacement(
        required,
        core,
        distances,
        neighbors,
        args.rings,
        args.iterations,
    )
    after = [point.copy() for point in before]
    affected = {
        index for index, value in enumerate(field) if value > TOLERANCE_MM
    }
    for index in affected:
        _, _, _, direction = radial_coordinates(
            before[index],
            target_length,
        )
        after[index] += direction * field[index]

    repair = candidate.shape_key_add(
        name=args.shape_key,
        from_mix=False,
    )
    repair.relative_key = relative_key
    inverse = candidate.matrix_world.inverted()
    for index, point in enumerate(after):
        repair.data[index].co = inverse @ point
    repair.value = 1.0

    group_name = f"MASK_{args.shape_key}"
    if candidate.vertex_groups.get(group_name) is not None:
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: vertex group "
            f"'{group_name}' already exists"
        )
    group = candidate.vertex_groups.new(name=group_name)
    maximum = max(field)
    for index in affected:
        group.add([index], field[index] / maximum, "REPLACE")

    candidate["latest_clearance_patch"] = repair.name
    candidate["latest_clearance_patch_component"] = args.component
    candidate["latest_clearance_patch_role"] = (
        "bounded cutter-conforming local reconstruction"
    )
    candidate["latest_clearance_patch_status"] = "candidate_not_approved"
    candidate["latest_clearance_patch_clusters"] = args.clusters
    candidate["latest_clearance_patch_topology_rings"] = args.rings
    bpy.context.view_layer.update()

    evaluated_after, after_faces, after_material_indices = (
        evaluated_geometry(candidate)
    )
    after_margins = point_margins(
        evaluated_after,
        target_length,
        grid,
    )
    orientations = negative_orientation_locators(
        source,
        before,
        evaluated_after,
        faces,
    )
    if orientations["count"]:
        raise RuntimeError(
            f"LOCAL_CLEARANCE_RECONSTRUCTION: '{repair.name}' creates "
            f"{orientations['count']} negative-orientation locator(s); "
            "restore the input checkpoint and choose another field"
        )
    edges = [tuple(edge.vertices) for edge in source.data.edges]
    report = {
        "tool": Path(__file__).name,
        "status": "local_reconstruction_candidate_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "patch": {
            "shape_key": repair.name,
            "relative_key": relative_key.name,
            "vertex_group": group.name,
            "component": args.component,
            "selected_clusters": selected_clusters,
            "topology_rings": args.rings,
            "harmonic_iterations": args.iterations,
            "core_vertices": len(core),
            "transition_vertices": len(distances),
            "affected_vertices": len(affected),
            "maximum_displacement_mm": round(maximum, 6),
        },
        "topology": {
            "source_vertices": len(source.data.vertices),
            "candidate_vertices": len(candidate.data.vertices),
            "source_faces": len(source.data.polygons),
            "candidate_faces": len(candidate.data.polygons),
            "face_indices_unchanged": after_faces == faces,
            "material_assignments_unchanged": (
                after_material_indices == material_indices
            ),
        },
        "clearance": {
            "before_global_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in before_margins
            ),
            "after_global_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in after_margins
            ),
            "before_global_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in before_margins
            ),
            "after_global_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in after_margins
            ),
            "before_global_triangle_overlaps": overlap_count(
                before,
                faces,
                cutter,
            ),
            "after_global_triangle_overlaps": overlap_count(
                evaluated_after,
                after_faces,
                cutter,
            ),
            "after_component_vertices_below_cutter": sum(
                after_margins[index] < -TOLERANCE_MM
                for index in component
            ),
            "after_component_vertices_below_reserved_margin": sum(
                after_margins[index]
                < RESERVED_WALL_MM - TOLERANCE_MM
                for index in component
            ),
        },
        "distortion": {
            "affected_edge_ratio": edge_ratio_distribution(
                before,
                evaluated_after,
                edges,
                affected,
            ),
            "negative_orientation_locators": orientations,
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
        f"DONE: created reversible local reconstruction '{repair.name}'; "
        "qualitative review remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
