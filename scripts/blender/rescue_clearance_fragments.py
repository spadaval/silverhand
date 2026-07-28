"""Create a reversible, bounded rescue of fitted-surface clearance failures.

The script operates on the anatomy-led fitted-surface experiment. It preserves
the pre-rescue candidate as review evidence, creates one relative rescue shape
key, and changes only:

* vertices below the clearance cutter plus the reserved inward wall allowance;
* a short topology-neighbor falloff needed to avoid an abrupt mask boundary.

It does not delete faces, split components, remesh, Boolean, solidify, or move
whole components independently. Run it on an ignored working .blend.
"""

from __future__ import annotations

import argparse
import json
from math import atan2, cos, pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_static_fit_prototype import (  # noqa: E402
    ANGULAR_SAMPLES,
    CANDIDATE_NAME,
    CUTTER_NAME,
    RESERVED_WALL_MM,
    SOURCE_AXIS,
    SOURCE_NAME,
    SOURCE_WRIST,
    connected_components,
    evaluated_world_points,
    geometry_fingerprint,
    percentile,
    polygon_indices,
    sample_grid,
    source_frame,
    triangle_deformation_report,
)
from validation_camera_rig import VIEW_DIRECTIONS  # noqa: E402


RESCUE_KEY_NAME = "FRAGMENT_RESCUE_CLEARANCE"
PRE_RESCUE_NAME = "EVAL_STATIC_FIT_PRE_RESCUE"
MASK_GROUP_NAME = "RESCUE_MASK_CLEARANCE"
REVIEW_COLLECTION = "30_REVIEW"
MAX_ORIENTATION_DEFERRAL_ROUNDS = 8
GEOMETRIC_TOLERANCE_MM = 1.0e-4


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--reserved-margin-mm",
        type=float,
        default=RESERVED_WALL_MM,
        help=(
            "Required fitted-surface distance outside the clearance cutter; "
            "defaults to the wall allowance reserved by the static-fit build"
        ),
    )
    parser.add_argument(
        "--diffusion-iterations",
        type=int,
        default=3,
        help="Number of one-edge topology falloff passes",
    )
    parser.add_argument(
        "--diffusion-factor",
        type=float,
        default=0.55,
        help="Neighbor displacement fraction propagated per falloff pass",
    )
    parser.add_argument(
        "--depth-preservation",
        type=float,
        default=0.5,
        help=(
            "Fraction of radial depth retained inside each connected hard-mask "
            "patch: 0 projects each vertex independently; 1 gives every hard "
            "vertex the patch's maximum required lift"
        ),
    )
    parser.add_argument(
        "--mask-threshold-mm",
        type=float,
        default=0.01,
        help="Minimum propagated displacement recorded in the rescue mask",
    )
    parser.add_argument(
        "--protect-visible",
        action="store_true",
        help=(
            "Lock vertices belonging to a face visible from any canonical "
            "non-axial exterior review direction"
        ),
    )
    parser.add_argument(
        "--maximum-hard-lift-mm",
        type=float,
        default=None,
        help=(
            "Defer vertices requiring a larger radial lift instead of forcing "
            "a destructive rescue; omit to attempt every failure"
        ),
    )
    parser.add_argument(
        "--defer-negative-orientation",
        action="store_true",
        help=(
            "Iteratively defer topology neighborhoods whose tentative rescue "
            "turns a triangle more than 90 degrees from the pre-rescue surface"
        ),
    )
    parser.add_argument(
        "--orientation-deferral-rings",
        type=int,
        default=1,
        help=(
            "Topology rings deferred around each negative-orientation "
            "triangle; used only with --defer-negative-orientation"
        ),
    )
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(arguments)
    if args.reserved_margin_mm < 0.0:
        parser.error("--reserved-margin-mm must be non-negative")
    if args.diffusion_iterations < 0:
        parser.error("--diffusion-iterations must be non-negative")
    if not 0.0 <= args.diffusion_factor <= 1.0:
        parser.error("--diffusion-factor must be between 0 and 1")
    if not 0.0 <= args.depth_preservation <= 1.0:
        parser.error("--depth-preservation must be between 0 and 1")
    if args.mask_threshold_mm <= 0.0:
        parser.error("--mask-threshold-mm must be positive")
    if (
        args.maximum_hard_lift_mm is not None
        and args.maximum_hard_lift_mm <= 0.0
    ):
        parser.error("--maximum-hard-lift-mm must be positive")
    if args.orientation_deferral_rings < 0:
        parser.error("--orientation-deferral-rings must be non-negative")
    return args


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot rescue clearance fragments: {role} mesh '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot rescue clearance fragments: {role} object '{name}' has "
            f"type '{obj.type}', expected 'MESH'"
        )
    return obj


