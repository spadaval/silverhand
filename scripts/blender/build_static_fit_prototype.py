"""Build the first reversible, anatomy-led fitted-surface prototype.

The prototype deliberately stops before solidification or connectivity:

* recover a compact immutable right-arm reference from the verified pre-cleanup
  scene when it is not already present;
* derive straight cross-sections from that anatomical mesh;
* preserve the clean game surface as a Basis shape key;
* place one mapped candidate in a second shape key;
* record topology, distortion, and vertex/cutter-clearance evidence.

The source mesh is never edited. Run this on an ignored working copy until the
candidate has passed qualitative review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import atan2, cos, pi, sin
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SOURCE_NAME = "SRC_GAME_TPU_ONLY_BASELINE"
ANATOMY_NAME = "SRC_ANATOMY_ARM"
ANATOMY_CENTERLINE_NAME = "SRC_ANATOMY_ARM_CENTERLINE"
FIT_NAME = "REF_FIT_ANATOMY_STRAIGHT"
CUTTER_NAME = "CUT_CLEARANCE_ANATOMY_STRAIGHT"
CANDIDATE_NAME = "WORK_FITTED_SURFACE_CANDIDATE"

SOURCE_COLLECTION = "00_SOURCE_LOCKED"
ANATOMY_COLLECTION = "SRC_ANATOMY"
FIT_COLLECTION = "10_FIT_TOOLS"
CANDIDATE_COLLECTION = "20_FITTED_SURFACE"

CHECKPOINT_BODY = "VALIDATION_generic_male"
CHECKPOINT_RIG = "VALIDATION_generic_male_rig"
ARM_GROUP_NAMES = (
    "wrist.R",
    "lowerarm02.R",
    "lowerarm01.R",
    "upperarm02.R",
    "upperarm01.R",
)

# Reviewed source cut-marker coordinates after the millimeter migration.
SOURCE_WRIST = Vector((269.708900, -181.694220, -225.352800))
SOURCE_AXIS = Vector((-0.435269, 0.622288, 0.650614)).normalized()
SOURCE_LENGTH_MM = 420.0
SOURCE_BICEP_STATION_MM = 370.0

ANATOMY_UPPER_BICEP_FRACTION = 0.45
ANGULAR_SAMPLES = 24
ANATOMY_STATIONS = 17
COMFORT_CLEARANCE_MM = 2.0
RESERVED_WALL_MM = 1.6
OUTER_RADIAL_DEPTH_SCALE = 1.0
INNER_RADIAL_DEPTH_SCALE = 1.0
SOURCE_BASELINE_PERCENTILE = 0.10
SOURCE_BASELINE_HARMONICS = 2


def parse_args() -> argparse.Namespace:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        arguments: list[str] = []
    else:
        arguments = sys.argv[separator + 1 :]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anatomy-checkpoint",
        type=Path,
        required=True,
        help="Verified .blend containing the provided anatomical body",
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the currently opened blend after generating the prototype",
    )
    return parser.parse_args(arguments)


def require_mesh(name: str, role: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(
            f"Cannot build static fit prototype: {role} mesh '{name}' is missing"
        )
    if obj.type != "MESH":
        raise RuntimeError(
            f"Cannot build static fit prototype: {role} object '{name}' has "
            f"type '{obj.type}', expected 'MESH'"
        )
    return obj


def ensure_root_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def ensure_child_collection(
    parent_name: str,
    child_name: str,
) -> bpy.types.Collection:
    parent = ensure_root_collection(parent_name)
    child = bpy.data.collections.get(child_name)
    if child is None:
        child = bpy.data.collections.new(child_name)
    if parent.children.get(child.name) is None:
        parent.children.link(child)
    return child


def unlink_from_other_collections(
    obj: bpy.types.Object,
    target: bpy.types.Collection,
) -> None:
    if target.objects.get(obj.name) is None:
        target.objects.link(obj)
    for collection in list(obj.users_collection):
        if collection != target:
            collection.objects.unlink(obj)


def remove_generated_object(name: str) -> None:
    obj = bpy.data.objects.get(name)
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)


def weighted_group_centroid(
    body: bpy.types.Object,
    group_name: str,
) -> Vector:
    group = body.vertex_groups.get(group_name)
    if group is None:
        raise RuntimeError(
            "Cannot recover anatomical reference: body "
            f"'{body.name}' has no vertex group '{group_name}'"
        )
    total = 0.0
    center = Vector()
    for vertex in body.data.vertices:
        weight = next(
            (
                assignment.weight
                for assignment in vertex.groups
                if assignment.group == group.index
            ),
            0.0,
        )
        if weight > 0.0:
            center += vertex.co * weight
            total += weight
    if total <= 0.0:
        raise RuntimeError(
            "Cannot recover anatomical reference: vertex group "
            f"'{group_name}' on '{body.name}' has no weighted vertices"
        )
    return center / total * 1000.0


def arm_weight(
    vertex: bpy.types.MeshVertex,
    group_indices: set[int],
) -> float:
    return sum(
        assignment.weight
        for assignment in vertex.groups
        if assignment.group in group_indices
    )


def make_polyline(
    name: str,
    collection: bpy.types.Collection,
    points: list[Vector],
) -> bpy.types.Object:
    remove_generated_object(name)
    curve = bpy.data.curves.new(f"{name}_CURVE", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.display_type = "WIRE"
    obj.show_in_front = True
    obj.hide_render = True
    obj["role"] = "immutable anatomical arm centerline evidence"
    obj["printable"] = False
    return obj


def recover_anatomical_arm(
    checkpoint: Path,
) -> tuple[bpy.types.Object, list[Vector]]:
    existing = bpy.data.objects.get(ANATOMY_NAME)
    if existing is not None:
        if existing.type != "MESH":
            raise RuntimeError(
                f"Cannot use anatomical reference '{ANATOMY_NAME}': object has "
                f"type '{existing.type}', expected 'MESH'"
            )
        controls_json = existing.get("centerline_controls_mm")
        if not controls_json:
            raise RuntimeError(
                f"Cannot use anatomical reference '{ANATOMY_NAME}': custom "
                "property 'centerline_controls_mm' is missing"
            )
        controls = [
            Vector(values) for values in json.loads(controls_json)
        ]
        return existing, controls

    checkpoint = checkpoint.resolve()
    if not checkpoint.is_file():
        raise RuntimeError(
            "Cannot recover anatomical reference: checkpoint "
            f"'{checkpoint}' does not exist"
        )

    with bpy.data.libraries.load(str(checkpoint), link=False) as (
        data_from,
        data_to,
    ):
        missing = [
            name
            for name in (CHECKPOINT_BODY, CHECKPOINT_RIG)
            if name not in data_from.objects
        ]
        if missing:
            raise RuntimeError(
                "Cannot recover anatomical reference from "
                f"'{checkpoint}': missing objects {', '.join(missing)}"
            )
        data_to.objects = [CHECKPOINT_BODY, CHECKPOINT_RIG]

    loaded = {obj.name: obj for obj in data_to.objects if obj is not None}
    body = loaded.get(CHECKPOINT_BODY)
    rig = loaded.get(CHECKPOINT_RIG)
    if body is None or rig is None or body.type != "MESH":
        raise RuntimeError(
            "Cannot recover anatomical reference: Blender did not append the "
            f"required body and rig from '{checkpoint}'"
        )

    controls = [
        weighted_group_centroid(body, name) for name in ARM_GROUP_NAMES
    ]
    groups = [body.vertex_groups.get(name) for name in ARM_GROUP_NAMES]
    if any(group is None for group in groups):
        raise RuntimeError(
            f"Cannot recover anatomical reference from '{body.name}': one or "
            "more required right-arm vertex groups are missing"
        )
    group_indices = {group.index for group in groups if group is not None}
    selected = {
        vertex.index
        for vertex in body.data.vertices
        if arm_weight(vertex, group_indices) >= 0.10
    }
    selected_faces = [
        polygon
        for polygon in body.data.polygons
        if all(index in selected for index in polygon.vertices)
    ]
    if not selected_faces:
        raise RuntimeError(
            f"Cannot recover anatomical reference from '{body.name}': arm "
            "vertex groups selected no complete faces"
        )

    used = sorted(
        {
            index
            for polygon in selected_faces
            for index in polygon.vertices
        }
    )
    remap = {source: target for target, source in enumerate(used)}
    vertices = [
        body.data.vertices[index].co * 1000.0 for index in used
    ]
    faces = [
        tuple(remap[index] for index in polygon.vertices)
        for polygon in selected_faces
    ]
    mesh = bpy.data.meshes.new(f"{ANATOMY_NAME}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    arm = bpy.data.objects.new(ANATOMY_NAME, mesh)
    collection = ensure_child_collection(
        SOURCE_COLLECTION,
        ANATOMY_COLLECTION,
    )
    collection.objects.link(arm)
    arm.color = (0.34, 0.12, 0.08, 1.0)
    arm.display_type = "WIRE"
    arm.show_in_front = True
    arm.hide_render = True
    arm["role"] = "immutable provided anatomical right-arm evidence"
    arm["source_checkpoint"] = str(checkpoint)
    arm["source_body"] = CHECKPOINT_BODY
    arm["source_side"] = "right"
    arm["source_vertex_groups"] = ",".join(ARM_GROUP_NAMES)
    arm["centerline_controls_mm"] = json.dumps(
        [[float(value) for value in point] for point in controls]
    )
    arm["printable"] = False

    make_polyline(
        ANATOMY_CENTERLINE_NAME,
        collection,
        controls,
    )

    body_mesh = body.data
    rig_data = rig.data
    bpy.data.objects.remove(body, do_unlink=True)
    bpy.data.objects.remove(rig, do_unlink=True)
    if body_mesh.users == 0:
        bpy.data.meshes.remove(body_mesh)
    if rig_data.users == 0:
        bpy.data.armatures.remove(rig_data)
    return arm, controls


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    factor = position - left
    return ordered[left] + (ordered[right] - ordered[left]) * factor


class Centerline:
    def __init__(self, controls: list[Vector]):
        self.controls = controls
        self.arc = [0.0]
        for first, second in zip(controls, controls[1:]):
            self.arc.append(self.arc[-1] + (second - first).length)
        self.tangents = []
        for index in range(len(controls)):
            before = controls[max(0, index - 1)]
            after = controls[min(len(controls) - 1, index + 1)]
            self.tangents.append((after - before).normalized())

        normal = Vector((0.0, 1.0, 0.0))
        normal -= self.tangents[0] * normal.dot(self.tangents[0])
        if normal.length <= 1.0e-8:
            normal = Vector((0.0, 0.0, 1.0))
            normal -= self.tangents[0] * normal.dot(self.tangents[0])
        normal.normalize()
        self.frames = []
        previous = self.tangents[0]
        for tangent in self.tangents:
            normal = previous.rotation_difference(tangent) @ normal
            normal -= tangent * normal.dot(tangent)
            normal.normalize()
            self.frames.append(
                (normal.copy(), tangent.cross(normal).normalized())
            )
            previous = tangent

    @property
    def length(self) -> float:
        return self.arc[-1]

    def sample(self, distance: float) -> tuple[Vector, Vector, Vector, Vector]:
        value = max(0.0, min(self.length, distance))
        left = 0
        while (
            left < len(self.arc) - 2
            and self.arc[left + 1] < value
        ):
            left += 1
        span = self.arc[left + 1] - self.arc[left]
        factor = 0.0 if span <= 1.0e-9 else (
            value - self.arc[left]
        ) / span
        center = self.controls[left].lerp(
            self.controls[left + 1],
            factor,
        )
        tangent = self.tangents[left].lerp(
            self.tangents[left + 1],
            factor,
        ).normalized()
        normal = self.frames[left][0].lerp(
            self.frames[left + 1][0],
            factor,
        )
        normal -= tangent * normal.dot(tangent)
        normal.normalize()
        return center, tangent, normal, tangent.cross(normal).normalized()

    def coordinates(self, point: Vector) -> tuple[float, float, float]:
        best: tuple[float, float] | None = None
        for index, (first, second) in enumerate(
            zip(self.controls, self.controls[1:])
        ):
            edge = second - first
            factor = max(
                0.0,
                min(1.0, (point - first).dot(edge) / edge.length_squared),
            )
            nearest = first + edge * factor
            distance_squared = (point - nearest).length_squared
            arc_distance = self.arc[index] + factor * (
                self.arc[index + 1] - self.arc[index]
            )
            candidate = (distance_squared, arc_distance)
            if best is None or candidate[0] < best[0]:
                best = candidate
        if best is None:
            raise RuntimeError(
                "Cannot derive anatomical profile: centerline has no segments"
            )
        distance = best[1]
        center, _, normal, binormal = self.sample(distance)
        offset = point - center
        return distance, offset.dot(normal), offset.dot(binormal)


def source_frame() -> tuple[Vector, Vector]:
    normal = Vector((0.0, 0.0, 1.0))
    normal -= SOURCE_AXIS * normal.dot(SOURCE_AXIS)
    normal.normalize()
    return normal, SOURCE_AXIS.cross(normal).normalized()


def anatomical_profile(
    anatomy: bpy.types.Object,
    controls: list[Vector],
) -> tuple[list[float], list[list[float]], dict]:
    endpoint = controls[3].lerp(
        controls[4],
        ANATOMY_UPPER_BICEP_FRACTION,
    )
    path = Centerline(controls[:4] + [endpoint])
    samples = []
    for vertex in anatomy.data.vertices:
        point = anatomy.matrix_world @ vertex.co
        distance, first, second = path.coordinates(point)
        if (
            distance >= path.length - 1.0e-6
            and (point - endpoint).dot(path.tangents[-1]) > 12.0
        ):
            continue
        samples.append((distance, first, second))

    station_distances = [
        path.length * index / (ANATOMY_STATIONS - 1)
        for index in range(ANATOMY_STATIONS)
    ]
    radii = []
    station_reports = []
    spacing = path.length / (ANATOMY_STATIONS - 1)
    window = max(16.0, spacing * 0.70)
    for station, distance in enumerate(station_distances):
        section = [
            (first, second)
            for sample_distance, first, second in samples
            if abs(sample_distance - distance) <= window
        ]
        if len(section) < 12:
            nearest = sorted(
                samples,
                key=lambda item: abs(item[0] - distance),
            )[:32]
            section = [(first, second) for _, first, second in nearest]
        first_center = percentile(
            [point[0] for point in section],
            0.5,
        )
        second_center = percentile(
            [point[1] for point in section],
            0.5,
        )
        first_radius = percentile(
            [abs(first - first_center) for first, _ in section],
            0.95,
        )
        second_radius = percentile(
            [abs(second - second_center) for _, second in section],
            0.95,
        )
        if min(first_radius, second_radius) <= 5.0:
            raise RuntimeError(
                "Cannot derive anatomical profile: station "
                f"{station} produced implausible ellipse radii "
                f"{first_radius:.3f} × {second_radius:.3f} mm"
            )
        ring = [
            1.0
            / (
                (
                    cos(2.0 * pi * angular / ANGULAR_SAMPLES)
                    / first_radius
                )
                ** 2
                + (
                    sin(2.0 * pi * angular / ANGULAR_SAMPLES)
                    / second_radius
                )
                ** 2
            )
            ** 0.5
            for angular in range(ANGULAR_SAMPLES)
        ]
        radii.append(ring)
        station_reports.append(
            {
                "station": station,
                "arc_length_mm": round(distance, 3),
                "sample_vertices": len(section),
                "recentering_mm": [
                    round(first_center, 3),
                    round(second_center, 3),
                ],
                "ellipse_radii_mm": [
                    round(first_radius, 3),
                    round(second_radius, 3),
                ],
                "minimum_radius_mm": round(min(ring), 3),
                "maximum_radius_mm": round(max(ring), 3),
            }
        )

    # One mild longitudinal smoothing pass removes vertex-group sampling noise
    # without inventing a separate fit profile.
    smoothed = []
    for station in range(len(radii)):
        previous = radii[max(0, station - 1)]
        current = radii[station]
        following = radii[min(len(radii) - 1, station + 1)]
        smoothed.append(
            [
                (
                    previous[angular]
                    + 2.0 * current[angular]
                    + following[angular]
                )
                / 4.0
                for angular in range(ANGULAR_SAMPLES)
            ]
        )
    return station_distances, smoothed, {
        "centerline_length_mm": round(path.length, 3),
        "upper_bicep_fraction": ANATOMY_UPPER_BICEP_FRACTION,
        "stations": station_reports,
    }


def ring_perimeter(ring: list[Vector]) -> float:
    return sum(
        (following - current).length
        for current, following in zip(ring, ring[1:] + ring[:1])
    )


def make_ring_volume(
    name: str,
    collection: bpy.types.Collection,
    distances: list[float],
    radii: list[list[float]],
    radial_offset: float,
    role: str,
) -> tuple[bpy.types.Object, list[list[Vector]]]:
    remove_generated_object(name)
    normal, binormal = source_frame()
    vertices = []
    rings: list[list[Vector]] = []
    for distance, station_radii in zip(distances, radii):
        center = SOURCE_WRIST + SOURCE_AXIS * distance
        ring = []
        for angular, radius in enumerate(station_radii):
            angle = 2.0 * pi * angular / ANGULAR_SAMPLES
            point = (
                center
                + normal * (cos(angle) * (radius + radial_offset))
                + binormal * (sin(angle) * (radius + radial_offset))
            )
            ring.append(point)
            vertices.append(point)
        rings.append(ring)

    faces = []
    for station in range(len(rings) - 1):
        current = station * ANGULAR_SAMPLES
        following = (station + 1) * ANGULAR_SAMPLES
        for angular in range(ANGULAR_SAMPLES):
            next_angular = (angular + 1) % ANGULAR_SAMPLES
            faces.append(
                (
                    current + angular,
                    current + next_angular,
                    following + next_angular,
                    following + angular,
                )
            )
    faces.append(tuple(reversed(range(ANGULAR_SAMPLES))))
    final = (len(rings) - 1) * ANGULAR_SAMPLES
    faces.append(
        tuple(final + angular for angular in range(ANGULAR_SAMPLES))
    )
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.display_type = "WIRE"
    obj.show_in_front = True
    obj.hide_render = True
    obj["role"] = role
    obj["source_anatomy"] = ANATOMY_NAME
    obj["radial_offset_mm"] = radial_offset
    obj["printable"] = False
    return obj, rings


def source_samples(
    source: bpy.types.Object,
) -> list[tuple[float, float, float]]:
    normal, binormal = source_frame()
    samples = []
    for vertex in source.data.vertices:
        point = source.matrix_world @ vertex.co
        offset = point - SOURCE_WRIST
        distance = offset.dot(SOURCE_AXIS)
        radial = offset - SOURCE_AXIS * distance
        samples.append(
            (
                distance,
                atan2(radial.dot(binormal), radial.dot(normal))
                % (2.0 * pi),
                radial.length,
            )
        )
    return samples


def angular_difference(first: float, second: float) -> float:
    difference = abs(first - second) % (2.0 * pi)
    return min(difference, 2.0 * pi - difference)


def smooth_profile(values: list[float], iterations: int) -> list[float]:
    result = values[:]
    for _ in range(iterations):
        updated = []
        for station, current in enumerate(result):
            previous = result[max(0, station - 1)]
            following = result[min(len(result) - 1, station + 1)]
            updated.append((previous + 2.0 * current + following) / 4.0)
        result = updated
    return result


def low_frequency_ring(values: list[float], harmonics: int) -> list[float]:
    count = len(values)
    mean = sum(values) / count
    coefficients = []
    for harmonic in range(1, harmonics + 1):
        cosine = (
            2.0
            / count
            * sum(
                value * cos(2.0 * pi * harmonic * index / count)
                for index, value in enumerate(values)
            )
        )
        sine = (
            2.0
            / count
            * sum(
                value * sin(2.0 * pi * harmonic * index / count)
                for index, value in enumerate(values)
            )
        )
        coefficients.append((cosine, sine))
    return [
        mean
        + sum(
            cosine * cos(2.0 * pi * harmonic * index / count)
            + sine * sin(2.0 * pi * harmonic * index / count)
            for harmonic, (cosine, sine) in enumerate(
                coefficients,
                start=1,
            )
        )
        for index in range(count)
    ]


def source_baseline_grid(
    samples: list[tuple[float, float, float]],
    station_count: int,
) -> list[list[float]]:
    spacing = SOURCE_LENGTH_MM / (station_count - 1)
    station_window = max(18.0, spacing * 0.75)
    angle_window = 2.0 * pi / ANGULAR_SAMPLES * 0.90
    grid = []
    for station in range(station_count):
        distance = SOURCE_LENGTH_MM * station / (station_count - 1)
        row = []
        for angular in range(ANGULAR_SAMPLES):
            angle = 2.0 * pi * angular / ANGULAR_SAMPLES
            local = [
                radius
                for sample_distance, sample_angle, radius in samples
                if abs(sample_distance - distance) <= station_window
                and angular_difference(sample_angle, angle) <= angle_window
            ]
            if len(local) < 8:
                nearest = sorted(
                    samples,
                    key=lambda item: (
                        (item[0] - distance) / station_window
                    )
                    ** 2
                    + (
                        angular_difference(item[1], angle) / angle_window
                    )
                    ** 2,
                )[:32]
                local = [item[2] for item in nearest]
            row.append(percentile(local, SOURCE_BASELINE_PERCENTILE))
        grid.append(low_frequency_ring(row, SOURCE_BASELINE_HARMONICS))

    # Smooth each angular track longitudinally. The Fourier projection above
    # removes high-frequency angular ripples caused by gaps between disconnected
    # source pieces while retaining broad asymmetry in the original sleeve.
    columns = [
        smooth_profile(
            [grid[station][angular] for station in range(station_count)],
            3,
        )
        for angular in range(ANGULAR_SAMPLES)
    ]
    return [
        [columns[angular][station] for angular in range(ANGULAR_SAMPLES)]
        for station in range(station_count)
    ]


def sample_grid(
    grid: list[list[float]],
    normalized_station: float,
    angle: float,
) -> float:
    station_position = max(0.0, min(1.0, normalized_station)) * (
        len(grid) - 1
    )
    station_left = int(station_position)
    station_right = min(len(grid) - 1, station_left + 1)
    station_factor = station_position - station_left

    angular_position = (
        angle % (2.0 * pi)
    ) / (2.0 * pi) * ANGULAR_SAMPLES
    angular_left = int(angular_position) % ANGULAR_SAMPLES
    angular_right = (angular_left + 1) % ANGULAR_SAMPLES
    angular_factor = angular_position - int(angular_position)

    left = (
        grid[station_left][angular_left] * (1.0 - angular_factor)
        + grid[station_left][angular_right] * angular_factor
    )
    right = (
        grid[station_right][angular_left] * (1.0 - angular_factor)
        + grid[station_right][angular_right] * angular_factor
    )
    return left * (1.0 - station_factor) + right * station_factor


def extend_anatomical_profile(
    anatomy_distances: list[float],
    anatomy_radii: list[list[float]],
) -> tuple[list[float], list[list[float]], float]:
    anatomy_length = anatomy_distances[-1]
    target_length = SOURCE_LENGTH_MM * (
        anatomy_length / SOURCE_BICEP_STATION_MM
    )
    distances = [
        target_length * index / (ANATOMY_STATIONS - 1)
        for index in range(ANATOMY_STATIONS)
    ]
    radii = []
    for distance in distances:
        anatomy_distance = min(anatomy_length, distance)
        normalized = anatomy_distance / anatomy_length
        radii.append(
            [
                sample_grid(anatomy_radii, normalized, 2.0 * pi * angular / ANGULAR_SAMPLES)
                for angular in range(ANGULAR_SAMPLES)
            ]
        )
    return distances, radii, target_length


def candidate_points(
    source: bpy.types.Object,
    source_grid: list[list[float]],
    target_radii: list[list[float]],
    target_length: float,
) -> tuple[list[Vector], list[float], list[float]]:
    normal, binormal = source_frame()
    points = []
    cutter_margins = []
    visible_margins = []
    for vertex in source.data.vertices:
        world = source.matrix_world @ vertex.co
        offset = world - SOURCE_WRIST
        distance = offset.dot(SOURCE_AXIS)
        radial = offset - SOURCE_AXIS * distance
        radius = radial.length
        if radius <= 1.0e-8:
            raise RuntimeError(
                "Cannot map fitted surface: source vertex "
                f"{vertex.index} lies on the source axis"
            )
        angle = (
            atan2(radial.dot(binormal), radial.dot(normal))
            % (2.0 * pi)
        )
        normalized = max(
            0.0,
            min(1.0, distance / SOURCE_LENGTH_MM),
        )
        source_base = sample_grid(source_grid, normalized, angle)
        anatomy_radius = sample_grid(target_radii, normalized, angle)
        source_depth = radius - source_base
        depth_scale = (
            OUTER_RADIAL_DEPTH_SCALE
            if source_depth >= 0.0
            else INNER_RADIAL_DEPTH_SCALE
        )
        target_radius = (
            anatomy_radius
            + COMFORT_CLEARANCE_MM
            + RESERVED_WALL_MM
            + source_depth * depth_scale
        )
        target_distance = normalized * target_length
        direction = (
            normal * cos(angle) + binormal * sin(angle)
        ).normalized()
        points.append(
            SOURCE_WRIST
            + SOURCE_AXIS * target_distance
            + direction * target_radius
        )
        cutter_margins.append(
            target_radius - (anatomy_radius + COMFORT_CLEARANCE_MM)
        )
        visible_margins.append(target_radius - anatomy_radius)
    return points, cutter_margins, visible_margins


def create_candidate(
    source: bpy.types.Object,
    points: list[Vector],
    target_length: float,
) -> bpy.types.Object:
    remove_generated_object(CANDIDATE_NAME)
    mesh = source.data.copy()
    mesh.name = f"{CANDIDATE_NAME}_MESH"
    candidate = bpy.data.objects.new(CANDIDATE_NAME, mesh)
    ensure_root_collection(CANDIDATE_COLLECTION).objects.link(candidate)
    candidate.matrix_world = source.matrix_world.copy()
    basis = candidate.shape_key_add(name="Basis", from_mix=False)
    fitted = candidate.shape_key_add(
        name="STATIC_ANATOMICAL_FIT",
        from_mix=False,
    )
    inverse = candidate.matrix_world.inverted()
    for shape_vertex, world in zip(fitted.data, points):
        shape_vertex.co = inverse @ world
    fitted.value = 1.0
    basis.value = 0.0
    candidate.color = (0.035, 0.43, 0.48, 1.0)
    candidate["role"] = "static anatomical fitted surface candidate"
    candidate["source_object"] = source.name
    candidate["fit_reference"] = FIT_NAME
    candidate["clearance_cutter"] = CUTTER_NAME
    candidate["construction_pose"] = "straight"
    candidate["motion_claim"] = "none"
    candidate["target_length_mm"] = target_length
    candidate["comfort_clearance_mm"] = COMFORT_CLEARANCE_MM
    candidate["reserved_wall_mm"] = RESERVED_WALL_MM
    candidate["outer_radial_depth_scale"] = OUTER_RADIAL_DEPTH_SCALE
    candidate["inner_radial_depth_scale"] = INNER_RADIAL_DEPTH_SCALE
    candidate["mapping"] = (
        "shared low-frequency station-angle source baseline into smooth "
        "anatomical station-angle target; monotonic radial depth; "
        "Basis preserved"
    )
    candidate["status"] = "fitted_surface_candidate_not_approved"
    candidate["printable"] = False
    return candidate


def edge_ratios(
    source: bpy.types.Object,
    target_points: list[Vector],
) -> list[float]:
    source_points = [
        source.matrix_world @ vertex.co for vertex in source.data.vertices
    ]
    ratios = []
    for edge in source.data.edges:
        first, second = edge.vertices
        source_length = (source_points[first] - source_points[second]).length
        if source_length <= 1.0e-9:
            continue
        ratios.append(
            (target_points[first] - target_points[second]).length
            / source_length
        )
    return ratios


def polygon_indices(source: bpy.types.Object) -> list[tuple[int, ...]]:
    return [tuple(polygon.vertices) for polygon in source.data.polygons]


def geometry_fingerprint(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    material_indices: list[int],
) -> str:
    digest = hashlib.sha256()
    for point in points:
        digest.update(struct.pack("<3d", *point))
    for face, material_index in zip(faces, material_indices):
        digest.update(struct.pack("<I", len(face)))
        for index in face:
            digest.update(struct.pack("<I", index))
        digest.update(struct.pack("<I", material_index))
    return digest.hexdigest()


def evaluated_world_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [
            evaluated.matrix_world @ vertex.co for vertex in mesh.vertices
        ]
    finally:
        evaluated.to_mesh_clear()


def connected_components(
    source: bpy.types.Object,
) -> tuple[list[int], list[list[int]]]:
    neighbors = [[] for _ in source.data.vertices]
    for edge in source.data.edges:
        first, second = edge.vertices
        neighbors[first].append(second)
        neighbors[second].append(first)

    vertex_component = [-1] * len(source.data.vertices)
    components = []
    for start in range(len(source.data.vertices)):
        if vertex_component[start] >= 0:
            continue
        component_index = len(components)
        stack = [start]
        vertices = []
        vertex_component[start] = component_index
        while stack:
            current = stack.pop()
            vertices.append(current)
            for neighbor in neighbors[current]:
                if vertex_component[neighbor] < 0:
                    vertex_component[neighbor] = component_index
                    stack.append(neighbor)
        components.append(sorted(vertices))
    return vertex_component, components


def affected_component_report(
    source: bpy.types.Object,
    samples: list[tuple[float, float, float]],
    cutter_margins: list[float],
    overlap_faces: set[int],
) -> list[dict]:
    vertex_component, components = connected_components(source)
    faces_by_component = [set() for _ in components]
    overlap_faces_by_component = [set() for _ in components]
    for polygon in source.data.polygons:
        component = vertex_component[polygon.vertices[0]]
        faces_by_component[component].add(polygon.index)
        if polygon.index in overlap_faces:
            overlap_faces_by_component[component].add(polygon.index)

    affected = []
    for component, vertices in enumerate(components):
        violating = [
            index for index in vertices if cutter_margins[index] < -1.0e-6
        ]
        overlap_count = len(overlap_faces_by_component[component])
        if not violating and overlap_count == 0:
            continue
        distances = [samples[index][0] for index in vertices]
        violating_distances = [samples[index][0] for index in violating]
        affected.append(
            {
                "component": component,
                "vertices": len(vertices),
                "faces": len(faces_by_component[component]),
                "source_station_range_mm": [
                    round(min(distances), 3),
                    round(max(distances), 3),
                ],
                "vertices_inside_cutter": len(violating),
                "inside_station_range_mm": (
                    [
                        round(min(violating_distances), 3),
                        round(max(violating_distances), 3),
                    ]
                    if violating_distances
                    else None
                ),
                "minimum_vertex_margin_mm": round(
                    min(cutter_margins[index] for index in vertices),
                    6,
                ),
                "overlap_faces": overlap_count,
            }
        )
    return sorted(
        affected,
        key=lambda item: (
            -item["vertices_inside_cutter"],
            -item["overlap_faces"],
            item["component"],
        ),
    )


def triangle_deformation_report(
    source_points: list[Vector],
    target_points: list[Vector],
    faces: list[tuple[int, ...]],
) -> dict:
    area_ratios = []
    normal_dots = []
    degenerate_source = 0
    degenerate_target = 0
    for face in faces:
        for offset in range(1, len(face) - 1):
            indices = (face[0], face[offset], face[offset + 1])
            source_cross = (
                source_points[indices[1]] - source_points[indices[0]]
            ).cross(
                source_points[indices[2]] - source_points[indices[0]]
            )
            target_cross = (
                target_points[indices[1]] - target_points[indices[0]]
            ).cross(
                target_points[indices[2]] - target_points[indices[0]]
            )
            source_area = source_cross.length * 0.5
            target_area = target_cross.length * 0.5
            if source_area <= 1.0e-9:
                degenerate_source += 1
                continue
            area_ratios.append(target_area / source_area)
            if target_area <= 1.0e-9:
                degenerate_target += 1
                continue
            normal_dots.append(
                source_cross.normalized().dot(target_cross.normalized())
            )
    return {
        "triangles_measured": len(area_ratios),
        "degenerate_source_triangles": degenerate_source,
        "degenerate_target_triangles": degenerate_target,
        "area_ratio": {
            "minimum": round(min(area_ratios), 6),
            "p05": round(percentile(area_ratios, 0.05), 6),
            "median": round(percentile(area_ratios, 0.5), 6),
            "p95": round(percentile(area_ratios, 0.95), 6),
            "maximum": round(max(area_ratios), 6),
        },
        "source_target_normal_dot": {
            "minimum": round(min(normal_dots), 6),
            "p05": round(percentile(normal_dots, 0.05), 6),
            "median": round(percentile(normal_dots, 0.5), 6),
            "triangles_below_zero": sum(value < 0.0 for value in normal_dots),
        },
        "note": (
            "A negative source/target normal dot is a review locator, not by "
            "itself proof of a fold: valid deformation can rotate a triangle."
        ),
    }


def main() -> int:
    args = parse_args()
    source = require_mesh(SOURCE_NAME, "immutable source")
    anatomy, controls = recover_anatomical_arm(args.anatomy_checkpoint)
    anatomy_distances, anatomy_radii, anatomy_report = anatomical_profile(
        anatomy,
        controls,
    )
    target_distances, target_radii, target_length = (
        extend_anatomical_profile(anatomy_distances, anatomy_radii)
    )

    fit_collection = ensure_root_collection(FIT_COLLECTION)
    fit, fit_rings = make_ring_volume(
        FIT_NAME,
        fit_collection,
        target_distances,
        target_radii,
        0.0,
        "provided-anatomy straight fit reference",
    )
    cutter, cutter_rings = make_ring_volume(
        CUTTER_NAME,
        fit_collection,
        target_distances,
        target_radii,
        COMFORT_CLEARANCE_MM,
        "anatomical clearance cutter; subtraction and collision only",
    )
    fit["fit_claim"] = "anatomical digital fit only"
    cutter["fit_claim"] = "anatomical digital clearance only"

    samples = source_samples(source)
    source_grid = source_baseline_grid(samples, len(target_distances))
    points, cutter_margins, visible_margins = candidate_points(
        source,
        source_grid,
        target_radii,
        target_length,
    )
    candidate = create_candidate(source, points, target_length)
    bpy.context.view_layer.update()
    points = evaluated_world_points(candidate)

    faces = polygon_indices(source)
    candidate_tree = BVHTree.FromPolygons(
        points,
        faces,
        all_triangles=False,
    )
    cutter_vertices = [
        point for ring in cutter_rings for point in ring
    ]
    cutter_faces = polygon_indices(cutter)
    cutter_tree = BVHTree.FromPolygons(
        cutter_vertices,
        cutter_faces,
        all_triangles=False,
    )
    surface_overlaps = candidate_tree.overlap(cutter_tree)
    overlap_source_faces = {pair[0] for pair in surface_overlaps}

    source_points = [
        source.matrix_world @ vertex.co for vertex in source.data.vertices
    ]
    displacements = [
        (target - original).length
        for original, target in zip(source_points, points)
    ]
    ratios = edge_ratios(source, points)
    triangle_report = triangle_deformation_report(
        source_points,
        points,
        faces,
    )
    affected_components = affected_component_report(
        source,
        samples,
        cutter_margins,
        overlap_source_faces,
    )
    topology_equal = (
        len(source.data.vertices) == len(candidate.data.vertices)
        and len(source.data.edges) == len(candidate.data.edges)
        and len(source.data.polygons) == len(candidate.data.polygons)
        and len(source.data.loops) == len(candidate.data.loops)
        and polygon_indices(source) == polygon_indices(candidate)
        and [
            polygon.material_index for polygon in source.data.polygons
        ]
        == [
            polygon.material_index for polygon in candidate.data.polygons
        ]
    )

    circumference_reports = []
    for station, (distance, ring) in enumerate(
        zip(target_distances, fit_rings)
    ):
        circumference_reports.append(
            {
                "station": station,
                "arc_length_mm": round(distance, 3),
                "circumference_mm": round(ring_perimeter(ring), 3),
                "minimum_radius_mm": round(
                    min(target_radii[station]),
                    3,
                ),
                "maximum_radius_mm": round(
                    max(target_radii[station]),
                    3,
                ),
            }
        )

    report = {
        "tool": "build_static_fit_prototype.py",
        "status": "candidate_generated_not_approved",
        "blend_file": str(Path(bpy.data.filepath).resolve()),
        "units": "millimeters",
        "source": {
            "object": source.name,
            "vertices": len(source.data.vertices),
            "edges": len(source.data.edges),
            "faces": len(source.data.polygons),
            "loops": len(source.data.loops),
            "geometry_fingerprint": geometry_fingerprint(
                source_points,
                faces,
                [
                    polygon.material_index
                    for polygon in source.data.polygons
                ],
            ),
            "materials": [
                material.name if material is not None else None
                for material in source.data.materials
            ],
            "source_axis": [float(value) for value in SOURCE_AXIS],
            "source_length_mm": SOURCE_LENGTH_MM,
            "source_bicep_station_mm": SOURCE_BICEP_STATION_MM,
        },
        "anatomy": {
            "object": anatomy.name,
            "checkpoint": str(args.anatomy_checkpoint.resolve()),
            **anatomy_report,
        },
        "fit_reference": {
            "object": fit.name,
            "cutter": cutter.name,
            "target_length_mm": round(target_length, 3),
            "comfort_clearance_mm": COMFORT_CLEARANCE_MM,
            "reserved_wall_mm": RESERVED_WALL_MM,
            "circumferences": circumference_reports,
            "claim": "anatomical digital fit only",
        },
        "candidate": {
            "object": candidate.name,
            "shape_key": "STATIC_ANATOMICAL_FIT",
            "topology_equal_to_source": topology_equal,
            "vertices": len(candidate.data.vertices),
            "edges": len(candidate.data.edges),
            "faces": len(candidate.data.polygons),
            "loops": len(candidate.data.loops),
            "geometry_fingerprint": geometry_fingerprint(
                points,
                faces,
                [
                    polygon.material_index
                    for polygon in candidate.data.polygons
                ],
            ),
            "outer_radial_depth_scale": OUTER_RADIAL_DEPTH_SCALE,
            "inner_radial_depth_scale": INNER_RADIAL_DEPTH_SCALE,
            "source_baseline_percentile": SOURCE_BASELINE_PERCENTILE,
            "source_baseline_harmonics": SOURCE_BASELINE_HARMONICS,
            "source_baseline_stations": [
                {
                    "station": station,
                    "minimum_radius_mm": round(min(ring), 3),
                    "median_radius_mm": round(percentile(ring, 0.5), 3),
                    "maximum_radius_mm": round(max(ring), 3),
                }
                for station, ring in enumerate(source_grid)
            ],
            "mapping": candidate["mapping"],
            "motion_claim": "none",
        },
        "distortion": {
            "displacement_mm": {
                "minimum": round(min(displacements), 6),
                "median": round(percentile(displacements, 0.5), 6),
                "p95": round(percentile(displacements, 0.95), 6),
                "maximum": round(max(displacements), 6),
            },
            "edge_length_ratio": {
                "minimum": round(min(ratios), 6),
                "p05": round(percentile(ratios, 0.05), 6),
                "median": round(percentile(ratios, 0.5), 6),
                "p95": round(percentile(ratios, 0.95), 6),
                "maximum": round(max(ratios), 6),
            },
            "triangles": triangle_report,
        },
        "clearance": {
            "candidate_cutter_triangle_overlaps": len(surface_overlaps),
            "vertices_inside_cutter": sum(
                margin < -1.0e-6 for margin in cutter_margins
            ),
            "minimum_vertex_margin_mm": round(min(cutter_margins), 6),
            "median_vertex_margin_mm": round(
                percentile(cutter_margins, 0.5),
                6,
            ),
            "minimum_visible_surface_margin_mm": round(
                min(visible_margins),
                6,
            ),
            "affected_connected_components": len(affected_components),
            "affected_components": affected_components,
        },
        "promotion": {
            "gate_b_topology_invariants": (
                "PASS" if topology_equal else "FAIL"
            ),
            "gate_b_transformation_integrity": "PENDING",
            "gate_c_visual_review": "PENDING",
            "gate_d_anatomical_clearance": (
                "PASS"
                if not surface_overlaps
                and min(cutter_margins) >= -1.0e-6
                else "FAIL"
            ),
            "does_this_look_ass": None,
        },
    }

    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.hide_set(obj != candidate)
            obj.hide_render = True
    candidate.hide_set(False)
    candidate.hide_render = False
    bpy.context.view_layer.objects.active = candidate
    candidate.select_set(True)

    if args.save:
        if not bpy.data.filepath:
            raise RuntimeError(
                "Cannot save static fit prototype: the current Blender scene "
                "has no file path"
            )
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
