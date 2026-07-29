"""Attribute and, only after every gate, evaluate the joint C9/C20 v22 elbow."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_full_authored_frame_v21 as v21  # noqa: E402
import build_static_fit_prototype as static  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
from apply_bounded_clearance_patch import point_margins  # noqa: E402
from rescue_clearance_fragments import mesh_neighbors  # noqa: E402
from sweep_local_clearance_reconstruction import violation_clusters  # noqa: E402


OPERATION = "JOINT_C9_C20_ELBOW_V22"
SAFE_STOP = "NO_SAFE_JOINT_C9_C20_ELBOW_V22"
V21_SCRIPT_SHA256 = (
    "517234879f4e5ee4ba8edf51653a0ac8fdf8e443d71b5f4659a1eb485d766480"
)
V21_REPORT_SHA256 = (
    "02aaac5b47821e4d33b194d9ebd9bdc015c047024a272073041cea09062335ee"
)
V21_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_full_authored_frame_v21/build_report.json"
)
V13_REPORT_PATH = (
    SCRIPT_DIR.parent.parent
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_distinct_cage_terminals_v13/build_report.json"
)
GAPS_MM = (0.4, 0.6, 0.8)
LOWER_LANDING_FACES = {2741, 4711}


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def face_normal(points, face):
    origin = points[face[0]]
    normal = Vector()
    for index in range(1, len(face) - 1):
        normal += (points[face[index]] - origin).cross(
            points[face[index + 1]] - origin
        )
    return normal.normalized() if normal.length > 1.0e-12 else normal


def connected_face_islands(face_ids, faces):
    edge_faces = defaultdict(set)
    for face_id in face_ids:
        face = faces[face_id]
        for first, second in zip(face, (*face[1:], face[0])):
            edge_faces[tuple(sorted((first, second)))].add(face_id)
    adjacency = {face_id: set() for face_id in face_ids}
    for linked in edge_faces.values():
        for face_id in linked:
            adjacency[face_id].update(linked - {face_id})
    unseen = set(face_ids)
    islands = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        stack = [start]
        island = {start}
        while stack:
            current = stack.pop()
            following = adjacency[current] & unseen
            unseen -= following
            island |= following
            stack.extend(following)
        islands.append(sorted(island))
    return islands


def c9_source_context(context, target_length, grid):
    source = bpy.data.objects[static.SOURCE_NAME]
    candidate_points, candidate_faces, _ = v14.evaluated_geometry(
        bpy.data.objects[v4.CANDIDATE_NAME]
    )
    vertex_component, components = static.connected_components(source)
    component_vertices = set(components[9])
    component_face_ids = sorted(
        face_id
        for face_id, face in enumerate(context["staged_faces"])
        if face[0] in component_vertices
    )
    component_vertex_ids = sorted(component_vertices)
    local_vertex_to_source = component_vertex_ids
    local_face_to_source = component_face_ids
    margins = point_margins(candidate_points, target_length, grid)
    penetrating_cluster_margins = [
        margin + static.RESERVED_WALL_MM for margin in margins
    ]
    clusters = violation_clusters(
        component_vertices,
        penetrating_cluster_margins,
        mesh_neighbors(source.data),
    )
    candidates = []
    for cluster_index, cluster in enumerate(clusters):
        incident = sorted(
            face_id
            for face_id in component_face_ids
            if any(vertex in set(cluster) for vertex in candidate_faces[face_id])
        )
        stations = [
            v4.radial_coordinates(
                candidate_points[vertex],
                target_length,
            )[0]
            * target_length
            for vertex in cluster
        ]
        candidates.append(
            {
                "cluster_index": cluster_index,
                "vertex_ids": cluster,
                "vertex_count": len(cluster),
                "incident_face_ids": incident,
                "incident_face_count": len(incident),
                "station_bounds_mm": [
                    round(min(stations), 6),
                    round(max(stations), 6),
                ],
                "minimum_cutter_margin_mm": round(
                    min(margins[vertex] for vertex in cluster),
                    6,
                ),
            }
        )
    matching = [
        candidate
        for candidate in candidates
        if candidate["vertex_count"] == 86
        and candidate["incident_face_count"] == 238
    ]
    if len(matching) != 1:
        raise RuntimeError(
            f"{OPERATION}: proximal C9 86-vertex/238-face cluster "
            f"resolved {len(matching)} times; clusters={candidates}"
        )
    proximal = matching[0]
    return {
        "component_vertex_ids": component_vertex_ids,
        "component_face_ids": component_face_ids,
        "local_vertex_to_source": local_vertex_to_source,
        "local_face_to_source": local_face_to_source,
        "proximal": proximal,
        "clusters": candidates,
        "vertex_component": vertex_component,
    }


def open_face_mapping(context):
    removed = set(
        context["mapping"]["reconstruction_scope"]["rebuild_face_ids"]
    )
    open_to_source = [
        face_id
        for face_id in range(len(context["staged_faces"]))
        if face_id not in removed
    ]
    return open_to_source


def face_catalog(face_ids, points, faces, materials, target_length):
    catalog = {}
    for face_id in sorted(face_ids):
        face = faces[face_id]
        centroid = sum(
            (points[vertex] for vertex in face),
            Vector(),
        ) / len(face)
        normal = face_normal(points, face)
        station, _, _, radial = v4.radial_coordinates(
            centroid,
            target_length,
        )
        dot = normal.dot(radial)
        catalog[str(face_id)] = {
            "source_face_id": face_id,
            "loop_source_vertex_ids": list(face),
            "coordinates_mm": [
                [float(value) for value in points[vertex]]
                for vertex in face
            ],
            "material_index": materials[face_id],
            "station_mm": round(station * target_length, 6),
            "normal_radial_dot": round(dot, 8),
            "orientation": (
                "exterior_facing" if dot >= 0.0 else "wearer_facing"
            ),
        }
    return catalog


def immutable_complement(
    component_face_ids,
    excluded,
    points,
    faces,
    materials,
):
    face_ids = sorted(set(component_face_ids) - set(excluded))
    vertex_ids = sorted(
        {
            vertex
            for face_id in face_ids
            for vertex in faces[face_id]
        }
    )
    payload = {
        "face_ids": face_ids,
        "faces": [list(faces[face_id]) for face_id in face_ids],
        "materials": [materials[face_id] for face_id in face_ids],
        "vertex_ids": vertex_ids,
        "coordinates_mm": [
            [float(value) for value in points[vertex]]
            for vertex in vertex_ids
        ],
    }
    return {
        "face_count": len(face_ids),
        "vertex_count": len(vertex_ids),
        "fingerprint": stable_hash(payload),
    }


def rebuild_v21_variants(context):
    corridor = v21.reconstruct_v12_core(context)
    open_face_by_source = v21.source_to_open_faces(context)
    upper_allowed = {
        open_face_by_source[source_face_id]
        for source_face_id in v21.UPPER_ALLOWLIST
    }
    lower_allowed = {
        open_face_by_source[source_face_id]
        for source_face_id in v21.LOWER_ALLOWLIST
    }
    b0_samples = corridor["core"]["B0"]["_samples"]
    b2b_samples = corridor["core"]["B2b"]["_samples"]
    upper_first = context["staged_points"][v21.UPPER_ID]
    upper_second = b0_samples[0]
    upper_tangent = v21.UPPER_TANGENT.normalized()
    if upper_tangent.dot(upper_second - upper_first) < 0.0:
        upper_tangent.negate()
    upper_band_tangent = (b0_samples[1] - b0_samples[0]).normalized()
    _, _, _, upper_band_normal = v4.radial_coordinates(
        upper_second,
        corridor["target_length"],
    )
    lower_first = b2b_samples[-1]
    lower_second = context["staged_points"][v21.LOWER_ID]
    lower_band_tangent = (b2b_samples[-1] - b2b_samples[-2]).normalized()
    lower_tangent = v21.LOWER_TANGENT.normalized()
    if lower_tangent.dot(lower_second - lower_first) < 0.0:
        lower_tangent.negate()
    _, _, _, lower_band_normal = v4.radial_coordinates(
        lower_first,
        corridor["target_length"],
    )
    upper_records, _ = v21.search_approach(
        "UPPER_APPROACH_V21",
        upper_first,
        upper_second,
        upper_tangent,
        upper_band_tangent,
        v21.UPPER_NORMAL,
        upper_band_normal,
        upper_allowed,
        context,
        corridor,
    )
    lower_records, _ = v21.search_approach(
        "LOWER_APPROACH_V21",
        lower_first,
        lower_second,
        lower_band_tangent,
        lower_tangent,
        lower_band_normal,
        v21.LOWER_NORMAL,
        lower_allowed,
        context,
        corridor,
    )
    return corridor, upper_records, lower_records


def attribute_variant(
    label,
    record,
    context,
    c9,
    open_to_source,
    allowed_source_faces,
    target_length,
):
    c9_pairs = v14.overlap_pairs(
        record["_points"],
        record["_faces"],
        context["c9_points"],
        context["c9_faces"],
    )
    open_pairs = v14.overlap_pairs(
        record["_points"],
        record["_faces"],
        context["open_points"],
        context["open_faces"],
    )
    c9_faces = sorted(
        {
            c9["local_face_to_source"][pair[1]]
            for pair in c9_pairs
        }
    )
    c20_faces = sorted(
        {
            open_to_source[pair[1]]
            for pair in open_pairs
            if open_to_source[pair[1]] not in allowed_source_faces
        }
    )
    c9_vertices = sorted(
        {
            vertex
            for face_id in c9_faces
            for vertex in context["staged_faces"][face_id]
        }
    )
    c20_vertices = sorted(
        {
            vertex
            for face_id in c20_faces
            for vertex in context["staged_faces"][face_id]
        }
    )
    proximal = set(c9["proximal"]["incident_face_ids"])
    c9_membership = {
        str(face_id): face_id in proximal for face_id in c9_faces
    }
    c9_catalog = face_catalog(
        c9_faces,
        context["staged_points"],
        context["staged_faces"],
        context["staged_materials"],
        target_length,
    )
    c20_catalog = face_catalog(
        c20_faces,
        context["staged_points"],
        context["staged_faces"],
        context["staged_materials"],
        target_length,
    )
    c20_wearer_or_landing = all(
        catalog["orientation"] == "wearer_facing"
        or face_id in LOWER_LANDING_FACES
        for face_id, catalog in (
            (int(face_id), value)
            for face_id, value in c20_catalog.items()
        )
    )
    return {
        "variant_id": label,
        "handle_length_mm": record["handle_length_mm"],
        "midpoint_displacement_mm": record[
            "midpoint_displacement_mm"
        ],
        "curve_length_mm": record["curve_length_mm"],
        "cutter_overlap_count": record["cutter_overlap_count"],
        "self_overlap_count": record["self_overlap_count"],
        "minimum_cutter_margin_mm": record[
            "minimum_cutter_margin_mm"
        ],
        "triangle_quality": record["triangle_quality"],
        "C9_FACES": c9_faces,
        "C9_VERTICES": c9_vertices,
        "C9_overlap_pairs": [list(pair) for pair in c9_pairs],
        "C9_connected_face_islands": connected_face_islands(
            c9_faces,
            context["staged_faces"],
        ),
        "C9_face_records": c9_catalog,
        "C9_station_bounds_mm": (
            [
                min(
                    value["station_mm"]
                    for value in c9_catalog.values()
                ),
                max(
                    value["station_mm"]
                    for value in c9_catalog.values()
                ),
            ]
            if c9_catalog
            else None
        ),
        "C9_all_proximal_wearer_facing": all(c9_membership.values()),
        "C9_proximal_membership_by_face": c9_membership,
        "C20_FACES": c20_faces,
        "C20_VERTICES": c20_vertices,
        "C20_overlap_pairs": [
            [pair[0], open_to_source[pair[1]]]
            for pair in open_pairs
            if open_to_source[pair[1]] not in allowed_source_faces
        ],
        "C20_connected_face_islands": connected_face_islands(
            c20_faces,
            context["staged_faces"],
        ),
        "C20_face_records": c20_catalog,
        "C20_station_bounds_mm": (
            [
                min(
                    value["station_mm"]
                    for value in c20_catalog.values()
                ),
                max(
                    value["station_mm"]
                    for value in c20_catalog.values()
                ),
            ]
            if c20_catalog
            else None
        ),
        "C20_all_wearer_facing_or_landing": c20_wearer_or_landing,
        "gate_without_channel": all(
            (
                record["cutter_overlap_count"] == 0,
                record["self_overlap_count"] == 0,
                record["minimum_cutter_margin_mm"] >= 1.7,
                record["triangle_quality"]["minimum_angle_degrees"][
                    "minimum"
                ]
                >= 3.0,
                record["triangle_quality"]["aspect_ratio"]["maximum"]
                <= 12.0,
                all(c9_membership.values()),
                c20_wearer_or_landing,
            )
        ),
        "_record": record,
    }


def aggregate_attribution(
    name,
    records,
    context,
    c9,
    open_to_source,
    allowed_source_faces,
    target_length,
):
    variants = [
        attribute_variant(
            f"{name}_{index:02d}",
            record,
            context,
            c9,
            open_to_source,
            allowed_source_faces,
            target_length,
        )
        for index, record in enumerate(records)
    ]
    c9_sets = [set(record["C9_FACES"]) for record in variants]
    c20_sets = [set(record["C20_FACES"]) for record in variants]
    c9_shared = sorted(set.intersection(*c9_sets)) if c9_sets else []
    c20_shared = sorted(set.intersection(*c20_sets)) if c20_sets else []
    c9_union = sorted(set.union(*c9_sets)) if c9_sets else []
    c20_union = sorted(set.union(*c20_sets)) if c20_sets else []
    c9_shared_vertices = sorted(
        {
            vertex
            for face_id in c9_shared
            for vertex in context["staged_faces"][face_id]
        }
    )
    c20_shared_vertices = sorted(
        {
            vertex
            for face_id in c20_shared
            for vertex in context["staged_faces"][face_id]
        }
    )
    return {
        "variants": [public(record) for record in variants],
        "C9_SHARED_FACES": c9_shared,
        "C9_SHARED_VERTICES": c9_shared_vertices,
        "C9_UNION_FACES": c9_union,
        "C20_SHARED_FACES": c20_shared,
        "C20_SHARED_VERTICES": c20_shared_vertices,
        "C20_UNION_FACES": c20_union,
        "C9_connected_face_islands": connected_face_islands(
            c9_union,
            context["staged_faces"],
        ),
        "C20_connected_face_islands": connected_face_islands(
            c20_union,
            context["staged_faces"],
        ),
        "C9_face_catalog": face_catalog(
            c9_union,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
            target_length,
        ),
        "C20_face_catalog": face_catalog(
            c20_union,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
            target_length,
        ),
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    context = v17.baseline_context()
    actual_v21_script = sha_file(v21.__file__)
    actual_v21_report = sha_file(V21_REPORT_PATH)
    if (actual_v21_script, actual_v21_report) != (
        V21_SCRIPT_SHA256,
        V21_REPORT_SHA256,
    ):
        raise RuntimeError(
            f"{OPERATION}: v21 authority mismatch: script "
            f"{actual_v21_script}, report {actual_v21_report}"
        )
    corridor, upper_records, lower_records = rebuild_v21_variants(context)
    target_length = corridor["target_length"]
    grid = corridor["grid"]
    c9 = c9_source_context(context, target_length, grid)
    open_to_source = open_face_mapping(context)
    upper = aggregate_attribution(
        "U",
        upper_records,
        context,
        c9,
        open_to_source,
        set(v21.UPPER_ALLOWLIST),
        target_length,
    )
    lower = aggregate_attribution(
        "L",
        lower_records,
        context,
        c9,
        open_to_source,
        set(v21.LOWER_ALLOWLIST),
        target_length,
    )
    c9_union = sorted(
        set(upper["C9_UNION_FACES"]) | set(lower["C9_UNION_FACES"])
    )
    c20_union = sorted(
        set(upper["C20_UNION_FACES"])
        | set(lower["C20_UNION_FACES"])
    )
    c20_component_faces = sorted(context["retained_face_ids"])
    attribution = {
        "operation": OPERATION,
        "status": "READ_ONLY_EXACT_ATTRIBUTION_COMPLETE",
        "authorities": {
            "input_blend_sha256": context["blend_sha"],
            "v21_script_sha256": actual_v21_script,
            "v21_report_sha256": actual_v21_report,
            "retained_cage_fingerprint": context["checks"][
                "retained_fingerprint"
            ],
            "component_9_fingerprint": context["checks"][
                "component_9_fingerprint"
            ],
        },
        "component_9_classification": {
            "component_vertex_count": len(c9["component_vertex_ids"]),
            "component_face_count": len(c9["component_face_ids"]),
            "proximal_wearer_facing": c9["proximal"],
            "all_collision_clusters": c9["clusters"],
        },
        "upper": upper,
        "lower": lower,
        "immutable_complements": {
            "C9_outside_attribution_union": immutable_complement(
                c9["component_face_ids"],
                c9_union,
                context["staged_points"],
                context["staged_faces"],
                context["staged_materials"],
            ),
            "C20_outside_attribution_union": immutable_complement(
                c20_component_faces,
                c20_union,
                context["staged_points"],
                context["staged_faces"],
                context["staged_materials"],
            ),
            "v12_corridor_fingerprint": stable_hash(
                corridor["public"]
            ),
            "branch_a_fingerprint": stable_hash(
                {
                    "source_vertex_ids": [5702, 1784],
                    "coordinates_mm": [
                        [
                            float(value)
                            for value in context["staged_points"][source_id]
                        ]
                        for source_id in (5702, 1784)
                    ],
                }
            ),
        },
        "named_controls": {
            "C20_B2B_EXIT_mm": [
                float(value)
                for value in corridor["core"]["B2b"]["_samples"][-1]
            ],
            "C20_T0_LANDING": {
                "source_vertex_id": 1894,
                "coordinate_mm": [
                    float(value)
                    for value in context["staged_points"][1894]
                ],
                "tangent": [float(value) for value in v21.LOWER_TANGENT],
                "normal": [float(value) for value in v21.LOWER_NORMAL],
            },
            "C9_C20_TIP_PAIR": {
                "C20_source_vertex_id": 2119,
                "C9_source_vertex_id": 1295,
                "relative_vector_mm": [
                    float(value)
                    for value in (
                        context["staged_points"][1295]
                        - context["staged_points"][2119]
                    )
                ],
                "magnitude_mm": round(
                    (
                        context["staged_points"][1295]
                        - context["staged_points"][2119]
                    ).length,
                    6,
                ),
            },
            "branch_a_source_vertex_ids": [5702, 1784],
            "hard_control_error_mm": context["checks"][
                "hard_control_error_mm"
            ],
            "tip_gap_mm": context["checks"]["tip_gap_mm"],
        },
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    attribution_path = report_path.with_name(
        "exact_overlap_attribution.json"
    )
    attribution_path.write_text(
        json.dumps(attribution, indent=2) + "\n",
        encoding="utf-8",
    )
    lower_private = [
        attribute_variant(
            f"L_{index:02d}",
            record,
            context,
            c9,
            open_to_source,
            set(v21.LOWER_ALLOWLIST),
            target_length,
        )
        for index, record in enumerate(lower_records)
    ]
    eligible = [
        record for record in lower_private if record["gate_without_channel"]
    ]
    selected = (
        min(
            eligible,
            key=lambda record: (
                len(record["C9_FACES"]),
                len(record["C20_FACES"]),
                record["curve_length_mm"],
                -record["minimum_cutter_margin_mm"],
                record["handle_length_mm"],
                abs(record["midpoint_displacement_mm"]),
            ),
        )
        if eligible
        else None
    )
    blockers = []
    if selected is None:
        classification_counts = {
            "lower_variants": len(lower_private),
            "eligible_variants": 0,
            "cutter_clear": sum(
                record["cutter_overlap_count"] == 0
                for record in lower_private
            ),
            "self_clear": sum(
                record["self_overlap_count"] == 0
                for record in lower_private
            ),
            "margin_at_least_1.7": sum(
                record["minimum_cutter_margin_mm"] >= 1.7
                for record in lower_private
            ),
            "quality_pass": sum(
                record["triangle_quality"]["minimum_angle_degrees"][
                    "minimum"
                ]
                >= 3.0
                and record["triangle_quality"]["aspect_ratio"]["maximum"]
                <= 12.0
                for record in lower_private
            ),
            "all_c9_faces_proximal_wearer": sum(
                record["C9_all_proximal_wearer_facing"]
                for record in lower_private
            ),
            "all_c20_faces_wearer_or_landing": sum(
                record["C20_all_wearer_facing_or_landing"]
                for record in lower_private
            ),
        }
        blockers.append(
            {
                "operation": "lower_variant_classification",
                "target": "15 exact B2b->V1894 variants",
                "reason": (
                    "no lower variant passes the fixed "
                    "cutter/self/quality/C9/C20 classification gates"
                ),
                "measurements": classification_counts,
            }
        )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": SAFE_STOP,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "exact_overlap_attribution": str(attribution_path),
        "exact_overlap_attribution_sha256": sha_file(attribution_path),
        "selected_lower_variant": public(selected) if selected else None,
        "resolved_allowlists": None,
        "gap_preflight": {
            "gaps_mm": list(GAPS_MM),
            "records": [],
            "status": "NOT_RUN_NO_ELIGIBLE_LOWER_VARIANT",
        },
        "blockers": blockers,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "gate_pass": False,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": SAFE_STOP,
                "upper_variant_count": len(upper_records),
                "lower_variant_count": len(lower_records),
                "eligible_lower_variant_count": len(eligible),
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
                "promotion": "NOT_PROMOTED",
            },
            indent=2,
        )
    )
    print(
        f"DONE: v22 joint C9/C20 status={SAFE_STOP}; "
        "mutation_started=False; promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
