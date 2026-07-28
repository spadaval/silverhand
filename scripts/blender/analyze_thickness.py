"""Estimate per-face inward wall thickness for editable closed solids.

Each polygon center casts a line through the same constituent. Results are
advisory measurements: concave geometry may hit a nearby unrelated wall, and no
manufacturing minimum is assumed unless supplied.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils.bvhtree import BVHTree


DEFAULT_COLLECTION = "20_SALVAGE_WORKING"
RAY_OFFSET_MM = 1.0e-4
RAY_ADVANCE_MM = 1.0e-2
PROBE_OFFSET_MM = 0.25
DISTINCT_HIT_TOLERANCE_MM = 5.0e-3
MAX_RAY_DISTANCE_MM = 2000.0
MAX_LINE_HITS = 256


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--threshold-mm",
        type=float,
        help="optional advisory threshold; does not establish design authority",
    )
    args = parser.parse_args(arguments)
    if args.threshold_mm is not None and args.threshold_mm <= 0.0:
        parser.error("--threshold-mm must be positive")
    return args


def percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        raise ValueError("cannot calculate percentile of an empty list")
    position = (len(sorted_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    blend = position - lower
    return (
        sorted_values[lower] * (1.0 - blend)
        + sorted_values[upper] * blend
    )


def ray_hit_distances(
    bvh: BVHTree,
    origin,
    direction,
) -> list[float]:
    distances = []
    travelled = 0.0
    current = origin.copy()
    for _ in range(MAX_LINE_HITS):
        location, _, _, distance = bvh.ray_cast(
            current,
            direction,
            MAX_RAY_DISTANCE_MM - travelled,
        )
        if location is None:
            return distances
        travelled += float(distance)
        if (
            not distances
            or travelled - distances[-1] > DISTINCT_HIT_TOLERANCE_MM
        ):
            distances.append(travelled)
        current = location + direction * RAY_ADVANCE_MM
        travelled += RAY_ADVANCE_MM
        if travelled >= MAX_RAY_DISTANCE_MM:
            return distances
    raise RuntimeError(
        "Cannot analyze thickness: ray traversal exceeded "
        f"{MAX_LINE_HITS} surface hits"
    )


def thickness_along_normal(bvh: BVHTree, center, normal) -> float | None:
    candidates = []
    for side in (1.0, -1.0):
        outward = normal * side
        origin = center + outward * PROBE_OFFSET_MM
        hits = ray_hit_distances(bvh, origin, -outward)
        if len(hits) < 2:
            continue
        if hits[0] > PROBE_OFFSET_MM * 2.0:
            continue
        span = hits[1] - hits[0]
        if span > DISTINCT_HIT_TOLERANCE_MM:
            candidates.append(span)
    return min(candidates) if candidates else None


def inspect_object(
    obj: bpy.types.Object,
    threshold_mm: float | None,
) -> dict:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    bvh = BVHTree.FromPolygons(
        points,
        [tuple(polygon.vertices) for polygon in obj.data.polygons],
        all_triangles=False,
    )
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    measurements = []
    no_hit_faces = []
    for polygon in obj.data.polygons:
        center = obj.matrix_world @ polygon.center
        normal = normal_matrix @ polygon.normal
        if normal.length_squared == 0.0:
            no_hit_faces.append(polygon.index)
            continue
        normal.normalize()
        distance = thickness_along_normal(bvh, center, normal)
        if distance is None:
            no_hit_faces.append(polygon.index)
            continue
        measurements.append(distance)

    measurements.sort()
    if not measurements:
        raise RuntimeError(
            f"Cannot analyze thickness: object '{obj.name}' produced no "
            "inward ray hits"
        )
    below_threshold = (
        sum(value < threshold_mm for value in measurements)
        if threshold_mm is not None
        else None
    )
    return {
        "object": obj.name,
        "construction_region": obj.get(
            "construction_region",
            "UNASSIGNED",
        ),
        "declared_local_thickness_mm": obj.get("local_thickness_mm"),
        "faces": len(obj.data.polygons),
        "measured_faces": len(measurements),
        "no_hit_faces": len(no_hit_faces),
        "no_hit_face_indices": no_hit_faces,
        "minimum_mm": round(measurements[0], 6),
        "p05_mm": round(percentile(measurements, 0.05), 6),
        "median_mm": round(percentile(measurements, 0.50), 6),
        "p95_mm": round(percentile(measurements, 0.95), 6),
        "maximum_mm": round(measurements[-1], 6),
        "below_threshold_faces": below_threshold,
        "below_threshold_fraction": (
            round(below_threshold / len(measurements), 6)
            if below_threshold is not None
            else None
        ),
    }


def main() -> int:
    args = parse_args()
    collection = bpy.data.collections.get(args.collection)
    if collection is None:
        raise RuntimeError(
            f"Cannot analyze thickness: collection '{args.collection}' is "
            "missing"
        )
    objects = sorted(
        (
            obj
            for obj in collection.all_objects
            if obj.type == "MESH" and obj.name.startswith("REG_")
        ),
        key=lambda obj: obj.name,
    )
    if not objects:
        raise RuntimeError(
            f"Cannot analyze thickness: collection '{collection.name}' "
            "contains no REG_* mesh objects"
        )
    reports = [
        inspect_object(obj, args.threshold_mm) for obj in objects
    ]
    no_hit_objects = [
        report["object"] for report in reports if report["no_hit_faces"]
    ]
    below_threshold_objects = (
        [
            report["object"]
            for report in reports
            if report["below_threshold_faces"]
        ]
        if args.threshold_mm is not None
        else None
    )
    report = {
        "tool": "analyze_thickness.py",
        "status": "advisory_measurement_not_manufacturing_approval",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "collection": collection.name,
        "threshold_mm": args.threshold_mm,
        "summary": {
            "objects": len(reports),
            "faces": sum(report["faces"] for report in reports),
            "measured_faces": sum(
                report["measured_faces"] for report in reports
            ),
            "objects_with_no_hit_faces": len(no_hit_objects),
            "no_hit_faces": sum(
                report["no_hit_faces"] for report in reports
            ),
            "minimum_measured_mm": round(
                min(report["minimum_mm"] for report in reports),
                6,
            ),
            "minimum_p05_mm": round(
                min(report["p05_mm"] for report in reports),
                6,
            ),
            "objects_below_threshold": (
                len(below_threshold_objects)
                if below_threshold_objects is not None
                else None
            ),
        },
        "objects_with_no_hit_faces": no_hit_objects,
        "objects_below_threshold": below_threshold_objects,
        "objects": reports,
        "method_limits": [
            "A bidirectional line starts just off each polygon center and "
            "measures between the first two distinct surface crossings.",
            "Concave constituents may hit a nearby unrelated wall rather than "
            "the locally opposite wall.",
            "Thin features between sampled polygon centers may be missed.",
            "A threshold is advisory only until the nozzle, material, and "
            "physical coupon establish a manufacturing minimum.",
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
