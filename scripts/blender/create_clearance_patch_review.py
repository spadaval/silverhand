"""Create disposable pre/post review objects for one repair shape key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    SOURCE_NAME,
    connected_components,
)


REVIEW_COLLECTION = "30_REVIEW"


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape-key", required=True)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(arguments)


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"PATCH_REVIEW: {role} '{name}' has type/state '{actual}', "
            "expected MESH"
        )
    return obj


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def evaluated_duplicate(
    candidate: bpy.types.Object,
    collection: bpy.types.Collection,
    name: str,
) -> bpy.types.Object:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = candidate.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    mesh.name = f"{name}_MESH"
    obj = bpy.data.objects.new(name, mesh)
    obj.matrix_world = evaluated.matrix_world.copy()
    collection.objects.link(obj)
    obj["role"] = "clearance patch comparison"
    obj["status"] = "evaluation_only_not_approved"
    obj["printable"] = False
    obj.hide_set(True)
    obj.hide_render = True
    return obj


def detail_object(
    full: bpy.types.Object,
    collection: bpy.types.Collection,
    name: str,
    component_indices: list[int],
) -> bpy.types.Object:
    component_set = set(component_indices)
    world_points = [
        full.matrix_world @ vertex.co for vertex in full.data.vertices
    ]
    faces = [
        tuple(polygon.vertices)
        for polygon in full.data.polygons
        if all(index in component_set for index in polygon.vertices)
    ]
    used = sorted({index for face in faces for index in face})
    remap = {
        source_index: target_index
        for target_index, source_index in enumerate(used)
    }
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(
        [world_points[index] for index in used],
        [],
        [
            tuple(remap[index] for index in face)
            for face in faces
        ],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.matrix_world = Matrix.Identity(4)
    collection.objects.link(obj)
    obj["role"] = "clearance patch detail comparison"
    obj["status"] = "evaluation_only_not_approved"
    obj["printable"] = False
    obj.hide_set(True)
    obj.hide_render = True
    return obj


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    if candidate.data.shape_keys is None:
        raise RuntimeError(
            f"PATCH_REVIEW: candidate '{candidate.name}' has no shape keys"
        )
    key = candidate.data.shape_keys.key_blocks.get(args.shape_key)
    if key is None:
        raise RuntimeError(
            f"PATCH_REVIEW: shape key '{args.shape_key}' is missing"
        )
    _, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"PATCH_REVIEW: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )

    names = {
        "before": f"{args.prefix}_BEFORE",
        "after": f"{args.prefix}_AFTER",
        "detail_before": f"{args.prefix}_DETAIL_BEFORE",
        "detail_after": f"{args.prefix}_DETAIL_AFTER",
    }
    existing = [
        name for name in names.values() if bpy.data.objects.get(name)
    ]
    if existing:
        raise RuntimeError(
            f"PATCH_REVIEW: review objects already exist: {existing}"
        )

    collection = ensure_collection(REVIEW_COLLECTION)
    original_value = key.value
    try:
        key.value = 0.0
        bpy.context.view_layer.update()
        before = evaluated_duplicate(
            candidate,
            collection,
            names["before"],
        )
        key.value = 1.0
        bpy.context.view_layer.update()
        after = evaluated_duplicate(
            candidate,
            collection,
            names["after"],
        )
    finally:
        key.value = original_value
        bpy.context.view_layer.update()

    detail_before = detail_object(
        before,
        collection,
        names["detail_before"],
        components[args.component],
    )
    detail_after = detail_object(
        after,
        collection,
        names["detail_after"],
        components[args.component],
    )
    candidate.hide_set(False)
    candidate.hide_render = False
    bpy.context.view_layer.objects.active = candidate

    report = {
        "tool": Path(__file__).name,
        "status": "evaluation_only_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "shape_key": key.name,
        "component": args.component,
        "review_objects": [
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "faces": len(obj.data.polygons),
            }
            for obj in (before, after, detail_before, detail_after)
        ],
    }
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: created review objects for shape key '{key.name}'; "
        "qualitative review remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
