"""Extract every ordered ring from the provisional fit and clearance meshes.

The report describes existing geometry only. It deliberately does not assign
wearer landmarks or claim that the inherited profile is anatomically correct.
"""

from __future__ import annotations

import argparse
import csv
import json
from math import atan2, cos, sin
from pathlib import Path
import statistics
import sys

import bpy
from mathutils import Vector


DEFAULT_FIT = "REF_FIT_VOLUME_BASELINE"
DEFAULT_CUTTER = "CUT_CLEARANCE_BASELINE"


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit", default=DEFAULT_FIT)
    parser.add_argument("--cutter", default=DEFAULT_CUTTER)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--csv",
        type=Path,
        help="station CSV output; defaults beside the JSON report",
    )
    return parser.parse_args(arguments)


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot analyze fit profile: {role} object '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot analyze fit profile: {role} object '{name}' has type "
            f"'{obj.type}', expected 'MESH'"
        )
    return obj


def ordered_rings(obj: bpy.types.Object) -> list[list[Vector]]:
    polygon_sizes = [len(polygon.vertices) for polygon in obj.data.polygons]
    if not polygon_sizes:
        raise RuntimeError(
            f"Cannot analyze fit profile: object '{obj.name}' has no faces"
        )
    ring_size = max(polygon_sizes)
    cap_count = sum(size == ring_size for size in polygon_sizes)
    if ring_size < 8 or cap_count != 2:
        raise RuntimeError(
            f"Cannot analyze fit profile: object '{obj.name}' does not match "
            "the expected ordered-ring topology "
            f"(largest face={ring_size}, matching caps={cap_count})"
        )
    vertex_count = len(obj.data.vertices)
    if vertex_count % ring_size:
        raise RuntimeError(
            f"Cannot analyze fit profile: object '{obj.name}' has "
            f"{vertex_count} vertices, not divisible by ring size {ring_size}"
        )
    station_count = vertex_count // ring_size
    expected_faces = (station_count - 1) * ring_size + 2
    if len(obj.data.polygons) != expected_faces:
        raise RuntimeError(
            f"Cannot analyze fit profile: object '{obj.name}' has "
            f"{len(obj.data.polygons)} faces; ordered {station_count}x"
            f"{ring_size} ring topology expects {expected_faces}"
        )
    return [
        [
            obj.matrix_world
            @ obj.data.vertices[station * ring_size + sample].co
            for sample in range(ring_size)
        ]
        for station in range(station_count)
    ]


def ring_center(ring: list[Vector]) -> Vector:
    return sum(ring, Vector()) / len(ring)


def tangent_at(centers: list[Vector], index: int) -> Vector:
    if index == 0:
        tangent = centers[1] - centers[0]
    elif index == len(centers) - 1:
        tangent = centers[-1] - centers[-2]
    else:
        tangent = centers[index + 1] - centers[index - 1]
    if tangent.length_squared == 0.0:
        raise RuntimeError(
            f"Cannot analyze fit profile: station {index} has zero tangent"
        )
    return tangent.normalized()


def principal_diameters(
    ring: list[Vector],
    center: Vector,
    tangent: Vector,
) -> tuple[float, float]:
    normal = ring[0] - center
    normal -= tangent * normal.dot(tangent)
    if normal.length_squared == 0.0:
        normal = tangent.cross(Vector((0.0, 0.0, 1.0)))
    if normal.length_squared == 0.0:
        normal = tangent.cross(Vector((0.0, 1.0, 0.0)))
    normal.normalize()
    binormal = tangent.cross(normal).normalized()
    points = [
        ((point - center).dot(normal), (point - center).dot(binormal))
        for point in ring
    ]
    xx = sum(x * x for x, _ in points) / len(points)
    yy = sum(y * y for _, y in points) / len(points)
    xy = sum(x * y for x, y in points) / len(points)
    angle = 0.5 * atan2(2.0 * xy, xx - yy)
    axis_x = (cos(angle), sin(angle))
    axis_y = (-axis_x[1], axis_x[0])
    projected_x = [x * axis_x[0] + y * axis_x[1] for x, y in points]
    projected_y = [x * axis_y[0] + y * axis_y[1] for x, y in points]
    first = max(projected_x) - min(projected_x)
    second = max(projected_y) - min(projected_y)
    return (max(first, second), min(first, second))


def profile(rings: list[list[Vector]]) -> list[dict]:
    centers = [ring_center(ring) for ring in rings]
    arc_lengths = [0.0]
    for previous, current in zip(centers, centers[1:]):
        arc_lengths.append(arc_lengths[-1] + (current - previous).length)
    reports = []
    for index, ring in enumerate(rings):
        center = centers[index]
        tangent = tangent_at(centers, index)
        circumference = sum(
            (ring[(sample + 1) % len(ring)] - ring[sample]).length
            for sample in range(len(ring))
        )
        cross_sum = Vector()
        for sample, point in enumerate(ring):
            cross_sum += point.cross(ring[(sample + 1) % len(ring)])
        area = abs(cross_sum.dot(tangent)) * 0.5
        major, minor = principal_diameters(ring, center, tangent)
        reports.append(
            {
                "station_index": index,
                "normalized_position": round(
                    index / (len(rings) - 1),
                    6,
                ),
                "arc_length_mm": round(arc_lengths[index], 6),
                "center_mm": [
                    round(float(value), 6) for value in center
                ],
                "tangent": [
                    round(float(value), 9) for value in tangent
                ],
                "circumference_mm": round(circumference, 6),
                "area_mm2": round(area, 6),
                "major_diameter_mm": round(major, 6),
                "minor_diameter_mm": round(minor, 6),
                "aspect_ratio": round(major / minor, 6),
            }
        )
    return reports


