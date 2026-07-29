"""Build or reject one component-20 liner in native cylindrical UV space."""

from __future__ import annotations

import argparse
import json
from math import pi
from pathlib import Path
import statistics
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from apply_bounded_clearance_patch import evaluated_geometry  # noqa: E402
from build_combined_authored_inner_bowl_liner import (  # noqa: E402
    EXPECTED_BLEND_SHA256,
    MAPPING_PATH,
    boundary_cycles,
    sha256_file,
)
from build_static_fit_prototype import (  # noqa: E402
    CANDIDATE_NAME,
    CUTTER_NAME,
    SOURCE_NAME,
    connected_components,
)
from rescue_clearance_fragments import radial_coordinates  # noqa: E402


OPERATION = "CYLINDRICAL_UV_INNER_BOWL_LINER"
STAGED_NAME = "EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER"
EXPECTED_CYCLE_COUNTS = [4, 8, 8, 123]


def parse_args() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--required-blend-sha256",
        default=EXPECTED_BLEND_SHA256,
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


def cycle_edges(cycle: list[int]) -> set[tuple[int, int]]:
    return {
        tuple(sorted((first, second)))
        for first, second in zip(cycle, cycle[1:] + cycle[:1])
    }


def unwrap_cycle(
    cycle: list[int],
    points,
    target_length: float,
) -> dict:
    samples = [
        radial_coordinates(points[vertex], target_length)
        for vertex in cycle
    ]
    angles = [samples[0][1]]
    for _, angle, _, _ in samples[1:]:
        previous = angles[-1]
        while angle - previous > pi:
            angle -= 2.0 * pi
        while angle - previous < -pi:
            angle += 2.0 * pi
        angles.append(angle)
    closing_angle = samples[0][1]
    while closing_angle - angles[-1] > pi:
        closing_angle -= 2.0 * pi
    while closing_angle - angles[-1] < -pi:
        closing_angle += 2.0 * pi
    winding_number = round(
        (closing_angle - angles[0]) / (2.0 * pi)
    )
    representative_radius = statistics.median(
        sample[2] for sample in samples
    )
    coordinates = [
        [
            sample[0] * target_length,
            angle * representative_radius,
        ]
        for sample, angle in zip(samples, angles)
    ]
    return {
        "vertex_ids": cycle,
        "unwrapped_angles_radians": angles,
        "representative_radius_mm": representative_radius,
        "coordinates_mm": coordinates,
        "winding_number": winding_number,
    }


def orientation(
    first: list[float],
    second: list[float],
    third: list[float],
) -> float:
    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def strict_segment_crossing(
    first: list[float],
    second: list[float],
    third: list[float],
    fourth: list[float],
) -> bool:
    first_side = orientation(first, second, third)
    second_side = orientation(first, second, fourth)
    third_side = orientation(third, fourth, first)
    fourth_side = orientation(third, fourth, second)
    epsilon = 1.0e-9
    return (
        first_side * second_side < -(epsilon * epsilon)
        and third_side * fourth_side < -(epsilon * epsilon)
    )


def strict_self_crossings(
    record: dict,
    source_edge_id: dict[tuple[int, int], int],
) -> list[dict]:
    vertices = record["vertex_ids"]
    coordinates = record["coordinates_mm"]
    edge_count = len(vertices)
    tested_edge_count = (
        edge_count if record["winding_number"] == 0 else edge_count - 1
    )
    crossings = []
    for first_index in range(tested_edge_count):
        first_next = (first_index + 1) % edge_count
        for second_index in range(first_index + 1, tested_edge_count):
            second_next = (second_index + 1) % edge_count
            if (
                first_index == second_index
                or first_next == second_index
                or second_next == first_index
            ):
                continue
            if not strict_segment_crossing(
                coordinates[first_index],
                coordinates[first_next],
                coordinates[second_index],
                coordinates[second_next],
            ):
                continue
            first_edge = tuple(
                sorted((vertices[first_index], vertices[first_next]))
            )
            second_edge = tuple(
                sorted((vertices[second_index], vertices[second_next]))
            )
            crossings.append(
                {
                    "first_edge_id": source_edge_id[first_edge],
                    "first_edge_vertex_ids": list(first_edge),
                    "first_edge_uv_mm": [
                        coordinates[first_index],
                        coordinates[first_next],
                    ],
                    "second_edge_id": source_edge_id[second_edge],
                    "second_edge_vertex_ids": list(second_edge),
                    "second_edge_uv_mm": [
                        coordinates[second_index],
                        coordinates[second_next],
                    ],
                }
            )
    return crossings


