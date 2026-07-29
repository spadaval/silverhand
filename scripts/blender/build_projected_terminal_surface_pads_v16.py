"""Build terminal-local projected pads on the proven Repair 014 route."""

from __future__ import annotations

import bmesh
import json
from math import atan2, cos, radians, sin
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import build_surface_following_fan_saddles_v15 as v15  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "PROJECTED_TERMINAL_SURFACE_PADS_V16"
AUTHORITY_SHA256 = (
    "0b8d608eaf66a172837f69759d9012570d9a9881a81a909ad4bc6645b5bf764b"
)
REPORT_SHA256 = (
    "0ebd0a8b5a3b6f5da50905d725c16869326968ed8c6d15803501d8e7d58f8899"
)
REVIEW_SHA256 = (
    "a3da691a350d39e31607c7e738f7e6584cfaffe3950be7a2ebeeb81fb8cf3504"
)
V15_OBJECTS = (
    "EVAL_REPAIR_014_FAN_SADDLES_V15_AFTER",
    "EVAL_REPAIR_014_FAN_SADDLES_V15_NETWORK",
)
BASELINE_OBJECTS = v15.BASELINE_REPAIR_014_OBJECTS
THICKNESS_MM = 2.4
MIDSPAN_MINIMUM_MM = 4.5
MIDSPAN_SHOULDER_MM = 6.0
EXPECTED_C9_FINGERPRINT = (
    "f965804b766050eeb0c1dbad26fe24459983868df984ccfee9ae4129dc60db87"
)
V15_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_surface_following_fan_saddles_v15/build_report.json"
)
V15_REVIEW_PATH = V15_REPORT_PATH.with_name("review.json")

CANDIDATES = [
    (long_mm, short_mm, embed_mm, upper_rotation, lower_rotation)
    for long_mm, short_mm in ((10.0, 8.0), (10.0, 7.0), (9.0, 8.0), (9.0, 7.0))
    for embed_mm in (1.5, 1.8)
    for upper_rotation, lower_rotation in (
        (0, 0),
        (0, 90),
        (0, -90),
        (15, 75),
        (-15, -75),
    )
]
CANDIDATE_RECORDS = []


def oriented_faces(points, faces):
    mesh = bmesh.new()
    vertices = [mesh.verts.new(point) for point in points]
    mesh.verts.ensure_lookup_table()
    for face in faces:
        mesh.faces.new(tuple(vertices[index] for index in face))
    bmesh.ops.triangulate(
        mesh,
        faces=[face for face in mesh.faces if len(face.verts) > 4],
    )
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    mesh.verts.index_update()
    result = [tuple(vertex.index for vertex in face.verts) for face in mesh.faces]
    mesh.free()
    return v4.v2.base.positive_faces(points, result)


def nonadjacent_self_overlaps(points, faces):
    tree = BVHTree.FromPolygons(points, faces, all_triangles=False)
    face_sets = [set(face) for face in faces]
    return [
        (first, second)
        for first, second in tree.overlap(tree)
        if first < second and face_sets[first].isdisjoint(face_sets[second])
    ]


def terminal_frame(
    points,
    faces,
    endpoint,
    route_direction,
    rotation_degrees,
    target_length,
):
    tree = BVHTree.FromPolygons(points, faces, all_triangles=False)
    nearest, normal, _, distance = tree.find_nearest(endpoint)
    if nearest is None:
        raise RuntimeError(f"{OPERATION}: terminal surface projection failed")
    normal.normalize()
    _, _, _, radial = v4.radial_coordinates(nearest, target_length)
    if normal.dot(radial) < 0.0:
        normal.negate()
    nearby = [
        point - nearest
        for point in points
        if (point - nearest).length <= 30.0
    ]
    first = route_direction - normal * route_direction.dot(normal)
    if first.length <= 1.0e-6:
        first = normal.cross(Vector((1.0, 0.0, 0.0)))
    if first.length <= 1.0e-6:
        first = normal.cross(Vector((0.0, 1.0, 0.0)))
    first.normalize()
    second = normal.cross(first).normalized()
    xx = sum(vector.dot(first) ** 2 for vector in nearby)
    xy = sum(vector.dot(first) * vector.dot(second) for vector in nearby)
    yy = sum(vector.dot(second) ** 2 for vector in nearby)
    angle = 0.5 * atan2(2.0 * xy, xx - yy)
    tangent = (first * cos(angle) + second * sin(angle)).normalized()
    tangent = (Quaternion(normal, radians(rotation_degrees)) @ tangent).normalized()
    if tangent.dot(Vector((1.0, 0.0, 0.0))) < 0.0:
        tangent.negate()
    transverse = normal.cross(tangent).normalized()
    return {
        "tree": tree,
        "origin": nearest,
        "normal": normal,
        "tangent": tangent,
        "transverse": transverse,
        "endpoint_projection_distance_mm": distance,
        "nearby_vertex_count": len(nearby),
        "rotation_degrees": rotation_degrees,
    }


