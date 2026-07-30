# Silverhand — Current Status

Updated: 2026-07-30

## Active milestone

Build a coarse, complete wrist-to-upper-bicep structural mockup from the
source-led fitted exterior already present in the tracked master.

The mockup must remain recognizably Silverhand. It should preserve the
mechanical silhouette, layered plates, rails, cables, hubs, armor voids, and
intentional open spans while adding only the minimum hidden structure needed
for clearance, donning, support, and eventual assembly.

This is a whole-arm architecture pass. Do not return to component-by-component
vertex repair or replace the exterior with a generic anatomical carrier.

## Tracked authority

Master:

- file: `reference/Johnny.blend`
- SHA-256:
  `e837fa51c98ce258a56dabb2aecfd7cc7d9e79bc29203f5aaacd0fca8cb4a218`
- units: millimeters
- objects: `76`
- meshes: `65`
- collections: `10`
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

## What remains unresolved

### Whole-arm structure

- No complete permanent load path exists.
- Retained source sheets are not globally closed printable solids.
- The current local prototypes are not integrated into the source exterior.
- Large armor voids have not been classified with the armor shown in place.

### Wearability

- No concealed medial donning closure exists.
- No personalized wearer-fit pass exists.
- No physical comfort or fatigue authority exists.

### Elbow

- The straight scene makes no motion claim.
- The open hub/strut/cable composition must remain recognizable.
- The flex zone and both transitions require a deliberate architecture.

### Manufacturing

- No final thickness map exists.
- No structural junctions or armor hardpoints are approved.
- No A1 mini segmentation or weld plan exists.
- `exports/current/` remains empty.

## Immediate next work

1. Create one disposable whole-arm structural mockup from the tracked fitted
   candidate; do not rebuild the exterior from generic panels.
2. Review the six armor references in place and classify each visible void as
   intentional negative space, armor-covered space, or a genuine support need.
3. Preserve source-led hero forms and broadly remove only unusable hidden
   wearer-facing sheets.
4. Add a clean wrist interface, a simple concealed medial opening, local
   forearm/bicep supports, and an explicitly open elbow architecture.
5. Evaluate the entire arm for silhouette, clearance, donning, permanent
   connectivity, and obvious injury risks before refining any local region.
6. Only after that whole-arm pass, refine from wrist to bicep in broad
   appearance and engineering passes.

## Recovery

- Git tag before repository simplification:
  `pre-repo-cleanup-20260730`
- retained complete local checkpoint:
  `.work/archive/pre_repo_cleanup_20260730/latest_full_v28_checkpoint.blend`
- retained checkpoint SHA-256:
  `c1bcf11610bb739aca9579e18b1320b026af2c525d4bfd7eec9ca1111eac1c5b`

The recovery checkpoint includes historical review objects and the retired
coupon. It is archive evidence only and must not replace the simplified master.
