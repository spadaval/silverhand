"""Add the four required flared gussets to the saved v6 rail."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from math import cos, radians, sin
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_local_elbow_interface_band_v2 as v2  # noqa: E402
import build_local_elbow_interface_band_v3 as v3  # noqa: E402
from apply_bounded_clearance_patch import (  # noqa: E402
    evaluated_geometry,
    point_margins,
)
from build_combined_authored_inner_bowl_liner import (  # noqa: E402
    fingerprint,
    sha256_file,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, radial_coordinates  # noqa: E402
from try_cutter_patch_reconstruction import (  # noqa: E402
    create_object,
    ensure_collection,
    overlap_pairs,
)


OPERATION = "FLARED_GUSSET_NETWORK_V7"
EXPECTED_INPUT_SHA256 = (
    "68490689380360180cd106147ba1c0fc182710be1ef0315f7b7692b229c0d264"
)
CONTRACT_PATH = v2.CONTRACT_PATH
V6_RESULT_NAME = "EVAL_REPAIR_014_ANCHOR_TRANSITION_V6_AFTER"
V6_NETWORK_NAME = "EVAL_REPAIR_014_ANCHOR_TRANSITION_V6_NETWORK"
RESULT_COLLECTION = v2.REVIEW_COLLECTION
MAXIMUM_SAMPLE_SPACING_MM = 2.0
END_HALF_WIDTH_MM = 3.0
MID_HALF_WIDTH_MM = 1.8


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-blend-sha256",
        default=EXPECTED_INPUT_SHA256,
    )
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(sys.argv[separator + 1 :])


def flared_geometry(
    route,
    target_length,
    grid,
    *,
    end_half_width=END_HALF_WIDTH_MM,
    mid_half_width=MID_HALF_WIDTH_MM,
) -> dict:
    old_spacing = v2.MAXIMUM_SAMPLE_SPACING_MM
    v2.MAXIMUM_SAMPLE_SPACING_MM = MAXIMUM_SAMPLE_SPACING_MM
    try:
        samples, node_ring, exact_rings = v2.sample_route(
            route,
            target_length,
            grid,
            extend_ends=True,
        )
    finally:
        v2.MAXIMUM_SAMPLE_SPACING_MM = old_spacing
    half_widths = []
    denominator = max(1, len(samples) - 1)
    for index in range(len(samples)):
        normalized = index / denominator
        edge_factor = abs(2.0 * normalized - 1.0)
        smooth = edge_factor * edge_factor * (3.0 - 2.0 * edge_factor)
        half_widths.append(
            mid_half_width
            + (end_half_width - mid_half_width) * smooth
        )
    points, faces = v3.cap_safe_ribbon_geometry(
        samples,
        half_widths,
        target_length,
        grid,
        exact_rings,
    )
    return {
        "points": points,
        "faces": faces,
        "samples": samples,
        "node_ring": node_ring,
        "exact_rings": exact_rings,
        "half_widths": half_widths,
    }


def quality(points, faces) -> dict:
    return v2.triangulated_quality(points, faces)


def rerouted_island_1_to_3(
    first,
    second,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    midpoint = first.lerp(second, 0.5)
    tangent = (second - first).normalized()
    _, _, _, radial = radial_coordinates(midpoint, target_length)
    width_axis = tangent.cross(radial).normalized()
    attempts = []
    for offset_half in range(1, 25):
        offset = 0.5 * offset_half
        passing = []
        for angle_degrees in range(0, 360, 15):
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
            geometry = flared_geometry(
                [first, waypoint, second],
                target_length,
                grid,
            )
            c9_count = len(
                overlap_pairs(
                    geometry["points"],
                    geometry["faces"],
                    c9_points,
                    c9_faces,
                )
            )
            cutter_count = len(
                overlap_pairs(
                    geometry["points"],
                    geometry["faces"],
                    cutter_points,
                    cutter_faces,
                )
            )
            self_count = len(
                v2.ribbon_self_overlaps(
                    geometry["points"],
                    geometry["faces"],
                    len(geometry["samples"]),
                )
            )
            triangle_quality = quality(
                geometry["points"],
                geometry["faces"],
            )
            margins = point_margins(
                geometry["points"],
                target_length,
                grid,
            )
            gate_pass = (
                c9_count == 0
                and cutter_count == 0
                and self_count == 0
                and min(margins) >= 1.5998
                and triangle_quality["degenerate_triangle_count"] == 0
                and triangle_quality["minimum_angle_degrees"]["minimum"]
                >= 3.0
                and triangle_quality["aspect_ratio"]["maximum"] <= 12.0
            )
            record = {
                "offset_mm": offset,
                "angle_degrees": angle_degrees,
                "c9_overlap_count": c9_count,
                "cutter_overlap_count": cutter_count,
                "self_overlap_count": self_count,
                "minimum_margin_mm": round(min(margins), 6),
                "minimum_angle_degrees": triangle_quality[
                    "minimum_angle_degrees"
                ]["minimum"],
                "maximum_aspect_ratio": triangle_quality[
                    "aspect_ratio"
                ]["maximum"],
                "gate_pass": gate_pass,
                "_geometry": geometry,
            }
            attempts.append(record)
            if gate_pass:
                passing.append(record)
        if passing:
            selected = min(
                passing,
                key=lambda item: (
                    item["offset_mm"],
                    item["angle_degrees"],
                ),
            )
            return selected["_geometry"], {
                "attempt_count": len(attempts),
                "selected": {
                    key: value
                    for key, value in selected.items()
                    if not key.startswith("_")
                },
            }
    best = min(
        attempts,
        key=lambda item: (
            item["c9_overlap_count"],
            item["self_overlap_count"],
            item["cutter_overlap_count"],
            item["offset_mm"],
        ),
    )
    raise RuntimeError(
        f"{OPERATION}: island-1→3 reroute has no passing candidate within "
        f"12 mm; best offset={best['offset_mm']:.3f} mm "
        f"angle={best['angle_degrees']}° "
        f"c9={best['c9_overlap_count']} "
        f"self={best['self_overlap_count']} "
        f"cutter={best['cutter_overlap_count']}"
    )


def geometry_gate(
    geometry,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
    first_points,
    first_faces,
    island3_points,
    island3_faces,
):
    triangle_quality = quality(geometry["points"], geometry["faces"])
    margins = point_margins(geometry["points"], target_length, grid)
    record = {
        "c9_overlap_count": len(
            overlap_pairs(
                geometry["points"],
                geometry["faces"],
                c9_points,
                c9_faces,
            )
        ),
        "cutter_overlap_count": len(
            overlap_pairs(
                geometry["points"],
                geometry["faces"],
                cutter_points,
                cutter_faces,
            )
        ),
        "self_overlap_count": len(
            v2.ribbon_self_overlaps(
                geometry["points"],
                geometry["faces"],
                len(geometry["samples"]),
            )
        ),
        "minimum_margin_mm": round(min(margins), 6),
        "minimum_angle_degrees": triangle_quality[
            "minimum_angle_degrees"
        ]["minimum"],
        "maximum_aspect_ratio": triangle_quality["aspect_ratio"]["maximum"],
        "first_contact_count": len(
            overlap_pairs(
                geometry["points"],
                geometry["faces"],
                first_points,
                first_faces,
            )
        ),
        "island3_contact_count": len(
            overlap_pairs(
                geometry["points"],
                geometry["faces"],
                island3_points,
                island3_faces,
            )
        ),
    }
    record["gate_pass"] = (
        record["c9_overlap_count"] == 0
        and record["cutter_overlap_count"] == 0
        and record["self_overlap_count"] == 0
        and record["minimum_margin_mm"] >= 1.5998
        and record["minimum_angle_degrees"] >= 3.0
        and record["maximum_aspect_ratio"] <= 12.0
        and record["first_contact_count"] > 0
        and record["island3_contact_count"] > 0
    )
    return record


def select_island3_edge(
    staged_points,
    cage_points,
    cage_faces,
    open_cage,
    rail_points,
    rail_faces,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    _, components = connected_components(open_cage)
    marker_ids = {
        "0": 5702,
        "1": 4875,
        "2": 3924,
        "3": 4877,
    }
    labeled = {}
    remaining = list(components)
    for label, source_id in marker_ids.items():
        component = min(
            remaining,
            key=lambda item: min(
                (cage_points[index] - staged_points[source_id]).length
                for index in item
            ),
        )
        labeled[label] = component
        remaining.remove(component)
    component_geometry = {}
    for label, component in labeled.items():
        face_ids = {
            index
            for index, face in enumerate(cage_faces)
            if face[0] in component
        }
        component_geometry[label] = v2.base.component_local(
            cage_points,
            cage_faces,
            face_ids,
        )
    targets = {
        "0": (
            [cage_points[index] for index in sorted(labeled["0"])],
            *component_geometry["0"],
        ),
        "1": (
            [cage_points[index] for index in sorted(labeled["1"])],
            *component_geometry["1"],
        ),
        "2": (
            [cage_points[index] for index in sorted(labeled["2"])],
            *component_geometry["2"],
        ),
        "B": (rail_points, rail_points, rail_faces),
    }
    island3_vertices = [
        cage_points[index] for index in sorted(labeled["3"])
    ]
    island3_points, island3_faces = component_geometry["3"]
    ranked = []
    for label, (target_vertices, _, _) in targets.items():
        pairs = sorted(
            (
                ((first - second).length, first, second)
                for first in target_vertices
                for second in island3_vertices
            ),
            key=lambda item: item[0],
        )[:50]
        ranked.extend((distance, label, first, second) for distance, first, second in pairs)
    ranked.sort(key=lambda item: item[0])
    attempts = []
    passing = []
    for distance, label, first, second in ranked:
        first_points, first_faces = targets[label][1:]
        geometry = flared_geometry(
            [first, second],
            target_length,
            grid,
            end_half_width=2.0,
            mid_half_width=1.2,
        )
        audit = geometry_gate(
            geometry,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
            first_points,
            first_faces,
            island3_points,
            island3_faces,
        )
        record = {
            "method": "direct",
            "target": label,
            "endpoint_distance_mm": round(distance, 6),
            **audit,
            "_geometry": geometry,
        }
        attempts.append(record)
        if audit["gate_pass"]:
            passing.append(record)
    if not passing:
        for distance, label, first, second in ranked[:40]:
            first_points, first_faces = targets[label][1:]
            midpoint = first.lerp(second, 0.5)
            tangent = (second - first).normalized()
            _, _, _, radial = radial_coordinates(midpoint, target_length)
            width_axis = tangent.cross(radial).normalized()
            found = False
            for offset_half in range(1, 25):
                offset = 0.5 * offset_half
                for angle_degrees in range(0, 360, 15):
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
                    geometry = flared_geometry(
                        [first, waypoint, second],
                        target_length,
                        grid,
                        end_half_width=2.0,
                        mid_half_width=1.2,
                    )
                    audit = geometry_gate(
                        geometry,
                        target_length,
                        grid,
                        c9_points,
                        c9_faces,
                        cutter_points,
                        cutter_faces,
                        first_points,
                        first_faces,
                        island3_points,
                        island3_faces,
                    )
                    record = {
                        "method": "one_midpoint",
                        "target": label,
                        "endpoint_distance_mm": round(distance, 6),
                        "offset_mm": offset,
                        "angle_degrees": angle_degrees,
                        **audit,
                        "_geometry": geometry,
                    }
                    attempts.append(record)
                    if audit["gate_pass"]:
                        passing.append(record)
                        found = True
                        break
                if found:
                    break
    if not passing:
        best = min(
            attempts,
            key=lambda item: (
                item["c9_overlap_count"],
                item["self_overlap_count"],
                item["cutter_overlap_count"],
                item["endpoint_distance_mm"],
            ),
        )
        raise RuntimeError(
            f"{OPERATION}: no island-3 graph edge passes; best "
            f"target={best['target']} method={best['method']} "
            f"distance={best['endpoint_distance_mm']:.6f} mm "
            f"c9={best['c9_overlap_count']} "
            f"self={best['self_overlap_count']} "
            f"cutter={best['cutter_overlap_count']}"
        )
    selected = min(
        passing,
        key=lambda item: (
            item["endpoint_distance_mm"],
            0 if item["method"] == "direct" else 1,
            item.get("offset_mm", 0.0),
        ),
    )
    return selected["_geometry"], selected["target"], {
        "attempt_count": len(attempts),
        "passing_count": len(passing),
        "selected": {
            key: value
            for key, value in selected.items()
            if not key.startswith("_")
        },
    }


def component_near_marker(
    open_cage,
    cage_points,
    cage_faces,
    marker,
):
    _, components = connected_components(open_cage)
    component = min(
        components,
        key=lambda item: min(
            (cage_points[index] - marker).length for index in item
        ),
    )
    face_ids = {
        index
        for index, face in enumerate(cage_faces)
        if face[0] in component
    }
    local_points, local_faces = v2.base.component_local(
        cage_points,
        cage_faces,
        face_ids,
    )
    return (
        [cage_points[index] for index in sorted(component)],
        local_points,
        local_faces,
    )


def select_direct_graph_edge(
    first_vertices,
    first_points,
    first_faces,
    second_vertices,
    second_points,
    second_faces,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    ranked = sorted(
        (
            ((first - second).length, first, second)
            for first in first_vertices
            for second in second_vertices
        ),
        key=lambda item: item[0],
    )[:100]
    attempts = []
    for distance, first, second in ranked:
        geometry = flared_geometry([first, second], target_length, grid)
        audit = geometry_gate(
            geometry,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
            first_points,
            first_faces,
            second_points,
            second_faces,
        )
        record = {
            "method": "nearest_direct",
            "endpoint_distance_mm": round(distance, 6),
            **audit,
            "_geometry": geometry,
        }
        attempts.append(record)
    passing = [record for record in attempts if record["gate_pass"]]
    if not passing:
        for distance, first, second in ranked[:10]:
            midpoint = first.lerp(second, 0.5)
            tangent = (second - first).normalized()
            _, _, _, radial = radial_coordinates(midpoint, target_length)
            width_axis = tangent.cross(radial).normalized()
            found = False
            for offset_half in range(1, 25):
                offset = 0.5 * offset_half
                for angle_degrees in range(0, 360, 15):
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
                    geometry = flared_geometry(
                        [first, waypoint, second],
                        target_length,
                        grid,
                    )
                    audit = geometry_gate(
                        geometry,
                        target_length,
                        grid,
                        c9_points,
                        c9_faces,
                        cutter_points,
                        cutter_faces,
                        first_points,
                        first_faces,
                        second_points,
                        second_faces,
                    )
                    record = {
                        "method": "nearest_one_midpoint",
                        "endpoint_distance_mm": round(distance, 6),
                        "offset_mm": offset,
                        "angle_degrees": angle_degrees,
                        **audit,
                        "_geometry": geometry,
                    }
                    attempts.append(record)
                    if audit["gate_pass"]:
                        passing.append(record)
                        found = True
                        break
                if found:
                    break
        if not passing:
            best = min(
                attempts,
                key=lambda item: (
                    item["c9_overlap_count"],
                    item["self_overlap_count"],
                    item["cutter_overlap_count"],
                    item["endpoint_distance_mm"],
                ),
            )
            raise RuntimeError(
                f"{OPERATION}: nearest graph-edge search has no passing "
                f"candidate; best distance="
                f"{best['endpoint_distance_mm']:.6f} mm "
                f"method={best['method']} c9={best['c9_overlap_count']} "
                f"self={best['self_overlap_count']} "
                f"cutter={best['cutter_overlap_count']}"
            )
    selected = min(passing, key=lambda item: item["endpoint_distance_mm"])
    return selected["_geometry"], {
        "attempt_count": len(attempts),
        "passing_count": len(passing),
        "selected": {
            key: value
            for key, value in selected.items()
            if not key.startswith("_")
        },
    }


def select_extended_historical_edge(
    rail_vertices,
    rail_faces,
    historical_route,
    island_points,
    island_faces,
    target_length,
    grid,
    c9_points,
    c9_faces,
    cutter_points,
    cutter_faces,
):
    ranked = sorted(
        (
            ((point - historical_route[0]).length, point)
            for point in rail_vertices
        ),
        key=lambda item: item[0],
    )[:100]
    attempts = []
    for distance, rail_point in ranked:
        geometry = flared_geometry(
            [rail_point, *historical_route],
            target_length,
            grid,
            end_half_width=2.0,
            mid_half_width=1.2,
        )
        audit = geometry_gate(
            geometry,
            target_length,
            grid,
            c9_points,
            c9_faces,
            cutter_points,
            cutter_faces,
            rail_vertices,
            rail_faces,
            island_points,
            island_faces,
        )
        record = {
            "method": "historical_route_with_local_rail_prepend",
            "prepend_length_mm": round(distance, 6),
            **audit,
            "_geometry": geometry,
        }
        attempts.append(record)
    passing = [record for record in attempts if record["gate_pass"]]
    if not passing:
        best = min(
            attempts,
            key=lambda item: (
                item["c9_overlap_count"],
                item["self_overlap_count"],
                item["cutter_overlap_count"],
                item["prepend_length_mm"],
            ),
        )
        raise RuntimeError(
            f"{OPERATION}: historical-route prepend has no passing "
            f"candidate; best prepend={best['prepend_length_mm']:.6f} mm "
            f"c9={best['c9_overlap_count']} "
            f"self={best['self_overlap_count']} "
            f"cutter={best['cutter_overlap_count']}"
        )
    selected = min(passing, key=lambda item: item["prepend_length_mm"])
    return selected["_geometry"], {
        "attempt_count": len(attempts),
        "passing_count": len(passing),
        "selected": {
            key: value
            for key, value in selected.items()
            if not key.startswith("_")
        },
    }


def main() -> int:
    args = parse_args()
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha = sha256_file(blend_path)
    if actual_sha != args.required_blend_sha256:
        raise RuntimeError(
            f"{OPERATION}: input Blend '{blend_path}' has SHA-256 "
            f"'{actual_sha}', expected '{args.required_blend_sha256}'"
        )
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    v6_result = bpy.data.objects[V6_RESULT_NAME]
    v6_network = bpy.data.objects[V6_NETWORK_NAME]
    staged = bpy.data.objects[v2.base.STAGED_NAME]
    open_cage = bpy.data.objects[v2.base.OPEN_CAGE_NAME]
    candidate = bpy.data.objects[CANDIDATE_NAME]
    cutter = bpy.data.objects[CUTTER_NAME]
    result_points, result_faces, result_materials = evaluated_geometry(v6_result)
    rail_points, rail_faces, rail_materials = evaluated_geometry(v6_network)
    staged_points, _, _ = evaluated_geometry(staged)
    cage_points, cage_faces, _ = evaluated_geometry(open_cage)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    c9_points, c9_faces = v4.component9_geometry()
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    required_routes = [
        route
        for route in contract["recommended_routes_and_tabs"]
        if route["required"]
    ]
    geometries = []
    reroute_report = None
    island3_target = None
    edge_search_reports = {}
    for route in required_routes:
        route_points = [
            staged_points[source_id]
            for source_id in route["vertex_ids"]
        ]
        if route["role"] in {"band_to_island_1", "band_to_island_2"}:
            (
                _,
                island_points,
                island_faces,
            ) = component_near_marker(
                open_cage,
                cage_points,
                cage_faces,
                route_points[-1],
            )
            geometry, edge_report = select_extended_historical_edge(
                rail_points,
                rail_faces,
                route_points,
                island_points,
                island_faces,
                target_length,
                grid,
                c9_points,
                c9_faces,
                cutter_points,
                cutter_faces,
            )
            edge_search_reports[route["role"]] = edge_report
        elif route["role"] == "island_1_to_island_3":
            geometry, island3_target, reroute_report = select_island3_edge(
                staged_points,
                cage_points,
                cage_faces,
                open_cage,
                rail_points,
                rail_faces,
                target_length,
                grid,
                c9_points,
                c9_faces,
                cutter_points,
                cutter_faces,
            )
        else:
            geometry = flared_geometry(
                route_points,
                target_length,
                grid,
            )
        geometries.append((route, geometry))
    composite_points = [point.copy() for point in result_points]
    composite_faces = list(result_faces)
    composite_materials = list(result_materials)
    network_points = [point.copy() for point in rail_points]
    network_faces = list(rail_faces)
    network_materials = list(rail_materials)
    material = Counter(result_materials).most_common(1)[0][0]
    records = []
    for route, geometry in geometries:
        result_vertex_start, result_face_start = v2.base.append_geometry(
            composite_points,
            composite_faces,
            geometry["points"],
            geometry["faces"],
        )
        composite_materials.extend([material] * len(geometry["faces"]))
        network_vertex_start, network_face_start = v2.base.append_geometry(
            network_points,
            network_faces,
            geometry["points"],
            geometry["faces"],
        )
        network_materials.extend([material] * len(geometry["faces"]))
        margins = point_margins(
            geometry["points"],
            target_length,
            grid,
        )
        record = {
            "role": route["role"],
            "source_vertex_ids": route["vertex_ids"],
            "offsets": {
                "result_vertex_start": result_vertex_start,
                "result_face_start": result_face_start,
                "network_vertex_start": network_vertex_start,
                "network_face_start": network_face_start,
            },
            "audit": v2.base.audit_geometry(
                geometry["points"],
                geometry["faces"],
            ),
            "triangle_quality": quality(
                geometry["points"],
                geometry["faces"],
            ),
            "self_overlap_count": len(
                v2.ribbon_self_overlaps(
                    geometry["points"],
                    geometry["faces"],
                    len(geometry["samples"]),
                )
            ),
            "c9_overlap_count": len(
                overlap_pairs(
                    geometry["points"],
                    geometry["faces"],
                    c9_points,
                    c9_faces,
                )
            ),
            "cutter_overlap_count": len(
                overlap_pairs(
                    geometry["points"],
                    geometry["faces"],
                    cutter_points,
                    cutter_faces,
                )
            ),
            "minimum_cutter_margin_mm": round(min(margins), 6),
            "rail_overlap_count": len(
                overlap_pairs(
                    geometry["points"],
                    geometry["faces"],
                    rail_points,
                    rail_faces,
                )
            ),
            "cage_overlap_count": len(
                overlap_pairs(
                    geometry["points"],
                    geometry["faces"],
                    cage_points,
                    cage_faces,
                )
            ),
            "minimum_physical_width_mm": round(
                2.0 * min(geometry["half_widths"]),
                6,
            ),
            "maximum_physical_width_mm": round(
                2.0 * max(geometry["half_widths"]),
                6,
            ),
        }
        records.append(record)
    collection = ensure_collection(RESULT_COLLECTION)
    result_obj = create_object(
        f"{args.prefix}_AFTER",
        composite_points,
        composite_faces,
        composite_materials,
        list(v6_result.data.materials),
        collection,
    )
    network_obj = create_object(
        f"{args.prefix}_NETWORK",
        network_points,
        network_faces,
        network_materials,
        list(v6_result.data.materials),
        collection,
    )
    role_edge = {
        "band_to_island_1": ("B", "1"),
        "band_to_island_2": ("B", "2"),
        "island_0_to_island_1": ("1", "0"),
        "island_1_to_island_3": (island3_target, "3"),
    }
    graph_edges = {
        role_edge[record["role"]]
        for record in records
        if record["cage_overlap_count"] > 0
        and (
            not record["role"].startswith("band_to_")
            or record["rail_overlap_count"] > 0
        )
    }
    seen = {"B"}
    while True:
        expanded = seen | {
            second
            for first, second in graph_edges
            if first in seen
        } | {
            first
            for first, second in graph_edges
            if second in seen
        }
        if expanded == seen:
            break
        seen = expanded
    rail_fp_before = fingerprint(
        list(range(len(rail_points))),
        rail_points,
    )
    rail_fp_after = fingerprint(
        list(range(len(rail_points))),
        network_points[: len(rail_points)],
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": "evaluation_only_not_promoted",
        "input_blend": {
            "path": str(blend_path),
            "sha256": actual_sha,
        },
        "objects": {
            "result": result_obj.name,
            "network": network_obj.name,
        },
        "rail_preservation": {
            "fingerprint_before": rail_fp_before,
            "fingerprint_after": rail_fp_after,
            "exact": rail_fp_before == rail_fp_after,
        },
        "attachments": {
            "records": records,
            "optional_micro_tab_present": False,
            "graph_edges": [list(edge) for edge in sorted(graph_edges)],
            "graph_connected": seen == {"B", "0", "1", "2", "3"},
        },
        "island_1_to_3_reroute": reroute_report,
        "graph_edge_searches": edge_search_reports,
        "network": {
            "audit": v2.base.audit_geometry(
                network_points,
                network_faces,
            ),
        },
        "qualitative_review": "NOT_STARTED",
        "promotion": "NOT_PROMOTED",
    }
    report["gates"] = {
        "v6_rail_exact": report["rail_preservation"]["exact"],
        "required_graph_connected": report["attachments"]["graph_connected"],
        "optional_micro_tab_absent": True,
        "attachments_closed_positive_contiguous": all(
            record["audit"]["boundary_edges"] == 0
            and record["audit"]["nonmanifold_edges"] == 0
            and record["audit"]["noncontiguous_manifold_edges"] == 0
            and record["audit"]["signed_volume_mm3"] > 0.0
            for record in records
        ),
        "attachments_self_clear": all(
            record["self_overlap_count"] == 0 for record in records
        ),
        "attachments_c9_clear": all(
            record["c9_overlap_count"] == 0 for record in records
        ),
        "attachments_cutter_clear": all(
            record["cutter_overlap_count"] == 0 for record in records
        ),
        "attachment_margin": all(
            record["minimum_cutter_margin_mm"] >= 1.5998
            for record in records
        ),
        "attachment_triangle_quality": all(
            record["triangle_quality"]["degenerate_triangle_count"] == 0
            and record["triangle_quality"]["minimum_angle_degrees"]["minimum"]
            >= 3.0
            and record["triangle_quality"]["aspect_ratio"]["maximum"] <= 12.0
            for record in records
        ),
    }
    report["gate_pass"] = all(report["gates"].values())
    args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.report.resolve().write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: v7 flared gusset network gate_pass={report['gate_pass']}; "
        "promotion NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
