#!/usr/bin/env python3
"""Validate binary STL exports without third-party dependencies."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import struct
import sys


BED_LIMIT_MM = 180.0
STL_HEADER_BYTES = 84
STL_TRIANGLE_BYTES = 50
ZERO_AREA_EPSILON = 1e-10


Vertex = tuple[float, float, float]
Edge = tuple[Vertex, Vertex]


@dataclass
class Audit:
    file: str
    bytes: int
    triangles: int = 0
    dimensions_mm: tuple[float, float, float] | None = None
    connected_components: int = 0
    nonmanifold_edges: int = 0
    degenerate_triangles: int = 0
    signed_volume_mm3: float = 0.0
    issues: list[str] | None = None

    @property
    def passed(self) -> bool:
        return not self.issues


def canonical_edge(a: Vertex, b: Vertex) -> Edge:
    return (a, b) if a <= b else (b, a)


def triangle_area(a: Vertex, b: Vertex, c: Vertex) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * math.sqrt(sum(value * value for value in cross))


def connected_component_count(adjacency: dict[Vertex, set[Vertex]]) -> int:
    unseen = set(adjacency)
    count = 0
    while unseen:
        count += 1
        queue = deque([unseen.pop()])
        while queue:
            vertex = queue.popleft()
            for neighbor in adjacency[vertex]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return count


def audit_stl(
    path: Path,
    display_path: str,
    *,
    allow_overlapping_shells: bool = False,
    allow_bed_oversize: bool = False,
) -> Audit:
    data = path.read_bytes()
    audit = Audit(file=display_path, bytes=len(data), issues=[])

    if len(data) < STL_HEADER_BYTES:
        audit.issues.append(
            f"INVALID_STL: file has {len(data)} bytes; binary STL needs at least "
            f"{STL_HEADER_BYTES}"
        )
        return audit

    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_bytes = STL_HEADER_BYTES + triangle_count * STL_TRIANGLE_BYTES
    if len(data) != expected_bytes:
        audit.issues.append(
            "INVALID_STL: binary size check failed "
            f"(header triangles={triangle_count}, expected bytes={expected_bytes}, "
            f"actual bytes={len(data)}). Export as binary STL."
        )
        return audit

    audit.triangles = triangle_count
    edge_counts: Counter[Edge] = Counter()
    adjacency: dict[Vertex, set[Vertex]] = defaultdict(set)
    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    signed_volume_mm3 = 0.0

    for index in range(triangle_count):
        offset = STL_HEADER_BYTES + index * STL_TRIANGLE_BYTES
        values = struct.unpack_from("<12fH", data, offset)
        vertices: tuple[Vertex, Vertex, Vertex] = (
            tuple(values[3:6]),
            tuple(values[6:9]),
            tuple(values[9:12]),
        )

        for vertex in vertices:
            for axis in range(3):
                minimum[axis] = min(minimum[axis], vertex[axis])
                maximum[axis] = max(maximum[axis], vertex[axis])

        if triangle_area(*vertices) <= ZERO_AREA_EPSILON:
            audit.degenerate_triangles += 1

        a, b, c = vertices
        cross_bc = (
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        )
        signed_volume_mm3 += (
            a[0] * cross_bc[0]
            + a[1] * cross_bc[1]
            + a[2] * cross_bc[2]
        ) / 6.0

        for start, end in ((0, 1), (1, 2), (2, 0)):
            a, b = vertices[start], vertices[end]
            edge_counts[canonical_edge(a, b)] += 1
            adjacency[a].add(b)
            adjacency[b].add(a)

    audit.dimensions_mm = tuple(
        round(maximum[axis] - minimum[axis], 3) for axis in range(3)
    )
    audit.connected_components = connected_component_count(adjacency)
    audit.nonmanifold_edges = sum(count != 2 for count in edge_counts.values())
    audit.signed_volume_mm3 = round(signed_volume_mm3, 6)

    oversized = [
        f"{axis}={dimension:.3f} mm"
        for axis, dimension in zip("XYZ", audit.dimensions_mm)
        if dimension > BED_LIMIT_MM
    ]
    if oversized and not allow_bed_oversize:
        audit.issues.append(
            f"BED_OVERSIZE: {', '.join(oversized)} exceeds {BED_LIMIT_MM:.1f} mm"
        )
    if audit.connected_components != 1 and not allow_overlapping_shells:
        audit.issues.append(
            "DISCONNECTED_GEOMETRY: "
            f"found {audit.connected_components} components; expected exactly 1"
        )
    if audit.nonmanifold_edges:
        audit.issues.append(
            "NONMANIFOLD_GEOMETRY: "
            f"found {audit.nonmanifold_edges} edges with incidence other than 2"
        )
    if audit.degenerate_triangles:
        audit.issues.append(
            "DEGENERATE_GEOMETRY: "
            f"found {audit.degenerate_triangles} zero-area triangles"
        )
    if audit.signed_volume_mm3 <= 0.0:
        audit.issues.append(
            "NON_POSITIVE_VOLUME: "
            f"signed volume is {audit.signed_volume_mm3:.6f} mm³; "
            "repair shell orientation before export"
        )

    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit binary STL topology and A1 mini bed dimensions."
    )
    parser.add_argument(
        "export_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "exports" / "current",
        help=(
            "directory containing explicit current STL exports "
            "(default: repository exports/current/)"
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        help="also write the full report as JSON",
    )
    parser.add_argument(
        "--allow-overlapping-shells",
        action="store_true",
        help=(
            "allow multiple closed STL components when intentional overlap and "
            "slicer union are validated separately; manifold, degenerate, "
            "and bed checks remain mandatory"
        ),
    )
    parser.add_argument(
        "--allow-bed-oversize",
        action="store_true",
        help=(
            "allow dimensions over the A1 mini bed only for explicitly "
            "unsegmented evidence; all topology checks remain mandatory"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.export_root.resolve()
    if not root.is_dir():
        print(
            f"ERROR: cannot audit export root '{root}': directory does not exist",
            file=sys.stderr,
        )
        return 2

    paths = sorted(root.rglob("*.stl"))
    if not paths:
        print(f"ERROR: no .stl files found under '{root}'", file=sys.stderr)
        return 2

    audits: list[Audit] = []
    for path in paths:
        display_path = str(path.relative_to(root))
        try:
            audit = audit_stl(
                path,
                display_path,
                allow_overlapping_shells=args.allow_overlapping_shells,
                allow_bed_oversize=args.allow_bed_oversize,
            )
        except OSError as exc:
            audit = Audit(
                file=display_path,
                bytes=0,
                issues=[f"READ_FAILED: {exc}"],
            )
        audits.append(audit)

        dimensions = (
            "×".join(f"{value:.1f}" for value in audit.dimensions_mm) + " mm"
            if audit.dimensions_mm
            else "unknown dimensions"
        )
        state = "PASS" if audit.passed else "FAIL"
        print(
            f"{state:4} {audit.file}: {dimensions}; "
            f"triangles={audit.triangles}; components={audit.connected_components}; "
            f"nonmanifold_edges={audit.nonmanifold_edges}; "
            f"degenerate_triangles={audit.degenerate_triangles}; "
            f"signed_volume={audit.signed_volume_mm3:.3f} mm³"
        )
        for issue in audit.issues or []:
            print(f"     {issue}")

    report = {
        "export_root": str(root),
        "bed_limit_mm": BED_LIMIT_MM,
        "allow_overlapping_shells": args.allow_overlapping_shells,
        "allow_bed_oversize": args.allow_bed_oversize,
        "files": [asdict(audit) | {"passed": audit.passed} for audit in audits],
        "summary": {
            "files": len(audits),
            "passed": sum(audit.passed for audit in audits),
            "failed": sum(not audit.passed for audit in audits),
        },
    }

    if args.json_path:
        json_path = args.json_path.resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON report: {json_path}")

    failed = report["summary"]["failed"]
    print(
        f"Validation result: {report['summary']['passed']} passed, "
        f"{failed} failed, {len(audits)} total"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
