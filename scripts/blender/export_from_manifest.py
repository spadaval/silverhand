"""Export explicit Blender objects to binary millimeter STL artifacts.

The input manifest is the authority. Current selection, active object, and
viewport visibility are ignored. Every artifact declares its component and bed
policy, and every exported constituent must be a closed positive-volume solid.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from validate_stl_exports import audit_stl  # noqa: E402


ALLOWED_STATUSES = {
    "editable main geometry",
    "connected master",
    "print candidate",
    "physical-test candidate",
    "production export",
}
ALLOWED_COMPONENT_POLICIES = {
    "single_solid",
    "intentional_overlapping_solids",
}
ALLOWED_BED_POLICIES = {
    "must_fit",
    "unsegmented_evidence",
}
PROHIBITED_PREFIXES = ("SRC_", "EVAL_", "CUT_", "REF_", "VAL_CAM_")
TRIANGLE_RECORD = struct.Struct("<12fH")


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(arguments)


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(
            f"Cannot export from manifest: input '{path}' does not exist"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Cannot export from manifest: failed to read '{path}': {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeError(
            f"Cannot export from manifest: root of '{path}' must be an object"
        )
    return value


def require_string(mapping: dict, key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(
            f"Cannot export from manifest: '{context}.{key}' must be a "
            "non-empty string"
        )
    return value


def require_objects(names, context: str) -> list[bpy.types.Object]:
    if not isinstance(names, list) or not names:
        raise RuntimeError(
            f"Cannot export from manifest: '{context}.objects' must be a "
            "non-empty array"
        )
    if len(names) != len(set(names)):
        raise RuntimeError(
            f"Cannot export from manifest: '{context}.objects' contains "
            "duplicate names"
        )
    objects = []
    for name in names:
        if not isinstance(name, str) or not name:
            raise RuntimeError(
                f"Cannot export from manifest: '{context}.objects' contains "
                f"invalid name {name!r}"
            )
        if name.startswith(PROHIBITED_PREFIXES):
            raise RuntimeError(
                f"Cannot export from manifest: object '{name}' is prohibited "
                f"by prefix {PROHIBITED_PREFIXES}"
            )
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError(
                f"Cannot export from manifest: object '{name}' is missing"
            )
        if obj.type != "MESH":
            raise RuntimeError(
                f"Cannot export from manifest: object '{name}' has type "
                f"'{obj.type}', expected 'MESH'"
            )
        if obj.get("printable") is False:
            raise RuntimeError(
                f"Cannot export from manifest: object '{name}' declares "
                "printable=false"
            )
        if obj.get("print_ready") is False:
            raise RuntimeError(
                f"Cannot export from manifest: object '{name}' declares "
                "print_ready=false"
            )
        objects.append(obj)
    return objects


def evaluated_bmesh(obj: bpy.types.Object) -> bmesh.types.BMesh:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.transform(evaluated.matrix_world)
        bm.normal_update()
        return bm
    finally:
        evaluated.to_mesh_clear()


def inspect_constituent(obj: bpy.types.Object) -> tuple[dict, bmesh.types.BMesh]:
    bm = evaluated_bmesh(obj)
    report = {
        "object": obj.name,
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
        "nonmanifold_edges": sum(not edge.is_manifold for edge in bm.edges),
        "signed_volume_mm3": round(bm.calc_volume(signed=True), 6),
    }
    failures = []
    if not bm.verts or not bm.faces:
        failures.append("empty evaluated geometry")
    if report["boundary_edges"]:
        failures.append(f"{report['boundary_edges']} boundary edges")
    if report["nonmanifold_edges"]:
        failures.append(
            f"{report['nonmanifold_edges']} non-manifold edges"
        )
    if report["signed_volume_mm3"] <= 0.0:
        failures.append(
            f"non-positive signed volume {report['signed_volume_mm3']} mm³"
        )
    if failures:
        bm.free()
        raise RuntimeError(
            f"Cannot export from manifest: object '{obj.name}' is invalid ("
            + "; ".join(failures)
            + ")"
        )
    return report, bm


def triangulated_records(
    constituents: list[tuple[dict, bmesh.types.BMesh]],
) -> tuple[list[bytes], list[Vector]]:
    records = []
    points = []
    for _, bm in constituents:
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.normal_update()
        for face in bm.faces:
            if len(face.verts) != 3:
                raise RuntimeError(
                    "Cannot export from manifest: triangulation left a "
                    f"{len(face.verts)}-vertex face"
                )
            vertices = [vertex.co.copy() for vertex in face.verts]
            normal = (vertices[1] - vertices[0]).cross(
                vertices[2] - vertices[0]
            )
            if normal.length_squared == 0.0:
                raise RuntimeError(
                    "Cannot export from manifest: triangulation produced a "
                    "zero-area triangle"
                )
            normal.normalize()
            records.append(
                TRIANGLE_RECORD.pack(
                    float(normal.x),
                    float(normal.y),
                    float(normal.z),
                    *(float(value) for vertex in vertices for value in vertex),
                    0,
                )
            )
            points.extend(vertices)
    return records, points


def write_binary_stl(path: Path, records: list[bytes]) -> None:
    header = (
        b"Silverhand explicit millimeter export"
        + b"\0" * 80
    )[:80]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(records)))
        for record in records:
            handle.write(record)
    temporary.replace(path)


def dimensions(points: list[Vector]) -> list[float]:
    return [
        round(
            max(point[axis] for point in points)
            - min(point[axis] for point in points),
            6,
        )
        for axis in range(3)
    ]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    status = require_string(manifest, "artifact_status", "manifest")
    if status not in ALLOWED_STATUSES:
        raise RuntimeError(
            "Cannot export from manifest: 'artifact_status' must be one of "
            f"{sorted(ALLOWED_STATUSES)}, got {status!r}"
        )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError(
            "Cannot export from manifest: 'artifacts' must be a non-empty array"
        )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = []
    reports = []
    for index, artifact in enumerate(artifacts):
        context = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise RuntimeError(
                f"Cannot export from manifest: '{context}' must be an object"
            )
        filename = require_string(artifact, "filename", context)
        if Path(filename).name != filename or not filename.lower().endswith(
            ".stl"
        ):
            raise RuntimeError(
                f"Cannot export from manifest: '{context}.filename' must be a "
                f"plain .stl filename, got {filename!r}"
            )
        if filename in filenames:
            raise RuntimeError(
                f"Cannot export from manifest: duplicate filename '{filename}'"
            )
        filenames.append(filename)
        component_policy = require_string(
            artifact,
            "component_policy",
            context,
        )
        if component_policy not in ALLOWED_COMPONENT_POLICIES:
            raise RuntimeError(
                f"Cannot export from manifest: '{context}.component_policy' "
                f"must be one of {sorted(ALLOWED_COMPONENT_POLICIES)}, got "
                f"{component_policy!r}"
            )
        bed_policy = require_string(artifact, "bed_policy", context)
        if bed_policy not in ALLOWED_BED_POLICIES:
            raise RuntimeError(
                f"Cannot export from manifest: '{context}.bed_policy' must be "
                f"one of {sorted(ALLOWED_BED_POLICIES)}, got {bed_policy!r}"
            )
        objects = require_objects(artifact.get("objects"), context)
        constituents = []
        try:
            for obj in objects:
                constituents.append(inspect_constituent(obj))
            records, points = triangulated_records(constituents)
            expected_dimensions = dimensions(points)
            output_path = output_dir / filename
            write_binary_stl(output_path, records)
            audit = audit_stl(
                output_path,
                filename,
                allow_overlapping_shells=(
                    component_policy == "intentional_overlapping_solids"
                ),
                allow_bed_oversize=(
                    bed_policy == "unsegmented_evidence"
                ),
            )
            if not audit.passed:
                raise RuntimeError(
                    f"Cannot export from manifest: STL audit failed for "
                    f"'{output_path}' ({'; '.join(audit.issues or [])})"
                )
            reimported_dimensions = list(audit.dimensions_mm or ())
            dimension_delta = [
                round(abs(expected - actual), 6)
                for expected, actual in zip(
                    expected_dimensions,
                    reimported_dimensions,
                )
            ]
            if any(delta > 0.001 for delta in dimension_delta):
                raise RuntimeError(
                    f"Cannot export from manifest: reimported dimensions for "
                    f"'{filename}' differ from evaluated source by "
                    f"{dimension_delta} mm"
                )
            reports.append(
                {
                    "filename": filename,
                    "artifact_status": status,
                    "component_policy": component_policy,
                    "bed_policy": bed_policy,
                    "objects": [report for report, _ in constituents],
                    "triangles": len(records),
                    "dimensions_mm": reimported_dimensions,
                    "dimension_delta_mm": dimension_delta,
                    "connected_components": audit.connected_components,
                    "signed_volume_mm3": audit.signed_volume_mm3,
                    "bytes": output_path.stat().st_size,
                    "sha256": file_sha256(output_path),
                    "passed": True,
                }
            )
        finally:
            for _, bm in constituents:
                bm.free()

    report = {
        "tool": "export_from_manifest.py",
        "source_manifest": str(manifest_path),
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "stl_scale": 1.0,
        "artifact_status": status,
        "artifacts": reports,
        "summary": {
            "artifacts": len(reports),
            "triangles": sum(item["triangles"] for item in reports),
            "bytes": sum(item["bytes"] for item in reports),
            "passed": all(item["passed"] for item in reports),
        },
    }
    report_path = output_dir / "export_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
