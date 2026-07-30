#!/usr/bin/env python3
"""Merge the complete V27 Stage 2b local-gap evaluation authority."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


OPERATION = "MERGE_V27_LOCAL_GAP_FULL"
ROOT = Path(__file__).resolve().parents[2]
V27 = ROOT / (
    "_validation/experiments/geometry_repair/component_20_methods/"
    "repair_014_joint_c9_c20_elbow_v27"
)
OUTPUT = V27 / "v27_local_gap_full_exhaustion_authority.json"
RECEIPT = V27 / "v27_local_gap_full_exhaustion_receipt.json"
WIDTH12 = V27 / "v27_local_gap_width12_exhaustion_authority.json"
FAMILY_FINGERPRINT = (
    "6b0ee763889e4bbac7af1d638ec0f1e14b709098fcfbdcb12c910d7dc5a458a9"
)
ORDER_FINGERPRINT = (
    "260a549f826dab5990cd9507bc63a96ec46065ba81b384ac3e153758b98f5ac4"
)
MEMBERS_PER_WIDTH = 3_447_360
FULL_MEMBER_COUNT = 13_789_440
WIDTH_INTERVALS = {
    14: [3_447_360, 4_309_200, 5_171_040, 6_032_880],
    16: [6_894_720, 7_756_560, 8_618_400, 9_480_240],
    18: [10_342_080, 11_203_920, 12_065_760, 12_927_600],
}
SHARD_MEMBER_COUNT = 861_840


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
            f"{OPERATION}: cannot read authority {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeError(
            f"{OPERATION}: authority {path} is {type(value).__name__}, "
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


def shard_path(width: int, start: int, diagnostic: bool) -> Path:
    suffix = "_diag_negative" if diagnostic else ""
    return V27 / f"v27_local_gap_width{width}{suffix}_shard_{start}.json"


def validate_shard(
    path: Path, start: int, diagnostic: bool
) -> dict[str, Any]:
    shard = load_json(path)
    evaluation = shard["evaluation"]
    failures = []
    if shard["family_fingerprint"] != FAMILY_FINGERPRINT:
        failures.append("family_fingerprint")
    if shard["evaluation_order"]["fingerprint"] != ORDER_FINGERPRINT:
        failures.append("evaluation_order_fingerprint")
    if evaluation["start_member"] != start:
        failures.append("start_member")
    if evaluation["evaluated_member_count"] != SHARD_MEMBER_COUNT:
        failures.append("evaluated_member_count")
    if evaluation["selected_first_complete_pass"]:
        failures.append("unexpected_selection")
    expected_diagnostic = 100 if diagnostic else None
    if (
        evaluation.get("diagnostic_max_negative_space_hit_count")
        != expected_diagnostic
    ):
        failures.append("diagnostic_max_negative_space_hit_count")
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
    result: Counter[str] = Counter()
    for shard in shards:
        result.update(shard["evaluation"]["rejection_counts"])
    return dict(sorted(result.items()))


def best_counterexample(shards: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        shard["evaluation"]["best_immutable_counterexample"]
        for shard in shards
        if shard["evaluation"]["best_immutable_counterexample"] is not None
    ]
    return min(
        candidates,
        key=lambda record: (
            record["immutable_hit_count"],
            -sum(record["removal_counts"].values()),
            record["member_index"],
        ),
    )


def main() -> None:
    width12 = load_json(WIDTH12)
    if (
        width12["status"] != "V27_NO_VALID_LOCAL_12MM_FLEX_GAP"
        or width12["evaluated_member_count"] != MEMBERS_PER_WIDTH
        or width12["family_fingerprint"] != FAMILY_FINGERPRINT
        or width12["evaluation_order_fingerprint"] != ORDER_FINGERPRINT
    ):
        raise RuntimeError(
            f"{OPERATION}: frozen width-12 authority does not match the "
            "full-family merge contract"
        )
    primary: dict[int, list[dict[str, Any]]] = {}
    diagnostic: dict[int, list[dict[str, Any]]] = {}
    for width, starts in WIDTH_INTERVALS.items():
        primary[width] = [
            validate_shard(shard_path(width, start, False), start, False)
            for start in starts
        ]
        diagnostic[width] = [
            validate_shard(shard_path(width, start, True), start, True)
            for start in starts
        ]

    full_primary_rejections: Counter[str] = Counter(
        width12["primary_rejection_counts"]
    )
    width_summaries = {
        12: {
            "member_count": MEMBERS_PER_WIDTH,
            "rejection_counts": width12["primary_rejection_counts"],
            "selected_member_count": 0,
        }
    }
    all_primary_shards = []
    all_diagnostic_shards = []
    for width in (14, 16, 18):
        rejections = sum_rejections(primary[width])
        full_primary_rejections.update(rejections)
        width_summaries[width] = {
            "member_count": MEMBERS_PER_WIDTH,
            "rejection_counts": rejections,
            "selected_member_count": 0,
        }
        all_primary_shards.extend(primary[width])
        all_diagnostic_shards.extend(diagnostic[width])

    diagnostic_rejections = sum_rejections(all_diagnostic_shards)
    expected_primary_negative = sum(
        width_summaries[width]["rejection_counts"].get(
            "NEGATIVE_SPACE_CONFLICT", 0
        )
        for width in (14, 16, 18)
    )
    cutter_failures = diagnostic_rejections.get(
        "CUTTER_CLEARANCE_FAILED", 0
    )
    if expected_primary_negative != 20 or cutter_failures != 20:
        raise RuntimeError(
            f"{OPERATION}: central-opening survivor audit mismatch; "
            f"primary_negative={expected_primary_negative}; "
            f"diagnostic_cutter_failures={cutter_failures}"
        )
    if diagnostic_rejections.get("NEGATIVE_SPACE_CONFLICT", 0) != 0:
        raise RuntimeError(
            f"{OPERATION}: diagnostic negative-space bypass left unresolved "
            "negative-space conflicts"
        )
    first_opening = primary[14][0]["evaluation"]["first_counterexamples"][
        "NEGATIVE_SPACE_CONFLICT"
    ]
    first_clearance = diagnostic[14][0]["evaluation"][
        "first_counterexamples"
    ]["CUTTER_CLEARANCE_FAILED"]
    if (
        first_clearance["clearance"][
            "minimum_boundary_segment_to_cutter_distance_mm"
        ]
        != 0.0
    ):
        raise RuntimeError(
            f"{OPERATION}: expected exact zero-clearance merged-opening "
            "counterexample"
        )
    best = best_counterexample(all_primary_shards)
    result = {
        "operation": OPERATION,
        "mission": "R014-JOINT-C9-C20-ELBOW-V27",
        "status": "V27_NO_VALID_LOCAL_12MM_FLEX_GAP",
        "merged_opening_status": "V27_NO_VALID_CENTRAL_OPENING_MERGE",
        "code_sha256": sha_file(Path(__file__).resolve()),
        "evaluator_code_sha256": all_primary_shards[0]["code_sha256"],
        "family_fingerprint": FAMILY_FINGERPRINT,
        "evaluation_order_fingerprint": ORDER_FINGERPRINT,
        "exact_member_interval": [0, FULL_MEMBER_COUNT - 1],
        "evaluated_member_count": FULL_MEMBER_COUNT,
        "width_summaries": {
            str(width): summary
            for width, summary in sorted(width_summaries.items())
        },
        "full_rejection_counts": dict(sorted(full_primary_rejections.items())),
        "selected_member_count": 0,
        "best_immutable_counterexample": best,
        "first_zero_immutable_negative_space_counterexample": first_opening,
        "merged_central_opening_diagnostic": {
            "scope": (
                "all zero-immutable, both-component-removal members at widths "
                "14, 16, and 18 may continue through negative-space conflict "
                "to exact cutter clearance without reclassifying geometry"
            ),
            "primary_negative_space_survivor_count": 20,
            "cutter_clearance_failure_count": cutter_failures,
            "selected_member_count": 0,
            "first_clearance_counterexample": first_clearance,
            "common_minimum_clearance_mm": 0.0,
            "common_witness": {
                "component": "C9",
                "segment_index": 0,
                "cutter_triangle_index": 466,
            },
            "conclusion": (
                "merging the flex gap into the existing central opening does "
                "not restore wearer clearance under any frozen larger-width "
                "member"
            ),
        },
        "inputs": {
            "width12_authority": {
                "path": str(WIDTH12.relative_to(ROOT)),
                "sha256": sha_file(WIDTH12),
            },
            "primary_shards": [
                {
                    "path": str(
                        shard_path(width, start, False).relative_to(ROOT)
                    ),
                    "sha256": sha_file(shard_path(width, start, False)),
                    "width_mm": width,
                    "start_member": start,
                    "member_count": SHARD_MEMBER_COUNT,
                }
                for width, starts in WIDTH_INTERVALS.items()
                for start in starts
            ],
            "merged_opening_diagnostic_shards": [
                {
                    "path": str(
                        shard_path(width, start, True).relative_to(ROOT)
                    ),
                    "sha256": sha_file(shard_path(width, start, True)),
                    "width_mm": width,
                    "start_member": start,
                    "member_count": SHARD_MEMBER_COUNT,
                }
                for width, starts in WIDTH_INTERVALS.items()
                for start in starts
            ],
        },
        "invariants": {
            "complete_family_interval_has_no_gaps_or_overlaps": True,
            "all_13_789_440_members_evaluated": True,
            "all_shards_share_family_and_order_fingerprints": True,
            "all_shards_are_read_only": True,
            "no_member_selected": True,
            "all_central_opening_survivors_fail_cutter_clearance": True,
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
        "merged_opening_status": result["merged_opening_status"],
        "authority_path": str(OUTPUT),
        "authority_sha256": sha_file(OUTPUT),
        "semantic_fingerprint": result["semantic_fingerprint"],
        "evaluated_member_count": FULL_MEMBER_COUNT,
        "selected_member_count": 0,
        "primary_negative_space_survivor_count": 20,
        "merged_opening_cutter_failure_count": 20,
        "common_minimum_clearance_mm": 0.0,
        "safety": result["safety"],
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
