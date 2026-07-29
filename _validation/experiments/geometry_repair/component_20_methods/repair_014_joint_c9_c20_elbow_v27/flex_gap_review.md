# V27 fixed-frame flex-gap independent review

Status: `PASS_V27_FIXED_FRAME_FLEX_GAP_EXHAUSTION_AUDIT`

Review role: Agent Factory `review`

Reviewed commit: `e8452963e8909e2a73b664c8d4d0dd6e575374ae`

## Scope

This is a read-only proof review of the committed translation family for the
frozen `FLEX_GAP_MINIMUM_CORE`: exact `12.0 mm` chordwise width, frozen
orientation and transverse/depth envelope, translation only along the recorded
chord axis, and the frozen 26-cell aggregate/immutable contract.

This audit does **not** claim that every possible gap frame, orientation,
aggregate mask, immutable-face classification, or elbow-joint architecture has
been searched.

## Findings

- Low: `scripts/blender/solve_v27_flex_gap.py:876` records the frequency of
  only each placement's first sorted immutable witness face, while
  `checkpoint.md:781` calls the values the “most recurring exact witness
  faces.” The values are repeatable diagnostics, but they are not the
  occurrence frequency of every intersecting immutable face. Rename the
  checkpoint label to “first-witness frequency” if this ranking is reused.
  This does not affect the rejection count, best counterexample, or hard stop.

No blocking proof, safety, or authority issue was found.

## Fixed-frame completeness

Initial inspection identified a possible general event-enumeration weakness:
clipping a triangle against a fixed transverse/depth envelope can create new
edge/plane intersection vertices whose chord stations are not raw source
vertex stations. A separate background-Blender interval audit resolved that
concern for this exact frozen frame:

- immutable complement: `696` faces / `729` fan triangles;
- selected aggregate: `266` faces;
- fixed non-chord half-spaces: `4`;
- immutable vertex occurrences outside the transverse/depth envelope: `0`;
- selected vertex occurrences outside the transverse/depth envelope: `0`;
- immutable triangles whose chord interval changed after clipping: `0`.

Because every relevant source triangle is already wholly inside the fixed
transverse/depth envelope, its collision interval under chord translation is
exactly its raw chord-station span expanded by `6 mm` at each end. The solver
includes every such endpoint as an event, evaluates every event, and evaluates
one midpoint in every nonempty open interval. The immutable and aggregate
triangle-intersection states are therefore constant between consecutive
events for this frozen frame.

The independent sweep produced `729` immutable collision intervals. Their
union is exactly the complete allowed center-station domain:

`[-136.64553706761697, -10.263660358335688] mm`

Uncovered continuous intervals: `[]`.

Thus immutable-complement intersection alone rejects every continuous
fixed-frame placement. General completeness of terminal/keepout event
construction is not needed to establish this hard stop because no placement
can first pass the immutable gate.

## Authority and result audit

- All hashes embedded in `verified_inputs` match the current frozen aggregate,
  receipt, input Blend, input attestation, cell, cutter, exposure, floor,
  joint, negative-space, and terminal artifacts.
- Committed authority SHA-256:
  `e3b30ee70025dc36b60e5cd54eaefa9d64aeb146c6a361b0dccb8febc10720f9`.
- Committed receipt SHA-256:
  `de5c8b87646b73a13e12e0c9200175974df2b8869c7e766f25bfce823372c4b8`.
- Recomputed semantic fingerprint:
  `e7f6183a27716d9c916a2e5b7bf236ec9efb320a1775d5b358fa4b78eb1ba326`,
  exactly matching the authority.
- Independent execution against the frozen Blend reproduced the committed
  authority byte-for-byte. A second execution to the same temporary output
  paths reproduced both temporary authority and receipt byte-for-byte.
- Family counts reproduce exactly: `4,030` events, `8,059` placements,
  `8,059` immutable rejections, `1,988` additional
  `NO_C9_AGGREGATE_REMOVAL` rejections, and no accepted placement.
- The best eligible immutable counterexample reproduces at placement `8019`,
  center station `-10.989983793668 mm`, with `22` C20 and `2` C9 authorized
  removals and `46` immutable face hits. Its 46 face IDs and fingerprint
  `d0a5847feb727eb105fe3acf14a4149898d21833bb2ddee2b4494e0eeb7460f9`
  match the committed checkpoint.
- Exact source-triangle classification uses clipping against all six translated
  half-spaces. The supplementary best-counterexample audit covers all 46 hit
  faces as 48 intersecting triangle records and `9,587` barycentric samples.
  `ceil(max_triangle_edge / 1 mm)` bounds adjacent barycentric grid spacing to
  at most `1 mm`. Every one of the 48 records has at least one inside sample.

## Safety audit

Static inspection and two independent executions found no mesh-coordinate
write, object or mesh creation, save operator, render/image operation, Gate
B/D execution, or promotion. The script writes only its JSON authority and
receipt; independent reruns used temporary paths outside the repository.

- source/model mutation: false
- candidate geometry emitted: false
- Blend saved: false
- image work: false
- contract changed: false
- promotion: `NOT_PROMOTED`

## Conclusion

`V27_NO_VALID_12MM_FLEX_GAP` is valid for the stated fixed frozen
`FLEX_GAP_MINIMUM_CORE` translation architecture. Stage 3 surface construction
must remain stopped under that contract.

This is architectural exhaustion, not global impossibility. The legitimate
next scope decisions are:

1. deliberately redesign the flex-gap frame and/or orientation, then define
   and exhaust a new finite placement family;
2. deliberately revise the aggregate mask or immutable-face classification
   from new reviewed evidence; or
3. choose a different joint architecture that does not require this full
   fixed-frame 12 mm empty core.

None of those scope expansions is authorized by this review itself.

## Open questions

- Which of the three explicit architecture-level scope changes should become
  the next durable contract?

## Residual risk

- Convex keepout and terminal transition events were not independently proven
  complete as a general one-axis collision family. That does not weaken this
  result because the continuous immutable interval union already covers the
  entire domain.
- This is digital static geometry evidence only. It makes no motion, printable
  thickness, permanent connectivity, comfort, or physical-fit claim.

