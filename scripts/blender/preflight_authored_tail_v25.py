"""Persist exact V25 authored-tail authority and bounded search contract.

This stage is deliberately read-only. Candidate generation is added only after
the authority and A0-A3 boundary have been independently checkpointed.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_joint_c9_c20_elbow_v22 as v22  # noqa: E402
import build_parallel_transport_interface_rail_v8 as v8  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import build_upper_lower_terminal_bridge_v14 as v14  # noqa: E402
import preflight_b2b_exit_v24 as v24  # noqa: E402
import preflight_free_space_lower_route_v23 as v23  # noqa: E402


OPERATION = "AUTHORED_TAIL_RECONSTRUCTION_PREFLIGHT_V25"
AUTHORITY_BLEND_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
EXPECTED_V12_SHA256 = (
    "02c02b716c081c3a71826ccac84a154179f5b6a926471aa41d321dc4c6512bbb"
)
WIDTHS_MM = (6.0, 5.25, 4.5)
ADVANCES_MM = (4.0, 8.0, 12.0)
OFFSETS_MM = (-12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0)
ROLLS_DEGREES = (0, -15, 15, -30, 30, -45, 45, -60, 60)


def stable_hash(value):
    return sha256(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def public(record):
    return {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }


def point_list(points):
    return [[float(value) for value in point] for point in points]


def geometry_fingerprint(record):
    return stable_hash(
        {
            "points": point_list(record["_points"]),
            "faces": [list(face) for face in record["_faces"]],
        }
    )


def nearest_distance(points, tree):
    distances = []
    for point in points:
        nearest = tree.find_nearest(point)
        if nearest is not None:
            distances.append(nearest[3])
    return min(distances) if distances else None


def constituent_authority(
    name,
    record,
    corridor,
    c9_tree,
    source_tree,
):
    samples = record["_samples"]
    points = record["_points"]
    faces = record["_faces"]
    tangents = v8.centered_tangents(samples)
    frames = v8.minimum_twist_frames(
        samples,
        tangents,
        corridor["target_length"],
    )
    margins = v24.v4.v2.point_margins(
        points,
        corridor["target_length"],
        corridor["grid"],
    )
    cumulative = [0.0]
    for first, second in zip(samples, samples[1:]):
        cumulative.append(cumulative[-1] + (second - first).length)
    rings = []
    for ring_index, (center, tangent, frame) in enumerate(
        zip(samples, tangents, frames)
    ):
        width_axis, normal = v8.rotated_frame(
            frame[0],
            tangent,
            record["roll_degrees"],
        )
        start = ring_index * 5
        ring_points = points[start : start + 5]
        face_ids = [
            face_id
            for face_id, face in enumerate(faces)
            if any(start <= vertex < start + 5 for vertex in face)
        ]
        rings.append(
            {
                "ring_id": f"R{ring_index}",
                "center_mm": [float(value) for value in center],
                "ordered_ring_vertices_mm": point_list(ring_points),
                "tangent": [float(value) for value in tangent],
                "parallel_transport_normal": [float(value) for value in normal],
                "parallel_transport_binormal": [
                    float(value) for value in width_axis
                ],
                "roll_degrees": record["roll_degrees"],
                "cumulative_arclength_mm": round(
                    cumulative[ring_index],
                    6,
                ),
                "remaining_arclength_mm": round(
                    cumulative[-1] - cumulative[ring_index],
                    6,
                ),
                "section_width_mm": round(
                    (ring_points[4] - ring_points[0]).length,
                    6,
                ),
                "section_thickness_mm": round(
                    (ring_points[1] - ring_points[0]).length,
                    6,
                ),
                "minimum_cutter_margin_mm": round(
                    min(margins[start : start + 5]),
                    6,
                ),
                "minimum_c9_distance_mm": round(
                    nearest_distance(ring_points, c9_tree),
                    6,
                ),
                "minimum_source_distance_mm": round(
                    nearest_distance(ring_points, source_tree),
                    6,
                ),
                "related_face_ids": face_ids,
                "material_indices": [0],
            }
        )
    start_cap = [
        face_id
        for face_id, face in enumerate(faces)
        if all(vertex < 5 for vertex in face)
    ]
    end_start = (len(samples) - 1) * 5
    end_cap = [
        face_id
        for face_id, face in enumerate(faces)
        if all(vertex >= end_start for vertex in face)
    ]
    return {
        "name": name,
        "fingerprint": geometry_fingerprint(record),
        "centerline_samples_mm": point_list(samples),
        "rings": rings,
        "vertex_count": len(points),
        "face_count": len(faces),
        "faces": [
            {
                "local_face_id": face_id,
                "loop": list(face),
                "material_index": 0,
            }
            for face_id, face in enumerate(faces)
        ],
        "start_cap_face_ids": start_cap,
        "end_cap_face_ids": end_cap,
        "minimum_cutter_margin_mm": record["minimum_cutter_margin_mm"],
    }


def related_rings(face, ring_count):
    return sorted(
        {
            min(vertex // 5, ring_count - 1)
            for vertex in face
        }
    )


def prefix_fingerprint(record, anchor_index):
    point_limit = (anchor_index + 1) * 5
    faces = [
        list(face)
        for face in record["_faces"]
        if max(face) < point_limit
    ]
    payload = {
        "anchor_ring_index": anchor_index,
        "points": point_list(record["_points"][:point_limit]),
        "faces": faces,
    }
    return stable_hash(payload)


def resolve_anchors(context, corridor, authority):
    b2a = corridor["core"]["B2a"]
    bridge = corridor["turn"]
    pairs = v14.overlap_pairs(
        b2a["_points"],
        b2a["_faces"],
        bridge["_points"],
        bridge["_faces"],
    )
    ring_count = len(b2a["_samples"])
    face_rings = {
        face_id: related_rings(face, ring_count)
        for face_id, face in enumerate(b2a["_faces"])
    }
    bridge_touch_rings = sorted(
        {
            ring
            for face_id, _ in pairs
            for ring in face_rings[face_id]
        }
    )
    cumulative = [
        ring["cumulative_arclength_mm"]
        for ring in authority["constituents"]["B2a"]["rings"]
    ]
    source_v2111 = context["staged_points"][2111]
    v2111_ring = min(
        range(ring_count),
        key=lambda index: (
            b2a["_samples"][index] - source_v2111
        ).length,
    )
    eligible = []
    for anchor in range(ring_count):
        suffix = cumulative[-1] - cumulative[anchor]
        if suffix > 12.0 + 1.0e-6 or anchor < v2111_ring:
            continue
        scarf_start = anchor
        while (
            scarf_start > 0
            and cumulative[anchor] - cumulative[scarf_start] < 6.0
        ):
            scarf_start -= 1
        if cumulative[anchor] - cumulative[scarf_start] < 6.0 - 1.0e-6:
            continue
        scarf_face_ids = {
            face_id
            for face_id, rings in face_rings.items()
            if max(rings) >= scarf_start and max(rings) <= anchor
        }
        scarf_bridge_pairs = [
            list(pair) for pair in pairs if pair[0] in scarf_face_ids
        ]
        if scarf_bridge_pairs:
            continue
        eligible.append(
            {
                "ring_index": anchor,
                "scarf_start_ring_index": scarf_start,
                "scarf_length_mm": round(
                    cumulative[anchor] - cumulative[scarf_start],
                    6,
                ),
                "replaced_suffix_arclength_mm": round(suffix, 6),
                "prefix_fingerprint": prefix_fingerprint(b2a, anchor),
            }
        )
    if not eligible:
        raise RuntimeError(
            f"{OPERATION}: A0 cannot be resolved without touching the "
            f"bridge, B1, or V2111-side retained interval; "
            f"bridge_touch_rings={bridge_touch_rings}, "
            f"v2111_ring={v2111_ring}"
        )
    a0 = max(eligible, key=lambda record: record["ring_index"])
    by_index = {record["ring_index"]: record for record in eligible}
    anchors = []
    resolution_ledger = []
    for offset in range(4):
        ring_index = a0["ring_index"] - offset
        anchor_id = f"A{offset}"
        ring_id = f"R{ring_index}"
        if ring_index in by_index:
            record = {
                **by_index[ring_index],
                "anchor_id": anchor_id,
                "ring_id": ring_id,
            }
            anchors.append(record)
            resolution_ledger.append(
                {**record, "eligible_for_search": True}
            )
        else:
            suffix = cumulative[-1] - cumulative[ring_index]
            resolution_ledger.append(
                {
                    "anchor_id": anchor_id,
                    "ring_id": ring_id,
                    "ring_index": ring_index,
                    "replaced_suffix_arclength_mm": round(suffix, 6),
                    "eligible_for_search": False,
                    "rejection_reason": (
                        "replaced_B2a_suffix_exceeds_12mm"
                        if suffix > 12.0 + 1.0e-6
                        else "bridge_free_6mm_scarf_not_available"
                    ),
                }
            )
    return {
        "B2A_BRIDGE_OVERLAP_PAIRS": [list(pair) for pair in pairs],
        "BRIDGE_TOUCH_B2A_RINGS": bridge_touch_rings,
        "BRIDGE_TOUCH_B2B_RINGS": [
            int(ring["ring_id"][1:])
            for ring in authority["constituents"]["B2b"]["rings"]
            if ring["turn_bridge_overlap_pairs"]
        ],
        "LAST_BRIDGE_FREE_B2A_RING": f"R{a0['ring_index']}",
        "EARLIEST_ALLOWED_B2A_ANCHOR": (
            anchors[-1]["ring_id"] if anchors else None
        ),
        "V2111_NEAREST_B2A_RING": f"R{v2111_ring}",
        "ordered_anchors": anchors,
        "anchor_resolution_ledger": resolution_ledger,
    }


def main():
    report_path = Path(v14.argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    context = v17.baseline_context()
    if context["blend_sha"] != AUTHORITY_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: authority Blend hash mismatch for "
            f"{context['blend_path']}; expected {AUTHORITY_BLEND_SHA256}, "
            f"observed {context['blend_sha']}"
        )
    attribution = json.loads(
        v23.V22_ATTRIBUTION_PATH.read_text(encoding="utf-8")
    )
    corridor = v22.v21.reconstruct_v12_core(context)
    if stable_hash(corridor["public"]) != EXPECTED_V12_SHA256:
        raise RuntimeError(
            f"{OPERATION}: reconstructed V12 corridor fingerprint mismatch"
        )
    c9_tree = BVHTree.FromPolygons(
        context["c9_points"],
        context["c9_faces"],
        all_triangles=False,
    )
    source_tree = BVHTree.FromPolygons(
        context["staged_points"],
        context["staged_faces"],
        all_triangles=False,
    )
    constituents = {
        name: constituent_authority(
            name,
            corridor["core"][name],
            corridor,
            c9_tree,
            source_tree,
        )
        for name in ("B0", "B1", "B2a", "B2b")
    }
    turn = constituent_authority(
        "turn_bridge",
        corridor["turn"],
        corridor,
        c9_tree,
        source_tree,
    )
    turn["geometry_fingerprint"] = turn["fingerprint"]
    turn["fingerprint"] = stable_hash(public(corridor["turn"]))
    b2a_turn = v14.overlap_pairs(
        corridor["core"]["B2a"]["_points"],
        corridor["core"]["B2a"]["_faces"],
        corridor["turn"]["_points"],
        corridor["turn"]["_faces"],
    )
    b2b_turn = v14.overlap_pairs(
        corridor["core"]["B2b"]["_points"],
        corridor["core"]["B2b"]["_faces"],
        corridor["turn"]["_points"],
        corridor["turn"]["_faces"],
    )
    b1_b2a = v14.overlap_pairs(
        corridor["core"]["B1"]["_points"],
        corridor["core"]["B1"]["_faces"],
        corridor["core"]["B2a"]["_points"],
        corridor["core"]["B2a"]["_faces"],
    )
    for ring in constituents["B2b"]["rings"]:
        related = set(ring["related_face_ids"])
        ring["turn_bridge_overlap_pairs"] = [
            list(pair) for pair in b2b_turn if pair[0] in related
        ]
    opening_points, opening_faces, opening = v23.opening_keepout(context)
    t0 = {
        "source_face_ids": [2741, 4711],
        "face_records": v23.face_catalog(context, [2741, 4711]),
        "boundary_edges": [
            list(edge)
            for edge in v23.boundary_edges(
                [2741, 4711],
                context["staged_faces"],
            )
        ],
    }
    authority = {
        "operation": OPERATION,
        "status": "COMBINED_TAIL_AUTHORITY_CHECKPOINTED",
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "constituents": constituents,
        "turn_bridge": turn,
        "contacts": {
            "B1_to_B2a": [list(pair) for pair in b1_b2a],
            "B2a_to_turn_bridge": [list(pair) for pair in b2a_turn],
            "turn_bridge_to_B2b": [
                [second, first] for first, second in b2b_turn
            ],
        },
        "adjacency_graph": [
            ["B1", "B2a"],
            ["B2a", "turn_bridge"],
            ["turn_bridge", "B2b"],
        ],
        "source_controls": {
            "B2a": [2118, 2115, 2114, 2111, 2108],
            "B2b": [2108, 2119],
            "B0_tip": 2074,
            "B2b_tip": 2119,
            "C_tip_gap_mm": context["checks"]["tip_gap_mm"],
        },
        "fingerprints": {
            "B0": constituents["B0"]["fingerprint"],
            "B1": constituents["B1"]["fingerprint"],
            "B2a_complete": constituents["B2a"]["fingerprint"],
            "turn_bridge": turn["fingerprint"],
            "B2b": constituents["B2b"]["fingerprint"],
            "v12_corridor": stable_hash(corridor["public"]),
            "source_cage": context["checks"]["retained_fingerprint"],
            "C9": context["checks"]["component_9_fingerprint"],
            "Branch_A": attribution["immutable_complements"][
                "branch_a_fingerprint"
            ],
            "T0_landing": stable_hash(t0),
            "central_opening_keep_out": stable_hash(
                {
                    "record": opening,
                    "points": point_list(opening_points),
                    "faces": [list(face) for face in opening_faces],
                }
            ),
            "B1_to_B2a_junction": stable_hash(
                [list(pair) for pair in b1_b2a]
            ),
        },
        "T0_landing": t0,
        "central_opening_keep_out": opening,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    authority.update(resolve_anchors(context, corridor, authority))
    authority["fingerprints"]["B2a_prefixes"] = {
        anchor["anchor_id"]: anchor["prefix_fingerprint"]
        for anchor in authority["ordered_anchors"]
    }
    authority_path = report_path.with_name("combined_tail_authority.json")
    atomic_json(authority_path, authority)
    authority_sha = sha_file(authority_path)
    code_sha = sha_file(Path(__file__))
    tuple_count = (
        len(authority["ordered_anchors"])
        * 3
        * len(WIDTHS_MM)
        * len(ADVANCES_MM)
        * len(OFFSETS_MM)
        * len(OFFSETS_MM)
        * len(ROLLS_DEGREES)
    )
    contract = {
        "operation": OPERATION,
        "status": "V25_SEARCH_CONTRACT_CHECKPOINTED",
        "authority_sha256": authority_sha,
        "code_sha256": code_sha,
        "ordered_anchor_ids": [
            anchor["anchor_id"] for anchor in authority["ordered_anchors"]
        ],
        "ordered_anchor_records": authority["ordered_anchors"],
        "ordered_endpoint_ids": ["E0", "E1", "E2"],
        "ordered_widths_mm": list(WIDTHS_MM),
        "ordered_advances_mm": list(ADVANCES_MM),
        "ordered_normal_offsets_mm": list(OFFSETS_MM),
        "ordered_binormal_offsets_mm": list(OFFSETS_MM),
        "ordered_roll_knots_degrees": list(ROLLS_DEGREES),
        "candidate_tuple_schema": (
            "anchor_id:endpoint_id:width_mm:advance_mm:"
            "normal_offset_mm:binormal_offset_mm:roll_degrees"
        ),
        "candidate_tuple_count": tuple_count,
        "bounds": {
            "maximum_replaced_B2a_arclength_mm": 12.0,
            "scarf_length_mm": 6.0,
            "escape_length_mm": [6.0, 18.0],
            "maximum_radial_offset_mm": 12.0,
            "anchor_tangent_deflection_degrees": 30,
            "escape_tangent_deflection_degrees": 45,
            "lattice_spacing_mm": 4.0,
            "transverse_bounds_mm": [-24.0, 24.0],
            "maximum_chord_distance_mm": 28.0,
            "minimum_cutter_margin_mm": 1.7,
            "thickness_mm": 2.4,
        },
        "obstacle_fingerprints": {
            "source_cage": authority["fingerprints"]["source_cage"],
            "C9": authority["fingerprints"]["C9"],
            "Branch_A": authority["fingerprints"]["Branch_A"],
            "central_opening_keep_out": authority["fingerprints"][
                "central_opening_keep_out"
            ],
            "v12_corridor": authority["fingerprints"]["v12_corridor"],
        },
        "resume_contract": (
            "authority, contract, code, and obstacle hashes must all match"
        ),
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    contract_path = report_path.with_name("v25_search_contract.json")
    atomic_json(contract_path, contract)
    report = {
        "tool": Path(__file__).name,
        "operation": OPERATION,
        "status": "AUTHORITY_AND_CONTRACT_STAGE_DONE",
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "combined_tail_authority": str(authority_path),
        "combined_tail_authority_sha256": authority_sha,
        "v25_search_contract": str(contract_path),
        "v25_search_contract_sha256": sha_file(contract_path),
        "ordered_anchors": authority["ordered_anchors"],
        "candidate_tuple_count": tuple_count,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "gate_pass": False,
        "qualitative_review": "NOT_REQUESTED_NO_IMAGE_WORK",
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(report_path, report)
    print(json.dumps(report, indent=2))
    print(
        "DONE: V25 authority and contract checkpointed; "
        f"anchors={len(authority['ordered_anchors'])}; "
        f"candidate_tuples={tuple_count}; mutation_started=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