def remove_object(name: str) -> None:
    obj = bpy.data.objects.get(name)
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def reset_previous_rescue(candidate: bpy.types.Object) -> None:
    keys = candidate.data.shape_keys
    if keys is not None:
        rescue = keys.key_blocks.get(RESCUE_KEY_NAME)
        if rescue is not None:
            candidate.shape_key_remove(rescue)
    group = candidate.vertex_groups.get(MASK_GROUP_NAME)
    if group is not None:
        candidate.vertex_groups.remove(group)
    remove_object(PRE_RESCUE_NAME)


def preserve_pre_rescue(candidate: bpy.types.Object) -> bpy.types.Object:
    pre_rescue = candidate.copy()
    pre_rescue.data = candidate.data.copy()
    pre_rescue.name = PRE_RESCUE_NAME
    pre_rescue.data.name = f"{PRE_RESCUE_NAME}_MESH"
    ensure_collection(REVIEW_COLLECTION).objects.link(pre_rescue)
    pre_rescue.color = (0.22, 0.25, 0.30, 1.0)
    pre_rescue.hide_render = True
    pre_rescue.hide_set(True)
    pre_rescue["role"] = "pre-rescue fitted-surface comparison"
    pre_rescue["source_object"] = candidate.name
    pre_rescue["printable"] = False
    pre_rescue["status"] = "evaluation_only"
    return pre_rescue


def cutter_grid(
    cutter: bpy.types.Object,
) -> tuple[list[list[float]], list[Vector]]:
    vertices = [
        cutter.matrix_world @ vertex.co for vertex in cutter.data.vertices
    ]
    if len(vertices) % ANGULAR_SAMPLES != 0:
        raise RuntimeError(
            f"Cannot rescue clearance fragments: cutter '{cutter.name}' has "
            f"{len(vertices)} vertices, not a whole number of "
            f"{ANGULAR_SAMPLES}-vertex rings"
        )
    ring_count = len(vertices) // ANGULAR_SAMPLES
    if ring_count < 2:
        raise RuntimeError(
            f"Cannot rescue clearance fragments: cutter '{cutter.name}' has "
            f"only {ring_count} profile ring(s)"
        )
    grid = []
    for station in range(ring_count):
        ring = vertices[
            station * ANGULAR_SAMPLES : (station + 1) * ANGULAR_SAMPLES
        ]
        grid.append(
            [
                (
                    point
                    - SOURCE_WRIST
                    - SOURCE_AXIS
                    * (point - SOURCE_WRIST).dot(SOURCE_AXIS)
                ).length
                for point in ring
            ]
        )
    return grid, vertices


def radial_coordinates(
    point: Vector,
    target_length: float,
) -> tuple[float, float, float, Vector]:
    normal, binormal = source_frame()
    offset = point - SOURCE_WRIST
    distance = offset.dot(SOURCE_AXIS)
    radial = offset - SOURCE_AXIS * distance
    radius = radial.length
    if radius <= 1.0e-8:
        raise RuntimeError(
            "Cannot rescue clearance fragments: fitted-surface point lies on "
            "the construction axis"
        )
    angle = (
        atan2(radial.dot(binormal), radial.dot(normal))
        % (2.0 * pi)
    )
    normalized = max(0.0, min(1.0, distance / target_length))
    return normalized, angle, radius, radial / radius


def mesh_neighbors(mesh: bpy.types.Mesh) -> list[list[int]]:
    neighbors = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        first, second = edge.vertices
        neighbors[first].append(second)
        neighbors[second].append(first)
    return neighbors


