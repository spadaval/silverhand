# Silverhand — Retained History

This document records method boundaries that should influence future work.
Detailed scripts, generated reports, and intermediate scenes were removed from
the active tree on 2026-07-30. They remain recoverable at Git tag
`pre-repo-cleanup-20260730`; the complete latest local checkpoint is listed in
`docs/status.md`.

## Rejected carrier-backed generations

Early V2/V3/V4 workflows converted the game arm into many independently fitted
closed solids. The result passed several local mesh checks but failed as a
whole:

- exploded component placement;
- damaged source registration;
- shoulder and bicep compression;
- warped or floating details;
- loss of important negative space;
- no credible permanent load path.

Lesson: closed solids and zero cutter intersections do not establish a coherent
wearable arm. Do not resurrect the 101-solid carrier-free baseline as production
geometry.

## Shared-field anatomical fitting

A single reversible station/angle deformation kept all `64` disconnected
source constituents registered and preserved source topology. This was the
first recognizable anatomy-led result.

Global variants exposed an unavoidable tradeoff:

- broad radial expansion damaged mass distribution;
- asymmetric compression flattened mechanical depth;
- aggressive projection ironed layered forms onto the cutter;
- independently moving connected components destroyed registration.

Lesson: a shared field is useful for broad proportion and registration, but it
cannot create a human lumen through every deep prosthetic layer. Preserve the
coherent exterior and re-engineer only the wearer-facing failures.

## Bounded shallow clearance repair

Small penetrations responded well to reversible regional fields with explicit
lift and orientation limits. Repairs 001–013 retained recognizable nested
plates, cables, wrist details, hooks, braces, and upper-arm forms while clearing
their selected shallow failures.

Lesson: bounded regional corrections are appropriate when motion is small and
the source landmark remains visually coherent. They are not a universal
workflow and should not become a component-by-component repair queue.

## Deep Boolean and cutter-derived surfaces

Boolean subtraction against open source sheets produced ambiguous cutter walls,
new caps, tears, and increased non-manifold topology. Broad cutter-conforming
replacement strips produced smooth carrier-like slabs that erased the source's
stepped depth.

Lesson: the cutter may reject geometry or govern bounded subtraction. It must
not generate the visible exterior or a global hidden sleeve.

## Component 9/20 micro-repair exhaustion

The two largest problem components span almost the whole arm:

- component 9: approximately `0–293 mm`;
- component 20: approximately `230–419 mm`;
- together: about `53%` of all source faces.

V4–V27 tried progressively wider rails, patches, cages, saddles, landing
surfaces, gap families, and topology partitions. The work demonstrated several
hard limits:

- required local translations reached roughly `32–48 mm`;
- harmonic transitions reversed faces;
- rigid cores could not reconnect safely;
- broad annuli crowded or bridged intentional gaps;
- cutter-shaped patches lost recognizable relief;
- diagnostic face partitions did not produce credible production panels.

Lesson: treating giant wrapped components as individual repair units turns an
architectural problem into endless vertex work. Do not resume those versioned
families.

## V28 wearer-side prototypes

V28 discarded the idea that the hidden game topology must become the wearable
surface. It authored three clean local wearer-side panels from fit-reference
measurements while using the cutter only for clearance.

The retained result established:

- three closed positive-volume local solids;
- provisional `1.6 mm` outward wall;
- preserved local opening and seams;
- complete cutter clearance for the evaluated prototype region;
- live `0.4 mm`, two-segment rim bevels;
- no evaluated self- or cross-panel overlaps.

Lesson: clean hidden engineering geometry is feasible. It must remain visually
subordinate to the source exterior and must not expand into a generic whole-arm
carrier.

## Retired wall/rim coupon

The curved V28 wall/rim coupon was digitally valid and exported correctly. It
was retired because a generic curved cylinder fragment would mostly validate a
normal TPU printer profile, not the Silverhand arm. Future physical tests should
combine representative compound curvature, a real edge, a seam or opening, and
a structural or armor junction.

## Repository simplification

On 2026-07-30:

- the post-Repair-013 fitted candidate and accepted V28 live-bevel prototypes
  were consolidated into `reference/Johnny.blend`;
- the rejected 101-solid baseline and accumulated review objects were removed
  from the master;
- V4–V28 experimental scripts and generated authority dumps were removed from
  the active branch;
- local work moved to one ignored `.work/` hierarchy;
- the next milestone changed from local repair to a whole-arm structural
  mockup.

The migration receipt is
`validation_reviews/repository_cleanup/master_promotion.json`.
