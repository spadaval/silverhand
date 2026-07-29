# Silverhand — Current Status

Updated: 2026-07-29

## Active milestone

Create a source-faithful, anatomically human-sized wrist-to-upper-bicep
**fitted surface master** in the straight construction pose.

Current work is limited to source/anatomical landmarks, one shared deformation
field, matched-view review, anatomical clearance, and bounded visible
reconstruction. Personalized wearer tailoring, elbow mobility, local thickness,
structural junctions, armor-gap panels, magnet hardpoints, closure detail,
segmentation, and production exports follow after fitted-surface approval.

## Scene authority

Master: `reference/Johnny.blend`

The scene is millimeter-native and organized into:

| Collection | Role |
|---|---|
| `00_SOURCE_LOCKED` | immutable game, fitted, semantic, and comparison evidence |
| `10_FIT_TOOLS` | provisional fit reference and non-printable clearance cutter |
| `20_SALVAGE_WORKING` | retained 101-solid failed experiment; not the production starting point |
| `30_REVIEW` | disposable joined evidence of that processed baseline |
| `40_DEFERRED_ARMOR` | six registered armor sources; not print-ready |
| `90_VALIDATION_CAMERAS` | eight canonical semantic comparison cameras |

No active fitted surface candidate exists in the tracked master. Any promoted
candidate must be derived from `SRC_GAME_TPU_ONLY_BASELINE` without editing the
immutable source.
Objects under `20_SALVAGE_WORKING` must not be promoted or repaired as the new
master.
`EVAL_MAIN_GEOMETRY_BASELINE` is review-only.

The validation cameras are persistent review infrastructure. They do not belong
to the printable object graph and may be deterministically repaired with
`scripts/tools/sync_validation_cameras.sh`.

## Static-fit prototype evidence

An ignored local experiment now exists at:

- `blender_files/Johnny_static_fit_prototype.blend`

It is reproducible with `scripts/blender/build_static_fit_prototype.py`. The
script recovers the provided anatomical right arm from the verified pre-cleanup
checkpoint, derives a straight anatomical fit reference and cutter, duplicates
`SRC_GAME_TPU_ONLY_BASELINE`, and stores the deformation in the
`STATIC_ANATOMICAL_FIT` shape key. The source remains the untouched Basis.

The selected experimental pass uses one low-frequency station-angle source
baseline and one monotonic radial mapping. It preserves all `7,347` vertices,
`19,876` edges, `12,564` faces, polygon indices, material slots, and material
assignments. It does not split, delete, solidify, Boolean, remesh, or move
individual components.

This candidate is **not promoted**:

- topology invariants pass, but full transformation-integrity review remains
  open;
- the matched contact sheet is much more coherent than the rejected processed
  baseline and has no exploded registration;
- bicep/shoulder mass and axial depth remain visibly altered;
- `743` vertices remain inside the anatomical cutter, with a minimum margin of
  `-49.514 mm`;
- cutter intersections affect `19` of the source's `64` connected components;
- `30` triangulated faces are orientation-review locators and the long
  distortion tail remains unresolved.

The station-only alternative reduced the failure to six components and
`-11.754 mm`, but visibly inflated the whole sleeve. Strong asymmetric radial
compression reduced the vertex failure to `16` vertices within `-0.956 mm`,
but flattened too much axial depth. Both are rejected as automatic fixes.

Evidence:

- `_validation/static_fit_prototype/iteration_6/build_report.json`
- `_validation/static_fit_prototype/iteration_6/comparison/comparison_contact_sheet.png`
- `validation_reviews/static_fit_prototype/review.json`

## Bounded fragment rescue evidence

The first clearance-rescue pass is preserved in the ignored local experiment:

- `blender_files/Johnny_fragment_rescue_work.blend`

Before the experiment, the tracked master and static-fit prototype were copied
to:

