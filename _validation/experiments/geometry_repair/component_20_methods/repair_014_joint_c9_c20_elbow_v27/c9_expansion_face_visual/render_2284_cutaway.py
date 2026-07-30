"""Render a bounded local topology cutaway for V27 source face 2284."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


OBJECT_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
FACE_ID = 2284
RINGS = 3


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
    if not 0 <= FACE_ID < len(source.data.polygons):
        raise RuntimeError(
            f"face {FACE_ID} outside {OBJECT_NAME} polygon count "
            f"{len(source.data.polygons)}"
        )

    for item in bpy.context.scene.objects:
        item.hide_render = True

    vertex_faces: dict[int, set[int]] = {}
    for polygon in source.data.polygons:
        for vertex_id in polygon.vertices:
            vertex_faces.setdefault(vertex_id, set()).add(polygon.index)
    neighborhood = {FACE_ID}
    frontier = {FACE_ID}
    for _ in range(RINGS):
        next_frontier: set[int] = set()
        for face_id in frontier:
            for vertex_id in source.data.polygons[face_id].vertices:
                next_frontier.update(vertex_faces[vertex_id])
        next_frontier -= neighborhood
        neighborhood.update(next_frontier)
        frontier = next_frontier

    used_vertices = sorted(
        {
            vertex_id
            for face_id in neighborhood
            for vertex_id in source.data.polygons[face_id].vertices
        }
    )
    vertex_map = {source_id: local_id for local_id, source_id in enumerate(used_vertices)}
    local_vertices = [source.data.vertices[vertex_id].co.copy() for vertex_id in used_vertices]
    local_faces = [
        [vertex_map[vertex_id] for vertex_id in source.data.polygons[face_id].vertices]
        for face_id in sorted(neighborhood)
    ]
    local_mesh = bpy.data.meshes.new("V27_2284_CUTAWAY_MESH")
    local_mesh.from_pydata(local_vertices, [], local_faces)
    grey = bpy.data.materials.new("V27_2284_CUTAWAY_GREY")
    grey.diffuse_color = (0.17, 0.20, 0.23, 1.0)
    local_mesh.materials.append(grey)
    local_object = bpy.data.objects.new("V27_2284_CUTAWAY", local_mesh)
    local_object.matrix_world = source.matrix_world.copy()
    bpy.context.scene.collection.objects.link(local_object)
    local_object.hide_render = False

    polygon = source.data.polygons[FACE_ID]
    points = [
        source.matrix_world @ source.data.vertices[vertex_id].co
        for vertex_id in polygon.vertices
    ]
    center = sum(points, Vector()) / len(points)
    normal = (source.matrix_world.to_3x3() @ polygon.normal).normalized()
    magenta = bpy.data.materials.new("V27_2284_CUTAWAY_MAGENTA")
    magenta.diffuse_color = (1.0, 0.02, 0.62, 1.0)
    overlay_mesh = bpy.data.meshes.new("V27_2284_CUTAWAY_OVERLAY_MESH")
    overlay_vertices = (
        [point + normal * 0.15 for point in points]
        + [point - normal * 0.15 for point in points]
    )
    count = len(points)
    overlay_mesh.from_pydata(
        overlay_vertices,
        [],
        [list(range(count)), list(range(count, count * 2))],
    )
    overlay_mesh.materials.append(magenta)
    overlay = bpy.data.objects.new("V27_2284_CUTAWAY_OVERLAY", overlay_mesh)
    bpy.context.scene.collection.objects.link(overlay)
    overlay.hide_render = False

    camera_data = bpy.data.cameras.new("V27_2284_CUTAWAY_CAMERA")
    camera = bpy.data.objects.new("V27_2284_CUTAWAY_CAMERA", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.hide_render = False
    camera.data.type = "ORTHO"
    camera.data.clip_start = 0.05
    camera.data.clip_end = 1000
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

    world_local_points = [
        source.matrix_world @ source.data.vertices[vertex_id].co
        for vertex_id in used_vertices
    ]
    local_span = max((point - center).length for point in world_local_points)
    tangent = points[1] - points[0]
    tangent -= normal * tangent.dot(normal)
    if tangent.length < 1e-6:
        tangent = normal.cross(Vector((0.0, 0.0, 1.0)))
    if tangent.length < 1e-6:
        tangent = normal.cross(Vector((0.0, 1.0, 0.0)))
    tangent.normalize()
    views = {
        "local_reverse": -normal,
        "local_oblique": (-normal * 0.68 + tangent * 0.73).normalized(),
    }
    camera.data.ortho_scale = max(5.0, local_span * 2.25)
    distance = max(30.0, local_span * 8.0)
    manifest = [
        f"face_id={FACE_ID}",
        f"rings={RINGS}",
        f"neighborhood_face_ids={sorted(neighborhood)}",
        f"source_vertex_ids={used_vertices}",
    ]
    for view_name, direction in views.items():
        camera.location = center + direction * distance
        point_camera(camera, center)
        output = parsed.out / f"face_{FACE_ID}__{view_name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        manifest.append(f"view={view_name} output={output}")

    (parsed.out.parent / "face_2284_cutaway_manifest.txt").write_text(
        "\n".join(manifest) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
