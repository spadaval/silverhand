"""Sanitize generated raster images with ImageMagick."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess


MAX_IMAGE_MODEL_BYTES = 10_000_000


def sanitize_image(path: Path) -> dict[str, object]:
    """Replace a generated PNG or JPEG with a plain, sanitized derivative."""
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(
            f"Cannot sanitize generated image '{path}': file does not exist"
        )

    magick = os.environ.get("MAGICK_PATH") or shutil.which("magick")
    if not magick:
        raise RuntimeError(
            f"Cannot sanitize generated image '{path}': ImageMagick executable "
            "'magick' was not found. Install ImageMagick or set MAGICK_PATH."
        )

    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise RuntimeError(
            f"Cannot sanitize generated image '{path}': unsupported output "
            f"extension '{path.suffix}'; expected PNG or JPEG"
        )

    temporary = path.with_name(
        f".{path.stem}.sanitizing-{os.getpid()}{suffix}"
    )
    command = [
        magick,
        str(path),
        "-auto-orient",
        "-colorspace",
        "sRGB",
        "-strip",
        "-alpha",
        "off",
        "-depth",
        "8",
        "-type",
        "TrueColor",
    ]
    if suffix == ".png":
        command.extend(
            [
                "-define",
                "png:bit-depth=8",
                "-define",
                "png:color-type=2",
            ]
        )
    command.append(str(temporary))

    try:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise RuntimeError(
                f"Cannot sanitize generated image '{path}': failed to execute "
                f"ImageMagick command {shlex.join(command)}: {exc}"
            ) from exc
        if completed.returncode != 0:
            reason = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                f"Cannot sanitize generated image '{path}': ImageMagick "
                f"command failed with exit code {completed.returncode}: "
                f"{shlex.join(command)}"
                + (f"; output: {reason}" if reason else "")
            )
        if not temporary.is_file():
            raise RuntimeError(
                f"Cannot sanitize generated image '{path}': ImageMagick "
                f"reported success but did not create '{temporary}'"
            )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()

    size_bytes = path.stat().st_size
    return {
        "tool": "ImageMagick",
        "metadata_stripped": True,
        "orientation_normalized": True,
        "colorspace": "sRGB",
        "bit_depth": 8,
        "alpha": False,
        "size_bytes": size_bytes,
        "direct_image_model_review": size_bytes <= MAX_IMAGE_MODEL_BYTES,
    }
