# Repair 012 Component 39 regional validation checkpoint

## Assignment

- Validation-only review of
  `blender_files/experiments/geometry_repair/repair_012_component_39_regional_f25.blend`.
- Before object: `EVAL_REPAIR_012_COMPONENT_39_BEFORE`.
- After object: `EVAL_REPAIR_012_COMPONENT_39_AFTER`.
- Detail objects are present in the experiment scene.
- Numerical report:
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/build_report.json`.
- Do not modify models, shared scripts, shared docs, or `classification.json`.

## Claims

1. The compact visible wrist detail remains recognizable and registered.
2. The repair does not flatten or rotate the detail.
3. It creates no gap closure, fusion, spike, slab, depth inversion, abrupt seam,
   or collateral wrist damage.
4. The large `13.094812 mm` translation and affected-edge distortion tail
   (`0.369226` minimum, `1.452809` p95, `1.736243` maximum) are not visually
   destructive.
5. Explicitly answer `does_this_repair_delta_look_ass`.
6. Retain or reject the candidate.

## Image-safety protocol

- Every image operation is documented before and after execution.
- Every generated derivative is immediately sanitized with ImageMagick:
  metadata and profiles stripped, orientation normalized, converted to sRGB,
  written as an 8-bit PNG or JPEG, and alpha removed.
- Only sanitized derivatives at or below `10,000,000` bytes may be inspected.
- Inspection starts at high detail and uses the smallest sufficient matched
  evidence. Stop early on a decisive failure.

## Text-only numerical evidence

- Repair 012 preserves topology (`7,347` vertices, `12,564` faces), face
  indices, and material assignments.
- It clears all Component 39 cutter and reserved-margin failures.
- Global below-cutter vertices improve `278 -> 265`; reserved-margin failures
  improve `297 -> 282`; triangle overlaps improve `692 -> 675`.
- No negative-orientation locator is reported.
- The motion is nevertheless aggressive: `790` affected vertices,
  `13.094812 mm` component translation, and edge ratios from `0.369226` to
  `1.736243`.

## Progress

- 2026-07-28: Validation initialized. No image has been generated or inspected.

## Recovery state

State: `READY_TO_RENDER_CANONICAL`

Next image operation:

- Render canonical matched source/current views with
  `scripts/blender/render_geometry_comparison.py`.
- Use source `EVAL_REPAIR_012_COMPONENT_39_BEFORE`, target
  `EVAL_REPAIR_012_COMPONENT_39_AFTER`, resolution `1000 x 1400`, and output
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/`.
- The renderer must immediately sanitize every generated PNG in place through
  the repository ImageMagick sanitizer.
- After generation, verify and record the manifest and sizes before inspecting
  any image.

## Canonical render result

- 2026-07-28: Blender 5.2.0 completed all 16 canonical source/current renders.
  Manifest:
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/manifest.json`.
- The renderer immediately sanitized every output through ImageMagick. The
  manifest records stripped metadata/profiles, normalized orientation, sRGB,
  8-bit color, no alpha, and `direct_image_model_review: true`.
- Sizes range from `911,878` to `1,076,913` bytes; all are below
  `10,000,000` bytes.
- No canonical image has been inspected.
- Text-only Blender inspection confirms the supplied detail objects exist and
  share identical `31.497 x 65.454 x 42.691 mm` bounding dimensions. The
  canonical arm views are broader than necessary for the detail-shape claim.

State: `READY_TO_RENDER_LOCAL_DETAIL`

Next image operation:

- Render `EVAL_REPAIR_012_COMPONENT_39_DETAIL_BEFORE` and
  `EVAL_REPAIR_012_COMPONENT_39_DETAIL_AFTER` with a temporary validation-only
  driver. Do not save or mutate the blend.
- Use a shared orthographic frame and matched dorsal, ventral, medial, lateral,
  wrist-axial, and two three-quarter cameras at `900 x 900`.
- Write outputs to
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/local/`.
- Immediately sanitize every output through the repository ImageMagick helper,
  then record the manifest and sizes before inspection.