- `blender_files/archive/Johnny_pre_fragment_rescue_20260727_221837.blend`
- `blender_files/archive/Johnny_static_fit_pre_fragment_rescue_20260727_221837.blend`

The retained rescue is a second reversible shape key,
`FRAGMENT_RESCUE_CLEARANCE`, relative to `STATIC_ANATOMICAL_FIT`. It uses a
global `5 mm` maximum hard lift, a three-edge falloff, and a topology-driven
orientation deferral rule. It does not delete, split, remesh, solidify, Boolean,
or independently translate connected components.

Results:

- topology remains exactly equal to the source;
- `566` of `999` reserved-wall failures were cleared;
- actual cutter penetrations fell from `743` to `424`;
- no pre-rescue-to-rescue negative-orientation locators remain;
- the matched pre-rescue/rescue contact sheet shows no new exterior silhouette
  damage, spikes, or flattened carrier-like slabs;
- `395` deep vertices were deferred by the `5 mm` lift limit and `40` vertices
  were deferred by the orientation rule;
- `1,051` cutter triangle overlaps and a `-46.575 mm` minimum margin remain, so
  anatomical clearance still fails and this object is not promoted.

This pass proves that shallow local failures can be salvaged without repeating
the destructive global clearance strategies. The remaining failures are not
appropriate for further automatic radial lifting; they require bounded
classification and reconstruction.

Evidence:

- `_validation/fragment_rescue/iteration_10/build_report.json`
- `_validation/fragment_rescue/iteration_10/pre_vs_rescue/comparison_contact_sheet.png`
- `validation_reviews/fragment_rescue/review.json`

## Rejected deep-clearance experiments

Direct Boolean subtraction against `CUT_CLEARANCE_ANATOMY_STRAIGHT` is rejected
for the current open fitted surface:

- normal Exact mode grafted cutter walls and caps into the result;
- hole-tolerant Exact mode tore visible holes and still left `932` cutter
  overlaps;
- a `1 mm` Voxel Remesh made the generated pieces manifold but produced
  `3,409` thin solids; subtraction then removed almost the entire visible arm
  and left `92` disconnected solids.

These trials are preserved only in ignored local Blender files and generated
validation evidence. The tracked master and retained rescue candidate were not
changed. A Boolean cutter becomes viable only after a bounded region has been
classified and reconstructed as a coherent volume.

## Deep-fragment pilot evidence

Two ignored local pilot scenes compare vertex deletion, rigid translation,
uniform radial offset, radial-depth compression, and a procedural masked
displacement field:

- a borderline component with only two violating vertices can be cleared by
  the masked field without a perceptible exterior change;
- the selected deep wrist component has `40` vertices, `15` cutter
  penetrations, and a `-11.748 mm` minimum margin;
- deleting its violating vertices removes `15` vertices and `33` of its `65`
  faces;
- uniform radial offset inflates it, while masked displacement and radial-depth
  compression visibly crush its axial profile;
- a `15.2 mm` rigid lift preserves the fragment but breaks local registration
  when applied to that component alone.

A final spatial-field trial applied the same rigid motion to nearby geometry
with smooth `25 mm` and `40 mm` falloffs. The `25 mm` field is the least
destructive deep-failure result so far: it preserves the pilot fragment,
affects `493` nearby vertices, and reduces total cutter penetrations from `424`
to `401`. The `40 mm` field affects `1,085` vertices and creates new
reserved-margin failures.

No deep-fragment variant is promoted. The useful result is strategic: deep
failures should first be tested as bounded corrections to the shared regional
fit field. Isolated component repair remains a fallback only after neighboring
registration has been evaluated.

Evidence:

- `blender_files/Johnny_pilot_reconstruction_trials.blend`
- `blender_files/Johnny_pilot_reconstruction_component59_trials.blend`
- `_validation/pilot_reconstruction/iteration_2_component59/build_report.json`
- [Regional clearance-deformation approach](approaches/regional-clearance-deformation.md)

## Stepwise geometry-repair evidence

The active ignored repair scene is:

