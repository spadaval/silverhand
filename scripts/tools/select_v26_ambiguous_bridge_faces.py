#!/usr/bin/env python3
"""Select the next deterministic V26 ambiguous bridge-face review batch.

This command reads only JSON authority.  It does not open Blender, inspect or
generate images, construct candidate geometry, or change exposure authority.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path


OPERATION = "V26_AMBIGUOUS_BRIDGE_FACE_SELECTOR"
MISSION = "R014-JOINT-C9-C20-ELBOW-V26"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTHORITY = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
    / "v26_exposure_cell_authority.json"
)
EXPECTED_AUTHORITY_SHA256 = (
    "1b716b8b2415145d31850bd09a2cdf001fb3ed30a1e65822f33124393ca59507"
)
ROUND_INDEX = 2
EXPECTED_REVIEWED_FACE_COUNT = 45
EXPECTED_ROUND_FACE_IDS = {"C9": [], "C20": []}


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


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authority",
        type=Path,
        default=DEFAULT_AUTHORITY,
        help="V26 exposure-cell authority JSON",
    )
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    return parser.parse_args()


def reviewed_face_authority(authority):
    revision = authority["contract_revision"]
    base = {
        "concealed_wearer_side_removable": sorted(
            revision["concealed_wearer_side_removable_face_ids"]
        ),
        "visible_silhouette_rim_opening_immutable": sorted(
            revision["visible_silhouette_rim_opening_immutable_face_ids"]
        ),
    }
    bridge = revision["bridge_classification_round_01"]
    round_01 = {
        key: sorted(value)
        for key, value in bridge.items()
        if key.endswith("_face_ids")
    }
    base_ids = {
        face_id for face_ids in base.values() for face_id in face_ids
    }
    round_01_ids = {
        face_id for face_ids in round_01.values() for face_id in face_ids
    }
    if base_ids & round_01_ids:
        raise RuntimeError(
            f"{OPERATION}: base and round-01 reviewed authorities overlap: "
            f"{sorted(base_ids & round_01_ids)}"
        )
    excluded = base_ids | round_01_ids
    if len(base_ids) != 19 or len(round_01_ids) != 26:
        raise RuntimeError(
            f"{OPERATION}: reviewed authority counts changed; "
            f"base={len(base_ids)}, round_01={len(round_01_ids)}, "
            "expected base=19 and round_01=26"
        )
    if len(excluded) != EXPECTED_REVIEWED_FACE_COUNT:
        raise RuntimeError(
            f"{OPERATION}: reviewed exclusion count is {len(excluded)}, "
            f"expected={EXPECTED_REVIEWED_FACE_COUNT}"
        )
    return {
        "base": base,
        "bridge_round_01": round_01,
        "excluded_source_face_ids": sorted(excluded),
        "excluded_source_face_count": len(excluded),
    }


def required_bridge_records(authority, excluded_face_ids):
    required_cells = set(
        authority["seed_covering_subset"]["selected_cell_ids"]
    )
    known_cells = {
        cell["name"]: cell["component"]
        for cell in authority["exposure_cells"]
    }
    unknown = required_cells - set(known_cells)
    if unknown:
        raise RuntimeError(
            f"{OPERATION}: required seed-covering cells are absent from "
            f"exposure authority: {sorted(unknown)}"
        )

    ambiguous = {
        component: set(
            authority["immutable_complements"][component][
                "ambiguous_source_face_ids"
            ]
        )
        for component in ("C9", "C20")
    }
    excluded_face_ids = set(excluded_face_ids)
    touched = defaultdict(set)
    edge_witnesses = defaultdict(list)
    for cell in authority["exposure_cells"]:
        cell_id = cell["name"]
        if cell_id not in required_cells:
            continue
        component = cell["component"]
        for edge in cell["boundary_edge_records"]:
            if "EXPOSURE_CLASS_SEAM" not in edge["barrier_reasons"]:
                continue
            for face_id in edge["complement_incident_face_ids"]:
                if face_id in excluded_face_ids:
                    continue
                if face_id not in ambiguous[component]:
                    raise RuntimeError(
                        f"{OPERATION}: source face {component}:{face_id} "
                        "touches a required exposure cell but is not current "
                        "EXTERIOR_OR_AMBIGUOUS authority"
                    )
                key = (component, int(face_id))
                touched[key].add(cell_id)
                edge_witnesses[key].append(
                    {
                        "required_cell_id": cell_id,
                        "vertex_ids": edge["vertex_ids"],
                        "selected_incident_face_ids": edge[
                            "selected_incident_face_ids"
                        ],
                    }
                )

    records = []
    for (component, face_id), cell_ids in touched.items():
        if len(cell_ids) < 2:
            continue
        witnesses = sorted(
            edge_witnesses[(component, face_id)],
            key=lambda record: (
                record["required_cell_id"],
                record["vertex_ids"],
                record["selected_incident_face_ids"],
            ),
        )
        record = {
            "component": component,
            "source_face_id": face_id,
            "required_cells_merged": len(cell_ids),
            "touched_required_cell_ids": sorted(cell_ids),
            "source_edge_witnesses": witnesses,
            "current_exposure_class": "EXTERIOR_OR_AMBIGUOUS",
        }
        record["fingerprint"] = stable_hash(record)
        records.append(record)
    return sorted(
        records,
        key=lambda record: (
            -record["required_cells_merged"],
            record["component"],
            record["source_face_id"],
        ),
    )


def text_report(report):
    lines = [
        f"# V26 ambiguous bridge-face review batch round {ROUND_INDEX:02d}",
        "",
        f"Status: `{report['status']}`",
        "",
        (
            "Ranking: descending required seed-covering cells merged, then "
            "component and source face ID."
        ),
        "",
        (
            f"Already-reviewed faces excluded: "
            f"{report['reviewed_face_exclusion']['excluded_source_face_count']}."
        ),
        "",
        "| Rank | Component | Face | Required cells merged | Touched cells |",
        "|---:|---|---:|---:|---|",
    ]
    for rank, record in enumerate(report["ordered_faces"], start=1):
        lines.append(
            f"| {rank} | {record['component']} | "
            f"{record['source_face_id']} | "
            f"{record['required_cells_merged']} | "
            f"{', '.join(record['touched_required_cell_ids'])} |"
        )
    lines.extend(
        [
            "",
            f"C9 face IDs: `{report['face_ids_by_component']['C9']}`",
            "",
            f"C20 face IDs: `{report['face_ids_by_component']['C20']}`",
            "",
            "No image, model, Blender, candidate, or mutation work performed.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    arguments = parse_arguments()
    authority_path = arguments.authority.resolve()
    authority_sha = sha_file(authority_path)
    if authority_sha != EXPECTED_AUTHORITY_SHA256:
        raise RuntimeError(
            f"{OPERATION}: exposure authority hash mismatch for "
            f"'{authority_path}'; actual={authority_sha}; "
            f"expected={EXPECTED_AUTHORITY_SHA256}"
        )
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    reviewed = reviewed_face_authority(authority)
    records = required_bridge_records(
        authority,
        reviewed["excluded_source_face_ids"],
    )
    face_ids = {
        component: sorted(
            record["source_face_id"]
            for record in records
            if record["component"] == component
        )
        for component in ("C9", "C20")
    }
    if face_ids != EXPECTED_ROUND_FACE_IDS:
        raise RuntimeError(
            f"{OPERATION}: deterministic current-round selection mismatch; "
            f"actual={face_ids}; expected={EXPECTED_ROUND_FACE_IDS}"
        )
    report = {
        "operation": OPERATION,
        "mission": MISSION,
        "status": (
            "V26_AMBIGUOUS_BRIDGE_REVIEW_BATCH_CHECKPOINTED"
            if records
            else "V26_NO_ADDITIONAL_AMBIGUOUS_BRIDGE_FACES"
        ),
        "round_index": ROUND_INDEX,
        "scope": (
            "read-only ambiguous face selection for later delegated visual "
            "classification"
        ),
        "input": {
            "path": str(authority_path),
            "sha256": authority_sha,
            "semantic_fingerprint": authority["semantic_fingerprint"],
            "source_authorities": authority["source_authorities"],
        },
        "selection_contract": {
            "candidate_class": "EXTERIOR_OR_AMBIGUOUS",
            "adjacency": "exact shared source edge",
            "minimum_distinct_required_seed_covering_cells": 2,
            "required_cell_authority": (
                "seed_covering_subset.selected_cell_ids"
            ),
            "ranking": (
                "required_cells_merged descending, component ascending, "
                "source_face_id ascending"
            ),
        },
        "required_seed_covering_cell_count": len(
            authority["seed_covering_subset"]["selected_cell_ids"]
        ),
        "reviewed_face_exclusion": reviewed,
        "batch_face_count": len(records),
        "face_ids_by_component": face_ids,
        "batch_touched_required_cell_ids": sorted(
            {
                cell_id
                for record in records
                for cell_id in record["touched_required_cell_ids"]
            }
        ),
        "ordered_faces": records,
        "safety": {
            "images_read": False,
            "images_generated": False,
            "model_or_blend_opened": False,
            "candidate_construction_started": False,
            "exposure_authority_modified": False,
            "mutation_started": False,
        },
    }
    report["semantic_fingerprint"] = stable_hash(report)
    atomic_text(
        arguments.json.resolve(),
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    atomic_text(arguments.text.resolve(), text_report(report))
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "status": report["status"],
                "batch_face_count": report["batch_face_count"],
                "face_ids_by_component": face_ids,
                "json": str(arguments.json.resolve()),
                "text": str(arguments.text.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
