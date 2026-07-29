"""Measure whether one fitted-surface component duplicates another.

This diagnostic saves no geometry. It compares evaluated component vertices,
optionally limited to explicit clearance-failure clusters, against their
nearest vertices on a second source component.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils.kdtree import KDTree

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
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    mesh_neighbors,
    radial_coordinates,
)
from sweep_local_clearance_reconstruction import (  # noqa: E402
    parse_cluster_selection,
    violation_clusters,
)


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--neighbor", type=int, required=True)
    parser.add_argument(
        "--clusters",
        default="all",
        help="Clearance-failure clusters on --component, or 'all'.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[separator + 1 :])


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"COMPONENT_PROXIMITY: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)

    def percentile(fraction: float) -> float:
        return ordered[round((len(ordered) - 1) * fraction)]

    return {
        "minimum": round(ordered[0], 6),
        "median": round(percentile(0.5), 6),
        "p95": round(percentile(0.95), 6),
        "maximum": round(ordered[-1], 6),
    }


def proximity(
    indices: list[int],
    neighbor_indices: list[int],
    points,
    target_length: float,
) -> dict:
    tree = KDTree(len(neighbor_indices))
    for offset, index in enumerate(neighbor_indices):
        tree.insert(points[index], offset)
    tree.balance()

    distances = []
    radial_deltas = []
    station_deltas = []
    nearest_records = []
    for index in indices:
        _, offset, distance = tree.find(points[index])
        neighbor_index = neighbor_indices[offset]
        station, radial, _, _ = radial_coordinates(
            points[index],
            target_length,
        )
        neighbor_station, neighbor_radial, _, _ = radial_coordinates(
            points[neighbor_index],
            target_length,
        )
        distances.append(distance)
        radial_deltas.append(radial - neighbor_radial)
        station_deltas.append(station - neighbor_station)
        nearest_records.append((distance, index, neighbor_index))

    thresholds = (0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
    return {
        "vertices": len(indices),
        "nearest_distance_mm": distribution(distances),
        "radial_delta_mm": distribution(radial_deltas),
        "station_delta_mm": distribution(station_deltas),
        "counts_within_mm": {
            str(limit): sum(value <= limit for value in distances)
            for limit in thresholds
        },
        "ten_closest_pairs": [
            {
                "distance_mm": round(distance, 6),
                "component_vertex": index,
                "neighbor_vertex": neighbor_index,
            }
            for distance, index, neighbor_index in sorted(nearest_records)[:10]
        ],
    }


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    _, components = connected_components(source)
    for value, role in (
        (args.component, "component"),
        (args.neighbor, "neighbor"),
    ):
        if not 0 <= value < len(components):
            raise RuntimeError(
                f"COMPONENT_PROXIMITY: {role} {value} is outside "
                f"0..{len(components) - 1}"
            )

    points, _, _ = evaluated_geometry(candidate)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    margins = point_margins(points, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    component = set(components[args.component])
    neighbor_component = list(components[args.neighbor])
    clusters = violation_clusters(component, margins, neighbors)
    selected_clusters = parse_cluster_selection(
        args.clusters,
        len(clusters),
    )
    selected = sorted(
        {
            index
            for cluster_index in selected_clusters
            for index in clusters[cluster_index]
        }
    )
    report = {
        "tool": Path(__file__).name,
        "status": "diagnostic_only_no_geometry_saved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "neighbor": args.neighbor,
        "selected_clusters": selected_clusters,
        "selected_cluster_vertices": proximity(
            selected,
            neighbor_component,
            points,
            target_length,
        ),
        "whole_component": proximity(
            sorted(component),
            neighbor_component,
            points,
            target_length,
        ),
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
        f"DONE: compared component {args.component} to component "
        f"{args.neighbor}; no geometry was saved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
