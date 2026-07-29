#!/usr/bin/env python3
"""Write the read-only V27 Blender/source attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import bpy


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27/v27_input_attestation.json"
)
SOURCE_OBJECT = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
SHAPE_KEY_OBJECT = "WORK_FITTED_SURFACE_CANDIDATE"
OPERATION = "ATTEST_V27_INPUTS"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(
        json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    temporary.replace(path)


def mesh_identity(obj: bpy.types.Object) -> dict[str, Any]:
    if obj.type != "MESH" or obj.data is None:
        raise RuntimeError(
            f"{OPERATION}: object {obj.name!r} is not a mesh with data"
        )
    mesh = obj.data
    geometry = {
        "vertex_coordinates": [
            [float(value) for value in vertex.co] for vertex in mesh.vertices
        ],
        "polygons": [
            {
                "loop_vertex_ids": [int(value) for value in polygon.vertices],
                "material_index": int(polygon.material_index),
                "use_smooth": bool(polygon.use_smooth),
            }
            for polygon in mesh.polygons
        ],
        "material_slots": [
            material.name if material is not None else None
            for material in mesh.materials
        ],
    }
    return {
        "object": obj.name,
        "object_type": obj.type,
        "mesh_datablock": mesh.name,
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "polygon_count": len(mesh.polygons),
        "loop_count": len(mesh.loops),
        "material_slot_count": len(mesh.materials),
        "geometry_fingerprint": stable_hash(geometry),
    }


def arguments() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main() -> None:
    args = arguments()
    blend_path = Path(bpy.data.filepath).resolve()
    expected_blend = (
        ROOT
        / "blender_files/experiments/geometry_repair/"
        "repair_014_joint_c9_c20_elbow_v24.blend"
    ).resolve()
    if blend_path != expected_blend:
        raise RuntimeError(
            f"{OPERATION}: wrong input Blend; expected={expected_blend}, "
            f"actual={blend_path}"
        )
    missing = [
        name
        for name in (SOURCE_OBJECT, SHAPE_KEY_OBJECT)
        if bpy.data.objects.get(name) is None
    ]
    if missing:
        raise RuntimeError(
            f"{OPERATION}: required source objects are missing: {missing}"
        )
    unit_settings = bpy.context.scene.unit_settings
    units = {
        "system": unit_settings.system,
        "scale_length": float(unit_settings.scale_length),
        "length_unit": unit_settings.length_unit,
    }
    if (
        units["system"] != "METRIC"
        or abs(units["scale_length"] - 0.001) > 1e-9
        or units["length_unit"] != "MILLIMETERS"
    ):
        raise RuntimeError(
            f"{OPERATION}: scene unit contract mismatch: {units}"
        )
    result = {
        "operation": OPERATION,
        "status": "V27_INPUT_AUTHORITIES_FROZEN",
        "input_blend": str(blend_path),
        "input_blend_sha256": sha_file(blend_path),
        "blender": {
            "version": bpy.app.version_string,
            "version_tuple": list(bpy.app.version),
        },
        "scene": {
            "name": bpy.context.scene.name,
            "units": units,
        },
        "objects": {
            SOURCE_OBJECT: mesh_identity(bpy.data.objects[SOURCE_OBJECT]),
            SHAPE_KEY_OBJECT: mesh_identity(
                bpy.data.objects[SHAPE_KEY_OBJECT]
            ),
        },
        "safety": {
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        },
    }
    result["semantic_fingerprint"] = stable_hash(result)
    atomic_json(args.output.resolve(), result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output.resolve()),
                "output_sha256": sha_file(args.output.resolve()),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
