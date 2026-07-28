"""Inventory editable working solids without modifying the Blender scene."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector


DEFAULT_COLLECTION = "20_SALVAGE_WORKING"


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
    return parser.parse_args(arguments)


def connected_components(bm: bmesh.types.BMesh) -> int:
    unseen = set(bm.verts)
    count = 0
    while unseen:
        count += 1
        stack = [unseen.pop()]
        while stack:
            vertex = stack.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
    return count


def fingerprint(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    digest.update(obj.name.encode("utf-8"))
    for row in obj.matrix_world:
        digest.update(struct.pack("<4d", *row))
    for vertex in obj.data.vertices:
        digest.update(struct.pack("<3d", *vertex.co))
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(
        tuple(min(point[axis] for point in points) for axis in range(3))
    )
    maximum = Vector(
        tuple(max(point[axis] for point in points) for axis in range(3))
    )
    return minimum, maximum


def inspect(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        minimum, maximum = world_bounds(obj)
        center = (minimum + maximum) * 0.5
        return {
            "object": obj.name,
            "mesh": obj.data.name,
            "mesh_users": obj.data.users,
            "construction_region": obj.get(
                "construction_region",
                "UNASSIGNED",
            ),
            "disposition": obj.get("disposition", "UNCLASSIFIED"),
            "pre_cleanup_name": obj.get("pre_cleanup_name"),
            "geometry": {
                "vertices": len(bm.verts),
                "edges": len(bm.edges),
                "faces": len(bm.faces),
                "connected_components": connected_components(bm),
                "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
                "nonmanifold_edges": sum(
                    not edge.is_manifold for edge in bm.edges
                ),
                "signed_volume_mm3": round(
                    bm.calc_volume(signed=True),
                    6,
                ),
                "dimensions_mm": [
                    round(float(value), 3) for value in maximum - minimum
                ],
                "bounds_min_mm": [
                    round(float(value), 3) for value in minimum
                ],
                "bounds_max_mm": [
                    round(float(value), 3) for value in maximum
                ],
                "bounds_center_mm": [
                    round(float(value), 3) for value in center
                ],
                "fingerprint": fingerprint(obj),
            },
            "construction_metadata": {
                key: obj.get(key)
                for key in (
                    "station_mm",
                    "local_thickness_mm",
                    "source_area_mm2",
                    "collision_area_removed_mm2",
                    "closure_method",
                    "under_removed_armor_filler",
                    "region_assignment",
                    "manufacturing_status",
                    "print_ready",
                    "printable",
                )
                if key in obj
            },
            "modifiers": [
                {"name": modifier.name, "type": modifier.type}
                for modifier in obj.modifiers
            ],
            "materials": [
                material.name if material is not None else None
                for material in obj.data.materials
            ],
        }
    finally:
        bm.free()


def main() -> int:
    args = parse_args()
    collection = bpy.data.collections.get(args.collection)
    if collection is None:
        raise RuntimeError(
            f"Cannot inventory working geometry: collection "
            f"'{args.collection}' is missing"
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
            f"Cannot inventory working geometry: collection "
            f"'{collection.name}' contains no REG_* mesh objects"
        )
    reports = [inspect(obj) for obj in objects]
    invalid = [
        report["object"]
        for report in reports
        if report["geometry"]["boundary_edges"]
        or report["geometry"]["nonmanifold_edges"]
        or report["geometry"]["signed_volume_mm3"] <= 0.0
        or report["mesh_users"] != 1
    ]
    report = {
        "tool": "inventory_working_geometry.py",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "collection": collection.name,
        "summary": {
            "objects": len(reports),
            "regions": dict(
                sorted(
                    Counter(
                        item["construction_region"] for item in reports
                    ).items()
                )
            ),
            "dispositions": dict(
                sorted(
                    Counter(item["disposition"] for item in reports).items()
                )
            ),
            "invalid_objects": invalid,
            "vertices": sum(
                item["geometry"]["vertices"] for item in reports
            ),
            "faces": sum(item["geometry"]["faces"] for item in reports),
            "signed_volume_mm3": round(
                sum(
                    item["geometry"]["signed_volume_mm3"]
                    for item in reports
                ),
                3,
            ),
        },
        "objects": reports,
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