- `blender_files/Johnny_geometry_repair_work.blend`

It begins from the retained fragment rescue and stores each accepted change as
a reversible relative shape key. `REPAIR_001_COMPONENT_0` is retained as a
bounded shallow-clearance patch:

- two remaining penetrations are cleared;
- global cutter penetrations fall from `424` to `422`;
- reserved-margin failures fall from `433` to `431`;
- cutter triangle overlaps fall from `1,051` to `1,037`;
- source topology, face indices, and material assignments remain unchanged;
- no negative-orientation locators are introduced;
- local and complete high-detail review pages show no perceptible damage.

The patch does not promote the complete fitted surface. Two contracted local
edges remain recorded as later thickness/print-detail watch items.

`REPAIR_002_COMPONENT_1_REGIONAL` is retained as a second reversible candidate,
relative to Repair 001. Component `1` is a visible ventral mechanical plate
nested against component `25`, so isolated lifting, deletion, masked radial
displacement, and depth compression were rejected. A shared `35 mm` regional
field moves the plate through an `8.2 mm` rigid core correction and blends the
same motion through nearby source geometry:

- all `8` component-1 penetrations are cleared;
- global cutter penetrations fall from `422` to `397`;
- reserved-margin failures fall from `431` to `411`;
- cutter triangle overlaps fall from `1,037` to `978`;
- topology and material assignments remain unchanged;
- component `1` remains approximately `0.277 mm` from component `25`;
- no negative-orientation locators are introduced;
- local and complete high-detail review shows no perceptible registration or
  silhouette damage.

The field affects `1,471` weighted vertices and its affected-edge ratios range
from `0.723772` to `1.312896`. It remains a fitted-surface candidate and does
not establish a general automatic regional-lifting rule.

Three additional hidden-side repairs are retained as reversible relative shape
keys:

| Repair | Component | Cutter vertices cleared | Global overlaps before → after | Visible result |
|---|---:|---:|---:|---|
| `REPAIR_003_COMPONENT_25_MASKED` | 25 | 29 | 978 → 885 | visible cradle preserved; displaced surface is buried |
| `REPAIR_004_COMPONENT_37_MASKED` | 37 | 7 | 885 → 870 | exposed cable curve preserved; distorted endpoint is buried |
| `REPAIR_005_COMPONENT_42_MASKED` | 42 | 7 | 870 → 837 | exposed upper-arm composition preserved; displaced branch is buried |

Together, Repairs 003–005 reduce cutter penetrations from `397` to `354` and
reserved-margin failures from `411` to `365`. They preserve all source
vertices, faces, polygon indices, and material assignments, and introduce no
negative-orientation locators. The active work scene is checkpointed after
each retained repair.

These are fitted-surface repairs, not printable-solid approval. Component `25`
has five hidden edges contracted below half length; component `37` has three
such edges plus one edge expanded to `2.088288`; component `42` has one edge
contracted to `0.448621`. Those buried regions are explicit later
solidification watch items.

Eight further repairs are retained as reversible candidates after independent,
sanitized, high-detail local and complete matched-view review:

| Repair | Component | Method | Global cutter vertices before → after | Global overlaps before → after |
|---|---:|---|---:|---:|
| `REPAIR_006_COMPONENT_20_MINOR_PATCHES` | 20 | six-ring harmonic field over minor clusters 2–5 | 354 → 336 | 837 → 806 |
| `REPAIR_007_COMPONENT_16_HARMONIC` | 16 | eight-ring harmonic field | 336 → 334 | 806 → 792 |
| `REPAIR_008_COMPONENT_52_REGIONAL` | 52 | `35 mm` shared regional rigid field | 334 → 326 | 792 → 769 |
| `REPAIR_009_COMPONENT_57_REGIONAL` | 57 | `45 mm` shared regional rigid field | 326 → 309 | 769 → 741 |
| `REPAIR_010_COMPONENT_59_REGIONAL` | 59 | `40 mm` shared regional rigid field | 309 → 282 | 741 → 701 |
| `REPAIR_011_COMPONENT_36_REGIONAL` | 36 | `30 mm` shared regional rigid field | 282 → 278 | 701 → 692 |
| `REPAIR_012_COMPONENT_39_REGIONAL` | 39 | `25 mm` shared regional rigid field | 278 → 265 | 692 → 675 |
| `REPAIR_013_COMPONENT_19_CLUSTER_RIGID` | 19 | six-ring harmonic transition around one rigid cluster | 265 → 258 | 675 → 653 |

