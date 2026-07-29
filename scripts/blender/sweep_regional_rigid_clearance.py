"""Sweep shared regional rigid-clearance fields for one source component.

The selected component moves rigidly. Every nearby source vertex receives the
same translation with a smooth Euclidean falloff. This diagnostic saves no
geometry and does not approve any variant.
"""

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


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument(
        "--falloffs-mm",
        default="15,25,35,45",
        help="Comma-separated positive falloff distances.",
    )
    parser.add_argument("--maximum-translation-mm", type=float, default=100.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[separator + 1 :])
    try:
        args.falloffs_mm = [
            float(value) for value in args.falloffs_mm.split(",")
        ]
    except ValueError as error:
        parser.error(f"--falloffs-mm contains a non-number: {error}")
    if not args.falloffs_mm or any(
        value <= 0.0 for value in args.falloffs_mm
    ):
        parser.error("--falloffs-mm must contain positive values")
    if args.maximum_translation_mm <= 0.0:
        parser.error("--maximum-translation-mm must be positive")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"REGIONAL_RIGID_SWEEP: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def smoothstep_falloff(distance: float, limit: float) -> float:
    normalized = min(1.0, distance / limit)
    return 1.0 - normalized * normalized * (3.0 - 2.0 * normalized)


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"REGIONAL_RIGID_SWEEP: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )
    component = components[args.component]
    component_set = set(component)
    before, faces, _ = evaluated_geometry(candidate)
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
            f"REGIONAL_RIGID_SWEEP: component {args.component} has no "
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
            f"REGIONAL_RIGID_SWEEP: component {args.component} violating "
            "vertices have no coherent mean radial direction"
        )
    direction.normalize()

    low = 0.0
    high = args.maximum_translation_mm
    for _ in range(40):
        middle = (low + high) * 0.5
        translated = [
            before[index] + direction * middle for index in component
        ]
        margins = point_margins(translated, target_length, grid)
        if min(margins) >= RESERVED_WALL_MM:
            high = middle
        else:
            low = middle
    if high >= args.maximum_translation_mm - 1.0e-6:
        raise RuntimeError(
            f"REGIONAL_RIGID_SWEEP: component {args.component} cannot clear "
            f"within {args.maximum_translation_mm:.3f} mm along its mean "
            "radial direction"
        )
    translation = high + 0.05

    tree = KDTree(len(component))
    for offset, index in enumerate(component):
        tree.insert(before[index], offset)
    tree.balance()
    edges = [tuple(edge.vertices) for edge in source.data.edges]
    variants = []
    for falloff in args.falloffs_mm:
        weights = []
        after = [point.copy() for point in before]
        for index, point in enumerate(before):
            if index in component_set:
                weight = 1.0
            else:
                _, _, distance = tree.find(point)
                weight = smoothstep_falloff(distance, falloff)
            weights.append(weight)
            if weight > 0.0:
                after[index] += direction * translation * weight
        after_margins = point_margins(after, target_length, grid)
        affected = {
            index
            for index, weight in enumerate(weights)
            if weight > TOLERANCE_MM
        }
        orientations = negative_orientation_locators(
            source,
            before,
            after,
            faces,
        )
        variants.append(
            {
                "falloff_mm": falloff,
                "affected_vertices": len(affected),
                "component_vertices_below_cutter": sum(
                    after_margins[index] < -TOLERANCE_MM
                    for index in component
                ),
                "component_vertices_below_reserved_margin": sum(
                    after_margins[index]
                    < RESERVED_WALL_MM - TOLERANCE_MM
                    for index in component
                ),
                "global_vertices_below_cutter": sum(
                    margin < -TOLERANCE_MM for margin in after_margins
                ),
                "global_vertices_below_reserved_margin": sum(
                    margin < RESERVED_WALL_MM - TOLERANCE_MM
                    for margin in after_margins
                ),
                "global_triangle_overlaps": overlap_count(
                    after,
                    faces,
                    cutter,
                ),
                "affected_edge_ratio": edge_ratio_distribution(
                    before,
                    after,
                    edges,
                    affected,
                ),
                "negative_orientation_locators": orientations,
            }
        )

    report = {
        "tool": Path(__file__).name,
        "status": "diagnostic_sweep_only_no_geometry_saved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "component_vertices": len(component),
        "violating_vertices": len(violating),
        "translation_direction": [
            round(value, 6) for value in direction
        ],
        "translation_mm": round(translation, 6),
        "before": {
            "global_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in before_margins
            ),
            "global_vertices_below_reserved_margin": sum(
                margin < RESERVED_WALL_MM - TOLERANCE_MM
                for margin in before_margins
            ),
            "global_triangle_overlaps": overlap_count(
                before,
                faces,
                cutter,
            ),
        },
        "variants": variants,
        "promotion": "NOT_PROMOTED",
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    print(
        f"DONE: swept {len(variants)} shared regional fields for component "
        f"{args.component}; no geometry was saved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
