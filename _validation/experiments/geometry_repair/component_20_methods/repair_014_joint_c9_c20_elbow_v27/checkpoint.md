# Repair 014 V27 full C9/C20 elbow-interface reconstruction checkpoint

Status: `V27_CONTRACT_AUTHORED_IMPLEMENTATION_NOT_STARTED`

Last durable update: 2026-07-29

## Outcome

V27 will produce one static, zero-thickness C9/C20 elbow-interface fitted
surface candidate whose aggregate reconstruction mask covers the complete
wearer-side interface demand proven by V26 while preserving the exact reviewed
visible complement and intentional negative space. The complete candidate must
pass cumulative Gate B transformation-integrity and Gate D clearance checks
before any visual claim is requested.

This checkpoint authorizes planning and later construction inside the V27 mask.
It does not report a candidate, a passed gate, a saved Blend, or promotion.

## V26 closure

V26 closes read-only at:

`NO_SEED_COVERING_EXPOSURE_CELL_SUBSET_V26`

The final exposure authority requires `23` seed-covering cells against V26's
aggregate cap of `12`. The cap is not wrong and must not be edited: it bounded
the V26 experiment and truthfully rejects that experiment. The independently
completed finite terminal search does establish both upper and lower
boundary-coincident terminal pairs, but it does not override the cell-cap
failure and does not authorize V26 geometry.

V26 performed no source mutation, candidate construction, flex-gap placement,
image request for a candidate, Blend save, or promotion.

## Frozen input authorities

V27 implementation must hash-verify every authority before deriving a mask or
geometry. Any mismatch is a hard stop until this checkpoint is deliberately
revised.

| Authority | Frozen path | SHA-256 |
| --- | --- | --- |
| Read-only Blender/source attestation | `v27_input_attestation.json` | `0c10b913be5647e53c623d2de62ab064874cfcc5d7a16b147f0139561e679bce` |
| Final exposure-cell authority after visual rounds 01–05 | `../repair_014_joint_c9_c20_elbow_v26/v26_exposure_cell_authority.json` | `bba29d185676ed6dadaa77c81b37ae8d05f149886a3151887b2804c88bc9b0a5` |
| Exact boundary-coincident terminal authority | `../repair_014_joint_c9_c20_elbow_v26/v26_terminal_authority.json` | `159cbf3a3ddacf0a6628d7f4d2f5bf5a69161727176095871ef3899e7d807c1d` |
| Exact cutter authority | `../repair_014_joint_c9_c20_elbow_v26/v26_cutter_authority.json` | `52baafbc473c0e85952b80c4db56bb5620310fb82aa7b23bd55f529e83b78d45` |
| Exact negative-space authority | `../repair_014_joint_c9_c20_elbow_v26/v26_negative_space_authority.json` | `4ba0184076e0f635fc64eaa82da59993dfa4b75b8c8edd82efa5139db0f8f2bd` |
| Exact floor-ownership authority | `../repair_014_joint_c9_c20_elbow_v26/v26_floor_ownership_authority.json` | `02b758bddee0be121c9c1e93cef13b781b4e8241bda862ec6c8d389aaf653ab9` |
| Compact floor-ownership summary | `../repair_014_joint_c9_c20_elbow_v26/v26_floor_ownership_summary.json` | `2a054e9290869a6b647b4da1fa52f98e6537c8bca2a3b12546374ff788c982a9` |
| Exact source cell and barrier authority | `../repair_014_joint_c9_c20_elbow_v26/v26_cell_authority.json` | `85a1a31f4ecb43dab16461684d53ba9d7e9c5090c1202dd021b101778b97edca` |
| Joint maximum-mask authority | `../repair_014_joint_c9_c20_elbow_v26/v26_joint_authority.json` | `e4a01b2d0e0f5d7997983d43af90cf2f2cd2bec81c859645b7e6961b8a55bbef` |

The exposure authority already incorporates the base face classification and
all five additive bridge-classification rounds. Those classifications are
frozen through its verified input hashes; an implementation must not silently
relabel reviewed faces.

## Aggregate reconstruction authority

V27 deliberately changes the scope boundary, not the V26 evidence:

- The aggregate authorized reconstruction mask is the union of the following
  `26` V26 wearer-facing exposure cells: the `23` exact seed-covering cells
  plus three exact terminal-dependency cells proven necessary by
  V27-AUTH-005.
  - C20: `000`, `002`, `003`, `004`, `005`, `006`, `007`, `008`, `009`,
    `010`, `011`, `012`, `013`, `017`, `018`, `020`, `021`, `022`, `023`,
    `028`, `029`.
  - C9: `000`, `001`, `002`, `003`, `004`.
- Full cell identifiers retain the `EXPOSURE_CELL_C20_` or
  `EXPOSURE_CELL_C9_` prefix from the frozen exposure authority.
- The face-level mask is the exact union of those cell memberships. Cell
  membership is authority; a geometric bounding box, proximity selection,
  material selection, or flood fill is not.
- All reviewed `EXTERIOR_OR_AMBIGUOUS` faces and every wearer-side face outside
  that exact union are the immutable complement. Shared boundary coordinates
  may be referenced as constraints, but immutable faces, loops, material
  assignments, and winding must remain byte-for-byte/topologically unchanged.
- `NO_FLOOR` samples are intentional openness, never repair seeds, fill targets,
  interpolation support, or permission for a carrier. The known `12,523`
  non-gap `NO_FLOOR` samples remain excluded.
- The clearance cutter is a subtraction and collision authority only. Cutter
  triangles, offsets, projections, and iso-surfaces must not become a global
  visible carrier or supply the visible design field.
- V27 may remove and reconstruct the complete aggregate mask in one authority,
  but implementation and proof must be checkpointed in batches of no more than
  `12` exposure cells. This is an implementation/recovery bound only. It must
  never be reapplied as an aggregate authorization or used to claim that a
  partial batch completes the interface.

