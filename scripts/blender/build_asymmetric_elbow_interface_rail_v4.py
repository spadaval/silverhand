"""Preflight a full-width Repair 014 rail shifted away from component 9."""

from __future__ import annotations

from copy import deepcopy
import json
from math import ceil, cos, radians, sin
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_local_elbow_interface_band_v2 as v2  # noqa: E402
from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import (  # noqa: E402
    cutter_grid,
    radial_coordinates,
)
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "ASYMMETRIC_ELBOW_INTERFACE_RAIL_V4"
TARGET_WIDTH_MM = 6.0
TIP_SEGMENTS = {0, 11}
_C9_BVH = None
FRAME_DIAGNOSTICS = []
SAMPLE_DIAGNOSTICS = []
ORIENTATION_DIAGNOSTICS = []
SAMPLE_TIP_SEGMENTS = set()
DETOUR_DIAGNOSTICS = []
ROUTE_NODE_RING = {}
OBSTRUCTED_ROUTE_SEGMENTS = {10}
RELAXED_ROUTE_CONTROL_IDS = {
    2065,
    2067,
    2068,
    2069,
    2070,
    2071,
    2073,
    2110,
}
SWEEP_OFFSET_MM = (
    float(os.environ["REPAIR014_V4_DETOUR_OFFSET_MM"])
    if "REPAIR014_V4_DETOUR_OFFSET_MM" in os.environ
    else None
)
SWEEP_ANGLE_DEGREES = (
    int(os.environ["REPAIR014_V4_DETOUR_ANGLE_DEGREES"])
    if "REPAIR014_V4_DETOUR_ANGLE_DEGREES" in os.environ
    else None
)
LOCAL_SPAN_WIDTH_MM = float(
    os.environ.get("REPAIR014_V4_LOCAL_WIDTH_MM", "6.0")
)
ADAPTIVE_MINIMUM_HALF_WIDTH_MM = float(
    os.environ.get("REPAIR014_V4_ADAPTIVE_MIN_HALF_WIDTH_MM", "1.5")
)


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def rail_only_contract() -> dict:
    contract = deepcopy(ORIGINAL_LOAD_CONTRACT())
    contract["recommended_routes_and_tabs"] = []
    contract["ordered_centerline_source_vertex_ids"] = [
        source_id
        for source_id in contract["ordered_centerline_source_vertex_ids"]
        if source_id not in RELAXED_ROUTE_CONTROL_IDS
    ]
    return contract


def component9_geometry() -> tuple[list[Vector], list[tuple[int, ...]]]:
    staged = bpy.data.objects[v2.base.STAGED_NAME]
    source = bpy.data.objects[SOURCE_NAME]
    staged_points, staged_faces, _ = evaluated_geometry(staged)
    _, components = connected_components(source)
    component9 = set(components[9])
    face_ids = {
        index
        for index, face in enumerate(staged_faces)
        if face[0] in component9
    }
    return v2.base.component_local(staged_points, staged_faces, face_ids)


def c9_bvh() -> BVHTree:
    global _C9_BVH
    if _C9_BVH is None:
        points, faces = component9_geometry()
        _C9_BVH = BVHTree.FromPolygons(points, faces, all_triangles=False)
    return _C9_BVH