Repairs 006–013 preserve all source vertices, faces, face indices, and material
assignments and introduce no negative-orientation locators. Each bounded delta
answers `does_this_repair_delta_look_ass: false`. Component `16`, component
`19`, component `36`, component `39`, component `52`, component `57`, and
component `59` now have zero vertices below either the cutter or the reserved
wall. Repair 006 clears only the four minor component-20 clusters; `115`
component-20 vertices remain inside the cutter.

The active scene and its post-Repair-013 checkpoint are byte-identical at
SHA-256
`ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e`:

- `blender_files/Johnny_geometry_repair_work.blend`
- `blender_files/checkpoints/geometry_repair/post_repair_013_component_19_20260728.blend`

The earlier failed radial, compression, and isolated-lift trials for components
`19`, `36`, `39`, and `59` remain rejected. Repairs 010–013 supersede the
decision to park those components by using different bounded methods. The
component-19 cluster field is especially local: a `5.430353 mm` rigid motion
of seven core vertices is blended through only 53 affected vertices, with
edge ratios bounded to `0.827474–1.088134`.

Component `9` is also classified, but no geometry is retained from its trials.
It is a `2,508`-vertex structural surface spanning much of the wrist and
forearm, not one movable fragment. Its `163` penetrating vertices form six
clusters; the two dominant wearer-facing inner-wall clusters contain `86` and
`68` vertices at the proximal and wrist ends.

Whole-component movement, radial compression, uniform offset, and masked
projection are rejected. The nominal rigid lift creates `670` component-9
penetrations; compression introduces `11` reversed faces; uniform offset
introduces `9`; the ordinary masked field introduces `58`. Increasing masked
diffusion raises the failure to `90–125` reversed faces. Deleting the
penetrating vertices removes `466` interior faces and confirms that the outer
silhouette is mostly unaffected, but the resulting open lumen holes are not a
retained repair.

Component `20`, only `0.012323 mm` from component `9`, was originally
classified into six violation clusters. Repair 006 retains bounded harmonic
corrections for minor clusters 2–5. On the exact post-Repair-013 base, major
clusters 0 and 1 contain `87` and `31` reserved-margin failures and require
wearer-facing surface replacement. The former `32` count is stale: Repair
006's transition also cleared adjacent vertex `4860`.

The first cutter-derived replacement trials are not retained. An unbridged
patch splits the candidate from `64` to `68` connected components and raises
boundary edges from `1,756` to `1,929`. The best tested boundary bridge keeps
`64` components but still raises boundary edges to at least `1,785`; conforming
bridges raise them further. These trials prove the replacement location and
clearance effect, not a valid transition topology.

A boundary-count-preserving strip then met those numerical topology bounds:
`64` connected components and `1,756` boundary/nonmanifold edges were
unchanged, no noncontiguous manifold edges appeared, penetrations fell from
`309` to `194`, and overlaps fell from `741` to `519`. It is nevertheless
rejected. Bicep-axial high-detail review shows that its `1,451`-face
cutter-conforming strip erases the source's stepped angular inner depth and
reads as a broad smooth carrier-like slab. It also retains `42` replacement
triangle overlaps.