No face may enter the aggregate mask merely because a construction algorithm
finds it convenient. A required expansion is a contract change and hard stop.

## Exact terminal contract

The frozen terminal authority supplies four exact source-boundary chains:

- C20 upper: `C20_CHAIN_17929_5618`
- C20 lower: `C20_CHAIN_3151_8123`
- C9 upper: `C9_CHAIN_2821_2823`
- C9 lower: `C9_CHAIN_15240_5360`

Every final patch incident to a terminal must use the recorded ordered source
coordinates and complementary winding exactly. Snapping by tolerance or
substituting a nearby chain is not boundary coincidence. Each terminal must
retain at least `1.7 mm` exact cutter clearance in the cumulative candidate.

## Dependency graph

Implementation must emit a deterministic, hashable dependency DAG before
constructing geometry. Its nodes are:

1. the `26` exact exposure cells;
2. the four frozen terminal chains;
3. the exact immutable-complement boundary loops adjacent to each cell;
4. the required flex-gap keepout cells;
5. the source-open-route, aperture, and central-opening keepout cells touched
   by a candidate cell;
6. exact floor-ownership conflict records touched by a candidate cell.

Edges must identify a concrete relation: shared boundary edge, shared boundary
vertex, terminal incidence, gap incidence, keepout incidence, or cumulative
topology dependency. Stable sorting is by component, exposure-cell numeric ID,
dependency kind, and exact source identifier.

The DAG determines batch order. A batch may contain at most `12` cells and must
be closed over all earlier dependencies needed to evaluate its cumulative
boundary. Cycles are condensed deterministically and must fit in one batch; a
strongly connected component larger than `12` is a hard stop, not permission
to split coincident boundary work or raise the bound.

## Deterministic stages

### Stage 0 — Freeze and attest inputs

Hash-verify every frozen authority and the exact input Blend identified by
those authorities. Record the script/code hash, Blender version, scene units,
object identities, source mesh fingerprints, and a clean statement that no
mutation has started. Copy no authority by hand.

Result on success: `V27_INPUT_AUTHORITIES_FROZEN`

### Stage 1 — Materialize aggregate mask and DAG

Derive the exact face union, immutable complement, boundary loops, terminal
incidences, keepout incidences, floor conflicts, DAG, strongly connected
components, and deterministic batches. Prove that the mask contains exactly
the frozen `26` cell memberships, contains no immutable face, and gives every
face unique ownership.

Result on success: `V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED`

### Stage 2 — Solve the flex gap before geometry

Select a flex-gap placement from the exact negative-space authority before
surface construction. The placement must:

- preserve a continuous empty gap of at least `12 mm`;
- avoid all exact immutable-complement triangles;
- preserve source apertures, source-open routes, central opening, and
  intentional `NO_FLOOR` openness;
- remain disjoint from the four exact terminal chains;
- declare which authorized wearer-side faces are removed on each side; and
- produce exact half-space/cell evidence, not sparse point-only evidence.

No patch generation may start until one placement satisfies the complete
aggregate contract.

Result on success: `V27_FLEX_GAP_SOLVED`

### Stage 3 — Enumerate the finite surface-construction family

For each batch, enumerate a finite, recorded family of zero-thickness
source-led surfaces. Every member must:

- interpolate exact immutable and terminal boundary coordinates with
  complementary winding;
- use source ridge, angular-depth, and layer-order landmarks as the visible
  design field;
- preserve material ownership explicitly;
- remain inside the authorized face union;
- maintain the solved flex gap and all negative-space keepouts; and
- meet at least `1.7 mm` exact cutter clearance over triangles and adaptive
  samples.

The finite family may include boundary-constrained triangulations and
landmark-constrained piecewise surface fields with a recorded finite parameter
grid. It may not include an unconstrained remesh, whole-component
displacement, collision-driven lift, cutter-conforming slab, full-perimeter
translated-core annulus, automatic face deletion, or a smooth global carrier.
Tie-breaking must be deterministic and recorded before evaluation.

Result when a batch has at least one numerically eligible member:
`V27_BATCH_SURFACE_CANDIDATE_FOUND`

### Stage 4 — Exact cumulative Gate B and Gate D per batch

Evaluate each batch as the cumulative aggregate candidate, never as an
isolated patch. After adding a batch, repeat:

- Gate B counts and immutable-complement identity;
- exact reconstruction-mask membership;
- winding, orientation, distortion, edge-stretch, layer-order, and material
  evidence;
- connected-component and boundary/nonmanifold-edge deltas against the
  declared cumulative target;
- exact triangle/cutter intersection plus adaptive clearance sampling;
- minimum cutter margin of `1.7 mm`;
- exact negative-space, flex-gap, aperture, route, and opening tests; and
- terminal coincidence for every terminal whose dependency is active.

Failed variants are evidence and remain unpromoted. The next batch cannot
start until the cumulative candidate for the current batch passes the named
Gate B and Gate D checks applicable to this bounded reconstruction.

Result per successful batch: `PASS_V27_BATCH_<NN>_CUMULATIVE_GATE_B_D`

### Stage 5 — Complete aggregate Gate B and Gate D

After all `26` cells are represented, rerun Gate B and Gate D from the frozen
source through the complete candidate, independent of batch receipts. Confirm
that partial checkpoints did not hide cross-batch regressions.

Results:

- `PASS_V27_COMPLETE_AGGREGATE_GATE_B`
- `PASS_V27_COMPLETE_AGGREGATE_GATE_D`

Anything less remains an experiment and is not a fitted-surface candidate for
visual review.

### Stage 6 — Disposable sanitized Gate C review

