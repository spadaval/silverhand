"""Sweep bounded cutter-conforming reconstruction fields.

This diagnostic does not save geometry. It projects explicitly selected
clearance-failure clusters to the cutter plus the reserved wall, solves a
harmonic transition over a bounded number of topology rings, and reports
clearance, orientation, and edge distortion for each requested ring count.
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


TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument(
        "--clusters",
        default="all",
        help="Comma-separated violation-cluster indices or 'all'.",
    )
    parser.add_argument(
        "--rings",
        default="2,4,6,8,12,16",
        help="Comma-separated positive topology-ring counts.",
    )
    parser.add_argument("--iterations", type=int, default=400)
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
    return args


def violation_clusters(
    component: set[int],
    margins: list[float],
    neighbors: list[list[int]],
) -> list[list[int]]:
    unseen = {
        index
        for index in component
        if margins[index] < RESERVED_WALL_MM - TOLERANCE_MM
    }
    clusters = []
    while unseen:
        start = unseen.pop()
        stack = [start]
        cluster = {start}
        while stack:
            current = stack.pop()
            for neighbor in neighbors[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    cluster.add(neighbor)
                    stack.append(neighbor)
        clusters.append(sorted(cluster))
    clusters.sort(
        key=lambda value: (
            -len(value),
            min(margins[index] for index in value),
        )
    )
    return clusters


def parse_cluster_selection(
    value: str,
    cluster_count: int,
) -> list[int]:
    if value == "all":
        return list(range(cluster_count))
    try:
        result = sorted({int(item) for item in value.split(",")})
    except ValueError as error:
        raise RuntimeError(
            f"LOCAL_RECONSTRUCTION_SWEEP: --clusters '{value}' contains "
            f"a non-integer value ({error})"
        ) from error
    invalid = [
        index for index in result if not 0 <= index < cluster_count
    ]
    if invalid:
        raise RuntimeError(
            "LOCAL_RECONSTRUCTION_SWEEP: cluster indices "
            f"{invalid} are outside 0..{cluster_count - 1}"
        )
    return result


def expanded_distances(
    core: set[int],
    component: set[int],
    neighbors: list[list[int]],
    rings: int,
) -> dict[int, int]:
    distances = {index: 0 for index in core}
    frontier = set(core)
    for distance in range(1, rings + 1):
        following = {
            neighbor
            for index in frontier
            for neighbor in neighbors[index]
            if neighbor in component and neighbor not in distances
        }
        for index in following:
            distances[index] = distance
        frontier = following
        if not frontier:
            break
    return distances


def harmonic_displacement(
    required: list[float],
    core: set[int],
    distances: dict[int, int],
    neighbors: list[list[int]],
    rings: int,
    iterations: int,
) -> list[float]:
    field = [0.0] * len(required)
    active = set(distances)
    boundary = {
        index for index, distance in distances.items() if distance == rings
    }
    for index in active:
        if index in core:
            field[index] = required[index]
        else:
            normalized = distances[index] / rings
            field[index] = required[index] * (
                1.0 - normalized * normalized * (3.0 - 2.0 * normalized)
            )
    for _ in range(iterations):
        updated = field[:]
        maximum_change = 0.0
        for index in active:
            if index in core:
                updated[index] = required[index]
                continue
            if index in boundary:
                updated[index] = 0.0
                continue
            adjacent = [
                neighbor
                for neighbor in neighbors[index]
                if neighbor in active
            ]
            if not adjacent:
                continue
            value = sum(field[neighbor] for neighbor in adjacent) / len(
                adjacent
            )
            updated[index] = value
            maximum_change = max(
                maximum_change,
                abs(value - field[index]),
            )
        field = updated
        if maximum_change < 1.0e-6:
            break
    return field


def overlap_count(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    cutter: bpy.types.Object,
) -> int:
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    candidate_tree = BVHTree.FromPolygons(
        points,
        faces,
        all_triangles=False,
    )
    cutter_tree = BVHTree.FromPolygons(
        cutter_points,
        cutter_faces,
        all_triangles=False,
    )
    return len(candidate_tree.overlap(cutter_tree))


def main() -> int:
    args = parse_args()
    source = bpy.data.objects.get(SOURCE_NAME)
    candidate = bpy.data.objects.get(CANDIDATE_NAME)
    cutter = bpy.data.objects.get(CUTTER_NAME)
    for obj, role, name in (
        (source, "immutable source", SOURCE_NAME),
        (candidate, "fitted-surface candidate", CANDIDATE_NAME),
        (cutter, "clearance cutter", CUTTER_NAME),
    ):
        if obj is None or obj.type != "MESH":
            actual = "missing" if obj is None else obj.type
            raise RuntimeError(
                f"LOCAL_RECONSTRUCTION_SWEEP: {role} '{name}' has state "
                f"'{actual}', expected MESH"
            )

    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"LOCAL_RECONSTRUCTION_SWEEP: component {args.component} is "
            f"outside 0..{len(components) - 1}"
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

    edges = [tuple(edge.vertices) for edge in source.data.edges]
    variants = []
    for rings in args.rings:
        distances = expanded_distances(
            core,
            component,
            neighbors,
            rings,
        )
        field = harmonic_displacement(
            required,
            core,
            distances,
            neighbors,
            rings,
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
        after_margins = point_margins(after, target_length, grid)
        orientations = negative_orientation_locators(
            source,
            before,
            after,
            faces,
        )
        variants.append(
            {
                "rings": rings,
                "transition_vertices": len(distances),
                "affected_vertices": len(affected),
                "selected_component_vertices_below_cutter": sum(
                    after_margins[index] < -TOLERANCE_MM
                    for index in component
                ),
                "selected_component_vertices_below_reserved_margin": sum(
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
                "negative_orientation_locators": orientations,
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
        "cluster_summary": [
            {
                "cluster": index,
                "vertices_below_reserved_margin": len(cluster),
                "minimum_margin_mm": round(
                    min(before_margins[vertex] for vertex in cluster),
                    6,
                ),
            }
            for index, cluster in enumerate(clusters)
        ],
        "before": {
            "component_vertices_below_cutter": sum(
                before_margins[index] < -TOLERANCE_MM
                for index in component
            ),
            "component_vertices_below_reserved_margin": sum(
                before_margins[index]
                < RESERVED_WALL_MM - TOLERANCE_MM
                for index in component
            ),
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
        f"DONE: swept {len(variants)} bounded reconstruction variants for "
        f"component {args.component}; no geometry was saved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