def bounded_span_feasibility(first, second, target_length, grid) -> dict:
    def path_metrics(path):
        minimum_distance = float("inf")
        crossing = False
        for start, end in zip(path, path[1:]):
            delta = end - start
            length = delta.length
            direction = delta.normalized()
            hit, _, _, _ = c9_bvh().ray_cast(
                start + direction * 1.0e-4,
                direction,
                max(0.0, length - 2.0e-4),
            )
            crossing = crossing or hit is not None
            steps = max(2, int(ceil(length / 0.2)))
            for step in range(steps + 1):
                point = start.lerp(end, step / steps)
                nearest, _, _, distance = c9_bvh().find_nearest(point)
                if nearest is None:
                    raise RuntimeError(
                        f"{OPERATION}: span-scan C9 query failed"
                    )
                minimum_distance = min(minimum_distance, distance)
        return crossing, minimum_distance

    direct_crossing, direct_clearance = path_metrics([first, second])
    if not direct_crossing and direct_clearance >= 0.2:
        return {
            "feasible": True,
            "method": "direct",
            "offset_mm": 0.0,
            "minimum_distance_mm": round(direct_clearance, 6),
        }
    midpoint = first.lerp(second, 0.5)
    tangent = (second - first).normalized()
    _, _, _, radial = radial_coordinates(midpoint, target_length)
    width_axis = tangent.cross(radial).normalized()
    best_residual = None
    for waypoint_count in (1, 2):
        for offset_half_mm in range(4, 25):
            offset = 0.5 * offset_half_mm
            viable = []
            for angle_degrees in range(0, 360, 15):
                angle = radians(angle_degrees)
                direction = (
                    width_axis * cos(angle) + radial * sin(angle)
                ).normalized()
                fractions = (0.5,) if waypoint_count == 1 else (0.25, 0.75)
                waypoints = [
                    v2.clamp_to_reserved_wall(
                        first.lerp(second, fraction) + direction * offset,
                        target_length,
                        grid,
                        1.7,
                    )
                    for fraction in fractions
                ]
                if (
                    min(v2.point_margins(waypoints, target_length, grid))
                    < 1.6998
                ):
                    continue
                crossing, clearance = path_metrics(
                    [first, *waypoints, second]
                )
                residual = {
                    "waypoint_count": waypoint_count,
                    "offset_mm": offset,
                    "angle_degrees": angle_degrees,
                    "crossing": crossing,
                    "minimum_distance_mm": clearance,
                }
                if best_residual is None or (
                    not crossing,
                    clearance,
                    -offset,
                ) > (
                    not best_residual["crossing"],
                    best_residual["minimum_distance_mm"],
                    -best_residual["offset_mm"],
                ):
                    best_residual = residual
                if not crossing and clearance >= 0.2:
                    viable.append(residual)
            if viable:
                selected = max(
                    viable,
                    key=lambda record: record["minimum_distance_mm"],
                )
                return {
                    "feasible": True,
                    "method": f"{waypoint_count}_waypoint",
                    **{
                        key: (
                            round(value, 6)
                            if isinstance(value, float)
                            else value
                        )
                        for key, value in selected.items()
                    },
                }
    return {
        "feasible": False,
        "method": "bounded_sweep_exhausted",
        "best_residual": {
            key: round(value, 6) if isinstance(value, float) else value
            for key, value in best_residual.items()
        },
    }


def progressive_relaxation_scan() -> dict:
    staged = bpy.data.objects[v2.base.STAGED_NAME]
    candidate = bpy.data.objects[CANDIDATE_NAME]
    cutter = bpy.data.objects[CUTTER_NAME]
    staged_points, _, _ = evaluated_geometry(staged)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    spans = [
        (2064, 2068),
        (2064, 2069),
        (2064, 2070),
        (2064, 2071),
        (2064, 2118),
        (2071, 2118),
        (2111, 2108),
    ]
    return {
        f"{first_id}->{second_id}": bounded_span_feasibility(
            staged_points[first_id],
            staged_points[second_id],
            target_length,
            grid,
        )
        for first_id, second_id in spans
    }


