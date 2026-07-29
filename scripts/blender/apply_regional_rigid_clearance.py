"""Apply one reviewed shared regional rigid-clearance field as a shape key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

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
    negative_orientation_locators,
    radial_coordinates,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    overlap_count,
)
from sweep_regional_rigid_clearance import (  # noqa: E402
    smoothstep_falloff,
)


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--falloff-mm", type=float, required=True)
    parser.add_argument("--maximum-translation-mm", type=float, default=100.0)
    parser.add_argument("--shape-key", required=True)
    parser.add_argument("--relative-key", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.falloff_mm <= 0.0:
        parser.error("--falloff-mm must be positive")
    if args.maximum_translation_mm <= 0.0:
        parser.error("--maximum-translation-mm must be positive")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    if candidate.data.shape_keys is None:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: candidate '{candidate.name}' has no "
            "shape keys"
        )
    keys = candidate.data.shape_keys.key_blocks
    relative_key = keys.get(args.relative_key)
    if relative_key is None:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: relative key '{args.relative_key}' "
            "is missing"
        )
    if keys.get(args.shape_key) is not None:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: shape key '{args.shape_key}' already "
            "exists"
        )
    if relative_key.value < 1.0 - TOLERANCE_MM:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: relative key '{relative_key.name}' has "
            f"value {relative_key.value}, expected 1.0"
        )

    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )
    component = components[args.component]
    component_set = set(component)
    before, faces, material_indices = evaluated_geometry(candidate)
    target_length = float(candidate["target_length_mm"])
    grid, _ = cutter_grid(cutter)
    before_margins = point_margins(before, target_length, grid)
    violating = [
        index
        for index in component
        if before_margins[index]
        < RESERVED_WALL_MM - TOLERANCE_MM
    ]
    if not violating:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: component {args.component} has no "
            "clearance failures"
        )
    direction = sum(
        (
            radial_coordinates(before[index], target_length)[3]
            for index in violating
        ),
        Vector(),
    )
    if direction.length <= 1.0e-9:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: component {args.component} violating "
            "vertices have no coherent mean radial direction"
        )
    direction.normalize()
    low = 0.0
    high = args.maximum_translation_mm
    for _ in range(40):
        middle = (low + high) * 0.5
        margins = point_margins(
            [
                before[index] + direction * middle
                for index in component
            ],
            target_length,
            grid,
        )
        if min(margins) >= RESERVED_WALL_MM:
            high = middle
        else:
            low = middle
    if high >= args.maximum_translation_mm - 1.0e-6:
        raise RuntimeError(
            f"REGIONAL_RIGID_APPLY: component {args.component} cannot clear "
            f"within {args.maximum_translation_mm:.3f} mm"
        )
    translation = high + 0.05

    tree = KDTree(len(component))
    for offset, index in enumerate(component):
        tree.insert(before[index], offset)
    tree.balance()
    weights = []
    after = [point.copy() for point in before]
    for index, point in enumerate(before):
        if index in component_set:
            weight = 1.0
        else:
            _, _, distance = tree.find(point)
            weight = smoothstep_falloff(
                distance,
                args.falloff_mm,
            )
        weights.append(weight)
        if weight > 0.0:
            after[index] += direction * translation * weight
    affected = {
        index
        for index, weight in enumerate(weights)
        if weight > TOLERANCE_MM
    }

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
    group = candidate.vertex_groups.new(name=group_name)
    for index in affected:
        group.add([index], weights[index], "REPLACE")

    candidate["latest_clearance_patch"] = repair.name
    candidate["latest_clearance_patch_component"] = args.component
    candidate["latest_clearance_patch_role"] = (
        "shared regional rigid-clearance field"
    )
    candidate["latest_clearance_patch_status"] = "candidate_not_approved"
    candidate["latest_clearance_patch_falloff_mm"] = args.falloff_mm
    candidate["latest_clearance_patch_translation_mm"] = translation
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
            f"REGIONAL_RIGID_APPLY: '{repair.name}' creates "
            f"{orientations['count']} negative-orientation locator(s); "
            "restore the input checkpoint and choose another field"
        )
    edges = [tuple(edge.vertices) for edge in source.data.edges]
    report = {
        "tool": Path(__file__).name,
        "status": "regional_rigid_candidate_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "patch": {
            "shape_key": repair.name,
            "relative_key": relative_key.name,
            "vertex_group": group.name,
            "component": args.component,
            "component_vertices": len(component),
            "initial_violating_vertices": len(violating),
            "affected_vertices": len(affected),
            "falloff_mm": args.falloff_mm,
            "translation_mm": round(translation, 6),
            "translation_direction": [
                round(value, 6) for value in direction
            ],
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
        f"DONE: created reversible regional field '{repair.name}'; "
        "qualitative review remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
