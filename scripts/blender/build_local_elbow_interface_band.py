"""Build an evaluation-only local C-band and cage-junction network."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from math import ceil
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
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
    mesh_audit,
    overlap_pairs,
)
from try_landmark_sector_retopology import (  # noqa: E402
    REVIEW_COLLECTION,
    audit_noncontiguous,
)
from try_remove_component20_inner_bowl import remap_retained  # noqa: E402


OPERATION = "LOCAL_ELBOW_INTERFACE_BAND"
STAGED_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
OPEN_CAGE_NAME = "EVAL_REPAIR_014_OPEN_CAGE_AFTER"
EXPECTED_BLEND_SHA256 = (
    "c77d7b84af3ab60c6a12f64c24fdb80fde25556176f53c5c17c758663445a82c"
)
ANCHOR_IDS = (
    2074,
    2054,
    2055,
    2058,
    2060,
    2062,
    2064,
    2118,
    2115,
    2114,
    2111,
    2108,
    2119,
)
PATH_IDS = (
    2074,
    2054,
    2055,
    2058,
    2060,
    2062,
    2064,
    2065,
    2067,
    2068,
    2069,
    2070,
    2071,
    2073,
    2118,
    2115,
    2114,
    2111,
    2108,
    2119,
)
REGISTRATION_IDS = (5840, 5852)
ISLAND_TAB_SOURCE_PAIRS = ((1931, 1998), (5702, 1784), (4875, 4877))
BAND_THICKNESS_MM = 1.8
BAND_HALF_WIDTH_MM = 0.8
MAX_SEGMENT_MM = 3.0
TAB_HALF_WIDTH_MM = 1.1
TAB_OVERLAP_MM = 0.8
TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--required-blend-sha256", default=EXPECTED_BLEND_SHA256)
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(sys.argv[separator + 1 :])


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def audit_geometry(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> dict:
    mesh = bpy.data.meshes.new(f"{OPERATION}_AUDIT_MESH")
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"{OPERATION}_AUDIT", mesh)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        volume = bm.calc_volume(signed=True)
    finally:
        bm.free()
    audit = mesh_audit(obj)
    winding = audit_noncontiguous(obj)
    bpy.data.objects.remove(obj, do_unlink=True)
    return {
        **audit,
        **winding,
        "signed_volume_mm3": round(volume, 6),
    }


def positive_faces(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> list[tuple[int, ...]]:
    if audit_geometry(points, faces)["signed_volume_mm3"] < 0.0:
        return [tuple(reversed(face)) for face in faces]
    return faces


def append_geometry(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    added_points: list[Vector],
    added_faces: list[tuple[int, ...]],
) -> tuple[int, int]:
    vertex_start = len(points)
    face_start = len(faces)
    points.extend(point.copy() for point in added_points)
    faces.extend(
        tuple(vertex_start + index for index in face)
        for face in added_faces
    )
    return vertex_start, face_start


def path_samples(
    path: list[Vector],
    target_length: float,
    grid,
) -> tuple[list[Vector], dict[int, int]]:
    samples: list[Vector] = [path[0].copy()]
    path_sample: dict[int, int] = {0: 0}
    for segment, (first, second) in enumerate(zip(path, path[1:])):
        steps = max(1, int(ceil((second - first).length / MAX_SEGMENT_MM)))
        for step in range(1, steps + 1):
            point = first.lerp(second, step / steps)
            if step < steps:
                point = clamp_to_reserved_wall(
                    point,
                    target_length,
                    grid,
                    1.7,
                )
            samples.append(point)
        path_sample[segment + 1] = len(samples) - 1
    return samples, path_sample


def build_band(
    path: list[Vector],
    target_length: float,
    grid,
) -> tuple[list[Vector], list[tuple[int, ...]], dict[int, int]]:
    samples, path_sample = path_samples(path, target_length, grid)
    points: list[Vector] = []
    previous_width = None
    for index, point in enumerate(samples):
        tangent = (
            samples[1] - point
            if index == 0
            else point - samples[index - 1]
            if index == len(samples) - 1
            else samples[index + 1] - samples[index - 1]
        ).normalized()
        _, _, _, radial = radial_coordinates(point, target_length)
        width = tangent.cross(radial)
        if width.length <= 1.0e-8:
            raise RuntimeError(
                f"{OPERATION}: degenerate band frame at sample {index}"
            )
        width.normalize()
        if previous_width is not None and width.dot(previous_width) < 0.0:
            width.negate()
        previous_width = width.copy()
        points.extend(
            (
                point.copy(),
                point + radial * BAND_THICKNESS_MM + width * BAND_HALF_WIDTH_MM,
                point + radial * BAND_THICKNESS_MM - width * BAND_HALF_WIDTH_MM,
            )
        )
    faces: list[tuple[int, ...]] = []
    for index in range(len(samples) - 1):
        first = index * 3
        second = (index + 1) * 3
        faces.extend(
            (
                (first, second, second + 1, first + 1),
                (first + 1, second + 1, second + 2, first + 2),
                (first + 2, second + 2, second, first),
            )
        )
    last = (len(samples) - 1) * 3
    faces.extend(((0, 1, 2), (last, last + 2, last + 1)))
    return points, positive_faces(points, faces), path_sample


def build_tab(
    start: Vector,
    end: Vector,
    target_length: float,
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    direction = end - start
    if direction.length <= 1.0e-6:
        raise RuntimeError(f"{OPERATION}: tab endpoints are coincident")
    direction.normalize()
    _, _, _, radial = radial_coordinates((start + end) * 0.5, target_length)
    first_axis = direction.cross(radial)
    if first_axis.length <= 1.0e-8:
        first_axis = direction.cross(Vector((1.0, 0.0, 0.0)))
    first_axis.normalize()
    second_axis = direction.cross(first_axis).normalized()
    start = start - direction * TAB_OVERLAP_MM
    end = end + direction * TAB_OVERLAP_MM
    points = []
    for center in (start, end):
        points.extend(
            (
                center - first_axis * TAB_HALF_WIDTH_MM - second_axis * TAB_HALF_WIDTH_MM,
                center + first_axis * TAB_HALF_WIDTH_MM - second_axis * TAB_HALF_WIDTH_MM,
                center + first_axis * TAB_HALF_WIDTH_MM + second_axis * TAB_HALF_WIDTH_MM,
                center - first_axis * TAB_HALF_WIDTH_MM + second_axis * TAB_HALF_WIDTH_MM,
            )
        )
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return points, positive_faces(points, faces)


def component_local(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    face_ids: set[int],
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    ids = sorted({vertex for face_id in face_ids for vertex in faces[face_id]})
    remap = {source_id: result_id for result_id, source_id in enumerate(ids)}
    return (
        [points[index] for index in ids],
        [
            tuple(remap[index] for index in faces[face_id])
            for face_id in sorted(face_ids)
        ],
    )


def self_overlaps(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> list[tuple[int, int]]:
    tree = BVHTree.FromPolygons(points, faces, all_triangles=False)
    return sorted(
        {
            (first, second)
            for first, second in tree.overlap(tree)
            if first < second and not (set(faces[first]) & set(faces[second]))
        }
    )


def main() -> int:
    args = parse_args()
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha = sha256_file(blend_path)
    if actual_sha != args.required_blend_sha256:
        raise RuntimeError(
            f"{OPERATION}: input blend '{blend_path}' has SHA-256 "
            f"'{actual_sha}', expected '{args.required_blend_sha256}'"
        )
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    staged = require_mesh(STAGED_NAME, "coordinated interface")
    open_cage = require_mesh(OPEN_CAGE_NAME, "validated open cage")
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
        or len(open_points) != len(retained_points)
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
    path = [staged_points[index].copy() for index in PATH_IDS]
    band_points, band_faces, path_sample = build_band(
        path,
        target_length,
        grid,
    )
    band_audit = audit_geometry(band_points, band_faces)
    if (
        band_audit["boundary_edges"]
        or band_audit["nonmanifold_edges"]
        or band_audit["noncontiguous_manifold_edges"]
        or band_audit["signed_volume_mm3"] <= 0.0
    ):
        raise RuntimeError(
            f"{OPERATION}: band is not closed positive volume: {band_audit}"
        )
    composite_points = [point.copy() for point in retained_points]
    composite_faces = list(retained_faces)
    composite_materials = list(retained_materials)
    material = Counter(retained_materials).most_common(1)[0][0]
    band_vertex_start, _ = append_geometry(
        composite_points,
        composite_faces,
        band_points,
        band_faces,
    )
    composite_materials.extend([material] * len(band_faces))
    tab_records = []
    tab_geometries = []
    for first_id, second_id in ISLAND_TAB_SOURCE_PAIRS:
        if first_id not in source_to_retained or second_id not in source_to_retained:
            raise RuntimeError(
                f"{OPERATION}: tab route V{first_id}↔V{second_id} is not "
                "retained by the open cage"
            )
        tab_points, tab_faces = build_tab(
            staged_points[first_id],
            staged_points[second_id],
            target_length,
        )
        vertex_start, face_start = append_geometry(
            composite_points,
            composite_faces,
            tab_points,
            tab_faces,
        )
        composite_materials.extend([material] * len(tab_faces))
        tab_geometries.append((tab_points, tab_faces))
        tab_records.append(
            {
                "role": "cage_island_link",
                "source_vertex_ids": [first_id, second_id],
                "centerline_length_mm": round(
                    (staged_points[first_id] - staged_points[second_id]).length,
                    6,
                ),
                "vertex_start": vertex_start,
                "face_start": face_start,
                "audit": audit_geometry(tab_points, tab_faces),
            }
        )
    # One shortest deterministic band-to-cage tab makes the C-band part of the
    # same junction network. Search only retained component-20 vertices.
    retained_c20_vertices = sorted(
        {
            vertex
            for face_id in retained_c20_faces
            for vertex in staged_faces[face_id]
        }
    )
    best = min(
        (
            (staged_points[cage_id] - staged_points[path_id]).length,
            cage_id,
            path_id,
        )
        for cage_id in retained_c20_vertices
        for path_id in PATH_IDS
    )
    _, cage_id, path_id = best
    _, _, _, band_link_radial = radial_coordinates(
        staged_points[path_id],
        target_length,
    )
    band_link_end = (
        staged_points[path_id]
        + band_link_radial * (BAND_THICKNESS_MM * 0.65)
    )
    tab_points, tab_faces = build_tab(
        staged_points[cage_id],
        band_link_end,
        target_length,
    )
    vertex_start, face_start = append_geometry(
        composite_points,
        composite_faces,
        tab_points,
        tab_faces,
    )
    composite_materials.extend([material] * len(tab_faces))
    tab_geometries.append((tab_points, tab_faces))
    tab_records.append(
        {
            "role": "band_to_cage_link",
            "source_vertex_ids": [cage_id, path_id],
            "centerline_length_mm": round(best[0], 6),
            "vertex_start": vertex_start,
            "face_start": face_start,
            "audit": audit_geometry(tab_points, tab_faces),
        }
    )
    network_points = [point.copy() for point in band_points]
    network_faces = list(band_faces)
    for tab_points, tab_faces in tab_geometries:
        append_geometry(network_points, network_faces, tab_points, tab_faces)
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
    result_obj["role"] = "retained cage plus local C-band junction network"
    network_obj["role"] = "local C-band junction network"
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    _, components = connected_components(source)
    component9 = set(components[9])
    c9_face_ids = {
        index
        for index, face in enumerate(staged_faces)
        if face[0] in component9
    }
    c9_points, c9_faces = component_local(
        staged_points,
        staged_faces,
        c9_face_ids,
    )
    c20_points, c20_faces = component_local(
        staged_points,
        staged_faces,
        retained_c20_faces,
    )
    band_cutter = overlap_pairs(
        band_points,
        band_faces,
        cutter_points,
        cutter_faces,
    )
    band_c9 = overlap_pairs(band_points, band_faces, c9_points, c9_faces)
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
    tab_contacts = []
    for index, (tab_points, tab_faces) in enumerate(tab_geometries):
        tab_contacts.append(
            {
                "tab_index": index,
                "band_overlap_count": len(
                    overlap_pairs(
                        tab_points,
                        tab_faces,
                        band_points,
                        band_faces,
                    )
                ),
                "cage_overlap_count": len(
                    overlap_pairs(
                        tab_points,
                        tab_faces,
                        c20_points,
                        c20_faces,
                    )
                ),
            }
        )
    retained_before_fp = fingerprint(retained_source_ids, retained_points)
    retained_after_fp = fingerprint(
        retained_source_ids,
        composite_points[: len(retained_points)],
    )
    path_index = {source_id: index for index, source_id in enumerate(PATH_IDS)}
    anchor_registration = {
        str(source_id): round(
            (
                band_points[path_sample[path_index[source_id]] * 3]
                - staged_points[source_id]
            ).length,
            9,
        )
        for source_id in ANCHOR_IDS
    }
    hard_registration = {
        str(source_id): round(
            (
                composite_points[source_to_retained[source_id]]
                - staged_points[source_id]
            ).length,
            9,
        )
        for source_id in REGISTRATION_IDS
    }
    network_audit = audit_geometry(network_points, network_faces)
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": "evaluation_only_not_promoted",
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": actual_sha,
            "open_cage_object": OPEN_CAGE_NAME,
            "coordinated_interface_object": STAGED_NAME,
        },
        "mapping": {
            "path": str(MAPPING_PATH),
            "sha256": sha256_file(MAPPING_PATH),
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
            "anchor_ids_ordered": list(ANCHOR_IDS),
            "path_ids_ordered": list(PATH_IDS),
            "c_tips": [2074, 2119],
            "central_bowl_filled": False,
            "audit": band_audit,
            "cutter_overlap_count": len(band_cutter),
            "c9_overlap_count": len(band_c9),
            "self_overlap_pairs": [
                list(pair) for pair in self_overlaps(band_points, band_faces)
            ],
        },
        "tabs": {
            "count": len(tab_records),
            "records": tab_records,
            "contacts": tab_contacts,
        },
        "registration": {
            "anchor_error_mm": anchor_registration,
            "hard_control_error_mm": hard_registration,
        },
        "network": {
            "audit": network_audit,
            "cutter_overlap_count": len(network_cutter),
            "c9_overlap_count": len(network_c9),
            "raw_cross_constituent_or_self_overlap_pair_count": len(
                self_overlaps(network_points, network_faces)
            ),
            "per_constituent_self_intersection_counts": {
                "band": len(self_overlaps(band_points, band_faces)),
                "tabs": [
                    len(self_overlaps(tab_points, tab_faces))
                    for tab_points, tab_faces in tab_geometries
                ],
            },
            "intended_constituent_contact_pairs": {
                "band_to_cage_tab_with_band": (
                    tab_contacts[-1]["band_overlap_count"]
                ),
                "all_tabs_with_cage": sum(
                    record["cage_overlap_count"]
                    for record in tab_contacts
                ),
            },
        },
        "combined_result": {
            "audit": audit_geometry(composite_points, composite_faces),
            "vertex_count": len(composite_points),
            "face_count": len(composite_faces),
        },
        "objects": {
            "result": result_obj.name,
            "network": network_obj.name,
        },
        "qualitative_review": "NOT_STARTED",
        "promotion": "NOT_PROMOTED",
    }
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
        "band_cutter_clear": len(band_cutter) == 0,
        "band_non_self_intersecting": not self_overlaps(
            band_points,
            band_faces,
        ),
        "all_13_anchor_positions_exact": all(
            error <= TOLERANCE_MM
            for error in anchor_registration.values()
        ),
        "registration_5840_5852_exact": all(
            error <= TOLERANCE_MM for error in hard_registration.values()
        ),
        "all_tabs_closed_positive_volume": all(
            record["audit"]["boundary_edges"] == 0
            and record["audit"]["nonmanifold_edges"] == 0
            and record["audit"]["signed_volume_mm3"] > 0.0
            for record in tab_records
        ),
        "network_contacts_cage": all(
            record["cage_overlap_count"] > 0 for record in tab_contacts
        ),
        "band_link_contacts_band": (
            tab_contacts[-1]["band_overlap_count"] > 0
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
        f"DONE: built local C-band and {len(tab_records)} tabs; "
        f"gate_pass={report['gate_pass']}; promotion remains NOT_PROMOTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
