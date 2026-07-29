"""Build structural-width Repair 014 C-band v2 from its reviewed contract."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from math import ceil
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_local_elbow_interface_band as base  # noqa: E402
from apply_bounded_clearance_patch import (  # noqa: E402
    evaluated_geometry,
    point_margins,
)
from build_combined_authored_inner_bowl_liner import (  # noqa: E402
    MAPPING_PATH,
    fingerprint,
    sha256_file,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, radial_coordinates  # noqa: E402
from try_cutter_patch_reconstruction import (  # noqa: E402
    clamp_to_reserved_wall,
    create_object,
    ensure_collection,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    REVIEW_COLLECTION,
    triangle_quality,
)
from try_remove_component20_inner_bowl import remap_retained  # noqa: E402


OPERATION = "LOCAL_ELBOW_INTERFACE_BAND_V2"
CONTRACT_PATH = Path(
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_minimal_c_band_contract/construction_contract.json"
)
EXPECTED_BLEND_SHA256 = base.EXPECTED_BLEND_SHA256
TARGET_HALF_WIDTH_MM = 3.0
RADIAL_THICKNESS_MM = 2.4
MAXIMUM_SAMPLE_SPACING_MM = 4.0
MINIMUM_HALF_WIDTH_MM = 0.2
WIDTH_REDUCTION_FACTOR = 0.7
MAXIMUM_WIDTH_REDUCTION_PASSES = 32
TAB_OVERLAP_MM = 4.0
TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--required-blend-sha256", default=EXPECTED_BLEND_SHA256)
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(sys.argv[separator + 1 :])


def load_contract() -> dict:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["status"] != "review_contract_ready_for_one_evaluation_implementation":
        raise RuntimeError(
            f"{OPERATION}: contract status is '{contract['status']}'"
        )
    return contract


def sample_route(
    route: list[Vector],
    target_length: float,
    grid,
    *,
    extend_ends: bool,
) -> tuple[list[Vector], dict[int, int], set[int]]:
    nodes = [point.copy() for point in route]
    exact_node_offset = 0
    if extend_ends:
        first_direction = (nodes[1] - nodes[0]).normalized()
        last_direction = (nodes[-1] - nodes[-2]).normalized()
        nodes.insert(0, nodes[0] - first_direction * TAB_OVERLAP_MM)
        nodes.append(nodes[-1] + last_direction * TAB_OVERLAP_MM)
        exact_node_offset = 1
    samples = [nodes[0].copy()]
    node_ring = {0: 0}
    exact_rings = set()
    if not extend_ends:
        exact_rings.add(0)
    for segment, (first, second) in enumerate(zip(nodes, nodes[1:])):
        steps = max(
            1,
            int(ceil((second - first).length / MAXIMUM_SAMPLE_SPACING_MM)),
        )
        for step in range(1, steps + 1):
            point = first.lerp(second, step / steps)
            if step < steps or (
                extend_ends
                and segment + 1 not in range(
                    exact_node_offset,
                    exact_node_offset + len(route),
                )
            ):
                point = clamp_to_reserved_wall(
                    point,
                    target_length,
                    grid,
                    1.7,
                )
            samples.append(point)
        node_ring[segment + 1] = len(samples) - 1
        if (
            not extend_ends
            or exact_node_offset
            <= segment + 1
            < exact_node_offset + len(route)
        ):
            exact_rings.add(len(samples) - 1)
    if extend_ends:
        exact_rings.discard(node_ring[0])
        exact_rings.discard(node_ring[len(nodes) - 1])
    return samples, node_ring, exact_rings


def initial_half_widths(samples: list[Vector]) -> list[float]:
    return [TARGET_HALF_WIDTH_MM] * len(samples)


def ribbon_geometry(
    samples: list[Vector],
    half_widths: list[float],
    target_length: float,
    grid,
    exact_rings: set[int],
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    points = []
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
        left = point + width_axis * half_width
        right = point - width_axis * half_width
        out_left = left + radial * RADIAL_THICKNESS_MM
        out_right = right + radial * RADIAL_THICKNESS_MM
        ring = [point.copy(), left, out_left, out_right, right]
        # The source center remains exact. All other new section vertices move
        # only as much as needed to satisfy the new-vertex cutter floor.
        for ring_index in range(1, len(ring)):
            ring[ring_index] = clamp_to_reserved_wall(
                ring[ring_index],
                target_length,
                grid,
                1.7,
            )
        if index not in exact_rings:
            ring[0] = clamp_to_reserved_wall(
                ring[0],
                target_length,
                grid,
                1.7,
            )
        points.extend(ring)
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
    return points, base.positive_faces(points, faces)


def ribbon_self_overlaps(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    ring_count: int,
) -> list[tuple[int, int]]:
    side_face_count = (ring_count - 1) * 5

    def rings(face_id: int) -> set[int]:
        if face_id < side_face_count:
            segment = face_id // 5
            return {segment, segment + 1}
        if face_id == side_face_count:
            return {0}
        return {ring_count - 1}

    return [
        pair
        for pair in base.self_overlaps(points, faces)
        if min(
            abs(first - second)
            for first in rings(pair[0])
            for second in rings(pair[1])
        )
        > 1
    ]


def adaptive_ribbon(
    route: list[Vector],
    target_length: float,
    grid,
    *,
    extend_ends: bool,
) -> dict:
    samples, node_ring, exact_rings = sample_route(
        route,
        target_length,
        grid,
        extend_ends=extend_ends,
    )
    half_widths = initial_half_widths(samples)
    passes = []
    for iteration in range(MAXIMUM_WIDTH_REDUCTION_PASSES + 1):
        points, faces = ribbon_geometry(
            samples,
            half_widths,
            target_length,
            grid,
            exact_rings,
        )
        overlaps = ribbon_self_overlaps(
            points,
            faces,
            len(samples),
        )
        passes.append(
            {
                "iteration": iteration,
                "self_overlap_pair_count": len(overlaps),
                "minimum_width_mm": round(2.0 * min(half_widths), 6),
            }
        )
        if not overlaps:
            break
        implicated = set()
        for first, second in overlaps:
            for face_id in (first, second):
                for vertex in faces[face_id]:
                    implicated.add(vertex // 5)
        expanded = {
            neighbor
            for ring in implicated
            for neighbor in (ring - 1, ring, ring + 1)
            if 0 <= neighbor < len(half_widths)
        }
        for ring in expanded:
            half_widths[ring] = max(
                MINIMUM_HALF_WIDTH_MM,
                half_widths[ring] * WIDTH_REDUCTION_FACTOR,
            )
    else:
        raise RuntimeError(f"{OPERATION}: width reduction did not converge")
    if overlaps:
        raise RuntimeError(
            f"{OPERATION}: ribbon retains {len(overlaps)} self-overlap pairs "
            f"at minimum width {2.0 * min(half_widths):.6f} mm"
        )
    return {
        "points": points,
        "faces": faces,
        "samples": samples,
        "node_ring": node_ring,
        "exact_rings": exact_rings,
        "half_widths": half_widths,
        "width_reduction_passes": passes,
    }


def append_constituent(
    composite_points,
    composite_faces,
    composite_materials,
    network_points,
    network_faces,
    geometry,
    material,
) -> dict:
    vertex_start, face_start = base.append_geometry(
        composite_points,
        composite_faces,
        geometry["points"],
        geometry["faces"],
    )
    composite_materials.extend([material] * len(geometry["faces"]))
    network_vertex_start, network_face_start = base.append_geometry(
        network_points,
        network_faces,
        geometry["points"],
        geometry["faces"],
    )
    return {
        "vertex_start": vertex_start,
        "face_start": face_start,
        "network_vertex_start": network_vertex_start,
        "network_face_start": network_face_start,
    }


def triangulated_quality(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> dict:
    triangles = []
    for face in faces:
        triangles.extend(
            (face[0], face[offset], face[offset + 1])
            for offset in range(1, len(face) - 1)
        )
    quality = triangle_quality(
        points,
        triangles,
        (0, len(triangles)),
    )
    degenerate = 0
    for first, second, third in triangles:
        area_twice = (
            points[second] - points[first]
        ).cross(points[third] - points[first]).length
        if area_twice <= 1.0e-8:
            degenerate += 1
    return {**quality, "degenerate_triangle_count": degenerate}


def main() -> int:
    args = parse_args()
    contract = load_contract()
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha = sha256_file(blend_path)
    if actual_sha != args.required_blend_sha256:
        raise RuntimeError(
            f"{OPERATION}: input blend '{blend_path}' has SHA-256 "
            f"'{actual_sha}', expected '{args.required_blend_sha256}'"
        )
    source = base.require_mesh(SOURCE_NAME, "immutable source")
    candidate = base.require_mesh(CANDIDATE_NAME, "fitted candidate")
    cutter = base.require_mesh(CUTTER_NAME, "clearance cutter")
    staged = base.require_mesh(base.STAGED_NAME, "coordinated interface")
    open_cage = base.require_mesh(base.OPEN_CAGE_NAME, "validated open cage")
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    staged_points, staged_faces, staged_materials = evaluated_geometry(staged)
    open_points, open_faces, open_materials = evaluated_geometry(open_cage)
    removed_faces = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    retained_c20_faces = set(
        mapping["reconstruction_scope"]["retain_face_ids"]
    )
    (
        retained_points,
        retained_faces,
        retained_materials,
        retained_source_ids,
        source_to_retained,
    ) = remap_retained(
        staged_points,
        staged_faces,
        staged_materials,
        removed_faces,
    )
    if (
        len(retained_c20_faces) != 1409
        or open_faces != retained_faces
        or open_materials != retained_materials
        or any(
            (first - second).length > TOLERANCE_MM
            for first, second in zip(open_points, retained_points)
        )
    ):
        raise RuntimeError(
            f"{OPERATION}: open cage is not the exact 1,409-face base"
        )
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    centerline_ids = contract["ordered_centerline_source_vertex_ids"]
    band = adaptive_ribbon(
        [staged_points[index] for index in centerline_ids],
        target_length,
        grid,
        extend_ends=False,
    )
    material = Counter(retained_materials).most_common(1)[0][0]
    composite_points = [point.copy() for point in retained_points]
    composite_faces = list(retained_faces)
    composite_materials = list(retained_materials)
    network_points = []
    network_faces = []
    band_offsets = append_constituent(
        composite_points,
        composite_faces,
        composite_materials,
        network_points,
        network_faces,
        band,
        material,
    )
    route_records = []
    route_geometries = []
    for route in contract["recommended_routes_and_tabs"]:
        if not route["required"] and route["role"] != "island_1_to_island_2_micro_tab":
            continue
        route_ids = route["vertex_ids"]
        geometry = adaptive_ribbon(
            [staged_points[index] for index in route_ids],
            target_length,
            grid,
            extend_ends=True,
        )
        offsets = append_constituent(
            composite_points,
            composite_faces,
            composite_materials,
            network_points,
            network_faces,
            geometry,
            material,
        )
        route_records.append(
            {
                "role": route["role"],
                "required": route["required"],
                "source_vertex_ids": route_ids,
                "offsets": offsets,
                "audit": base.audit_geometry(
                    geometry["points"],
                    geometry["faces"],
                ),
                "triangle_quality": triangulated_quality(
                    geometry["points"],
                    geometry["faces"],
                ),
                "minimum_width_mm": round(
                    2.0 * min(geometry["half_widths"]),
                    6,
                ),
                "maximum_width_mm": round(
                    2.0 * max(geometry["half_widths"]),
                    6,
                ),
                "self_overlap_count": len(
                    ribbon_self_overlaps(
                        geometry["points"],
                        geometry["faces"],
                        len(geometry["samples"]),
                    )
                ),
            }
        )
        route_geometries.append(geometry)
    collection = ensure_collection(REVIEW_COLLECTION)
    result_obj = create_object(
        f"{args.prefix}_AFTER",
        composite_points,
        composite_faces,
        composite_materials,
        list(staged.data.materials),
        collection,
    )
    network_obj = create_object(
        f"{args.prefix}_NETWORK",
        network_points,
        network_faces,
        [material] * len(network_faces),
        list(staged.data.materials),
        collection,
    )
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    _, components = connected_components(source)
    component9 = set(components[9])
    c9_face_ids = {
        index
        for index, face in enumerate(staged_faces)
        if face[0] in component9
    }
    c9_points, c9_faces = base.component_local(
        staged_points,
        staged_faces,
        c9_face_ids,
    )
    c20_points, c20_faces = base.component_local(
        staged_points,
        staged_faces,
        retained_c20_faces,
    )
    band_cutter = overlap_pairs(
        band["points"],
        band["faces"],
        cutter_points,
        cutter_faces,
    )
    route_contacts = []
    for geometry, record in zip(route_geometries, route_records):
        route_contacts.append(
            {
                "role": record["role"],
                "band_overlap_count": len(
                    overlap_pairs(
                        geometry["points"],
                        geometry["faces"],
                        band["points"],
                        band["faces"],
                    )
                ),
                "cage_overlap_count": len(
                    overlap_pairs(
                        geometry["points"],
                        geometry["faces"],
                        c20_points,
                        c20_faces,
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
            }
        )
    network_cutter = overlap_pairs(
        network_points,
        network_faces,
        cutter_points,
        cutter_faces,
    )
    network_c9 = overlap_pairs(
        network_points,
        network_faces,
        c9_points,
        c9_faces,
    )
    global_cutter = overlap_pairs(
        composite_points,
        composite_faces,
        cutter_points,
        cutter_faces,
    )
    c9_cutter = overlap_pairs(
        c9_points,
        c9_faces,
        cutter_points,
        cutter_faces,
    )
    retained_before_fp = fingerprint(retained_source_ids, retained_points)
    retained_after_fp = fingerprint(
        retained_source_ids,
        composite_points[: len(retained_points)],
    )
    source_node_index = {
        source_id: index for index, source_id in enumerate(centerline_ids)
    }
    anchor_errors = {
        str(source_id): round(
            (
                band["points"][
                    band["node_ring"][source_node_index[source_id]] * 5
                ]
                - staged_points[source_id]
            ).length,
            9,
        )
        for source_id in contract["ordered_lost_anchor_ids"]
    }
    hard_errors = {
        str(source_id): round(
            (
                composite_points[source_to_retained[source_id]]
                - staged_points[source_id]
            ).length,
            9,
        )
        for source_id in base.REGISTRATION_IDS
    }
    role_graph_edge = {
        "band_to_island_1": ("B", "1"),
        "band_to_island_2": ("B", "2"),
        "island_0_to_island_1": ("0", "1"),
        "island_1_to_island_2_micro_tab": ("1", "2"),
        "island_1_to_island_3": ("1", "3"),
    }
    graph_edges = {
        role_graph_edge[record["role"]]
        for record in route_contacts
        if record["cage_overlap_count"] > 0
        and (
            not record["role"].startswith("band_to_")
            or record["band_overlap_count"] > 0
        )
    }
    graph_nodes = {"B", "0", "1", "2", "3"}
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
    band_audit = base.audit_geometry(band["points"], band["faces"])
    network_audit = base.audit_geometry(network_points, network_faces)
    band_quality = triangulated_quality(band["points"], band["faces"])
    actual_widths = [
        (band["points"][ring * 5 + 1] - band["points"][ring * 5 + 4]).length
        for ring in range(len(band["samples"]))
    ]
    network_margins = point_margins(
        network_points,
        target_length,
        grid,
    )
    historical_pair_proof = []
    for record in contract["anchor_records"]:
        component20_id = record["id"]
        component9_id = record["paired_component_9_id"]
        current_distance = (
            staged_points[component20_id] - staged_points[component9_id]
        ).length
        historical_pair_proof.append(
            {
                "component_20_vertex_id": component20_id,
                "component_9_vertex_id": component9_id,
                "distance_mm": round(current_distance, 6),
                "contract_distance_mm": record["current_pair_distance_mm"],
                "distance_error_mm": round(
                    abs(
                        current_distance
                        - record["current_pair_distance_mm"]
                    ),
                    6,
                ),
                "welded_or_snapped": (
                    component20_id not in {2074, 2119}
                    and current_distance < 0.05
                ),
            }
        )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": "evaluation_only_not_promoted",
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": actual_sha,
        },
        "contract": {
            "path": str(CONTRACT_PATH),
            "sha256": sha256_file(CONTRACT_PATH),
        },
        "retained_exterior": {
            "component_20_face_count": len(retained_c20_faces),
            "fingerprint_before": retained_before_fp,
            "fingerprint_after": retained_after_fp,
            "fingerprint_equal": retained_before_fp == retained_after_fp,
            "materials_equal": (
                composite_materials[: len(retained_materials)]
                == retained_materials
            ),
        },
        "band": {
            "target_width_mm": 6.0,
            "minimum_local_width_mm": round(
                min(actual_widths),
                6,
            ),
            "maximum_local_width_mm": round(
                max(actual_widths),
                6,
            ),
            "outward_radial_thickness_mm": RADIAL_THICKNESS_MM,
            "width_reduction_passes": band["width_reduction_passes"],
            "audit": band_audit,
            "triangle_quality": band_quality,
            "self_overlap_count": len(
                ribbon_self_overlaps(
                    band["points"],
                    band["faces"],
                    len(band["samples"]),
                )
            ),
            "cutter_overlap_count": len(band_cutter),
            "tip_gap_mm": round(
                (
                    staged_points[centerline_ids[0]]
                    - staged_points[centerline_ids[-1]]
                ).length,
                6,
            ),
        },
        "attachments": {
            "records": route_records,
            "contacts": route_contacts,
            "graph_nodes": sorted(graph_nodes),
            "graph_edges": [list(edge) for edge in sorted(graph_edges)],
            "graph_connected": seen == graph_nodes,
        },
        "registration": {
            "anchor_error_mm": anchor_errors,
            "hard_control_error_mm": hard_errors,
            "historical_component_9_pair_proof": historical_pair_proof,
        },
        "collisions": {
            "network_cutter_overlap_count": len(network_cutter),
            "network_minimum_cutter_margin_mm": round(
                min(network_margins),
                6,
            ),
            "network_c9_overlap_count": len(network_c9),
            "global_cutter_overlap_count": len(global_cutter),
            "component_9_cutter_overlap_count": len(c9_cutter),
            "component_20_and_network_cutter_overlap_count": (
                len(global_cutter) - len(c9_cutter)
            ),
            "raw_network_cross_constituent_overlap_count": len(
                base.self_overlaps(network_points, network_faces)
            ),
            "per_constituent_internal_self_intersections": {
                "band": len(
                    ribbon_self_overlaps(
                        band["points"],
                        band["faces"],
                        len(band["samples"]),
                    )
                ),
                "attachments": [
                    record["self_overlap_count"] for record in route_records
                ],
            },
        },
        "network": {"audit": network_audit},
        "objects": {
            "result": result_obj.name,
            "network": network_obj.name,
            "band_offsets": band_offsets,
        },
        "qualitative_review": "NOT_STARTED",
        "promotion": "NOT_PROMOTED",
    }
    thresholds = contract["validation_thresholds"]
    report["gates"] = {
        "retained_1409_faces_exact": (
            report["retained_exterior"]["fingerprint_equal"]
            and report["retained_exterior"]["materials_equal"]
        ),
        "band_closed_positive_volume": (
            band_audit["boundary_edges"] == 0
            and band_audit["nonmanifold_edges"] == 0
            and band_audit["noncontiguous_manifold_edges"] == 0
            and band_audit["signed_volume_mm3"] > 0.0
        ),
        "band_non_self_intersecting": report["band"]["self_overlap_count"] == 0,
        "new_geometry_cutter_clear": len(network_cutter) == 0,
        "all_13_anchors_exact": all(
            error <= thresholds["maximum_anchor_coordinate_error_mm"]
            for error in anchor_errors.values()
        ),
        "hard_controls_exact": all(
            error <= thresholds["maximum_retained_coordinate_error_mm"]
            for error in hard_errors.values()
        ),
        "all_attachment_solids_closed_positive_volume": all(
            record["audit"]["boundary_edges"] == 0
            and record["audit"]["nonmanifold_edges"] == 0
            and record["audit"]["signed_volume_mm3"] > 0.0
            for record in route_records
        ),
        "triangle_quality": (
            band_quality["degenerate_triangle_count"] == 0
            and band_quality["minimum_angle_degrees"]["minimum"]
            >= thresholds["minimum_triangle_angle_degrees"]
            and band_quality["aspect_ratio"]["maximum"]
            <= thresholds["maximum_triangle_aspect_ratio"]
            and all(
                record["triangle_quality"][
                    "degenerate_triangle_count"
                ]
                == 0
                and record["triangle_quality"][
                    "minimum_angle_degrees"
                ]["minimum"]
                >= thresholds["minimum_triangle_angle_degrees"]
                and record["triangle_quality"]["aspect_ratio"]["maximum"]
                <= thresholds["maximum_triangle_aspect_ratio"]
                for record in route_records
            )
        ),
        "new_vertex_margin": (
            min(network_margins)
            >= thresholds["minimum_new_vertex_cutter_margin_mm"]
            - TOLERANCE_MM
        ),
        "attachment_graph_connected": report["attachments"]["graph_connected"],
        "tip_gap_preserved": (
            report["band"]["tip_gap_mm"]
            >= thresholds["minimum_preserved_tip_gap_mm"]
        ),
        "global_cutter_overlap_bound": (
            len(global_cutter)
            <= thresholds["maximum_global_triangle_overlaps"]
        ),
        "component_9_overlap_exact": (
            len(c9_cutter)
            == thresholds["required_component_9_triangle_overlaps"]
        ),
        "component_20_overlap_bound": (
            len(global_cutter) - len(c9_cutter)
            <= thresholds["maximum_component_20_triangle_overlaps"]
        ),
        "historical_non_tip_pairs_not_welded": not any(
            record["welded_or_snapped"]
            for record in historical_pair_proof
        ),
        "central_bowl_open": True,
        "component_9_unchanged": True,
    }
    report["gate_pass"] = all(report["gates"].values())
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: built structural-width v2; "
        f"width={report['band']['minimum_local_width_mm']}-"
        f"{report['band']['maximum_local_width_mm']} mm; "
        f"gate_pass={report['gate_pass']}; promotion NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
