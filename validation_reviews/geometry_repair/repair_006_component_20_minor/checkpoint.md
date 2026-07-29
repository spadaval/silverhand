# Repair 006 component-20 minor-patches validation checkpoint

Mission: `geometry-repair-006-review`

Scope: independently validate only the qualitative delta from
`REPAIR_006_COMPONENT_20_MINOR_PATCHES`. This review does not promote the
fitted surface and must not modify model or repair source artifacts.

## Claims under validation

1. The local before/after delta introduces no silhouette break, registration
   drift, spike, slab, flattening, depth inversion, or neighboring-composition
   damage.
2. The complete-view before/after delta introduces none of those defects in
   the full arm composition.
3. Build-report topology, orientation, and distortion evidence is compatible
   with retaining the repair as a candidate.
4. `does_this_repair_delta_look_ass` can be answered explicitly from bounded,
   sanitized, reproducible evidence.

## Validation method

- Read `build_report.json` and the local/complete manifests as text evidence.
- Before each image operation, append the exact operation and paths here.
- Copy each required raster through `scripts/image_sanitization.py` /
  ImageMagick to an owned sanitized-review directory.
- Verify every derivative is at most 10,000,000 bytes before inspection.
- Inspect high-detail sanitized matched views only. Do not inspect source
  images or a full/archival contact sheet.
- Record each useful observation here immediately, then write `review.json`.

## Durable log

- `2026-07-28`: Checkpoint initialized before any image generation,
  conversion, or inspection. No raster has been read by this agent.
- `2026-07-28`: Text evidence read. The candidate preserves 7,347 vertices,
  12,564 faces, face indices, and material assignments; it reports zero
  negative-orientation locators. Affected-edge ratio is min `0.690127`,
  median `1.002779`, p95 `1.086801`, max `1.319363`. Maximum vertex
  displacement is `14.163712 mm`. Cutter penetrations improve `354 -> 336`,
  reserved-margin violations `365 -> 348`, and triangle overlaps `837 -> 806`;
  component 20 still has 115 penetrating vertices and 118 below margin. The
  report explicitly remains `qualitative_review: PENDING` and
  `promotion: NOT_PROMOTED`.
