"""Analyze current geometry against a non-printable clearance cutter.

This is a geometric collision audit, not wearer-fit approval. It reports exact
surface-triangle intersections plus an approximate signed vertex clearance
derived from the cutter's nearest surface normal.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils.bvhtree import BVHTree


DEFAULT_CUTTER = "CUT_CLEARANCE_BASELINE"
DEFAULT_FIT_REFERENCE = "REF_FIT_VOLUME_BASELINE"
DEFAULT_COLLECTION = "20_SALVAGE_WORKING"
TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutter", default=DEFAULT_CUTTER)
    parser.add_argument("--fit-reference", default=DEFAULT_FIT_REFERENCE)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(arguments)


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot analyze clearance: {role} object '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot analyze clearance: {role} object '{name}' has type "
            f"'{obj.type}', expected 'MESH'"
        )
    return obj


def inspect_closed_mesh(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        return {
            "vertices": len(bm.verts),
            "faces": len(bm.faces),
            "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
            "nonmanifold_edges": sum(
                not edge.is_manifold for edge in bm.edges
            ),
            "signed_volume_mm3": round(bm.calc_volume(signed=True), 6),
        }
    finally:
        bm.free()


def world_vertices(obj: bpy.types.Object) -> list:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def world_bvh(obj: bpy.types.Object) -> BVHTree:
    return BVHTree.FromPolygons(
        world_vertices(obj),
        [tuple(polygon.vertices) for polygon in obj.data.polygons],
        all_triangles=False,
    )


def signed_vertex_clearance(
    obj: bpy.types.Object,
    cutter_bvh: BVHTree,
) -> dict:
    signed_distances = []
    for point in world_vertices(obj):
        nearest = cutter_bvh.find_nearest(point)
        if nearest[0] is None:
            raise RuntimeError(
                "Cannot analyze clearance: nearest-surface lookup failed for "
                f"object '{obj.name}'"
            )
        location, normal, _, distance = nearest
        side = (point - location).dot(normal)
        signed_distances.append(
            -float(distance) if side < 0.0 else float(distance)
        )

    inside = [
        distance
        for distance in signed_distances
        if distance < -TOLERANCE_MM
    ]
    return {
        "minimum_signed_vertex_clearance_mm": round(
            min(signed_distances),
            6,
        ),
        "maximum_signed_vertex_clearance_mm": round(
            max(signed_distances),
            6,
        ),
        "vertices_inside_cutter": len(inside),
        "maximum_vertex_penetration_mm": round(
            -min(inside) if inside else 0.0,
            6,
        ),
    }


def main() -> int:
    args = parse_args()
    cutter = require_mesh(args.cutter, "clearance cutter")
    fit_reference = require_mesh(args.fit_reference, "fit reference")
    collection = bpy.data.collections.get(args.collection)
    if collection is None:
        raise RuntimeError(
            f"Cannot analyze clearance: collection '{args.collection}' is "
            "missing"
        )
    if cutter.get("printable") is not False:
        raise RuntimeError(
            f"Cannot analyze clearance: cutter '{cutter.name}' must declare "
            "printable=false"
        )

    cutter_geometry = inspect_closed_mesh(cutter)
    cutter_failures = []
    if cutter_geometry["boundary_edges"]:
        cutter_failures.append(
            f"{cutter_geometry['boundary_edges']} boundary edges"
        )
    if cutter_geometry["nonmanifold_edges"]:
        cutter_failures.append(
            f"{cutter_geometry['nonmanifold_edges']} non-manifold edges"
        )
    if cutter_geometry["signed_volume_mm3"] <= 0.0:
        cutter_failures.append(
            "non-positive signed volume "
            f"{cutter_geometry['signed_volume_mm3']} mm³"
        )
    if cutter_failures:
        raise RuntimeError(
            f"Cannot analyze clearance: cutter '{cutter.name}' is invalid ("
            + "; ".join(cutter_failures)
            + ")"
        )

    cutter_bvh = world_bvh(cutter)
    fit_bvh = world_bvh(fit_reference)
    fit_surface_overlaps = cutter_bvh.overlap(fit_bvh)
    fit_clearance = signed_vertex_clearance(fit_reference, cutter_bvh)

    objects = sorted(
        (
            obj
            for obj in collection.all_objects
            if obj.type == "MESH" and obj.name.startswith("REG_")
        ),
        key=lambda obj: obj.name,
    )
    reports = []
    for obj in objects:
        overlaps = cutter_bvh.overlap(world_bvh(obj))
        clearance = signed_vertex_clearance(obj, cutter_bvh)
        reports.append(
            {
                "object": obj.name,
                "construction_region": obj.get(
                    "construction_region",
                    "UNASSIGNED",
                ),
                "surface_triangle_intersection_pairs": len(overlaps),
                **clearance,
            }
        )

    collision_reports = [
        report
        for report in reports
        if report["surface_triangle_intersection_pairs"]
        or report["vertices_inside_cutter"]
    ]
    warnings = []
    if fit_surface_overlaps:
        warnings.append(
            f"Fit reference '{fit_reference.name}' and cutter "
            f"'{cutter.name}' have {len(fit_surface_overlaps)} surface-triangle "
            "intersection pairs; inspect coincident or insufficiently expanded "
            "end boundaries."
        )

    report = {
        "tool": "analyze_clearance.py",
        "status": "geometry_only_not_fit_approval",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "cutter": {
            "object": cutter.name,
            "geometry": cutter_geometry,
            "radial_margin_mm": cutter.get("radial_margin_mm"),
            "printable": cutter.get("printable"),
        },
        "fit_reference": {
            "object": fit_reference.name,
            "role": fit_reference.get("role"),
            "surface_triangle_intersection_pairs_with_cutter": len(
                fit_surface_overlaps
            ),
            **fit_clearance,
        },
        "working_geometry": {
            "collection": collection.name,
            "objects_tested": len(reports),
            "objects_with_clearance_violations": len(collision_reports),
            "surface_triangle_intersection_pairs": sum(
                item["surface_triangle_intersection_pairs"]
                for item in reports
            ),
            "vertices_inside_cutter": sum(
                item["vertices_inside_cutter"] for item in reports
            ),
            "violations": collision_reports,
            "objects": reports,
        },
        "warnings": warnings,
        "method_limits": [
            "Surface-triangle overlap is exact for the current triangulation.",
            "Signed vertex clearance uses the nearest cutter surface normal and "
            "is an approximation on strongly concave geometry.",
            "A geometric pass does not establish wearer dimensions, comfort, "
            "TPU stretch, or motion clearance.",
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