Only after both complete aggregate gates pass may the parent delegate render,
conversion, sanitization, and inspection to disposable image subagents.
Every generated render must be sanitized with ImageMagick to stripped,
auto-oriented, sRGB, conventional 8-bit PNG or JPEG. The subagent must record
the raw and sanitized paths, commands, sizes, observations, and decisions
immediately. No image over `10 MB` may enter image-model review. Review starts
at high detail from individual matched views or paginated contact sheets; no
full archival contact sheet may be inspected directly.

Gate C must compare the complete aggregate candidate against immutable source
evidence and explicitly answer `does_this_look_ass: false`.

Result on success: `PASS_V27_COMPLETE_STATIC_GATE_C`

## Explicitly deferred

V27 ends at the accepted static zero-thickness fitted surface. It makes no
claim about:

- Gate E motion behavior or the approximately `30°` priority pose;
- Gate F printable solids, thickness, or closure;
- Gate G permanent connectivity or loads;
- yokes, hinges, hardpoints, closures, or armor panels; or
- a TPU insert, its thickness, fastening, buckling, or physical validation.

These require later contracts after V27 passes Gate C.

## Hard stops

Stop without mutating or promoting when any of the following occurs:

- `V27_INPUT_AUTHORITY_HASH_MISMATCH`
- `V27_SOURCE_SCENE_OR_OBJECT_IDENTITY_MISMATCH`
- `V27_AGGREGATE_MASK_INCLUDES_IMMUTABLE_FACE`
- `V27_AGGREGATE_MASK_EXPANSION_REQUIRED`
- `V27_CELL_OWNERSHIP_NOT_UNIQUE`
- `V27_DEPENDENCY_SCC_EXCEEDS_BATCH_BOUND`
- `V27_NO_VALID_12MM_FLEX_GAP`
- `V27_NEGATIVE_SPACE_OR_NO_FLOOR_CONFLICT`
- `V27_NO_BOUNDARY_COINCIDENT_TERMINAL_CONSTRUCTION`
- `V27_NO_FINITE_SURFACE_MEMBER_CLEARS_CUTTER`
- `V27_CUMULATIVE_GATE_B_FAILED`
- `V27_CUMULATIVE_GATE_D_FAILED`
- `V27_COMPLETE_GATE_B_FAILED`
- `V27_COMPLETE_GATE_D_FAILED`
- `V27_GATE_C_REJECTED`

A hard stop must name the exact operation, cell/batch/candidate, authority
identifier, measured counterexample, and actionable reason. It must not relax a
threshold, relabel a face, widen the mask, fill `NO_FLOOR`, or substitute the
cutter as geometry.

## Result language

- Use `DONE` for successful tool execution and artifact production.
- Use `PASS` only for a named validation gate or audit.
- `CHECKPOINTED`, `FOUND`, and `SOLVED` record intermediate state; they do not
  imply promotion.
- `V27_STATIC_SURFACE_ACCEPTED` may be recorded only after complete aggregate
  Gates B, D, and C pass.
- Never describe a batch pass, terminal search, gap solution, or machine-only
  candidate as wearable, printable, connected, motion-safe, or promoted.

## Checkpoint and resume contract

Every implementation action must append a durable text entry before the next
action. Each entry records:

- UTC timestamp and monotonic stage/batch/candidate identifier;
- exact input and code hashes;
- operation and resolved object/face/cell identifiers;
- candidate artifact path and SHA-256;
- cumulative mask and completed-batch fingerprints;
- measurements, named result, and failed invariants;
- whether mutation began, geometry was emitted, a Blend was saved, images were
  requested, or anything was promoted; and
- the single next resumable operation.

Write artifacts atomically. Never overwrite a prior receipt: supersede it with
an explicit pointer and retain the earlier file. Save any experimental Blend
only under `blender_files/` with a versioned V27 name, never over the tracked
master or current salvage checkpoint. A restarted agent must reconstruct state
from hashes and receipts, not memory, chat, screenshots, or an unsaved Blender
session.

For image work, the image subagent writes its checkpoint before and after every
render, sanitization, size check, and inspection. The parent coordinates only
from that text evidence and never reads an image.

## First implementation milestone

The first implementation slice is read-only:

1. create a V27 authority builder that hash-verifies all frozen inputs;
2. derive the exact `26`-cell aggregate face mask and immutable complement;
3. emit the deterministic dependency DAG, SCCs, and `<=12`-cell batch order;
4. prove unique membership, exact terminal incidence, keepout incidence, and
   `NO_FLOOR` exclusion; and
5. write repeat-identical machine-readable authority and a concise receipt.

It must stop at `V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED`. It must not solve
the gap, generate geometry, request images, mutate a mesh, or save a Blend.
## V27 aggregate authority implementation retry01

- role: Agent Factory `implement`
- inherited_implementation_state: none; the prior implementation worker produced no checkpoint, file, or process progress
- next_action: implement and verify the deterministic V27 aggregate authority builder from the frozen V27 inputs, using the compact floor summary unless a specifically required exact record forces a separately checkpointed full-ledger read
- scope_stop: `V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED`
- prohibited_in_this_retry: gap solving, candidate geometry, source mutation, image work, and Blender saves

### V27-AUTH-001 — frozen schema inspection

- operation: inspect frozen authority schemas without loading the 315 MiB full
  floor ledger
- resolved_contract: 23 selected exposure cells, four terminal chains, 296
  negative-space convex cells, and compact proof excluding 12,523 intentional
  non-gap `NO_FLOOR` samples
- full_floor_ledger_loaded: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

## V27 Stage 2b contract revision — bounded local source-surface flex gap

Contract status: `V27_STAGE2B_LOCAL_GAP_CONTRACT_AUTHORED`

