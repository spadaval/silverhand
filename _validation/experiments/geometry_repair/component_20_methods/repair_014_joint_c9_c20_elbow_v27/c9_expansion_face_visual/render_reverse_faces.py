"""Render reverse-side close-ups for unresolved V27 C9 faces, without saving."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


OBJECT_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
FACE_IDS = [2222, 2226, 2284]
COLORS = {
    2222: (1.0, 0.90, 0.01, 1.0),
    2226: (0.02, 0.28, 1.0, 1.0),
    2284: (1.0, 0.03, 0.58, 1.0),
}


def args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


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
    context.name = "V27_C9_REVERSE_CONTEXT_COPY"
    bpy.context.scene.collection.objects.link(context)
    context.hide_render = False
    grey = bpy.data.materials.new("V27_REVERSE_CONTEXT_GREY")
    grey.diffuse_color = (0.17, 0.20, 0.23, 1.0)
    context.data.materials.clear()
    context.data.materials.append(grey)
    for polygon in context.data.polygons:
        polygon.material_index = 0

    camera_data = bpy.data.cameras.new("V27_REVERSE_CAMERA")
    camera = bpy.data.objects.new("V27_REVERSE_CAMERA", camera_data)
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
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.025, 0.03, 0.04)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"

    manifest = []
    for face_id in FACE_IDS:
        polygon = source.data.polygons[face_id]
        points = [
            source.matrix_world @ source.data.vertices[vertex_id].co
            for vertex_id in polygon.vertices
        ]
        center = sum(points, Vector()) / len(points)
        normal = (source.matrix_world.to_3x3() @ polygon.normal).normalized()
        reverse = -normal
        target_material = bpy.data.materials.new(f"V27_REVERSE_{face_id}_COLOR")
        target_material.diffuse_color = COLORS[face_id]
        overlay_mesh = bpy.data.meshes.new(f"V27_REVERSE_{face_id}_MESH")
        overlay_mesh.from_pydata(
            [point + reverse * 0.15 for point in points],
            [],
            [list(range(len(points)))],
        )
        overlay_mesh.materials.append(target_material)
        overlay = bpy.data.objects.new(f"V27_REVERSE_{face_id}", overlay_mesh)
        bpy.context.scene.collection.objects.link(overlay)
        overlay.hide_render = False

        span = max((point - center).length for point in points)
        camera.data.ortho_scale = max(7.0, span * 8.0)
        camera.location = center + reverse * max(25.0, span * 18.0)
        point_camera(camera, center)
        output = parsed.out / f"face_{face_id}__reverse.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        manifest.append(f"face={face_id} view=reverse output={output}")
        bpy.data.objects.remove(overlay, do_unlink=True)

    (parsed.out.parent / "reverse_render_manifest.txt").write_text(
        "\n".join(manifest) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
