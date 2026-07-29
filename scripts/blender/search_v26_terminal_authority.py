"""Search exact source boundaries for corrected V26 terminal authority.

Run with the V24 evidence Blend open:

    blender -b INPUT.blend --python search_v26_terminal_authority.py -- \
        --report OUTPUT/v26_terminal_authority.json

This is a read-only authority search.  It creates no candidate surface, changes
no Blender datablock, saves no Blend, and performs no image work.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audit_v26_cutter_authority as cutter_api  # noqa: E402
import build_asymmetric_elbow_interface_rail_v4 as v4  # noqa: E402
import build_three_constituent_lap_network_v17 as v17  # noqa: E402
import preflight_open_bay_joint_v26 as v26  # noqa: E402


OPERATION = "V26_TERMINAL_AUTHORITY_SEARCH"
MISSION = "R014-JOINT-C9-C20-ELBOW-V26"
MINIMUM_MARGIN_MM = 1.7
CHAIN_EDGE_COUNTS = (2, 3, 4)
EXPECTED_BLEND_SHA256 = (
    "68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823"
)
ROOT = SCRIPT_DIR.parent.parent
AUTHORITY_DIR = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
)
INPUTS = {
    "cell": (
        AUTHORITY_DIR / "v26_cell_authority.json",
        "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca",
    ),
    "cutter": (
        AUTHORITY_DIR / "v26_cutter_authority.json",
        "52baafbc473c0e85952b80c4db56bb5620310fb82aa7b23bd55f529e83b78d45",
    ),
    "ownership_summary": (
        AUTHORITY_DIR / "v26_floor_ownership_summary.json",
        "2a054e9290869a6b647b4da1fa52f98e6537c8bca2a3b12546374ff788c982a9",
    ),
    "negative_space": (
        AUTHORITY_DIR / "v26_negative_space_authority.json",
        "4ba0184076e0f635fc64eaa82da59993dfa4b75b8c8edd82efa5139db0f8f2bd",
    ),
    "review": (
        AUTHORITY_DIR / "authority_review.md",
        "c7efbcfce71eea84a6e0e75092c1f8e5e60cdf16e3e9ecb5700c35ff409ec325",
    ),
    "face_visual_classification": (
        AUTHORITY_DIR / "face_visual/classification.json",
        "d3f7dfbfff0fdaa6f50c65f6d26aa60c32567f5b3711d474ef335714a14794cf",
    ),
}

# The two cutter-penetrating C9 faces, their current ambiguous companions, and
# the visually confirmed silhouette/rim face are never eligible.
FORBIDDEN_FACE_IDS = {
    1613,
    1617,
    1696,
}


def sha_file(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value):
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def archive_existing(path):
    """Preserve a completed authority before starting a superseding run."""
    path = Path(path)
    if not path.exists():
        return None
    digest = sha_file(path)
    archived = path.with_name(
        f"{path.stem}.stale-{digest[:12]}{path.suffix}"
    )
    if archived.exists():
        if sha_file(archived) != digest:
            raise RuntimeError(
                f"{OPERATION}: stale artifact hash collision for "
                f"'{archived}'"
            )
        return {
            "path": str(archived),
            "sha256": digest,
            "already_archived": True,
        }
    path.replace(archived)
    return {
        "path": str(archived),
        "sha256": digest,
        "already_archived": False,
    }


def argument(name):
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    try:
        return arguments[arguments.index(name) + 1]
    except (ValueError, IndexError) as error:
        raise RuntimeError(
            f"{OPERATION}: missing required argument {name}; "
            f"received={arguments}"
        ) from error


def point_record(point):
    return [float(value) for value in point]


def source_triangles(context, face_ids):
    records = []
    for face_id in sorted(face_ids):
        face = context["staged_faces"][face_id]
        for fan_index in range(1, len(face) - 1):
            vertex_ids = (face[0], face[fan_index], face[fan_index + 1])
            records.append(
                {
                    "triangle_id": f"face_{face_id}:fan_{fan_index - 1}",
                    "source_fixture": {
                        "kind": "exact_terminal_incident_source_triangle",
                        "source_face_id": face_id,
                        "source_vertex_ids": list(vertex_ids),
                    },
                    "points": tuple(
                        context["staged_points"][vertex].copy()
                        for vertex in vertex_ids
                    ),
                }
            )
    return records


def clearance_summary(record):
    nearest = record["minimum_triangle_to_cutter"]
    samples = record["adaptive_samples"]
    return {
        "triangle_id": record["candidate_triangle_id"],
        "source_face_id": record["source_fixture"]["source_face_id"],
        "source_vertex_ids": record["source_fixture"]["source_vertex_ids"],
        "points_mm": record["points_mm"],
        "exact_intersection_pairs": record["intersection_pairs"],
        "minimum_triangle_to_cutter": nearest,
        "adaptive_converged": samples["converged"],
        "adaptive_refinement_history": samples["refinement_history"],
        "minimum_signed_sample_margin_mm": record[
            "minimum_signed_sample_margin_mm"
        ],
        "rejection_reasons": record["rejection_reasons"],
        "clearance_pass": record["clearance_pass"],
    }


def edge_clearance(points, cutter_tree, orientation_sign):
    samples = []
    for edge_index, (first, second) in enumerate(zip(points, points[1:])):
        divisions = max(
            1,
            int(ceil((second - first).length)),
        )
        for sample_index in range(divisions + 1):
            if edge_index and sample_index == 0:
                continue
            factor = sample_index / divisions
            sample = cutter_api.signed_margin(
                first.lerp(second, factor),
                cutter_tree,
                orientation_sign,
            )
            sample["chain_edge_index"] = edge_index
            sample["edge_parameter"] = factor
            samples.append(sample)
    minimum = min(
        (record["signed_margin_mm"] for record in samples),
        default=None,
    )
    return {
        "maximum_sample_spacing_mm": 1.0,
        "samples": samples,
        "minimum_signed_margin_mm": minimum,
        "clearance_pass": minimum is not None and minimum >= MINIMUM_MARGIN_MM,
    }


def negative_space_edge_ids(authority, edge_ids_by_vertices):
    result = set()
    sources = defaultdict(list)
    for group in authority["source_open_route_keepouts"]["groups"]:
        for edge_id in group["source_edge_ids"]:
            result.add(edge_id)
            sources[edge_id].append(group["route_id"])
    for aperture in authority["aperture_keepouts"]:
        for edge_id in aperture["source"]["source_edge_ids"]:
            result.add(edge_id)
            sources[edge_id].append(aperture["keepout_id"])
    for vertices in authority["central_opening_keepouts"][
        "source_edge_vertex_ids"
    ]:
        key = tuple(sorted(vertices))
        if key not in edge_ids_by_vertices:
            raise RuntimeError(
                f"{OPERATION}: central-opening source edge {key} is absent "
                "from the staged source topology"
            )
        edge_id = edge_ids_by_vertices[key]
        result.add(edge_id)
        sources[edge_id].append("CENTRAL_OPENING")
    return result, {str(key): sorted(value) for key, value in sources.items()}


def visual_classification_sets(authority):
    if authority["status"] != "DONE_SOURCE_FACE_CLASSIFICATION_V26":
        raise RuntimeError(
            f"{OPERATION}: visual classification status is "
            f"{authority['status']!r}, expected "
            "'DONE_SOURCE_FACE_CLASSIFICATION_V26'"
        )
    if authority["authority"]["blend_sha256"] != EXPECTED_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: visual classification Blend authority mismatch"
        )
    classifications = authority["classifications"]
    if classifications["unresolved"]:
        raise RuntimeError(
            f"{OPERATION}: visual classification still has unresolved faces: "
            f"{classifications['unresolved']}"
        )
    result = {
        "C20": {"wearer": set(), "immutable": set()},
        "C9": {"wearer": set(), "immutable": set()},
    }
    for class_name, target in (
        ("concealed_wearer_side_removable", "wearer"),
        ("visible_silhouette_rim_opening_immutable", "immutable"),
    ):
        for group, face_ids in classifications[class_name].items():
            component = "C20" if group.endswith("_c20") else "C9"
            result[component][target].update(face_ids)
    for component in ("C20", "C9"):
        overlap = result[component]["wearer"] & result[component]["immutable"]
        if overlap:
            raise RuntimeError(
                f"{OPERATION}: visual classification overlaps for "
                f"{component}: {sorted(overlap)}"
            )
    expected = {
        "C9": {
            "wearer": {1621, 1676, 1700, 2243, 2244},
            "immutable": {1613, 1617, 1619, 1623, 1696},
        },
        "C20": {
            "wearer": {2663, 3102, 3103, 8839, 8844},
            "immutable": {3065, 3066, 8699, 8700},
        },
    }
    if result != expected:
        raise RuntimeError(
            f"{OPERATION}: visual classification exact face authority "
            f"mismatch; actual={result}; expected={expected}"
        )
    return result


def exposure_sets(ownership, visual_authority):
    """Stream the five exposure ID pairs; never load the 315 MiB ledger."""
    full = ownership["full_authority"]
    ledger_path = Path(full["path"])
    if not ledger_path.is_file():
        raise RuntimeError(
            f"{OPERATION}: ownership ledger is absent: '{ledger_path}'"
        )
    if ledger_path.stat().st_size != full["size_bytes"]:
        raise RuntimeError(
            f"{OPERATION}: ownership ledger size mismatch for '{ledger_path}'; "
            f"actual={ledger_path.stat().st_size}; expected={full['size_bytes']}"
        )
    if sha_file(ledger_path) != full["sha256"]:
        raise RuntimeError(
            f"{OPERATION}: ownership ledger hash mismatch for '{ledger_path}'"
        )
    cell_ids = ownership["exact_atomic_cell_ids"]
    pairs = []
    current = {}
    active_key = None
    fragments = []
    with ledger_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if active_key is None:
                for key in ("wearer_facing_face_ids", "ambiguous_face_ids"):
                    marker = f'"{key}":'
                    if marker not in line:
                        continue
                    active_key = key
                    fragments = [line.split(marker, 1)[1].strip()]
                    break
            else:
                fragments.append(line.strip())
            if active_key is None:
                continue
            joined = " ".join(fragments)
            try:
                value, end = json.JSONDecoder().raw_decode(joined)
            except json.JSONDecodeError:
                continue
            if joined[end:].strip().startswith(","):
                pass
            if not isinstance(value, list) or not all(
                isinstance(item, int) for item in value
            ):
                raise RuntimeError(
                    f"{OPERATION}: streamed exposure key {active_key} is not "
                    "an integer array"
                )
            current[active_key] = value
            active_key = None
            fragments = []
            if set(current) == {
                "wearer_facing_face_ids",
                "ambiguous_face_ids",
            }:
                pairs.append(current)
                current = {}
                if len(pairs) == len(cell_ids):
                    break
    if len(pairs) != len(cell_ids):
        raise RuntimeError(
            f"{OPERATION}: streamed {len(pairs)} exposure records from "
            f"'{ledger_path}', expected={len(cell_ids)}"
        )
    result = {}
    visual = visual_classification_sets(visual_authority)
    for component in ("C20", "C9"):
        wearer = set()
        ambiguous = set()
        for cell_id, record in zip(cell_ids, pairs):
            record_component = cell_id.split("_")[2]
            if record_component != component:
                continue
            wearer.update(record["wearer_facing_face_ids"])
            ambiguous.update(record["ambiguous_face_ids"])
        if wearer & ambiguous:
            raise RuntimeError(
                f"{OPERATION}: exposure authority overlaps for {component}: "
                f"{sorted(wearer & ambiguous)}"
            )
        maximum = wearer | ambiguous
        visual_faces = visual[component]["wearer"] | visual[component]["immutable"]
        if not visual_faces <= maximum:
            raise RuntimeError(
                f"{OPERATION}: visual classification leaves the {component} "
                f"maximum exposure authority: {sorted(visual_faces - maximum)}"
            )
        wearer.difference_update(visual[component]["immutable"])
        ambiguous.difference_update(visual[component]["wearer"])
        wearer.update(visual[component]["wearer"])
        ambiguous.update(visual[component]["immutable"])
        if wearer & ambiguous:
            raise RuntimeError(
                f"{OPERATION}: corrected exposure authority overlaps for "
                f"{component}: {sorted(wearer & ambiguous)}"
            )
        if wearer | ambiguous != maximum:
            raise RuntimeError(
                f"{OPERATION}: corrected exposure authority changed the "
                f"{component} maximum face set"
            )
        result[component] = {
            "wearer": wearer,
            "immutable": ambiguous,
            "visual_override": visual[component],
        }
    return result


def boundary_edge_records(context, exposure, negative_edges, negative_sources):
    edge_ids, edge_faces, edge_winding = v26.source_edge_context(context)
    records = {"C20": [], "C9": []}
    rejected = []
    for component in ("C20", "C9"):
        wearer = exposure[component]["wearer"]
        immutable = exposure[component]["immutable"]
        for vertices, linked in sorted(
            edge_faces.items(),
            key=lambda item: edge_ids[item[0]],
        ):
            candidate_faces = sorted(wearer & set(linked))
            retained_faces = sorted(immutable & set(linked))
            if not candidate_faces or not retained_faces:
                continue
            edge_id = edge_ids[vertices]
            reasons = []
            if len(linked) != 2:
                reasons.append("source_edge_not_manifold")
            if len(candidate_faces) != 1:
                reasons.append("candidate_side_not_unique")
            if len(retained_faces) != 1:
                reasons.append("retained_side_not_unique")
            incident = sorted(set(candidate_faces) | set(retained_faces))
            if set(incident) & FORBIDDEN_FACE_IDS:
                reasons.append("forbidden_current_terminal_face")
            if edge_id in negative_edges:
                reasons.append("immutable_negative_space_route_edge")
            candidate_materials = {
                context["staged_materials"][face_id]
                for face_id in candidate_faces
            }
            retained_materials = {
                context["staged_materials"][face_id]
                for face_id in retained_faces
            }
            if candidate_materials != retained_materials:
                reasons.append("material_boundary")
            record = {
                "component": component,
                "source_edge_id": edge_id,
                "vertex_ids": list(vertices),
                "exact_source_coordinates_mm": [
                    point_record(context["staged_points"][vertex])
                    for vertex in vertices
                ],
                "candidate_incident_face_ids": candidate_faces,
                "retained_incident_face_ids": retained_faces,
                "all_source_incident_face_ids": sorted(linked),
                "candidate_source_winding": (
                    edge_winding[(candidate_faces[0], vertices)]
                    if len(candidate_faces) == 1
                    else None
                ),
                "retained_source_winding": (
                    edge_winding[(retained_faces[0], vertices)]
                    if len(retained_faces) == 1
                    else None
                ),
                "candidate_material_indices": sorted(candidate_materials),
                "retained_material_indices": sorted(retained_materials),
                "negative_space_authority_ids": negative_sources.get(
                    str(edge_id), []
                ),
                "rejection_reasons": reasons,
                "eligible_before_clearance": not reasons,
            }
            if reasons:
                rejected.append(record)
            else:
                records[component].append(record)
    return records, rejected


def enumerate_chains(component, edges):
    by_id = {record["source_edge_id"]: record for record in edges}
    by_vertex = defaultdict(list)
    for record in edges:
        for vertex in record["vertex_ids"]:
            by_vertex[vertex].append(record["source_edge_id"])
    canonical = {}

    def walk(vertex_ids, edge_ids):
        if len(edge_ids) in CHAIN_EDGE_COUNTS:
            forward = tuple(edge_ids)
            reverse = tuple(reversed(edge_ids))
            key = min(forward, reverse)
            canonical[key] = list(key)
        if len(edge_ids) >= max(CHAIN_EDGE_COUNTS):
            return
        for edge_id in sorted(by_vertex[vertex_ids[-1]]):
            if edge_id in edge_ids:
                continue
            record = by_id[edge_id]
            first, second = record["vertex_ids"]
            next_vertex = second if first == vertex_ids[-1] else first
            if next_vertex in vertex_ids:
                continue
            walk([*vertex_ids, next_vertex], [*edge_ids, edge_id])

    for edge_id in sorted(by_id):
        first, second = by_id[edge_id]["vertex_ids"]
        walk([first, second], [edge_id])
        walk([second, first], [edge_id])

    records = []
    for edge_ids in sorted(canonical.values()):
        first_edge = by_id[edge_ids[0]]
        shared = set(first_edge["vertex_ids"]) & set(
            by_id[edge_ids[1]]["vertex_ids"]
        )
        if len(shared) != 1:
            continue
        shared_vertex = next(iter(shared))
        first_vertex = next(
            vertex
            for vertex in first_edge["vertex_ids"]
            if vertex != shared_vertex
        )
        vertex_ids = [first_vertex, shared_vertex]
        valid = True
        for edge_id in edge_ids[1:]:
            candidates = [
                vertex
                for vertex in by_id[edge_id]["vertex_ids"]
                if vertex != vertex_ids[-1]
            ]
            if len(candidates) != 1:
                valid = False
                break
            vertex_ids.append(candidates[0])
        if not valid:
            continue
        reverse_vertices = list(reversed(vertex_ids))
        if tuple(reverse_vertices) < tuple(vertex_ids):
            vertex_ids = reverse_vertices
            edge_ids = list(reversed(edge_ids))
        candidate_faces = sorted(
            {
                face_id
                for edge_id in edge_ids
                for face_id in by_id[edge_id]["candidate_incident_face_ids"]
            }
        )
        retained_faces = sorted(
            {
                face_id
                for edge_id in edge_ids
                for face_id in by_id[edge_id]["retained_incident_face_ids"]
            }
        )
        records.append(
            {
                "chain_id": (
                    f"{component}_CHAIN_"
                    + "_".join(str(edge_id) for edge_id in edge_ids)
                ),
                "component": component,
                "source_edge_ids": edge_ids,
                "ordered_boundary_vertex_ids": vertex_ids,
                "exact_source_coordinates_mm": [],
                "candidate_incident_face_ids": candidate_faces,
                "retained_incident_face_ids": retained_faces,
                "edge_records": [by_id[edge_id] for edge_id in edge_ids],
            }
        )
    return records


def station_mm(context, point):
    target_length = float(
        bpy.data.objects[v4.CANDIDATE_NAME]["target_length_mm"]
    )
    station, _, _, _ = v4.radial_coordinates(point, target_length)
    return float(station * target_length)


def old_terminal_landmarks(cell_authority):
    result = {}
    for terminal in cell_authority["terminal_boundary_coincidence"]["records"]:
        points = [
            Vector(coordinate)
            for coordinate in terminal["exact_source_coordinates_mm"]
        ]
        result[(terminal["component"], terminal["role"])] = (
            sum(points, Vector()) / len(points)
        )
    return result


def main():
    report_path = Path(argument("--report")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    stale_artifact = archive_existing(report_path)
    actual_hashes = {
        name: sha_file(path)
        for name, (path, _) in INPUTS.items()
    }
    expected_hashes = {
        name: expected
        for name, (_, expected) in INPUTS.items()
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(
            f"{OPERATION}: authority mismatch; actual={actual_hashes}; "
            f"expected={expected_hashes}"
        )
    authorities = {
        name: (
            json.loads(path.read_text(encoding="utf-8"))
            if path.suffix == ".json"
            else path.read_text(encoding="utf-8")
        )
        for name, (path, _) in INPUTS.items()
    }
    context = v17.baseline_context()
    if context["blend_sha"] != EXPECTED_BLEND_SHA256:
        raise RuntimeError(
            f"{OPERATION}: input Blend mismatch for "
            f"'{context['blend_path']}'; actual={context['blend_sha']}; "
            f"expected={EXPECTED_BLEND_SHA256}"
        )
    scene_before = {
        "is_dirty": bool(bpy.data.is_dirty),
        "object_names": sorted(obj.name for obj in bpy.data.objects),
        "mesh_names": sorted(mesh.name for mesh in bpy.data.meshes),
    }
    initial = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": "V26_TERMINAL_SEARCH_AUTHORITY_CHECKPOINTED",
        "input_blend": str(context["blend_path"]),
        "input_blend_sha256": context["blend_sha"],
        "authority_sha256": actual_hashes,
        "finite_search_contract": {
            "components": ["C20", "C9"],
            "chain_edge_counts": list(CHAIN_EDGE_COUNTS),
            "candidate_side": "WEARER_FACING only",
            "retained_side": "EXTERIOR_OR_AMBIGUOUS immutable complement",
            "minimum_exact_triangle_and_signed_sample_margin_mm": (
                MINIMUM_MARGIN_MM
            ),
            "forbidden_source_face_ids": sorted(FORBIDDEN_FACE_IDS),
            "selection": (
                "nearest cutter-clear exact boundary chain to each former "
                "component/role fixture, with a chain used by at most one role"
            ),
        },
        "superseded_artifact": stale_artifact,
        "search_started": False,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
        "image_work_requested": False,
        "promotion": "NOT_PROMOTED",
    }
    atomic_json(report_path, initial)

    edge_ids, _, _ = v26.source_edge_context(context)
    negative_edges, negative_sources = negative_space_edge_ids(
        authorities["negative_space"],
        edge_ids,
    )
    exposure = exposure_sets(
        authorities["ownership_summary"],
        authorities["face_visual_classification"],
    )
    edges, rejected_edges = boundary_edge_records(
        context,
        exposure,
        negative_edges,
        negative_sources,
    )
    chains = [
        chain
        for component in ("C20", "C9")
        for chain in enumerate_chains(component, edges[component])
    ]
    incident_faces = sorted(
        {
            face_id
            for chain in chains
            for face_id in (
                chain["candidate_incident_face_ids"]
                + chain["retained_incident_face_ids"]
            )
        }
    )
    cutter = bpy.data.objects[cutter_api.EXPECTED_CUTTER_NAME]
    provenance, cutter_points, cutter_triangles, orientation_sign = (
        cutter_api.evaluated_cutter_provenance(cutter)
    )
    face_clearance = cutter_api.clearance_contract(
        source_triangles(context, incident_faces),
        cutter_points,
        cutter_triangles,
        orientation_sign,
    )
    triangle_records = [
        clearance_summary(record)
        for record in face_clearance["triangle_records"]
    ]
    face_records = defaultdict(list)
    for record in triangle_records:
        face_records[record["source_face_id"]].append(record)
    cutter_tree = BVHTree.FromPolygons(
        cutter_points,
        cutter_triangles,
        all_triangles=True,
    )
    landmarks = old_terminal_landmarks(authorities["cell"])
    tested = []
    for chain in chains:
        points = [
            context["staged_points"][vertex].copy()
            for vertex in chain["ordered_boundary_vertex_ids"]
        ]
        chain["exact_source_coordinates_mm"] = [
            point_record(point) for point in points
        ]
        relevant = [
            record
            for face_id in (
                chain["candidate_incident_face_ids"]
                + chain["retained_incident_face_ids"]
            )
            for record in face_records[face_id]
        ]
        boundary_clearance = edge_clearance(
            points,
            cutter_tree,
            orientation_sign,
        )
        reasons = []
        failed_faces = sorted(
            {
                record["source_face_id"]
                for record in relevant
                if not record["clearance_pass"]
            }
        )
        if failed_faces:
            reasons.append("incident_triangle_cutter_clearance_below_1.7mm")
        if not boundary_clearance["clearance_pass"]:
            reasons.append("boundary_edge_cutter_clearance_below_1.7mm")
        midpoint = sum(points, Vector()) / len(points)
        distances = {
            role: float((midpoint - landmarks[(chain["component"], role)]).length)
            for role in ("UPPER", "LOWER")
        }
        chain.update(
            {
                "boundary_exactly_source_coincident": True,
                "station_range_mm": [
                    min(station_mm(context, point) for point in points),
                    max(station_mm(context, point) for point in points),
                ],
                "midpoint_mm": point_record(midpoint),
                "former_fixture_distance_mm": distances,
                "boundary_clearance": boundary_clearance,
                "incident_triangle_ids": [
                    record["triangle_id"] for record in relevant
                ],
                "failed_incident_face_ids": failed_faces,
                "rejection_reasons": reasons,
                "eligible": not reasons,
            }
        )
        tested.append(chain)

    selected = {}
    used = set()
    for component in ("C20", "C9"):
        selected[component] = {}
        for role in ("UPPER", "LOWER"):
            eligible = sorted(
                (
                    chain
                    for chain in tested
                    if chain["component"] == component
                    and chain["eligible"]
                    and chain["chain_id"] not in used
                ),
                key=lambda chain: (
                    chain["former_fixture_distance_mm"][role],
                    len(chain["source_edge_ids"]),
                    chain["source_edge_ids"],
                ),
            )
            choice = eligible[0] if eligible else None
            selected[component][role] = (
                {
                    "chain_id": choice["chain_id"],
                    "source_edge_ids": choice["source_edge_ids"],
                    "ordered_boundary_vertex_ids": choice[
                        "ordered_boundary_vertex_ids"
                    ],
                    "exact_source_coordinates_mm": choice[
                        "exact_source_coordinates_mm"
                    ],
                    "candidate_incident_face_ids": choice[
                        "candidate_incident_face_ids"
                    ],
                    "retained_incident_face_ids": choice[
                        "retained_incident_face_ids"
                    ],
                    "candidate_source_winding": [
                        record["candidate_source_winding"]
                        for record in choice["edge_records"]
                    ],
                    "retained_source_winding": [
                        record["retained_source_winding"]
                        for record in choice["edge_records"]
                    ],
                    "material_indices": choice["edge_records"][0][
                        "candidate_material_indices"
                    ],
                    "minimum_boundary_signed_margin_mm": choice[
                        "boundary_clearance"
                    ]["minimum_signed_margin_mm"],
                    "minimum_incident_triangle_distance_mm": min(
                        record["minimum_triangle_to_cutter"]["distance_mm"]
                        for face_id in (
                            choice["candidate_incident_face_ids"]
                            + choice["retained_incident_face_ids"]
                        )
                        for record in face_records[face_id]
                    ),
                    "minimum_incident_signed_sample_margin_mm": min(
                        record["minimum_signed_sample_margin_mm"]
                        for face_id in (
                            choice["candidate_incident_face_ids"]
                            + choice["retained_incident_face_ids"]
                        )
                        for record in face_records[face_id]
                    ),
                    "boundary_exactly_source_coincident": True,
                    "selection_distance_to_former_fixture_mm": choice[
                        "former_fixture_distance_mm"
                    ][role],
                }
                if choice is not None
                else None
            )
            if choice is not None:
                used.add(choice["chain_id"])

    upper_exists = all(
        selected[component]["UPPER"] is not None
        for component in ("C20", "C9")
    )
    lower_exists = all(
        selected[component]["LOWER"] is not None
        for component in ("C20", "C9")
    )
    both_sides_exist = upper_exists and lower_exists
    scene_after = {
        "is_dirty": bool(bpy.data.is_dirty),
        "object_names": sorted(obj.name for obj in bpy.data.objects),
        "mesh_names": sorted(mesh.name for mesh in bpy.data.meshes),
    }
    if scene_after != scene_before:
        raise RuntimeError(
            f"{OPERATION}: read-only scene invariant changed; "
            f"before={scene_before}; after={scene_after}"
        )
    report = {
        **initial,
        "status": (
            "V26_BOTH_TERMINAL_SIDES_EXIST"
            if both_sides_exist
            else "NO_BOUNDARY_COINCIDENT_TERMINAL_PAIR_V26"
        ),
        "search_started": True,
        "search_completed": True,
        "authority_inputs": {
            name: {"path": str(INPUTS[name][0]), "sha256": actual_hashes[name]}
            for name in INPUTS
        },
        "cutter_provenance": {
            "object_name": provenance["object_name"],
            "geometry_fingerprint": provenance["geometry_fingerprint"],
            "provenance_fingerprint": provenance["provenance_fingerprint"],
            "orientation": provenance["signed_orientation"],
        },
        "exposure_counts": {
            component: {
                "wearer_facing_face_count": len(exposure[component]["wearer"]),
                "immutable_face_count": len(exposure[component]["immutable"]),
                "visual_override": {
                    key: sorted(value)
                    for key, value in exposure[component][
                        "visual_override"
                    ].items()
                },
            }
            for component in ("C20", "C9")
        },
        "negative_space_source_edge_ids": sorted(negative_edges),
        "rejected_boundary_edges": rejected_edges,
        "eligible_boundary_edges": edges,
        "tested_chains": tested,
        "incident_triangle_clearance_records": triangle_records,
        "selection": selected,
        "result": {
            "upper_terminal_pair_exists": upper_exists,
            "lower_terminal_pair_exists": lower_exists,
            "both_sides_exist": both_sides_exist,
            "tested_chain_count": len(tested),
            "eligible_chain_count": sum(chain["eligible"] for chain in tested),
            "rejected_chain_count": sum(
                not chain["eligible"] for chain in tested
            ),
            "candidate_surface_construction_authorized": False,
            "flex_gap_placement_authorized": False,
        },
        "source_scene_invariant": {
            "unchanged": True,
            "before": scene_before,
            "after": scene_after,
        },
    }
    report["semantic_fingerprint"] = stable_hash(report)
    atomic_json(report_path, report)
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "status": report["status"],
                "report": str(report_path),
                "tested_chain_count": report["result"]["tested_chain_count"],
                "eligible_chain_count": report["result"][
                    "eligible_chain_count"
                ],
                "upper_terminal_pair_exists": upper_exists,
                "lower_terminal_pair_exists": lower_exists,
                "both_sides_exist": both_sides_exist,
                "mutation_started": False,
                "geometry_emitted": False,
                "blend_saved": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