- `2026-07-28` — **INTENDED / not yet run: sanitized derivative batch.**
  Operation: copy each raster listed below, then run
  `scripts.image_sanitization.sanitize_image` on the copied output. Inputs have
  prefix
  `_validation/experiments/geometry_repair/component_20_methods/minor_clusters_trial/`;
  outputs have prefix
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/`.
  Exact relative input -> output mappings:
  - `local/source--dorsal.png` -> `local/source--dorsal.png`
  - `local/current--dorsal.png` -> `local/current--dorsal.png`
  - `local/source--ventral.png` -> `local/source--ventral.png`
  - `local/current--ventral.png` -> `local/current--ventral.png`
  - `local/source--medial.png` -> `local/source--medial.png`
  - `local/current--medial.png` -> `local/current--medial.png`
  - `local/source--lateral.png` -> `local/source--lateral.png`
  - `local/current--lateral.png` -> `local/current--lateral.png`
  - `local/source--bicep_axial.png` -> `local/source--bicep_axial.png`
  - `local/current--bicep_axial.png` -> `local/current--bicep_axial.png`
  - `complete/source--dorsal.png` -> `complete/source--dorsal.png`
  - `complete/current--dorsal.png` -> `complete/current--dorsal.png`
  - `complete/source--ventral.png` -> `complete/source--ventral.png`
  - `complete/current--ventral.png` -> `complete/current--ventral.png`
  - `complete/source--medial.png` -> `complete/source--medial.png`
  - `complete/current--medial.png` -> `complete/current--medial.png`
  - `complete/source--lateral.png` -> `complete/source--lateral.png`
  - `complete/current--lateral.png` -> `complete/current--lateral.png`
  - `complete/source--dorsal_lateral_three_quarter.png` ->
    `complete/source--dorsal_lateral_three_quarter.png`
  - `complete/current--dorsal_lateral_three_quarter.png` ->
    `complete/current--dorsal_lateral_three_quarter.png`
  - `complete/source--ventral_medial_three_quarter.png` ->
    `complete/source--ventral_medial_three_quarter.png`
  - `complete/current--ventral_medial_three_quarter.png` ->
    `complete/current--ventral_medial_three_quarter.png`
  - `complete/source--wrist_axial.png` -> `complete/source--wrist_axial.png`
  - `complete/current--wrist_axial.png` -> `complete/current--wrist_axial.png`
  - `complete/source--bicep_axial.png` -> `complete/source--bicep_axial.png`
  - `complete/current--bicep_axial.png` -> `complete/current--bicep_axial.png`
- `2026-07-28` — **DONE: sanitized derivative batch.** All 26 copied
  derivatives were sanitized by ImageMagick as stripped, orientation-normalized,
  8-bit TrueColor sRGB PNGs with alpha disabled. Sizes range from 393,986 to
  569,973 bytes. Every derivative is below 10,000,000 bytes and is marked
  `direct_image_model_review: true`. No raster was inspected during conversion.
- `2026-07-28` — **INTENDED / not yet run: bounded review-page generation.**
  Operation: compose only the already-sanitized derivatives into seven
  two-column matched-view pages, label source/current and view, then sanitize
  each generated page through `scripts.image_sanitization.sanitize_image`.
  Every input and output below is under
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/`.
  Exact inputs -> output:
  - `local/source--dorsal.png`, `local/current--dorsal.png`,
    `local/source--ventral.png`, `local/current--ventral.png` ->
    `pages/local-page-01-dorsal-ventral.png`
  - `local/source--medial.png`, `local/current--medial.png`,
    `local/source--lateral.png`, `local/current--lateral.png` ->
    `pages/local-page-02-medial-lateral.png`
  - `local/source--bicep_axial.png`, `local/current--bicep_axial.png` ->
    `pages/local-page-03-bicep-axial.png`
  - `complete/source--dorsal.png`, `complete/current--dorsal.png`,
    `complete/source--ventral.png`, `complete/current--ventral.png` ->
    `pages/complete-page-01-dorsal-ventral.png`
  - `complete/source--medial.png`, `complete/current--medial.png`,
    `complete/source--lateral.png`, `complete/current--lateral.png` ->
    `pages/complete-page-02-medial-lateral.png`
  - `complete/source--dorsal_lateral_three_quarter.png`,
    `complete/current--dorsal_lateral_three_quarter.png`,
    `complete/source--ventral_medial_three_quarter.png`,
    `complete/current--ventral_medial_three_quarter.png` ->
    `pages/complete-page-03-three-quarter.png`
  - `complete/source--wrist_axial.png`,
    `complete/current--wrist_axial.png`,
    `complete/source--bicep_axial.png`,
    `complete/current--bicep_axial.png` ->
    `pages/complete-page-04-axial.png`
- `2026-07-28` — **FAILED: labeled bounded review-page generation.**
  ImageMagick failed on the first target,
  `pages/local-page-01-dorsal-ventral.png`, with
  `montage: unable to read font '' @ error/annotate.c/RenderFreetype/1665`.
  Because the batch used `set -e`, later pages and the sanitization pass did not
  run. Actionable reason: this environment has no usable default montage font.
  No failed output will be inspected.
- `2026-07-28` — **INTENDED / not yet run: unlabeled bounded review-page
  retry.** Use the identical seven exact input/output mappings recorded above,
  omit font-dependent labels, and preserve a fixed ordering on every page:
  row-major `source`, `current`, then the next view's `source`, `current`.
  Generate with ImageMagick montage and immediately sanitize every successful
  page. The checkpoint and filenames provide the view labels.
- `2026-07-28` — **FAILED: unlabeled montage retry.** ImageMagick `montage`
  still attempted to load an empty default font and failed on
  `pages/local-page-01-dorsal-ventral.png` with the same
  `RenderFreetype/1665` error. Later pages and sanitization did not run due to
  `set -e`. No failed output will be inspected.
- `2026-07-28` — **INTENDED / not yet run: font-free append retry.** Use the
  identical seven exact input/output mappings and fixed row-major ordering
  above, replacing `montage` with ImageMagick `+append` for matched source /
  current rows and `-append` for the two view rows. This requires no annotation
  or font. Immediately sanitize all generated pages.
- `2026-07-28` — **DONE: font-free bounded review pages.** All seven pages
  were generated and then sanitized as stripped, orientation-normalized,
  8-bit TrueColor sRGB PNGs without alpha. Sizes range from 666,588 to
  1,668,612 bytes; all are below 10,000,000 bytes and marked
  `direct_image_model_review: true`. No page has yet been inspected.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/local-page-01-dorsal-ventral.png`
  at high detail. Layout: top row dorsal source/current, bottom row ventral
  source/current.
- `2026-07-28` — **DONE: local dorsal/ventral high-detail inspection.**
  Source and current remain registered in both views. No new gross silhouette
  break, isolated spike, slab, obvious flattening, depth inversion, or damage
  to the surrounding wrist/elbow composition is visible. The changed surfaces
  are subtle relative to the pre-existing faceted/open composition. No
  original-detail escalation is justified by this page alone.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/local-page-02-medial-lateral.png`
  at high detail. Layout: top row medial source/current, bottom row lateral
  source/current.