def obstacle_following_sample_route(
    route,
    target_length,
    grid,
    *,
    extend_ends,
):
    if extend_ends:
        raise RuntimeError(
            f"{OPERATION}: v4 rail-only route does not support end extension"
        )
    SAMPLE_TIP_SEGMENTS.clear()
    ROUTE_NODE_RING.clear()
    DETOUR_DIAGNOSTICS.clear()

    def path_metrics(path):
        minimum_distance = float("inf")
        crossing = False
        for first, second in zip(path, path[1:]):
            delta = second - first
            length = delta.length
            direction = delta.normalized()
            hit, _, _, _ = c9_bvh().ray_cast(
                first + direction * 1.0e-4,
                direction,
                max(0.0, length - 2.0e-4),
            )
            crossing = crossing or hit is not None
            steps = max(2, int(ceil(length / 0.2)))
            for step in range(steps + 1):
                point = first.lerp(second, step / steps)
                nearest, _, _, distance = c9_bvh().find_nearest(point)
                if nearest is None:
                    raise RuntimeError(
                        f"{OPERATION}: midpoint sweep C9 query failed"
                    )
                minimum_distance = min(minimum_distance, distance)
        return crossing, minimum_distance

    paths = []
    for segment, (first, second) in enumerate(zip(route, route[1:])):
        if segment not in OBSTRUCTED_ROUTE_SEGMENTS:
            paths.append([first.copy(), second.copy()])
            continue
        midpoint = first.lerp(second, 0.5)
        tangent = (second - first).normalized()
        _, _, _, radial = radial_coordinates(midpoint, target_length)
        width_axis = tangent.cross(radial).normalized()
        viable = []
        attempted = []
        offset_half_steps = (
            [round(SWEEP_OFFSET_MM * 2.0)]
            if SWEEP_OFFSET_MM is not None
            else range(1, 25)
        )
        angle_steps = (
            [SWEEP_ANGLE_DEGREES]
            if SWEEP_ANGLE_DEGREES is not None
            else range(0, 360, 15)
        )
        for offset_half_mm in offset_half_steps:
            offset = 0.5 * offset_half_mm
            for angle_degrees in angle_steps:
                angle = radians(angle_degrees)
                direction = (
                    width_axis * cos(angle) + radial * sin(angle)
                ).normalized()
                waypoint = v2.clamp_to_reserved_wall(
                    midpoint + direction * offset,
                    target_length,
                    grid,
                    1.7,
                )
                if (
                    min(v2.point_margins([waypoint], target_length, grid))
                    < 1.6998
                ):
                    continue
                crossing, minimum_distance = path_metrics(
                    [first, waypoint, second]
                )
                attempted.append(
                    {
                        "offset_mm": offset,
                        "angle_degrees": angle_degrees,
                        "crossing": crossing,
                        "minimum_distance_mm": minimum_distance,
                    }
                )
                if crossing or minimum_distance < 0.2:
                    continue
                viable.append(
                    (
                        offset,
                        -minimum_distance,
                        angle_degrees,
                        [waypoint],
                        minimum_distance,
                    )
                )
            if viable:
                break
        if not viable:
            for offset_half_mm in offset_half_steps:
                offset = 0.5 * offset_half_mm
                for angle_degrees in angle_steps:
                    angle = radians(angle_degrees)
                    direction = (
                        width_axis * cos(angle) + radial * sin(angle)
                    ).normalized()
                    waypoints = [
                        v2.clamp_to_reserved_wall(
                            first.lerp(second, fraction)
                            + direction * offset,
                            target_length,
                            grid,
                            1.7,
                        )
                        for fraction in (0.25, 0.75)
                    ]
                    if (
                        min(
                            v2.point_margins(
                                waypoints,
                                target_length,
                                grid,
                            )
                        )
                        < 1.6998
                    ):
                        continue
                    crossing, minimum_distance = path_metrics(
                        [first, *waypoints, second]
                    )
                    if crossing or minimum_distance < 0.2:
                        continue
                    viable.append(
                        (
                            offset,
                            -minimum_distance,
                            angle_degrees,
                            waypoints,
                            minimum_distance,
                        )
                    )
                if viable:
                    break
        if not viable:
            best = max(
                attempted,
                key=lambda record: (
                    not record["crossing"],
                    record["minimum_distance_mm"],
                    -record["offset_mm"],
                ),
            )
            raise RuntimeError(
                f"{OPERATION}: one- and two-waypoint sweeps found no "
                f"0.2mm-clear detour for route segment {segment}; best "
                f"one-waypoint candidate offset={best['offset_mm']:.3f}mm "
                f"angle={best['angle_degrees']}deg "
                f"crossing={best['crossing']} "
                f"minimum_distance={best['minimum_distance_mm']:.6f}mm"
            )
        (
            selected_offset,
            _,
            selected_angle,
            selected_waypoints,
            selected_clearance,
        ) = min(viable)
        paths.append([first.copy(), *selected_waypoints, second.copy()])
        DETOUR_DIAGNOSTICS.append(
            {
                "route_segment_index": segment,
                "offset_mm": selected_offset,
                "angle_degrees": selected_angle,
                "waypoint_count": len(selected_waypoints),
                "minimum_centerline_c9_clearance_mm": round(
                    selected_clearance,
                    6,
                ),
            }
        )

    samples = [route[0].copy()]
    exact_rings = {0}
    node_ring = {0: 0}
    for segment, path in enumerate(paths):
        for leg_index, (first, second) in enumerate(zip(path, path[1:])):
            steps = max(1, int(ceil((second - first).length / 2.0)))
            for step in range(1, steps + 1):
                point = first.lerp(second, step / steps)
                is_source_endpoint = (
                    leg_index == len(path) - 2 and step == steps
                )
                if not is_source_endpoint:
                    point = v2.clamp_to_reserved_wall(
                        point,
                        target_length,
                        grid,
                        1.7,
                    )
                samples.append(point)
        node_ring[segment + 1] = len(samples) - 1
        exact_rings.add(len(samples) - 1)
    SAMPLE_DIAGNOSTICS.clear()
    SAMPLE_DIAGNOSTICS.extend(
        {
            "ring": index,
            "exact_control": index in exact_rings,
            "displacement_mm": 0.0,
        }
        for index, point in enumerate(samples)
    )
    SAMPLE_TIP_SEGMENTS.update(range(node_ring[1]))
    SAMPLE_TIP_SEGMENTS.update(
        range(node_ring[len(route) - 2], len(samples) - 1)
    )
    ROUTE_NODE_RING.update(node_ring)
    return samples, node_ring, exact_rings


