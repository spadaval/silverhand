"""Validate the consolidated Silverhand whole-arm evaluation master."""

from __future__ import annotations

import hashlib
import json
import struct

import bmesh
import bpy


EXPECTED_COLLECTIONS = (
    "00_SOURCE_LOCKED",
    "10_FIT_TOOLS",
    "20_FITTED_SURFACE",
    "25_ENGINEERING_PROTOTYPES",
    "40_DEFERRED_ARMOR",
    "90_VALIDATION_CAMERAS",
)
PROHIBITED_COLLECTIONS = (
    "20_SALVAGE_WORKING",
    "30_REVIEW",
    "EVAL_V28_THREE_PANEL_SCAFFOLD",
    "EVAL_V28_THREE_PANEL_PHYSICAL_SHELLS",
    "EVAL_V28_REVERSIBLE_EDGE_SOFTENING",
)
SOURCE_FINGERPRINTS = {
    "SRC_GAME_RAW": (
        "15fefd43b96fec1875618ecbca0aadd4bd8c847aa658ec5da02a838c6020fc96"
    ),
    "SRC_GAME_FITTED": (
        "cb94949e59502987fee6c844115fcc39c3701b66386148639fc124364c7bc68e"
    ),
    "SRC_DEFORMED_FULL_BASELINE": (
        "57d082b44b3c3993b0ae56703757edf287c0c5e2100bb1ca1f9ef13e4c8ac264"
    ),
    "SRC_GAME_TPU_ONLY_BASELINE": (
        "e439687dfa926a2dbac969464daa54d71cd2a7d2674fb2ee1e27d54b486afcf4"
    ),
}
CANDIDATE = "WORK_FITTED_SURFACE_CANDIDATE"
CANDIDATE_FINGERPRINT = (
    "70f1f224b0c8be72abfba6bd3c0ce341c5685e3c541fb17bede0d59dcd8c95d3"
)
EXPECTED_SHAPE_KEYS = (
    "Basis",
    "STATIC_ANATOMICAL_FIT",
    "FRAGMENT_RESCUE_CLEARANCE",
    "REPAIR_001_COMPONENT_0",
    "REPAIR_002_COMPONENT_1_REGIONAL",
    "REPAIR_003_COMPONENT_25_MASKED",
    "REPAIR_004_COMPONENT_37_MASKED",
    "REPAIR_005_COMPONENT_42_MASKED",
    "REPAIR_006_COMPONENT_20_MINOR_PATCHES",
    "REPAIR_007_COMPONENT_16_HARMONIC",
    "REPAIR_008_COMPONENT_52_REGIONAL",
    "REPAIR_009_COMPONENT_57_REGIONAL",
    "REPAIR_010_COMPONENT_59_REGIONAL",
    "REPAIR_011_COMPONENT_36_REGIONAL",
    "REPAIR_012_COMPONENT_39_REGIONAL",
    "REPAIR_013_COMPONENT_19_CLUSTER_RIGID",
)
PROTOTYPE_FINGERPRINTS = {
    "PROTOTYPE_V28_WEARABLE_PANEL_0": (
        "327874ca7de7ee1e8cb15bf6a85daa16bc4b68fd6adafff830cc4754a9bec9d4"
    ),
    "PROTOTYPE_V28_WEARABLE_PANEL_1": (
        "65c9720e54eb3410603511174bd892d2709e420d9953d1217329908138d641c8"
    ),
    "PROTOTYPE_V28_WEARABLE_PANEL_2": (
        "e2091bed93c4596af8db552ac84ca4a8390509897066f9260a86da0d90a3a3df"
    ),
}
EXPECTED_CAMERAS = (
    "VAL_CAM_DORSAL",
    "VAL_CAM_VENTRAL",
    "VAL_CAM_MEDIAL",
    "VAL_CAM_LATERAL",
    "VAL_CAM_DORSAL_LATERAL_THREE_QUARTER",
    "VAL_CAM_VENTRAL_MEDIAL_THREE_QUARTER",
    "VAL_CAM_WRIST_AXIAL",
    "VAL_CAM_BICEP_AXIAL",
)