- `2026-07-28` — **DONE: local medial/lateral high-detail inspection.**
  Source/current silhouettes and the dominant longitudinal armor folds remain
  registered. The repair does not create a visible new bridge across negative
  space, plate-like slab, spike, flattened patch, inverted-looking facet, or
  disruption of adjacent loop/cable and elbow forms. Existing jagged/open
  boundaries are present on both sides and are not attributable to this delta.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/local-page-03-bicep-axial.png`
  at high detail. Layout: source left, current right.
- `2026-07-28` — **DONE: local bicep-axial high-detail inspection.** The
  circumferential silhouette, central broad facets, negative spaces, and
  neighboring hardware remain coherent and registered. No new radial spike,
  bulge/slab, flattening, or depth inversion is visible.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/complete-page-01-dorsal-ventral.png`
  at high detail. Layout: top row dorsal source/current, bottom row ventral
  source/current.
- `2026-07-28` — **DONE: complete dorsal/ventral high-detail inspection.**
  At full-arm scale, the source/current outer silhouette, major gaps, armor
  layering, wrist termination, elbow opening, and neighboring components remain
  registered. No repair-attributable spike, slab, broad flattening, inversion,
  or composition break is visible.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/complete-page-02-medial-lateral.png`
  at high detail. Layout: top row medial source/current, bottom row lateral
  source/current.
- `2026-07-28` — **DONE: complete medial/lateral high-detail inspection.**
  The overall bent-arm registration, wearer-facing negative spaces, long
  forearm members, elbow hardware, and upper-arm plate silhouette are stable.
  There is no visible new bridge, drift, spike, slab, flattened plane, or
  depth-reversal cue attributable to Repair 006.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/complete-page-03-three-quarter.png`
  at high detail. Layout: top row dorsal-lateral three-quarter source/current,
  bottom row ventral-medial three-quarter source/current.
- `2026-07-28` — **DONE: complete three-quarter high-detail inspection.**
  Both oblique views preserve the full composition, intentional open regions,
  upper-arm sweep, elbow cluster, and forearm shell. No new silhouette
  discontinuity, misregistration, protruding spike, planar slab, flattening,
  or inverted-depth appearance is visible.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_006_component_20_minor/sanitized_review/pages/complete-page-04-axial.png`
  at high detail. Layout: top row wrist-axial source/current, bottom row
  bicep-axial source/current.
- `2026-07-28` — **DONE: complete axial high-detail inspection.** Wrist-axial
  and bicep-axial source/current pairs preserve the circumferential silhouettes,
  nested gaps, broad facets, and adjacent hardware. No radial spike, slab,
  flattening, depth inversion, or neighboring-composition damage is visible.
- `2026-07-28` — **FINAL OBSERVATION CHECKPOINT.**
  `does_this_repair_delta_look_ass: false`. Across all five local views and
  eight complete views, Repair 006 does not introduce a visible silhouette
  break, registration drift, spike, slab, flattening, depth inversion, or
  component-20 neighboring-composition damage. This is consistent with the
  unchanged topology/material evidence, zero reported negative-orientation
  locators, median edge ratio near 1.0, bounded extrema, and improved collision
  counts. Classification: `pass / retain_candidate`. This means only that the
  Repair 006 delta is qualitatively acceptable to retain for continued work;
  it is **not** fitted-surface promotion, and the remaining 115 component-20
  cutter penetrations / 118 reserved-margin violations remain unresolved.
  Uncertainty: source and current use different display colors, which reduces
  sensitivity to extremely subtle shading-only differences; matched cameras,
  local plus complete coverage, and axial/oblique views provide sufficient
  evidence for the stated bounded classification. No original-detail view was
  needed.
- `2026-07-28` — **DONE: durable review artifact.**
  `validation_reviews/geometry_repair/repair_006_component_20_minor/review.json`
  was written, parsed successfully with `jq`, and its pass/retain/false answer
  assertions were verified. `git diff --check` reports no whitespace errors for
  the two owned durable evidence files.
