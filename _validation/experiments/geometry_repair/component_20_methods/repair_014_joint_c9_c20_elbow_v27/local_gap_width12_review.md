# V27 local-gap minimum-width review

Status: `PASS_V27_LOCAL_GAP_WIDTH12_EXHAUSTION_AUDIT`

## Result

The complete requested-width-`12 mm` Stage 2b slice contains `3,447,360`
members. Two disjoint sharding layouts evaluate the exact interval
`[0, 3,447,359]` with no gaps or overlaps and produce identical rejection
totals. No member reaches all acceptance gates.

The truthful result is `V27_NO_VALID_LOCAL_12MM_FLEX_GAP`.

## Best primary counterexample

- member: `687056`
- pair: `LOCAL_GAP_PAIR_000215`
- width: `12 mm`
- orientation: `10°`
- C20/C9 signed depth: `4 / -2 mm`
- allocation: `0.5`
- minimum measured chord: `28.559136961565805 mm`
- authorized removals: six C20 faces and one C9 face
- immutable intersections: face `2227` only

This does not authorize face `2227` for removal.

## Single-face diagnostic

The complete width-12 family was evaluated again with a diagnostic rule that
allowed members with at most one immutable hit to continue to later checks.
The immutable classification itself remained frozen.

- downstream negative-space conflicts: `145`
- selected members: `0`
- terminal conflicts reached: `0`
- cutter-clearance failures reached: `0`

Every primary survivor violates exact source-open-route or central-opening
negative space. Therefore
`V27_NO_SUFFICIENT_SINGLE_IMMUTABLE_FACE_EXCEPTION` is supported: sacrificing
or relabeling one extra face cannot make a width-12 member valid.

## Safety

- source/model mutation: false
- candidate geometry emitted: false
- Blend saved: false
- image work: false
- Gate B/D execution: false
- promotion: `NOT_PROMOTED`

## Scope

This audit closes only the width-12 axis. Widths 14, 16, and 18 mm remain
unevaluated members of the frozen Stage 2b family. Stage 3 construction remains
unauthorized.