def fingerprint(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    digest.update(obj.type.encode("utf-8"))
    for row in obj.matrix_world:
        digest.update(struct.pack("<4d", *row))
    if obj.type == "MESH":
        for vertex in obj.data.vertices:
            digest.update(struct.pack("<3d", *vertex.co))
        for polygon in obj.data.polygons:
            digest.update(struct.pack("<I", len(polygon.vertices)))
            for index in polygon.vertices:
                digest.update(struct.pack("<I", index))
        if obj.data.shape_keys is not None:
            for key_block in obj.data.shape_keys.key_blocks:
                digest.update(key_block.name.encode("utf-8"))
                for point in key_block.data:
                    digest.update(struct.pack("<3d", *point.co))
    return digest.hexdigest()


def evaluated_topology(obj: bpy.types.Object) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        return {
            "vertices": len(bm.verts),
            "faces": len(bm.faces),
            "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
            "nonmanifold_edges": sum(not edge.is_manifold for edge in bm.edges),
            "signed_volume_mm3": round(bm.calc_volume(signed=True), 6),
        }
    finally:
        bm.free()
        evaluated.to_mesh_clear()


issues: list[str] = []
scene = bpy.context.scene

if scene.unit_settings.system != "METRIC":
    issues.append(f"units.system={scene.unit_settings.system!r}; expected METRIC")
if abs(scene.unit_settings.scale_length - 0.001) > 1.0e-9:
    issues.append(
        f"units.scale_length={scene.unit_settings.scale_length}; expected 0.001"
    )
if scene.unit_settings.length_unit != "MILLIMETERS":
    issues.append(
        f"units.length_unit={scene.unit_settings.length_unit!r}; "
        "expected MILLIMETERS"
    )

for name in EXPECTED_COLLECTIONS:
    if bpy.data.collections.get(name) is None:
        issues.append(f"required collection is missing: {name}")
for name in PROHIBITED_COLLECTIONS:
    if bpy.data.collections.get(name) is not None:
        issues.append(f"retired collection remains: {name}")

source_results = {}
for name, expected in SOURCE_FINGERPRINTS.items():
    obj = bpy.data.objects.get(name)
    if obj is None:
        issues.append(f"immutable source object is missing: {name}")
        continue
    actual = fingerprint(obj)
    source_results[name] = actual
    if actual != expected:
        issues.append(
            f"immutable source fingerprint changed: {name}; "
            f"expected={expected}; actual={actual}"
        )

candidate = bpy.data.objects.get(CANDIDATE)
candidate_result = None
if candidate is None:
    issues.append(f"fitted candidate is missing: {CANDIDATE}")
else:
    candidate_result = {
        "fingerprint": fingerprint(candidate),
        "vertices": len(candidate.data.vertices),
        "faces": len(candidate.data.polygons),
        "shape_keys": (
            [key.name for key in candidate.data.shape_keys.key_blocks]
            if candidate.data.shape_keys is not None
            else []
        ),
    }
    if candidate_result["fingerprint"] != CANDIDATE_FINGERPRINT:
        issues.append(
            "fitted candidate fingerprint changed; "
            f"expected={CANDIDATE_FINGERPRINT}; "
            f"actual={candidate_result['fingerprint']}"
        )
    if tuple(candidate_result["shape_keys"]) != EXPECTED_SHAPE_KEYS:
        issues.append(
            "fitted candidate shape-key sequence changed; "
            f"actual={candidate_result['shape_keys']}"
        )
    if candidate.get("printable") is not False:
        issues.append(f"{CANDIDATE} must declare printable=false")
    if candidate.get("print_ready") is not False:
        issues.append(f"{CANDIDATE} must declare print_ready=false")

prototype_results = {}
for name, expected in PROTOTYPE_FINGERPRINTS.items():
    obj = bpy.data.objects.get(name)
    if obj is None:
        issues.append(f"engineering prototype is missing: {name}")
        continue
    actual = fingerprint(obj)
    topology = evaluated_topology(obj)
    prototype_results[name] = {
        "fingerprint": actual,
        "evaluated_topology": topology,
        "modifiers": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "width_mm": getattr(modifier, "width", None),
                "segments": getattr(modifier, "segments", None),
            }
            for modifier in obj.modifiers
        ],
    }
    if actual != expected:
        issues.append(
            f"prototype fingerprint changed: {name}; "
            f"expected={expected}; actual={actual}"
        )
    if (
        topology["boundary_edges"]
        or topology["nonmanifold_edges"]
        or topology["signed_volume_mm3"] <= 0.0
    ):
        issues.append(f"prototype evaluated topology is invalid: {name}; {topology}")
    bevels = [modifier for modifier in obj.modifiers if modifier.type == "BEVEL"]
    if len(bevels) != 1:
        issues.append(f"{name} must retain exactly one live Bevel modifier")
    elif abs(bevels[0].width - 0.4) > 1.0e-6 or bevels[0].segments != 2:
        issues.append(
            f"{name} bevel changed; width={bevels[0].width}; "
            f"segments={bevels[0].segments}"
        )
    if obj.get("printable") is not False or obj.get("print_ready") is not False:
        issues.append(f"{name} must remain a non-print-ready engineering checkpoint")

for name in ("REF_FIT_ANATOMY_STRAIGHT", "CUT_CLEARANCE_ANATOMY_STRAIGHT"):
    obj = bpy.data.objects.get(name)
    if obj is None:
        issues.append(f"fit tool is missing: {name}")
    elif obj.get("printable") is not False:
        issues.append(f"fit tool must declare printable=false: {name}")

camera_collection = bpy.data.collections.get("90_VALIDATION_CAMERAS")
for name in EXPECTED_CAMERAS:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "CAMERA":
        issues.append(f"validation camera is missing or invalid: {name}")
    elif camera_collection is None or camera_collection.objects.get(name) is None:
        issues.append(f"validation camera is not in its collection: {name}")

retired_objects = sorted(
    obj.name
    for obj in bpy.data.objects
    if obj.name.startswith(("EVAL_", "REG_"))
)
if retired_objects:
    issues.append(f"retired evaluation/salvage objects remain: {retired_objects}")

orphans = {
    "meshes": sum(mesh.users == 0 for mesh in bpy.data.meshes),
    "cameras": sum(camera.users == 0 for camera in bpy.data.cameras),
    "curves": sum(curve.users == 0 for curve in bpy.data.curves),
    "images": sum(image.users == 0 for image in bpy.data.images),
}
if any(orphans.values()):
    issues.append(f"unused datablocks remain: {orphans}")

report = {
    "tool": "validate_master.py",
    "blend_file": bpy.data.filepath,
    "status": "PASS" if not issues else "FAIL",
    "issues": issues,
    "units": "millimeters",
    "scene": {
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "collections": len(bpy.data.collections),
        "cameras": len(bpy.data.cameras),
        "images": len(bpy.data.images),
        "orphans": orphans,
    },
    "source_fingerprints": source_results,
    "fitted_candidate": candidate_result,
    "engineering_prototypes": prototype_results,
    "claims": {
        "printable": False,
        "wearable": False,
        "motion": False,
    },
}
print(json.dumps(report, indent=2))
raise SystemExit(0 if not issues else 1)