The independently reviewed fixed-frame result at commit `7b1ee11` exhausts
only the translated global `FLEX_GAP_MINIMUM_CORE`. Stage 2b deliberately
replaces that frame with a local gap bounded by two source-surface cut chains.
It does not expand the aggregate, relabel a face, authorize a carrier, or
authorize Stage 3 surface construction.

### Frozen and superseded authority

- Hash-verify the corrected Stage 0/1 aggregate authority, its receipt, the
  frozen input attestation, and every V26 authority already named by the
  aggregate authority.
- The exact 26-cell aggregate, its 266 source faces, 20 ordered boundary loops,
  four terminal chains, immutable complement, non-flex negative-space cells,
  and 12,523 `NO_FLOOR` exclusions remain frozen.
- Only the placement shape of `FLEX_GAP_MINIMUM_CORE` is superseded. Its
  `12.0 mm` minimum empty chord remains the acceptance threshold. The other
  295 negative-space cells remain exact keepouts.
- `v27_flex_gap_authority.json` remains retained failure evidence. Stage 2b
  writes new versioned authority and receipt files; it must not overwrite the
  fixed-frame result.

### Exact local chain family

Build the selected C20 and C9 half-edge graphs from source topology, using only
faces in the exact aggregate mask. A base chain is a simple ordered source-edge
path whose endpoints lie on exact ordered aggregate-boundary loops, whose
interior vertices are not boundary vertices, and whose edges have no immutable
face incidence. A chain may touch a frozen terminal only at an exact recorded
terminal vertex and may not use a terminal edge.

Enumerate base chains without geometric flood fill:

1. take every ordered endpoint pair on distinct boundary-loop records of the
   same component;
2. retain endpoint pairs connected through the selected aggregate graph;
3. emit the three deterministic shortest vertex-simple paths by source-edge
   length, with ties broken by the complete ordered vertex-ID tuple; and
4. reject a path that repeats a vertex, traverses an aggregate boundary edge
   except at an endpoint, leaves the component mask, or crosses an exact
   barrier/keepout incidence.

A Stage 2b chain pair contains one retained C20 path and one retained C9 path.
For each component, define its source-led station axis from the centroid of its
exact lower terminal chain toward the centroid of its exact upper terminal
chain. Orient a path from the lower endpoint dot-product station toward the
upper; reverse by lexicographic endpoint identity only when the stations tie.
Pair only paths whose endpoint order agrees and whose normalized-arclength
correspondence is non-crossing. This makes the two opposed cut chains explicit
without pretending C9 and C20 are one topological sheet.

### Source-led local frames and finite parameter grid

At every base-chain vertex, derive:

- tangent: centered path-edge tangent, with one-sided endpoint tangents;
- normal: normalized, area-weighted normal of incident selected source
  triangles, sign fixed by source winding; and
- chord: normalized cross product of normal and tangent, with sign from C20
  toward the paired C9 chain.

Parallel-transport the frame along each chain. A zero-length tangent, opposing
adjacent normals, or frame sign flip is a candidate rejection. The cutter must
not choose or flip tangent, normal, chord, or chain order.

For every base-chain pair, enumerate this complete grid:

- requested empty chord width: `[12, 14, 16, 18] mm`;
- chord orientation about the source normal:
  `[-30, -20, -10, 0, 10, 20, 30] degrees`;
- C20 and C9 signed local normal depth independently:
  `[-12, -8, -4, -2, 0, 2, 4, 8, 12] mm`; and
- chord displacement allocation from C20 to C9:
  `[0, 0.25, 0.5, 0.75, 1.0]`.

At each normalized-arclength correspondence, let `p20` and `p9` be the base
points, let the oriented local chord after the selected rotation be `c`, let
`d = dot(p9 - p20, c)`, let `delta = max(0, requested_width - d)`, and let `a`
be the selected allocation. Before normal depth, the displaced pair is
`p20 - a * delta * c` and `p9 + (1-a) * delta * c`. Depth and chord offsets use
a piecewise-linear endpoint taper that is exactly zero at both
source-boundary endpoints and reaches the grid value over the middle 50
percent of normalized arclength. Intersections with source triangles are
solved exactly and recorded as ordered barycentric cut coordinates; they are
not snapped to nearby vertices.

The matched cut chains define a ruled empty strip. Each corresponding ruled
quad is split by the lexicographically smaller diagonal and enclosed by its
local convex prism. Prism depth is exactly the maximum absolute selected
normal depth plus `1.7 mm`; transverse extent is the selected chord width and
never the fixed-frame transverse/depth envelope. The union of these local
prisms is only an empty-gap collision/removal footprint. It is not emitted as
visible geometry, a hidden carrier, a cutter surface, or a reconstruction
base.

Before evaluation, write the sorted base-chain records, parameter grid, ruled
quad/prism records, and a semantic fingerprint. Evaluation may not add a chain,
orientation, width, depth, or displacement allocation.

### Exact acceptance

A member is `V27_LOCAL_FLEX_GAP_SOLVED` only when all of these hold:

- the relative interiors of both cut chains and every ruled prism intersect
  only exact aggregate faces; immutable source triangles have zero-area
  intersection and may meet only at already shared aggregate-boundary
  coordinates;
- both components contribute a nonempty authorized removal, all removed faces
  belong to the exact 26-cell mask, and unique face ownership is preserved;
- ordered chain correspondence has no reversal or ruled-quad self-intersection
  and every exact local chord measurement is at least the requested width and
  never below `12.0 mm`;
- all four terminal polylines remain exact, ordered, disjoint from the open gap
  footprint, and at least `1.7 mm` from the cutter;
- the ruled-prism union is disjoint from every non-flex aperture,
  source-open-route, and central-opening keepout by combined-half-space
  feasibility;
- all 12,523 `NO_FLOOR` samples remain openness: none is used as a seed,
  interpolant, floor, side wall, or permission to enlarge the footprint;
