"""Intersect explicit evaluated meshes with a review plane.

The tool emits segment topology, measurements, and an SVG. It never bisects,
caps, duplicates, or saves Blender geometry.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import html
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_fit_profile import (  # noqa: E402
    ordered_rings,
    ring_center,
    tangent_at,
)


DEFAULT_FIT = "REF_FIT_VOLUME_BASELINE"
PLANE_TOLERANCE_MM = 1.0e-5
JOIN_TOLERANCE_MM = 1.0e-3
STATION_PLANE_NUDGE_MM = 1.0e-2


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objects", nargs="+", required=True)
    parser.add_argument("--fit-reference", default=DEFAULT_FIT)
    parser.add_argument("--station-index", type=int)
    parser.add_argument("--plane-origin", nargs=3, type=float)
    parser.add_argument("--plane-normal", nargs=3, type=float)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--svg",
        type=Path,
        help="SVG output; defaults beside the JSON report",
    )
    args = parser.parse_args(arguments)
    station_mode = args.station_index is not None
    explicit_mode = (
        args.plane_origin is not None and args.plane_normal is not None
    )
    partial_explicit = (
        args.plane_origin is None
    ) != (args.plane_normal is None)
    if partial_explicit or station_mode == explicit_mode:
        parser.error(
            "provide exactly one plane mode: --station-index, or both "
            "--plane-origin and --plane-normal"
        )
    return args


def require_mesh(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot analyze cross-section: object '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot analyze cross-section: object '{name}' has type "
            f"'{obj.type}', expected 'MESH'"
        )
    return obj


def evaluated_triangles(obj: bpy.types.Object) -> list[tuple[Vector, Vector, Vector]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.transform(evaluated.matrix_world)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        return [
            tuple(vertex.co.copy() for vertex in face.verts)
            for face in bm.faces
        ]
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def unique_points(points: list[Vector]) -> list[Vector]:
    result = []
    for point in points:
        if all((point - existing).length > JOIN_TOLERANCE_MM for existing in result):
            result.append(point)
    return result


def triangle_section(
    triangle: tuple[Vector, Vector, Vector],
    origin: Vector,
    normal: Vector,
) -> tuple[list[Vector], bool]:
    distances = [(point - origin).dot(normal) for point in triangle]
    if all(abs(distance) <= PLANE_TOLERANCE_MM for distance in distances):
        return [], True
    intersections = []
    for index in range(3):
        first = triangle[index]
        second = triangle[(index + 1) % 3]
        first_distance = distances[index]
        second_distance = distances[(index + 1) % 3]
        if abs(first_distance) <= PLANE_TOLERANCE_MM:
            intersections.append(first)
        if first_distance * second_distance < 0.0:
            factor = first_distance / (first_distance - second_distance)
            intersections.append(first.lerp(second, factor))
    return unique_points(intersections), False


def point_key(point: Vector) -> tuple[int, int, int]:
    return tuple(round(float(value) / JOIN_TOLERANCE_MM) for value in point)


def graph_metrics(
    segments: list[tuple[Vector, Vector]],
) -> dict:
    adjacency = {}
    for first, second in segments:
        first_key = point_key(first)
        second_key = point_key(second)
        adjacency.setdefault(first_key, set()).add(second_key)
        adjacency.setdefault(second_key, set()).add(first_key)
    degrees = Counter(len(neighbors) for neighbors in adjacency.values())
    unseen = set(adjacency)
    components = 0
    while unseen:
        components += 1
        queue = deque([unseen.pop()])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return {
        "section_components": components,
        "endpoint_degree_distribution": dict(sorted(degrees.items())),
        "open_endpoints": degrees.get(1, 0),
        "branch_points": sum(
            count for degree, count in degrees.items() if degree > 2
        ),
        "closed_section_graph": bool(adjacency)
        and degrees.get(1, 0) == 0
        and not any(degree > 2 for degree in degrees),
    }


def plane_basis(normal: Vector) -> tuple[Vector, Vector]:
    reference = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(reference)) > 0.9:
        reference = Vector((0.0, 1.0, 0.0))
    first = normal.cross(reference).normalized()
    second = normal.cross(first).normalized()
    return first, second


def analyze_object(
    obj: bpy.types.Object,
    origin: Vector,
    normal: Vector,
    axis_x: Vector,
    axis_y: Vector,
) -> dict:
    segments = []
    coplanar_triangles = 0
    malformed_crossings = 0
    for triangle in evaluated_triangles(obj):
        points, coplanar = triangle_section(triangle, origin, normal)
        if coplanar:
            coplanar_triangles += 1
        elif len(points) == 2:
            segments.append((points[0], points[1]))
        elif points:
            malformed_crossings += 1
    projected_segments = [
        [
            [
                round((point - origin).dot(axis_x), 6),
                round((point - origin).dot(axis_y), 6),
            ]
            for point in segment
        ]
        for segment in segments
    ]
    perimeter = sum((second - first).length for first, second in segments)
    return {
        "object": obj.name,
        "segments": len(segments),
        "section_line_length_mm": round(perimeter, 6),
        "coplanar_triangles": coplanar_triangles,
        "malformed_crossings": malformed_crossings,
        **graph_metrics(segments),
        "projected_segments_mm": projected_segments,
    }


def write_svg(path: Path, reports: list[dict]) -> None:
    colors = (
        "#9ca3af",
        "#22d3ee",
        "#f59e0b",
        "#f472b6",
        "#a78bfa",
        "#34d399",
    )
    points = [
        point
        for report in reports
        for segment in report["projected_segments_mm"]
        for point in segment
    ]
    if not points:
        raise RuntimeError(
            "Cannot write cross-section SVG: the plane produced no segments"
        )
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    canvas = 1000
    padding = 80
    scale = min(
        (canvas - padding * 2) / width,
        (canvas - padding * 2) / height,
    )

    def project(point: list[float]) -> tuple[float, float]:
        return (
            padding + (point[0] - min_x) * scale,
            canvas - padding - (point[1] - min_y) * scale,
        )

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {canvas} {canvas}">',
        '<rect width="100%" height="100%" fill="#071018"/>',
        (
            f'<text x="{padding}" y="38" fill="#edf3fa" '
            'font-family="system-ui,sans-serif" font-size="24">'
            "Silverhand cross-section evidence</text>"
        ),
    ]
    for index, report in enumerate(reports):
        color = colors[index % len(colors)]
        for segment in report["projected_segments_mm"]:
            first = project(segment[0])
            second = project(segment[1])
            lines.append(
                f'<line x1="{first[0]:.3f}" y1="{first[1]:.3f}" '
                f'x2="{second[0]:.3f}" y2="{second[1]:.3f}" '
                f'stroke="{color}" stroke-width="2"/>'
            )
        lines.append(
            f'<text x="{padding}" y="{canvas - 48 + index * 18}" '
            f'fill="{color}" font-family="system-ui,sans-serif" '
            f'font-size="14">{html.escape(report["object"])}</text>'
        )
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.station_index is not None:
        fit = require_mesh(args.fit_reference)
        rings = ordered_rings(fit)
        if not 0 <= args.station_index < len(rings):
            raise RuntimeError(
                f"Cannot analyze cross-section: station index "
                f"{args.station_index} is outside 0..{len(rings) - 1}"
            )
        centers = [ring_center(ring) for ring in rings]
        origin = centers[args.station_index]
        normal = tangent_at(centers, args.station_index)
        nudge_direction = -1.0 if args.station_index == len(rings) - 1 else 1.0
        origin += normal * STATION_PLANE_NUDGE_MM * nudge_direction
        plane_source = {
            "mode": "fit_station",
            "fit_reference": fit.name,
            "station_index": args.station_index,
            "station_count": len(rings),
            "station_plane_nudge_mm": (
                STATION_PLANE_NUDGE_MM * nudge_direction
            ),
        }
    else:
        origin = Vector(args.plane_origin)
        normal = Vector(args.plane_normal)
        if normal.length_squared == 0.0:
            raise RuntimeError(
                "Cannot analyze cross-section: plane normal is zero"
            )
        normal.normalize()
        plane_source = {"mode": "explicit"}

    axis_x, axis_y = plane_basis(normal)
    objects = [require_mesh(name) for name in args.objects]
    reports = [
        analyze_object(obj, origin, normal, axis_x, axis_y)
        for obj in objects
    ]
    report = {
        "tool": "analyze_cross_section.py",
        "status": "section_evidence_not_segmentation",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "plane": {
            **plane_source,
            "origin_mm": [round(float(value), 6) for value in origin],
            "normal": [round(float(value), 9) for value in normal],
            "axis_x": [round(float(value), 9) for value in axis_x],
            "axis_y": [round(float(value), 9) for value in axis_y],
        },
        "objects": reports,
        "summary": {
            "objects": len(reports),
            "objects_intersected": sum(
                bool(item["segments"]) for item in reports
            ),
            "segments": sum(item["segments"] for item in reports),
            "all_sections_closed": all(
                not item["segments"] or item["closed_section_graph"]
                for item in reports
            ),
        },
        "method_limits": [
            "The tool reports a plane intersection only; it does not split or "
            "cap geometry.",
            "Coplanar triangles are reported but excluded from section lines.",
            "A closed section graph does not select a structurally acceptable "
            "production cut location.",
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    svg_path = (
        args.svg.resolve()
        if args.svg is not None
        else output_path.with_suffix(".svg")
    )
    write_svg(svg_path, reports)
    print(json.dumps(report["summary"], indent=2))
    print(output_path)
    print(svg_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
