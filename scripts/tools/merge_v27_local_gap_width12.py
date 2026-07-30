#!/usr/bin/env python3
"""Merge and audit the sharded V27 width-12 local-gap evaluation."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


OPERATION = "MERGE_V27_LOCAL_GAP_WIDTH12"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
OUTPUT = V27 / "v27_local_gap_width12_exhaustion_authority.json"
RECEIPT = V27 / "v27_local_gap_width12_exhaustion_receipt.json"
FAMILY_FINGERPRINT = (
    "6b0ee763889e4bbac7af1d638ec0f1e14b709098fcfbdcb12c910d7dc5a458a9"
)
ORDER_FINGERPRINT = (
    "260a549f826dab5990cd9507bc63a96ec46065ba81b384ac3e153758b98f5ac4"
)
WIDTH12_MEMBER_COUNT = 3_447_360
PRIMARY_INTERVALS = [
    (0, 861_840),
    (861_840, 861_840),
    (1_723_680, 861_840),
    (2_585_520, 861_840),
]
REPEAT_INTERVALS = [(0, 500_000)] + [
    (start, 250_000)
    for start in range(500_000, 3_250_000, 250_000)
] + [(3_250_000, 197_360)]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{OPERATION}: cannot read shard {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeError(
            f"{OPERATION}: shard {path} is {type(value).__name__}, "
            "expected object"
        )
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode()
        + b"\n"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def primary_path(start: int) -> Path:
    return V27 / f"v27_local_gap_width12_shard_{start}.json"


def diagnostic_path(start: int) -> Path:
    return V27 / f"v27_local_gap_width12_diag1_shard_{start}.json"


def repeat_path(start: int) -> Path:
    if start == 0:
        return V27 / "v27_local_gap_evaluation_authority.json"
    return V27 / f"v27_local_gap_evaluation_shard_{start}.json"


def validate_shard(
    path: Path,
    start: int,
    count: int,
    diagnostic_max: int | None,
) -> dict[str, Any]:
    shard = load_json(path)
    evaluation = shard["evaluation"]
    failures = []
    if shard["family_fingerprint"] != FAMILY_FINGERPRINT:
        failures.append("family_fingerprint")
    if shard["evaluation_order"]["fingerprint"] != ORDER_FINGERPRINT:
        failures.append("evaluation_order_fingerprint")
    if evaluation.get("start_member", 0) != start:
        failures.append("start_member")
    if evaluation["evaluated_member_count"] != count:
        failures.append("evaluated_member_count")
    if evaluation["selected_first_complete_pass"]:
        failures.append("unexpected_selection")
    if evaluation.get("diagnostic_max_immutable_hit_count") != diagnostic_max:
        failures.append("diagnostic_max_immutable_hit_count")
    if not all(shard["invariants"].values()):
        failures.append("invariants")
    if any(
        shard["safety"][key]
        for key in (
            "mutation_started",
            "candidate_surface_geometry_emitted",
            "blend_saved",
            "image_work_requested",
            "gate_b_run",
            "gate_d_run",
        )
    ):
        failures.append("safety")
    if shard["safety"]["promotion"] != "NOT_PROMOTED":
        failures.append("promotion")
    if failures:
        raise RuntimeError(
            f"{OPERATION}: shard validation failed; path={path}; "
            f"failures={failures}"
        )
    return shard


def sum_rejections(shards: list[dict[str, Any]]) -> dict[str, int]:
    values: Counter[str] = Counter()
    for shard in shards:
        values.update(shard["evaluation"]["rejection_counts"])
    return dict(sorted(values.items()))


def best_counterexample(shards: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        shard["evaluation"]["best_immutable_counterexample"]
        for shard in shards
        if shard["evaluation"]["best_immutable_counterexample"] is not None
    ]
    if not candidates:
        raise RuntimeError(
            f"{OPERATION}: no immutable counterexample found in primary shards"
        )
    return min(
        candidates,
        key=lambda record: (
            record["immutable_hit_count"],
            -sum(record["removal_counts"].values()),
            record["member_index"],
        ),
    )


def main() -> None:
    primary = [
        validate_shard(primary_path(start), start, count, None)
        for start, count in PRIMARY_INTERVALS
    ]
    diagnostic = [
        validate_shard(diagnostic_path(start), start, count, 1)
        for start, count in PRIMARY_INTERVALS
    ]
    repeat = [
        validate_shard(repeat_path(start), start, count, None)
        for start, count in REPEAT_INTERVALS
    ]
    primary_rejections = sum_rejections(primary)
    repeat_rejections = sum_rejections(repeat)
    if primary_rejections != repeat_rejections:
        raise RuntimeError(
            f"{OPERATION}: repeat rejection totals differ; "
            f"primary={primary_rejections}; repeat={repeat_rejections}"
        )
    diagnostic_rejections = sum_rejections(diagnostic)
    if diagnostic_rejections.get("NEGATIVE_SPACE_CONFLICT", 0) <= 0:
        raise RuntimeError(
            f"{OPERATION}: one-face diagnostic produced no negative-space "
            "counterexamples"
        )
    if diagnostic_rejections.get("CUTTER_CLEARANCE_FAILED", 0) != 0:
        raise RuntimeError(
            f"{OPERATION}: unexpected cutter-stage diagnostic record; "
            "review downstream gate ordering"
        )
    best = best_counterexample(primary)
    result = {
        "operation": OPERATION,
        "mission": "R014-JOINT-C9-C20-ELBOW-V27",
        "status": "V27_NO_VALID_LOCAL_12MM_FLEX_GAP",
        "single_face_diagnostic_status": (
            "V27_NO_SUFFICIENT_SINGLE_IMMUTABLE_FACE_EXCEPTION"
        ),
        "code_sha256": sha_file(Path(__file__).resolve()),
        "family_fingerprint": FAMILY_FINGERPRINT,
        "evaluation_order_fingerprint": ORDER_FINGERPRINT,
        "requested_empty_chord_width_mm": 12,
        "exact_member_interval": [0, WIDTH12_MEMBER_COUNT - 1],
        "evaluated_member_count": WIDTH12_MEMBER_COUNT,
        "primary_rejection_counts": primary_rejections,
        "repeat_rejection_counts": repeat_rejections,
        "primary_repeat_identical": True,
        "best_immutable_counterexample": best,
        "single_face_diagnostic": {
            "maximum_diagnostically_allowed_immutable_hit_count": 1,
            "evaluated_member_count": WIDTH12_MEMBER_COUNT,
            "rejection_counts": diagnostic_rejections,
            "negative_space_conflict_count": diagnostic_rejections[
                "NEGATIVE_SPACE_CONFLICT"
            ],
            "terminal_conflict_count": diagnostic_rejections.get(
                "TERMINAL_CONFLICT", 0
            ),
            "cutter_clearance_failure_count": diagnostic_rejections.get(
                "CUTTER_CLEARANCE_FAILED", 0
            ),
            "selected_member_count": 0,
            "conclusion": (
                "no width-12 member becomes valid by preserving all but at "
                "most one immutable face; every primary survivor conflicts "
                "with frozen negative space before cutter clearance"
            ),
        },
        "shards": {
            "primary": [
                {
                    "path": str(primary_path(start).relative_to(ROOT)),
                    "sha256": sha_file(primary_path(start)),
                    "start_member": start,
                    "member_count": count,
                }
                for start, count in PRIMARY_INTERVALS
            ],
            "diagnostic_max_one_immutable": [
                {
                    "path": str(diagnostic_path(start).relative_to(ROOT)),
                    "sha256": sha_file(diagnostic_path(start)),
                    "start_member": start,
                    "member_count": count,
                }
                for start, count in PRIMARY_INTERVALS
            ],
            "repeat": [
                {
                    "path": str(repeat_path(start).relative_to(ROOT)),
                    "sha256": sha_file(repeat_path(start)),
                    "start_member": start,
                    "member_count": count,
                }
                for start, count in REPEAT_INTERVALS
            ],
        },
        "invariants": {
            "complete_interval_has_no_gaps_or_overlaps": True,
            "primary_and_repeat_rejection_totals_match": True,
            "all_shards_share_family_and_order_fingerprints": True,
            "all_shards_are_read_only": True,
            "no_member_reached_terminal_or_cutter_gate": (
                primary_rejections.get("TERMINAL_CONFLICT", 0) == 0
                and primary_rejections.get("CUTTER_CLEARANCE_FAILED", 0) == 0
            ),
            "single_face_exception_is_insufficient": True,
        },
        "safety": {
            "mutation_started": False,
            "candidate_surface_geometry_emitted": False,
            "blend_saved": False,
            "image_work_requested": False,
            "promotion": "NOT_PROMOTED",
            "gate_b_run": False,
            "gate_d_run": False,
        },
    }
    result["semantic_fingerprint"] = stable_hash(result)
    atomic_json(OUTPUT, result)
    receipt = {
        "operation": OPERATION,
        "status": result["status"],
        "single_face_diagnostic_status": result[
            "single_face_diagnostic_status"
        ],
        "authority_path": str(OUTPUT),
        "authority_sha256": sha_file(OUTPUT),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "evaluated_member_count": WIDTH12_MEMBER_COUNT,
        "best_immutable_hit_count": best["immutable_hit_count"],
        "best_immutable_source_face_ids": best[
            "immutable_source_face_ids"
        ],
        "single_face_negative_space_conflict_count": result[
            "single_face_diagnostic"
        ]["negative_space_conflict_count"],
        "safety": result["safety"],
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
