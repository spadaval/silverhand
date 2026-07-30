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

### V27-LOCAL-001 — Stage 2b family builder started

- started_from_commit: `3ee52eb6415349107c174c16d4f636d632febea5`
- operation: implement the first read-only Stage 2b milestone as
  `scripts/blender/build_v27_local_gap_family.py`
- required_outputs: atomic full family authority plus compact receipt under
  this V27 evidence directory
- required_proof: hash-verify the corrected Stage 0/1 authority, receipt,
  attestation, and frozen V26 inputs; enumerate exact aggregate-topology C20
  and C9 base chains, ordered non-crossing pairs, the complete finite parameter
  grid, and deterministic ruled-prism definitions; prove no terminal edge,
  immutable incidence, barrier edge, or `NO_FLOOR` datum supplies construction
  input
- planned_terminal_result: `V27_LOCAL_GAP_FAMILY_CHECKPOINTED`
- evaluation_started: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`

### V27-LOCAL-002 — implementation handoff checkpoint

- result: family-builder design completed but no script or family artifact was
  materialized by the first implementation worker
- verified_topology_scope: C20 has 185 selected faces and 16 ordered boundary
  loops; C9 has 81 selected faces and four ordered boundary loops
- planned_algorithm: three deterministic Yen paths per reachable
  distinct-loop endpoint pair, source-led frames, exact edge exclusions,
  ordered non-crossing pair filter, and a factorized 5,040-member parameter
  grid per retained pair
- retained_work: contract and this text checkpoint only; there is no
  uncheckpointed code or generated authority to resume
- evaluation_started: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: a fresh implementation worker materializes
  `scripts/blender/build_v27_local_gap_family.py` incrementally from the
  committed Stage 2b contract and this exact handoff

### V27-LOCAL-003 — repeatable local-gap family checkpointed

- script: `scripts/blender/build_v27_local_gap_family.py`
- authority: `v27_local_gap_family_authority.json`
- receipt: `v27_local_gap_family_authority_receipt.json`
- result: `V27_LOCAL_GAP_FAMILY_CHECKPOINTED`
- corrected_parameter_tuple_count_per_pair: `11,340`
- stale_handoff_count: `5,040`
- correction_reason: the exact grid has four widths, seven orientations, nine
  independent C20 depths, nine independent C9 depths, and five allocations;
  `4 * 7 * 9 * 9 * 5 = 11,340`
- eligible_chain_counts: C20 `152`, C9 `8`
- ordered_non_crossing_chain_pair_count: `1,216`
- factorized_family_member_count: `13,789,440`
- family_fingerprint:
  `6b0ee763889e4bbac7af1d638ec0f1e14b709098fcfbdcb12c910d7dc5a458a9`
- authority_sha256:
  `14eccf5706d6325901cb9a025ca16a8cb8898dd190be672863c308403f06866d`
- receipt_sha256:
  `5a1da9d6636138f32c2dc3b11a5da8f1e15967fa9693d620c4a66622625c36aa`
- repeatability: `DONE`; two default-path background-Blender executions
  produced byte-identical authority and receipt files
- semantic_audit: `PASS_V27_LOCAL_GAP_FAMILY_SEMANTIC_AUDIT`; code hash,
  every chain fingerprint, every pair fingerprint, the complete family
  fingerprint, Cartesian-product count, unique chain IDs, and all recorded
  invariants recomputed exactly
- rejected_implementation_attempts:
  - treating every edge of a keepout-intersecting face as an exact barrier
    removed all C20 chains; only exact shared source-edge barriers belong in
    base-chain exclusion, while full keepout volumes remain reserved for exact
    prism evaluation
  - the first completed file was byte-repeatable but failed semantic audit
    because endpoint frame dictionaries were aliased and mutated during pair
    construction; copied endpoint frames resolve the mismatch
- evaluation_started: false
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: independently review the frozen family authority, then build a
  read-only exact member evaluator that preserves the factorized family and
  records deterministic rejection witnesses before any Stage 3 geometry

### V27-LOCAL-004 — minimum-width family exhausted

- evaluator: `scripts/blender/evaluate_v27_local_gap_family.py`
- merger: `scripts/tools/merge_v27_local_gap_width12.py`
- authority: `v27_local_gap_width12_exhaustion_authority.json`
- receipt: `v27_local_gap_width12_exhaustion_receipt.json`
- exact_member_interval: `[0, 3,447,359]`
- evaluated_width_12_member_count: `3,447,360`
- primary_result: `V27_NO_VALID_LOCAL_12MM_FLEX_GAP`
- primary_repeatability: `DONE`; one 13-shard execution and one independent
  four-shard execution have identical rejection totals
- best_primary_counterexample:
  - member_index: `687056`
  - pair_id: `LOCAL_GAP_PAIR_000215`
  - parameters: width `12`, orientation `10`, C20 depth `4`, C9 depth `-2`,
    allocation `0.5`
  - minimum_chord_mm: `28.559136961565805`
  - removals: C20 `6`, C9 `1`
  - immutable_hit_count: `1`
  - immutable_source_face_ids: `[2227]`
- single_face_diagnostic:
  - operation: repeat the complete width-12 family while allowing any member
    with at most one immutable hit to continue through downstream gates,
    without relabeling or authorizing that face
  - result: `V27_NO_SUFFICIENT_SINGLE_IMMUTABLE_FACE_EXCEPTION`
  - negative_space_conflict_count: `145`
  - selected_member_count: `0`
  - conclusion: every zero/one-immutable primary survivor conflicts with
    frozen source-open-route or central-opening negative space before cutter
    clearance; deleting or relabeling one extra face cannot solve width 12
- authority_sha256:
  `828080c31125d1119afba78f404a112867b3d78816d403a942d65c6a4b4df372`
- receipt_sha256:
  `09258c55424c79008837623cc5b74c21a663486be32de92ca322a5834ca207ad`
- semantic_fingerprint:
  `bdd64e4db64360111c6902feb0f7375d58ba5fbba519f6dd34126b0d2bbceb77`
- merge_repeatability: `DONE`; two executions produced byte-identical compact
  authority and receipt files
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: preserve this minimum-width hard stop, then evaluate the frozen
  14/16/18 mm width axes only to complete the authored family; Stage 3 remains
  unauthorized

### V27-LOCAL-005 — complete Stage 2b family exhausted

- evaluator: `scripts/blender/evaluate_v27_local_gap_family.py`
- merger: `scripts/tools/merge_v27_local_gap_full.py`
- authority: `v27_local_gap_full_exhaustion_authority.json`
- receipt: `v27_local_gap_full_exhaustion_receipt.json`
- exact_member_interval: `[0, 13,789,439]`
- evaluated_member_count: `13,789,440`
- widths_exhausted_mm: `[12, 14, 16, 18]`
- result: `V27_NO_VALID_LOCAL_12MM_FLEX_GAP`
- selected_member_count: `0`
- zero_immutable_negative_space_survivors:
  - width 12: `0`
  - width 14: `5`
  - width 16: `5`
  - width 18: `10`
- survivor_geometry: all `20` records are allocation-equivalent evaluations
  of the frozen central-opening corridor family; the first uses pair
  `LOCAL_GAP_PAIR_000071`, width `14`, zero orientation, zero depths, and
  removes three C20 faces plus one C9 face
- merged_opening_diagnostic:
  - operation: allow every zero-immutable larger-width survivor to continue
    through its exact central-opening conflict without relabeling the opening,
    then run exact cutter clearance
  - result: `V27_NO_VALID_CENTRAL_OPENING_MERGE`
  - evaluated_survivor_count: `20`
  - cutter_clearance_failure_count: `20`
  - common_minimum_clearance_mm: `0.0`
  - common_witness: C9 cut-chain segment `0`, cutter triangle `466`
  - conclusion: merging the flex gap into the existing central opening does
    not restore wearer clearance
- exact_C9_landing_dependency:
  - chain_id: `LOCAL_GAP_C9_CHAIN_EB7E82AAC63863FF`
  - ordered_vertex_ids: `[1541, 1543]`
  - source_edge_id: `12916`
  - endpoint_boundaries:
    `[AGGREGATE_BOUNDARY_C9_001, AGGREGATE_BOUNDARY_C9_000]`
  - reason_for_next_scope: the chain is a single boundary-to-boundary source
    edge and the endpoint taper forces zero displacement along the exact
    cutter-intersecting segment; more interior prism parameters cannot repair
    it
- authority_sha256:
  `c1212eff5367b58c9450bfae0caeddaf6a7efcc0a163a3b096d4175b097abdc3`
- receipt_sha256:
  `70c0ed4e3f677d391b4287052d6b5c4b5725bccc9cfc11aa73e86da58e15fadd`
- semantic_fingerprint:
  `ce651ed92c02092e4fdcd3da390d50055b345e28a58d77cf58da1dcb84d4bfe9`
- merge_repeatability: `DONE`; two executions produced byte-identical compact
  authority and receipt files
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: stop searching the frozen local-prism family; author a new
  bounded C9 landing reconstruction that may move/rebuild source edge `12916`
  and its exact adjacent aggregate boundary dependencies far enough to achieve
  `>=1.7 mm` cutter clearance before defining a new flex-gap footprint

## V27 Stage 2c contract revision — bounded C9 landing reconstruction

Contract status: `V27_STAGE2C_C9_LANDING_CONTRACT_AUTHORED`

The complete Stage 2b family proves that the frozen C9 landing, not the
interior gap width, is the controlling wearer-clearance dependency. Stage 2c
therefore permits read-only exploration of one finite C9 landing patch before
any new gap footprint or surface construction.

### Exact landing scope

- source edge: `12916`
- ordered source vertices: `[1541, 1543]`
- source coordinates:
  - vertex `1541`: `[131.5033721923828, -54.486942291259766,
    -78.9244613647461]`
  - vertex `1543`: `[149.577880859375, -63.37962341308594,
    -55.896202087402344]`
- exact incident selected faces: `[2230, 2240]`
- exact endpoint one-ring faces:
  `[2227, 2228, 2230, 2231, 2232, 2235, 2239, 2240, 2243, 2244, 2245]`
- prior classifications inside that one-ring:
  - selected aggregate: `[2228, 2230, 2240, 2243, 2244]`
  - immutable complement: `[2227, 2231, 2232, 2245]`
  - outside prior maximum mask: `[2235, 2239]`
- endpoint boundary records:
  `[AGGREGATE_BOUNDARY_C9_001, AGGREGATE_BOUNDARY_C9_000]`

The 11-face one-ring is a candidate reconstruction mask, not an authorized
mutation. Its four immutable and two outside-mask faces remain source evidence
until a finite landing family proves an exact clearance benefit and a separate
review authorizes the mask revision.

### First Stage 2c milestone

1. Hash-verify the complete Stage 2b exhaustion authority and frozen source
   scene.
2. Enumerate a finite source/cutter-normal-led family of displaced endpoint
   pairs for edge `12916`.
3. Require exact segment-to-cutter clearance of at least `1.7 mm`.
4. Reject intersection with source faces outside the 11-face landing mask,
   frozen terminal chains, apertures, or source-open-route keepouts.
5. Record central-opening incidence but allow it only as an explicit
   flex-opening merge diagnostic.
6. Stop read-only at `V27_C9_LANDING_FAMILY_CHECKPOINTED`,
   `V27_C9_LANDING_CLEARANCE_SOLVED`, or
   `V27_NO_VALID_C9_LANDING_CLEARANCE`.

Stage 2c may write JSON/text evidence only. It must not mutate a mesh, emit
candidate geometry, save a Blend, request image work, run Gates B/D, or
promote anything.

### V27-LANDING-001 — landing solver authorized

- started_from_commit: `fb212dd`
- planned_script: `scripts/blender/analyze_v27_c9_landing.py`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: materialize the read-only finite landing solver and identify
  the minimum-displacement exact-clearance endpoint pair

### V27-LANDING-002 — C9 landing clearance solved

- timestamp_utc: `2026-07-30T03:07:44Z`
- script: `scripts/blender/analyze_v27_c9_landing.py`
- authority: `v27_c9_landing_authority.json`
- receipt: `v27_c9_landing_authority_receipt.json`
- result: `V27_C9_LANDING_CLEARANCE_SOLVED`
- finite_family_member_count: `11,250`
- evaluated_member_count: `3,727`
- selected_member_index: `3,726`
- selected_endpoint_offsets_mm: `[4, 8]`
- selected_common_direction:
  `[-0.43621088003759323, -0.8956946816447896, -0.08631978573923607]`
- selected_moved_endpoint_coordinates_mm:
  - vertex `1541`:
    `[129.75852867223244, -58.06972101783892, -79.26974050770303]`
  - vertex `1543`:
    `[146.08819381907426, -70.54518086624425, -56.58676037331623]`
- exact_minimum_segment_cutter_distance_mm: `2.012107006124184`
- minimum_signed_sample_margin_mm: `2.0413452591747046`
- edge_length_ratio: `1.0003974793505002`
- source_complement_hit_count: `0`
- terminal_hit_count: `0`
- protected_nonflex_keepout_hit_count: `0`
- flex_opening_merge: the candidate intersects nine recorded
  central-opening cells; this is explicit intended flex-opening incidence,
  not permission to fill the opening
- code_sha256:
  `3f87ef5e1bfe63be6a094d9db42fa68a335d1dfa9e22de86bc735f5d721e29b0`
- family_fingerprint:
  `b36e91661ae9be29d28217b65e8a1d5f8028f6d29ab0642579615a205321dfde`
- selection_fingerprint:
  `cd1f20883f0edfdef9548e153bc8fce344e2bbc356db7eb28f55329c7d900ddf`
- authority_sha256:
  `c2529003261cf0f086c6de01bb700474fc6dfa3c016e03671cf928effa79dfc6`
- receipt_sha256:
  `e947c383ab4d093a0274160c4d7faa83df1ea4efd98bd36b5134a59807bb285a`
- semantic_fingerprint:
  `a0a4ea1383c378f0cbc18b544108e393817a217da09f4f6c52e163eaf6f3e455`
- repeatability: `DONE`; two default-path background-Blender executions
  produced byte-identical authority and receipt hashes
- named_audit: `PASS_V27_C9_LANDING_AUTHORITY_AUDIT`
- rejection_counts_before_selection:
  - cutter clearance: `3,696`
  - protected negative space: `5`
  - source complement: `25`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: evaluate the complete 11-face landing surface produced by this
  endpoint relocation for triangle orientation, distortion, edge stretch,
  exact cutter clearance, and complement/keepout collisions before any mesh
  mutation or Blend save

### V27-LANDING-003 — direct 11-face deformation rejected

- timestamp_utc: `2026-07-30T03:12:09Z`
- operation: move only endpoint vertices `1541` and `1543` to the reviewed
  Stage 2c coordinates in memory, preserving the source triangulation, and
  audit every triangle and affected edge in the exact 11-face one-ring
- script: `scripts/blender/analyze_v27_c9_landing_surface.py`
- first_execution_result: `V27_C9_LANDING_DIRECT_SURFACE_REJECTED`
- first_execution_code_sha256:
  `a9a471b7b21332301a6e981b29be9dd2720c8bb0a165f6d249da9266254c64d8`
- first_execution_authority_sha256:
  `2872540f60a9f82d0931d151c13011dfa08e3b3ce323be54317e4fce80a94d65`
- first_execution_receipt_sha256:
  `80dcf07c6e43111b3b684a7ca9e924d3412bbba74d35ac1f1929f6d3ce3a8dd3`
- first_execution_semantic_fingerprint:
  `6cd3935f720b7c1b4dc09c661446d62f4da9fa0789824badac02cb0d649f64b0`
- candidate_fingerprint:
  `23d356cf70f556fd0c15ab63e8bbd51e56c91b4c7ca4ab443908e00a523c9659`
- flipped_triangle_count: `5`
- flipped_faces: `[2231, 2235, 2239, 2240, 2244]`
- minimum_source_normal_dot: `-0.7963564321398735`
- affected_edge_ratio_range: `[0.9205596160481258, 2.3797866395854035]`
- over-stretched_edge: source edge `2955`, vertices `[1537, 1543]`,
  ratio `2.3797866395854035`
- maximum_triangle_aspect_ratio: `11.71642660293299`
- cutter_rejecting_triangle_count: `9`
- minimum_exact_triangle_cutter_clearance_mm: `0.0`
- minimum_signed_sample_margin_mm: `-19.07624626159668`
- self_intersection_conflict_count: `0`
- provisional_absolute_complement_overlap_count: `45`
- audit_correction_required: the first complement check records absolute patch
  overlap against the complete source complement. Because the frozen source
  can contain pre-existing cross-component contacts, the final complement
  claim must compare the original patch and candidate patch and reject only
  new overlap pairs or worsened witnesses. The provisional absolute count is
  retained as implementation evidence but is not independently used to
  characterize the direct deformation.
- controlling_rejections_independent_of_that_correction: five flipped
  triangles, one edge above the existing `2.0` stretch bound, and nine
  triangle-level cutter failures
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: add baseline-delta overlap evidence, repeat the authority, and
  then enumerate a distributed landing-surface family rather than retrying the
  rejected two-vertex drag

### V27-LANDING-004 — corrected direct-surface authority checkpointed

- operation: repeat V27-LANDING-003 with original-versus-candidate overlap
  deltas so pre-existing source contacts are retained as baseline evidence
  instead of being mislabeled as reconstruction regressions
- result: `V27_C9_LANDING_DIRECT_SURFACE_REJECTED`
- authority: `v27_c9_landing_surface_authority.json`
- receipt: `v27_c9_landing_surface_authority_receipt.json`
- code_sha256:
  `a40c07eb48537f019ddbcd04fa2abea713d4bd0762ac6ae19a85846c19d12f99`
- authority_sha256:
  `a1fbd4f844e423823a4852e0b6ecdaa9927069f0a013dc859d13d344891961e4`
- receipt_sha256:
  `dc26f4bfb4faa67ae5be0f930e304cfc68559950b5bcc8dd5c6b05e809cab59d`
- semantic_fingerprint:
  `dc811fc430dd82c6d51db54cf01e22f773a8c0712dd906c130134f868c2edd02`
- candidate_fingerprint:
  `23d356cf70f556fd0c15ab63e8bbd51e56c91b4c7ca4ab443908e00a523c9659`
- complement_overlap_delta:
  - baseline conflict pairs: `29`
  - candidate conflict pairs: `45`
  - new conflict pairs: `28`
  - resolved conflict pairs: `12`
  - retained conflict pairs: `17`
- self_overlap_delta:
  - baseline conflict pairs: `1`
  - candidate conflict pairs: `0`
  - new conflict pairs: `0`
- controlling_rejections:
  - five flipped triangles, on faces
    `[2231, 2235, 2239, 2240, 2244]`
  - source edge `2955` stretched to ratio `2.3797866395854035`
  - nine of eleven patch triangles fail the exact/signed cutter contract
  - 28 new source-complement intersection pairs
- repeatability: `DONE`; two final background-Blender executions produced
  byte-identical authority and receipt hashes
- named_audit: `PASS_V27_C9_DIRECT_SURFACE_AUTHORITY_AUDIT`
- mutation_started: false
- geometry_emitted: false
- blend_saved: false
- images_requested: false
- promotion: `NOT_PROMOTED`
- next_action: enumerate a finite distributed one-ring surface family with
  interior/control displacements shared across the landing patch; do not retry
  the endpoint-only deformation

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
