"""Run the bounded numerical cleanup of structural-width Repair 014 v2."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_local_elbow_interface_band_v2 as v2  # noqa: E402
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
from rescue_clearance_fragments import cutter_grid, radial_coordinates  # noqa: E402
from try_cutter_patch_reconstruction import overlap_pairs  # noqa: E402


OPERATION = "LOCAL_ELBOW_INTERFACE_BAND_V3"
CAP_CENTER_OUTWARD_MM = 0.18
ROBUST_NEW_VERTEX_FLOOR_MM = 1.61
EXACT_COORDINATE_TOLERANCE_MM = 1.0e-5


def report_argument() -> Path:
    try:
        index = sys.argv.index("--report")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: command line lacks --report PATH"
        ) from error


def cleaned_contract() -> dict:
    contract = deepcopy(ORIGINAL_LOAD_CONTRACT())
    contract["recommended_routes_and_tabs"] = [
        route
        for route in contract["recommended_routes_and_tabs"]
        if route["required"]
    ]
    return contract


def cap_safe_ribbon_geometry(
    samples,
    half_widths,
    target_length,
    grid,
    exact_rings,
):
    points, faces = ORIGINAL_RIBBON_GEOMETRY(
        samples,
        half_widths,
        target_length,
        grid,
        exact_rings,
    )
    for ring in (0, len(samples) - 1):
        if ring in exact_rings:
            continue
        point_index = ring * 5
        _, _, _, radial = radial_coordinates(
            points[point_index],
            target_length,
        )
        points[point_index] += radial * CAP_CENTER_OUTWARD_MM
    return points, v2.base.positive_faces(points, faces)


def component9_geometry(staged_points, staged_faces):
    source = bpy.data.objects[SOURCE_NAME]
    _, components = connected_components(source)
    component9 = set(components[9])
    face_ids = {
        index
        for index, face in enumerate(staged_faces)
        if face[0] in component9
    }
    return v2.base.component_local(
        staged_points,
        staged_faces,
        face_ids,
    )


def localize_c9_overlaps(report: dict) -> dict:
    network = bpy.data.objects[report["objects"]["network"]]
    staged = bpy.data.objects[v2.base.STAGED_NAME]
    network_points, network_faces, _ = evaluated_geometry(network)
    staged_points, staged_faces, _ = evaluated_geometry(staged)
    c9_points, c9_faces = component9_geometry(staged_points, staged_faces)
    pairs = overlap_pairs(
        network_points,
        network_faces,
        c9_points,
        c9_faces,
    )
    band_face_end = report["attachments"]["records"][0]["offsets"][
        "network_face_start"
    ]
    ranges = [("band", 0, band_face_end)]
    records = report["attachments"]["records"]
    for index, record in enumerate(records):
        start = record["offsets"]["network_face_start"]
        end = (
            records[index + 1]["offsets"]["network_face_start"]
            if index + 1 < len(records)
            else len(network_faces)
        )
        ranges.append((record["role"], start, end))
    by_constituent = {name: 0 for name, _, _ in ranges}
    band_by_segment = {
        f"{first}->{second}": 0
        for first, second in zip(
            v2.load_contract()["ordered_centerline_source_vertex_ids"],
            v2.load_contract()["ordered_centerline_source_vertex_ids"][1:],
        )
    }
    centerline_ids = v2.load_contract()[
        "ordered_centerline_source_vertex_ids"
    ]
    for network_face_id, _ in pairs:
        role = next(
            name
            for name, start, end in ranges
            if start <= network_face_id < end
        )
        by_constituent[role] += 1
        if role != "band":
            continue
        centroid = sum(
            (network_points[index] for index in network_faces[network_face_id]),
            network_points[network_faces[network_face_id][0]] * 0.0,
        ) / len(network_faces[network_face_id])
        nearest_segment = min(
            range(len(centerline_ids) - 1),
            key=lambda index: min(
                (centroid - staged_points[centerline_ids[index]]).length,
                (centroid - staged_points[centerline_ids[index + 1]]).length,
            ),
        )
        key = (
            f"{centerline_ids[nearest_segment]}->"
            f"{centerline_ids[nearest_segment + 1]}"
        )
        band_by_segment[key] += 1
    return {
        "total_overlap_count": len(pairs),
        "by_constituent": by_constituent,
        "band_by_nearest_route_segment": band_by_segment,
        "interpretation": (
            "collision evidence only; component 9 is unchanged and no "
            "non-tip historical pair is treated as a welded contact"
        ),
    }


def robust_new_vertex_margin(report: dict) -> dict:
    network = bpy.data.objects[report["objects"]["network"]]
    staged = bpy.data.objects[v2.base.STAGED_NAME]
    candidate = bpy.data.objects[CANDIDATE_NAME]
    cutter = bpy.data.objects[CUTTER_NAME]
    network_points, _, _ = evaluated_geometry(network)
    staged_points, _, _ = evaluated_geometry(staged)
    contract = v2.load_contract()
    exact_source_ids = set(contract["ordered_centerline_source_vertex_ids"])
    for route in contract["recommended_routes_and_tabs"]:
        exact_source_ids.update(route["vertex_ids"])
    exact_points = [staged_points[index] for index in sorted(exact_source_ids)]
    exact_network_indices = {
        index
        for index, point in enumerate(network_points)
        if any(
            (point - exact).length <= EXACT_COORDINATE_TOLERANCE_MM
            for exact in exact_points
        )
    }
    grid, _ = cutter_grid(cutter)
    margins = point_margins(
        network_points,
        float(candidate["target_length_mm"]),
        grid,
    )
    new_margins = [
        margin
        for index, margin in enumerate(margins)
        if index not in exact_network_indices
    ]
    exact_margins = [
        margin
        for index, margin in enumerate(margins)
        if index in exact_network_indices
    ]
    return {
        "robust_floor_mm": ROBUST_NEW_VERTEX_FLOOR_MM,
        "new_vertex_count": len(new_margins),
        "minimum_new_vertex_margin_mm": round(min(new_margins), 6),
        "exact_source_node_count": len(exact_margins),
        "minimum_exact_source_node_margin_mm": round(
            min(exact_margins),
            6,
        ),
        "pass": min(new_margins) >= ROBUST_NEW_VERTEX_FLOOR_MM - 1.0e-4,
    }


ORIGINAL_LOAD_CONTRACT = v2.load_contract
ORIGINAL_RIBBON_GEOMETRY = v2.ribbon_geometry


def main() -> int:
    v2.OPERATION = OPERATION
    v2.__file__ = __file__
    v2.load_contract = cleaned_contract
    v2.ribbon_geometry = cap_safe_ribbon_geometry
    result = v2.main()
    report_path = report_argument()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["status"] = "evaluation_only_not_promoted"
    report["v3_cleanup"] = {
        "omitted_optional_micro_tab": True,
        "cap_center_outward_mm": CAP_CENTER_OUTWARD_MM,
        "scope": "machine cleanup only; no route or retained geometry change",
    }
    report["new_vertex_margin"] = robust_new_vertex_margin(report)
    report["network_vs_component_9_localization"] = localize_c9_overlaps(report)
    report["gates"]["new_vertex_margin"] = report["new_vertex_margin"]["pass"]
    report["gate_pass"] = all(report["gates"].values())
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "tool": Path(__file__).name,
                "gate_pass": report["gate_pass"],
                "new_vertex_margin": report["new_vertex_margin"],
                "network_vs_component_9_localization": report[
                    "network_vs_component_9_localization"
                ],
            },
            indent=2,
        )
    )
    print(
        f"DONE: v3 numerical cleanup gate_pass={report['gate_pass']}; "
        "promotion remains NOT_PROMOTED"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