- every retained or newly cut boundary segment is at least `1.7 mm` from the
  exact cutter under triangle/segment distance plus adaptive samples at no more
  than `1.0 mm` spacing; and
- the cutter is referenced only by those collision and clearance tests.

Shared-boundary contact is not immutable removal. Any positive-area immutable
intersection, out-of-mask triangle fragment, terminal-edge use, or
non-flex-keepout intersection rejects the member.

### Stage 2b hard stops

- `V27_LOCAL_GAP_INPUT_HASH_MISMATCH`
- `V27_LOCAL_GAP_NO_ELIGIBLE_C20_CHAIN`
- `V27_LOCAL_GAP_NO_ELIGIBLE_C9_CHAIN`
- `V27_LOCAL_GAP_NO_ORDERED_CHAIN_PAIR`
- `V27_LOCAL_GAP_FRAME_DEGENERATE`
- `V27_LOCAL_GAP_FAMILY_NOT_PREENUMERATED`
- `V27_LOCAL_GAP_AGGREGATE_MASK_EXPANSION_REQUIRED`
- `V27_LOCAL_GAP_IMMUTABLE_INTERSECTION`
- `V27_LOCAL_GAP_TERMINAL_CONFLICT`
- `V27_LOCAL_GAP_NEGATIVE_SPACE_OR_NO_FLOOR_CONFLICT`
- `V27_LOCAL_GAP_CUTTER_CLEARANCE_FAILED`
- `V27_NO_VALID_LOCAL_12MM_FLEX_GAP`

If no member passes, record the best counterexample per rejection class,
including exact chain IDs, parameter tuple, face/cell IDs, minimum chord and
cutter margin, intersection witnesses, and fingerprints. Face classification
must remain frozen unless the complete local family identifies a specific
immutable face or finite face set as the sole remaining barrier after every
other gate passes. That result is
`V27_LOCAL_GAP_SPECIFIC_REVIEWED_BARRIER_IDENTIFIED`; it requests a separate
review and does not itself authorize relabeling.

### Safety and first implementation milestone

Stage 2b is read-only. It may write JSON/text authority and receipts only. It
must not mutate a mesh, emit candidate geometry, save a Blend, request image
work, run Gate B/D, or promote anything.

The first implementation slice is:

1. implement a read-only local-gap family builder that hash-verifies the
   corrected Stage 0/1 and frozen V26 inputs;
2. enumerate and fingerprint the eligible C20 and C9 base chains, ordered
   chain pairs, exact parameter grid, and ruled local-prism definitions;
3. prove every chain edge and prism seed belongs only to the exact aggregate
   and no terminal edge or `NO_FLOOR` record supplied construction data;
4. execute twice and require byte-identical authority plus semantic
   fingerprint; and
5. stop at `V27_LOCAL_GAP_FAMILY_CHECKPOINTED` before evaluating a member.

Only a separately reviewed family authority may proceed to exact member
evaluation. Stage 3 remains stopped until an evaluated member records
`V27_LOCAL_FLEX_GAP_SOLVED`.

- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: determine whether compact evidence contains every exact
  cell-level floor-conflict incidence

### V27-AUTH-002 — specific full-ledger need

- operation: identify exact records absent from the compact floor summary
- result: the summary proves `NO_FLOOR` exclusion and unique ownership, but
  exposes only the first and last of 91 gap-floor conflicts and seven
  layer-order inversions
- exact_record_need: enumerate only
  `ownership.gap_source_floors_requiring_removal` and the seven
  `ownership.samples[*]` records where
  `ordered_cutter_floor_exterior_valid == false`
- full_floor_ledger_read_authorized: true, after byte-hash verification, with
  no mutation and no retained bulk copy
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: extract those 98 exact conflict records and implement the
  deterministic aggregate builder

### V27-AUTH-003 — exact conflict extraction

- operation: hash-verify the full ledger and extract only the required conflict
  classes
- full_floor_authority_sha256:
  `02b758bddee0be121c9c1e93cef13b781b4e8241bda862ec6c8d389aaf653ab9`
- exact_gap_floor_record_count: 91
- exact_layer_inversion_record_count: 7
- extracted_bulk_floor_samples: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: implement the builder using these exact paths directly from the
  frozen authority

### V27-AUTH-004 — builder materialized and statically checked

- artifact: `scripts/blender/build_v27_aggregate_authority.py`
- operation: implement the complete read-only aggregate authority builder
- `python3 -m py_compile`: `DONE`
- `ruff check`: `DONE`; all checks passed
- observed_contract_conflict: C20 upper terminal candidate faces `2995` and
  `3052` belong to excluded exposure cells `007` and `009`; C20 lower candidate
  face `3102` belongs to excluded exposure cell `011`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: execute the builder twice, compare byte hashes, and audit every
  mask, terminal, keepout, floor, SCC, and batch invariant

### V27-AUTH-005 — aggregate authority checkpointed

- operation: execute, repeat, byte-compare, and independently audit the V27
  aggregate authority builder
- code_path: `scripts/blender/build_v27_aggregate_authority.py`
- code_sha256:
  `eab9839de351366b29912c5c9ea5814d2a8161ee7872be86bc1a62df63aaaa4b`
- authority_path:
  `_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/v27_aggregate_authority.json`
- authority_sha256:
  `0c1cd7188aca4eb05effdd1afd30c277d002b71692e4e8d25e61da534dad6609`
- receipt_path:
  `_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/v27_aggregate_authority_receipt.json`
- receipt_sha256:
  `66382f3006f3f037bb01bce00a968553a062409edf7b1131d040ff63b9816a9f`
- repeatability: `DONE`; two authority runs and two receipt runs were
  byte-identical