Two relief-preserving deformation controls are also rejected numerically.
Pointwise projection of the original major-cluster vertices clears component
`20` but reverses `8–22` triangles and stretches one edge to `11.8664` times
its original length. Translating each major cluster rigidly before a harmonic
boundary blend requires `48.205661 mm` and `32.556071 mm` motions; every
tested transition reverses at least seven triangles, and the variants that
clear the clusters reverse `43–202`.

A component-proximity audit does not justify deleting component `20` as a
duplicate of component `9`. Only `2` of the `118` major-cluster vertices are
within `0.1 mm` of component `9`; the median nearest distance is
`10.186440 mm`. The two surfaces occupy similar stations and radii but
different angular locations around the lumen.

A closed-core topology trial isolates the smaller major cluster `1`. Its
original `87` faces and recognizable faceted relief are translated rigidly by
`32.556071 mm`, then connected to the unchanged source through a one-layer,
`60`-edge, `120`-triangle annulus. The trial preserves `64` connected
components, `1,756` boundary/nonmanifold edges, and contiguous winding, while
reducing penetrations from `309` to `296` and overlaps from `741` to `704`.
It is rejected visually. Dorsal and ventral high-detail review show the
annulus as a long triangular shelf/wall with spike-like projections that
crowds and partially bridges the intentional local gap. The translated core
itself preserves relief; the full-perimeter transition is the defect.

The next component-20 method must preserve the reviewed exterior boundary and
the source's angular inner relief, replace only the two major wearer-facing
patches, and avoid increasing boundary-edge or connected-component counts.
The next bounded trial should transfer the source ridge/depth landmarks as
outward relief on a cutter-safe base. Do not repeat pointwise projection, a
smooth cutter-only field, a harmonic blend of the full `32–48 mm` motion, or a
full-perimeter annulus around a translated core.

Repair 014 has now exhausted the bounded component-20-only reconstruction
scope through v21. A broad `6 × 2.4 mm` C9-clear frame corridor is numerically
recoverable, but neither bounded terminal approach can reach the retained
cage: every upper variant intersects source outside the four-face topology
allowlist, and every lower variant also intersects immutable component `9`.
No v21 topology was changed or geometry promoted. The immediate decision is
either a wider component-20 landing replacement or a joint
component-9/component-20 elbow-interface reconstruction.

The joint v22 attribution preflight is also complete without mutation. It
recovers exact C9/C20 overlap identities for all `30` bounded terminal
approaches, but every lower variant crosses `5–19` exterior-facing
component-20 faces; six also leave the proximal C9 wearer class. A local C9
channel alone is therefore not authorized. The next joint trial must
re-author the approach corridor from the exact attributed face evidence before
defining either component's topology mask.

The v23 free-space preflight also stops read-only. All `315` primary and
`315` exterior-C20-relaxed route tuples are blocked at the first `6 mm`
tangent-continuous scarf leaving the fixed B2b exit; no path reaches spline
fitting. The immediate numeric dependency is therefore a bounded B2b exit
trim/reauthoring, not a broader free-space search from the same portal.

The v24 B2b exit preflight exhausts that bounded dependency without mutation.
Exact trims at `R8`, `R7`, and `R6` clear the local departure but produce no
complete route; the `R5` trim cannot clear the required local `2 mm`
departure. Of `675` bounded R5/R6/R7 terminal-subsegment replacements, `62`
clear the local geometry gate and zero complete the unchanged v23 route
contract. The obstruction therefore extends upstream of the authorized
terminal subsegment. The next joint trial must re-author the earlier B2b/turn-
bridge corridor; repeating terminal-only exit changes is not justified.

The v25 authored-tail preflight exhausts that fixed upstream scope without
mutation. It evaluates all `11,907` escape tuples, retains `3,570` local
passes at `1,190` unique portals, and tests all `3,570` portal/endpoint routes.
Every route fails the necessary radius-`1.2 mm` inscribed-capsule search on
the same `4 mm` lattice, so none can contain the required
`4.5–6.0 × 2.4 mm` rectangular rail. The named stop is
`NO_SAFE_AUTHORED_TAIL_ROUTE_V25`. The next decision must deliberately expand
into B1 or beyond the `12 mm` B2a suffix authority, or choose a different
joint-interface architecture; another fixed-scope route iteration is not
justified.

