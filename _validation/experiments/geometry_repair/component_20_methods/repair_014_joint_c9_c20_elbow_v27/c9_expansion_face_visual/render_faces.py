"""Render the bounded V27 C9 expansion-face set without saving the Blend."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


OBJECT_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
FACE_IDS = [2220, 2221, 2222, 2224, 2225, 2226, 2233, 2284]
COLORS = [
    (1.0, 0.04, 0.02, 1.0),
    (1.0, 0.42, 0.01, 1.0),
    (1.0, 0.90, 0.01, 1.0),
    (0.18, 1.0, 0.04, 1.0),
    (0.01, 0.95, 0.95, 1.0),
    (0.02, 0.28, 1.0, 1.0),
    (0.68, 0.05, 1.0, 1.0),
    (1.0, 0.03, 0.58, 1.0),
]


def args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def material(name: str, rgba: tuple[float, float, float, float]):
    value = bpy.data.materials.new(name)
    value.diffuse_color = rgba
    return value


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def face_world_data(obj: bpy.types.Object, face_id: int):
    polygon = obj.data.polygons[face_id]
    points = [
        obj.matrix_world @ obj.data.vertices[vertex_id].co
        for vertex_id in polygon.vertices
    ]
    center = sum(points, Vector()) / len(points)
    normal = (obj.matrix_world.to_3x3() @ polygon.normal).normalized()
    return points, center, normal


def add_overlay(
    face_id: int,
    points: list[Vector],
    normal: Vector,
    target_material: bpy.types.Material,
) -> bpy.types.Object:
    overlay_mesh = bpy.data.meshes.new(f"V27_FACE_{face_id}_OVERLAY_MESH")
    overlay_mesh.from_pydata(
        [point + normal * 0.15 for point in points],
        [],
        [list(range(len(points)))],
    )
    overlay_mesh.materials.append(target_material)
    overlay = bpy.data.objects.new(f"V27_FACE_{face_id}_OVERLAY", overlay_mesh)
    bpy.context.scene.collection.objects.link(overlay)
    overlay.hide_render = False
    return overlay


def add_label(
    face_id: int,
    center: Vector,
    normal: Vector,
    target_material: bpy.types.Material,
) -> bpy.types.Object:
    label_curve = bpy.data.curves.new(f"V27_LABEL_{face_id}_CURVE", "FONT")
    label_curve.body = str(face_id)
    label_curve.align_x = "CENTER"
    label_curve.align_y = "CENTER"
    label_curve.size = 1.25
    label_curve.extrude = 0.025
    label_curve.materials.append(target_material)
    label = bpy.data.objects.new(f"V27_LABEL_{face_id}", label_curve)
    label.location = center + normal * 2.0
    bpy.context.scene.collection.objects.link(label)
    label.hide_render = False
    return label


def configure_scene() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("V27_C9_EXPANSION_CAMERA")
    camera = bpy.data.objects.new("V27_C9_EXPANSION_CAMERA", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.hide_render = False
    camera.data.type = "ORTHO"
    camera.data.clip_start = 0.05
    camera.data.clip_end = 2000
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 2.0
    scene.display.shading.curvature_valley_factor = 1.5
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.025, 0.03, 0.04)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    return camera


def main() -> None:
    parsed = args()
    parsed.out.mkdir(parents=True, exist_ok=True)

    source = bpy.data.objects.get(OBJECT_NAME)
    if source is None or source.type != "MESH":
        raise RuntimeError(f"authority object is missing or not a mesh: {OBJECT_NAME}")
    invalid = [face_id for face_id in FACE_IDS if not 0 <= face_id < len(source.data.polygons)]
    if invalid:
        raise RuntimeError(
            f"requested faces outside {OBJECT_NAME} polygon count "
            f"{len(source.data.polygons)}: {invalid}"
        )

    for item in bpy.context.scene.objects:
        item.hide_render = True
    context = source.copy()
    context.data = source.data.copy()
    context.name = "V27_C9_EXPANSION_CONTEXT_COPY"
    bpy.context.scene.collection.objects.link(context)
    context.hide_render = False

    base_material = material("V27_C9_CONTEXT_GREY", (0.17, 0.20, 0.23, 1.0))
    context.data.materials.clear()
    context.data.materials.append(base_material)
    for polygon in context.data.polygons:
        polygon.material_index = 0

    target_materials = [
        material(f"V27_FACE_{face_id}_COLOR", color)
        for face_id, color in zip(FACE_IDS, COLORS, strict=True)
    ]
    camera = configure_scene()
    scene = bpy.context.scene

    face_data = {
        face_id: face_world_data(source, face_id)
        for face_id in FACE_IDS
    }
    all_points = [
        point
        for face_id in FACE_IDS
        for point in face_data[face_id][0]
    ]
    centers = [face_data[face_id][1] for face_id in FACE_IDS]
    normals = [face_data[face_id][2] for face_id in FACE_IDS]
    focus = sum(centers, Vector()) / len(centers)
    mean_normal = sum(normals, Vector())
    if mean_normal.length < 1e-6:
        mean_normal = Vector((1.0, 0.0, 0.0))
    mean_normal.normalize()
    tangent = mean_normal.cross(Vector((0.0, 0.0, 1.0)))
    if tangent.length < 1e-6:
        tangent = mean_normal.cross(Vector((0.0, 1.0, 0.0)))
    tangent.normalize()
    third = mean_normal.cross(tangent).normalized()
    group_span = max((point - focus).length for point in all_points)

    overlays = []
    labels = []
    for face_id, target_material in zip(FACE_IDS, target_materials, strict=True):
        points, center, normal = face_data[face_id]
        overlays.append(add_overlay(face_id, points, normal, target_material))
        labels.append(add_label(face_id, center, normal, target_material))

    group_views = {
        "front": mean_normal,
        "reverse": -mean_normal,
        "side_a": (tangent * 0.85 + mean_normal * 0.20 + third * 0.35).normalized(),
        "side_b": (-tangent * 0.85 + mean_normal * 0.20 + third * 0.35).normalized(),
    }
    camera.data.ortho_scale = max(20.0, group_span * 3.4)
    distance = max(70.0, group_span * 5.0)
    manifest = [
        f"authority_object={OBJECT_NAME}",
        f"polygon_count={len(source.data.polygons)}",
        f"face_ids={FACE_IDS}",
    ]
    for view_name, direction in group_views.items():
        camera.location = focus + direction * distance
        point_camera(camera, focus)
        for label in labels:
            label.rotation_euler = camera.rotation_euler
        output = parsed.out / f"group__{view_name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        manifest.append(f"group view={view_name} output={output}")

    for overlay in overlays:
        overlay.hide_render = True
    for label in labels:
        label.hide_render = True

    for face_id, target_material in zip(FACE_IDS, target_materials, strict=True):
        points, center, normal = face_data[face_id]
        overlay = add_overlay(face_id, points, normal, target_material)
        tangent = points[1] - points[0]
        tangent -= normal * tangent.dot(normal)
        if tangent.length < 1e-6:
            tangent = normal.cross(Vector((0.0, 0.0, 1.0)))
        if tangent.length < 1e-6:
            tangent = normal.cross(Vector((0.0, 1.0, 0.0)))
        tangent.normalize()
        span = max((point - center).length for point in points)
        camera.data.ortho_scale = max(7.0, span * 8.0)
        distance = max(25.0, span * 18.0)
        individual_views = {
            "normal": normal,
            "oblique": (normal * 0.70 + tangent * 0.714).normalized(),
        }
        for view_name, direction in individual_views.items():
            camera.location = center + direction * distance
            point_camera(camera, center)
            output = parsed.out / f"face_{face_id}__{view_name}.png"
            scene.render.filepath = str(output)
            bpy.ops.render.render(write_still=True)
            manifest.append(
                f"face={face_id} view={view_name} output={output}"
            )
        bpy.data.objects.remove(overlay, do_unlink=True)

    (parsed.out.parent / "render_manifest.txt").write_text(
        "\n".join(manifest) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
