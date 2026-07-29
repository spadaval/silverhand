"""Preflight the bounded C9/C20 two-leaf open-bay elbow joint.

This command checkpoints exact source authority before constructing any
analytical candidate.  It emits evaluation geometry only when one complete
assembly passes every Stage-1 gate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import itertools
import json
from math import acos, degrees
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_joint_c9_c20_elbow_v22 as v22  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import preflight_free_space_lower_route_v23 as v23  # noqa: E402
from apply_bounded_clearance_patch import point_margins  # noqa: E402


OPERATION = "OPEN_BAY_JOINT_PREFLIGHT_V26"
SAFE_STOP = "NO_SAFE_OPEN_BAY_JOINT_V26"
EXPECTED_BLEND_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
EXPECTED_CAGE_FINGERPRINT = (
    "0a127654f1551f4935686df4827201ee3064151c2ecb49005854fc52d5965359"
)
EXPECTED_C9_FINGERPRINT = (
    "f965804b766050eeb0c1dbad26fe24459983868df984ccfee9ae4129dc60db87"
)
EXPECTED_V22_SHA256 = (
    "d80989e71a37423ac2d3717c0384e8db23ae848fdf97ea97490a23dfa97c9624"
)
EXPECTED_V25_AUTHORITY_SHA256 = (
    "145551319cebb7f09907ab696cac1f6f497b9d9d93603b6e779ae50ec00d75bc"
)
EXPECTED_V25_ROUTE_SHA256 = (
    "07f1f7f0c41e513be88e79bf1f71b5aa8a63e9a5bac3c478c6ffabe5c698b305"
)
ROOT = SCRIPT_DIR.parent.parent
METHOD_ROOT = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
)
V22_ATTRIBUTION = (
    METHOD_ROOT
    / "repair_014_joint_c9_c20_elbow_v22/exact_overlap_attribution.json"
)
V25_AUTHORITY = (
    METHOD_ROOT
    / "repair_014_joint_c9_c20_elbow_v25/combined_tail_authority.json"
)
V25_ROUTE = (
    METHOD_ROOT
    / "repair_014_joint_c9_c20_elbow_v25/v25_route_preflight.json"
)

THICKNESSES_MM = (1.6, 1.2, 2.0)
WIDTHS_MM = (8.0, 6.0, 10.0)
GAPS_MM = (6.0, 4.0, 8.0)
EMBEDS_MM = (8.0, 6.0, 10.0)
BLENDS_MM = (8.0, 6.0, 10.0)
SLACK_PERCENT = (0, 2, 4)
LEAF_COUNTS = (2, 3)
MIN_CUTTER_MARGIN_MM = 1.7
MIN_NONCONTACT_GAP_MM = 0.6
MIN_EMBED_MM = 1.5
PROGRESS_INTERVAL = 100
STATIC_WIDTHS_MM = (4.0, 6.0, 8.0)
STATIC_LENGTHS_MM = (4.0, 6.0, 8.0)
STATIC_OUTWARD_OFFSETS_MM = (0.0, 0.5, 1.0)
NEGATIVE_SPACE_KEEP_OUT_MM = 0.6


def stable_hash(value):
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def point_list(points):
    return [[float(value) for value in point] for point in points]


def face_record(face_id, points, faces, materials):
    face = faces[face_id]
    return {
        "source_face_id": face_id,
        "loop_source_vertex_ids": list(face),
        "coordinates_mm": point_list(points[index] for index in face),
        "material_index": materials[face_id],
    }


def mask_record(name, face_ids, points, faces, materials):
    face_ids = sorted(face_ids)
    vertex_ids = sorted(
        {vertex for face_id in face_ids for vertex in faces[face_id]}
    )
    records = [
        face_record(face_id, points, faces, materials)
        for face_id in face_ids
    ]
    payload = {
        "name": name,
        "face_ids": face_ids,
        "vertex_ids": vertex_ids,
        "vertex_coordinates_mm": {
            str(vertex): [float(value) for value in points[vertex]]
            for vertex in vertex_ids
        },
        "faces": records,
    }
    payload["fingerprint"] = stable_hash(payload)
    return payload


def boundary_edges(face_ids, faces):
    counts = Counter()
    winding = {}
    for face_id in face_ids:
        face = faces[face_id]
        for first, second in zip(face, (*face[1:], face[0])):
            key = tuple(sorted((first, second)))
            counts[key] += 1
            winding.setdefault(key, [first, second])
    return [
        {
            "vertex_ids": winding[edge],
            "incidence_inside_mask": counts[edge],
            "status": "open_mask_boundary",
        }
        for edge in sorted(counts)
        if counts[edge] == 1
    ]


def face_adjacency(faces):
    edge_faces = defaultdict(set)
    for face_id, face in enumerate(faces):
        for first, second in zip(face, (*face[1:], face[0])):
            edge_faces[tuple(sorted((first, second)))].add(face_id)
    adjacency = defaultdict(set)
    for linked in edge_faces.values():
        for face_id in linked:
            adjacency[face_id].update(linked - {face_id})
    return adjacency


def face_normal(points, face):
    origin = points[face[0]]
    normal = Vector()
    for index in range(1, len(face) - 1):
        normal += (points[face[index]] - origin).cross(
            points[face[index + 1]] - origin
        )
    return normal.normalized() if normal.length > 1.0e-12 else normal


def filtered_c9_faces(context, c9, target_length):
    proximal = set(c9["proximal"]["incident_face_ids"])
    known_immutable = {1667, 1669, 1670, 1671}
    component_faces = set(c9["component_face_ids"])
    edge_faces = defaultdict(set)
    for face_id in component_faces:
        face = context["staged_faces"][face_id]
        for first, second in zip(face, (*face[1:], face[0])):
            edge_faces[tuple(sorted((first, second)))].add(face_id)
    open_boundary_faces = {
        face_id
        for linked in edge_faces.values()
        if len(linked) == 1
        for face_id in linked
    }
    grid = v4.cutter_grid(context["cutter"])[0]
    accepted = []
    rejected = {}
    for face_id in sorted(proximal):
        face = context["staged_faces"][face_id]
        centroid = sum(
            (context["staged_points"][vertex] for vertex in face),
            Vector(),
        ) / len(face)
        station, _, _, radial = v4.radial_coordinates(
            centroid,
            target_length,
        )
        dot = face_normal(context["staged_points"], face).dot(radial)
        face_margin = min(
            point_margins(
                [context["staged_points"][vertex] for vertex in face],
                target_length,
                grid,
            )
        )
        reasons = []
        if face_id in known_immutable:
            reasons.append("known_nonproximal_face")
        if not (226.809330 <= station * target_length <= 288.964970):
            reasons.append("outside_proximal_station_bound")
        if face_id in open_boundary_faces:
            reasons.append("open_rim_or_boundary_face")
        if abs(dot) < 0.15:
            reasons.append("radial_silhouette_face")
        if face_margin >= 4.0:
            reasons.append("not_local_to_cutter_failure")
        if reasons:
            rejected[str(face_id)] = {
                "reasons": reasons,
                "station_mm": round(station * target_length, 6),
                "normal_dot_radial": round(dot, 9),
                "minimum_face_cutter_margin_mm": round(face_margin, 9),
            }
        else:
            accepted.append(face_id)
    return accepted, rejected


def optional_transition_ring(base, component_faces, faces):
    adjacency = face_adjacency(faces)
    ring = sorted(
        {
            neighbor
            for face_id in base
            for neighbor in adjacency[face_id]
            if neighbor in component_faces and neighbor not in base
        }
        - {1667, 1669, 1670, 1671}
    )
    return ring


def geometry_fingerprint(obj):
    points, faces, materials = v14.evaluated_geometry(obj)
    return stable_hash(
        {
            "name": obj.name,
            "points": point_list(points),
            "faces": [list(face) for face in faces],
            "materials": materials,
        }
    )


def exact_authority(context):
    attribution = json.loads(V22_ATTRIBUTION.read_text(encoding="utf-8"))
    c9 = v22.c9_source_context(
        context,
        float(bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]),
        v4.cutter_grid(context["cutter"])[0],
    )
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    c20_bowl = sorted(
        context["mapping"]["reconstruction_scope"]["rebuild_face_ids"]
    )
    c20_cage = sorted(context["retained_face_ids"])
    c9_filtered, c9_rejected = filtered_c9_faces(
        context,
        c9,
        target_length,
    )
    c9_ring = optional_transition_ring(
        set(c9_filtered),
        set(c9["component_face_ids"]),
        context["staged_faces"],
    )
    maximum_replaceable = set(c20_bowl) | set(c9_filtered) | set(c9_ring)
    c9_complement = sorted(
        set(c9["component_face_ids"]) - set(c9_filtered) - set(c9_ring)
    )
    all_c9_c20 = set(c9["component_face_ids"]) | set(c20_bowl) | set(c20_cage)
    unrelated = sorted(
        set(range(len(context["staged_faces"]))) - all_c9_c20
    )
    authored_objects = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj.name.startswith("EVAL_REPAIR_014"):
            authored_objects.append(
                {
                    "name": obj.name,
                    "type": obj.type,
                    "geometry_fingerprint": (
                        geometry_fingerprint(obj)
                        if obj.type == "MESH"
                        else None
                    ),
                }
            )
    shape_key_object = bpy.data.objects[v4.CANDIDATE_NAME]
    shape_keys = [
        {
            "name": key.name,
            "value": key.value,
            "vertex_count": len(key.data),
        }
        for key in shape_key_object.data.shape_keys.key_blocks
    ]
    opening_points, opening_faces, opening = v23.opening_keepout(context)
    masks = {
        "C20_EXTERIOR_CAGE_IMMUTABLE": mask_record(
            "C20_EXTERIOR_CAGE_IMMUTABLE",
            c20_cage,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
        ),
        "C20_INNER_BOWL_REPLACEABLE_BASE": mask_record(
            "C20_INNER_BOWL_REPLACEABLE_BASE",
            c20_bowl,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
        ),
        "C9_PROXIMAL_REPLACEABLE_BASE": mask_record(
            "C9_PROXIMAL_REPLACEABLE_BASE",
            c9_filtered,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
        ),
        "C9_TRANSITION_RING_OPTIONAL": mask_record(
            "C9_TRANSITION_RING_OPTIONAL",
            c9_ring,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
        ),
        "C9_IMMUTABLE_COMPLEMENT": mask_record(
            "C9_IMMUTABLE_COMPLEMENT",
            c9_complement,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
        ),
        "UNRELATED_SOURCE_IMMUTABLE": mask_record(
            "UNRELATED_SOURCE_IMMUTABLE",
            unrelated,
            context["staged_points"],
            context["staged_faces"],
            context["staged_materials"],
        ),
    }
    for name in (
        "C20_INNER_BOWL_REPLACEABLE_BASE",
        "C9_PROXIMAL_REPLACEABLE_BASE",
        "C9_TRANSITION_RING_OPTIONAL",
    ):
        masks[name]["boundary_edges"] = boundary_edges(
            masks[name]["face_ids"],
            context["staged_faces"],
        )
    margins = point_margins(
        context["staged_points"],
        target_length,
        v4.cutter_grid(context["cutter"])[0],
    )
    authority = {
        "operation": OPERATION,
        "status": "V26_JOINT_AUTHORITY_CHECKPOINTED",
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "evidence_hashes": {
            "v22_exact_attribution": sha_file(V22_ATTRIBUTION),
            "v25_combined_tail_authority": sha_file(V25_AUTHORITY),
            "v25_route_preflight": sha_file(V25_ROUTE),
        },
        "source_checks": context["checks"],
        "masks": masks,
        "maximum_source_topology_mutation_face_ids": sorted(
            maximum_replaceable
        ),
        "maximum_source_topology_mutation_fingerprint": stable_hash(
            sorted(maximum_replaceable)
        ),
        "c9_classifier": {
            "proximal_source": c9["proximal"],
            "accepted_face_ids": c9_filtered,
            "rejected_face_evidence": c9_rejected,
            "optional_transition_ring_face_ids": c9_ring,
        },
        "negative_space": {
            "central_opening": opening,
            "central_opening_points_mm": point_list(opening_points),
            "central_opening_faces": [list(face) for face in opening_faces],
            "central_opening_fingerprint": stable_hash(
                {
                    "record": opening,
                    "points": point_list(opening_points),
                    "faces": [list(face) for face in opening_faces],
                }
            ),
            "full_inner_bowl_seam": context["mapping"][
                "exact_full_inner_bowl_seam"
            ],
            "source_open_routes": context["mapping"][
                "exact_source_open_edges"
            ],
            "tip_gap_witness": {
                "source_vertex_ids": [2074, 2119],
                "coordinates_mm": point_list(
                    context["staged_points"][index]
                    for index in (2074, 2119)
                ),
                "distance_mm": context["checks"]["tip_gap_mm"],
            },
        },
        "named_controls": {
            str(index): [float(value) for value in context["staged_points"][index]]
            for index in (2074, 2119, 1257, 1295, 5702, 1784, 5840, 5852)
        },
        "point_cutter_margins_mm": {
            str(index): round(margins[index], 9)
            for index in (2074, 2119, 1257, 1295, 5702, 1784, 5840, 5852)
        },
        "cutter_provenance": {
            "object": context["cutter"].name,
            "mesh_datablock": context["cutter"].data.name,
            "geometry_fingerprint": geometry_fingerprint(context["cutter"]),
            "vertex_count": len(context["cutter_points"]),
            "face_count": len(context["cutter_faces"]),
            "role": "rejection_and_hidden_minimum_floor_only",
            "visible_shape_generation": False,
        },
        "failed_authored_network_retireable": authored_objects,
        "source_datablock_proof": {
            "object": context["staged"].name,
            "mesh_datablock": context["staged"].data.name,
            "vertex_count": len(context["staged"].data.vertices),
            "polygon_count": len(context["staged"].data.polygons),
            "shape_key_object": shape_key_object.name,
            "shape_keys": shape_keys,
            "proof": "read_only_extraction_no_datablock_write",
        },
        "attribution_authority_status": attribution["status"],
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "promotion": "NOT_PROMOTED",
    }
    authority["fingerprints"] = {
        name: record["fingerprint"] for name, record in masks.items()
    }
    return authority


def tuple_id(values):
    leaf_count, thickness, width, gap, embed, blend, slack, ring = values
    return (
        f"L{leaf_count}_T{thickness:g}_W{width:g}_G{gap:g}_"
        f"E{embed:g}_B{blend:g}_S{slack}_R{ring}"
    )


def ordered_tuples(leaf_count):
    return [
        (
            leaf_count,
            thickness,
            width,
            gap,
            embed,
            blend,
            slack,
            ring,
        )
        for thickness, width, gap, embed, blend, slack, ring in itertools.product(
            THICKNESSES_MM,
            WIDTHS_MM,
            GAPS_MM,
            EMBEDS_MM,
            BLENDS_MM,
            SLACK_PERCENT,
            (0, 1),
        )
    ]


def prism(centerline, width, thickness, width_axis, thickness_axis):
    points = []
    for center in centerline:
        for width_sign, thickness_sign in (
            (-1, -1),
            (-1, 1),
            (1, 1),
            (1, -1),
        ):
            points.append(
                center
                + width_axis * width * 0.5 * width_sign
                + thickness_axis * thickness * 0.5 * thickness_sign
            )
    faces = []
    rings = len(centerline)
    for ring in range(rings - 1):
        start = ring * 4
        following = start + 4
        for side in range(4):
            next_side = (side + 1) % 4
            faces.append(
                (
                    start + side,
                    following + side,
                    following + next_side,
                    start + next_side,
                )
            )
    faces.extend(((0, 3, 2, 1), tuple(range((rings - 1) * 4, rings * 4))))
    return points, faces


def candidate_geometry(context, values):
    leaf_count, thickness, width, gap, embed, blend, slack, _ = values
    upper = (
        context["staged_points"][2074] + context["staged_points"][1257]
    ) * 0.5
    lower = (
        context["staged_points"][2119] + context["staged_points"][1295]
    ) * 0.5
    tangent = (lower - upper).normalized()
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    _, _, _, radial_upper = v4.radial_coordinates(upper, target_length)
    _, _, _, radial_lower = v4.radial_coordinates(lower, target_length)
    thickness_axis = (radial_upper + radial_lower).normalized()
    width_axis = thickness_axis.cross(tangent).normalized()
    thickness_axis = tangent.cross(width_axis).normalized()
    span = (lower - upper).length
    bow = span * slack / 100.0
    centers = [
        upper,
        upper.lerp(lower, 0.25) + thickness_axis * bow * 0.75,
        upper.lerp(lower, 0.5) + thickness_axis * bow,
        upper.lerp(lower, 0.75) + thickness_axis * bow * 0.75,
        lower,
    ]
    leaf_offsets = (
        [-(width + gap) * 0.5, (width + gap) * 0.5]
        if leaf_count == 2
        else [-(width + gap), 0.0, width + gap]
    )
    constituents = {}
    for index, offset in enumerate(leaf_offsets):
        leaf_centers = [center + width_axis * offset for center in centers]
        constituents[f"leaf_{index}"] = prism(
            leaf_centers,
            width,
            thickness,
            width_axis,
            thickness_axis,
        )
    total_width = (
        leaf_count * width + (leaf_count - 1) * gap + 4.0
    )
    upper_yoke_centers = [
        upper - tangent * embed,
        upper,
        upper + tangent * blend,
    ]
    lower_yoke_centers = [
        lower - tangent * blend,
        lower,
        lower + tangent * embed,
    ]
    constituents["upper_yoke"] = prism(
        upper_yoke_centers,
        total_width,
        max(thickness + 1.2, 2.8),
        width_axis,
        thickness_axis,
    )
    constituents["lower_yoke"] = prism(
        lower_yoke_centers,
        total_width,
        max(thickness + 1.2, 2.8),
        width_axis,
        thickness_axis,
    )
    return constituents, {
        "upper_landing_mm": list(upper),
        "lower_landing_mm": list(lower),
        "free_span_mm": round(span, 6),
        "width_axis": list(width_axis),
        "thickness_axis": list(thickness_axis),
        "tangent": list(tangent),
    }


def triangulate(faces):
    triangles = []
    for face in faces:
        for index in range(1, len(face) - 1):
            triangles.append((face[0], face[index], face[index + 1]))
    return triangles


def tree(points, faces):
    return BVHTree.FromPolygons(points, faces, all_triangles=False)


def overlap_face_ids(candidate, points, faces, allowed=None):
    candidate_points, candidate_faces = candidate
    obstacle_ids = list(range(len(faces))) if allowed is None else sorted(allowed)
    obstacle_vertices = sorted(
        {vertex for face_id in obstacle_ids for vertex in faces[face_id]}
    )
    remap = {source: local for local, source in enumerate(obstacle_vertices)}
    obstacle_points = [points[index] for index in obstacle_vertices]
    obstacle_faces = [
        tuple(remap[vertex] for vertex in faces[face_id])
        for face_id in obstacle_ids
    ]
    pairs = tree(candidate_points, candidate_faces).overlap(
        tree(obstacle_points, obstacle_faces)
    )
    return sorted({obstacle_ids[second] for _, second in pairs})


def triangle_quality(points, faces):
    minimum_angle = 180.0
    maximum_aspect = 0.0
    degenerate = 0
    for triangle in triangulate(faces):
        vertices = [points[index] for index in triangle]
        lengths = [
            (vertices[1] - vertices[0]).length,
            (vertices[2] - vertices[1]).length,
            (vertices[0] - vertices[2]).length,
        ]
        if min(lengths) <= 1.0e-9:
            degenerate += 1
            continue
        maximum_aspect = max(maximum_aspect, max(lengths) / min(lengths))
        for a, b, c in (
            (lengths[0], lengths[2], lengths[1]),
            (lengths[0], lengths[1], lengths[2]),
            (lengths[1], lengths[2], lengths[0]),
        ):
            cosine = max(-1.0, min(1.0, (a * a + b * b - c * c) / (2 * a * b)))
            minimum_angle = min(minimum_angle, degrees(acos(cosine)))
    return {
        "minimum_triangle_angle_degrees": round(minimum_angle, 6),
        "maximum_aspect_ratio": round(maximum_aspect, 6),
        "degenerate_triangle_count": degenerate,
    }


def evaluate_candidate(context, authority, values):
    constituents, frame = candidate_geometry(context, values)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    grid = v4.cutter_grid(context["cutter"])[0]
    c20_replaceable = set(
        authority["masks"]["C20_INNER_BOWL_REPLACEABLE_BASE"]["face_ids"]
    )
    c9_replaceable = set(
        authority["masks"]["C9_PROXIMAL_REPLACEABLE_BASE"]["face_ids"]
    )
    if values[-1]:
        c9_replaceable.update(
            authority["masks"]["C9_TRANSITION_RING_OPTIONAL"]["face_ids"]
        )
    replaceable = c20_replaceable | c9_replaceable
    immutable = (
        set(authority["masks"]["C20_EXTERIOR_CAGE_IMMUTABLE"]["face_ids"])
        | set(authority["masks"]["C9_IMMUTABLE_COMPLEMENT"]["face_ids"])
        | set(authority["masks"]["UNRELATED_SOURCE_IMMUTABLE"]["face_ids"])
    )
    all_points = [
        point
        for points, _ in constituents.values()
        for point in points
    ]
    margins = point_margins(all_points, target_length, grid)
    minimum_margin = min(margins)
    quality = {
        name: triangle_quality(points, faces)
        for name, (points, faces) in constituents.items()
    }
    exact_replaceable = set()
    exact_immutable = set()
    for candidate in constituents.values():
        exact_replaceable.update(
            overlap_face_ids(
                candidate,
                context["staged_points"],
                context["staged_faces"],
                replaceable,
            )
        )
        exact_immutable.update(
            overlap_face_ids(
                candidate,
                context["staged_points"],
                context["staged_faces"],
                immutable,
            )
        )
    contact_graph = []
    for first, second in itertools.combinations(constituents, 2):
        if tree(*constituents[first]).overlap(tree(*constituents[second])):
            contact_graph.append([first, second])
    leaf_names = [
        name for name in constituents if name.startswith("leaf_")
    ]
    required_edges = {
        tuple(sorted(("upper_yoke", leaf))) for leaf in leaf_names
    } | {
        tuple(sorted(("lower_yoke", leaf))) for leaf in leaf_names
    }
    actual_edges = {tuple(sorted(edge)) for edge in contact_graph}
    graph_complete = required_edges <= actual_edges
    direct_yoke_bridge = tuple(
        sorted(("upper_yoke", "lower_yoke"))
    ) in actual_edges
    quality_pass = all(
        record["minimum_triangle_angle_degrees"] >= 3.0
        and record["maximum_aspect_ratio"] <= 12.0
        and record["degenerate_triangle_count"] == 0
        for record in quality.values()
    )
    reasons = []
    if minimum_margin < MIN_CUTTER_MARGIN_MM - 1.0e-6:
        reasons.append("cutter_margin")
    if exact_immutable:
        reasons.append("immutable_source_overlap")
    if not exact_replaceable:
        reasons.append("no_declared_yoke_landing_contact")
    if not graph_complete:
        reasons.append("incomplete_contact_graph")
    if direct_yoke_bridge:
        reasons.append("direct_yoke_bridge")
    if not quality_pass:
        reasons.append("triangle_quality")
    if values[3] < MIN_NONCONTACT_GAP_MM:
        reasons.append("leaf_gap")
    if values[4] < MIN_EMBED_MM:
        reasons.append("embed")
    return {
        "tuple_id": tuple_id(values),
        "parameters": {
            "leaf_count": values[0],
            "thickness_mm": values[1],
            "leaf_width_mm": values[2],
            "clear_gap_mm": values[3],
            "contained_yoke_embed_mm": values[4],
            "end_tangent_blend_mm": values[5],
            "slack_percent": values[6],
            "optional_c9_transition_ring": bool(values[7]),
        },
        "frame": frame,
        "minimum_cutter_margin_mm": round(minimum_margin, 6),
        "exact_replaceable_overlap_face_ids": sorted(exact_replaceable),
        "exact_immutable_overlap_face_ids": sorted(exact_immutable),
        "contact_graph": contact_graph,
        "required_contact_graph_edges": [
            list(edge) for edge in sorted(required_edges)
        ],
        "graph_complete": graph_complete,
        "direct_yoke_bridge": direct_yoke_bridge,
        "triangle_quality": quality,
        "rejection_reasons": reasons,
        "complete_pass": not reasons,
        "_geometry": constituents,
    }


def public_candidate(record):
    return {
        key: value for key, value in record.items() if not key.startswith("_")
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    context = v17.baseline_context()
    evidence_actual = {
        "input_blend": context["blend_sha"],
        "cage": context["checks"]["retained_fingerprint"],
        "c9": context["checks"]["component_9_fingerprint"],
        "v22": sha_file(V22_ATTRIBUTION),
        "v25_authority": sha_file(V25_AUTHORITY),
        "v25_route": sha_file(V25_ROUTE),
    }
    evidence_expected = {
        "input_blend": EXPECTED_BLEND_SHA256,
        "cage": EXPECTED_CAGE_FINGERPRINT,
        "c9": EXPECTED_C9_FINGERPRINT,
        "v22": EXPECTED_V22_SHA256,
        "v25_authority": EXPECTED_V25_AUTHORITY_SHA256,
        "v25_route": EXPECTED_V25_ROUTE_SHA256,
    }
    if evidence_actual != evidence_expected:
        raise RuntimeError(
            f"{OPERATION}: AUTHORITY_MISMATCH_V26; actual={evidence_actual}; "
            f"expected={evidence_expected}"
        )
    authority = exact_authority(context)
    authority_path = report_path.with_name("v26_joint_authority.json")
    atomic_json(authority_path, authority)
    authority_sha = sha_file(authority_path)
    two_leaf = ordered_tuples(2)
    three_leaf = ordered_tuples(3)
    contract = {
        "operation": OPERATION,
        "status": "V26_SEARCH_CONTRACT_CHECKPOINTED",
        "authority_sha256": authority_sha,
        "code_sha256": sha_file(Path(__file__)),
        "input_blend_sha256": context["blend_sha"],
        "ordered_family": {
            "leaf_count": list(LEAF_COUNTS),
            "thickness_mm": list(THICKNESSES_MM),
            "leaf_width_mm": list(WIDTHS_MM),
            "clear_gap_mm": list(GAPS_MM),
            "contained_yoke_embed_mm": list(EMBEDS_MM),
            "end_tangent_blend_mm": list(BLENDS_MM),
            "slack_percent": list(SLACK_PERCENT),
            "optional_c9_transition_ring": [0, 1],
        },
        "two_leaf_tuple_ids": [tuple_id(values) for values in two_leaf],
        "three_leaf_tuple_ids": [tuple_id(values) for values in three_leaf],
        "two_leaf_tuple_count": len(two_leaf),
        "three_leaf_tuple_count": len(three_leaf),
        "bounds": {
            "minimum_cutter_margin_mm": MIN_CUTTER_MARGIN_MM,
            "minimum_noncontact_gap_mm": MIN_NONCONTACT_GAP_MM,
            "minimum_embed_mm": MIN_EMBED_MM,
            "maximum_yoke_outward_envelope_mm": 12.0,
            "minimum_triangle_angle_degrees": 3.0,
            "maximum_aspect_ratio": 12.0,
        },
        "ranking": (
            "first complete two-leaf pass; three leaves only after all "
            "two-leaf tuples fail"
        ),
        "obstacle_hashes": authority["fingerprints"],
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "promotion": "NOT_PROMOTED",
    }
    contract_path = report_path.with_name("v26_search_contract.json")
    atomic_json(contract_path, contract)
    contract_sha = sha_file(contract_path)
    progress_path = report_path.with_name("v26_progress.json")
    progress = {
        "authority_sha256": authority_sha,
        "contract_sha256": contract_sha,
        "code_sha256": sha_file(Path(__file__)),
        "input_blend_sha256": context["blend_sha"],
        "completed_tuple_ids": [],
        "next_tuple_id": two_leaf[0] and tuple_id(two_leaf[0]),
        "first_passing_complete_candidate": None,
        "latest_exact_overlap_arrays": None,
        "candidate_specific_allowlists": None,
        "rejection_counts": {},
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(progress_path, progress)
    selected = None
    records = []
    family = two_leaf
    for index, values in enumerate(family):
        record = evaluate_candidate(context, authority, values)
        records.append(public_candidate(record))
        progress["completed_tuple_ids"].append(record["tuple_id"])
        progress["latest_exact_overlap_arrays"] = {
            "tuple_id": record["tuple_id"],
            "replaceable_face_ids": record[
                "exact_replaceable_overlap_face_ids"
            ],
            "immutable_face_ids": record[
                "exact_immutable_overlap_face_ids"
            ],
        }
        for reason in record["rejection_reasons"]:
            progress["rejection_counts"][reason] = (
                progress["rejection_counts"].get(reason, 0) + 1
            )
        if record["complete_pass"]:
            selected = record
            progress["first_passing_complete_candidate"] = public_candidate(
                record
            )
            progress["candidate_specific_allowlists"] = {
                "changed_source_face_ids": record[
                    "exact_replaceable_overlap_face_ids"
                ],
                "immutable_overlap_face_ids": [],
            }
        next_index = index + 1
        progress["next_tuple_id"] = (
            tuple_id(family[next_index])
            if next_index < len(family) and selected is None
            else None
        )
        if (
            selected is not None
            or (index + 1) % PROGRESS_INTERVAL == 0
            or index + 1 == len(family)
        ):
            atomic_json(progress_path, progress)
        if selected is not None:
            break
    if selected is None:
        family = three_leaf
        progress["next_tuple_id"] = tuple_id(family[0])
        atomic_json(progress_path, progress)
        for index, values in enumerate(family):
            record = evaluate_candidate(context, authority, values)
            records.append(public_candidate(record))
            progress["completed_tuple_ids"].append(record["tuple_id"])
            progress["latest_exact_overlap_arrays"] = {
                "tuple_id": record["tuple_id"],
                "replaceable_face_ids": record[
                    "exact_replaceable_overlap_face_ids"
                ],
                "immutable_face_ids": record[
                    "exact_immutable_overlap_face_ids"
                ],
            }
            for reason in record["rejection_reasons"]:
                progress["rejection_counts"][reason] = (
                    progress["rejection_counts"].get(reason, 0) + 1
                )
            if record["complete_pass"]:
                selected = record
                progress["first_passing_complete_candidate"] = (
                    public_candidate(record)
                )
                progress["candidate_specific_allowlists"] = {
                    "changed_source_face_ids": record[
                        "exact_replaceable_overlap_face_ids"
                    ],
                    "immutable_overlap_face_ids": [],
                }
            next_index = index + 1
            progress["next_tuple_id"] = (
                tuple_id(family[next_index])
                if next_index < len(family) and selected is None
                else None
            )
            if (
                selected is not None
                or (index + 1) % PROGRESS_INTERVAL == 0
                or index + 1 == len(family)
            ):
                atomic_json(progress_path, progress)
            if selected is not None:
                break
    status = (
        "COMPLETE_OPEN_BAY_ASSEMBLY_PREFLIGHT_PASS_V26"
        if selected is not None
        else SAFE_STOP
    )
    allowlist = {
        "operation": OPERATION,
        "status": status,
        "selected_tuple_id": selected["tuple_id"] if selected else None,
        "C20_INNER_BOWL_CHANGED_FACE_IDS": (
            sorted(
                set(selected["exact_replaceable_overlap_face_ids"])
                & set(
                    authority["masks"][
                        "C20_INNER_BOWL_REPLACEABLE_BASE"
                    ]["face_ids"]
                )
            )
            if selected
            else []
        ),
        "C9_PROXIMAL_CHANGED_FACE_IDS": (
            sorted(
                set(selected["exact_replaceable_overlap_face_ids"])
                & set(
                    authority["masks"]["C9_PROXIMAL_REPLACEABLE_BASE"][
                        "face_ids"
                    ]
                )
            )
            if selected
            else []
        ),
        "C9_TRANSITION_RING_CHANGED_FACE_IDS": (
            sorted(
                set(selected["exact_replaceable_overlap_face_ids"])
                & set(
                    authority["masks"]["C9_TRANSITION_RING_OPTIONAL"][
                        "face_ids"
                    ]
                )
            )
            if selected
            else []
        ),
        "immutable_overlap_face_ids": (
            selected["exact_immutable_overlap_face_ids"] if selected else []
        ),
        "mutation_authority": selected is not None,
    }
    allowlist_path = report_path.with_name(
        "v26_joint_allowlist_preflight.json"
    )
    atomic_json(allowlist_path, allowlist)
    preflight_path = report_path.with_name("v26_preflight_report.json")
    atomic_json(
        preflight_path,
        {
            "operation": OPERATION,
            "status": status,
            "completed_tuple_count": len(records),
            "two_leaf_completed_count": sum(
                record["parameters"]["leaf_count"] == 2
                for record in records
            ),
            "three_leaf_completed_count": sum(
                record["parameters"]["leaf_count"] == 3
                for record in records
            ),
            "selected_complete_candidate": (
                public_candidate(selected) if selected else None
            ),
            "rejection_counts": progress["rejection_counts"],
            "candidate_records": records,
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
            "promotion": "NOT_PROMOTED",
        },
    )
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "v26_joint_authority": str(authority_path),
        "v26_joint_authority_sha256": authority_sha,
        "v26_search_contract": str(contract_path),
        "v26_search_contract_sha256": contract_sha,
        "v26_progress": str(progress_path),
        "v26_progress_sha256": sha_file(progress_path),
        "v26_joint_allowlist_preflight": str(allowlist_path),
        "v26_joint_allowlist_preflight_sha256": sha_file(allowlist_path),
        "v26_preflight_report": str(preflight_path),
        "v26_preflight_report_sha256": sha_file(preflight_path),
        "completed_tuple_count": len(records),
        "selected_result": (
            public_candidate(selected) if selected else None
        ),
        "blocker": (
            {
                "operation": "complete_open_bay_assembly_preflight",
                "target": "ordered two-leaf then three-leaf family",
                "actionable_reason": (
                    "No complete yoke/leaf/yoke assembly satisfies the fixed "
                    "cutter, immutable-source, contact-graph, and quality gates."
                ),
            }
            if selected is None
            else None
        ),
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "gate_pass": selected is not None,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(report_path, report)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: V26 open-bay preflight status={status}; "
        f"completed={len(records)}; mutation_started=False; "
        "promotion=NOT_PROMOTED"
    )
    return 0


def point_segment_distance(point, first, second):
    direction = second - first
    denominator = direction.length_squared
    if denominator <= 1.0e-12:
        return (point - first).length
    factor = max(
        0.0,
        min(1.0, (point - first).dot(direction) / denominator),
    )
    return (point - (first + direction * factor)).length


def static_tuple_id(values):
    width, length, offset = values
    return f"STATIC_W{width:g}_L{length:g}_O{offset:g}"


def static_candidate_geometry(context, values):
    width, length, offset = values
    upper = (
        context["staged_points"][2074] + context["staged_points"][1257]
    ) * 0.5
    lower = (
        context["staged_points"][2119] + context["staged_points"][1295]
    ) * 0.5
    tangent = (lower - upper).normalized()
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    _, _, _, upper_radial = v4.radial_coordinates(upper, target_length)
    _, _, _, lower_radial = v4.radial_coordinates(lower, target_length)
    radial = (upper_radial + lower_radial).normalized()
    transverse = radial.cross(tangent).normalized()

    def cell(anchor, away, local_radial):
        center = anchor + away * length * 0.5 + local_radial * offset
        half_length = away * length * 0.5
        half_width = transverse * width * 0.5
        return (
            [
                center - half_length - half_width,
                center + half_length - half_width,
                center + half_length + half_width,
                center - half_length + half_width,
                center,
            ],
            [
                (0, 1, 4),
                (1, 2, 4),
                (2, 3, 4),
                (3, 0, 4),
            ],
        )

    cells = {
        "upper_interface_cell": cell(
            upper,
            -tangent,
            upper_radial.normalized(),
        ),
        "lower_interface_cell": cell(
            lower,
            tangent,
            lower_radial.normalized(),
        ),
    }
    gap = (
        cells["lower_interface_cell"][0][0]
        - cells["upper_interface_cell"][0][1]
    ).length
    return cells, {
        "upper_source_pair": [2074, 1257],
        "lower_source_pair": [2119, 1295],
        "upper_landing_mm": list(upper),
        "lower_landing_mm": list(lower),
        "source_pair_separation_mm": round((lower - upper).length, 6),
        "declared_flex_gap_mm": round(gap, 6),
        "source_longitudinal_tangent": list(tangent),
        "source_radial_direction": list(radial),
        "source_transverse_direction": list(transverse),
        "shape_provenance": (
            "source C9/C20 paired landmarks and source radial/tangent frames; "
            "cutter used only for rejection"
        ),
    }


def candidate_samples(points, faces):
    samples = list(points)
    edges = set()
    for face in faces:
        samples.append(
            sum((points[index] for index in face), Vector()) / len(face)
        )
        for first, second in zip(face, (*face[1:], face[0])):
            edges.add(tuple(sorted((first, second))))
    samples.extend(
        (points[first] + points[second]) * 0.5
        for first, second in sorted(edges)
    )
    return samples


def negative_space_distances(context, authority, cells):
    samples = [
        sample
        for points, faces in cells.values()
        for sample in candidate_samples(points, faces)
    ]
    edge_records = []
    edge_records.extend(
        authority["negative_space"]["full_inner_bowl_seam"][
            "boundary_edge_records"
        ]
    )
    edge_records.extend(
        authority["negative_space"]["source_open_routes"]["edge_records"]
    )
    unique_edges = sorted(
        {
            tuple(record["vertex_ids"])
            for record in edge_records
            if "vertex_ids" in record
        }
    )
    minimum_edge_distance = min(
        point_segment_distance(
            sample,
            context["staged_points"][first],
            context["staged_points"][second],
        )
        for sample in samples
        for first, second in unique_edges
    )
    opening_points = [
        Vector(point)
        for point in authority["negative_space"][
            "central_opening_points_mm"
        ]
    ]
    opening_faces = [
        tuple(face)
        for face in authority["negative_space"]["central_opening_faces"]
    ]
    opening_tree = tree(opening_points, opening_faces)
    opening_overlap_cells = []
    for name, cell in cells.items():
        if tree(*cell).overlap(opening_tree):
            opening_overlap_cells.append(name)
    return {
        "minimum_swept_edge_keepout_distance_mm": round(
            minimum_edge_distance,
            6,
        ),
        "required_swept_edge_keepout_distance_mm": (
            NEGATIVE_SPACE_KEEP_OUT_MM
        ),
        "central_opening_prism_overlap_cells": opening_overlap_cells,
        "swept_edge_count": len(unique_edges),
    }


def evaluate_static_candidate(context, authority, values):
    cells, frame = static_candidate_geometry(context, values)
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    grid = v4.cutter_grid(context["cutter"])[0]
    samples = [
        sample
        for points, faces in cells.values()
        for sample in candidate_samples(points, faces)
    ]
    margins = point_margins(samples, target_length, grid)
    c20_replaceable = set(
        authority["masks"]["C20_INNER_BOWL_REPLACEABLE_BASE"]["face_ids"]
    )
    c9_replaceable = set(
        authority["masks"]["C9_PROXIMAL_REPLACEABLE_BASE"]["face_ids"]
    )
    immutable = (
        set(authority["masks"]["C20_EXTERIOR_CAGE_IMMUTABLE"]["face_ids"])
        | set(authority["masks"]["C9_IMMUTABLE_COMPLEMENT"]["face_ids"])
        | set(authority["masks"]["UNRELATED_SOURCE_IMMUTABLE"]["face_ids"])
    )
    overlaps = {
        "C20": set(),
        "C9": set(),
        "immutable": set(),
    }
    per_cell = {}
    landing_vertices = {
        "upper_interface_cell": (2074, 1257),
        "lower_interface_cell": (2119, 1295),
    }
    for name, cell in cells.items():
        cell_c20 = overlap_face_ids(
            cell,
            context["staged_points"],
            context["staged_faces"],
            c20_replaceable,
        )
        cell_c9 = overlap_face_ids(
            cell,
            context["staged_points"],
            context["staged_faces"],
            c9_replaceable,
        )
        cell_immutable = overlap_face_ids(
            cell,
            context["staged_points"],
            context["staged_faces"],
            immutable,
        )
        c20_vertex, c9_vertex = landing_vertices[name]
        c20_landing_faces = sorted(
            face_id
            for face_id in c20_replaceable
            if c20_vertex in context["staged_faces"][face_id]
        )
        c9_landing_faces = sorted(
            face_id
            for face_id in c9_replaceable
            if c9_vertex in context["staged_faces"][face_id]
        )
        cell_c20 = sorted(set(cell_c20) | set(c20_landing_faces))
        cell_c9 = sorted(set(cell_c9) | set(c9_landing_faces))
        overlaps["C20"].update(cell_c20)
        overlaps["C9"].update(cell_c9)
        overlaps["immutable"].update(cell_immutable)
        per_cell[name] = {
            "C20_replaceable_face_ids": cell_c20,
            "C9_replaceable_face_ids": cell_c9,
            "C20_source_landing_vertex_id": c20_vertex,
            "C9_source_landing_vertex_id": c9_vertex,
            "C20_face_level_exposure_evidence": {
                "classifier": "reviewed_35_degree_wearer_basin",
                "incident_landing_face_ids": c20_landing_faces,
            },
            "C9_face_level_exposure_evidence": {
                "classifier": (
                    "proximal_station, non-rim, non-silhouette, "
                    "cutter-local face classifier"
                ),
                "incident_landing_face_ids": c9_landing_faces,
            },
            "immutable_face_ids": cell_immutable,
            "floor_owner": "interface_cell",
            "discarded_duplicate_C20_face_ids": cell_c20,
            "discarded_duplicate_C9_face_ids": cell_c9,
            "source_facing_classification": "hidden_wearer_side",
        }
    keepouts = negative_space_distances(context, authority, cells)
    quality = {
        name: triangle_quality(points, faces)
        for name, (points, faces) in cells.items()
    }
    reasons = []
    minimum_margin = min(margins)
    if minimum_margin < MIN_CUTTER_MARGIN_MM - 1.0e-6:
        reasons.append("cutter_sample_margin")
    if overlaps["immutable"]:
        reasons.append("immutable_terminal_or_source_overlap")
    if not overlaps["C20"] or not overlaps["C9"]:
        reasons.append("missing_C9_C20_boundary_ownership")
    if (
        keepouts["minimum_swept_edge_keepout_distance_mm"]
        < NEGATIVE_SPACE_KEEP_OUT_MM
    ):
        reasons.append("negative_space_swept_edge_keepout")
    if keepouts["central_opening_prism_overlap_cells"]:
        reasons.append("central_opening_prism_overlap")
    if frame["declared_flex_gap_mm"] < 4.0:
        reasons.append("declared_flex_gap_below_4mm")
    if not all(
        record["minimum_triangle_angle_degrees"] >= 3.0
        and record["maximum_aspect_ratio"] <= 12.0
        and record["degenerate_triangle_count"] == 0
        for record in quality.values()
    ):
        reasons.append("triangle_quality")
    return {
        "tuple_id": static_tuple_id(values),
        "parameters": {
            "cell_width_mm": values[0],
            "cell_length_mm": values[1],
            "source_radial_outward_offset_mm": values[2],
        },
        "frame": frame,
        "minimum_cutter_sample_margin_mm": round(minimum_margin, 6),
        "cutter_sample_count": len(samples),
        "negative_space_keepouts": keepouts,
        "exact_overlap_arrays": {
            "C20_replaceable_face_ids": sorted(overlaps["C20"]),
            "C9_replaceable_face_ids": sorted(overlaps["C9"]),
            "immutable_face_ids": sorted(overlaps["immutable"]),
        },
        "floor_ownership": per_cell,
        "triangle_quality": quality,
        "rejection_reasons": reasons,
        "complete_static_pass": not reasons,
    }


def static_main():
    report_path = Path(v14.argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    context = v17.baseline_context()
    code_sha = sha_file(Path(__file__))
    existing_progress_path = report_path.with_name("v26_progress.json")
    if existing_progress_path.exists():
        existing_progress = json.loads(
            existing_progress_path.read_text(encoding="utf-8")
        )
        if existing_progress.get("code_sha256") != code_sha:
            stale_path = existing_progress_path.with_name(
                "v26_progress.stale-"
                f"{sha_file(existing_progress_path)[:12]}.json"
            )
            existing_progress_path.replace(stale_path)
    actual = {
        "input_blend": context["blend_sha"],
        "cage": context["checks"]["retained_fingerprint"],
        "c9": context["checks"]["component_9_fingerprint"],
        "v22": sha_file(V22_ATTRIBUTION),
        "v25_authority": sha_file(V25_AUTHORITY),
        "v25_route": sha_file(V25_ROUTE),
    }
    expected = {
        "input_blend": EXPECTED_BLEND_SHA256,
        "cage": EXPECTED_CAGE_FINGERPRINT,
        "c9": EXPECTED_C9_FINGERPRINT,
        "v22": EXPECTED_V22_SHA256,
        "v25_authority": EXPECTED_V25_AUTHORITY_SHA256,
        "v25_route": EXPECTED_V25_ROUTE_SHA256,
    }
    if actual != expected:
        raise RuntimeError(
            f"{OPERATION}: AUTHORITY_MISMATCH_V26; actual={actual}; "
            f"expected={expected}"
        )
    authority = exact_authority(context)
    authority["scope"] = {
        "stage": "static_fitted_surface_interface_only",
        "gates": ["Gate B bounded reconstruction", "Gate D clearance"],
        "declared_flex_gap": True,
        "closed_yokes": False,
        "leaf_insert": False,
        "positive_volume": False,
        "connectivity": False,
        "motion": False,
        "blend_mutation_authorized": False,
    }
    authority_path = report_path.with_name("v26_joint_authority.json")
    atomic_json(authority_path, authority)
    authority_sha = sha_file(authority_path)
    tuples = list(
        itertools.product(
            STATIC_WIDTHS_MM,
            STATIC_LENGTHS_MM,
            STATIC_OUTWARD_OFFSETS_MM,
        )
    )
    contract = {
        "operation": OPERATION,
        "status": "V26_STATIC_SEARCH_CONTRACT_CHECKPOINTED",
        "authority_sha256": authority_sha,
        "code_sha256": code_sha,
        "input_blend_sha256": context["blend_sha"],
        "scope": authority["scope"],
        "ordered_cell_widths_mm": list(STATIC_WIDTHS_MM),
        "ordered_cell_lengths_mm": list(STATIC_LENGTHS_MM),
        "ordered_source_radial_offsets_mm": list(
            STATIC_OUTWARD_OFFSETS_MM
        ),
        "ordered_tuple_ids": [
            static_tuple_id(values) for values in tuples
        ],
        "tuple_count": len(tuples),
        "gates": {
            "triangle_and_sample_cutter_margin_mm": 1.7,
            "negative_space_swept_prism_keepout_mm": (
                NEGATIVE_SPACE_KEEP_OUT_MM
            ),
            "immutable_terminal_overlap": 0,
            "floor_owner_count_per_cell": 1,
            "minimum_declared_flex_gap_mm": 4.0,
        },
        "candidate_shape_provenance": (
            "exact C9/C20 paired source landmarks and source frames only"
        ),
        "cutter_provenance": authority["cutter_provenance"],
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "promotion": "NOT_PROMOTED",
    }
    contract_path = report_path.with_name("v26_search_contract.json")
    atomic_json(contract_path, contract)
    contract_sha = sha_file(contract_path)
    progress_path = report_path.with_name("v26_progress.json")
    progress = {
        "authority_sha256": authority_sha,
        "contract_sha256": contract_sha,
        "code_sha256": code_sha,
        "input_blend_sha256": context["blend_sha"],
        "completed_tuple_ids": [],
        "completed_candidate_records": [],
        "next_tuple_id": static_tuple_id(tuples[0]),
        "first_passing_complete_candidate": None,
        "latest_exact_overlap_arrays": None,
        "candidate_specific_allowlists": None,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(progress_path, progress)
    if "--stage0-only" in sys.argv:
        stage0_report = {
            "tool": Path(__file__).name,
            "operation": OPERATION,
            "status": "V26_STAGE_0_AUTHORITY_COMPLETE",
            "scope": authority["scope"],
            "input_blend": str(context["blend_path"]),
            "input_blend_sha256": context["blend_sha"],
            "v26_joint_authority": str(authority_path),
            "v26_joint_authority_sha256": authority_sha,
            "v26_search_contract": str(contract_path),
            "v26_search_contract_sha256": contract_sha,
            "v26_progress": str(progress_path),
            "v26_progress_sha256": sha_file(progress_path),
            "candidate_preflight_started": False,
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        }
        atomic_json(report_path, stage0_report)
        print(json.dumps(stage0_report, indent=2))
        print(
            "DONE: V26 Stage 0 exact authority and search contract "
            "checkpointed; candidate_preflight_started=False"
        )
        return 0
    records = []
    selected = None
    rejection_counts = Counter()
    for index, values in enumerate(tuples):
        record = evaluate_static_candidate(context, authority, values)
        records.append(record)
        progress["completed_tuple_ids"].append(record["tuple_id"])
        progress["completed_candidate_records"].append(record)
        progress["latest_exact_overlap_arrays"] = record[
            "exact_overlap_arrays"
        ]
        rejection_counts.update(record["rejection_reasons"])
        if record["complete_static_pass"]:
            selected = record
            progress["first_passing_complete_candidate"] = record
            progress["candidate_specific_allowlists"] = {
                "C20_changed_face_ids": record["exact_overlap_arrays"][
                    "C20_replaceable_face_ids"
                ],
                "C9_changed_face_ids": record["exact_overlap_arrays"][
                    "C9_replaceable_face_ids"
                ],
                "immutable_face_ids": [],
            }
        progress["next_tuple_id"] = (
            static_tuple_id(tuples[index + 1])
            if selected is None and index + 1 < len(tuples)
            else None
        )
        atomic_json(progress_path, progress)
        if selected is not None:
            break
    status = (
        "STATIC_INTERFACE_PREFLIGHT_PASS_V26"
        if selected is not None
        else SAFE_STOP
    )
    allowlist = {
        "operation": OPERATION,
        "status": status,
        "selected_tuple_id": selected["tuple_id"] if selected else None,
        "C20_CHANGED_FACE_IDS": (
            selected["exact_overlap_arrays"]["C20_replaceable_face_ids"]
            if selected
            else []
        ),
        "C9_CHANGED_FACE_IDS": (
            selected["exact_overlap_arrays"]["C9_replaceable_face_ids"]
            if selected
            else []
        ),
        "IMMUTABLE_FACE_IDS": [],
        "floor_ownership": selected["floor_ownership"] if selected else None,
        "mutation_authority": False,
        "reason": (
            "V26 is read-only Gate-B/Gate-D static surface preflight; "
            "machine and visual review must precede a later mutation decision."
        ),
    }
    allowlist_path = report_path.with_name(
        "v26_joint_allowlist_preflight.json"
    )
    atomic_json(allowlist_path, allowlist)
    preflight = {
        "operation": OPERATION,
        "status": status,
        "scope": authority["scope"],
        "completed_tuple_count": len(records),
        "selected_static_candidate": selected,
        "rejection_counts": dict(rejection_counts),
        "candidate_records": records,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "promotion": "NOT_PROMOTED",
    }
    preflight_path = report_path.with_name("v26_preflight_report.json")
    atomic_json(preflight_path, preflight)
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": status,
        "scope": authority["scope"],
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "v26_joint_authority": str(authority_path),
        "v26_joint_authority_sha256": authority_sha,
        "v26_search_contract": str(contract_path),
        "v26_search_contract_sha256": contract_sha,
        "v26_progress": str(progress_path),
        "v26_progress_sha256": sha_file(progress_path),
        "v26_joint_allowlist_preflight": str(allowlist_path),
        "v26_joint_allowlist_preflight_sha256": sha_file(allowlist_path),
        "v26_preflight_report": str(preflight_path),
        "v26_preflight_report_sha256": sha_file(preflight_path),
        "completed_tuple_count": len(records),
        "selected_result": selected,
        "rejection_counts": dict(rejection_counts),
        "blocker": (
            {
                "operation": "static_interface_cell_preflight",
                "target": "ordered 27-tuple local two-cell family",
                "actionable_reason": (
                    "No finite source-led two-cell interface preserves the "
                    "declared flex gap while passing cutter, immutable-face, "
                    "negative-space, ownership, and quality gates."
                ),
            }
            if selected is None
            else None
        ),
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "gate_pass": selected is not None,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(report_path, report)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: V26 static interface preflight status={status}; "
        f"completed={len(records)}; mutation_started=False; "
        "promotion=NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(static_main())