The v26 static-interface preflight also closes without mutation. Exact
cutter, negative-space, floor-ownership, exposure, terminal, and five rounds
of disposable sanitized face-review authority establish valid upper and lower
boundary-coincident terminals, but the complete wearer-side demand requires
`23` exposure cells against v26's aggregate cap of `12`. Its truthful named
stop is `NO_SEED_COVERING_EXPOSURE_CELL_SUBSET_V26`; the cap and result remain
unchanged.

V27 now deliberately authorizes the aggregate `26`-cell C9/C20 wearer-side
interface reconstruction: the `23` seed-covering cells plus exact C20 terminal
dependency cells `007`, `009`, and `011`. It preserves the reviewed visible
complement, intentional `NO_FLOOR` openness, exact negative space, a
`>=12 mm` flex gap, exact terminals, and `>=1.7 mm` cutter clearance. The
`<=12`-cell limit survives only as a checkpoint/recovery batch bound. The
first milestone is a read-only, hash-verified aggregate mask and dependency
DAG; surface construction cannot begin until the flex gap is solved, and
solids, motion, yokes, TPU, and Gates E/F/G remain deferred.

Component `9` follows with the same bounded classification principle; do not
reconstruct coincident component-9 and component-20 inner layers twice.

The earlier shallow radial-patch method remains rejected for components `16`,
`19`, and `52`: component `16` visibly narrows, component `19` introduces a
flipped triangle, and component `52` produces severe edge collapse/stretch
plus two flipped triangles. Repairs 007, 008, and 013 supersede those failed
methods without invalidating the rejection lessons.

Only components `9` and `20` remain offending. Neither qualifies for further
shallow automatic lifting; each requires bounded wearer-facing reconstruction.

Evidence:

- `validation_reviews/geometry_repair/classification.json`
- `validation_reviews/geometry_repair/repair_001_component_0/review.json`
- `_validation/geometry_repair/repair_001_component_0/`
- `experiments/geometry_repair/component_1_methods/README.md`
- `_validation/experiments/geometry_repair/component_1_methods/`
- `experiments/geometry_repair/component_25_methods/README.md`
- `experiments/geometry_repair/component_37_methods/README.md`
- `experiments/geometry_repair/component_42_methods/README.md`
- `experiments/geometry_repair/component_36_methods/README.md`
- `experiments/geometry_repair/component_39_methods/README.md`
- `experiments/geometry_repair/component_9_methods/README.md`
- `validation_reviews/geometry_repair/repair_005_checkpoint/review.json`
- `validation_reviews/geometry_repair/repair_006_component_20_minor/review.json`
- `validation_reviews/geometry_repair/repair_007_component_16_harmonic/review.json`
- `validation_reviews/geometry_repair/repair_008_component_52_regional/review.json`
- `validation_reviews/geometry_repair/repair_009_component_57_regional/review.json`
- `validation_reviews/geometry_repair/repair_010_component_59_regional/review.json`
- `validation_reviews/geometry_repair/repair_011_component_36_regional/review.json`
- `validation_reviews/geometry_repair/repair_012_component_39_regional/review.json`
- `validation_reviews/geometry_repair/repair_013_component_19_cluster_rigid/review.json`
- `validation_reviews/geometry_repair/component_20_boundary_r2_l16_o4/review.json`
- `validation_reviews/geometry_repair/component_20_relief_core_c1_l1/review.json`
- [Component 20 landmark-sector reconstruction](approaches/component-20-landmark-sector-reconstruction.md)

## Cleanup baseline

- 170 objects
- 160 mesh datablocks
- 16 collections
- 8 validation cameras and no curve or image datablocks
- 101 closed salvage solids
- 31 reversed salvage solids repaired to positive orientation
- all geometry converted from centimeters to millimeters
- legacy sleeve, V2/V3/V4, coupon, reimport, and embedded 3MF collections removed
- unused datablocks purged