def localized_half_widths(samples) -> list[float]:
    half_widths = [TARGET_WIDTH_MM * 0.5] * len(samples)
    start = ROUTE_NODE_RING[10]
    end = ROUTE_NODE_RING[11]
    local_half = LOCAL_SPAN_WIDTH_MM * 0.5
    for ring in range(start, end + 1):
        half_widths[ring] = local_half
    for distance in (1, 2):
        blend = distance / 3.0
        half_width = local_half + (
            TARGET_WIDTH_MM * 0.5 - local_half
        ) * blend
        if start - distance >= 0:
            half_widths[start - distance] = half_width
        if end + distance < len(half_widths):
            half_widths[end + distance] = half_width
    return half_widths


def fixed_width_ribbon(
    route,
    target_length,
    grid,
    *,
    extend_ends,
) -> dict:
    samples, node_ring, exact_rings = obstacle_following_sample_route(
        route,
        target_length,
        grid,
        extend_ends=extend_ends,
    )
    half_widths = localized_half_widths(samples)
    points, faces = asymmetric_ribbon_geometry(
        samples,
        half_widths,
        target_length,
        grid,
        exact_rings,
    )
    overlaps = v2.ribbon_self_overlaps(points, faces, len(samples))
    return {
        "points": points,
        "faces": faces,
        "samples": samples,
        "node_ring": node_ring,
        "exact_rings": exact_rings,
        "half_widths": half_widths,
        "width_reduction_passes": [
            {
                "iteration": 0,
                "self_overlap_pair_count": len(overlaps),
                "minimum_width_mm": round(2.0 * min(half_widths), 6),
            }
        ],
    }