def write_report(path: Path, report: dict) -> None:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    blend_path = Path(bpy.data.filepath).resolve()
    actual_sha = sha256_file(blend_path)
    if actual_sha != args.required_blend_sha256:
        raise RuntimeError(
            f"{OPERATION}: staged blend '{blend_path}' has SHA-256 "
            f"{actual_sha}, expected {args.required_blend_sha256}"
        )
    source = require_mesh(SOURCE_NAME, "immutable source")
    candidate = require_mesh(CANDIDATE_NAME, "fitted-surface candidate")
    staged = require_mesh(STAGED_NAME, "coordinated staged geometry")
    require_mesh(CUTTER_NAME, "clearance cutter")
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    staged_points, staged_faces, _ = evaluated_geometry(staged)
    rebuild_faces = set(mapping["reconstruction_scope"]["rebuild_face_ids"])
    retain_c20_faces = set(mapping["reconstruction_scope"]["retain_face_ids"])
    _, components = connected_components(source)
    component20 = set(components[20])
    component20_faces = {
        face_id
        for face_id, face in enumerate(staged_faces)
        if face[0] in component20
    }
    if rebuild_faces | retain_c20_faces != component20_faces:
        raise RuntimeError(
            f"{OPERATION}: mapped component-20 partition is not exact"
        )
    cycles, complete_boundary = boundary_cycles(staged_faces, rebuild_faces)
    if sorted(len(cycle) for cycle in cycles) != EXPECTED_CYCLE_COUNTS:
        raise RuntimeError(
            f"{OPERATION}: complete boundary cycle counts are "
            f"{sorted(len(cycle) for cycle in cycles)}, expected "
            f"{EXPECTED_CYCLE_COUNTS}"
        )
    source_edge_id = {
        tuple(sorted(edge.vertices)): edge.index for edge in source.data.edges
    }
    aperture_edge_sets = [
        {
            tuple(sorted(edge))
            for edge in group["edge_vertex_ids"]
        }
        for group in mapping["exact_full_inner_bowl_seam"]["boundary_groups"]
        if group["status"] == "closed"
    ]
    aperture_cycles = []
    outer_cycles = []
    unmatched_apertures = list(aperture_edge_sets)
    for cycle in cycles:
        edges = cycle_edges(cycle)
        matching = next(
            (
                aperture
                for aperture in unmatched_apertures
                if edges == aperture
            ),
            None,
        )
        if matching is None:
            outer_cycles.append(cycle)
        else:
            aperture_cycles.append(cycle)
            unmatched_apertures.remove(matching)
    if (
        sorted(len(cycle) for cycle in outer_cycles) != [8, 123]
        or sorted(len(cycle) for cycle in aperture_cycles) != [4, 8]
        or unmatched_apertures
    ):
        raise RuntimeError(
            f"{OPERATION}: classified outer cycles "
            f"{[len(cycle) for cycle in outer_cycles]} and apertures "
            f"{[len(cycle) for cycle in aperture_cycles]}; expected "
            "outer 123/8 and apertures 8/4"
        )
    target_length = float(candidate["target_length_mm"])
    loop_records = []
    for kind, loops in (
        ("outer", outer_cycles),
        ("aperture", aperture_cycles),
    ):
        for index, cycle in enumerate(loops):
            record = unwrap_cycle(cycle, staged_points, target_length)
            record["kind"] = kind
            record["index"] = index
            record["edge_ids"] = sorted(
                source_edge_id[edge] for edge in cycle_edges(cycle)
            )
            if record["winding_number"]:
                seam_edge = tuple(sorted((cycle[-1], cycle[0])))
                record["axial_angle_seam"] = {
                    "edge_id": source_edge_id[seam_edge],
                    "edge_vertex_ids": list(seam_edge),
                    "winding_number": record["winding_number"],
                    "reason": (
                        "excluded from strict-crossing tests because this "
                        "closing edge is the deterministic cut in the "
                        "cylindrical universal cover"
                    ),
                }
            else:
                record["axial_angle_seam"] = None
            record["strict_self_crossings"] = strict_self_crossings(
                record,
                source_edge_id,
            )
            loop_records.append(record)
    crossing_records = [
        {
            "kind": record["kind"],
            "index": record["index"],
            "cycle_vertex_count": len(record["vertex_ids"]),
            "crossings": record["strict_self_crossings"],
        }
        for record in loop_records
        if record["strict_self_crossings"]
    ]
    winding_seam_records = [
        {
            "kind": record["kind"],
            "index": record["index"],
            **record["axial_angle_seam"],
        }
        for record in loop_records
        if record["axial_angle_seam"] is not None
    ]
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": (
            "evaluation_only_uv_boundary_self_crossing"
            if crossing_records
            else "evaluation_only_uv_boundary_simple_pending_construction"
        ),
        "repair_base": {
            "blend_file": str(blend_path),
            "blend_file_sha256": actual_sha,
            "staged_object": STAGED_NAME,
        },
        "mapping": {
            "path": str(MAPPING_PATH),
            "sha256": sha256_file(MAPPING_PATH),
            "removed_face_count": len(rebuild_faces),
            "retained_component_20_face_count": len(retain_c20_faces),
        },
        "uv_parameterization": {
            "axial_mm": "normalized_station * target_length_mm",
            "circumferential_mm": (
                "sequentially_unwrapped_angle_radians * "
                "loop_representative_radius_mm"
            ),
            "target_length_mm": target_length,
            "loops": loop_records,
        },
        "boundary": {
            "complete_edge_count": len(complete_boundary),
            "outer_cycle_vertex_counts": [
                len(cycle) for cycle in outer_cycles
            ],
            "aperture_cycle_vertex_counts": [
                len(cycle) for cycle in aperture_cycles
            ],
            "strict_self_crossing_count": sum(
                len(record["strict_self_crossings"])
                for record in loop_records
            ),
            "crossing_records": crossing_records,
            "winding_seam_records": winding_seam_records,
        },
        "gate_pass": False,
        "blocker": (
            f"{OPERATION}: cylindrical UV boundary has strict "
            "self-intersections; use the reported crossing edge IDs to "
            "author a specific axial-angle seam"
            if crossing_records
            else (
                f"{OPERATION}: all cylindrical UV boundaries are simple; "
                "continue this builder with UV tessellation"
            )
        ),
        "objects": {"created": []},
        "images": {"generated": False, "reviewed": False},
        "promotion": "NOT_PROMOTED",
    }
    write_report(args.report, report)
    if not crossing_records:
        raise RuntimeError(
            f"{OPERATION}: UV boundary crossing gate passed for all loops, "
            "but UV tessellation is not yet implemented"
        )
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps(report, indent=2))
    print(
        f"DONE: cylindrical UV boundary rejected with "
        f"{report['boundary']['strict_self_crossing_count']} strict crossings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
