"""Validate the cleaned millimeter-native Silverhand master scene."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import bmesh
import bpy


EXPECTED_COLLECTIONS = (
    "00_SOURCE_LOCKED",
    "10_FIT_TOOLS",
    "20_SALVAGE_WORKING",
    "30_REVIEW",
    "40_DEFERRED_ARMOR",
)
EXPECTED_SOURCE_OBJECTS = (
    "SRC_GAME_RAW",
    "SRC_GAME_FITTED",
    "SRC_DEFORMED_FULL_BASELINE",
    "SRC_GAME_TPU_ONLY_BASELINE",
)
EXPECTED_DETAIL_COUNT = 101
EXPECTED_VALIDATION_CAMERAS = (
    "VAL_CAM_DORSAL",
    "VAL_CAM_VENTRAL",
    "VAL_CAM_MEDIAL",
    "VAL_CAM_LATERAL",
    "VAL_CAM_DORSAL_LATERAL_THREE_QUARTER",
    "VAL_CAM_VENTRAL_MEDIAL_THREE_QUARTER",
    "VAL_CAM_WRIST_AXIAL",
    "VAL_CAM_BICEP_AXIAL",
)
VALIDATION_RIG_VERSION = 1


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


def inspect_mesh(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    report = {
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "components": connected_components(bm),
        "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
        "nonmanifold_edges": sum(not edge.is_manifold for edge in bm.edges),
        "signed_volume_mm3": round(bm.calc_volume(signed=True), 6),
    }
    bm.free()
    return report


def geometry_fingerprint(objects: list[bpy.types.Object]) -> str:
    digest = hashlib.sha256()
    for obj in sorted(objects, key=lambda value: value.name):
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


scene = bpy.context.scene
issues: list[str] = []

if scene.unit_settings.system != "METRIC":
    issues.append(
        f"SCENE_UNITS: expected METRIC, got {scene.unit_settings.system!r}"
    )
if abs(scene.unit_settings.scale_length - 0.001) > 1e-9:
    issues.append(
        "SCENE_SCALE: expected scale_length=0.001 for millimeters, "
        f"got {scene.unit_settings.scale_length}"
    )
if scene.unit_settings.length_unit != "MILLIMETERS":
    issues.append(
        "DISPLAY_UNITS: expected MILLIMETERS, "
        f"got {scene.unit_settings.length_unit!r}"
    )

missing_collections = [
    name for name in EXPECTED_COLLECTIONS if bpy.data.collections.get(name) is None
]
if missing_collections:
    issues.append(
        "SCENE_COLLECTIONS: missing required collections "
        + ", ".join(missing_collections)
    )

missing_sources = [
    name for name in EXPECTED_SOURCE_OBJECTS if bpy.data.objects.get(name) is None
]
if missing_sources:
    issues.append(
        "SOURCE_EVIDENCE: missing required objects " + ", ".join(missing_sources)
    )

camera_collection = bpy.data.collections.get("90_VALIDATION_CAMERAS")
if camera_collection is not None:
    camera_failures = []
    for name in EXPECTED_VALIDATION_CAMERAS:
        camera = bpy.data.objects.get(name)
        if camera is None:
            camera_failures.append(f"missing '{name}'")
            continue
        if camera.type != "CAMERA":
            camera_failures.append(
                f"'{name}' has type '{camera.type}', expected 'CAMERA'"
            )
            continue
        if camera_collection.objects.get(name) is None:
            camera_failures.append(
                f"'{name}' is not linked to '90_VALIDATION_CAMERAS'"
            )
        if camera.get("validation_rig_version") != VALIDATION_RIG_VERSION:
            camera_failures.append(
                f"'{name}' has validation_rig_version="
                f"{camera.get('validation_rig_version')!r}, expected "
                f"{VALIDATION_RIG_VERSION}"
            )
        if camera.get("matching_camera") is not True:
            camera_failures.append(
                f"'{name}' must declare matching_camera=true"
            )
        if camera.get("printable") is not False:
            camera_failures.append(f"'{name}' must declare printable=false")
    if camera_failures:
        issues.append(
            "VALIDATION_CAMERAS: " + "; ".join(camera_failures)
        )

salvage = bpy.data.collections.get("20_SALVAGE_WORKING")
details = (
    sorted(
        (
            obj
            for obj in salvage.all_objects
            if obj.type == "MESH" and obj.name.startswith("REG_")
        ),
        key=lambda obj: obj.name,
    )
    if salvage
    else []
)
if len(details) != EXPECTED_DETAIL_COUNT:
    issues.append(
        f"SALVAGE_COUNT: expected {EXPECTED_DETAIL_COUNT} detail solids, "
        f"found {len(details)}"
    )

detail_reports = {}
invalid_details = {}
for obj in details:
    report = inspect_mesh(obj)
    detail_reports[obj.name] = report
    failures = []
    if report["vertices"] == 0 or report["faces"] == 0:
        failures.append("empty geometry")
    if report["boundary_edges"]:
        failures.append(f"{report['boundary_edges']} boundary edges")
    if report["nonmanifold_edges"]:
        failures.append(f"{report['nonmanifold_edges']} non-manifold edges")
    if report["signed_volume_mm3"] <= 0.0:
        failures.append(
            f"non-positive signed volume {report['signed_volume_mm3']} mm³"
        )
    if obj.data.users != 1:
        failures.append(f"mesh datablock has {obj.data.users} object users")
    if failures:
        invalid_details[obj.name] = failures

if invalid_details:
    issues.append(
        f"SALVAGE_GEOMETRY: {len(invalid_details)} invalid detail solids; "
        "inspect invalid_details in the JSON report"
    )

clearance = bpy.data.objects.get("CUT_CLEARANCE_BASELINE")
fit_reference = bpy.data.objects.get("REF_FIT_VOLUME_BASELINE")
for role, obj in (
    ("CLEARANCE_CUTTER", clearance),
    ("FIT_REFERENCE", fit_reference),
):
    if obj is None:
        issues.append(f"{role}: required object is missing")
    elif obj.get("printable") is not False:
        issues.append(
            f"{role}: '{obj.name}' must explicitly declare printable=false"
        )

review = bpy.data.objects.get("EVAL_MAIN_GEOMETRY_BASELINE")
if review is None:
    issues.append("REVIEW_BASELINE: EVAL_MAIN_GEOMETRY_BASELINE is missing")
elif review.get("print_ready") is not False:
    issues.append(
        "REVIEW_BASELINE: joined review object must declare print_ready=false"
    )

missing_files = []
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        path = Path(bpy.path.abspath(image.filepath))
        if not path.is_file():
            missing_files.append(str(path))
if missing_files:
    issues.append(
        f"EXTERNAL_FILES: {len(missing_files)} image files are missing"
    )

orphans = {
    "meshes": sum(mesh.users == 0 for mesh in bpy.data.meshes),
    "cameras": sum(camera.users == 0 for camera in bpy.data.cameras),
    "curves": sum(curve.users == 0 for curve in bpy.data.curves),
    "images": sum(image.users == 0 for image in bpy.data.images),
}
if any(orphans.values()):
    issues.append(f"ORPHANS: unused datablocks remain: {orphans}")

region_counts = Counter(
    str(obj.get("construction_region", "UNASSIGNED")) for obj in details
)
report = {
    "blend_file": bpy.data.filepath,
    "passed": not issues,
    "issues": issues,
    "units": {
        "system": scene.unit_settings.system,
        "scale_length": scene.unit_settings.scale_length,
        "length_unit": scene.unit_settings.length_unit,
    },
    "scene": {
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "collections": len(bpy.data.collections),
        "cameras": len(bpy.data.cameras),
        "images": len(bpy.data.images),
        "orphans": orphans,
    },
    "salvage": {
        "detail_count": len(details),
        "region_counts": dict(sorted(region_counts.items())),
        "geometry_fingerprint": geometry_fingerprint(details) if details else None,
        "invalid_details": invalid_details,
        "total_vertices": sum(value["vertices"] for value in detail_reports.values()),
        "total_faces": sum(value["faces"] for value in detail_reports.values()),
        "summed_signed_volume_mm3": round(
            sum(value["signed_volume_mm3"] for value in detail_reports.values()),
            3,
        ),
    },
    "review": {
        "object": review.name if review else None,
        "dimensions_mm": (
            [round(float(value), 3) for value in review.dimensions]
            if review
            else None
        ),
    },
    "missing_external_files": missing_files,
}

print(json.dumps(report, indent=2))
raise SystemExit(0 if report["passed"] else 1)
