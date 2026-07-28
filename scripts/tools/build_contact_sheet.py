# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pillow==11.3.0",
# ]
# ///
"""Build an annotated validation contact sheet from a render manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version


BACKGROUND = "#071018"
PANEL_BACKGROUND = "#101c29"
TEXT = "#edf3fa"
MUTED_TEXT = "#9fb2c9"
BORDER = "#35435a"
SOURCE_ACCENT = "#8f99a5"
CURRENT_ACCENT = "#12a9b4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="manifest.json emitted by render_geometry_comparison.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output PNG; defaults beside the manifest",
    )
    parser.add_argument(
        "--cell-width",
        type=int,
        default=520,
        help="width of each source/current image cell",
    )
    args = parser.parse_args()
    if args.cell_width < 160:
        parser.error("--cell-width must be at least 160 pixels")
    return args


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def require_mapping(value, context: str) -> dict:
    if not isinstance(value, dict):
        raise RuntimeError(
            f"Cannot build contact sheet: '{context}' must be a JSON object"
        )
    return value


def require_list(value, context: str) -> list:
    if not isinstance(value, list):
        raise RuntimeError(
            f"Cannot build contact sheet: '{context}' must be a JSON array"
        )
    return value


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(
            f"Cannot build contact sheet: manifest '{path}' does not exist"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Cannot build contact sheet: failed to read manifest '{path}': "
            f"{exc}"
        ) from exc
    return require_mapping(value, "manifest")


def shorten(value: object, length: int = 12) -> str:
    text = str(value or "unknown")
    return text if len(text) <= length else text[:length]


def pretty_view(view: str) -> str:
    return view.replace("_", " ").title().replace(
        "Three Quarter",
        "Three-Quarter",
    )


def text_size(draw: ImageDraw.ImageDraw, text: str, selected_font) -> tuple[int, int]:
    bounds = draw.textbbox((0, 0), text, font=selected_font)
    return bounds[2] - bounds[0], bounds[3] - bounds[1]


def draw_centered(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    text: str,
    selected_font,
    fill: str,
) -> None:
    width, height = text_size(draw, text, selected_font)
    left, top, right, bottom = bounds
    draw.text(
        (
            left + (right - left - width) / 2,
            top + (bottom - top - height) / 2,
        ),
        text,
        font=selected_font,
        fill=fill,
    )


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    output_dir = manifest_path.parent
    output_path = (
        args.output.resolve()
        if args.output is not None
        else output_dir / "comparison_contact_sheet.png"
    )

    render = require_mapping(manifest.get("render"), "render")
    layout = require_mapping(
        render.get("contact_sheet_layout"),
        "render.contact_sheet_layout",
    )
    columns = require_list(
        layout.get("columns"),
        "render.contact_sheet_layout.columns",
    )
    rows = require_list(
        layout.get("rows"),
        "render.contact_sheet_layout.rows",
    )
    images = require_list(render.get("images"), "render.images")
    if columns != ["source", "current"]:
        raise RuntimeError(
            "Cannot build contact sheet: expected columns "
            "['source', 'current'], got "
            f"{columns!r}"
        )
    if not rows:
        raise RuntimeError(
            "Cannot build contact sheet: manifest contains no view rows"
        )

    image_paths = {}
    for item in images:
        item = require_mapping(item, "render.images[]")
        key = (item.get("view"), item.get("role"))
        relative_path = item.get("path")
        if not all(isinstance(value, str) for value in (*key, relative_path)):
            raise RuntimeError(
                "Cannot build contact sheet: each image needs string "
                "'view', 'role', and 'path' fields"
            )
        path = output_dir / relative_path
        if not path.is_file():
            raise RuntimeError(
                f"Cannot build contact sheet: rendered image '{path}' is "
                "missing"
            )
        image_paths[key] = path

    required_keys = {
        (view, role) for view in rows for role in ("source", "current")
    }
    missing_keys = sorted(required_keys - set(image_paths))
    if missing_keys:
        raise RuntimeError(
            "Cannot build contact sheet: manifest is missing render pairs "
            + ", ".join(f"{view}/{role}" for view, role in missing_keys)
        )

    source = require_mapping(manifest.get("source"), "source")
    target = require_mapping(manifest.get("target"), "target")
    views = require_mapping(render.get("views"), "render.views")

    with Image.open(image_paths[(rows[0], "source")]) as sample:
        cell_height = round(args.cell_width * sample.height / sample.width)

    outer_padding = 24
    column_gap = 18
    header_height = 158
    column_header_height = 48
    row_label_height = 44
    row_gap = 18
    footer_height = 92
    sheet_width = (
        outer_padding * 2 + args.cell_width * 2 + column_gap
    )
    row_height = row_label_height + cell_height
    sheet_height = (
        outer_padding
        + header_height
        + column_header_height
        + len(rows) * row_height
        + (len(rows) - 1) * row_gap
        + footer_height
        + outer_padding
    )

    sheet = Image.new("RGB", (sheet_width, sheet_height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title_font = font(36)
    subtitle_font = font(20)
    heading_font = font(24)
    label_font = font(20)
    metadata_font = font(16)

    draw.text(
        (outer_padding, outer_padding),
        "Silverhand Main-Geometry Comparison",
        font=title_font,
        fill=TEXT,
    )
    draw.text(
        (outer_padding, outer_padding + 52),
        "Exact matched orthographic camera per source/current pair",
        font=subtitle_font,
        fill=MUTED_TEXT,
    )
    draw.text(
        (outer_padding, outer_padding + 88),
        f"Rig v{manifest.get('rig_version', 'unknown')}  |  "
        f"{manifest.get('units', 'unknown')}  |  "
        f"{len(rows)} semantic views",
        font=metadata_font,
        fill=MUTED_TEXT,
    )

    content_top = outer_padding + header_height
    source_left = outer_padding
    current_left = outer_padding + args.cell_width + column_gap
    for left, label, accent in (
        (source_left, f"SOURCE | {source.get('object')}", SOURCE_ACCENT),
        (current_left, f"CURRENT | {target.get('object')}", CURRENT_ACCENT),
    ):
        draw.rectangle(
            (
                left,
                content_top,
                left + args.cell_width,
                content_top + column_header_height,
            ),
            fill=PANEL_BACKGROUND,
            outline=accent,
            width=2,
        )
        draw_centered(
            draw,
            (
                left,
                content_top,
                left + args.cell_width,
                content_top + column_header_height,
            ),
            label,
            heading_font,
            TEXT,
        )

    row_top = content_top + column_header_height
    for index, view in enumerate(rows):
        view_record = require_mapping(
            views.get(view),
            f"render.views.{view}",
        )
        camera_name = view_record.get("camera", "unknown camera")
        row_label = f"{index + 1:02d}  {pretty_view(view)}  -  {camera_name}"
        draw.rectangle(
            (
                outer_padding,
                row_top,
                sheet_width - outer_padding,
                row_top + row_label_height,
            ),
            fill=PANEL_BACKGROUND,
        )
        draw.text(
            (outer_padding + 12, row_top + 10),
            row_label,
            font=label_font,
            fill=TEXT,
        )

        image_top = row_top + row_label_height
        for left, role, accent in (
            (source_left, "source", SOURCE_ACCENT),
            (current_left, "current", CURRENT_ACCENT),
        ):
            with Image.open(image_paths[(view, role)]) as source_image:
                resized = source_image.convert("RGB").resize(
                    (args.cell_width, cell_height),
                    Image.Resampling.LANCZOS,
                )
                sheet.paste(resized, (left, image_top))
            draw.rectangle(
                (
                    left,
                    image_top,
                    left + args.cell_width - 1,
                    image_top + cell_height - 1,
                ),
                outline=accent,
                width=2,
            )
        row_top += row_height + row_gap

    footer_top = sheet_height - outer_padding - footer_height
    source_dimensions = " x ".join(
        str(value) for value in source.get("dimensions_mm", [])
    )
    target_dimensions = " x ".join(
        str(value) for value in target.get("dimensions_mm", [])
    )
    footer_lines = [
        f"Source: {source_dimensions} mm  |  "
        f"fingerprint {shorten(source.get('geometry_fingerprint'))}",
        f"Current: {target_dimensions} mm  |  "
        f"fingerprint {shorten(target.get('geometry_fingerprint'))}",
        f"Generated with Pillow {pillow_version}; qualitative approval remains "
        "a human review.",
    ]
    for line_index, line in enumerate(footer_lines):
        draw.text(
            (outer_padding, footer_top + line_index * 25),
            line,
            font=metadata_font,
            fill=MUTED_TEXT,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)
    render["contact_sheet"] = output_path.name
    render["contact_sheet_generator"] = {
        "tool": "build_contact_sheet.py",
        "pillow_version": pillow_version,
        "cell_width": args.cell_width,
        "annotated": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
