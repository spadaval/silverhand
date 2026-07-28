"""Build a geometric-overlap graph for editable working solids.

An edge means two closed solids intersect or one contains vertices of the
other. It is evidence of geometric contact, not proof of a durable load path or
slicer fusion.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


DEFAULT_COLLECTION = "20_SALVAGE_WORKING"
INSIDE_TOLERANCE_MM = 1.0e-4
RAY_DIRECTIONS = (
    Vector((0.936329, 0.281718, 0.210449)).normalized(),
    Vector((-0.317999, 0.887291, 0.334736)).normalized(),
    Vector((0.196116, -0.588348, 0.784465)).normalized(),
)


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
        "--dot",
        type=Path,
        help="Graphviz DOT output; defaults beside the JSON report",
    )
    return parser.parse_args(arguments)


def world_vertices(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def world_bvh(obj: bpy.types.Object, points: list[Vector]) -> BVHTree:
    return BVHTree.FromPolygons(
        points,
        [tuple(polygon.vertices) for polygon in obj.data.polygons],
        all_triangles=False,
    )


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        Vector(
            tuple(min(point[axis] for point in points) for axis in range(3))
        ),
        Vector(
            tuple(max(point[axis] for point in points) for axis in range(3))
        ),
    )


def bounds_overlap(
    first: tuple[Vector, Vector],
    second: tuple[Vector, Vector],
) -> bool:
    return all(
        first[0][axis] <= second[1][axis]
        and second[0][axis] <= first[1][axis]
        for axis in range(3)
    )


def ray_intersection_count(
    point: Vector,
    direction: Vector,
    container: BVHTree,
) -> int:
    origin = point.copy()
    count = 0
    for _ in range(10000):
        location, _, _, _ = container.ray_cast(origin, direction)
        if location is None:
            return count
        count += 1
        origin = location + direction * INSIDE_TOLERANCE_MM
    raise RuntimeError(
        "Cannot analyze connectivity: ray-parity containment exceeded 10,000 "
        f"intersections from point {tuple(round(value, 6) for value in point)}"
    )


def point_inside(point: Vector, container: BVHTree) -> bool:
    votes = [
        ray_intersection_count(point, direction, container) % 2 == 1
        for direction in RAY_DIRECTIONS
    ]
    return sum(votes) >= 2


class DisjointSet:
    def __init__(self, names: list[str]):
        self.parent = {name: name for name in names}

    def find(self, name: str) -> str:
        parent = self.parent[name]
        if parent != name:
            self.parent[name] = self.find(parent)
        return self.parent[name]

    def union(self, first: str, second: str) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


def dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_dot(
    path: Path,
    objects: list[bpy.types.Object],
    edges: list[dict],
    isolated: set[str],
) -> None:
    region_colors = {
        region: color
        for region, color in zip(
            sorted(
                {
                    str(obj.get("construction_region", "UNASSIGNED"))
                    for obj in objects
                }
            ),
            (
                "#60a5fa",
                "#34d399",
                "#fbbf24",
                "#f472b6",
                "#a78bfa",
                "#fb7185",
                "#22d3ee",
            ),
        )
    }
    lines = [
        "graph SilverhandConnectivity {",
        '  graph [overlap=false, splines=true, bgcolor="#071018"];',
        '  node [shape=box, style=filled, fontname="Helvetica", fontsize=9, '
        'fontcolor="#071018"];',
        '  edge [color="#9fb2c9", fontname="Helvetica", fontsize=8, '
        'fontcolor="#9fb2c9"];',
    ]
    for obj in objects:
        region = str(obj.get("construction_region", "UNASSIGNED"))
        color = "#ef4444" if obj.name in isolated else region_colors[region]
        lines.append(
            f'  "{dot_escape(obj.name)}" '
            f'[fillcolor="{color}", tooltip="{dot_escape(region)}"];'
        )
    for edge in edges:
        label = str(edge["surface_triangle_intersection_pairs"])
        if edge["first_inside_second"]:
            label += "/first-in-second"
        if edge["second_inside_first"]:
            label += "/second-in-first"
        lines.append(
            f'  "{dot_escape(edge["first"])}" -- '
            f'"{dot_escape(edge["second"])}" [label="{dot_escape(label)}"];'
        )
    lines.append("}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    collection = bpy.data.collections.get(args.collection)
    if collection is None:
        raise RuntimeError(
            f"Cannot analyze connectivity: collection '{args.collection}' is "
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
            f"Cannot analyze connectivity: collection '{collection.name}' "
            "contains no REG_* mesh objects"
        )

    geometry = {}
    for obj in objects:
        points = world_vertices(obj)
        geometry[obj.name] = {
            "points": points,
            "bounds": bounds(points),
            "bvh": world_bvh(obj, points),
        }

    edges = []
    disjoint = DisjointSet([obj.name for obj in objects])
    candidate_pairs = 0
    for first_index, first in enumerate(objects):
        first_geometry = geometry[first.name]
        for second in objects[first_index + 1 :]:
            second_geometry = geometry[second.name]
            if not bounds_overlap(
                first_geometry["bounds"],
                second_geometry["bounds"],
            ):
                continue
            candidate_pairs += 1
            surface_overlaps = first_geometry["bvh"].overlap(
                second_geometry["bvh"]
            )
            first_inside_second = False
            second_inside_first = False
            if not surface_overlaps:
                first_inside_second = point_inside(
                    first_geometry["points"][0],
                    second_geometry["bvh"],
                )
                second_inside_first = point_inside(
                    second_geometry["points"][0],
                    first_geometry["bvh"],
                )
            if not (
                surface_overlaps
                or first_inside_second
                or second_inside_first
            ):
                continue
            edge = {
                "first": first.name,
                "second": second.name,
                "first_region": first.get(
                    "construction_region",
                    "UNASSIGNED",
                ),
                "second_region": second.get(
                    "construction_region",
                    "UNASSIGNED",
                ),
                "surface_triangle_intersection_pairs": len(
                    surface_overlaps
                ),
                "first_inside_second": first_inside_second,
                "second_inside_first": second_inside_first,
            }
            edges.append(edge)
            disjoint.union(first.name, second.name)

    groups_by_root = {}
    for obj in objects:
        groups_by_root.setdefault(disjoint.find(obj.name), []).append(obj.name)
    groups = sorted(
        (sorted(group) for group in groups_by_root.values()),
        key=lambda group: (-len(group), group[0]),
    )
    isolated = {group[0] for group in groups if len(group) == 1}
    cross_region_edges = [
        edge
        for edge in edges
        if edge["first_region"] != edge["second_region"]
    ]
    report = {
        "tool": "analyze_connectivity.py",
        "status": "geometric_contact_evidence_not_load_path_approval",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "collection": collection.name,
        "summary": {
            "objects": len(objects),
            "possible_pairs": len(objects) * (len(objects) - 1) // 2,
            "aabb_candidate_pairs": candidate_pairs,
            "contact_edges": len(edges),
            "connected_groups": len(groups),
            "isolated_objects": len(isolated),
            "largest_group": max(len(group) for group in groups),
            "cross_region_edges": len(cross_region_edges),
            "group_size_distribution": dict(
                sorted(Counter(len(group) for group in groups).items())
            ),
        },
        "groups": [
            {
                "group": index + 1,
                "size": len(group),
                "objects": group,
            }
            for index, group in enumerate(groups)
        ],
        "isolated_objects": sorted(isolated),
        "edges": edges,
        "cross_region_edges": cross_region_edges,
        "method_limits": [
            "An edge records surface intersection or vertex containment.",
            "Geometric contact does not prove adequate overlap volume, layer "
            "fusion, junction strength, or a durable assembled load path.",
            "Containment uses majority ray parity from one representative "
            "vertex only when the two closed surfaces do not cross.",
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    dot_path = (
        args.dot.resolve()
        if args.dot is not None
        else output_path.with_suffix(".dot")
    )
    write_dot(dot_path, objects, edges, isolated)
    print(json.dumps(report["summary"], indent=2))
    print(output_path)
    print(dot_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