def asymmetric_ribbon_geometry(
    samples,
    half_widths,
    target_length,
    grid,
    exact_rings,
):
    FRAME_DIAGNOSTICS.clear()
    ORIENTATION_DIAGNOSTICS.clear()
    frames = []
    previous_width_axis = None
    for index, (point, half_width) in enumerate(zip(samples, half_widths)):
        tangent = (
            samples[1] - point
            if index == 0
            else point - samples[index - 1]
            if index == len(samples) - 1
            else samples[index + 1] - samples[index - 1]
        ).normalized()
        _, _, _, radial = radial_coordinates(point, target_length)
        width_axis = tangent.cross(radial)
        if width_axis.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: degenerate ribbon frame at ring {index}"
            )
        width_axis.normalize()
        if (
            previous_width_axis is not None
            and width_axis.dot(previous_width_axis) < 0.0
        ):
            width_axis.negate()
        previous_width_axis = width_axis.copy()
        frames.append((point, tangent, radial, width_axis, half_width))

    candidates = []
    for index, (point, tangent, radial, width_axis, half_width) in enumerate(
        frames
    ):
        ring_candidates = []
        width = 2.0 * half_width
        for angle_degrees in range(0, 360, 10):
            angle = radians(angle_degrees)
            width_direction = (
                width_axis * cos(angle) + radial * sin(angle)
            ).normalized()
            thickness_direction = tangent.cross(width_direction).normalized()
            if thickness_direction.dot(radial) < 0.0:
                thickness_direction.negate()
            radial_bias = thickness_direction.dot(radial)
            if radial_bias < 0.2:
                continue
            new_corners = [
                point + thickness_direction * v2.RADIAL_THICKNESS_MM,
                point + width_direction * width,
                point
                + width_direction * width
                + thickness_direction * v2.RADIAL_THICKNESS_MM,
            ]
            margins = v2.point_margins(new_corners, target_length, grid)
            if min(margins) < 1.6998:
                continue
            clearance_samples = []
            for width_fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
                for thickness_fraction in (0.0, 0.5, 1.0):
                    if width_fraction == 0.0 and thickness_fraction == 0.0:
                        continue
                    sample = (
                        point
                        + width_direction * width * width_fraction
                        + thickness_direction
                        * v2.RADIAL_THICKNESS_MM
                        * thickness_fraction
                    )
                    nearest, _, _, distance = c9_bvh().find_nearest(sample)
                    if nearest is None:
                        raise RuntimeError(
                            f"{OPERATION}: nearest component-9 query failed "
                            f"for orientation candidate at ring {index}"
                        )
                    clearance_samples.append(distance)
            ring_candidates.append(
                {
                    "angle_degrees": angle_degrees,
                    "width_direction": width_direction,
                    "thickness_direction": thickness_direction,
                    "radial_bias": radial_bias,
                    "minimum_c9_sample_clearance_mm": min(clearance_samples),
                    "minimum_cutter_margin_mm": min(margins),
                    "ring_points": [
                        point.copy(),
                        point
                        + thickness_direction * v2.RADIAL_THICKNESS_MM,
                        point
                        + width_direction * width * 0.5
                        + thickness_direction * v2.RADIAL_THICKNESS_MM,
                        point
                        + width_direction * width
                        + thickness_direction * v2.RADIAL_THICKNESS_MM,
                        point + width_direction * width,
                    ],
                }
            )
        if not ring_candidates:
            raise RuntimeError(
                f"{OPERATION}: no cutter-clear positive-radial rectangle "
                f"orientation exists at ring {index}"
            )
        candidates.append(ring_candidates)

    scores = []
    parents = []
    for index, ring_candidates in enumerate(candidates):
        ring_scores = []
        ring_parents = []
        for candidate in ring_candidates:
            local_score = 12.0 * min(
                candidate["minimum_c9_sample_clearance_mm"],
                4.0,
            )
            if index == 0:
                ring_scores.append(local_score)
                ring_parents.append(None)
                continue
            options = []
            for previous_index, previous in enumerate(candidates[index - 1]):
                segment_points = (
                    previous["ring_points"] + candidate["ring_points"]
                )
                segment_faces = [
                    (
                        side,
                        5 + side,
                        5 + (side + 1) % 5,
                        (side + 1) % 5,
                    )
                    for side in range(5)
                ]
                segment_bvh = BVHTree.FromPolygons(
                    segment_points,
                    segment_faces,
                    all_triangles=False,
                )
                overlap_count = len(segment_bvh.overlap(c9_bvh()))
                collision_cost = (
                    0.0
                    if index - 1 in SAMPLE_TIP_SEGMENTS
                    else 10000.0 * overlap_count
                )
                smoothness_cost = (
                    2.0
                    * (
                        1.0
                        - candidate["width_direction"].dot(
                            previous["width_direction"]
                        )
                    )
                    + 1.0
                    * (
                        1.0
                        - candidate["thickness_direction"].dot(
                            previous["thickness_direction"]
                        )
                    )
                )
                options.append(
                    (
                        scores[index - 1][previous_index]
                        + local_score
                        - smoothness_cost
                        - collision_cost,
                        previous_index,
                    )
                )
            best_score, best_parent = max(options)
            ring_scores.append(best_score)
            ring_parents.append(best_parent)
        scores.append(ring_scores)
        parents.append(ring_parents)
    selected_indices = [max(range(len(scores[-1])), key=scores[-1].__getitem__)]
    for index in range(len(candidates) - 1, 0, -1):
        selected_indices.append(parents[index][selected_indices[-1]])
    selected_indices.reverse()

    points = []
    for index, ((point, _, radial, width_axis, half_width), selected_index) in (
        enumerate(zip(frames, selected_indices))
    ):
        selected = candidates[index][selected_index]
        width_direction = selected["width_direction"]
        thickness_direction = selected["thickness_direction"]
        nearest, _, _, _ = c9_bvh().find_nearest(point)
        lateral = nearest - point
        lateral -= radial * lateral.dot(radial)
        toward_axis = (
            width_axis
            if lateral.dot(width_axis) >= 0.0
            else -width_axis
        )
        FRAME_DIAGNOSTICS.append(
            {
                "ring": index,
                "exact_control": index in exact_rings,
                "nearest_c9_distance_mm": round((nearest - point).length, 6),
                "signed_lateral_mm": round(lateral.dot(width_axis), 6),
                "toward_axis_sign": (
                    1 if toward_axis.dot(width_axis) > 0.0 else -1
                ),
            }
        )
        width = 2.0 * half_width
        c20_edge = point + width_direction * width
        out_c9 = point + thickness_direction * v2.RADIAL_THICKNESS_MM
        out_c20 = c20_edge + thickness_direction * v2.RADIAL_THICKNESS_MM
        out_mid = out_c9.lerp(out_c20, 0.5)
        # This is a four-corner rectangular cross-section. The collinear
        # out_mid subdivision preserves the established five-index ring
        # bookkeeping without adding a geometric corner.
        ring = [point.copy(), out_c9, out_mid, out_c20, c20_edge]
        for ring_index in range(1, len(ring)):
            ring[ring_index] = v2.clamp_to_reserved_wall(
                ring[ring_index],
                target_length,
                grid,
                1.7,
            )
        if index not in exact_rings:
            ring[0] = v2.clamp_to_reserved_wall(
                ring[0],
                target_length,
                grid,
                1.7,
            )
        points.extend(ring)
        ORIENTATION_DIAGNOSTICS.append(
            {
                "ring": index,
                "exact_control": index in exact_rings,
                "angle_degrees": selected["angle_degrees"],
                "thickness_radial_bias": round(
                    selected["radial_bias"],
                    6,
                ),
                "minimum_sampled_c9_clearance_mm": round(
                    selected["minimum_c9_sample_clearance_mm"],
                    6,
                ),
                "minimum_new_corner_cutter_margin_mm": round(
                    selected["minimum_cutter_margin_mm"],
                    6,
                ),
            }
        )
    faces = []
    ring_size = 5
    for index in range(len(samples) - 1):
        first = index * ring_size
        second = (index + 1) * ring_size
        for side in range(ring_size):
            following = (side + 1) % ring_size
            faces.append(
                (
                    first + side,
                    second + side,
                    second + following,
                    first + following,
                )
            )
    last = (len(samples) - 1) * ring_size
    faces.extend(
        (
            tuple(range(ring_size)),
            tuple(last + index for index in reversed(range(ring_size))),
        )
    )
    return points, v2.base.positive_faces(points, faces)


