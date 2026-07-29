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
  `23` V26 wearer-facing exposure cells:
  - C20: `000`, `002`, `003`, `004`, `005`, `006`, `008`, `010`, `012`,
    `013`, `017`, `018`, `020`, `021`, `022`, `023`, `028`, `029`.
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

1. the `23` exact exposure cells;
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
the frozen `23` cell memberships, contains no immutable face, and gives every
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

After all `23` cells are represented, rerun Gate B and Gate D from the frozen
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
2. derive the exact `23`-cell aggregate face mask and immutable complement;
3. emit the deterministic dependency DAG, SCCs, and `<=12`-cell batch order;
4. prove unique membership, exact terminal incidence, keepout incidence, and
   `NO_FLOOR` exclusion; and
5. write repeat-identical machine-readable authority and a concise receipt.

It must stop at `V27_AGGREGATE_MASK_AND_DAG_CHECKPOINTED`. It must not solve
the gap, generate geometry, request images, mutate a mesh, or save a Blend.

