# Silverhand — Current Status

Updated: 2026-07-28

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

1. Generate explicit review masks for the remaining penetrations across the
   `14` still-intersecting components.
2. Classify each masked region as visible source surface, removable prosthetic
   interior, or bounded reconstruction.
3. Rework the deep wrist pilot as a bounded shared regional deformation,
   starting from the `25 mm` falloff trial and reviewing registration against
   adjacent source landmarks.
4. If regional deformation cannot preserve the wrist composition, rebuild only
   the pilot's hidden/interior surface while preserving its visible boundary.
5. Preserve the accepted shallow rescue mask; do not continue automatic radial
   lifting beyond its `5 mm` and orientation limits.
6. Reconstruct the larger shoulder, elbow, wrist, and embedded failures only
   after the pilot establishes a reviewable method.
7. Repeat triangle-orientation, distortion, matched-view, and exact
   surface-clearance evidence after every bounded reconstruction.
8. Promote a fitted surface master only after qualitative visual and digital
   clearance review.
9. Begin hidden solidification and connectivity work only after that promotion.
10. Defer the approximately `30°` priority wear pose and broader elbow mobility
   until the static straight composition is accepted.

## Deferred decisions already recorded

- Clearance geometry is cutter-only.
- Tactical armor panels are local, never global.
- Major armor plans for magnet-to-magnet clamping plus mechanical registration.
- Velcro remains a smaller/flexible-part option.
- Exact attachment geometry requires later physical iteration.
