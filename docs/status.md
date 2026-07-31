# Silverhand — Current Status

Updated: 2026-07-30

## Active milestone

Turn the accepted coarse wrist-to-upper-bicep solid mockup into a deliberate
worn assembly: establish its minimum permanent load path, donning strategy,
touch-safe wearer openings, and A1 mini segmentation without replacing the
source-led exterior with a generic carrier.

The mockup must remain recognizably Silverhand. It should preserve the
mechanical silhouette, layered plates, rails, cables, hubs, armor voids, and
intentional open spans while adding only the minimum hidden structure needed
for clearance, donning, support, and eventual assembly.

This remains a whole-arm architecture pass. Do not return to
component-by-component vertex repair or replace the exterior with a generic
anatomical carrier.

## Tracked authority

Master:

- file: `reference/Johnny.blend`
- SHA-256:
  `ab57ad38c4b88afecac86889ee145d8acd88774fb2799b79ce8c4acc6c64976f`
- units: millimeters
- objects: `160`
- meshes: `149`
- collections: `13`
- cameras: `8`
- images: `0`

The 2026-07-30 master promotion is recorded in
`validation_reviews/repository_cleanup/master_promotion.json`.

### Scene collections

| Collection | Authority |
| --- | --- |
| `00_SOURCE_LOCKED` | immutable game, fitted, comparison, component, and anatomy evidence |
| `10_FIT_TOOLS` | fit references and non-printable clearance cutters |
| `20_FITTED_SURFACE` | current source-led whole-arm fitted candidate |
| `25_ENGINEERING_PROTOTYPES` | accepted local wearer-side engineering prototypes |
| `30_EDITABLE_MAIN_GEOMETRY` | accepted V03 coarse solids, split into structural-network and post-print-detail children |
| `40_DEFERRED_ARMOR` | six registered rigid-armor references; not print-ready |
| `90_VALIDATION_CAMERAS` | canonical matched-view cameras |

The rejected 101-solid carrier-free baseline and accumulated `EVAL_*` review
objects are no longer present in the active master.

## Whole-arm fitted candidate

`WORK_FITTED_SURFACE_CANDIDATE` is the current source-led starting point.

- geometry/shape-key fingerprint:
  `70f1f224b0c8be72abfba6bd3c0ce341c5685e3c541fb17bede0d59dcd8c95d3`
- source topology: `7,347` vertices and `12,564` faces;
- all `64` source constituents remain registered;
- source materials and topology are preserved;
- retained reversible controls include the static anatomical fit, shallow
  fragment rescue, and Repairs 001–013;
- `printable=false`;
- `print_ready=false`.

This candidate preserves the recognizable overall composition much better than
the removed carrier-free baseline, but it is still open source surface
geometry. It has no wearability, motion, solid-construction, or print claim.

The evaluated 2026-07-30 anatomical-clearance audit reports `653`
surface-triangle intersection pairs and `255` candidate vertices inside
`CUT_CLEARANCE_ANATOMY_STRAIGHT`. These are known whole-arm clearance defects,
not a promotion pass. The retained shape keys and repairs are active in that
measurement.

## Accepted experimental solid mockup

The current experimental authority is:

- file: `reference/Johnny.blend`;
- collection: `30_EDITABLE_MAIN_GEOMETRY`;
- promoted source checkpoint:
  `.work/runs/full_prototype_v03_solid/full_prototype_v03_candidate_roles_classified.blend`;
- SHA-256:
  `0c09e5230daabdbd05e1c7ffb7798726fda5ff04aea3938726de49a91a46f13e`
  for the promoted source checkpoint;
- active printable-intent constituents: `84`;
- topology-and-clearance result: `PASS`;
- visual result: `KEEP`;
- `does_this_look_ass: false`.

All `84` constituents are closed, manifold, positive-volume solids with zero
clearance-cutter triangle intersections and zero vertices inside the cutter.
The candidate preserves the source-led wrist-to-bicep silhouette, armor voids,
open elbow, cables, rails, separated panels, and wearer openings.

Gross even-offset solidification failures have been removed. Source components
`3` and `7` use bounded non-even, angle-clamped solidification; components
`51` and `53` are quarantined as non-hero artifacts. The accepted fitted
distal-forearm patch remains active.

Two accepted bounded local junctions now attach the formerly detached dorsal
bicep hero shell to the dominant structural group. They form a small
two-strut bracket on the external shell boundary, preserve the split-bicep
void, and do not enter the wearer opening.

This is accepted **editable main geometry** in the tracked master, not a
connected master or print candidate. The promotion preserved all `76`
preexisting master objects, added zero image datablocks, and is recorded in
`validation_reviews/v03_editable_main/promotion.json`.

### A1 mini segmentation evidence

A non-promoted segmentation experiment replaces only `V03_MAJOR_0` and
`V03_MAJOR_1` with four capped transverse segments:

