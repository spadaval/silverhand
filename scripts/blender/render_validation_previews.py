"""Render solid, wire-free STL previews in Blender.

Invoke through render_validation_previews.sh rather than calling this file with
the system Python.
"""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from image_sanitization import sanitize_image  # noqa: E402


VIEWS = {
    "iso": Vector((1.3, -1.3, 0.9)),
    "front": Vector((0.0, -1.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
}


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args(arguments)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def configure_scene(output_dir: Path) -> tuple[bpy.types.Object, bpy.types.Material]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output_dir)

    world = scene.world or bpy.data.worlds.new("Validation World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.035, 0.045, 0.06, 1.0)
    background.inputs["Strength"].default_value = 0.35

    material = bpy.data.materials.new("Validation Solid")
    material.diffuse_color = (0.22, 0.48, 0.72, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.11, 0.34, 0.62, 1.0)
    principled.inputs["Roughness"].default_value = 0.58
    principled.inputs["Metallic"].default_value = 0.05

    camera_data = bpy.data.cameras.new("Validation Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Validation Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    for name, rotation, energy in (
        ("Validation Key", (0.55, -0.35, -0.6), 4.0),
        ("Validation Fill", (-0.6, 0.2, 2.2), 2.0),
    ):
        light_data = bpy.data.lights.new(name, type="SUN")
        light_data.energy = energy
        light = bpy.data.objects.new(name, light_data)
        light.rotation_euler = rotation
        scene.collection.objects.link(light)

    return camera, material


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    minimum = Vector(tuple(min(corner[axis] for corner in corners) for axis in range(3)))
    maximum = Vector(tuple(max(corner[axis] for corner in corners) for axis in range(3)))
    return minimum, maximum


def render_file(
    path: Path,
    relative_path: Path,
    output_dir: Path,
    camera: bpy.types.Object,
    material: bpy.types.Material,
) -> list[tuple[str, Path]]:
    before = set(bpy.data.objects)
    status = bpy.ops.wm.stl_import(filepath=str(path), use_mesh_validate=False)
    if "FINISHED" not in status:
        raise RuntimeError(f"Blender STL import returned {sorted(status)}")

    imported = [
        obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"
    ]
    if not imported:
        raise RuntimeError("Blender STL import created no mesh objects")

    for obj in imported:
        obj.data.materials.clear()
        obj.data.materials.append(material)
        obj.show_wire = False
        obj.show_all_edges = False

    bpy.context.view_layer.update()
    minimum, maximum = world_bounds(imported)
    center = (minimum + maximum) * 0.5
    largest_dimension = max(maximum - minimum)
    if largest_dimension <= 0:
        raise RuntimeError(f"bounding box is empty: min={tuple(minimum)}, max={tuple(maximum)}")

    relative_stem = relative_path.with_suffix("")
    output_stem = "__".join(relative_stem.parts)
    renders: list[tuple[str, Path]] = []
    for view_name, direction in VIEWS.items():
        camera.location = center + direction.normalized() * largest_dimension * 3.0
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = largest_dimension * 1.35
        render_path = output_dir / f"{output_stem}--{view_name}.png"
        bpy.context.scene.render.filepath = str(render_path)
        bpy.ops.render.render(write_still=True)
        sanitize_image(render_path)
        renders.append((view_name, render_path))

    for obj in imported:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    return renders


def write_index(
    output_dir: Path,
    rendered: list[tuple[Path, list[tuple[str, Path]]]],
    failures: list[tuple[Path, str]],
) -> None:
    cards = []
    for source, images in rendered:
        image_html = "".join(
            f'<figure><img src="{escape(image.name)}" alt="{escape(str(source))} '
            f'{escape(view)}"><figcaption>{escape(view)}</figcaption></figure>'
            for view, image in images
        )
        cards.append(
            f'<section><h2>{escape(str(source))}</h2><div class="views">{image_html}</div></section>'
        )
    failure_html = "".join(
        f"<li><code>{escape(str(source))}</code>: {escape(reason)}</li>"
        for source, reason in failures
    )
    document = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Silverhand solid STL previews</title>
<style>
  body {{ margin: 0; padding: 2rem; background: #111722; color: #edf3fa;
          font: 15px/1.45 system-ui, sans-serif; }}
  h1 {{ margin-top: 0; }} section {{ margin: 2rem 0 3rem; }}
  .views {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }}
  figure {{ margin: 0; }} img {{ display: block; width: 100%; border: 1px solid #35435a; }}
  figcaption {{ padding-top: .4rem; color: #9fb2c9; }}
  code {{ color: #b9d8ff; }}
  @media (max-width: 800px) {{ .views {{ grid-template-columns: 1fr; }} }}
</style>
<h1>Silverhand solid STL previews</h1>
<p>Reject unexplained slabs, fans, bridges, spikes, folds, gaps, and interior caps.
These renders complement—not replace—the automated STL audit.</p>
{f'<h2>Render failures</h2><ul>{failure_html}</ul>' if failures else ''}
{''.join(cards)}
</html>
"""
    (output_dir / "index.html").write_text(document, encoding="utf-8")


def main() -> int:
    args = parse_args()
    export_root = args.export_root.resolve()
    output_dir = args.output_dir.resolve()
    if not export_root.is_dir():
        print(
            f"ERROR: cannot render export root '{export_root}': directory does not exist",
            file=sys.stderr,
        )
        return 2

    paths = sorted(export_root.rglob("*.stl"))
    if not paths:
        print(f"ERROR: no .stl files found under '{export_root}'", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    clear_scene()
    camera, material = configure_scene(output_dir)
    rendered: list[tuple[Path, list[tuple[str, Path]]]] = []
    failures: list[tuple[Path, str]] = []

    for path in paths:
        relative_path = path.relative_to(export_root)
        try:
            images = render_file(
                path, relative_path, output_dir, camera, material
            )
        except Exception as exc:
            failures.append((relative_path, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {relative_path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        else:
            rendered.append((relative_path, images))
            print(
                f"DONE {relative_path}: rendered and sanitized "
                f"{len(images)} views"
            )

    write_index(output_dir, rendered, failures)
    print(f"Wrote preview index: {output_dir / 'index.html'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
