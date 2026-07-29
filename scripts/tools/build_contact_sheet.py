# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pillow==11.3.0",
# ]
# ///
"""Build bounded review sheets from a comparison-render manifest."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from image_sanitization import sanitize_image  # noqa: E402


BACKGROUND = "#071018"
PANEL_BACKGROUND = "#101c29"
TEXT = "#edf3fa"
MUTED_TEXT = "#9fb2c9"
SOURCE_ACCENT = "#8f99a5"
CURRENT_ACCENT = "#12a9b4"

ROLES = (
    ("source", "SOURCE", SOURCE_ACCENT),
    ("current", "CURRENT", CURRENT_ACCENT),
)
VIEWS_PER_PAGE = 4
PAIRS_PER_ROW = 2


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
        help=(
            "review-sheet PNG base; defaults to "
            "comparison_review_sheet.png beside the manifest"
        ),
    )
    parser.add_argument(
        "--cell-width",
        type=int,
        default=360,
        help="width of each source/current image cell",
    )
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=2000,
        help="hard maximum width or height for each review page",
    )
    parser.add_argument(
        "--archival-output",
        type=Path,
        help=(
            "optional full vertical PNG for human archival use; this file "
            "must not be inspected directly by an image model"
        ),
    )
    parser.add_argument(
        "--archival-cell-width",
        type=int,
        default=520,
        help="cell width used only with --archival-output",
    )
    args = parser.parse_args()
    if args.cell_width < 160:
        parser.error("--cell-width must be at least 160 pixels")
    if args.archival_cell_width < 160:
        parser.error("--archival-cell-width must be at least 160 pixels")
    if args.max_dimension < 800:
        parser.error("--max-dimension must be at least 800 pixels")
    for option, path in (
        ("--output", args.output),
        ("--archival-output", args.archival_output),
    ):
        if path is not None and path.suffix.lower() != ".png":
            parser.error(f"{option} must name a PNG file, got '{path}'")
    return args


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def require_mapping(value, context: str) -> dict:
    if not isinstance(value, dict):
        raise RuntimeError(
            f"Cannot build review sheets: '{context}' must be a JSON object"
        )
    return value


def require_list(value, context: str) -> list:
    if not isinstance(value, list):
        raise RuntimeError(
            f"Cannot build review sheets: '{context}' must be a JSON array"
        )
    return value


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(
            f"Cannot build review sheets: manifest '{path}' does not exist"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Cannot build review sheets: failed to read manifest '{path}': "
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


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    selected_font,
) -> tuple[int, int]:
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


def output_name(path: Path, page: int, page_count: int) -> Path:
    if page_count == 1:
        return path
    return path.with_name(f"{path.stem}-{page + 1:02d}{path.suffix}")


def manifest_path(path: Path, manifest_dir: Path) -> str:
    try:
        return str(path.relative_to(manifest_dir))
    except ValueError:
        return str(path)


def page_geometry(
    *,
    cell_width: int,
    cell_aspect: float,
    view_count: int,
    pairs_per_row: int,
) -> dict:
    outer_padding = 24
    cell_gap = 12
    pair_gap = 28
    header_height = 122
    view_label_height = 40
    role_header_height = 32
    row_gap = 18
    footer_height = 88

    cell_height = round(cell_width * cell_aspect)
    pair_width = cell_width * 2 + cell_gap
    pair_columns = min(pairs_per_row, view_count)
    pair_rows = math.ceil(view_count / pair_columns)
    row_height = view_label_height + role_header_height + cell_height
    sheet_width = (
        outer_padding * 2
        + pair_columns * pair_width
        + (pair_columns - 1) * pair_gap
    )
    sheet_height = (
        outer_padding
        + header_height
        + pair_rows * row_height
        + (pair_rows - 1) * row_gap
        + footer_height
        + outer_padding
    )
    return {
        "outer_padding": outer_padding,
        "cell_gap": cell_gap,
        "pair_gap": pair_gap,
        "header_height": header_height,
        "view_label_height": view_label_height,
        "role_header_height": role_header_height,
        "row_gap": row_gap,
        "footer_height": footer_height,
        "cell_height": cell_height,
        "pair_width": pair_width,
        "pair_columns": pair_columns,
        "pair_rows": pair_rows,
        "row_height": row_height,
        "sheet_width": sheet_width,
        "sheet_height": sheet_height,
    }


def render_page(
    *,
    output_path: Path,
    page_views: Sequence[str],
    view_offset: int,
    page_number: int,
    page_count: int,
    total_views: int,
    cell_width: int,
    pairs_per_row: int,
    cell_aspect: float,
    image_paths: dict[tuple[str, str], Path],
    views: dict,
    source: dict,
    target: dict,
    rig_version: object,
    units: object,
    archival: bool,
    max_dimension: int | None,
) -> dict:
    geometry = page_geometry(
        cell_width=cell_width,
        cell_aspect=cell_aspect,
        view_count=len(page_views),
        pairs_per_row=pairs_per_row,
    )
    sheet_width = geometry["sheet_width"]
    sheet_height = geometry["sheet_height"]
    if (
        max_dimension is not None
        and max(sheet_width, sheet_height) > max_dimension
    ):
        raise RuntimeError(
            "Cannot build review sheet: calculated page size "
            f"{sheet_width}x{sheet_height}px exceeds --max-dimension "
            f"{max_dimension}px. Reduce --cell-width from {cell_width}."
        )

    sheet = Image.new("RGB", (sheet_width, sheet_height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title_font = font(30)
    subtitle_font = font(18)
    label_font = font(18)
    role_font = font(16)
    metadata_font = font(15)

    outer_padding = geometry["outer_padding"]
    title = (
        "Silverhand Geometry Comparison - Archival Full Sheet"
        if archival
        else f"Silverhand Geometry Review - {page_number}/{page_count}"
    )
    draw.text(
        (outer_padding, outer_padding),
        title,
        font=title_font,
        fill=TEXT,
    )
    subtitle = (
        "Human archival evidence; do not inspect directly with an image model"
        if archival
        else "Matched source/current cameras · bounded image-model review page"
    )
    draw.text(
        (outer_padding, outer_padding + 43),
        subtitle,
        font=subtitle_font,
        fill=MUTED_TEXT,
    )
    draw.text(
        (outer_padding, outer_padding + 76),
        f"Rig v{rig_version or 'unknown'} · {units or 'unknown'} · "
        f"{len(page_views)} of {total_views} semantic views",
        font=metadata_font,
        fill=MUTED_TEXT,
    )

    content_top = outer_padding + geometry["header_height"]
    for local_index, view in enumerate(page_views):
        row = local_index // geometry["pair_columns"]
        column = local_index % geometry["pair_columns"]
        pair_left = outer_padding + column * (
            geometry["pair_width"] + geometry["pair_gap"]
        )
        pair_top = content_top + row * (
            geometry["row_height"] + geometry["row_gap"]
        )
        view_record = require_mapping(
            views.get(view),
            f"render.views.{view}",
        )
        camera_name = shorten(view_record.get("camera"), 30)
        view_label = (
            f"{view_offset + local_index + 1:02d} "
            f"{pretty_view(view)} · {camera_name}"
        )
        draw.rectangle(
            (
                pair_left,
                pair_top,
                pair_left + geometry["pair_width"],
                pair_top + geometry["view_label_height"],
            ),
            fill=PANEL_BACKGROUND,
        )
        draw.text(
            (pair_left + 10, pair_top + 9),
            view_label,
            font=label_font,
            fill=TEXT,
        )

        role_top = pair_top + geometry["view_label_height"]
        image_top = role_top + geometry["role_header_height"]
        for role_index, (role, label, accent) in enumerate(ROLES):
            left = pair_left + role_index * (
                cell_width + geometry["cell_gap"]
            )
            role_bounds = (
                left,
                role_top,
                left + cell_width,
                role_top + geometry["role_header_height"],
            )
            draw.rectangle(
                role_bounds,
                fill=PANEL_BACKGROUND,
                outline=accent,
                width=2,
            )
            draw_centered(
                draw,
                role_bounds,
                label,
                role_font,
                TEXT,
            )
            with Image.open(image_paths[(view, role)]) as source_image:
                resized = source_image.convert("RGB").resize(
                    (cell_width, geometry["cell_height"]),
                    Image.Resampling.LANCZOS,
                )
                sheet.paste(resized, (left, image_top))
            draw.rectangle(
                (
                    left,
                    image_top,
                    left + cell_width - 1,
                    image_top + geometry["cell_height"] - 1,
                ),
                outline=accent,
                width=2,
            )

    footer_top = sheet_height - outer_padding - geometry["footer_height"]
    source_dimensions = " x ".join(
        str(value) for value in source.get("dimensions_mm", [])
    )
    target_dimensions = " x ".join(
        str(value) for value in target.get("dimensions_mm", [])
    )
    footer_lines = [
        f"Source: {source_dimensions} mm · "
        f"fingerprint {shorten(source.get('geometry_fingerprint'))}",
        f"Current: {target_dimensions} mm · "
        f"fingerprint {shorten(target.get('geometry_fingerprint'))}",
        f"Pillow {pillow_version} · qualitative approval remains human review",
    ]
    for line_index, line in enumerate(footer_lines):
        draw.text(
            (outer_padding, footer_top + line_index * 23),
            line,
            font=metadata_font,
            fill=MUTED_TEXT,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)
    sanitization = sanitize_image(output_path)
    return {
        "path": output_path,
        "views": list(page_views),
        "dimensions_px": [sheet_width, sheet_height],
        "sanitization": sanitization,
    }


def main() -> int:
    args = parse_args()
    manifest_path_value = args.manifest.resolve()
    manifest = load_manifest(manifest_path_value)
    output_dir = manifest_path_value.parent
    output_base = (
        args.output.resolve()
        if args.output is not None
        else output_dir / "comparison_review_sheet.png"
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
            "Cannot build review sheets: expected columns "
            f"['source', 'current'], got {columns!r}"
        )
    if not rows:
        raise RuntimeError(
            "Cannot build review sheets: manifest contains no view rows"
        )

    image_paths = {}
    for item in images:
        item = require_mapping(item, "render.images[]")
        key = (item.get("view"), item.get("role"))
        relative_path = item.get("path")
        if not all(isinstance(value, str) for value in (*key, relative_path)):
            raise RuntimeError(
                "Cannot build review sheets: each image needs string "
                "'view', 'role', and 'path' fields"
            )
        path = output_dir / relative_path
        if not path.is_file():
            raise RuntimeError(
                f"Cannot build review sheets: rendered image '{path}' is "
                "missing"
            )
        image_paths[key] = path

    required_keys = {
        (view, role) for view in rows for role in ("source", "current")
    }
    missing_keys = sorted(required_keys - set(image_paths))
    if missing_keys:
        raise RuntimeError(
            "Cannot build review sheets: manifest is missing render pairs "
            + ", ".join(f"{view}/{role}" for view, role in missing_keys)
        )

    source = require_mapping(manifest.get("source"), "source")
    target = require_mapping(manifest.get("target"), "target")
    views = require_mapping(render.get("views"), "render.views")
    with Image.open(image_paths[(rows[0], "source")]) as sample:
        cell_aspect = sample.height / sample.width

    pages = [
        rows[offset : offset + VIEWS_PER_PAGE]
        for offset in range(0, len(rows), VIEWS_PER_PAGE)
    ]
    review_records = []
    for page_index, page_views in enumerate(pages):
        page_path = output_name(output_base, page_index, len(pages))
        record = render_page(
            output_path=page_path,
            page_views=page_views,
            view_offset=page_index * VIEWS_PER_PAGE,
            page_number=page_index + 1,
            page_count=len(pages),
            total_views=len(rows),
            cell_width=args.cell_width,
            pairs_per_row=PAIRS_PER_ROW,
            cell_aspect=cell_aspect,
            image_paths=image_paths,
            views=views,
            source=source,
            target=target,
            rig_version=manifest.get("rig_version"),
            units=manifest.get("units"),
            archival=False,
            max_dimension=args.max_dimension,
        )
        review_records.append(record)

    archival_record = None
    if args.archival_output is not None:
        archival_record = render_page(
            output_path=args.archival_output.resolve(),
            page_views=rows,
            view_offset=0,
            page_number=1,
            page_count=1,
            total_views=len(rows),
            cell_width=args.archival_cell_width,
            pairs_per_row=1,
            cell_aspect=cell_aspect,
            image_paths=image_paths,
            views=views,
            source=source,
            target=target,
            rig_version=manifest.get("rig_version"),
            units=manifest.get("units"),
            archival=True,
            max_dimension=None,
        )

    manifest_records = [
        {
            **record,
            "path": manifest_path(record["path"], output_dir),
            "direct_image_model_review": record["sanitization"][
                "direct_image_model_review"
            ],
            "detail_hint": "high",
        }
        for record in review_records
    ]
    render["contact_sheet"] = (
        manifest_records[0]["path"]
        if len(manifest_records) == 1
        else None
    )
    render["contact_sheets"] = manifest_records
    render["archival_contact_sheet"] = (
        {
            **archival_record,
            "path": manifest_path(archival_record["path"], output_dir),
            "direct_image_model_review": False,
            "detail_hint": "do_not_inspect_directly",
        }
        if archival_record is not None
        else None
    )
    render["contact_sheet_generator"] = {
        "tool": "build_contact_sheet.py",
        "pillow_version": pillow_version,
        "layout": "two_view_pairs_per_row",
        "views_per_page": VIEWS_PER_PAGE,
        "cell_width": args.cell_width,
        "max_dimension": args.max_dimension,
        "annotated": True,
        "role_labels": ["SOURCE", "CURRENT"],
    }
    manifest_path_value.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    for record in review_records:
        print(record["path"])
    if archival_record is not None:
        print(archival_record["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
