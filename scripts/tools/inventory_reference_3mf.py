"""List named objects and parts in the proven Bambu Studio 3MF reference."""

import argparse
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


def metadata_value(element, key, default="?"):
    for child in element.findall("metadata"):
        if child.attrib.get("key") == key:
            return child.attrib.get("value", default)
    return default


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "reference"
        / "johnny_silverhand_arm_scaled_up.3mf",
    )
    args = parser.parse_args()
    try:
        with ZipFile(args.path) as archive:
            root = ElementTree.fromstring(
                archive.read("Metadata/model_settings.config")
            )
    except (OSError, KeyError, ElementTree.ParseError) as exc:
        raise SystemExit(
            f"Cannot inventory 3MF reference '{args.path}': {exc}"
        ) from exc

    for obj in root.findall("object"):
        parts = []
        for part in obj.findall("part"):
            stat = part.find("mesh_stat")
            face_count = (
                stat.attrib.get("face_count", "?") if stat is not None else "?"
            )
            parts.append(f"{metadata_value(part, 'name')} ({face_count} faces)")
        print(
            f"{obj.attrib.get('id', '?'):>3}  "
            f"{metadata_value(obj, 'name')}: {', '.join(parts)}"
        )


if __name__ == "__main__":
    main()