## Local-detail render result

- 2026-07-28: Blender completed 14 matched local-detail renders. Manifest:
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/local/manifest.json`.
- Every output was immediately sanitized through ImageMagick. The manifest
  records stripped metadata/profiles, normalized orientation, sRGB, 8-bit
  color, no alpha, and `direct_image_model_review: true`.
- Sizes range from `466,683` to `500,974` bytes. Every derivative is below
  `10,000,000` bytes.
- No image has been inspected.

State: `READY_TO_BUILD_LOCAL_PAIRS`

Next image operation:

- Build font-free source-left/current-right matched pairs for all seven local
  views from the already sanitized source/current renders using ImageMagick
  `+append`.
- Immediately sanitize each pair through
  `scripts.image_sanitization.sanitize_image`.
- Record the pair paths and sizes before high-detail inspection.

## Local matched-pair result

- 2026-07-28: Seven font-free source-left/current-right pair pages were
  generated from already sanitized local renders and immediately sanitized
  again through the repository ImageMagick helper.

| sanitized pair | bytes | direct review |
| --- | ---: | --- |
| `pair--dorsal.png` | 625688 | true |
| `pair--ventral.png` | 610204 | true |
| `pair--medial.png` | 583583 | true |
| `pair--lateral.png` | 588544 | true |
| `pair--dorsal_lateral_three_quarter.png` | 558173 | true |
| `pair--ventral_medial_three_quarter.png` | 548635 | true |
| `pair--wrist_axial.png` | 625362 | true |

- Every pair is sRGB, 8-bit, no alpha, stripped of metadata/profiles, with
  normalized orientation and size below `10,000,000` bytes.
- No pair has been inspected.

State: `READY_TO_INSPECT_LOCAL_DORSAL`

Next image operation:

- Inspect
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/local/pair--dorsal.png`
  at high detail. Source is left; Repair 012 is right.
- Test recognizable silhouette, rotation, flattening, abrupt seam, spikes,
  and gross distortion. Stop early if failure is decisive.

### Local dorsal observation

- 2026-07-28: High-detail inspection completed.
- The long faceted strip remains immediately recognizable. Its crooked
  centerline, broad angular cap, narrow midsection, and blunt lower foot all
  remain present.
- The after silhouette closely tracks the source; no visible wholesale
  rotation, flattening, spike, slab, inversion, or abrupt falloff seam appears.
- Subtle depth changes cannot be classified from this projection alone.

State: `READY_TO_INSPECT_LOCAL_LATERAL`

Next image operation:

- Inspect
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/local/pair--lateral.png`
  at high detail. Source is left; Repair 012 is right.
- Test preserved depth profile, cap/foot shape, folds, and whether the severe
  edge-ratio tail has a visible destructive manifestation.

### Local lateral observation

- 2026-07-28: High-detail inspection completed.
- The shallow bowed lower run, long tapered middle, raised angular shoulder,
  and blunt box-like cap remain intact.
- The repair visibly redistributes curvature through the middle and shoulder,
  but does not collapse the strip, reverse its depth, create a spike, or turn
  it into a flat slab. No pinched fold or abrupt seam corresponding to the
  numerical distortion extremes is visible.
- The after object still reads as a coherent variant of the same detail, not a
  rotated or replaced form.

State: `READY_TO_INSPECT_LOCAL_DORSAL_LATERAL_THREE_QUARTER`

Next image operation:

- Inspect
  `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/review/local/pair--dorsal_lateral_three_quarter.png`
  at high detail for combined silhouette/depth preservation and local
  stretching.

### Local dorsal-lateral three-quarter observation

- 2026-07-28: High-detail inspection completed.
- The repair preserves the thin faceted rail, its gradual long-axis bow, the
  raised shoulder, and the broad terminal plate. The same characteristic
  stepped transition beneath the cap remains visible.
- There is some intentional redistribution of segment lengths through the
  shoulder, consistent with the numerical distortion tail, but no visual
  tearing, fold-over, spike, plate collapse, or abrupt discontinuity.
- Local shape claims provisionally pass. Whole-wrist context is still required
  for registration, fusion, gap closure, and collateral-damage claims.

State: `READY_TO_BUILD_CANONICAL_CONTEXT_PAIRS`

Next image operation:

- Build font-free source-left/current-right pairs from the already sanitized
  canonical `wrist_axial`, `dorsal_lateral_three_quarter`, and
  `ventral_medial_three_quarter` renders.
- Immediately sanitize each generated pair through the repository ImageMagick
  helper, record its size, and only then inspect at high detail.

## Canonical context-pair result

- 2026-07-28: Three source-left/current-right canonical context pairs were
  generated and immediately sanitized.

| sanitized pair | bytes | direct review |
| --- | ---: | --- |
| `review/pair--wrist_axial.png` | 1578374 | true |
| `review/pair--dorsal_lateral_three_quarter.png` | 1353134 | true |
| `review/pair--ventral_medial_three_quarter.png` | 1312619 | true |

- All are sRGB, 8-bit, no alpha, metadata/profile stripped, normalized, and
  below `10,000,000` bytes. None has been inspected.

State: `READY_TO_INSPECT_CONTEXT_WRIST_AXIAL`

Next image operation:

- Inspect `review/pair--wrist_axial.png` at high detail. Source is left;
  Repair 012 is right.
- Test wrist-opening registration, retained negative spaces, fusion, new walls
  or bridges, and collateral deformation.

### Canonical wrist-axial observation

- 2026-07-28: High-detail inspection completed.
- The central wrist opening, large internal negative space, outer cuff rings,
  and three prominent external loops remain registered and open.
- No new wall, bridge, slab, spike, or fusion is visible. The dense layered
  wrist assembly retains the same depth ordering and overall silhouette.
- No collateral deformation is apparent at this scale, but an oblique context
  view is needed to judge longitudinal registration of the moved strip.

State: `READY_TO_INSPECT_CONTEXT_DORSAL_LATERAL`

Next image operation:

- Inspect `review/pair--dorsal_lateral_three_quarter.png` at high detail.
  Source is left; Repair 012 is right.
- Test longitudinal registration, gaps around the compact wrist detail, local
  fusion, seam formation, and collateral forearm damage.

### Canonical dorsal-lateral three-quarter observation

- 2026-07-28: High-detail inspection completed.
- The wrist assembly, paired circular insets, long rails, layered cuff, and
  forearm shell remain registered. Existing negative spaces remain open.
- The repair produces no visible new bridge, carrier slab, spike, fused
  neighbor, abrupt seam, or collateral shift in the surrounding wrist and
  forearm geometry.
- From this whole-arm view, the moved detail remains compositionally
  subordinate and does not look detached or misplaced.

State: `READY_TO_INSPECT_CONTEXT_VENTRAL_MEDIAL`

Next image operation:

- Inspect `review/pair--ventral_medial_three_quarter.png` at high detail.
  Source is left; Repair 012 is right.
- Use this opposing context view as the final adversarial check for gap
  closure, fusion, displaced registration, and depth inversion.

### Canonical ventral-medial three-quarter observation

- 2026-07-28: High-detail inspection completed.
- The opposing view preserves the wrist cuff, long rails, upper forearm shell,
  large open channels, and separated upper-arm masses.
- No new fusion, gap closure, depth inversion, local carrier wall, abrupt seam,
  or collateral displacement is visible. The repaired detail does not break
  the surrounding wrist composition.

## Final classification

- `does_this_repair_delta_look_ass: false`
- Candidate disposition: `retain_candidate`
- Qualitative delta: `pass`
- Fitted-surface promotion: `deferred`
- Anatomical clearance: `fail` because the full candidate still contains
  `265` cutter penetrations, `282` reserved-margin failures, and `675`
  triangle overlaps.
- The unusually wide edge-ratio tail is real numerically, but the matched
  local views show it as coherent redistribution through a low-poly strip,
  without a visually destructive pinch, fold, reversal, or spike.

State: `DONE`