- named_audit: `PASS_V27_AGGREGATE_AUTHORITY_INVARIANT_AUDIT`
- exact_aggregate_mask: 23 cells; 179 C20 faces and 81 C9 faces; unique face
  ownership; zero immutable overlap; zero maximum-mask expansion
- aggregate_boundary: 252 exact boundary edges in 10 connected boundary
  components
- exact_terminal_incidences: four records; both C9 incidences complete; both
  C20 incidences incomplete
- negative_space_incidences: 551 exact convex-cell/source-edge incidence
  records
- floor_conflicts: 98 exact frozen records accounted for; 63 touch the
  aggregate mask and 35 remain in the immutable complement
- no_floor_exclusion: all 12,523 intentional non-gap `NO_FLOOR` samples remain
  excluded and were not used as faces, seeds, or support
- dependency_graph: eight cell SCCs; maximum SCC size 7; deterministic batch
  cell counts `[7, 11, 5]`; no SCC is split and every batch is at most 12 cells
- result: `V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED`
- hard_stop: `V27_NO_BOUNDARY_COINCIDENT_TERMINAL_CONSTRUCTION`
- counterexample:
  - C20 upper `C20_CHAIN_17929_5618`: candidate faces `2995` and `3052`
    require excluded cells `EXPOSURE_CELL_C20_007` and
    `EXPOSURE_CELL_C20_009`
  - C20 lower `C20_CHAIN_3151_8123`: candidate face `3102` requires excluded
    cell `EXPOSURE_CELL_C20_011`; only candidate face `3103` is in selected
    cell `EXPOSURE_CELL_C20_012`
- actionable_reason: the frozen 23-cell aggregate mask and frozen exact C20
  terminal contract cannot both be satisfied; do not solve the flex gap,
  construct geometry, or widen the mask until the V27 contract is deliberately
  revised
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: parent reviews the named terminal/mask contract inconsistency and
  decides whether a deliberate V27 charter revision may add cells `007`, `009`,
  and `011`

### V27-AUTH-006 — deliberate terminal-dependency charter revision

- authority_decision: the user already authorized full C9/C20 interface
  reconstruction; expand V27 aggregate authority from the 23 exact
  seed-covering cells to 26 exact cells by adding only
  `EXPOSURE_CELL_C20_007`, `EXPOSURE_CELL_C20_009`, and
  `EXPOSURE_CELL_C20_011`
- exact_reason: these three wearer-facing cells contain the candidate-side
  source faces required by the already frozen C20 upper and lower
  boundary-coincident terminal chains
- unchanged_constraints: immutable reviewed faces, `NO_FLOOR` openness,
  negative-space cells, `>=12 mm` flex gap, `>=1.7 mm` cutter clearance,
  exact four terminal chains, and `<=12`-cell implementation batches
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: regenerate and independently audit the 26-cell aggregate
  authority; do not start flex-gap solving until all four terminal incidences
  are complete

### V27-AUTH-007 — 26-cell aggregate authority checkpointed

- operation: regenerate, repeat, byte-compare, and audit the deliberately
  revised 26-cell aggregate authority
- code_sha256:
  `a8d4e418dc7b9cf4fe3ca97ed5d914a7487a5a238811d37c95f94fd517f921ba`
- authority_sha256:
  `552544386bb3f3012527b2bfd819986c1c7b3f82d5d4585b01feb426e4ad78af`
- receipt_sha256:
  `d22e2b1e85b199f789cf7bf875288b2208db50eddb524fc9b89e7c6875f4bff3`
- repeatability: `DONE`; two authority and receipt runs were byte-identical
- named_audit: `PASS_V27_AGGREGATE_AUTHORITY_INVARIANT_AUDIT`
- exact_aggregate_mask: 26 cells; 185 C20 faces and 81 C9 faces; unique face
  ownership; zero immutable overlap; zero maximum-mask expansion
- exact_terminal_incidences: four records and all four complete
- aggregate_boundary: nine connected boundary components
- negative_space_incidences: 571
- floor_conflicts: all 98 exact frozen records accounted for; 63 touch the
  aggregate mask and 35 remain excluded
- no_floor_exclusion: all 12,523 intentional non-gap `NO_FLOOR` samples remain
  excluded
- dependency_graph: seven SCCs; maximum SCC size 7; deterministic batch cell
  counts `[7, 12, 7]`
