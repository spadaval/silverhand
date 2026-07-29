"""Audit patch and transition boundaries around clearance-failure clusters.

This diagnostic saves no geometry. It reports whether each selected cluster
has a bounded face region whose transition annulus can be reconstructed
without guessing at open-boundary topology.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import cutter_grid, mesh_neighbors  # noqa: E402
from sweep_local_clearance_reconstruction import (  # noqa: E402
    parse_cluster_selection,
    violation_clusters,
)
from try_boundary_preserving_cutter_reconstruction import (  # noqa: E402
    edge_faces,
    expand_face_rings,
    removed_open_boundary_edges,
    transition_edges,
)
from try_cutter_patch_reconstruction import ordered_boundary_groups  # noqa: E402


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=int, required=True)
    parser.add_argument("--clusters", required=True)
    parser.add_argument(
        "--annulus-rings",
        default="1,2,3,4,6,8",
        help="Comma-separated positive face-ring counts.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[separator + 1 :])
    try:
        args.annulus_rings = [
            int(value) for value in args.annulus_rings.split(",")
        ]
    except ValueError as error:
        parser.error(f"--annulus-rings contains a non-integer: {error}")
    if not args.annulus_rings or any(
        value <= 0 for value in args.annulus_rings
    ):
        parser.error("--annulus-rings must contain positive integers")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        actual = "missing" if obj is None else obj.type
        raise RuntimeError(
            f"CLUSTER_TRANSITION_AUDIT: {role} '{name}' has state "
            f"'{actual}', expected MESH"
        )
    return obj


def group_summary(
    edges: list[tuple[int, int]],
) -> dict:
    adjacency = defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    degree_counts = Counter(len(value) for value in adjacency.values())
    if any(degree > 2 for degree in degree_counts):
        unseen = set(adjacency)
        graph_components = []
        while unseen:
            start = unseen.pop()
            stack = [start]
            vertices = {start}
            while stack:
                current = stack.pop()
                for neighbor in adjacency[current]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        vertices.add(neighbor)
                        stack.append(neighbor)
            graph_components.append(len(vertices))
        return {
            "status": "branched",
            "edges": len(edges),
            "vertices": len(adjacency),
            "degree_counts": {
                str(degree): count
                for degree, count in sorted(degree_counts.items())
            },
            "graph_component_vertex_counts": sorted(
                graph_components,
                reverse=True,
            ),
        }
    groups = ordered_boundary_groups(edges)
    return {
        "status": "ordered",
        "edges": len(edges),
        "vertices": len(adjacency),
        "degree_counts": {
            str(degree): count
            for degree, count in sorted(degree_counts.items())
        },
        "groups": [
            {
                "vertices": len(group),
                "edges": len(group) if closed else len(group) - 1,
                "closed": closed,
                "endpoints": [] if closed else [group[0], group[-1]],
            }
            for group, closed in groups
        ],
    }


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")
    vertex_component, components = connected_components(source)
    if not 0 <= args.component < len(components):
        raise RuntimeError(
            f"CLUSTER_TRANSITION_AUDIT: component {args.component} is "
            f"outside 0..{len(components) - 1}"
        )

    points, faces, _ = evaluated_geometry(candidate)
    grid, _ = cutter_grid(cutter)
    target_length = float(candidate["target_length_mm"])
    margins = point_margins(points, target_length, grid)
    neighbors = mesh_neighbors(source.data)
    component = set(components[args.component])
    clusters = violation_clusters(component, margins, neighbors)
    selected_clusters = parse_cluster_selection(
        args.clusters,
        len(clusters),
    )
    component_faces = {
        face_index
        for face_index, face in enumerate(faces)
        if vertex_component[face[0]] == args.component
    }
    linked_faces = edge_faces(faces)
    records = []
    for cluster_index in selected_clusters:
        cluster = set(clusters[cluster_index])
        core_faces = {
            face_index
            for face_index in component_faces
            if any(index in cluster for index in faces[face_index])
        }
        variants = []
        for rings in args.annulus_rings:
            expanded = expand_face_rings(
                core_faces,
                component_faces,
                linked_faces,
                rings,
            )
            variants.append(
                {
                    "annulus_rings": rings,
                    "expanded_faces": len(expanded),
                    "annulus_faces": len(expanded - core_faces),
                    "outer_transition_groups": group_summary(
                        transition_edges(expanded, linked_faces)
                    ),
                    "expanded_open_boundary_groups": group_summary(
                        removed_open_boundary_edges(
                            expanded,
                            linked_faces,
                        )
                    ),
                }
            )
        records.append(
            {
                "cluster": cluster_index,
                "cluster_vertices": len(cluster),
                "core_faces": len(core_faces),
                "core_transition_groups": group_summary(
                    transition_edges(core_faces, linked_faces)
                ),
                "core_open_boundary_groups": group_summary(
                    removed_open_boundary_edges(
                        core_faces,
                        linked_faces,
                    )
                ),
                "variants": variants,
            }
        )

    report = {
        "tool": Path(__file__).name,
        "status": "diagnostic_only_no_geometry_saved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "component": args.component,
        "selected_clusters": selected_clusters,
        "clusters": records,
        "promotion": "NOT_PROMOTED",
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    print(
        f"DONE: audited transition topology for component "
        f"{args.component}; no geometry was saved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
