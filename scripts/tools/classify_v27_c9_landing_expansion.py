#!/usr/bin/env python3
"""Classify the exact C9 landing-mask expansion against frozen authorities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


OPERATION = "CLASSIFY_V27_C9_LANDING_EXPANSION"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
V26 = V27.parent / "repair_014_joint_c9_c20_elbow_v26"
BOUNDARY_AUTHORITY = V27 / "v27_c9_landing_boundary_authority.json"
AGGREGATE_AUTHORITY = V27 / "v27_aggregate_authority.json"
EXPOSURE_AUTHORITY = V26 / "v26_exposure_cell_authority.json"
CELL_AUTHORITY = V26 / "v26_cell_authority.json"
TERMINAL_AUTHORITY = V26 / "v26_terminal_authority.json"
OUTPUT = V27 / "v27_c9_landing_expansion_classification.json"
RECEIPT = V27 / "v27_c9_landing_expansion_classification_receipt.json"
EXPANSION_FACE_IDS = [2220, 2221, 2222, 2224, 2225, 2226, 2229, 2233, 2283, 2284]
EXPECTED_HASHES = {
    "boundary_authority": (
        BOUNDARY_AUTHORITY,
        "83b7c5ed527f241a8e4e31b5e125ec395fd8c8ebe9cdc8bcce419bddd53079f6",
    ),
    "aggregate_authority": (
        AGGREGATE_AUTHORITY,
        "43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338",
    ),
    "exposure_authority": (
        EXPOSURE_AUTHORITY,
        "bba29d185676ed6dadaa77c81b37ae8d05f149886a3151887b2804c88bc9b0a5",
    ),
    "cell_authority": (
        CELL_AUTHORITY,
        "85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca",
    ),
    "terminal_authority": (
        TERMINAL_AUTHORITY,
        "159cbf3a3ddacf0a6628d7f4d2f5bf5a69161727176095871ef3899e7d807c1d",
    ),
}


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    verified_inputs = {}
    for label, (path, expected) in sorted(EXPECTED_HASHES.items()):
        actual = sha_file(path)
        if actual != expected:
            raise RuntimeError(
                f"{OPERATION}: V27_C9_LANDING_EXPANSION_INPUT_HASH_MISMATCH; "
                f"input={label}; path={path}; expected={expected}; "
                f"actual={actual}"
            )
        verified_inputs[label] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual,
        }

    boundary = load(BOUNDARY_AUTHORITY)
    aggregate = load(AGGREGATE_AUTHORITY)
    exposure = load(EXPOSURE_AUTHORITY)
    cell = load(CELL_AUTHORITY)
    terminal = load(TERMINAL_AUTHORITY)
    required = boundary["boundary"][
        "required_adjacent_face_ids_for_any_boundary_motion"
    ]
    if required != EXPANSION_FACE_IDS:
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_EXPANSION_FACE_SET_MISMATCH; "
            f"expected={EXPANSION_FACE_IDS}; actual={required}"
        )

    selected = set(aggregate["aggregate_mask"]["source_face_ids"]["C9"])
    immutable = set(
        aggregate["aggregate_mask"][
            "immutable_complement_source_face_ids"
        ]["C9"]
    )
    maximum = set(cell["maximum_masks"]["C9"]["face_ids"])
    ambiguous = set(
        exposure["immutable_complements"]["C9"][
            "ambiguous_source_face_ids"
        ]
    )
    exposure_membership: dict[int, list[str]] = {
        face_id: [] for face_id in EXPANSION_FACE_IDS
    }
    for record in exposure["exposure_cells"]:
        if record["component"] != "C9":
            continue
        for face_id in set(record["source_face_ids"]) & set(EXPANSION_FACE_IDS):
            exposure_membership[face_id].append(record["name"])

    barrier_records: dict[int, list[dict[str, Any]]] = {
        face_id: [] for face_id in EXPANSION_FACE_IDS
    }
    for record in cell["barriers"]["inventory"]:
        hits = set(record.get("adjacent_source_face_ids", [])) & set(
            EXPANSION_FACE_IDS
        )
        for face_id in hits:
            barrier_records[face_id].append(
                {
                    "barrier_id": record.get("barrier_id"),
                    "kind": record.get("kind"),
                    "reason": record.get("reason"),
                    "source_edge_id": record.get("source_edge_id"),
                    "adjacent_source_face_ids": record.get(
                        "adjacent_source_face_ids", []
                    ),
                }
            )

    negative_incidences: dict[int, list[dict[str, Any]]] = {
        face_id: [] for face_id in EXPANSION_FACE_IDS
    }
    for record in aggregate["negative_space_incidences"]:
        for face_id in set(record["intersecting_source_face_ids"]) & set(
            EXPANSION_FACE_IDS
        ):
            negative_incidences[face_id].append(
                {
                    "keepout_cell_id": record["keepout_cell_id"],
                    "keepout_kind": record["keepout_kind"],
                    "exposure_cell_id": record["exposure_cell_id"],
                }
            )

    terminal_vertices = {
        int(vertex_id)
        for side in terminal["selection"]["C9"].values()
        for vertex_id in side["ordered_boundary_vertex_ids"]
    }
    terminal_faces = {
        int(face_id)
        for side in terminal["selection"]["C9"].values()
        for key in ("candidate_incident_face_ids", "retained_incident_face_ids")
        for face_id in side[key]
    }
    face_records = []
    for face_id in EXPANSION_FACE_IDS:
        ownership = (
            "AGGREGATE_SELECTED"
            if face_id in selected
            else "IMMUTABLE_COMPLEMENT"
            if face_id in immutable
            else "UNACCOUNTED"
        )
        classification = (
            "WEARER_SIDE_SELECTED"
            if face_id in selected
            else "EXTERIOR_OR_AMBIGUOUS_IMMUTABLE"
            if face_id in ambiguous
            else "UNKNOWN"
        )
        face_records.append(
            {
                "face_id": face_id,
                "inside_c9_maximum_mask": face_id in maximum,
                "v27_ownership": ownership,
                "frozen_exposure_classification": classification,
                "exposure_cell_ids": sorted(exposure_membership[face_id]),
                "barrier_records": barrier_records[face_id],
                "negative_space_incidences": sorted(
                    negative_incidences[face_id],
                    key=lambda record: (
                        record["keepout_kind"],
                        record["keepout_cell_id"],
                    ),
                ),
                "terminal_face_incidence": face_id in terminal_faces,
            }
        )

    selected_expansion = [
        record["face_id"]
        for record in face_records
        if record["v27_ownership"] == "AGGREGATE_SELECTED"
    ]
    immutable_expansion = [
        record["face_id"]
        for record in face_records
        if record["v27_ownership"] == "IMMUTABLE_COMPLEMENT"
    ]
    source_open_route_faces = [
        record["face_id"]
        for record in face_records
        if any(
            incidence["keepout_kind"] == "SOURCE_OPEN_ROUTE"
            for incidence in record["negative_space_incidences"]
        )
    ]
    status = "V27_C9_LANDING_EXPANSION_REQUIRES_VISIBLE_ROLE_REVIEW"
    result = {
        "operation": OPERATION,
        "status": status,
        "scope": (
            "read-only classification of the exact ten-face expansion proven "
            "necessary by the fixed-boundary clearance authority"
        ),
        "code_sha256": sha_file(Path(__file__).resolve()),
        "verified_inputs": verified_inputs,
        "required_expansion_face_ids": EXPANSION_FACE_IDS,
        "classification": {
            "records": face_records,
            "aggregate_selected_face_ids": selected_expansion,
            "immutable_ambiguous_face_ids": immutable_expansion,
            "source_open_route_incident_face_ids": source_open_route_faces,
            "terminal_face_ids": sorted(
                set(EXPANSION_FACE_IDS) & terminal_faces
            ),
            "terminal_vertex_ids": sorted(terminal_vertices),
            "all_faces_inside_c9_maximum_mask": all(
                record["inside_c9_maximum_mask"] for record in face_records
            ),
        },
        "decision": {
            "automatic_mask_expansion_authorized": False,
            "reason": (
                "eight necessary faces are frozen exterior-or-ambiguous "
                "immutable evidence; face 2283 also has an exact source-open-"
                "route incidence; visible role and opening preservation must "
                "be reviewed before a contract revision"
            ),
            "next_operation": (
                "review the eight immutable ambiguous faces as a bounded "
                "visible-role set and retain the exact source-open-route "
                "keepout while defining any expanded reconstruction mask"
            ),
        },
        "invariants": {
            "all_frozen_hashes_match": True,
            "required_face_set_matches_boundary_authority": True,
            "every_face_has_unique_v27_ownership": all(
                record["v27_ownership"] != "UNACCOUNTED"
                for record in face_records
            ),
            "all_faces_inside_c9_maximum_mask": all(
                record["inside_c9_maximum_mask"] for record in face_records
            ),
            "no_terminal_face_incidence": not (
                set(EXPANSION_FACE_IDS) & terminal_faces
            ),
        },
        "safety": {
            "mutation_started": False,
            "geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
        },
    }
    if not all(result["invariants"].values()):
        failed = [
            key for key, passed in result["invariants"].items() if not passed
        ]
        raise RuntimeError(
            f"{OPERATION}: V27_C9_LANDING_EXPANSION_INVARIANT_FAILED; "
            f"failed={failed}"
        )
    result["semantic_fingerprint"] = stable_hash(result)
    atomic_json(OUTPUT, result)
    receipt = {
        "operation": OPERATION,
        "status": status,
        "authority_path": str(OUTPUT),
        "authority_sha256": sha_file(OUTPUT),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "aggregate_selected_face_ids": selected_expansion,
        "immutable_ambiguous_face_ids": immutable_expansion,
        "source_open_route_incident_face_ids": source_open_route_faces,
        "terminal_face_ids": result["classification"]["terminal_face_ids"],
        "safety": result["safety"],
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
