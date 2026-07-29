"""Render a matched-view source/current geometry comparison.

The source and target use the exact same orthographic camera transform for each
semantic view. The script uses the canonical cameras stored in the blend file,
restores scene state, and never saves the blend file.

Run this with Blender's Python, not the system Python. The companion shell
launcher is the normal entry point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from image_sanitization import sanitize_image  # noqa: E402
from validation_camera_rig import (  # noqa: E402
    DEFAULT_SOURCE,
    DEFAULT_TARGET,
    RIG_VERSION,
    VIEW_DIRECTIONS,
    camera_record,
    require_camera_rig,
)


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resolution-x", type=int, default=700)
    parser.add_argument("--resolution-y", type=int, default=1000)
    args = parser.parse_args(arguments)
    if args.resolution_x <= 0 or args.resolution_y <= 0:
        parser.error("render resolution must be positive")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot render comparison: {role} object '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot render comparison: {role} object '{name}' has type "
            f"'{obj.type}', expected 'MESH'"
        )
    return obj


def evaluated_world_points(obj: bpy.types.Object) -> list:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            raise RuntimeError(
                f"Cannot render comparison: object '{obj.name}' has no vertices"
            )
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def geometry_fingerprint(
    obj: bpy.types.Object,
    world_points: list,
) -> str:
    digest = hashlib.sha256()
    for point in world_points:
        digest.update(struct.pack("<3d", *point))
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", index))
        digest.update(struct.pack("<I", polygon.material_index))
    return digest.hexdigest()


def dimensions(points: list) -> list[float]:
    return [
        round(
            max(point[axis] for point in points)
            - min(point[axis] for point in points),
            3,
        )
        for axis in range(3)
    ]


def configure_render(
    output_dir: Path,
    resolution_x: int,
    resolution_y: int,
) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output_dir)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.018, 0.027, 0.043)


def set_render_target(rendered: bpy.types.Object) -> None:
    for obj in bpy.context.scene.objects:
        if hasattr(obj, "hide_render"):
            obj.hide_render = obj != rendered and obj.type != "CAMERA"
    rendered.hide_render = False
    bpy.context.view_layer.update()


def main() -> int:
    args = parse_args()
    source = require_mesh(args.source, "source")
    target = require_mesh(args.target, "target")
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_points = evaluated_world_points(source)
    target_points = evaluated_world_points(target)
    cameras = require_camera_rig()

    scene = bpy.context.scene
    original_camera = scene.camera
    original_filepath = scene.render.filepath
    original_engine = scene.render.engine
    original_hide_render = {
        obj.name: obj.hide_render for obj in scene.objects
    }
    original_colors = {
        source.name: tuple(source.color),
        target.name: tuple(target.color),
    }
    renders: list[dict] = []
    view_records: dict[str, dict] = {}

    try:
        configure_render(
            output_dir,
            args.resolution_x,
            args.resolution_y,
        )
        source.color = (0.20, 0.22, 0.25, 1.0)
        target.color = (0.035, 0.43, 0.48, 1.0)
        for view_name in VIEW_DIRECTIONS:
            camera = cameras[view_name]
            scene.camera = camera
            view_records[view_name] = camera_record(camera)
            for label, obj in (("source", source), ("current", target)):
                set_render_target(obj)
                path = output_dir / f"{label}--{view_name}.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                if not path.is_file():
                    raise RuntimeError(
                        "Cannot render comparison: Blender reported success but "
                        f"did not create '{path}'"
                    )
                sanitization = sanitize_image(path)
                renders.append(
                    {
                        "role": label,
                        "object": obj.name,
                        "view": view_name,
                        "path": path.name,
                        "sanitization": sanitization,
                    }
                )

        manifest = {
            "tool": "render_geometry_comparison.py",
            "rig_version": RIG_VERSION,
            "blend_file": str(Path(bpy.data.filepath).resolve()),
            "units": "millimeters",
            "matching_camera_per_view": True,
            "source": {
                "object": source.name,
                "dimensions_mm": dimensions(source_points),
                "geometry_fingerprint": geometry_fingerprint(
                    source,
                    source_points,
                ),
            },
            "target": {
                "object": target.name,
                "dimensions_mm": dimensions(target_points),
                "geometry_fingerprint": geometry_fingerprint(
                    target,
                    target_points,
                ),
            },
            "render": {
                "resolution": [args.resolution_x, args.resolution_y],
                "views": view_records,
                "images": renders,
                "contact_sheet_layout": {
                    "columns": ["source", "current"],
                    "rows": list(VIEW_DIRECTIONS),
                },
                "contact_sheet": None,
                "contact_sheets": [],
                "archival_contact_sheet": None,
            },
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(manifest, indent=2))
        return 0
    finally:
        source.color = original_colors[source.name]
        target.color = original_colors[target.name]
        for name, hidden in original_hide_render.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = hidden
        scene.camera = original_camera
        scene.render.filepath = original_filepath
        scene.render.engine = original_engine


if __name__ == "__main__":
    raise SystemExit(main())
