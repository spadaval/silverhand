"""Create or update the canonical validation cameras in the open blend file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validation_camera_rig import (  # noqa: E402
    DEFAULT_SOURCE,
    DEFAULT_TARGET,
    RIG_VERSION,
    build_camera_rig,
    require_mesh,
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
    parser.add_argument("--resolution-x", type=int, default=700)
    parser.add_argument("--resolution-y", type=int, default=1000)
    parser.add_argument("--margin", type=float, default=1.10)
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the updated rig back to the currently loaded blend file.",
    )
    args = parser.parse_args(arguments)
    if args.resolution_x <= 0 or args.resolution_y <= 0:
        parser.error("camera framing resolution must be positive")
    if args.margin <= 1.0:
        parser.error("--margin must be greater than 1.0")
    return args


def main() -> int:
    args = parse_args()
    source = require_mesh(args.source, "source")
    target = require_mesh(args.target, "target")
    cameras, records = build_camera_rig(
        source,
        target,
        args.resolution_x,
        args.resolution_y,
        args.margin,
    )
    result = {
        "rig_version": RIG_VERSION,
        "source": source.name,
        "target": target.name,
        "camera_count": len(cameras),
        "views": records,
        "saved": False,
    }
    if args.save:
        if not bpy.data.filepath:
            raise RuntimeError(
                "Cannot save validation cameras: the current Blender scene has "
                "no file path"
            )
        status = bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        if "FINISHED" not in status:
            raise RuntimeError(
                "Cannot save validation cameras: Blender save operation "
                f"returned {sorted(status)} for '{bpy.data.filepath}'"
            )
        result["saved"] = True
        result["blend_file"] = bpy.data.filepath
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