Recoverable local checkpoints:

- `blender_files/archive/Johnny_pre_cleanup_20260727.blend`
- `blender_files/archive/rework_evidence_pre_cleanup_20260727.tar.gz`

## What the scene proves

- The clean armor-stripped source preserves the intended wrist, forearm, elbow,
  upper-arm composition, longitudinal rails, cables, layered masses, and
  negative spaces.
- The processed 101-solid experiment is recoverable and measurable.
- The prior straight fit reference reported no triangle intersections.
- The current clearance audit reports zero cutter intersections and zero tested
  vertices inside the cutter across all 101 working solids.
- Each retained editable form is locally closed and consistently oriented.

## Why the processed baseline is rejected

The matched contact sheet shows exploded component placement, damaged source
registration, severe bicep/shoulder compression, unexpected warping, and
floating fragments. It fails the qualitative main-geometry visual gate.

The archived generator combined a hard-coded straight-axis mapping, piecewise
longitudinal rescaling, radial-depth compression, eight independent forearm
sectors, collision-driven component lifting, face deletion, component pruning,
and local solidification. Its zero-clearance result and closed-shell reports do
not rescue the visible failure.

The current geometric contact graph reproduces 30 overlap groups and 18
isolated solids. The largest group contains 35 solids. These remain defects,
not accepted architecture or proof of slicer fusion. The baseline is historical
transformation evidence, not a salvage library for production.

## Known strategic debt

- The tracked master does not yet contain a promoted source-derived fitted
  surface candidate.
- The processed geometry was generated by an experimental centimeter-based
  script with a duplicated hard-coded fit profile and fails visual review.
- The old generator is archived, not active authority.
- The existing fit volume must be verified against the provided anatomical
  reference before it can govern the first fitted surface.
- Its extracted 77-ring profile is approximately 390 mm long, begins near
  `163.5 mm` circumference, and reaches only `295.7 mm`; this is below the
  recorded wearer measurements, but those measurements are later tailoring
  evidence rather than the current digital target.
- The inherited cutter is a consistent `2.5 mm` radial expansion, but shares
  surface triangles with the fit volume at its unexpanded end boundaries.
- The clean source elbow is composition evidence, not the final flex zone.
- Source islands must remain registered during fitting; pruning happens only
  after fitted-surface review.

## Immediate next work

1. Preserve Repairs 001–013 and the exact post-Repair-013 checkpoint with
   SHA-256
   `ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e`.
2. Resume from `blender_files/Johnny_geometry_repair_work.blend`.
3. For component `20`, replace only major clusters 0 and 1 with local
   wearer-facing surfaces that retain the source's stepped angular depth.
   Reject any transition construction that increases boundary-edge count,
   creates an additional component, or smooths the inner surface into a broad
   carrier-like field.
4. After component `20`, preserve component `9`'s exterior and rebuild only
   its two dominant wearer-facing patches. Do not rerun whole-component
   displacement or wider diffusion.
5. Delegate every image operation to a disposable subagent. Sanitize and size
   checkpoint every derivative before high-detail review; never replay
   unsanitized historical image outputs.
6. Repeat triangle-orientation, distortion, matched-view, and exact
   surface-clearance evidence after every bounded reconstruction.
7. Promote a fitted surface master only after qualitative visual and digital
   clearance review.
8. Begin hidden solidification and connectivity work only after that
    promotion.
9. Defer the approximately `30°` priority wear pose and broader elbow mobility
   until the static straight composition is accepted.

## Deferred decisions already recorded

- Clearance geometry is cutter-only.
- Tactical armor panels are local, never global.
- Major armor plans for magnet-to-magnet clamping plus mechanical registration.
- Velcro remains a smaller/flexible-part option.
- Exact attachment geometry requires later physical iteration.
