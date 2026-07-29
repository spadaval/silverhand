#!/usr/bin/env python3
"""Merge completed V25 capsule-route shards into the final read-only stop."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys


OPERATION = "AUTHORED_TAIL_RECONSTRUCTION_PREFLIGHT_V25"
FINAL_STATUS = "NO_SAFE_AUTHORED_TAIL_ROUTE_V25"


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


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: merge_v25_route_shards.py V25_VALIDATION_DIRECTORY"
        )
    directory = Path(sys.argv[1]).resolve()
    authority_path = directory / "combined_tail_authority.json"
    contract_path = directory / "v25_search_contract.json"
    progress_path = directory / "v25_progress.json"
    portal_path = directory / "v25_portal_dedup.json"
    shard_contract_path = directory / "v25_route_shard_contract.json"
    capsule_validation_path = (
        directory / "v25_capsule_prefilter_validation.json"
    )
    equivalence_path = directory / "v25_cached_astar_equivalence.json"
    required = (
        authority_path,
        contract_path,
        progress_path,
        portal_path,
        shard_contract_path,
        capsule_validation_path,
        equivalence_path,
    )
    for path in required:
        if not path.exists():
            raise RuntimeError(
                f"{OPERATION}: merge missing required checkpoint: {path}"
            )
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    portals = json.loads(portal_path.read_text(encoding="utf-8"))
    shard_contract = json.loads(
        shard_contract_path.read_text(encoding="utf-8")
    )
    capsule_validation = json.loads(
        capsule_validation_path.read_text(encoding="utf-8")
    )
    equivalence = json.loads(
        equivalence_path.read_text(encoding="utf-8")
    )
    if contract["authority_sha256"] != sha_file(authority_path):
        raise RuntimeError(
            f"{OPERATION}: contract/authority hash mismatch"
        )
    if not capsule_validation["all_cases_pass"]:
        raise RuntimeError(
            f"{OPERATION}: capsule necessity validation is not passing"
        )
    if not equivalence["all_cases_match"]:
        raise RuntimeError(
            f"{OPERATION}: cached A* equivalence checkpoint is not passing"
        )
    if len(progress["completed_tuple_ids"]) != 11907:
        raise RuntimeError(
            f"{OPERATION}: escape ledger incomplete: "
            f"{len(progress['completed_tuple_ids'])}/11907"
        )
    if len(progress["accepted_escape_ids"]) != 3570:
        raise RuntimeError(
            f"{OPERATION}: accepted escape count changed: "
            f"{len(progress['accepted_escape_ids'])}"
        )
    if portals["unique_portal_count"] != 1190:
        raise RuntimeError(
            f"{OPERATION}: unique portal count changed: "
            f"{portals['unique_portal_count']}"
        )
    shard_records = []
    completed_route_ids = []
    capsule_path_ids = []
    for shard in range(3):
        path = directory / f"v25_capsule_route_shard_{shard}_of_3.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["status"] != "CAPSULE_ROUTE_SHARD_COMPLETE":
            raise RuntimeError(
                f"{OPERATION}: capsule shard {shard}/3 incomplete: "
                f"{record['status']}"
            )
        expected_ids = {
            f"{portal_id}:{endpoint_id}"
            for portal_id in shard_contract["shards"][str(shard)]
            for endpoint_id in ("E0", "E1", "E2")
        }
        observed_ids = set(record["completed_route_ids"])
        if observed_ids != expected_ids:
            raise RuntimeError(
                f"{OPERATION}: capsule shard {shard}/3 route-ID mismatch; "
                f"missing={len(expected_ids - observed_ids)}, "
                f"extra={len(observed_ids - expected_ids)}"
            )
        if record["capsule_path_route_ids"]:
            capsule_path_ids.extend(record["capsule_path_route_ids"])
        completed_route_ids.extend(record["completed_route_ids"])
        shard_records.append(
            {
                "shard": shard,
                "path": str(path),
                "sha256": sha_file(path),
                "completed_route_count": len(record["completed_route_ids"]),
                "capsule_path_count": len(
                    record["capsule_path_route_ids"]
                ),
                "rejection_counts": record["rejection_counts"],
            }
        )
    if len(completed_route_ids) != 3570:
        raise RuntimeError(
            f"{OPERATION}: merged capsule route count is "
            f"{len(completed_route_ids)}, expected 3570"
        )
    if len(set(completed_route_ids)) != 3570:
        raise RuntimeError(
            f"{OPERATION}: merged capsule route IDs are not unique"
        )
    if capsule_path_ids:
        raise RuntimeError(
            f"{OPERATION}: {len(capsule_path_ids)} routes remain full-roll "
            f"pending; cannot issue {FINAL_STATUS}"
        )
    merge_path = directory / "v25_capsule_route_merge.json"
    merge = {
        "operation": OPERATION,
        "status": "CAPSULE_ROUTE_SHARDS_MERGED",
        "authority_sha256": sha_file(authority_path),
        "contract_sha256": sha_file(contract_path),
        "portal_dedup_sha256": sha_file(portal_path),
        "shard_contract_sha256": sha_file(shard_contract_path),
        "capsule_validation_sha256": sha_file(capsule_validation_path),
        "cached_astar_equivalence_sha256": sha_file(equivalence_path),
        "completed_route_count": len(completed_route_ids),
        "unique_completed_route_count": len(set(completed_route_ids)),
        "capsule_path_count": 0,
        "shards": shard_records,
        "result": "every route is inscribed_capsule_no_path",
        "full_roll_search_required_count": 0,
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    atomic_json(merge_path, merge)
    route_path = directory / "v25_route_preflight.json"
    route = {
        "operation": OPERATION,
        "status": FINAL_STATUS,
        "authorities": {
            "input_blend_sha256": authority["input_blend_sha256"],
            "combined_tail_authority_sha256": sha_file(authority_path),
            "search_contract_sha256": sha_file(contract_path),
            "portal_dedup_sha256": sha_file(portal_path),
        },
        "candidate_counts": {
            "fixed_tuple_count": 11907,
            "locally_passing_escape_count": 3570,
            "unique_portal_count": 1190,
            "endpoint_route_count": 3570,
            "inscribed_capsule_no_path_count": 3570,
            "capsule_path_count": 0,
            "full_roll_search_required_count": 0,
            "complete_route_channel_pair_count": 0,
        },
        "escape_rejection_counts": progress[
            "rejection_counts_by_exact_obstacle"
        ],
        "capsule_route_merge": str(merge_path),
        "capsule_route_merge_sha256": sha_file(merge_path),
        "selected_complete_pair": None,
        "hard_stop": {
            "operation": "fixed_A0_authored_tail_search",
            "target": "A0_R18_to_T0_E0_E1_E2",
            "actionable_reason": (
                "Every one of the 3,570 endpoint routes is disconnected even "
                "for the radius-1.2mm inscribed capsule on the unchanged 4mm "
                "lattice. A passing 4.5–6.0 x 2.4mm rectangular rail would "
                "necessarily contain that capsule, so no V23 roll evolution "
                "can recover a route inside the fixed V25 bounds. Expansion "
                "into B1 or beyond 12mm of B2a is a new decision."
            ),
        },
        "mutation_started": False,
        "geometry_emitted": False,
        "blend_saved": False,
    }
    atomic_json(route_path, route)
    allowlist_path = directory / "v25_joint_allowlist_preflight.json"
    allowlist = {
        "operation": OPERATION,
        "status": FINAL_STATUS,
        "authored_C20_replacement_scope": None,
        "C20_T0_mask": [2741, 4711],
        "C9_base_mask": [],
        "C9_transition_ring": [],
        "visible_C20_island": None,
        "immutable_complement_fingerprints": {
            "B0": authority["fingerprints"]["B0"],
            "B1": authority["fingerprints"]["B1"],
            "B2a_prefix_A0": authority["fingerprints"]["B2a_prefixes"][
                "A0"
            ],
            "source_cage": authority["fingerprints"]["source_cage"],
            "C9": authority["fingerprints"]["C9"],
            "Branch_A": authority["fingerprints"]["Branch_A"],
            "central_opening": authority["fingerprints"][
                "central_opening_keep_out"
            ],
        },
        "mutation_authority": False,
    }
    atomic_json(allowlist_path, allowlist)
    report_path = directory / "build_report.json"
    report = {
        "tool": "preflight_authored_tail_v25.py",
        "merge_tool": Path(__file__).name,
        "operation": OPERATION,
        "status": FINAL_STATUS,
        "input_blend": authority["input_blend"],
        "input_blend_sha256": authority["input_blend_sha256"],
        "combined_tail_authority": str(authority_path),
        "combined_tail_authority_sha256": sha_file(authority_path),
        "v25_search_contract": str(contract_path),
        "v25_search_contract_sha256": sha_file(contract_path),
        "v25_progress": str(progress_path),
        "v25_progress_sha256": sha_file(progress_path),
        "v25_portal_dedup": str(portal_path),
        "v25_portal_dedup_sha256": sha_file(portal_path),
        "v25_capsule_route_merge": str(merge_path),
        "v25_capsule_route_merge_sha256": sha_file(merge_path),
        "v25_route_preflight": str(route_path),
        "v25_route_preflight_sha256": sha_file(route_path),
        "v25_joint_allowlist_preflight": str(allowlist_path),
        "v25_joint_allowlist_preflight_sha256": sha_file(allowlist_path),
        "candidate_counts": route["candidate_counts"],
        "rejection_counts": {
            **progress["rejection_counts_by_exact_obstacle"],
            "inscribed_capsule_no_path": 3570,
        },
        "selected_result": None,
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
        f"DONE: V25 route shards merged; status={FINAL_STATUS}; "
        "completed=3570/3570; mutation_started=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
