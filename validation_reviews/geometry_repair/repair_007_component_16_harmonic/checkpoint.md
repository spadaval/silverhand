# Repair 007 component-16 harmonic validation checkpoint

Mission: `geometry-repair-007-review`

Scope: independently validate only the delta introduced by
`REPAIR_007_COMPONENT_16_HARMONIC` relative to retained-candidate Repair 006.
This review does not promote the fitted surface and must not modify model,
script, status, history, or shared repair-record artifacts.

## Claims under validation

1. The local before/after delta does not unacceptably narrow the component-16
   ribbon or introduce a silhouette break, registration drift, spike, slab,
   flattening, depth inversion, or adjacent-composition damage.
2. The complete-view before/after delta introduces none of those defects in
   the full-arm composition.
3. Build-report topology, orientation, edge-ratio, and clearance evidence is
   compatible with retaining the repair as a candidate.
4. `does_this_repair_delta_look_ass` can be answered explicitly from bounded,
   sanitized, reproducible evidence.

## Validation method

- Read `build_report.json` and the local/complete manifests as text evidence.
- Before each image operation, append the exact operation and paths here.
- Copy each required raster to the owned sanitized-review directory, then
  sanitize the copy through `scripts/image_sanitization.py` / ImageMagick.
- Verify every derivative is at most 10,000,000 bytes before inspection.
- Inspect high-detail sanitized matched views only. Never inspect source
  rasters or a full/archival contact sheet.
- Record every useful observation here immediately, then write `review.json`.

## Durable log

- `2026-07-28`: Checkpoint initialized before any image generation,
  conversion, or inspection. No raster has been read by this agent.
- `2026-07-28`: Text evidence read. The candidate preserves 7,347 vertices,
  12,564 faces, face indices, and material assignments. It reports zero
  negative-orientation locators. The 60 affected vertices have maximum
  displacement `5.646307 mm`; affected-edge ratios are minimum `0.984548`,
  median `1.015695`, p95 `1.110634`, and maximum `1.132143`. Global cutter
  penetrations improve `336 -> 334`, reserved-margin violations `348 -> 346`,
  and triangle overlaps `806 -> 792`. Component 16 reaches zero vertices below
  both the cutter and reserved margin. The report remains
  `qualitative_review: PENDING` and `promotion: NOT_PROMOTED`.
- `2026-07-28` — **INTENDED / not yet run: sanitized derivative batch.**
  Operation: copy each raster listed below, then run
  `scripts.image_sanitization.sanitize_image` on the copied output. Inputs have
  prefix
  `_validation/experiments/geometry_repair/component_16_methods/harmonic_r8_trial/`;
  outputs have prefix
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/`.
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
  derivatives were sanitized by ImageMagick as stripped,
  orientation-normalized, 8-bit TrueColor sRGB PNGs with alpha disabled. Sizes
  range from 475,940 to 640,887 bytes. Every derivative is below 10,000,000
  bytes and marked `direct_image_model_review: true`. No raster was inspected
  during conversion.
- `2026-07-28` — **INTENDED / not yet run: font-free bounded review-page
  generation.** Compose only the already-sanitized derivatives into seven
  pages using ImageMagick `+append` for each source/current row and `-append`
  for paired view rows. Fixed ordering is row-major source then current. Then
  immediately sanitize each page through `scripts.image_sanitization`.
  Every input and output below is under
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/`.
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
- `2026-07-28` — **DONE: font-free bounded review pages.** All seven pages
  were generated and then sanitized as stripped, orientation-normalized, 8-bit
  TrueColor sRGB PNGs without alpha. Sizes range from 1,075,301 to 2,355,804
  bytes; all are below 10,000,000 bytes and marked
  `direct_image_model_review: true`. No page has yet been inspected.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/local-page-01-dorsal-ventral.png`
  at high detail. Layout: top row dorsal source/current, bottom row ventral
  source/current. Review ribbon width/profile, silhouette, registration,
  spikes, slabs, flattening, inversion, and adjacent composition.
- `2026-07-28` — **DONE: local dorsal/ventral high-detail inspection.**
  The narrow diagonal ribbon remains continuously registered between the same
  neighboring forms in both views. Its visible width and tapered profile are
  preserved without the severe pinching/collapse seen in the rejected prior
  component-16 method. No repair-attributable spike, slab, broad flattening,
  inversion cue, or adjacent-composition break is visible. Existing sharp
  facets and open gaps occur on both source and current. Different display
  colors limit sensitivity to shading-only changes; no original-detail
  escalation is justified from this page.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/local-page-02-medial-lateral.png`
  at high detail. Layout: top row medial source/current, bottom row lateral
  source/current. Review ribbon width/profile, silhouette, registration,
  spikes, slabs, flattening, inversion, and adjacent composition.
