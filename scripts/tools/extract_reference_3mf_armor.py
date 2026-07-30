"""Extract armor-shaped donor meshes from the proven 3MF without plate transforms.

The output is local working data under ignored ``.work/``. Meshes remain in
millimeters and are centered as stored by Bambu
Studio; they are shape/scale donors, not anatomically registered parts.
"""

import argparse
import math
from pathlib import Path
import struct
from xml.etree import ElementTree
from zipfile import ZipFile


CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PRODUCTION_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
ARMOR_PREFIXES = (
    "arm",
    "elbow",
    "shoulder",
    "bracket",
    "wrist",
    "forearm",
)


def metadata_value(element, key, default="?"):
    for child in element.findall("metadata"):
        if child.attrib.get("key") == key:
            return child.attrib.get("value", default)
    return default


def transform_point(point, values):
    x, y, z = point
    return (
        x * values[0] + y * values[3] + z * values[6] + values[9],
        x * values[1] + y * values[4] + z * values[7] + values[10],
        x * values[2] + y * values[5] + z * values[8] + values[11],
    )


def triangle_normal(a, b, c):
    left = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    right = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    normal = (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
    length = math.sqrt(sum(value * value for value in normal))
    if length == 0:
        return (0.0, 0.0, 0.0)
    return tuple(value / length for value in normal)


def write_binary_stl(path, vertices, triangles):
    with path.open("wb") as stream:
        stream.write(b"Silverhand 3MF armor donor".ljust(80, b"\0"))
        stream.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            points = [vertices[index] for index in triangle]
            stream.write(struct.pack("<3f", *triangle_normal(*points)))
            for point in points:
                stream.write(struct.pack("<3f", *point))
            stream.write(struct.pack("<H", 0))


def main():
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=repo_root
        / "reference"
        / "johnny_silverhand_arm_scaled_up.3mf",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / ".work" / "reference_3mf_armor_donors",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    core = {"m": CORE_NS, "p": PRODUCTION_NS}
    with ZipFile(args.source) as archive:
        main_model = ElementTree.fromstring(archive.read("3D/3dmodel.model"))
        settings = ElementTree.fromstring(
            archive.read("Metadata/model_settings.config")
        )
        root_objects = {
            element.attrib["id"]: element
            for element in main_model.findall(".//m:resources/m:object", core)
        }
        selected = []
        for configured in settings.findall("object"):
            name = metadata_value(configured, "name")
            lower = name.lower()
            if lower == "assembly" or lower.startswith(ARMOR_PREFIXES):
                selected.append((configured.attrib["id"], name, configured))

        written = []
        for object_id, configured_name, configured in selected:
            root_object = root_objects.get(object_id)
            if root_object is None:
                continue
            vertices = []
            triangles = []
            components = root_object.findall(".//m:component", core)
            for component in components:
                path_key = f"{{{PRODUCTION_NS}}}path"
                target = component.attrib[path_key].lstrip("/")
                external_root = ElementTree.fromstring(archive.read(target))
                external_id = component.attrib["objectid"]
                external_object = next(
                    (
                        item
                        for item in external_root.findall(
                            ".//m:resources/m:object", core
                        )
                        if item.attrib.get("id") == external_id
                    ),
                    None,
                )
                if external_object is None:
                    raise RuntimeError(
                        f"3MF object '{configured_name}' references missing "
                        f"object id '{external_id}' in '{target}'"
                    )
                values = [
                    float(value)
                    for value in component.attrib.get(
                        "transform", "1 0 0 0 1 0 0 0 1 0 0 0"
                    ).split()
                ]
                source_vertices = [
                    (
                        float(vertex.attrib["x"]),
                        float(vertex.attrib["y"]),
                        float(vertex.attrib["z"]),
                    )
                    for vertex in external_object.findall(
                        ".//m:vertices/m:vertex", core
                    )
                ]
                base = len(vertices)
                vertices.extend(
                    transform_point(point, values) for point in source_vertices
                )
                triangles.extend(
                    (
                        base + int(triangle.attrib["v1"]),
                        base + int(triangle.attrib["v2"]),
                        base + int(triangle.attrib["v3"]),
                    )
                    for triangle in external_object.findall(
                        ".//m:triangles/m:triangle", core
                    )
                )
            if not triangles:
                continue
            part = configured.find("part")
            filename = (
                metadata_value(part, "name")
                if part is not None
                else configured_name
            )
            path = args.output / Path(filename).name
            write_binary_stl(path, vertices, triangles)
            written.append((path, len(vertices), len(triangles)))

    for path, vertex_count, triangle_count in written:
        print(
            f"{path.name}: {vertex_count} vertices, "
            f"{triangle_count} triangles"
        )


if __name__ == "__main__":
    main()