def localize_component9_overlaps(report: dict) -> dict:
    network = bpy.data.objects[report["objects"]["network"]]
    network_points, network_faces, _ = evaluated_geometry(network)
    c9_points, c9_faces = component9_geometry()
    pairs = overlap_pairs(
        network_points,
        network_faces,
        c9_points,
        c9_faces,
    )
    centerline_ids = rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    by_segment = {
        f"{first}->{second}": 0
        for first, second in zip(centerline_ids, centerline_ids[1:])
    }
    tip_pair_count = 0
    non_tip_pair_count = 0
    for network_face_id, _ in pairs:
        centroid = sum(
            (network_points[index] for index in network_faces[network_face_id]),
            Vector(),
        ) / len(network_faces[network_face_id])
        segment = min(
            range(len(centerline_ids) - 1),
            key=lambda index: min(
                (
                    centroid
                    - bpy.data.objects[v2.base.STAGED_NAME].data.vertices[
                        centerline_ids[index]
                    ].co
                ).length,
                (
                    centroid
                    - bpy.data.objects[v2.base.STAGED_NAME].data.vertices[
                        centerline_ids[index + 1]
                    ].co
                ).length,
            ),
        )
        key = f"{centerline_ids[segment]}->{centerline_ids[segment + 1]}"
        by_segment[key] += 1
        if segment in TIP_SEGMENTS:
            tip_pair_count += 1
        else:
            non_tip_pair_count += 1
    return {
        "total_overlap_count": len(pairs),
        "tip_overlap_count": tip_pair_count,
        "non_tip_overlap_count": non_tip_pair_count,
        "by_route_segment": by_segment,
        "allowed_tip_segments": [
            f"{centerline_ids[index]}->{centerline_ids[index + 1]}"
            for index in sorted(TIP_SEGMENTS)
        ],
    }