- file:
  `.work/runs/full_prototype_v03_solid/full_prototype_v03_candidate_segmented.blend`;
- SHA-256:
  `069a4150e9d76cf593ca7bf893494b33eb53f8034bcb2849abbd9e8ea6146162`;
- segment longest PCA extents: `173.009`, `143.665`, `162.425`, and
  `150.494 mm`;
- topology-and-clearance result: `PASS`;
- visual result: `KEEP`;
- `does_this_look_ass: false`.

All `61` structural constituents now have a demonstrated PCA-oriented
preflight fit inside the `180 mm` cube. The two seams preserve the silhouette,
hero details, open elbow, wearer openings, fitted patch, cables, and bicep
bracket. This is bed-fit geometry evidence only; it has no joint-strength,
tolerance, slicer, or physical-process claim.

## Retained wearer-side prototypes

`25_ENGINEERING_PROTOTYPES` contains:

- `PROTOTYPE_V28_WEARABLE_PANEL_0`
- `PROTOTYPE_V28_WEARABLE_PANEL_1`
- `PROTOTYPE_V28_WEARABLE_PANEL_2`

Each object is a closed positive-volume local prototype derived from the
accepted V28 wearer-side experiment. Each retains a live, unapplied
angle-limited Bevel modifier:

- width: `0.4 mm`;
- segments: `2`;
- profile: `0.5`;
- provisional wall: `1.6 mm`.

These objects demonstrate one viable hidden-panel construction method for a
roughly `62.5 mm` difficult region. They are engineering evidence, not the
visual language for the complete arm and not production geometry.

The generic curved wall/rim coupon was retired. It was valid geometry but did
not test a sufficiently representative arm feature to justify blocking work.

## What the current model proves

- The intact source-led exterior can remain registered through broad
  anatomical fitting.
- Most recognizable plates, cables, rails, hooks, and layered forms can survive
  as the visible design.
- Difficult wearer-side surfaces can be replaced with closed local solids
  without using the cutter as visible geometry.
- Reversible edge softening can remain live without invalidating the three
  retained prototypes.
- The project does not require a smooth visible backing sleeve.
- The complete source-led composition can be converted into individually
  closed, cutter-clear positive solids without the catastrophic fins produced
  by unbounded even-offset miters.
- The repaired whole-arm solid mockup survives all eight canonical views
  without losing its hero silhouette or filling intentional negative space.

## What remains unresolved

### Whole-arm structure

- A dominant permanent printed-contact network exists, but no complete worn
  load path exists until the donning closure and later segment joins are
  defined.
- The accepted solid mockup has `20` geometric contact groups: one dominant
  `61`-object group, one four-object group, one two-object group, and `17`
  isolated objects.
- The remaining `23` detached objects are classified as post-print detail.
  They total only `0.503%` of candidate volume and do not drive the structural
  network.
- Deferred armor has now been classified in place: it explains tactical
  dorsal-forearm skin and local lateral-elbow hardpoint coverage only. It does
  not solve the elbow span, medial rail/cable attachments, or wearer closures.

### Wearability

- No concealed medial donning closure exists.
- No personalized wearer-fit pass exists.
- No physical comfort or fatigue authority exists.

### Elbow

- The straight scene makes no motion claim.
- The open hub/strut/cable composition must remain recognizable.
- The flex zone and both transitions require a deliberate architecture.

### Manufacturing

- Advisory thickness evidence exists, but no physical process minimum has been
  established.
- The two local dorsal-bicep junctions are approved for the coarse prototype;
  no armor hardpoints or additional junction process is approved.
- A1 mini segmentation geometry exists and is visually accepted. Its joint
  keys/tolerances, assembly access, weld/adhesive method, and slicer plan remain
  unresolved.
- `exports/current/` remains empty.

## Immediate next work

1. Add only the closure hardware and hidden support required
   for a durable worn load path. Preserve the open elbow and intended voids.
2. Apply reversible edge softening to the wearer openings and fitted-patch
   collar, then repeat the clearance and visual gates.
3. Define the accepted four-piece segmentation prototype's weld, fastener, or
   adhesive interfaces. Preserve assembly access around the lower elbow-side
   seam.
4. Refit the forearm plate and primary elbow armor only after main closure and
   flex architecture are stable.
5. After closure and segmentation are explicit, begin broad wrist-to-bicep
   refinement from the promoted editable geometry.

## Recovery

- Git tag before repository simplification:
  `pre-repo-cleanup-20260730`
- retained complete local checkpoint:
  `.work/archive/pre_repo_cleanup_20260730/latest_full_v28_checkpoint.blend`
- retained checkpoint SHA-256:
  `c1bcf11610bb739aca9579e18b1320b026af2c525d4bfd7eec9ca1111eac1c5b`

The recovery checkpoint includes historical review objects and the retired
coupon. It is archive evidence only and must not replace the simplified master.
