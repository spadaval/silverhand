"""Canonical semantic camera rig shared by validation scripts."""

from __future__ import annotations

from mathutils import Vector

import bpy


COLLECTION_NAME = "90_VALIDATION_CAMERAS"
RIG_VERSION = 1
DEFAULT_SOURCE = "SRC_GAME_TPU_ONLY_BASELINE"
DEFAULT_TARGET = "EVAL_MAIN_GEOMETRY_BASELINE"

# Millimeter migration preserved orientation. These are anatomical directions,
# not dimensions or a duplicated fit profile.
ARM_AXIS = Vector((-0.435269, 0.622288, 0.650614)).normalized()
DORSAL = Vector((0.0, 0.0, 1.0))
DORSAL -= ARM_AXIS * DORSAL.dot(ARM_AXIS)
DORSAL.normalize()
LATERAL = ARM_AXIS.cross(DORSAL).normalized()

VIEW_DIRECTIONS = {
    "dorsal": DORSAL,
    "ventral": -DORSAL,
    "medial": -LATERAL,
    "lateral": LATERAL,
    "dorsal_lateral_three_quarter": (DORSAL + LATERAL).normalized(),
    "ventral_medial_three_quarter": (-DORSAL - LATERAL).normalized(),
    "wrist_axial": -ARM_AXIS,
    "bicep_axial": ARM_AXIS,
}


def camera_name(view_name: str) -> str:
    return f"VAL_CAM_{view_name.upper()}"


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot build validation cameras: {role} object '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot build validation cameras: {role} object '{name}' has type "
            f"'{obj.type}', expected 'MESH'"
        )
    return obj


def evaluated_world_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            raise RuntimeError(
                f"Cannot build validation cameras: object '{obj.name}' has no "
                "vertices"
            )
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def fit_shared_camera(
    camera: bpy.types.Object,
    points: list[Vector],
    view_direction: Vector,
    aspect: float,
    margin: float,
) -> dict:
    direction = view_direction.normalized()
    rotation = (-direction).to_track_quat("-Z", "Y")
    right = rotation @ Vector((1.0, 0.0, 0.0))
    up = rotation @ Vector((0.0, 1.0, 0.0))
    depth = rotation @ Vector((0.0, 0.0, -1.0))

    right_values = [point.dot(right) for point in points]
    up_values = [point.dot(up) for point in points]
    depth_values = [point.dot(depth) for point in points]
    center = (
        right * ((min(right_values) + max(right_values)) * 0.5)
        + up * ((min(up_values) + max(up_values)) * 0.5)
        + depth * ((min(depth_values) + max(depth_values)) * 0.5)
    )
    width = max(right_values) - min(right_values)
    height = max(up_values) - min(up_values)
    depth_span = max(depth_values) - min(depth_values)
    ortho_scale = max(height, width / aspect) * margin
    distance = max(ortho_scale, depth_span, 1.0) * 2.0

    camera.location = center + direction * distance
    camera.rotation_euler = (center - camera.location).to_track_quat(
        "-Z", "Y"
    ).to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    camera.data.clip_start = 0.1
    camera.data.clip_end = distance * 4.0
    return {
        "direction": [round(float(value), 9) for value in direction],
        "location_mm": [
            round(float(value), 6) for value in camera.location
        ],
        "rotation_euler_radians": [
            round(float(value), 9) for value in camera.rotation_euler
        ],
        "ortho_scale_mm": round(float(ortho_scale), 6),
    }


def build_camera_rig(
    source: bpy.types.Object,
    target: bpy.types.Object,
    resolution_x: int,
    resolution_y: int,
    margin: float,
) -> tuple[dict[str, bpy.types.Object], dict[str, dict]]:
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)

    points = evaluated_world_points(source) + evaluated_world_points(target)
    aspect = resolution_x / resolution_y
    cameras = {}
    records = {}
    for order, (view_name, direction) in enumerate(
        VIEW_DIRECTIONS.items(),
        start=1,
    ):
        name = camera_name(view_name)
        camera = bpy.data.objects.get(name)
        if camera is not None and camera.type != "CAMERA":
            raise RuntimeError(
                f"Cannot build validation cameras: object '{name}' exists with "
                f"type '{camera.type}', expected 'CAMERA'"
            )
        if camera is None:
            camera_data = bpy.data.cameras.new(f"{name}_DATA")
            camera = bpy.data.objects.new(name, camera_data)
            collection.objects.link(camera)
        elif collection.objects.get(name) is None:
            collection.objects.link(camera)

        record = fit_shared_camera(
            camera,
            points,
            direction,
            aspect,
            margin,
        )
        camera["validation_rig_version"] = RIG_VERSION
        camera["semantic_view"] = view_name
        camera["review_order"] = order
        camera["source_object"] = source.name
        camera["target_object"] = target.name
        camera["matching_camera"] = True
        camera["printable"] = False
        camera["framing_resolution_x"] = resolution_x
        camera["framing_resolution_y"] = resolution_y
        camera["framing_margin"] = margin
        cameras[view_name] = camera
        records[view_name] = record

    return cameras, records


def require_camera_rig() -> dict[str, bpy.types.Object]:
    cameras = {}
    failures = []
    for view_name in VIEW_DIRECTIONS:
        name = camera_name(view_name)
        camera = bpy.data.objects.get(name)
        if camera is None:
            failures.append(f"missing '{name}'")
            continue
        if camera.type != "CAMERA":
            failures.append(f"'{name}' has type '{camera.type}'")
            continue
        if camera.get("validation_rig_version") != RIG_VERSION:
            failures.append(
                f"'{name}' has rig version "
                f"{camera.get('validation_rig_version')!r}, expected "
                f"{RIG_VERSION}"
            )
            continue
        if camera.get("semantic_view") != view_name:
            failures.append(
                f"'{name}' declares semantic view "
                f"{camera.get('semantic_view')!r}, expected '{view_name}'"
            )
            continue
        cameras[view_name] = camera
    if failures:
        raise RuntimeError(
            "Cannot render geometry comparison: canonical camera rig is "
            "incomplete or stale ("
            + "; ".join(failures)
            + "). Run './scripts/tools/sync_validation_cameras.sh' first."
        )
    return cameras


def camera_record(camera: bpy.types.Object) -> dict:
    direction = camera.rotation_euler.to_matrix() @ Vector((0.0, 0.0, 1.0))
    return {
        "camera": camera.name,
        "direction": [round(float(value), 9) for value in direction],
        "location_mm": [
            round(float(value), 6) for value in camera.location
        ],
        "rotation_euler_radians": [
            round(float(value), 9) for value in camera.rotation_euler
        ],
        "ortho_scale_mm": round(float(camera.data.ortho_scale), 6),
    }