def exact_control_feasibility_audit() -> dict:
    staged = bpy.data.objects[v2.base.STAGED_NAME]
    staged_points, _, _ = evaluated_geometry(staged)
    centerline_ids = rail_only_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    bvh = c9_bvh()
    controls = []
    for source_id in centerline_ids:
        point = staged_points[source_id]
        nearest, _, _, distance = bvh.find_nearest(point)
        if nearest is None:
            raise RuntimeError(
                f"{OPERATION}: exact-control C9 query failed for V{source_id}"
            )
        controls.append(
            {
                "source_vertex_id": source_id,
                "nearest_c9_distance_mm": round(distance, 6),
                "epsilon_0_2mm_obstructed": (
                    source_id not in {2074, 2119} and distance <= 0.2
                ),
            }
        )
    chords = []
    for index, (first_id, second_id) in enumerate(
        zip(centerline_ids, centerline_ids[1:])
    ):
        first = staged_points[first_id]
        second = staged_points[second_id]
        delta = second - first
        length = delta.length
        direction = delta.normalized()
        ray_origin = first + direction * 1.0e-4
        hit, _, _, hit_distance = bvh.ray_cast(
            ray_origin,
            direction,
            max(0.0, length - 2.0e-4),
        )
        steps = max(2, int(length / 0.1) + 1)
        sampled_distances = []
        for step in range(steps + 1):
            point = first.lerp(second, step / steps)
            nearest, _, _, distance = bvh.find_nearest(point)
            if nearest is None:
                raise RuntimeError(
                    f"{OPERATION}: chord C9 query failed for "
                    f"V{first_id}->V{second_id}"
                )
            sampled_distances.append(distance)
        allowed_tip = index in TIP_SEGMENTS
        chords.append(
            {
                "segment": f"{first_id}->{second_id}",
                "allowed_tip_segment": allowed_tip,
                "ray_surface_crossing": hit is not None,
                "first_hit_distance_mm": (
                    round(hit_distance, 6) if hit is not None else None
                ),
                "minimum_sampled_c9_distance_mm": round(
                    min(sampled_distances),
                    6,
                ),
                "epsilon_0_2mm_tube_obstructed": (
                    not allowed_tip and min(sampled_distances) <= 0.2
                ),
            }
        )
    return {
        "epsilon_mm": 0.2,
        "controls": controls,
        "chords": chords,
        "obstructed_non_tip_control_ids": [
            record["source_vertex_id"]
            for record in controls
            if record["epsilon_0_2mm_obstructed"]
        ],
        "obstructed_non_tip_segments": [
            record["segment"]
            for record in chords
            if record["epsilon_0_2mm_tube_obstructed"]
            or (
                not record["allowed_tip_segment"]
                and record["ray_surface_crossing"]
            )
        ],
    }