def hard_mask_clusters(
    hard_mask: list[bool],
    neighbors: list[list[int]],
) -> list[list[int]]:
    unseen = {
        index for index, active in enumerate(hard_mask) if active
    }
    clusters = []
    while unseen:
        start = unseen.pop()
        stack = [start]
        cluster = []
        while stack:
            current = stack.pop()
            cluster.append(current)
            for neighbor in neighbors[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        clusters.append(sorted(cluster))
    return clusters


def core_displacements(
    required: list[float],
    clusters: list[list[int]],
    depth_preservation: float,
) -> list[float]:
    core = required[:]
    for cluster in clusters:
        maximum = max(required[index] for index in cluster)
        for index in cluster:
            core[index] = (
                required[index]
                + depth_preservation * (maximum - required[index])
            )
    return core


def diffuse_displacements(
    required: list[float],
    core: list[float],
    neighbors: list[list[int]],
    locked: list[bool],
    iterations: int,
    factor: float,
) -> list[float]:
    displacement = core[:]
    for _ in range(iterations):
        updated = displacement[:]
        for index, adjacent in enumerate(neighbors):
            if locked[index]:
                updated[index] = 0.0
                continue
            if not adjacent:
                continue
            propagated = (
                sum(displacement[neighbor] for neighbor in adjacent)
                / len(adjacent)
                * factor
            )
            updated[index] = max(
                required[index],
                core[index],
                propagated,
            )
        displacement = updated
    return displacement


def visible_face_mask(
    points: list[Vector],
    faces: list[tuple[int, ...]],
) -> list[bool]:
    tree = BVHTree.FromPolygons(
        points,
        faces,
        all_triangles=False,
    )
    spans = [
        max(point[axis] for point in points)
        - min(point[axis] for point in points)
        for axis in range(3)
    ]
    ray_distance = max(spans) * 4.0
    directions = [
        direction.normalized()
        for name, direction in VIEW_DIRECTIONS.items()
        if name not in {"wrist_axial", "bicep_axial"}
    ]
    visible = [False] * len(faces)
    for face_index, face in enumerate(faces):
        centroid = sum(
            (points[index] for index in face),
            Vector(),
        ) / len(face)
        for direction in directions:
            origin = centroid + direction * ray_distance
            hit = tree.ray_cast(
                origin,
                -direction,
                ray_distance * 2.0,
            )
            if hit[2] == face_index:
                visible[face_index] = True
                break
    return visible


def locked_vertices_from_faces(
    vertex_count: int,
    faces: list[tuple[int, ...]],
    visible_faces: list[bool],
) -> list[bool]:
    locked = [False] * vertex_count
    for face, visible in zip(faces, visible_faces):
        if visible:
            for index in face:
                locked[index] = True
    return locked


def edge_ratio_report(
    mesh: bpy.types.Mesh,
    before: list[Vector],
    after: list[Vector],
) -> dict:
    ratios = []
    for edge in mesh.edges:
        first, second = edge.vertices
        original = (before[first] - before[second]).length
        if original <= 1.0e-9:
            continue
        ratios.append(
            (after[first] - after[second]).length / original
        )
    return {
        "minimum": round(min(ratios), 6),
        "p05": round(percentile(ratios, 0.05), 6),
        "median": round(percentile(ratios, 0.5), 6),
        "p95": round(percentile(ratios, 0.95), 6),
        "maximum": round(max(ratios), 6),
    }


def index_ranges(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []
    ranges = []
    start = previous = indices[0]
    for index in indices[1:]:
        if index == previous + 1:
            previous = index
            continue
        ranges.append([start, previous])
        start = previous = index
    ranges.append([start, previous])
    return ranges


def component_report(
    source: bpy.types.Object,
    hard_mask: list[bool],
    changed_mask: list[bool],
    displacement: list[float],
) -> list[dict]:
    vertex_component, components = connected_components(source)
    source_points = [
        source.matrix_world @ vertex.co for vertex in source.data.vertices
    ]
    affected = []
    for component, vertices in enumerate(components):
        hard = [index for index in vertices if hard_mask[index]]
        changed = [index for index in vertices if changed_mask[index]]
        if not changed:
            continue
        stations = [
            (source_points[index] - SOURCE_WRIST).dot(SOURCE_AXIS)
            for index in changed
        ]
        affected.append(
            {
                "component": component,
                "component_vertices": len(vertices),
                "hard_mask_vertices": len(hard),
                "changed_vertices": len(changed),
                "changed_station_range_mm": [
                    round(min(stations), 3),
                    round(max(stations), 3),
                ],
                "maximum_displacement_mm": round(
                    max(displacement[index] for index in changed),
                    6,
                ),
                "changed_vertex_index_ranges": index_ranges(changed),
            }
        )
    return affected


def clearance_component_report(
    source: bpy.types.Object,
    before_margins: list[float],
    after_margins: list[float],
    reserved_margin_mm: float,
    depth_deferred: list[bool],
) -> list[dict]:
    _, components = connected_components(source)
    affected = []
    for component, vertices in enumerate(components):
        before_reserved = [
            index
            for index in vertices
            if (
                before_margins[index]
                < reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
            )
        ]
        if not before_reserved:
            continue
        after_cutter = [
            index
            for index in vertices
            if after_margins[index] < -GEOMETRIC_TOLERANCE_MM
        ]
        after_reserved = [
            index
            for index in vertices
            if (
                after_margins[index]
                < reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
            )
        ]
        deferred = [
            index for index in vertices if depth_deferred[index]
        ]
        affected.append(
            {
                "component": component,
                "component_vertices": len(vertices),
                "pre_rescue_below_reserved_margin": len(before_reserved),
                "post_rescue_below_cutter": len(after_cutter),
                "post_rescue_below_reserved_margin": len(after_reserved),
                "depth_deferred_vertices": len(deferred),
                "minimum_post_rescue_cutter_margin_mm": round(
                    min(after_margins[index] for index in vertices),
                    6,
                ),
            }
        )
    return affected


def negative_orientation_locators(
    source: bpy.types.Object,
    before: list[Vector],
    after: list[Vector],
    faces: list[tuple[int, ...]],
) -> dict:
    vertex_component, _ = connected_components(source)
    locators = []
    counts: dict[int, int] = {}
    for face_index, face in enumerate(faces):
        component = vertex_component[face[0]]
        for offset in range(1, len(face) - 1):
            indices = (face[0], face[offset], face[offset + 1])
            before_cross = (
                before[indices[1]] - before[indices[0]]
            ).cross(before[indices[2]] - before[indices[0]])
            after_cross = (
                after[indices[1]] - after[indices[0]]
            ).cross(after[indices[2]] - after[indices[0]])
            if before_cross.length <= 1.0e-9 or after_cross.length <= 1.0e-9:
                continue
            dot = before_cross.normalized().dot(after_cross.normalized())
            if dot >= 0.0:
                continue
            counts[component] = counts.get(component, 0) + 1
            locators.append(
                {
                    "component": component,
                    "face": face_index,
                    "triangle_vertices": list(indices),
                    "normal_dot": round(dot, 6),
                }
            )
    return {
        "count": len(locators),
        "counts_by_component": [
            {"component": component, "triangles_below_zero": count}
            for component, count in sorted(counts.items())
        ],
        "locators": locators,
    }


def expanded_vertex_mask(
    vertex_count: int,
    seed_indices: set[int],
    neighbors: list[list[int]],
    rings: int,
) -> list[bool]:
    selected = set(seed_indices)
    frontier = set(seed_indices)
    for _ in range(rings):
        following = {
            neighbor
            for index in frontier
            for neighbor in neighbors[index]
            if neighbor not in selected
        }
        selected.update(following)
        frontier = following
        if not frontier:
            break
    return [index in selected for index in range(vertex_count)]


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    cutter = require_mesh(CUTTER_NAME, "clearance cutter")

    if candidate.data.shape_keys is None:
        raise RuntimeError(
            f"Cannot rescue clearance fragments: candidate '{candidate.name}' "
            "has no shape keys"
        )
    fitted = candidate.data.shape_keys.key_blocks.get(
        "STATIC_ANATOMICAL_FIT"
    )
    if fitted is None:
        raise RuntimeError(
            f"Cannot rescue clearance fragments: candidate '{candidate.name}' "
            "has no 'STATIC_ANATOMICAL_FIT' shape key"
        )
    target_length = float(candidate.get("target_length_mm", 0.0))
    if target_length <= 0.0:
        raise RuntimeError(
            f"Cannot rescue clearance fragments: candidate '{candidate.name}' "
            "has no positive 'target_length_mm' property"
        )

    reset_previous_rescue(candidate)
    fitted.value = 1.0
    bpy.context.view_layer.update()
    before = evaluated_world_points(candidate)
    pre_rescue = preserve_pre_rescue(candidate)
    faces = polygon_indices(candidate)
    visible_faces = (
        visible_face_mask(before, faces)
        if args.protect_visible
        else [False] * len(faces)
    )
    visibility_locked = locked_vertices_from_faces(
        len(candidate.data.vertices),
        faces,
        visible_faces,
    )

    grid, cutter_vertices = cutter_grid(cutter)
    raw_required = []
    directions = []
    before_cutter_margins = []
    for point in before:
        normalized, angle, radius, direction = radial_coordinates(
            point,
            target_length,
        )
        cutter_radius = sample_grid(grid, normalized, angle)
        margin = radius - cutter_radius
        before_cutter_margins.append(margin)
        raw_required.append(
            max(0.0, args.reserved_margin_mm - margin)
        )
        directions.append(direction)

    depth_deferred = [
        (
            args.maximum_hard_lift_mm is not None
            and value > args.maximum_hard_lift_mm
        )
        for value in raw_required
    ]
    base_locked = [
        visibility_locked[index] or depth_deferred[index]
        for index in range(len(raw_required))
    ]
    neighbors = mesh_neighbors(candidate.data)
    quality_deferred = [False] * len(raw_required)
    orientation_deferral_rounds = []
    while True:
        locked = [
            base_locked[index] or quality_deferred[index]
            for index in range(len(raw_required))
        ]
        required = [
            0.0 if locked[index] else raw_required[index]
            for index in range(len(raw_required))
        ]
        hard_mask = [value > 1.0e-8 for value in required]
        clusters = hard_mask_clusters(hard_mask, neighbors)
        core = core_displacements(
            required,
            clusters,
            args.depth_preservation,
        )
        displacement = diffuse_displacements(
            required,
            core,
            neighbors,
            locked,
            args.diffusion_iterations,
            args.diffusion_factor,
        )
        rescued_points = [
            point + direction * value
            for point, direction, value in zip(
                before,
                directions,
                displacement,
            )
        ]
        tentative_locators = negative_orientation_locators(
            source,
            before,
            rescued_points,
            faces,
        )
        if (
            not args.defer_negative_orientation
            or tentative_locators["count"] == 0
            or len(orientation_deferral_rounds)
            >= MAX_ORIENTATION_DEFERRAL_ROUNDS
        ):
            break
        seeds = {
            index
            for locator in tentative_locators["locators"]
            for index in locator["triangle_vertices"]
        }
        neighborhood = expanded_vertex_mask(
            len(raw_required),
            seeds,
            neighbors,
            args.orientation_deferral_rings,
        )
        newly_deferred = [
            index
            for index, selected in enumerate(neighborhood)
            if selected and not quality_deferred[index]
        ]
        if not newly_deferred:
            break
        for index in newly_deferred:
            quality_deferred[index] = True
        orientation_deferral_rounds.append(
            {
                "input_negative_triangles": tentative_locators["count"],
                "newly_deferred_vertices": len(newly_deferred),
                "newly_deferred_vertex_index_ranges": index_ranges(
                    newly_deferred
                ),
            }
        )

    changed_mask = [
        value >= args.mask_threshold_mm for value in displacement
    ]

    rescue = candidate.shape_key_add(
        name=RESCUE_KEY_NAME,
        from_mix=True,
    )
    rescue.relative_key = fitted
    inverse = candidate.matrix_world.inverted()
    for shape_vertex, world in zip(rescue.data, rescued_points):
        shape_vertex.co = inverse @ world
    rescue.value = 1.0
    bpy.context.view_layer.update()
    rescued_points = evaluated_world_points(candidate)

    mask_group = candidate.vertex_groups.new(name=MASK_GROUP_NAME)
    maximum_displacement = max(displacement)
    if maximum_displacement <= 0.0:
        raise RuntimeError(
            "Cannot rescue clearance fragments: no candidate vertex violates "
            "the requested cutter margin"
        )
    for index, value in enumerate(displacement):
        if value >= args.mask_threshold_mm:
            mask_group.add(
                [index],
                min(1.0, value / maximum_displacement),
                "REPLACE",
            )

    after_cutter_margins = []
    for point in rescued_points:
        normalized, angle, radius, _ = radial_coordinates(
            point,
            target_length,
        )
        after_cutter_margins.append(
            radius - sample_grid(grid, normalized, angle)
        )

    cutter_faces = polygon_indices(cutter)
    candidate_tree = BVHTree.FromPolygons(
        rescued_points,
        faces,
        all_triangles=False,
    )
    cutter_tree = BVHTree.FromPolygons(
        cutter_vertices,
        cutter_faces,
        all_triangles=False,
    )
    overlaps = candidate_tree.overlap(cutter_tree)

    source_points = [
        source.matrix_world @ vertex.co for vertex in source.data.vertices
    ]
    material_indices = [
        polygon.material_index for polygon in candidate.data.polygons
    ]
    topology_equal = (
        len(source.data.vertices) == len(candidate.data.vertices)
        and len(source.data.edges) == len(candidate.data.edges)
        and len(source.data.loops) == len(candidate.data.loops)
        and len(source.data.polygons) == len(candidate.data.polygons)
        and polygon_indices(source) == polygon_indices(candidate)
        and [
            polygon.material_index for polygon in source.data.polygons
        ]
        == material_indices
    )

    hard_indices = [
        index for index, active in enumerate(hard_mask) if active
    ]
    changed_indices = [
        index for index, active in enumerate(changed_mask) if active
    ]
    displacements = [
        (after - original).length
        for original, after in zip(before, rescued_points)
    ]
    report = {
        "tool": "rescue_clearance_fragments.py",
        "status": "bounded_rescue_candidate_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "geometric_tolerance_mm": GEOMETRIC_TOLERANCE_MM,
        "source": {
            "object": source.name,
            "geometry_fingerprint": geometry_fingerprint(
                source_points,
                polygon_indices(source),
                [
                    polygon.material_index
                    for polygon in source.data.polygons
                ],
            ),
        },
        "pre_rescue": {
            "object": pre_rescue.name,
            "geometry_fingerprint": geometry_fingerprint(
                before,
                faces,
                material_indices,
            ),
            "vertices_below_cutter": sum(
                value < -GEOMETRIC_TOLERANCE_MM
                for value in before_cutter_margins
            ),
            "vertices_below_reserved_margin": sum(
                value
                < args.reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
                for value in before_cutter_margins
            ),
            "minimum_cutter_margin_mm": round(
                min(before_cutter_margins),
                6,
            ),
        },
        "rescue": {
            "object": candidate.name,
            "shape_key": rescue.name,
            "relative_to": fitted.name,
            "mask_vertex_group": mask_group.name,
            "topology_equal_to_source": topology_equal,
            "geometry_fingerprint": geometry_fingerprint(
                rescued_points,
                faces,
                material_indices,
            ),
            "reserved_margin_mm": args.reserved_margin_mm,
            "diffusion_iterations": args.diffusion_iterations,
            "diffusion_factor": args.diffusion_factor,
            "depth_preservation": args.depth_preservation,
            "protect_visible": args.protect_visible,
            "visible_faces": sum(visible_faces),
            "visibility_locked_vertices": sum(visibility_locked),
            "maximum_hard_lift_mm": args.maximum_hard_lift_mm,
            "depth_deferred_vertices": sum(depth_deferred),
            "defer_negative_orientation": (
                args.defer_negative_orientation
            ),
            "orientation_deferral_rings": (
                args.orientation_deferral_rings
            ),
            "orientation_deferral_rounds": (
                orientation_deferral_rounds
            ),
            "orientation_deferred_vertices": sum(quality_deferred),
            "orientation_deferred_vertex_index_ranges": index_ranges(
                [
                    index
                    for index, deferred in enumerate(quality_deferred)
                    if deferred
                ]
            ),
            "locked_vertices": sum(locked),
            "protected_vertices_below_reserved_margin": sum(
                visibility_locked[index]
                and raw_required[index] > 1.0e-8
                for index in range(len(visibility_locked))
            ),
            "mask_threshold_mm": args.mask_threshold_mm,
            "hard_mask_clusters": len(clusters),
            "hard_mask_cluster_vertices": sorted(
                [len(cluster) for cluster in clusters],
                reverse=True,
            ),
            "hard_mask_vertices": len(hard_indices),
            "changed_vertices": len(changed_indices),
            "hard_mask_vertex_index_ranges": index_ranges(hard_indices),
            "changed_vertex_index_ranges": index_ranges(changed_indices),
            "affected_components": component_report(
                source,
                hard_mask,
                changed_mask,
                displacement,
            ),
        },
        "clearance": {
            "candidate_cutter_triangle_overlaps": len(overlaps),
            "vertices_below_cutter": sum(
                value < -GEOMETRIC_TOLERANCE_MM
                for value in after_cutter_margins
            ),
            "vertices_below_reserved_margin": sum(
                value
                < args.reserved_margin_mm - GEOMETRIC_TOLERANCE_MM
                for value in after_cutter_margins
            ),
            "minimum_cutter_margin_mm": round(
                min(after_cutter_margins),
                6,
            ),
            "median_cutter_margin_mm": round(
                percentile(after_cutter_margins, 0.5),
                6,
            ),
            "affected_components": clearance_component_report(
                source,
                before_cutter_margins,
                after_cutter_margins,
                args.reserved_margin_mm,
                depth_deferred,
            ),
        },
        "distortion": {
            "rescue_displacement_mm": {
                "minimum": round(min(displacements), 6),
                "median": round(percentile(displacements, 0.5), 6),
                "p95": round(percentile(displacements, 0.95), 6),
                "maximum": round(max(displacements), 6),
            },
            "pre_rescue_to_rescue_edge_ratio": edge_ratio_report(
                candidate.data,
                before,
                rescued_points,
            ),
            "pre_rescue_to_rescue_triangles": (
                triangle_deformation_report(
                    before,
                    rescued_points,
                    faces,
                )
            ),
            "negative_orientation_locators": (
                negative_orientation_locators(
                    source,
                    before,
                    rescued_points,
                    faces,
                )
            ),
            "source_to_rescue_triangles": triangle_deformation_report(
                source_points,
                rescued_points,
                faces,
            ),
        },
        "promotion": {
            "gate_b_topology_invariants": (
                "PASS" if topology_equal else "FAIL"
            ),
            "gate_b_bounded_reconstruction_review": "PENDING",
            "gate_c_visual_review": "PENDING",
            "gate_d_anatomical_clearance": (
                "PASS"
                if not overlaps
                and min(after_cutter_margins)
                >= -GEOMETRIC_TOLERANCE_MM
                else "FAIL"
            ),
            "does_this_look_ass": None,
        },
        "motion_claim": "none",
    }

    candidate["role"] = "bounded clearance-rescue fitted surface candidate"
    candidate["status"] = "bounded_rescue_candidate_not_approved"
    candidate["rescue_shape_key"] = rescue.name
    candidate["rescue_mask_vertex_group"] = mask_group.name
    candidate["rescue_reserved_margin_mm"] = args.reserved_margin_mm
    candidate["rescue_changed_vertices"] = len(changed_indices)
    candidate["printable"] = False

    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.hide_set(obj != candidate)
            obj.hide_render = obj != candidate
    candidate.hide_set(False)
    candidate.hide_render = False
    bpy.context.view_layer.objects.active = candidate
    candidate.select_set(True)

    if args.save:
        if not bpy.data.filepath:
            raise RuntimeError(
                "Cannot save fragment rescue: current scene has no file path"
            )
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