def mitered_polygon(long_mm, short_mm):
    x = long_mm * 0.5
    y = short_mm * 0.5
    return [
        (-x, -y),
        (x, -y),
        (x, y),
        (-x, y),
    ]


def projected_pad(
    terminal_geometry,
    endpoint,
    other_endpoint,
    route_direction,
    long_mm,
    short_mm,
    embed_mm,
    rotation_degrees,
    target_length,
):
    points, faces = terminal_geometry
    frame = terminal_frame(
        points,
        faces,
        endpoint,
        route_direction,
        rotation_degrees,
        target_length,
    )
    support = []
    for sign in (-1.0, 1.0):
        probe = (
            frame["origin"]
            + frame["tangent"] * sign * long_mm * 0.45
        )
        location, _, _, _ = frame["tree"].ray_cast(
            probe + frame["normal"] * 20.0,
            -frame["normal"],
            40.0,
        )
        support.append(
            (
                (probe - location).length if location is not None else float("inf"),
                sign,
            )
        )
    interior_sign = min(support)[1]
    center_shift_mm = long_mm * 0.4
    footprint_center = (
        frame["origin"]
        + frame["tangent"] * interior_sign * center_shift_mm
    )
    projected = []
    normals = []
    footprint = mitered_polygon(long_mm, short_mm)
    for x, y in footprint:
        target = (
            footprint_center
            + frame["tangent"] * x
            + frame["transverse"] * y
        )
        location, normal, _, _ = frame["tree"].ray_cast(
            target + frame["normal"] * 20.0,
            -frame["normal"],
            40.0,
        )
        if location is None:
            location, normal, _, _ = frame["tree"].find_nearest(target)
        if location is None:
            raise RuntimeError(f"{OPERATION}: pad footprint projection failed")
        normal.normalize()
        if normal.dot(frame["normal"]) < 0.0:
            normal.negate()
        projected.append(location)
        normals.append(normal)
    surface_offset_mm = 0.5
    bottom = [
        point + normal * surface_offset_mm
        for point, normal in zip(projected, normals)
    ]
    outward_mm = surface_offset_mm + THICKNESS_MM
    top = [
        point + normal * outward_mm
        for point, normal in zip(projected, normals)
    ]
    opening_edge = min(
        range(len(footprint)),
        key=lambda index: (
            projected[index].lerp(
                projected[(index + 1) % len(footprint)],
                0.5,
            )
            - other_endpoint
        ).length,
    )
    pad_points = bottom + top
    count = len(footprint)
    pad_faces = [
        tuple(reversed(range(count))),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        if index == opening_edge:
            continue
        following = (index + 1) % count
        pad_faces.append(
            (index, following, following + count, index + count)
        )
    following = (opening_edge + 1) % count
    opening_ring = [
        opening_edge,
        following,
        following + count,
        opening_edge + count,
    ]
    long_coordinates = [
        (point - frame["origin"]).dot(frame["tangent"])
        for point in projected
    ]
    projected_extent = max(long_coordinates) - min(long_coordinates)
    outward_extent = max(
        (top_point - projected_point).dot(normal)
        for top_point, projected_point, normal in zip(top, projected, normals)
    )
    metrics = {
        "long_dimension_mm": long_mm,
        "short_dimension_mm": short_mm,
        "embed_mm": embed_mm,
        "projected_surface_offset_mm": surface_offset_mm,
        "measured_surface_contact_lap_mm": round(
            center_shift_mm + long_mm * 0.5,
            6,
        ),
        "outward_extent_mm": round(outward_extent, 6),
        "projected_surface_long_extent_mm": round(projected_extent, 6),
        "projection_to_outward_extent_ratio": round(
            projected_extent / max(outward_extent, 1.0e-8),
            6,
        ),
        "long_axis_terminal_tangent_alignment_abs_dot": 1.0,
        "long_axis_route_abs_dot": round(
            abs(frame["tangent"].dot(route_direction)),
            6,
        ),
        "nearby_vertex_count": frame["nearby_vertex_count"],
        "endpoint_projection_distance_mm": round(
            frame["endpoint_projection_distance_mm"],
            6,
        ),
        "tangent_rotation_degrees": rotation_degrees,
        "opening_edge_index": opening_edge,
        "interior_tangent_sign": interior_sign,
        "footprint_center_shift_mm": center_shift_mm,
        "estimated_terminal_tangent": [
            round(value, 8) for value in frame["tangent"]
        ],
        "estimated_terminal_normal": [
            round(value, 8) for value in frame["normal"]
        ],
    }
    return pad_points, pad_faces, opening_ring, metrics


def ring_normal(points, ring):
    result = Vector((0.0, 0.0, 0.0))
    for index, current in enumerate(ring):
        following = ring[(index + 1) % len(ring)]
        result.x += (points[current].y - points[following].y) * (
            points[current].z + points[following].z
        )
        result.y += (points[current].z - points[following].z) * (
            points[current].x + points[following].x
        )
        result.z += (points[current].x - points[following].x) * (
            points[current].y + points[following].y
        )
    return result.normalized()


def neck_ring(point, tangent, target_length, width):
    _, _, _, radial = v4.radial_coordinates(point, target_length)
    thickness_axis = radial - tangent * radial.dot(tangent)
    thickness_axis.normalize()
    width_axis = thickness_axis.cross(tangent).normalized()
    width_axis, thickness_axis = v8.rotated_frame(
        width_axis,
        tangent,
        120,
    )
    return [
        point.copy(),
        point + width_axis * width,
        point + width_axis * width + thickness_axis * THICKNESS_MM,
        point + thickness_axis * THICKNESS_MM,
    ]


def cyclically_align_ring(points, previous, ring):
    rotations = [
        ring[offset:] + ring[:offset]
        for offset in range(len(ring))
    ]
    return min(
        rotations,
        key=lambda candidate: sum(
            (points[first] - points[second]).length_squared
            for first, second in zip(previous, candidate)
        ),
    )


def projected_pad_geometry(
    upper_point,
    lower_point,
    upper_geometry,
    lower_geometry,
    spec,
    target_length,
):
    long_mm, short_mm, embed_mm, upper_rotation, lower_rotation = spec
    route = lower_point - upper_point
    route_length = route.length
    route.normalize()
    upper = projected_pad(
        upper_geometry,
        upper_point,
        upper_point - route * embed_mm,
        route,
        long_mm,
        short_mm,
        embed_mm,
        upper_rotation,
        target_length,
    )
    lower = projected_pad(
        lower_geometry,
        lower_point,
        lower_point + route * embed_mm,
        route,
        long_mm,
        short_mm,
        embed_mm,
        lower_rotation,
        target_length,
    )
    points = [point.copy() for point in upper[0]]
    faces = list(upper[1])
    lower_offset = len(points)
    points.extend(point.copy() for point in lower[0])
    faces.extend(
        tuple(lower_offset + index for index in face)
        for face in lower[1]
    )
    upper_open = list(upper[2])
    lower_open = [lower_offset + index for index in lower[2]]
    if ring_normal(points, upper_open).dot(route) < 0.0:
        upper_open.reverse()
    if ring_normal(points, lower_open).dot(route) < 0.0:
        lower_open.reverse()
    neck_specs = (
        (upper_point.lerp(lower_point, 0.25), MIDSPAN_SHOULDER_MM),
        (upper_point.lerp(lower_point, 0.50), MIDSPAN_MINIMUM_MM),
        (upper_point.lerp(lower_point, 0.75), MIDSPAN_SHOULDER_MM),
    )
    rings = [upper_open]
    for point, width in neck_specs:
        start = len(points)
        points.extend(neck_ring(point, route, target_length, width))
        ring = list(range(start, start + 4))
        if ring_normal(points, ring).dot(route) < 0.0:
            ring.reverse()
        ring = cyclically_align_ring(points, rings[-1], ring)
        rings.append(ring)
    lower_open = cyclically_align_ring(points, rings[-1], lower_open)
    rings.append(lower_open)
    for first, second in zip(rings, rings[1:]):
        for index in range(4):
            following = (index + 1) % 4
            faces.append(
                (
                    first[index],
                    first[following],
                    second[following],
                    second[index],
                )
            )
    faces = oriented_faces(points, faces)
    return points, faces, {
        "upper_pad": upper[3],
        "lower_pad": lower[3],
        "route_length_mm": round(route_length, 6),
        "midspan_width_profile_mm": [6.0, 4.5, 6.0],
    }


def candidate(
    upper_point,
    lower_point,
    midpoint_offset,
    midpoint_angle,
    spec,
    target_length,
    grid,
    upper_geometry,
    lower_geometry,
    allowed_open_faces,
    open_points,
    open_faces,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    del midpoint_offset, midpoint_angle
    points, faces, pad_metrics = projected_pad_geometry(
        upper_point,
        lower_point,
        upper_geometry,
        lower_geometry,
        spec,
        target_length,
    )
    upper_pairs = overlap_pairs(points, faces, *upper_geometry)
    lower_pairs = overlap_pairs(points, faces, *lower_geometry)
    full_pairs = overlap_pairs(points, faces, open_points, open_faces)
    unrelated = [pair for pair in full_pairs if pair[1] not in allowed_open_faces]
    c9_pairs = overlap_pairs(points, faces, c9_points, c9_faces)
    cutter_pairs = overlap_pairs(points, faces, cutter_points, cutter_faces)
    self_pairs = nonadjacent_self_overlaps(points, faces)
    margins = v4.v2.point_margins(points, target_length, grid)
    audit = v4.v2.base.audit_geometry(points, faces)
    quality = v4.v2.triangulated_quality(points, faces)
    pad_gate = all(
        metrics["long_axis_terminal_tangent_alignment_abs_dot"] >= 0.95
        and metrics["projected_surface_long_extent_mm"] >= 8.0
        and metrics["projection_to_outward_extent_ratio"] >= 2.5
        and metrics["outward_extent_mm"]
        <= THICKNESS_MM + 0.5 + 1.0e-4
        and metrics["measured_surface_contact_lap_mm"] >= 1.5
        for metrics in (pad_metrics["upper_pad"], pad_metrics["lower_pad"])
    )
    passed = all(
        (
            upper_pairs,
            lower_pairs,
            not unrelated,
            not c9_pairs,
            not cutter_pairs,
            not self_pairs,
            min(margins) >= 1.6998,
            audit["connected_components"] == 1,
            audit["boundary_edges"] == 0,
            audit["nonmanifold_edges"] == 0,
            audit["noncontiguous_manifold_edges"] == 0,
            audit["signed_volume_mm3"] > 0.0,
            quality["degenerate_triangle_count"] == 0,
            quality["minimum_angle_degrees"]["minimum"] >= 3.0,
            quality["aspect_ratio"]["maximum"] <= 12.0,
            pad_gate,
        )
    )
    long_mm, short_mm, embed_mm, _, _ = spec
    record = {
        "midpoint_offset_mm": 0.0,
        "midpoint_angle_degrees": 0,
        "roll_degrees": 120,
        "ring_count": 5,
        "minimum_width_mm": MIDSPAN_MINIMUM_MM,
        "maximum_width_mm": long_mm,
        "thickness_mm": THICKNESS_MM,
        "terminal_embed_mm": embed_mm,
        "pad_long_dimension_mm": long_mm,
        "pad_short_dimension_mm": short_mm,
        "pad_metrics": pad_metrics,
        "anti_fin_topology_gate": pad_gate,
        "upper_terminal_overlap_count": len(upper_pairs),
        "lower_terminal_overlap_count": len(lower_pairs),
        "full_open_overlap_count": len(full_pairs),
        "unrelated_full_open_overlap_count": len(unrelated),
        "T_CAGE_2_overlap_count": 0 if not unrelated else None,
        "T_CAGE_3_overlap_count": 0 if not unrelated else None,
        "c9_overlap_count": len(c9_pairs),
        "cutter_overlap_count": len(cutter_pairs),
        "self_overlap_count": len(self_pairs),
        "self_overlap_pairs": self_pairs,
        "self_overlap_faces": {
            str(face_id): list(faces[face_id])
            for face_id in sorted({
                face_id for pair in self_pairs for face_id in pair
            })
        },
        "minimum_cutter_margin_mm": round(min(margins), 6),
        "audit": audit,
        "triangle_quality": quality,
        "gate_pass": passed,
        "_points": points,
        "_faces": faces,
    }
    CANDIDATE_RECORDS.append(v14.public(record))
    return record


def recover_v15_authority():
    blend_path = Path(bpy.data.filepath).resolve()
    blend_sha = v14.v10.sha256_file(blend_path)
    report_sha = v14.v10.sha256_file(V15_REPORT_PATH)
    review_sha = v14.v10.sha256_file(V15_REVIEW_PATH)
    if (blend_sha, report_sha, review_sha) != (
        AUTHORITY_SHA256,
        REPORT_SHA256,
        REVIEW_SHA256,
    ):
        raise RuntimeError(
            f"{OPERATION}: authority hash mismatch for Blend/report/review: "
            f"{blend_sha}, {report_sha}, {review_sha}"
        )
    report = json.loads(V15_REPORT_PATH.read_text(encoding="utf-8"))
    review = json.loads(V15_REVIEW_PATH.read_text(encoding="utf-8"))
    if not report["gate_pass"] or review["decision"] != (
        "REPLACE_CROSS_SECTION_FANS_WITH_TERMINAL_SURFACE_CONFORMING_PADS"
    ):
        raise RuntimeError(f"{OPERATION}: v15 authorities do not authorize v16")
    missing = [name for name in V15_OBJECTS if name not in bpy.data.objects]
    if missing:
        raise RuntimeError(f"{OPERATION}: v15 authority lacks objects {missing}")
    for name in V15_OBJECTS:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    remaining = {
        obj.name for obj in bpy.data.objects
        if obj.name.startswith("EVAL_REPAIR_014")
    }
    if remaining != BASELINE_OBJECTS:
        raise RuntimeError(
            f"{OPERATION}: recovered baseline object set is {sorted(remaining)}, "
            f"expected {sorted(BASELINE_OBJECTS)}"
        )
    staged = bpy.data.objects[v4.v2.base.STAGED_NAME]
    open_cage = bpy.data.objects[v4.v2.base.OPEN_CAGE_NAME]
    staged_points, staged_faces, staged_materials = v14.evaluated_geometry(staged)
    open_points, open_faces, open_materials = v14.evaluated_geometry(open_cage)
    mapping = json.loads(v4.v2.MAPPING_PATH.read_text(encoding="utf-8"))
    retained_face_ids = sorted(mapping["reconstruction_scope"]["retain_face_ids"])
    retained_ids = sorted({
        vertex for face_id in retained_face_ids for vertex in staged_faces[face_id]
    })
    retained_fingerprint = v4.v2.fingerprint(
        retained_ids, [staged_points[index] for index in retained_ids]
    )
    removed = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    rebuilt_points, rebuilt_faces, rebuilt_materials, _, _ = v4.v2.remap_retained(
        staged_points, staged_faces, staged_materials, removed
    )
    open_exact = all((
        rebuilt_faces == open_faces,
        rebuilt_materials == open_materials,
        all((a - b).length <= 1.0e-4 for a, b in zip(rebuilt_points, open_points)),
    ))
    c9_points, c9_faces = v4.component9_geometry()
    c9_fingerprint = v4.v2.fingerprint(range(len(c9_points)), c9_points)
    centerline_ids = v4.rail_only_contract()["ordered_centerline_source_vertex_ids"]
    tip_gap = (staged_points[centerline_ids[0]] - staged_points[centerline_ids[-1]]).length
    checks = {
        "baseline_eval_objects": sorted(remaining),
        "retained_face_count": len(retained_face_ids),
        "retained_fingerprint": retained_fingerprint,
        "retained_fingerprint_exact": (
            retained_fingerprint == v15.EXPECTED_RETAINED_FINGERPRINT
        ),
        "open_lineage_and_materials_exact": open_exact,
        "component_9_vertex_count": len(c9_points),
        "component_9_face_count": len(c9_faces),
        "component_9_fingerprint": c9_fingerprint,
        "component_9_fingerprint_exact": (
            c9_fingerprint == EXPECTED_C9_FINGERPRINT
        ),
        "central_bowl_open": report["preservation"]["central_bowl_open"],
        "tip_gap_mm": round(tip_gap, 6),
        "tip_gap_exact": abs(tip_gap - 30.588488) <= 1.0e-6,
        "hard_control_error_mm": report["preservation"]["hard_control_error_mm"],
    }
    if not all((
        checks["retained_face_count"] == 1409,
        checks["retained_fingerprint_exact"],
        checks["open_lineage_and_materials_exact"],
        checks["component_9_fingerprint_exact"],
        checks["central_bowl_open"],
        checks["tip_gap_exact"],
        all(value <= 1.0e-4 for value in checks["hard_control_error_mm"].values()),
    )):
        raise RuntimeError(f"{OPERATION}: baseline proof failed: {checks}")
    return {
        "input_blend": str(blend_path),
        "input_blend_sha256": blend_sha,
        "build_report_sha256": report_sha,
        "review_sha256": review_sha,
        "removed_objects_in_memory": list(V15_OBJECTS),
        "checks_before_construction": checks,
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    authority = recover_v15_authority()
    v14.OPERATION = OPERATION
    v14.UPPER_SEED = 5702
    v14.LOWER_SEED = 1784
    v14.ENDPOINT_RADIUS_MM = 0.001
    v14.MAXIMUM_ENDPOINTS_PER_TERMINAL = 1
    v14.ROLLS_DEGREES = CANDIDATES
    v14.MIDPOINT_OFFSETS_MM = ()
    v14.candidate = candidate
    v4.v2.EXPECTED_BLEND_SHA256 = AUTHORITY_SHA256
    result = v14.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update({
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": (
            "evaluation_only_projected_terminal_surface_pads_machine_pass"
            if report["gate_pass"]
            else "evaluation_only_projected_terminal_surface_pads_machine_failed"
        ),
        "authority_recovery": authority,
        "terminal_treatment": {
            "construction_scope": "terminal projected pads and neck lofts only",
            "route": "exact V5702(T1)-to-V1784(T0)",
            "midspan_width_range_mm": [4.5, 6.0],
            "thickness_mm": THICKNESS_MM,
            "surface_operation": (
                "independent tangent-frame footprints projected to T1/T0, "
                "embedded, outward-offset, and lofted from inward edges"
            ),
            "outward_fin_or_arrowhead_topology_allowed": False,
        },
        "bounded_search": {
            "pad_long_dimensions_mm": [9.0, 10.0],
            "pad_short_dimensions_mm": [7.0, 8.0],
            "embeds_mm": [1.5, 1.8],
            "paired_tangent_rotations_degrees": [
                [0, 0],
                [0, 90],
                [0, -90],
                [15, 75],
                [-15, -75],
            ],
            "candidate_count": len(CANDIDATES),
            "records": CANDIDATE_RECORDS,
        },
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    })
    report["graph"]["nodes"][1] = "PROJECTED_SURFACE_PADS_V16"
    report["graph"]["edges"] = [
        ["T_CAGE_1", "PROJECTED_SURFACE_PADS_V16"],
        ["PROJECTED_SURFACE_PADS_V16", "T_CAGE_0"],
    ]
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"DONE: v16 projected terminal pads gate_pass={report['gate_pass']}; "
        "promotion=NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