ORIGINAL_LOAD_CONTRACT = v2.load_contract


def main() -> int:
    v2.OPERATION = OPERATION
    v2.__file__ = __file__
    v2.MAXIMUM_SAMPLE_SPACING_MM = 2.0
    v2.MINIMUM_HALF_WIDTH_MM = ADAPTIVE_MINIMUM_HALF_WIDTH_MM
    v2.load_contract = rail_only_contract
    v2.sample_route = obstacle_following_sample_route
    v2.ribbon_geometry = asymmetric_ribbon_geometry
    v2.adaptive_ribbon = fixed_width_ribbon
    result = v2.main()
    report_path = report_argument()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    localization = localize_component9_overlaps(report)
    feasibility = exact_control_feasibility_audit()
    network = bpy.data.objects[report["objects"]["network"]]
    network_points, _, _ = evaluated_geometry(network)
    physical_widths = [
        (network_points[index + 4] - network_points[index]).length
        for index in range(0, len(network_points), 5)
    ]
    physical_thicknesses = [
        (network_points[index + 1] - network_points[index]).length
        for index in range(0, len(network_points), 5)
    ]
    report["band"]["minimum_local_width_mm"] = round(
        min(physical_widths),
        6,
    )
    report["band"]["maximum_local_width_mm"] = round(
        max(physical_widths),
        6,
    )
    report["band"]["physical_cross_section_edges"] = {
        "width_edge_mm": {
            "minimum": round(min(physical_widths), 6),
            "maximum": round(max(physical_widths), 6),
        },
        "thickness_edge_mm": {
            "minimum": round(min(physical_thicknesses), 6),
            "maximum": round(max(physical_thicknesses), 6),
        },
        "measurement": (
            "per ring: exact-corner index 0 to width-corner index 4; "
            "exact-corner index 0 to thickness-corner index 1"
        ),
    }
    report["status"] = "evaluation_only_not_promoted"
    report["v4_preflight"] = {
        "scope": "rail only; attachments intentionally deferred",
        "localized_2111_to_2108_width_mm": LOCAL_SPAN_WIDTH_MM,
        "relaxed_route_control_ids": sorted(RELAXED_ROUTE_CONTROL_IDS),
        "target_width_mm": TARGET_WIDTH_MM,
        "component_9_edge_offset_mm": 0.0,
        "component_20_side_nominal_width_mm": TARGET_WIDTH_MM,
        "cross_section": (
            "four-corner rectangle; exact control is C9-facing wearer-side "
            "corner; collinear top-edge subdivision preserves ring indexing"
        ),
        "frame_diagnostics": FRAME_DIAGNOSTICS,
        "sample_diagnostics": SAMPLE_DIAGNOSTICS,
        "orientation_diagnostics": ORIENTATION_DIAGNOSTICS,
        "detour_diagnostics": DETOUR_DIAGNOSTICS,
        "component_9_overlap_localization": localization,
        "exact_control_feasibility": feasibility,
    }
    report["gates"].pop("attachment_graph_connected", None)
    report["gates"]["no_attachments_in_preflight"] = (
        not report["attachments"]["records"]
    )
    report["gates"]["non_tip_component_9_clear"] = (
        localization["non_tip_overlap_count"] == 0
    )
    report["gates"]["minimum_physical_width_3mm"] = (
        min(physical_widths) >= 3.0 - 1.0e-4
    )
    report["gate_pass"] = all(report["gates"].values())
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "tool": Path(__file__).name,
                "gate_pass": report["gate_pass"],
                "component_9_overlap_localization": localization,
            },
            indent=2,
        )
    )
    print(
        f"DONE: v4 rail-only preflight gate_pass={report['gate_pass']}; "
        f"non_tip_c9_pairs={localization['non_tip_overlap_count']}; "
        "promotion NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
