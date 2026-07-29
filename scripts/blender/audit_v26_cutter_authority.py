"""Checkpoint exact V26 cutter provenance and the future clearance contract.

This script is deliberately read-only.  It does not construct candidate
geometry.  The fixture audit exercises the reusable clearance APIs against
exact source faces incident to the four V26 cell-authority terminal boundaries.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri, intersect_ray_tri

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_three_constituent_lap_network_v17 as v17  # noqa: E402


OPERATION = "V26_CUTTER_AUTHORITY_AUDIT"
MISSION = "R014-JOINT-C9-C20-ELBOW-V26"
EXPECTED_BLEND_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
EXPECTED_CUTTER_NAME = "CUT_CLEARANCE_ANATOMY_STRAIGHT"
EXPECTED_VERTEX_COUNT = 408
EXPECTED_FACE_COUNT = 386
EXPECTED_GEOMETRY_FINGERPRINT = (
    "148c9a04b047b02263b72f56836eaaadd86cffdb4f8e26f678a6dae56d8f7d78"
)
MINIMUM_MARGIN_MM = 1.7
MAXIMUM_SAMPLE_SPACING_MM = 1.0
MAXIMUM_ADJACENT_VARIATION_MM = 0.5
MAXIMUM_SUBDIVISIONS = 4096
ROOT = SCRIPT_DIR.parent.parent
METHOD_ROOT = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
CELL_AUTHORITY_PATH = METHOD_ROOT / "v26_cell_authority.json"
EXPECTED_CELL_AUTHORITY_SHA256 = (
    "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca"
)


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
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def argument(name):
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if name not in arguments:
        raise RuntimeError(
            f"{OPERATION}: missing required argument {name}; "
            f"received={arguments}"
        )
    index = arguments.index(name)
    if index + 1 >= len(arguments):
        raise RuntimeError(
            f"{OPERATION}: argument {name} has no value; received={arguments}"
        )
    return arguments[index + 1]


def json_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_list"):
        return value.to_list()
    try:
        return [json_value(item) for item in value]
    except TypeError:
        return str(value)


def point_record(point):
    return [float(coordinate) for coordinate in point]


def evaluated_cutter_provenance(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    try:
        mesh.calc_loop_triangles()
        matrix = evaluated.matrix_world.copy()
        points = [matrix @ vertex.co for vertex in mesh.vertices]
        polygons = [
            tuple(polygon.vertices)
            for polygon in mesh.polygons
        ]
        materials = [
            int(polygon.material_index)
            for polygon in mesh.polygons
        ]
        triangles = [
            tuple(triangle.vertices)
            for triangle in mesh.loop_triangles
        ]
        triangle_polygons = [
            int(triangle.polygon_index)
            for triangle in mesh.loop_triangles
        ]
        signed_volume = sum(
            points[first].dot(
                points[second].cross(points[third])
            )
            for first, second, third in triangles
        ) / 6.0
        orientation_sign = 1.0 if signed_volume >= 0.0 else -1.0
        geometry_payload = {
            "name": obj.name,
            "points": [point_record(point) for point in points],
            "faces": [list(face) for face in polygons],
            "materials": materials,
        }
        geometry_fingerprint = stable_hash(geometry_payload)
        custom_properties = {
            key: json_value(obj[key])
            for key in sorted(obj.keys())
            if key != "_RNA_UI"
        }
        provenance = {
            "object_name": obj.name,
            "source_mesh_datablock_name": obj.data.name,
            "evaluated_object_name": evaluated.name,
            "evaluated_mesh_name": mesh.name,
            "input_blend": str(Path(bpy.data.filepath).resolve()),
            "input_blend_sha256": sha_file(bpy.data.filepath),
            "scene_units": {
                "system": bpy.context.scene.unit_settings.system,
                "scale_length": float(
                    bpy.context.scene.unit_settings.scale_length
                ),
                "length_unit": bpy.context.scene.unit_settings.length_unit,
                "project_convention": "1 Blender unit = 1 mm",
            },
            "object_transform": {
                "matrix_world": [
                    [float(value) for value in row]
                    for row in matrix
                ],
                "location": point_record(obj.location),
                "rotation_mode": obj.rotation_mode,
                "rotation_euler": point_record(obj.rotation_euler),
                "scale": point_record(obj.scale),
            },
            "visibility": {
                "hide_viewport": bool(obj.hide_viewport),
                "hide_render": bool(obj.hide_render),
                "hide_get": bool(obj.hide_get()),
                "visible_get": bool(obj.visible_get()),
            },
            "modifier_stack": [
                {
                    "name": modifier.name,
                    "type": modifier.type,
                    "show_viewport": bool(modifier.show_viewport),
                    "show_render": bool(modifier.show_render),
                }
                for modifier in obj.modifiers
            ],
            "custom_provenance_properties": custom_properties,
            "source_fit_reference_name": custom_properties.get(
                "source_anatomy"
            ),
            "source_fit_reference_names": sorted(
                {
                    str(value)
                    for key, value in custom_properties.items()
                    if "source" in key.lower()
                    or "fit" in key.lower()
                    or "anatom" in key.lower()
                }
            ),
            "vertex_count": len(points),
            "face_count": len(polygons),
            "triangle_count": len(triangles),
            "world_space_vertices_mm": [
                point_record(point) for point in points
            ],
            "world_space_faces": [list(face) for face in polygons],
            "world_space_triangles": [list(face) for face in triangles],
            "triangle_source_polygon_ids": triangle_polygons,
            "materials": materials,
            "world_space_bounding_box_mm": {
                "minimum": [
                    min(point[axis] for point in points)
                    for axis in range(3)
                ],
                "maximum": [
                    max(point[axis] for point in points)
                    for axis in range(3)
                ],
            },
            "signed_orientation": {
                "signed_volume_mm3": float(signed_volume),
                "triangle_winding": (
                    "positive" if orientation_sign > 0.0 else "negative"
                ),
                "outward_normal_multiplier": orientation_sign,
            },
            "geometry_fingerprint": geometry_fingerprint,
        }
        provenance["provenance_fingerprint"] = stable_hash(provenance)
        return provenance, points, triangles, orientation_sign
    finally:
        evaluated.to_mesh_clear()


def closest_segment_points(first_a, first_b, second_a, second_b):
    """Return closest points on two closed 3D segments."""
    epsilon = 1.0e-12
    direction_a = first_b - first_a
    direction_b = second_b - second_a
    offset = first_a - second_a
    aa = direction_a.dot(direction_a)
    bb = direction_b.dot(direction_b)
    ab = direction_a.dot(direction_b)
    ac = direction_a.dot(offset)
    bc = direction_b.dot(offset)
    denominator = aa * bb - ab * ab
    first_parameter = 0.0
    second_parameter = 0.0
    if aa <= epsilon and bb <= epsilon:
        return first_a.copy(), second_a.copy()
    if aa <= epsilon:
        second_parameter = max(0.0, min(1.0, bc / bb))
    else:
        if bb <= epsilon:
            first_parameter = max(0.0, min(1.0, -ac / aa))
        else:
            if denominator > epsilon:
                first_parameter = max(
                    0.0,
                    min(1.0, (ab * bc - ac * bb) / denominator),
                )
            second_parameter = (ab * first_parameter + bc) / bb
            if second_parameter < 0.0:
                second_parameter = 0.0
                first_parameter = max(0.0, min(1.0, -ac / aa))
            elif second_parameter > 1.0:
                second_parameter = 1.0
                first_parameter = max(
                    0.0,
                    min(1.0, (ab - ac) / aa),
                )
    return (
        first_a + direction_a * first_parameter,
        second_a + direction_b * second_parameter,
    )


def triangle_distance(first, second):
    """Exact finite-feature distance for two non-intersecting triangles."""
    best = None

    def retain(point_a, point_b, feature):
        nonlocal best
        distance = (point_a - point_b).length
        record = (distance, point_a.copy(), point_b.copy(), feature)
        if best is None or record[0] < best[0]:
            best = record

    for vertex_id, vertex in enumerate(first):
        closest = closest_point_on_tri(vertex, *second)
        retain(vertex, closest, f"candidate_vertex_{vertex_id}_to_cutter_face")
    for vertex_id, vertex in enumerate(second):
        closest = closest_point_on_tri(vertex, *first)
        retain(closest, vertex, f"cutter_vertex_{vertex_id}_to_candidate_face")
    first_edges = ((0, 1), (1, 2), (2, 0))
    second_edges = ((0, 1), (1, 2), (2, 0))
    for first_edge_id, (first_start, first_end) in enumerate(first_edges):
        for second_edge_id, (second_start, second_end) in enumerate(
            second_edges
        ):
            point_a, point_b = closest_segment_points(
                first[first_start],
                first[first_end],
                second[second_start],
                second[second_end],
            )
            retain(
                point_a,
                point_b,
                f"candidate_edge_{first_edge_id}_to_cutter_edge_"
                f"{second_edge_id}",
            )
    return {
        "distance_mm": float(best[0]),
        "candidate_point_mm": point_record(best[1]),
        "cutter_point_mm": point_record(best[2]),
        "feature_pair": best[3],
    }


def triangle_intersection_witness(first, second):
    """Return an exact shared point for a non-coplanar triangle intersection."""
    edges = ((0, 1), (1, 2), (2, 0))
    for source, target, direction in (
        (first, second, "candidate_edge_through_cutter_face"),
        (second, first, "cutter_edge_through_candidate_face"),
    ):
        for edge_id, (start_id, end_id) in enumerate(edges):
            start = source[start_id]
            edge = source[end_id] - start
            if edge.length <= 1.0e-12:
                continue
            point = intersect_ray_tri(
                target[0],
                target[1],
                target[2],
                edge,
                start,
                True,
            )
            if point is None:
                continue
            parameter = (point - start).dot(edge) / edge.length_squared
            if -1.0e-9 <= parameter <= 1.0 + 1.0e-9:
                return {
                    "distance_mm": 0.0,
                    "candidate_point_mm": point_record(point),
                    "cutter_point_mm": point_record(point),
                    "feature_pair": f"{direction}_{edge_id}",
                }
    return None


def barycentric_lattice(triangle, subdivisions):
    points = {}
    for first_weight in range(subdivisions + 1):
        for second_weight in range(subdivisions + 1 - first_weight):
            third_weight = subdivisions - first_weight - second_weight
            point = (
                triangle[0] * first_weight
                + triangle[1] * second_weight
                + triangle[2] * third_weight
            ) / subdivisions
            points[(first_weight, second_weight)] = point
    adjacency = set()
    neighbor_steps = ((1, 0), (0, 1), (1, -1))
    for key in points:
        for step in neighbor_steps:
            neighbor = (key[0] + step[0], key[1] + step[1])
            if neighbor in points:
                adjacency.add(tuple(sorted((key, neighbor))))
    return points, sorted(adjacency)


def signed_margin(point, cutter_tree, orientation_sign):
    nearest = cutter_tree.find_nearest(point)
    if nearest[0] is None:
        raise RuntimeError(
            f"{OPERATION}: cutter nearest-point query failed for "
            f"sample={point_record(point)}"
        )
    location, normal, triangle_id, distance = nearest
    outward = normal * orientation_sign
    signed = float(distance)
    if (point - location).dot(outward) < 0.0:
        signed = -signed
    return {
        "point_mm": point_record(point),
        "signed_margin_mm": signed,
        "nearest_cutter_triangle_id": int(triangle_id),
        "nearest_cutter_point_mm": point_record(location),
    }


def adaptive_triangle_samples(
    triangle,
    cutter_tree,
    orientation_sign,
):
    edge_lengths = (
        (triangle[1] - triangle[0]).length,
        (triangle[2] - triangle[1]).length,
        (triangle[0] - triangle[2]).length,
    )
    subdivisions = max(
        1,
        int(ceil(max(edge_lengths) / MAXIMUM_SAMPLE_SPACING_MM)),
    )
    refinement_history = []
    while True:
        lattice, adjacency = barycentric_lattice(triangle, subdivisions)
        margins = {
            key: signed_margin(point, cutter_tree, orientation_sign)
            for key, point in lattice.items()
        }
        maximum_variation = max(
            (
                abs(
                    margins[first]["signed_margin_mm"]
                    - margins[second]["signed_margin_mm"]
                )
                for first, second in adjacency
            ),
            default=0.0,
        )
        maximum_edge_step = max(edge_lengths) / subdivisions
        refinement_history.append(
            {
                "subdivisions": subdivisions,
                "maximum_edge_step_mm": float(maximum_edge_step),
                "maximum_adjacent_signed_margin_variation_mm": float(
                    maximum_variation
                ),
                "lattice_sample_count": len(lattice),
            }
        )
        if maximum_variation <= MAXIMUM_ADJACENT_VARIATION_MM:
            break
        if subdivisions >= MAXIMUM_SUBDIVISIONS:
            return {
                "converged": False,
                "rejection_reason": (
                    "adaptive_signed_margin_variation_did_not_converge"
                ),
                "refinement_history": refinement_history,
                "samples": [],
            }
        subdivisions = min(MAXIMUM_SUBDIVISIONS, subdivisions * 2)

    special = {
        "vertex_0": triangle[0],
        "vertex_1": triangle[1],
        "vertex_2": triangle[2],
        "edge_midpoint_0_1": (triangle[0] + triangle[1]) * 0.5,
        "edge_midpoint_1_2": (triangle[1] + triangle[2]) * 0.5,
        "edge_midpoint_2_0": (triangle[2] + triangle[0]) * 0.5,
        "centroid": sum(triangle, Vector()) / 3.0,
    }
    records = [
        {
            "sample_id": f"barycentric_{key[0]}_{key[1]}",
            **margins[key],
        }
        for key in sorted(lattice)
    ]
    records.extend(
        {
            "sample_id": sample_id,
            **signed_margin(point, cutter_tree, orientation_sign),
        }
        for sample_id, point in special.items()
    )
    return {
        "converged": True,
        "rejection_reason": None,
        "refinement_history": refinement_history,
        "samples": records,
    }


def clearance_contract(
    candidate_triangles,
    cutter_points,
    cutter_triangles,
    orientation_sign,
):
    """Evaluate future candidate triangles without modifying Blender data."""
    cutter_tree = BVHTree.FromPolygons(
        cutter_points,
        cutter_triangles,
        all_triangles=True,
    )
    flat_candidate_points = []
    flat_candidate_triangles = []
    for record in candidate_triangles:
        start = len(flat_candidate_points)
        flat_candidate_points.extend(record["points"])
        flat_candidate_triangles.append((start, start + 1, start + 2))
    candidate_tree = BVHTree.FromPolygons(
        flat_candidate_points,
        flat_candidate_triangles,
        all_triangles=True,
    )
    intersection_pairs = sorted(
        [list(pair) for pair in candidate_tree.overlap(cutter_tree)]
    )
    records = []
    for candidate_id, candidate in enumerate(candidate_triangles):
        triangle = candidate["points"]
        triangle_intersections = [
            pair for pair in intersection_pairs if pair[0] == candidate_id
        ]
        nearest = None
        for cutter_id, cutter_face in enumerate(cutter_triangles):
            cutter_triangle = tuple(
                cutter_points[index] for index in cutter_face
            )
            if [candidate_id, cutter_id] in triangle_intersections:
                distance = triangle_intersection_witness(
                    triangle,
                    cutter_triangle,
                )
                if distance is None:
                    raise RuntimeError(
                        f"{OPERATION}: BVH reported an intersection for "
                        f"candidate_triangle={candidate_id}, "
                        f"cutter_triangle={cutter_id}, but no exact segment/"
                        "triangle witness was reproduced"
                    )
            else:
                distance = triangle_distance(triangle, cutter_triangle)
            key = (
                distance["distance_mm"],
                cutter_id,
                distance["feature_pair"],
            )
            if nearest is None or key < nearest[0]:
                nearest = (
                    key,
                    {
                        **distance,
                        "cutter_triangle_id": cutter_id,
                    },
                )
        samples = adaptive_triangle_samples(
            triangle,
            cutter_tree,
            orientation_sign,
        )
        minimum_sample = min(
            (
                sample["signed_margin_mm"]
                for sample in samples["samples"]
            ),
            default=None,
        )
        rejection_reasons = []
        if triangle_intersections:
            rejection_reasons.append("exact_cutter_triangle_intersection")
        if nearest[1]["distance_mm"] < MINIMUM_MARGIN_MM:
            rejection_reasons.append("triangle_distance_below_1.7mm")
        if not samples["converged"]:
            rejection_reasons.append(samples["rejection_reason"])
        if minimum_sample is None or minimum_sample < MINIMUM_MARGIN_MM:
            rejection_reasons.append("signed_sample_margin_below_1.7mm")
        records.append(
            {
                "candidate_triangle_id": candidate["triangle_id"],
                "source_fixture": candidate["source_fixture"],
                "points_mm": [
                    point_record(point) for point in triangle
                ],
                "intersection_pairs": triangle_intersections,
                "minimum_triangle_to_cutter": nearest[1],
                "adaptive_samples": samples,
                "minimum_signed_sample_margin_mm": minimum_sample,
                "rejection_reasons": rejection_reasons,
                "clearance_pass": not rejection_reasons,
            }
        )
    return {
        "contract": {
            "exact_candidate_cutter_triangle_intersections": 0,
            "minimum_triangle_to_triangle_distance_mm": MINIMUM_MARGIN_MM,
            "maximum_barycentric_edge_spacing_mm": (
                MAXIMUM_SAMPLE_SPACING_MM
            ),
            "minimum_signed_sample_margin_mm": MINIMUM_MARGIN_MM,
            "maximum_adjacent_signed_margin_variation_mm": (
                MAXIMUM_ADJACENT_VARIATION_MM
            ),
            "required_special_samples": [
                "three_vertices",
                "three_edge_midpoints",
                "centroid",
            ],
            "pass_uses_unrounded_values": True,
            "visible_shape_generation_from_cutter": False,
        },
        "intersection_pairs": intersection_pairs,
        "triangle_records": records,
        "fixture_triangle_count": len(records),
        "fixture_pass_count": sum(
            record["clearance_pass"] for record in records
        ),
        "fixture_reject_count": sum(
            not record["clearance_pass"] for record in records
        ),
    }


def exact_terminal_face_fixtures(context, cell_authority):
    fixtures = []
    seen = set()
    for terminal in cell_authority["terminal_boundary_coincidence"]["records"]:
        boundary_vertices = set(terminal["ordered_boundary_vertex_ids"])
        for face_id in terminal["candidate_incident_face_ids"]:
            face = context["staged_faces"][face_id]
            if len(boundary_vertices & set(face)) < 2:
                raise RuntimeError(
                    f"{OPERATION}: terminal fixture face {face_id} for "
                    f"{terminal['terminal_id']} does not contain a declared "
                    "boundary edge"
                )
            for fan_id in range(1, len(face) - 1):
                triangle_vertex_ids = (
                    face[0],
                    face[fan_id],
                    face[fan_id + 1],
                )
                key = (face_id, triangle_vertex_ids)
                if key in seen:
                    continue
                seen.add(key)
                fixtures.append(
                    {
                        "triangle_id": (
                            f"{terminal['terminal_id']}:face_{face_id}:"
                            f"fan_{fan_id - 1}"
                        ),
                        "source_fixture": {
                            "kind": "exact_cell_terminal_incident_source_face",
                            "terminal_id": terminal["terminal_id"],
                            "boundary_path_id": terminal["boundary_path_id"],
                            "source_face_id": face_id,
                            "source_vertex_ids": list(triangle_vertex_ids),
                            "declared_boundary_vertex_ids": terminal[
                                "ordered_boundary_vertex_ids"
                            ],
                        },
                        "points": tuple(
                            context["staged_points"][vertex].copy()
                            for vertex in triangle_vertex_ids
                        ),
                    }
                )
    return fixtures


def boundary_sample_fixtures(cell_authority, cutter_tree, orientation_sign):
    records = []
    for terminal in cell_authority["terminal_boundary_coincidence"]["records"]:
        points = [
            Vector(coordinates)
            for coordinates in terminal["exact_source_coordinates_mm"]
        ]
        samples = []
        for edge_id, (first, second) in enumerate(zip(points, points[1:])):
            subdivisions = max(
                1,
                int(
                    ceil(
                        (second - first).length
                        / MAXIMUM_SAMPLE_SPACING_MM
                    )
                ),
            )
            for sample_id in range(subdivisions + 1):
                if edge_id and sample_id == 0:
                    continue
                factor = sample_id / subdivisions
                record = signed_margin(
                    first.lerp(second, factor),
                    cutter_tree,
                    orientation_sign,
                )
                record["edge_id"] = edge_id
                record["edge_parameter"] = factor
                samples.append(record)
        records.append(
            {
                "terminal_id": terminal["terminal_id"],
                "source": "v26_cell_authority exact terminal boundary",
                "maximum_spacing_mm": MAXIMUM_SAMPLE_SPACING_MM,
                "samples": samples,
                "minimum_signed_margin_mm": min(
                    sample["signed_margin_mm"] for sample in samples
                ),
            }
        )
    return records


def main():
    report_path = Path(argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if sha_file(CELL_AUTHORITY_PATH) != EXPECTED_CELL_AUTHORITY_SHA256:
        raise RuntimeError(
            f"{OPERATION}: V26 cell authority mismatch for "
            f"'{CELL_AUTHORITY_PATH}'; actual={sha_file(CELL_AUTHORITY_PATH)}; "
            f"expected={EXPECTED_CELL_AUTHORITY_SHA256}"
        )
    cell_authority = json.loads(
        CELL_AUTHORITY_PATH.read_text(encoding="utf-8")
    )
    context = v17.baseline_context()
    if context["blend_sha"] != EXPECTED_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: input Blend mismatch for "
            f"'{context['blend_path']}'; actual={context['blend_sha']}; "
            f"expected={EXPECTED_BLEND_SHA256}"
        )
    if EXPECTED_CUTTER_NAME not in bpy.data.objects:
        raise RuntimeError(
            f"{OPERATION}: required cutter object "
            f"'{EXPECTED_CUTTER_NAME}' is absent from '{context['blend_path']}'"
        )
    scene_before = {
        "is_dirty": bool(bpy.data.is_dirty),
        "object_names": sorted(obj.name for obj in bpy.data.objects),
        "mesh_names": sorted(mesh.name for mesh in bpy.data.meshes),
    }
    cutter = bpy.data.objects[EXPECTED_CUTTER_NAME]
    provenance, cutter_points, cutter_triangles, orientation_sign = (
        evaluated_cutter_provenance(cutter)
    )
    mismatches = {}
    expected = {
        "input_blend_sha256": EXPECTED_BLEND_SHA256,
        "object_name": EXPECTED_CUTTER_NAME,
        "vertex_count": EXPECTED_VERTEX_COUNT,
        "face_count": EXPECTED_FACE_COUNT,
        "geometry_fingerprint": EXPECTED_GEOMETRY_FINGERPRINT,
        "unit_system": "METRIC",
        "scale_length": 0.001,
    }
    actual = {
        "input_blend_sha256": provenance["input_blend_sha256"],
        "object_name": provenance["object_name"],
        "vertex_count": provenance["vertex_count"],
        "face_count": provenance["face_count"],
        "geometry_fingerprint": provenance["geometry_fingerprint"],
        "unit_system": provenance["scene_units"]["system"],
        "scale_length": provenance["scene_units"]["scale_length"],
    }
    for key, expected_value in expected.items():
        matches = actual[key] == expected_value
        if key == "scale_length":
            matches = abs(actual[key] - expected_value) <= 1.0e-9
        if not matches:
            mismatches[key] = {
                "actual": actual[key],
                "expected": expected_value,
            }
    if mismatches:
        raise RuntimeError(
            f"{OPERATION}: CUTTER_PROVENANCE_MISMATCH_V26 for "
            f"'{EXPECTED_CUTTER_NAME}'; mismatches={mismatches}"
        )
    provenance_checkpoint = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": "V26_CUTTER_PROVENANCE_CHECKPOINTED",
        "code_sha256": sha_file(Path(__file__)),
        "cell_authority_sha256": EXPECTED_CELL_AUTHORITY_SHA256,
        "cutter_provenance": provenance,
        "clearance_fixtures_started": False,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "visible_shape_generated_from_cutter": False,
        "promotion": "NOT_PROMOTED",
    }
    provenance_checkpoint["report_semantic_fingerprint"] = stable_hash(
        provenance_checkpoint
    )
    atomic_json(report_path, provenance_checkpoint)
    fixtures = exact_terminal_face_fixtures(context, cell_authority)
    clearance = clearance_contract(
        fixtures,
        cutter_points,
        cutter_triangles,
        orientation_sign,
    )
    cutter_tree = BVHTree.FromPolygons(
        cutter_points,
        cutter_triangles,
        all_triangles=True,
    )
    boundary_fixtures = boundary_sample_fixtures(
        cell_authority,
        cutter_tree,
        orientation_sign,
    )
    scene_after = {
        "is_dirty": bool(bpy.data.is_dirty),
        "object_names": sorted(obj.name for obj in bpy.data.objects),
        "mesh_names": sorted(mesh.name for mesh in bpy.data.meshes),
    }
    if scene_after != scene_before:
        raise RuntimeError(
            f"{OPERATION}: read-only scene invariant changed; "
            f"before={scene_before}; after={scene_after}"
        )
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": "V26_CUTTER_AUTHORITY_CHECKPOINTED",
        "code_sha256": sha_file(Path(__file__)),
        "checkpoint_sequence": [
            "V26_CUTTER_PROVENANCE_CHECKPOINTED",
            "V26_CUTTER_AUTHORITY_CHECKPOINTED",
        ],
        "provenance_persisted_before_clearance_fixtures": True,
        "cell_authority": {
            "path": str(CELL_AUTHORITY_PATH),
            "sha256": EXPECTED_CELL_AUTHORITY_SHA256,
            "fingerprint": cell_authority["fingerprint"],
        },
        "cutter_provenance": provenance,
        "future_candidate_clearance_api": {
            "entry_point": "clearance_contract",
            "triangle_distance_entry_point": "triangle_distance",
            "adaptive_sample_entry_point": "adaptive_triangle_samples",
            "input_coordinates": "world-space millimeters",
            "candidate_geometry_source": (
                "future source-boundary-controlled candidates only"
            ),
            "cutter_role": "rejection and hidden minimum-floor target only",
            "deterministic_ordering": (
                "caller triangle order, cutter loop-triangle order, sorted "
                "barycentric integer coordinates"
            ),
        },
        "exact_terminal_source_face_fixtures": clearance,
        "exact_terminal_boundary_sample_fixtures": boundary_fixtures,
        "fixture_interpretation": (
            "Fixtures audit existing exact source authority and are not V26 "
            "candidate geometry; fixture rejection does not classify a future "
            "candidate."
        ),
        "source_scene_invariant": {
            "unchanged": True,
            "before": scene_before,
            "after": scene_after,
        },
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "visible_shape_generated_from_cutter": False,
        "promotion": "NOT_PROMOTED",
    }
    report["report_semantic_fingerprint"] = stable_hash(report)
    atomic_json(report_path, report)
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "status": report["status"],
                "report": str(report_path),
                "cutter": {
                    "vertices": provenance["vertex_count"],
                    "faces": provenance["face_count"],
                    "triangles": provenance["triangle_count"],
                    "geometry_fingerprint": provenance[
                        "geometry_fingerprint"
                    ],
                },
                "fixture_triangle_count": clearance[
                    "fixture_triangle_count"
                ],
                "fixture_pass_count": clearance["fixture_pass_count"],
                "fixture_reject_count": clearance["fixture_reject_count"],
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
    )
    print(
        "DONE: V26 exact cutter authority and future-candidate clearance "
        "contract checkpointed; mutation_started=False; "
        "geometry_emitted=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
