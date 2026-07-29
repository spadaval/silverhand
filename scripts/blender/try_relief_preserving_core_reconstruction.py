"""Create an evaluation-only relief-preserving translated core.

The selected clearance-failure cluster must touch a face patch with one closed
transition loop and no existing open boundary. The source patch is translated
rigidly, preserving all of its local relief, and reconnected to the unchanged
surface through an explicit layered annulus. The active candidate is not
edited.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import evaluated_geometry, point_margins  # noqa: E402
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, mesh_neighbors  # noqa: E402
from sweep_cluster_rigid_clearance import cluster_translation  # noqa: E402
from sweep_local_clearance_reconstruction import (  # noqa: E402
    TOLERANCE_MM,
    parse_cluster_selection,
    violation_clusters,
)
from try_boundary_preserving_cutter_reconstruction import (  # noqa: E402
    edge_faces,
    orientation_audit,
    orient_transition_chain,
    removed_open_boundary_edges,
    transition_edges,
)
from try_cutter_patch_reconstruction import (  # noqa: E402
    REVIEW_COLLECTION,
    create_object,
    ensure_collection,
    mesh_audit,
    ordered_boundary_groups,
    overlap_pairs,
)


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--cluster", type=int, required=True)
    parser.add_argument("--annulus-layers", type=int, default=4)
    parser.add_argument("--maximum-translation-mm", type=float, default=100.0)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(sys.argv[separator + 1 :])
    if args.annulus_layers < 1:
        parser.error("--annulus-layers must be positive")
    if args.maximum_translation_mm <= 0:
        parser.error("--maximum-translation-mm must be positive")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"RELIEF_CORE_TRIAL: {role} '{name}' has state '{actual}', "
            "expected MESH"
        )
    return obj


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    vertex_component, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"RELIEF_CORE_TRIAL: component {args.component} is outside "
            f"0..{len(components) - 1}"
        )

    component = set(components[args.component])
    before, faces, material_indices = evaluated_geometry(candidate)
    cutter_points, cutter_faces, _ = evaluated_geometry(cutter)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    before_margins = point_margins(before, target_length, grid)
    clusters = violation_clusters(
        component,
        before_margins,
        mesh_neighbors(source.data),
    )
    selected = parse_cluster_selection(
        str(args.cluster),
        len(clusters),
    )
    cluster = clusters[selected[0]]
    direction, translation = cluster_translation(
        cluster,
        before,
        target_length,
        grid,
        args.maximum_translation_mm,
    )

    component_faces = {
        face_index
        for face_index, face in enumerate(faces)
        if vertex_component[face[0]] == args.component
    }
    core_faces = {
        face_index
        for face_index in component_faces
        if any(index in cluster for index in faces[face_index])
    }
    linked_faces = edge_faces(faces)
    transition_groups = ordered_boundary_groups(
        transition_edges(core_faces, linked_faces)
    )
    open_groups = ordered_boundary_groups(
        removed_open_boundary_edges(core_faces, linked_faces)
    )
    if len(transition_groups) != 1 or not transition_groups[0][1]:
        raise RuntimeError(
            "RELIEF_CORE_TRIAL: translated core requires exactly one closed "
            f"transition loop, got "
            f"{[(len(group), closed) for group, closed in transition_groups]}"
        )
    if open_groups:
        raise RuntimeError(
            "RELIEF_CORE_TRIAL: translated core must not touch an existing "
            f"open boundary, got "
            f"{[(len(group), closed) for group, closed in open_groups]}"
        )
    boundary = orient_transition_chain(
        transition_groups[0][0],
        core_faces,
        faces,
        linked_faces,
    )

    core_vertices = sorted(
        {
            index
            for face_index in core_faces
            for index in faces[face_index]
        }
    )
    kept_records = [
        (face, material_indices[index])
        for index, face in enumerate(faces)
        if index not in core_faces
    ]
    kept_vertices = sorted(
        {
            index
            for face, _ in kept_records
            for index in face
        }
    )
    remap = {
        source_index: target_index
        for target_index, source_index in enumerate(kept_vertices)
    }
    result_points = [before[index].copy() for index in kept_vertices]
    translated = {}
    for index in core_vertices:
        translated[index] = len(result_points)
        result_points.append(before[index] + direction * translation)

    result_faces = [
        tuple(remap[index] for index in face)
        for face, _ in kept_records
    ]
    result_materials = [material for _, material in kept_records]
    result_faces.extend(
        tuple(translated[index] for index in faces[face_index])
        for face_index in sorted(core_faces)
    )
    result_materials.extend(
        material_indices[face_index]
        for face_index in sorted(core_faces)
    )

    boundary_rows = [[remap[index] for index in boundary]]
    for layer in range(1, args.annulus_layers):
        factor = layer / args.annulus_layers
        row = []
        for index in boundary:
            row.append(len(result_points))
            result_points.append(
                before[index] + direction * translation * factor
            )
        boundary_rows.append(row)
    boundary_rows.append([translated[index] for index in boundary])

    bridge_material = material_indices[next(iter(core_faces))]
    bridge_face_count = 0
    for first_row, second_row in zip(
        boundary_rows,
        boundary_rows[1:],
    ):
        for offset, first in enumerate(first_row):
            following = (offset + 1) % len(first_row)
            second = first_row[following]
            translated_second = second_row[following]
            translated_first = second_row[offset]
            result_faces.extend(
                (
                    (first, second, translated_second),
                    (first, translated_second, translated_first),
                )
            )
            result_materials.extend((bridge_material, bridge_material))
            bridge_face_count += 2

    collection = ensure_collection(REVIEW_COLLECTION)
    before_obj = create_object(
        f"{args.prefix}_BEFORE",
        before,
        faces,
        material_indices,
        list(candidate.data.materials),
        collection,
    )
    after_obj = create_object(
        f"{args.prefix}_AFTER",
        result_points,
        result_faces,
        result_materials,
        list(candidate.data.materials),
        collection,
    )
    after_margins = point_margins(result_points, target_length, grid)
    before_overlaps = overlap_pairs(
        before,
        faces,
        cutter_points,
        cutter_faces,
    )
    after_overlaps = overlap_pairs(
        result_points,
        result_faces,
        cutter_points,
        cutter_faces,
    )
    before_audit = mesh_audit(before_obj)
    after_audit = mesh_audit(after_obj)
    report = {
        "tool": Path(__file__).name,
        "status": "evaluation_only_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "cluster": selected[0],
        "source_core": {
            "cluster_vertices": len(cluster),
            "faces": len(core_faces),
            "vertices": len(core_vertices),
            "transition_edges": len(boundary),
        },
        "motion": {
            "mode": "rigid_relief_preserving_translation",
            "direction": [round(value, 6) for value in direction],
            "translation_mm": round(translation, 6),
        },
        "annulus": {
            "layers": args.annulus_layers,
            "faces": bridge_face_count,
        },
        "clearance": {
            "before_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in before_margins
            ),
            "after_vertices_below_cutter": sum(
                margin < -TOLERANCE_MM for margin in after_margins
            ),
            "before_triangle_overlaps": len(before_overlaps),
            "after_triangle_overlaps": len(after_overlaps),
        },
        "objects": {
            "before": {
                "name": before_obj.name,
                "audit": before_audit,
                "orientation": orientation_audit(before_obj),
            },
            "after": {
                "name": after_obj.name,
                "audit": after_audit,
                "orientation": orientation_audit(after_obj),
            },
        },
        "topology_result": {
            "connected_component_delta": (
                after_audit["connected_components"]
                - before_audit["connected_components"]
            ),
            "boundary_edge_delta": (
                after_audit["boundary_edges"]
                - before_audit["boundary_edges"]
            ),
            "nonmanifold_edge_delta": (
                after_audit["nonmanifold_edges"]
                - before_audit["nonmanifold_edges"]
            ),
        },
        "qualitative_review": "PENDING",
        "promotion": "NOT_PROMOTED",
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        "DONE: created relief-preserving translated-core trial for "
        f"component {args.component} cluster {selected[0]}; qualitative "
        "review remains PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
