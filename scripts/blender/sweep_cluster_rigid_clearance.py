"""Sweep relief-preserving cluster-rigid clearance fields.

Each selected violation cluster receives one coherent rigid translation along
its mean radial direction. Only the scalar transition weight is harmonically
blended through the source component. This diagnostic saves no geometry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

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
    parser.add_argument(
        "--rings",
        default="2,4,6,8,12,16",
        help="Comma-separated positive topology-ring counts.",
    )
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--maximum-translation-mm", type=float, default=100.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[separator + 1 :])
    try:
        args.rings = [int(value) for value in args.rings.split(",")]
    except ValueError as error:
        parser.error(f"--rings contains a non-integer value: {error}")
    if not args.rings or any(value <= 0 for value in args.rings):
        parser.error("--rings must contain positive integers")
    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    if args.maximum_translation_mm <= 0:
        parser.error("--maximum-translation-mm must be positive")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"CLUSTER_RIGID_SWEEP: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def cluster_translation(
    cluster: list[int],
    points: list[Vector],
    target_length: float,
    grid: list[list[float]],
    maximum: float,
) -> tuple[Vector, float]:
    direction = sum(
        (
            radial_coordinates(points[index], target_length)[3]
            for index in cluster
        ),
        Vector(),
    )
    if direction.length <= 1.0e-9:
        raise RuntimeError(
            "CLUSTER_RIGID_SWEEP: selected cluster has no coherent mean "
            "radial direction"
        )
    direction.normalize()
    low = 0.0
    high = maximum
    for _ in range(48):
        middle = (low + high) * 0.5
        margins = point_margins(
            [points[index] + direction * middle for index in cluster],
            target_length,
            grid,
        )
        if min(margins) >= RESERVED_WALL_MM:
            high = middle
        else:
            low = middle
    if high >= maximum - 1.0e-6:
        raise RuntimeError(
            "CLUSTER_RIGID_SWEEP: cluster cannot clear within "
            f"{maximum:.3f} mm along its mean radial direction"
        )
    return direction, high + 0.05


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"CLUSTER_RIGID_SWEEP: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )

    component = set(components[args.component])
    before, faces, _ = evaluated_geometry(candidate)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    clusters = violation_clusters(component, before_margins, neighbors)
    selected_clusters = parse_cluster_selection(
        args.clusters,
        len(clusters),
    )
    motions = []
    for cluster_index in selected_clusters:
        cluster = clusters[cluster_index]
        direction, distance = cluster_translation(
            cluster,
            before,
            target_length,
            grid,
            args.maximum_translation_mm,
        )
        motions.append((cluster_index, cluster, direction, distance))

    edges = [tuple(edge.vertices) for edge in source.data.edges]
    variants = []
    for rings in args.rings:
        after = [point.copy() for point in before]
        affected = set()
        motion_records = []
        for cluster_index, cluster, direction, distance in motions:
            core = set(cluster)
            distances = expanded_distances(
                core,
                component,
                neighbors,
                rings,
            )
            required = [0.0] * len(before)
            for index in core:
                required[index] = 1.0
            weights = harmonic_displacement(
                required,
                core,
                distances,
                neighbors,
                rings,
                args.iterations,
            )
            cluster_affected = {
                index
                for index, weight in enumerate(weights)
                if weight > TOLERANCE_MM
            }
            affected.update(cluster_affected)
            for index in cluster_affected:
                after[index] += direction * distance * weights[index]
            motion_records.append(
                {
                    "cluster": cluster_index,
                    "core_vertices": len(cluster),
                    "transition_vertices": len(distances),
                    "affected_vertices": len(cluster_affected),
                    "direction": [round(value, 6) for value in direction],
                    "translation_mm": round(distance, 6),
                }
            )

        after_margins = point_margins(after, target_length, grid)
        variants.append(
            {
                "rings": rings,
                "motions": motion_records,
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
                "negative_orientation_locators": (
                    negative_orientation_locators(
                        source,
                        before,
                        after,
                        faces,
                    )
                ),
                "affected_edge_ratio": edge_ratio_distribution(
                    before,
                    after,
                    edges,
                    affected,
                ),
            }
        )

    report = {
        "tool": Path(__file__).name,
        "status": "diagnostic_sweep_only_no_geometry_saved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "selected_clusters": selected_clusters,
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
        f"DONE: swept {len(variants)} cluster-rigid variants for component "
        f"{args.component}; no geometry was saved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