- hard_stops: none
- result: `V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: independently review the revised authority, then solve the
  exact `>=12 mm` flex gap before any candidate geometry
### V27-AUTH-008 — ordered aggregate boundary implementation start

- role: Agent Factory `implement`
- review_hard_stop: `V27_AGGREGATE_BOUNDARY_LOOPS_NOT_MATERIALIZED`
- inherited_counterexample: four of nine aggregate boundary connected records
  contain degree-4 vertex touches and empty `ordered_vertex_ids`; the largest
  cited C20 graph contains 65 exact boundary edges
- authorized_change: preserve the revised exact 26-cell aggregate mask and
  every aggregate boundary edge exactly once while decomposing each
  vertex-touching graph into deterministically ordered, edge-disjoint simple
  source-oriented loops or paths with complementary source winding evidence
- prohibited: gap solving, candidate geometry, source mutation, image work,
  Blend saves, promotion, edge suppression, and degree-4 relabeling
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: inspect the revised 26-cell authority/checkpoint and exact review
  counterexamples, then patch only the aggregate boundary materialization

### V27-AUTH-009 — Stage 0 read-only metadata inspection authorized

- operation: materialize the missing exact Stage 0 scene attestation required
  by independent review
- reason_blend_open_is_required: frozen JSON authorities contain exact units,
  object/datablock identities, and source fingerprints, but do not record the
  Blender runtime/file version
- exact_background_command:
  `/Applications/Blender.app/Contents/MacOS/Blender --background blender_files/experiments/geometry_repair/repair_014_joint_c9_c20_elbow_v24.blend --python-expr <read-only JSON metadata expression>`
- read_only_expression_scope: report `bpy.app.version_string`,
  `bpy.data.version`, scene unit settings, and the exact object/datablock/count
  identities for `EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER` and
  `CUT_CLEARANCE_ANATOMY_STRAIGHT`
- save_operator_allowed: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: run the exact background read-only inspection, reconcile its
  output with frozen authority identities, and embed the attestation in the
  regenerated aggregate authority

### V27-AUTH-010 — Stage 0 metadata inspected

- operation: read exact source-scene metadata in Blender background mode
- runtime_version: `5.2.0 LTS Beta`
- runtime_version_tuple: `[5, 2, 0]`
- blend_file_version: `[5, 2, 44]`
- scene_units: `METRIC`, `MILLIMETERS`,
  `scale_length = 0.0010000000474974513`
- source_object: `EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER`, type `MESH`,
  datablock `EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER_MESH`, 7,347
  vertices, 12,564 polygons
- cutter_object: `CUT_CLEARANCE_ANATOMY_STRAIGHT`, type `MESH`, datablock
  `CUT_CLEARANCE_ANATOMY_STRAIGHT_MESH`, 408 vertices, 386 polygons
- reconciliation: all units, object/datablock identities, and counts match the
  frozen V26 joint/cutter authorities exactly
- save_operator_invoked: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: implement oriented edge-disjoint simple boundary decomposition,
  complementary winding validation, and the exact Stage 0 authority block

### V27-AUTH-011 — repeatable Stage 0 attestation checkpointed

- operation: materialize the V27-AUTH-010 metadata inspection as a
  repeat-identical machine-readable source attestation with exact mesh
  fingerprints
- attestation_code_sha256:
  `648e85d974ab077370945446e90eb412281702b847091e72c1b38ca54c4d520b`
- attestation_sha256:
  `0c10b913be5647e53c623d2de62ab064874cfcc5d7a16b147f0139561e679bce`
- source_object_fingerprint:
  `aaf473c8d127896bb7fa46cee96b7b56a4a6710bac203a977051393cf3136558`
- fitted_shape_key_object_fingerprint:
  `70180fc9e48bc346e446ccf49c3d6b79b2ca8d105cc5cab3c1806c6b7beb2326`
- repeatability: `DONE`; two background attestation runs were byte-identical
- result: `V27_INPUT_AUTHORITIES_FROZEN`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

### V27-AUTH-012 — ordered aggregate boundary audit passed

- operation: replace branched connected-boundary summaries with a
  deterministic edge-disjoint decomposition into ordered simple source
  boundary loops
- builder_code_sha256:
  `bdf56add14750578d045d8e1ab84002863cf9017188d48369607f3f9b8a3c268`
- authority_sha256:
  `43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338`
- receipt_sha256:
  `f4d1e3190999bd22bb9477953bd541f41c0d65b2dba86f729d854920ca0dc938`
- exact_boundary_partition: 260 unique edges, 20 ordered simple loops, every
  edge present exactly once, no empty orderings, no branched output record
- frozen_input_attestation_verified: true
- repeatability: `DONE`; two authority and receipt runs were byte-identical
- named_audit: `PASS_V27_ORDERED_BOUNDARY_AND_STAGE0_AUDIT`
- prior_review_stop_resolved:
  `V27_AGGREGATE_BOUNDARY_LOOPS_NOT_MATERIALIZED`
- hard_stops: none
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: independent re-review of the ordered boundary and Stage 0
  attestation before the exact flex-gap solver starts

### V27-FLEX-001 — Stage 2 exact flex-gap solver started

- operation: begin the read-only deterministic finite search for an empty,
  continuous, minimum-12-mm chordwise flex gap within the frozen 26-cell V27
  aggregate authority
- prerequisite_commit: `72be45d`
- required_inputs: committed V27 input attestation, aggregate authority and
  receipt, plus the attested V26 negative-space, cell, terminal, cutter, and
  exposure authorities
- evidence_contract: exact half-space/convex-cell and source-triangle
  intersection tests supplemented by adaptive sampling; no sparse point-only
  acceptance
- finite_family_contract: enumerate and fingerprint the complete ordered
  placement family before evaluating candidates
- exclusions: immutable complement triangles, aperture/open-route/central
  opening keepouts, all four exact terminal chains, and `NO_FLOOR` openness
- output_contract: atomic `v27_flex_gap_authority.json` and compact receipt;
  two byte-identical runs; stop at `V27_FLEX_GAP_SOLVED` or the exact
  `V27_NO_VALID_12MM_FLEX_GAP` counterexample set
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

### V27-FLEX-002 — frozen inputs verified and finite family defined

- operation: hash-verify the committed Stage 0/Stage 1 V27 artifacts and every
  V26 authority frozen by `v27_aggregate_authority.json`, then define the
  complete finite Stage 2 placement family
- verified_stage1_authority_sha256:
  `43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338`
- verified_stage1_receipt_sha256:
  `f4d1e3190999bd22bb9477953bd541f41c0d65b2dba86f729d854920ca0dc938`
- family_frame: reuse the frozen `FLEX_GAP_MINIMUM_CORE` orthonormal frame,
  transverse/depth envelope, and exact `12.0 mm` chordwise width; translation
  is permitted only along its recorded chord axis
- family_domain: the closed chord-station span of vertices referenced by the
  exact 26-cell aggregate source-face union and its 20 ordered boundary loops
- event_definition: all chord-station values at which a 12 mm slab boundary
  becomes coincident with an aggregate, immutable-complement, terminal, or
  aperture/open-route/central-opening source or convex-cell vertex
- finite_representatives: every in-domain event placement plus one
  deterministic midpoint from every nonempty interval between consecutive
  events; this exhausts the fixed-frame combinatorial placement states before
  evaluation
- acceptance: selected removals must include authorized aggregate faces on
  both C20 and C9, include no immutable face, remain exactly disjoint from all
  four terminal polylines and every non-flex negative-space convex cell, and
  retain an exact 12 mm chordwise width
- exactness: source triangles are clipped against all six translated slab
  half-spaces; convex-cell conflicts use combined-half-space feasibility;
  terminal segments use exact convex clipping; adaptive <=1 mm barycentric
  triangle samples independently audit each exact classification
- no_floor: the frozen 12,523 `NO_FLOOR` samples remain excluded from both
  family construction and acceptance
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

### V27-FLEX-003 — solver materialized for first execution

- script: `scripts/blender/solve_v27_flex_gap.py`
- operation: execute the complete pre-enumerated family in the frozen V24
  source scene and atomically write the V27 Stage 2 authority and receipt
- static_checks_before_execution: `python3 -m py_compile` DONE; initial Ruff
  found one unused local (`frozen_station`), which was removed; repeat static
  checks are required before execution
- expected_stop: `V27_FLEX_GAP_SOLVED` or
  `V27_NO_VALID_12MM_FLEX_GAP`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

### V27-FLEX-004 — first complete family execution found a hard stop

- operation: execute all fixed-frame finite placement representatives against
  exact source triangles before any candidate surface construction
- family_event_count: `4030`
- family_placement_count: `8059`
- family_fingerprint:
  `7eab8b9546b10c1c0544e601764e3feeed5fa2653ff1d59b0cb2ac1caaaa237d`
- chord_station_domain_mm:
  `[-136.64553706761697, -10.263660358335688]`
- evaluated_placement_count: `8059`
- immutable_triangle_intersection_count: `8059`
- no_C9_aggregate_removal_count: `1988`
- exact_result: `V27_NO_VALID_12MM_FLEX_GAP`
- first_execution_authority_sha256:
  `239a9da0179410ea9ecc92c8ddab60f4733a1523edb25de073a6e92fa08e21f2`
- first_execution_semantic_fingerprint:
  `af2c762deba7b1081aee419ac18408ab333c63c10b65764619e695ba09f7e835`
- first_exact_immutable_counterexample: placement `0`, center station
  `-136.645537067617 mm`, intersects immutable source faces beginning
  `[5765, 5766, 5768, 5770, 7452, 7456, 7457, 7458]`
- consequence: every member fails the immutable-complement gate; terminal and
  non-flex negative-space checks cannot rescue any member and are
  short-circuited only after the exact immutable rejection is recorded
- correction_before_repeat: add one exact immutable witness face ID to every
  placement record and correct the positive `no_floor_used_as_geometry_or_seed`
  invariant value; rerun the full family twice after static checks
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

### V27-FLEX-005 — Stage 2 repeatable hard stop checkpointed

- script: `scripts/blender/solve_v27_flex_gap.py`
- authority: `v27_flex_gap_authority.json`
- receipt: `v27_flex_gap_authority_receipt.json`
- exact_result: `V27_NO_VALID_12MM_FLEX_GAP`
- family_event_count: `4030`
- family_placement_count: `8059`
- evaluated_placement_count: `8059`
- family_fingerprint:
  `7eab8b9546b10c1c0544e601764e3feeed5fa2653ff1d59b0cb2ac1caaaa237d`
- authority_sha256:
  `e3b30ee70025dc36b60e5cd54eaefa9d64aeb146c6a361b0dccb8febc10720f9`
- receipt_sha256:
  `de5c8b87646b73a13e12e0c9200175974df2b8869c7e766f25bfce823372c4b8`
- semantic_fingerprint:
  `e7f6183a27716d9c916a2e5b7bf236ec9efb320a1775d5b358fa4b78eb1ba326`
- repeatability: `DONE`; two final background-Blender executions produced
  byte-identical authority and receipt hashes
- immutable_rejection: all `8059` placements have an exact
  immutable-complement triangle intersection
- additional_rejection: `1988` placements also remove no authorized C9 face
- minimum_immutable_hit_counterexample:
  - placement_index: `8019`
  - representative: `OPEN_INTERVAL_MIDPOINT`
  - center_station_mm: `-10.989983793668`
  - authorized_removals: C20 `22`, C9 `2`
  - immutable_hit_count: `46`
  - immutable_face_ids:
    `[2109, 2110, 2286, 2287, 2705, 2713, 2714, 2715, 2905, 2909, 2911, 2912, 7527, 7528, 7529, 7530, 7531, 9047, 9053, 9054, 9058, 9059, 9060, 9061, 9062, 9063, 9064, 9065, 9066, 9067, 9068, 9069, 9075, 9079, 9080, 9082, 9086, 9087, 9090, 9091, 9092, 9095, 9096, 9097, 9099, 12515]`
  - immutable_face_ids_fingerprint:
    `d0a5847feb727eb105fe3acf14a4149898d21833bb2ddee2b4494e0eeb7460f9`
- most_recurring_exact_witness_faces:
  `1409×1592`, `1084×1379`, `1407×1313`, `5765×922`, `1411×636`,
  `1440×456`, `2209×394`, `2109×220`
- adaptive_counterexample_audit: `48` exact intersecting triangle records,
  `9587` barycentric samples at no more than `1.0 mm` spacing
- named_audit: `PASS_V27_FLEX_GAP_AUTHORITY_INVARIANT_AUDIT`
- static_checks: `python3 -m py_compile` DONE; Ruff DONE; `git diff --check`
  DONE
- scope_stop: Stage 3 candidate surface construction remains unauthorized;
  changing the fixed frozen gap frame, expanding the 26-cell aggregate, or
  reclassifying immutable faces requires a deliberate contract revision
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
