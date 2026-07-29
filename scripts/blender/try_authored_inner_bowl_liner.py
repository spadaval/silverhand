"""Validate and construct the mapped component-20 inner-bowl liner.

The exact full-reconstruction mapping is authoritative. Before creating any
geometry, this tool proves that its frozen interface and clearance
requirements are mutually satisfiable. A frozen component-9 interface vertex
inside either current component-20 clearance cluster is a terminal
construction contradiction: moving it violates the interface contract, while
retaining it violates the required two-cluster clearance gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import (  # noqa: E402
    evaluated_geometry,
    point_margins,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    RESERVED_WALL_MM,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, mesh_neighbors  # noqa: E402
from sweep_local_clearance_reconstruction import violation_clusters  # noqa: E402
from try_landmark_sector_retopology import validate_base  # noqa: E402


OPERATION = "AUTHORED_INNER_BOWL_LINER"
EXPECTED_BASE_SHA256 = (
    "ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e"
)
EXPECTED_BASE_SHAPE_KEY = "REPAIR_013_COMPONENT_19_CLUSTER_RIGID"
MAPPING_PATH = Path(
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_full_recon_map/mapping.json"
)
FLOOR_OFFSET_MM = 1.7


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-base-sha256",
        default=EXPECTED_BASE_SHA256,
    )
    parser.add_argument(
        "--required-base-shape-key",
        default=EXPECTED_BASE_SHAPE_KEY,
    )
    parser.add_argument("--save", action="store_true")
    return parser.parse_args(sys.argv[separator + 1 :])


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"{OPERATION}: {role} '{name}' has state '{actual}', expected MESH"
        )
    return obj


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_mapping() -> dict:
    path = (Path.cwd() / MAPPING_PATH).resolve()
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{OPERATION}: cannot read mapping authority '{path}': {error}"
        ) from error
    expected = {
        "status": "PASS_CONDITIONAL_INDEPENDENT_RECONSTRUCTION",
        "rebuild_face_count": 724,
        "retain_face_count": 1409,
        "boundary_edge_count": 127,
        "boundary_group_count": 5,
        "interface_vertex_count": 15,
    }
    actual = {
        "status": mapping.get("status"),
        "rebuild_face_count": mapping.get("reconstruction_scope", {}).get(
            "rebuild_face_count"
        ),
        "retain_face_count": mapping.get("reconstruction_scope", {}).get(
            "retain_face_count"
        ),
        "boundary_edge_count": mapping.get(
            "exact_full_inner_bowl_seam", {}
        ).get("boundary_edge_count"),
        "boundary_group_count": len(
            mapping.get("exact_full_inner_bowl_seam", {}).get(
                "boundary_groups",
                [],
            )
        ),
        "interface_vertex_count": mapping.get(
            "exact_component_9_attachment_landmarks",
            {},
        ).get("vertex_count"),
    }
    if actual != expected:
        raise RuntimeError(
            f"{OPERATION}: mapping authority summary {actual} does not match "
            f"required {expected}"
        )
    groups = mapping["exact_full_inner_bowl_seam"]["boundary_groups"]
    statuses = [group["status"] for group in groups]
    if statuses.count("open") != 3 or statuses.count("closed") != 2:
        raise RuntimeError(
            f"{OPERATION}: seam group statuses are {statuses}, expected "
            "three open routes and two closed aperture loops"
        )
    return mapping


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    repair_base = validate_base(
        candidate,
        args.required_base_sha256,
        args.required_base_shape_key,
    )
    mapping = load_mapping()
    _, components = connected_components(source)
    component = set(components[20])
    points, faces, _ = evaluated_geometry(candidate)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    margins = point_margins(points, target_length, grid)
    clusters = violation_clusters(
        component,
        margins,
        mesh_neighbors(source.data),
    )
    cluster_by_vertex = {
        vertex: cluster_index
        for cluster_index, cluster in enumerate(clusters)
        for vertex in cluster
    }
    interface = mapping["exact_component_9_attachment_landmarks"]
    interface_records = interface["vertex_records"]
    conflicts = []
    for record in interface_records:
        vertex = record["component_20_vertex_id"]
        if vertex not in cluster_by_vertex:
            continue
        conflicts.append(
            {
                "component_20_vertex_id": vertex,
                "component_9_vertex_id": record["component_9_vertex_id"],
                "component_9_distance_mm": record["distance_mm"],
                "clearance_cluster": cluster_by_vertex[vertex],
                "current_cutter_margin_mm": round(margins[vertex], 6),
                "required_floor_margin_mm": FLOOR_OFFSET_MM,
                "minimum_required_motion_mm": round(
                    FLOOR_OFFSET_MM - margins[vertex],
                    6,
                ),
            }
        )
    retain_faces = set(mapping["reconstruction_scope"]["retain_face_ids"])
    rebuild_faces = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    component_faces = {
        index
        for index, face in enumerate(faces)
        if face[0] in component
    }
    partition_valid = (
        retain_faces.isdisjoint(rebuild_faces)
        and retain_faces | rebuild_faces == component_faces
    )
    seam_groups = mapping["exact_full_inner_bowl_seam"]["boundary_groups"]
    report = {
        "tool": Path(__file__).name,
        "status": (
            "evaluation_only_construction_infeasible"
            if conflicts
            else "evaluation_only_authority_satisfiable_not_constructed"
        ),
        "operation": OPERATION,
        "repair_base": repair_base,
        "mapping_authority": {
            "path": str(MAPPING_PATH),
            "sha256": sha256_file(MAPPING_PATH),
            "status": mapping["status"],
        },
        "verified_scope": {
            "component_20_faces": len(component_faces),
            "retain_face_count": len(retain_faces),
            "rebuild_face_count": len(rebuild_faces),
            "partition_exact": partition_valid,
            "seam_edge_count": mapping["exact_full_inner_bowl_seam"][
                "boundary_edge_count"
            ],
            "seam_group_statuses": [
                group["status"] for group in seam_groups
            ],
            "interface_vertex_count": len(interface_records),
            "interface_local_edge_count": len(interface["local_edge_ids"]),
        },
        "current_clearance": {
            "cluster_count": len(clusters),
            "cluster_vertex_counts": [len(cluster) for cluster in clusters],
            "reserved_wall_mm": RESERVED_WALL_MM,
            "required_liner_floor_mm": FLOOR_OFFSET_MM,
        },
        "frozen_interface_clearance_conflicts": conflicts,
        "result": {
            "candidate_created": False,
            "geometry_saved": False,
            "gate_pass": False,
            "reason": (
                f"{OPERATION}: {len(conflicts)} component-9 interface "
                "vertices are both required to remain exact and members of "
                "component-20 clearance clusters; no geometry can freeze "
                "them and clear both clusters simultaneously"
                if conflicts
                else (
                    f"{OPERATION}: mapping constraints are satisfiable; "
                    "construction implementation remains required"
                )
            ),
            "actionable_next_boundary_or_architecture": (
                "Split the coincident elbow interface out of the inner-bowl "
                "clearance gate as an explicitly shared/component-9-owned "
                "junction, or authorize coordinated component-9/component-20 "
                "interface reconstruction. Do not move the 15 vertices while "
                "continuing to claim the frozen-interface contract."
                if conflicts
                else None
            ),
        },
        "objects": None,
        "images": {"generated": False, "reviewed": False},
        "promotion": "NOT_PROMOTED",
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if conflicts:
        print(json.dumps(report, indent=2))
        print(
            f"DONE: authored inner-bowl construction is infeasible under "
            f"{len(conflicts)} frozen-interface clearance conflicts"
        )
        return 0
    raise RuntimeError(
        f"{OPERATION}: authority is satisfiable; this diagnostic must be "
        "extended to construct the requested liner"
    )


if __name__ == "__main__":
    raise SystemExit(main())