- `2026-07-28` — **DONE: local medial/lateral high-detail inspection.**
  The ribbon's long edges, taper, and attachment relationship remain coherent
  in both orthogonal views. Current does not show a new necked-down segment,
  folded strip, planar slab, protruding spike, or inverted-looking facet.
  Surrounding plate rims, circular recess, open channel, and lower hardware
  retain their before-state registration and depth ordering.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/local-page-03-bicep-axial.png`
  at high detail. Layout: source left, current right. Review cross-sectional
  ribbon thickness/width, radial displacement, registration, and depth order.
- `2026-07-28` — **DONE: local bicep-axial high-detail inspection.** The
  ribbon stays nested against the same broad plate and neighboring upright
  elements. The repair presents as a smooth bounded radial adjustment, not a
  collapsed width, spike, slab, or depth-order reversal. Its endpoints remain
  attached and the adjacent negative spaces remain open.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/complete-page-01-dorsal-ventral.png`
  at high detail. Layout: top row dorsal source/current, bottom row ventral
  source/current. Review full-arm silhouette and component registration.
- `2026-07-28` — **DONE: complete dorsal/ventral high-detail inspection.**
  Full-arm silhouette, elbow opening, upper-arm massing, lower-arm shell, major
  rails, and negative spaces remain registered. The Repair 007 delta is
  visually bounded at this scale; no new spike, slab, flattened region,
  detached element, or depth inversion is visible.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/complete-page-02-medial-lateral.png`
  at high detail. Layout: top row medial source/current, bottom row lateral
  source/current. Review full-arm silhouette, registration, and neighboring
  composition.
- `2026-07-28` — **DONE: complete medial/lateral high-detail inspection.**
  The bent-arm composition, separated upper/lower masses, elbow void, long
  cables, plate layers, and wearer-facing gaps remain stable. No
  repair-attributable outer-silhouette drift, unexpected bridge, spike, slab,
  flattening, or registration loss is visible.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/complete-page-03-three-quarter.png`
  at high detail. Layout: top row dorsal-lateral source/current, bottom row
  ventral-medial source/current. Review oblique silhouette, depth order,
  ribbon narrowing, and adjacent composition.
- `2026-07-28` — **DONE: complete three-quarter high-detail inspection.**
  Both oblique pairs preserve the upper-arm sweep, separated shell fragments,
  elbow mechanism, longitudinal forearm members, and intentional voids. No
  depth-layer inversion, floating or detached ribbon, new spike, slab,
  pinching cue, or neighboring-composition damage is visible.
- `2026-07-28` — **INTENDED / not yet run: high-detail inspection.**
  Inspect exact sanitized path
  `_validation/geometry_repair/repair_007_component_16_harmonic/sanitized_review/pages/complete-page-04-axial.png`
  at high detail. Layout: top row wrist-axial source/current, bottom row
  bicep-axial source/current. Review radial silhouette, nested gaps, ribbon
  profile, and depth ordering.
- `2026-07-28` — **DONE: complete axial high-detail inspection.** Wrist and
  bicep axial silhouettes, circumferential layers, loops, nested gaps, and
  broad plate facets remain coherent and registered. The bicep-side ribbon
  region shows no radial spike, collapsed strip, slab, flattening, or
  unexpected depth reversal.
- `2026-07-28` — **FINAL OBSERVATION CHECKPOINT.**
  `does_this_repair_delta_look_ass: false`. Across five local views and eight
  complete views, Repair 007 preserves the narrow component-16 ribbon's
  readable width, taper, attachment, and surrounding negative spaces. It does
  not introduce a visible silhouette break, registration drift, spike, slab,
  flattening, depth inversion, or adjacent-composition damage. This agrees
  with unchanged topology and materials, zero negative-orientation locators,
  tightly bounded affected-edge ratios (`0.984548–1.132143`), and full
  component-16 clearance. Classification: `pass / retain_candidate`. This is
  only a retain/reject decision for the Repair 007 delta relative to Repair
  006; it is not fitted-surface promotion. Global anatomical clearance still
  fails with 334 cutter penetrations, 346 reserved-margin violations, and 792
  triangle overlaps. Uncertainty: source/current display colors differ, which
  limits sensitivity to extremely subtle shading-only differences, but local
  matched cameras plus complete orthogonal, oblique, and axial coverage are
  sufficient for the bounded classification. No original-detail escalation
  was necessary.
- `2026-07-28` — **DONE: durable review artifact.**
  `validation_reviews/geometry_repair/repair_007_component_16_harmonic/review.json`
  was written and parsed successfully with `jq`. Assertions verified
  `pass`, `retain_candidate`, `does_this_repair_delta_look_ass: false`, no
  fitted-surface promotion, seven inspected pages under 10,000,000 bytes, and
  the continuing anatomical-clearance failure. Owned-evidence whitespace
  checks completed without errors.
