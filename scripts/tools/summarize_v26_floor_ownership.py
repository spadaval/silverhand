#!/usr/bin/env python3
"""Write a compact, hash-bound summary of V26 floor ownership authority."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys


OPERATION = "SUMMARIZE_V26_FLOOR_OWNERSHIP"
EXPECTED_AUTHORITY_SHA256 = (
    "02b758bddee0be121c9c1e93cef13b781b4e8241bda862ec6c8d389aaf653ab9"
)
EXPECTED_SEMANTIC_FINGERPRINT = (
    "18efafe3169ca3f0f5db613bfe63069da9d6475cc8041820d1175d25f0faa79d"
)
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTHORITY = (
    ROOT
    / "_validation/experiments/geometry_repair/component_20_methods"
    / "repair_014_joint_c9_c20_elbow_v26"
    / "v26_floor_ownership_authority.json"
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authority",
        type=Path,
        default=DEFAULT_AUTHORITY,
        help="validated full V26 floor-ownership authority",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "summary output; defaults to v26_floor_ownership_summary.json "
            "beside the authority"
        ),
    )
    return parser.parse_args()


def sha_file(path):
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def compact_sample(sample):
    intersections = [
        {
            "source_face_id": record.get("source_face_id"),
            "component": record.get("component"),
            "cell_id": record.get("cell_id"),
            "distance_mm": record.get("distance_mm"),
            "topology_distance_to_retained_boundary": record.get(
                "topology_distance_to_retained_boundary"
            ),
        }
        for _, record in sorted(
            sample.get("intersections", {}).items()
        )
    ]
    exterior = sample.get("exterior", {})
    return {
        "lattice_index": sample.get("lattice_index"),
        "station_mm": sample.get("station_mm"),
        "angle_radians": sample.get("angle_radians"),
        "declared_owner": sample.get("declared_owner"),
        "owner_reason": sample.get("owner_reason"),
        "inside_numeric_flex_gap": sample.get("inside_numeric_flex_gap"),
        "atomic_intersections": intersections,
        "first_retained_exterior_intersection": {
            "source_face_id": exterior.get("source_face_id"),
            "distance_mm": exterior.get("distance_mm"),
        },
        "ordered_cutter_floor_exterior_valid": sample.get(
            "ordered_cutter_floor_exterior_valid"
        ),
    }


def conflict_record(records):
    if not records:
        return {"count": 0, "first": None, "last": None}
    return {
        "count": len(records),
        "first": records[0],
        "last": records[-1],
    }


def summarize_stream(authority):
    jq = shutil.which("jq")
    if jq is None:
        raise RuntimeError(
            f"{OPERATION}: required streaming parser 'jq' was not found; "
            "install jq and rerun the exact authority path"
        )
    process = subprocess.Popen(
        [jq, "--compact-output", "--stream", ".", str(authority)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if process.stdout is None or process.stderr is None:
        raise RuntimeError(
            f"{OPERATION}: failed to open jq streams for '{authority}'"
        )

    top = {}
    evidence = {}
    contract = {}
    flags = {}
    failure_classes = []
    exact_cell_ids = []
    exposure = defaultdict(
        lambda: {
            "component": None,
            "face_count": 0,
            "sample_count": 0,
            "wearer_facing_face_count": 0,
            "ambiguous_face_count": 0,
        }
    )
    owner_counts = Counter()
    cell_intersection_samples = Counter()
    cell_first_owned_floor_samples = Counter()
    sample_witnesses = {}
    layer_inversions = []
    duplicate_records = {}
    no_floor_indices = []
    gap_records = {}
    ownership_summary = {}
    seam = {}
    flex_gap = {}
    semantic_fingerprint = None
    source_face_ownership_is_unique = None
    current_sample_index = None
    current_sample = {}

    def finish_sample():
        nonlocal current_sample_index, current_sample
        if current_sample_index is None:
            return
        witness = compact_sample(current_sample)
        lattice_index = witness["lattice_index"]
        sample_witnesses[lattice_index] = witness
        owner = witness["declared_owner"]
        owner_counts[str(owner) if owner is not None else "NO_FLOOR"] += 1
        intersected_cells = {
            record["cell_id"]
            for record in witness["atomic_intersections"]
            if record["cell_id"] is not None
        }
        for cell_id in intersected_cells:
            cell_intersection_samples[cell_id] += 1
        if owner in {"C9", "C20"}:
            first_owned = next(
                (
                    record
                    for record in witness["atomic_intersections"]
                    if record["component"] == owner
                ),
                None,
            )
            if first_owned is not None:
                cell_first_owned_floor_samples[first_owned["cell_id"]] += 1
        if witness["ordered_cutter_floor_exterior_valid"] is False:
            layer_inversions.append(witness)
        current_sample_index = None
        current_sample = {}

    for line in process.stdout:
        event = json.loads(line)
        if len(event) != 2:
            continue
        path, value = event
        if not path:
            continue
        first = path[0]
        if first in {"operation", "status", "scope"} and len(path) == 1:
            top[first] = value
        elif first == "semantic_fingerprint" and len(path) == 1:
            semantic_fingerprint = value
        elif first == "source_face_ownership_is_unique" and len(path) == 1:
            source_face_ownership_is_unique = value
        elif first == "evidence" and len(path) == 2:
            evidence[path[1]] = value
        elif first == "contract" and len(path) == 2:
            contract[path[1]] = value
        elif first in {
            "candidate_construction_started",
            "mutation_started",
            "geometry_emitted",
            "blend_saved",
            "image_work_requested",
            "promotion",
        } and len(path) == 1:
            flags[first] = value
        elif first == "failure_classes" and len(path) == 2:
            failure_classes.append(value)
        elif first == "exact_atomic_cell_ids" and len(path) == 2:
            exact_cell_ids.append(value)
        elif first == "exposure" and len(path) >= 3:
            cell_id = path[1]
            if path[2] == "component" and len(path) == 3:
                exposure[cell_id]["component"] = value
            elif path[2] == "face_count" and len(path) == 3:
                exposure[cell_id]["face_count"] = value
            elif (
                path[2] == "wearer_facing_face_ids"
                and len(path) == 4
            ):
                exposure[cell_id]["wearer_facing_face_count"] += 1
            elif path[2] == "ambiguous_face_ids" and len(path) == 4:
                exposure[cell_id]["ambiguous_face_count"] += 1
            elif (
                path[2] == "faces"
                and len(path) == 5
                and path[4] == "sample_count"
            ):
                exposure[cell_id]["sample_count"] += value
        elif first == "ownership" and len(path) >= 2:
            section = path[1]
            if section == "sample_count" and len(path) == 2:
                ownership_summary["sample_count"] = value
            elif section == "samples" and len(path) >= 4:
                sample_index = path[2]
                if sample_index != current_sample_index:
                    finish_sample()
                    current_sample_index = sample_index
                    current_sample = {"intersections": {}, "exterior": {}}
                field = path[3]
                if field == "ordered_atomic_intersections" and len(path) >= 6:
                    intersection = current_sample["intersections"].setdefault(
                        path[4], {}
                    )
                    if len(path) == 6:
                        intersection[path[5]] = value
                elif (
                    field == "first_retained_exterior_intersection"
                    and len(path) == 5
                ):
                    current_sample["exterior"][path[4]] = value
                elif len(path) == 4:
                    current_sample[field] = value
            elif section == "duplicate_c9_c20_floor_pairs" and len(path) == 4:
                duplicate = duplicate_records.setdefault(path[2], {})
                duplicate[path[3]] = value
            elif section == "non_gap_no_floor_lattice_indices" and len(path) == 3:
                no_floor_indices.append(value)
            elif section == "gap_source_floors_requiring_removal" and len(path) >= 4:
                record = gap_records.setdefault(
                    path[2], {"face_ids": []}
                )
                if path[3] == "face_ids" and len(path) == 5:
                    record["face_ids"].append(value)
                elif len(path) == 4:
                    record[path[3]] = value
            elif section == "ownership_seam" and len(path) == 3:
                seam[path[2]] = value
            elif section == "flex_gap" and len(path) == 3:
                flex_gap[path[2]] = value
    finish_sample()
    stderr = process.stderr.read()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(
            f"{OPERATION}: jq streaming parse failed for '{authority}' "
            f"with exit {return_code}: {stderr.strip()}"
        )

    duplicates = [
        duplicate_records[index] for index in sorted(duplicate_records)
    ]
    gap_conflicts = [gap_records[index] for index in sorted(gap_records)]
    no_floor_witnesses = [
        sample_witnesses[index]
        for index in no_floor_indices
        if index in sample_witnesses
    ]
    exposure_result = {}
    for cell_id in exact_cell_ids:
        record = dict(exposure[cell_id])
        record["ownership_intersection_sample_count"] = (
            cell_intersection_samples[cell_id]
        )
        record["first_owned_floor_sample_count"] = (
            cell_first_owned_floor_samples[cell_id]
        )
        exposure_result[cell_id] = record
    return {
        "source": {
            **top,
            "evidence": evidence,
            "semantic_fingerprint": semantic_fingerprint,
        },
        "contract": contract,
        "exact_atomic_cell_ids": exact_cell_ids,
        "failure_classes": failure_classes,
        "exposure": {
            "face_count": sum(
                record["face_count"] for record in exposure_result.values()
            ),
            "sample_count": sum(
                record["sample_count"] for record in exposure_result.values()
            ),
            "wearer_facing_face_count": sum(
                record["wearer_facing_face_count"]
                for record in exposure_result.values()
            ),
            "ambiguous_face_count": sum(
                record["ambiguous_face_count"]
                for record in exposure_result.values()
            ),
            "by_atomic_cell": exposure_result,
        },
        "ownership": {
            "sample_count": ownership_summary.get("sample_count"),
            "declared_owner_counts": dict(sorted(owner_counts.items())),
            "duplicate_c9_c20_floor_pairs": conflict_record(duplicates),
            "non_gap_zero_floor": conflict_record(no_floor_witnesses),
            "source_floor_inside_required_flex_gap": conflict_record(
                gap_conflicts
            ),
            "cutter_floor_exterior_layer_inversions": conflict_record(
                layer_inversions
            ),
            "ownership_seam": seam,
            "flex_gap": {
                "minimum_width_mm": flex_gap.get("minimum_width_mm"),
                "projected_boundary_separation_mm": flex_gap.get(
                    "projected_boundary_separation_mm"
                ),
                "upper_station_mm": flex_gap.get("upper_station_mm"),
                "lower_station_mm": flex_gap.get("lower_station_mm"),
            },
        },
        "source_face_ownership_is_unique": source_face_ownership_is_unique,
        "safety": flags,
    }


def validate_summary(summary):
    expected = {
        "exposure_face_count": 962,
        "exposure_sample_count": 303274,
        "wearer_facing_face_count": 236,
        "ambiguous_face_count": 726,
        "ownership_sample_count": 16486,
        "duplicate_pair_count": 0,
        "non_gap_zero_floor_count": 12523,
        "gap_source_floor_count": 91,
        "layer_inversion_count": 7,
    }
    actual = {
        "exposure_face_count": summary["exposure"]["face_count"],
        "exposure_sample_count": summary["exposure"]["sample_count"],
        "wearer_facing_face_count": summary["exposure"][
            "wearer_facing_face_count"
        ],
        "ambiguous_face_count": summary["exposure"]["ambiguous_face_count"],
        "ownership_sample_count": summary["ownership"]["sample_count"],
        "duplicate_pair_count": summary["ownership"][
            "duplicate_c9_c20_floor_pairs"
        ]["count"],
        "non_gap_zero_floor_count": summary["ownership"][
            "non_gap_zero_floor"
        ]["count"],
        "gap_source_floor_count": summary["ownership"][
            "source_floor_inside_required_flex_gap"
        ]["count"],
        "layer_inversion_count": summary["ownership"][
            "cutter_floor_exterior_layer_inversions"
        ]["count"],
    }
    if actual != expected:
        raise RuntimeError(
            f"{OPERATION}: compact count validation failed; "
            f"actual={actual}; expected={expected}"
        )
    expected_failures = [
        "NON_GAP_ZERO_FLOOR",
        "SOURCE_FLOOR_INSIDE_REQUIRED_FLEX_GAP",
        "CUTTER_FLOOR_EXTERIOR_LAYER_ORDER_INVERTED",
    ]
    if summary["failure_classes"] != expected_failures:
        raise RuntimeError(
            f"{OPERATION}: failure classes changed; "
            f"actual={summary['failure_classes']}; "
            f"expected={expected_failures}"
        )


def main():
    args = parse_args()
    authority = args.authority.resolve()
    output = (
        args.output.resolve()
        if args.output
        else authority.with_name("v26_floor_ownership_summary.json")
    )
    if not authority.is_file():
        raise RuntimeError(
            f"{OPERATION}: full authority '{authority}' is not a file"
        )
    authority_sha = sha_file(authority)
    if authority_sha != EXPECTED_AUTHORITY_SHA256:
        raise RuntimeError(
            f"{OPERATION}: full authority hash mismatch for '{authority}'; "
            f"actual={authority_sha}; expected={EXPECTED_AUTHORITY_SHA256}"
        )
    summary = summarize_stream(authority)
    if (
        summary["source"]["semantic_fingerprint"]
        != EXPECTED_SEMANTIC_FINGERPRINT
    ):
        raise RuntimeError(
            f"{OPERATION}: semantic fingerprint mismatch for '{authority}'; "
            f"actual={summary['source']['semantic_fingerprint']}; "
            f"expected={EXPECTED_SEMANTIC_FINGERPRINT}"
        )
    summary = {
        "operation": OPERATION,
        "status": "V26_FLOOR_OWNERSHIP_COMPACT_SUMMARY_COMPLETE",
        "full_authority": {
            "path": str(authority),
            "size_bytes": authority.stat().st_size,
            "sha256": authority_sha,
            "semantic_fingerprint": EXPECTED_SEMANTIC_FINGERPRINT,
            "unchanged": True,
        },
        **summary,
    }
    validate_summary(summary)
    atomic_json(output, summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "output": str(output),
                "output_sha256": sha_file(output),
                "full_authority_sha256": authority_sha,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"{OPERATION}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