def summarize(stations: list[dict]) -> dict:
    widest = max(stations, key=lambda item: item["circumference_mm"])
    narrowest = min(stations, key=lambda item: item["circumference_mm"])
    return {
        "station_count": len(stations),
        "arc_length_mm": stations[-1]["arc_length_mm"],
        "first_circumference_mm": stations[0]["circumference_mm"],
        "last_circumference_mm": stations[-1]["circumference_mm"],
        "widest_station": {
            "station_index": widest["station_index"],
            "arc_length_mm": widest["arc_length_mm"],
            "circumference_mm": widest["circumference_mm"],
        },
        "narrowest_station": {
            "station_index": narrowest["station_index"],
            "arc_length_mm": narrowest["arc_length_mm"],
            "circumference_mm": narrowest["circumference_mm"],
        },
    }


def write_csv(path: Path, fit: list[dict], cutter: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "station_index",
        "normalized_position",
        "arc_length_mm",
        "fit_circumference_mm",
        "cutter_circumference_mm",
        "fit_area_mm2",
        "cutter_area_mm2",
        "fit_major_diameter_mm",
        "fit_minor_diameter_mm",
        "fit_aspect_ratio",
        "minimum_vertex_margin_mm",
        "median_vertex_margin_mm",
        "maximum_vertex_margin_mm",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for fit_station, cutter_station in zip(fit, cutter):
            writer.writerow(
                {
                    "station_index": fit_station["station_index"],
                    "normalized_position": fit_station[
                        "normalized_position"
                    ],
                    "arc_length_mm": fit_station["arc_length_mm"],
                    "fit_circumference_mm": fit_station[
                        "circumference_mm"
                    ],
                    "cutter_circumference_mm": cutter_station[
                        "circumference_mm"
                    ],
                    "fit_area_mm2": fit_station["area_mm2"],
                    "cutter_area_mm2": cutter_station["area_mm2"],
                    "fit_major_diameter_mm": fit_station[
                        "major_diameter_mm"
                    ],
                    "fit_minor_diameter_mm": fit_station[
                        "minor_diameter_mm"
                    ],
                    "fit_aspect_ratio": fit_station["aspect_ratio"],
                    "minimum_vertex_margin_mm": fit_station[
                        "minimum_vertex_margin_mm"
                    ],
                    "median_vertex_margin_mm": fit_station[
                        "median_vertex_margin_mm"
                    ],
                    "maximum_vertex_margin_mm": fit_station[
                        "maximum_vertex_margin_mm"
                    ],
                }
            )


def main() -> int:
    args = parse_args()
    fit_object = require_mesh(args.fit, "fit reference")
    cutter_object = require_mesh(args.cutter, "clearance cutter")
    fit_rings = ordered_rings(fit_object)
    cutter_rings = ordered_rings(cutter_object)
    if len(fit_rings) != len(cutter_rings) or any(
        len(fit_ring) != len(cutter_ring)
        for fit_ring, cutter_ring in zip(fit_rings, cutter_rings)
    ):
        raise RuntimeError(
            "Cannot analyze fit profile: fit and cutter ring topology differs "
            f"({len(fit_rings)} versus {len(cutter_rings)} stations)"
        )
    fit_profile = profile(fit_rings)
    cutter_profile = profile(cutter_rings)
    all_margins = []
    for station, (fit_ring, cutter_ring) in enumerate(
        zip(fit_rings, cutter_rings)
    ):
        margins = sorted(
            (cutter_point - fit_point).length
            for fit_point, cutter_point in zip(fit_ring, cutter_ring)
        )
        all_margins.extend(margins)
        fit_profile[station].update(
            {
                "minimum_vertex_margin_mm": round(margins[0], 6),
                "median_vertex_margin_mm": round(
                    statistics.median(margins),
                    6,
                ),
                "maximum_vertex_margin_mm": round(margins[-1], 6),
            }
        )

    report = {
        "tool": "analyze_fit_profile.py",
        "status": "provisional_geometry_profile_not_wearer_fit_approval",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "landmarks_assigned": False,
        "fit_reference": {
            "object": fit_object.name,
            "role": fit_object.get("role"),
            "summary": summarize(fit_profile),
        },
        "clearance_cutter": {
            "object": cutter_object.name,
            "role": cutter_object.get("role"),
            "declared_radial_margin_mm": cutter_object.get(
                "radial_margin_mm"
            ),
            "summary": summarize(cutter_profile),
        },
        "corresponding_vertex_margin_mm": {
            "minimum": round(min(all_margins), 6),
            "median": round(statistics.median(all_margins), 6),
            "maximum": round(max(all_margins), 6),
        },
        "stations": [
            {
                "fit": fit_station,
                "cutter": cutter_station,
            }
            for fit_station, cutter_station in zip(
                fit_profile,
                cutter_profile,
            )
        ],
        "method_limits": [
            "Station order is inherited from the validated 77-ring mesh "
            "topology.",
            "No station is called wrist, elbow, or bicep until wearer landmarks "
            "are supplied.",
            "The profile describes the provisional inherited fit volume and "
            "does not override wearer circumference measurements.",
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    csv_path = (
        args.csv.resolve()
        if args.csv is not None
        else output_path.with_suffix(".csv")
    )
    write_csv(csv_path, fit_profile, cutter_profile)
    print(
        json.dumps(
            {
                "fit": report["fit_reference"]["summary"],
                "cutter": report["clearance_cutter"]["summary"],
                "margin_mm": report[
                    "corresponding_vertex_margin_mm"
                ],
                "landmarks_assigned": False,
            },
            indent=2,
        )
    )
    print(output_path)
    print(csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
