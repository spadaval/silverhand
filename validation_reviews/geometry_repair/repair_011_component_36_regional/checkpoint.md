# Repair 011 Component 36 regional validation checkpoint

## Assignment

- Validation-only review of `blender_files/experiments/geometry_repair/repair_011_component_36_regional_f30.blend`.
- Before object: `EVAL_REPAIR_011_COMPONENT_36_BEFORE`.
- After object: `EVAL_REPAIR_011_COMPONENT_36_AFTER`.
- Numerical report: `_validation/experiments/geometry_repair/component_36_methods/repair_011_f30/build_report.json`.
- Do not modify models, scripts, shared docs, or `classification.json`.

## Claims

1. The visible wrist hook/cable keeps its source curve.
2. The detail remains recognizable and registered.
3. The repair introduces no gap closure, fusion, spike, slab, flattening, depth inversion, or adjacent damage.
4. Explicitly answer `does_this_repair_delta_look_ass`.
5. Retain or reject the candidate.

## Image-safety protocol

- Every render is documented before it is generated.
- Every generated image is sanitized using ImageMagick before inspection:
  metadata/profiles stripped, orientation normalized, converted to sRGB,
  8-bit PNG or JPEG, and alpha removed.
- Only sanitized derivatives at or below 10,000,000 bytes may be inspected.
- Review starts at high detail and uses the smallest sufficient matched evidence.

## Progress

- 2026-07-28: Validation initialized. No image has yet been generated or inspected.
- 2026-07-28: Text-only numerical report reviewed. Repair 011 keeps topology
  (`7,347` vertices, `12,564` faces), face indices, and materials unchanged.
  It clears all Component 36 cutter and reserved-margin failures. Global
  below-cutter vertices improve `282 -> 278`, reserved-margin failures improve
  `305 -> 297`, and triangle overlaps improve `701 -> 692`. There are zero
  negative-orientation locators. Affected-edge ratios are `0.811078` minimum,
  `1.000061` median, `1.081979` p95, and `1.197074` maximum.

## Recovery state

State: `READY_TO_RENDER_CANONICAL`

Next image operation:

- Render all canonical matched source/current views from
  `blender_files/experiments/geometry_repair/repair_011_component_36_regional_f30.blend`
  with `scripts/blender/render_geometry_comparison.py`.
- Use source `EVAL_REPAIR_011_COMPONENT_36_BEFORE`, target
  `EVAL_REPAIR_011_COMPONENT_36_AFTER`, resolution `1000 x 1400`, and output
  `_validation/experiments/geometry_repair/component_36_methods/repair_011_f30/review`.
- The renderer immediately sanitizes each generated PNG in place using
  ImageMagick through `scripts.image_sanitization.sanitize_image`.
- After generation, verify and record every derivative's sanitization metadata
  and size before inspecting any image.

## Canonical render result

- 2026-07-28: Blender 5.2.0 completed all 16 matched renders. Manifest:
  `_validation/experiments/geometry_repair/component_36_methods/repair_011_f30/review/manifest.json`.
- Every output was sanitized in place through ImageMagick. The manifest reports
  sRGB, 8-bit color, alpha disabled, stripped metadata/profiles, normalized
  orientation, and `direct_image_model_review: true`.
- Sizes range from `911,959` to `1,075,760` bytes. All are below the
  `10,000,000`-byte limit.
- No canonical image has been inspected. Text-only object inspection found the
  supplied detail objects have identical `59.050 x 88.773 x 46.720 mm`
  dimensions. The full-arm canonical views are too broad to be the smallest
  sufficient proof for wrist-hook shape claims.

State: `READY_TO_RENDER_LOCAL_DETAIL`

Next image operation:

- Render the supplied `EVAL_REPAIR_011_COMPONENT_36_DETAIL_BEFORE` and
  `EVAL_REPAIR_011_COMPONENT_36_DETAIL_AFTER` objects with a temporary,
  validation-only Blender driver that does not save or mutate the blend.
- Use a shared orthographic frame and matched dorsal, ventral, medial, lateral,
  and wrist-axial cameras at `900 x 900`.
- Write to
  `_validation/experiments/geometry_repair/component_36_methods/repair_011_f30/review/local/`.
- Immediately sanitize every output in place through the repository
  `sanitize_image` helper, then record the manifest and file sizes before any
  inspection.

## Local-detail render result

- 2026-07-28: Blender completed ten matched local-detail renders. Manifest:
  `_validation/experiments/geometry_repair/component_36_methods/repair_011_f30/review/local/manifest.json`.
- All outputs were immediately sanitized with ImageMagick. Manifest checks
  report metadata stripped, orientation normalized, sRGB, 8-bit, no alpha, and
  `direct_image_model_review: true`.

| sanitized output | bytes |
| --- | ---: |
| `source--dorsal.png` | 481901 |
| `current--dorsal.png` | 486890 |
| `source--ventral.png` | 477232 |
| `current--ventral.png` | 482545 |
| `source--medial.png` | 467362 |
| `current--medial.png` | 470049 |
| `source--lateral.png` | 481307 |
| `current--lateral.png` | 486187 |
| `source--wrist_axial.png` | 464479 |
| `current--wrist_axial.png` | 466713 |

- Independent ImageMagick identification confirms sRGB, 8-bit, three-channel
  images with normalized `TopLeft` orientation. Its optional `%[profiles]`
  query emitted an unsupported-property warning; this did not affect images
  and the sanitization manifest already records profile stripping.
- Every local derivative is below `10,000,000` bytes. No image has been
  inspected.

State: `READY_TO_BUILD_LOCAL_PAIRS`

Next image operation:

- Build font-free, source-left/current-right matched pair pages for all five
  local views using ImageMagick `+append`.
- Immediately sanitize each pair in place using the repository ImageMagick
  sanitization helper.
- Record pair paths and sizes before inspection. Inspect the smallest decisive
  views one at a time at high detail.

## Local matched-pair result

- 2026-07-28: Five font-free source-left/current-right pairs were generated
  with ImageMagick and immediately sanitized in place through the repository
  helper.

| sanitized pair | bytes | direct review |
| --- | ---: | --- |
| `pair--dorsal.png` | 576956 | true |
| `pair--ventral.png` | 569310 | true |
| `pair--medial.png` | 540701 | true |
| `pair--lateral.png` | 554478 | true |
| `pair--wrist_axial.png` | 520880 | true |

- Each pair is sRGB, 8-bit, without alpha or metadata/profiles, with normalized
  orientation, and below `10,000,000` bytes.
- No image has yet been inspected.

State: `READY_TO_INSPECT_LOCAL_DORSAL`

Next image operation:

- Inspect `review/local/pair--dorsal.png` at high detail. Source is left and
  Repair 011 is right.

### Local dorsal observation

- 2026-07-28: High-detail inspection completed.
- The long narrow hook/cable retains its source S-like bend, straight upper
  run, lower kink, and faceted terminal foot. The after geometry shifts the
  lower bend and terminal outward slightly, but remains immediately
  recognizable.
- No spike, slab, flattening, depth inversion, obvious fold, or abrupt
  falloff seam is visible in this view.
- Registration and clearance around adjacent sleeve structures cannot be
  classified from the isolated dorsal view alone.

State: `READY_TO_INSPECT_LOCAL_LATERAL`

Next image operation:

- Inspect `review/local/pair--lateral.png` at high detail to test preserved
  depth, curvature, and terminal shape. Source is left and Repair 011 is right.

### Local lateral observation

- 2026-07-28: High-detail inspection completed.
- The before/after depth profile remains closely matched: a broad shallow
  curved lower run rises progressively into the narrow upper shaft. The
  terminal remains faceted and blunt rather than becoming a spike.
- The after curve is marginally smoother/broader through the middle, but the
  characteristic silhouette and depth progression are preserved. There is no
  slab, flat carrier, inversion, fold, or abrupt local bulge.

State: `READY_TO_INSPECT_LOCAL_WRIST_AXIAL`

Next image operation:

- Inspect `review/local/pair--wrist_axial.png` at high detail to test the
  terminal cross-section and curve from the axial direction. Source is left
  and Repair 011 is right.

### Local wrist-axial observation

- 2026-07-28: High-detail inspection completed.
- The distinctive hooked/J-shaped axial silhouette, curled lower tip, faceted
  shaft, and broad upper cap remain present after the repair. Depth ordering
  and the central concavity are preserved.
- The current silhouette is a small coherent displacement of the source, not a
  collapse, reversal, spike, or flattening.

State: `READY_TO_BUILD_CANONICAL_CONTEXT_PAIRS`

Next image operation:

- Build font-free source-left/current-right pairs from the already sanitized
  canonical wrist-axial and dorsal-lateral-three-quarter renders.
- Immediately sanitize the pair pages in place, record their sizes, and only
  then inspect at high detail for registration, gap closure, fusion, and
  adjacent damage.

## Canonical context-pair result

- 2026-07-28: Both source-left/current-right pairs were generated and
  immediately sanitized in place.

| sanitized pair | bytes | direct review |
| --- | ---: | --- |
| `review/pair--wrist_axial.png` | 1578216 | true |
| `review/pair--dorsal_lateral_three_quarter.png` | 1346101 | true |

- Both are sRGB, 8-bit, no alpha, metadata/profile stripped, orientation
  normalized, and below `10,000,000` bytes. Neither has been inspected.

State: `READY_TO_INSPECT_CONTEXT_WRIST_AXIAL`

Next image operation:

- Inspect `review/pair--wrist_axial.png` at high detail. Source is left and
  Repair 011 is right.

### Canonical wrist-axial context observation

- 2026-07-28: High-detail inspection completed.
- The wrist opening, large central negative space, outer cuff rings, and the
  visible side loops remain registered. Their openings remain open and no
  adjacent parts fuse into the Component 36 region.
- No new wall, bridge, slab, spike, or obvious depth inversion appears. The
  after image reads as the same layered wrist assembly with a bounded local
  displacement.

State: `READY_TO_INSPECT_CONTEXT_DORSAL_LATERAL`

Next image operation:

- Inspect `review/pair--dorsal_lateral_three_quarter.png` at high detail for
  the long hook/cable's registration along the forearm and collateral surface
  damage. Source is left and Repair 011 is right.

### Canonical dorsal-lateral context observation

- 2026-07-28: High-detail inspection completed.
- The wrist-to-forearm composition, circular wrist plates, nested rails,
  negative spaces, lower shell, and separated upper-arm masses remain
  registered. No propagated seam, fusion, bridge, gap closure, spike, slab,
  flattening, or obvious adjacent damage is visible.
- Together with the three local-detail views, this is sufficient evidence to
  classify the bounded visual delta.

## Final classification

- Result: `pass`.
- Candidate disposition: `retain_candidate`.
- `does_this_repair_delta_look_ass: false`.
- Fitted-surface promotion: deferred; global anatomical clearance still fails.
- First concrete failure outside this repair's bounded claim: the resulting
  whole candidate still has `278` below-cutter vertices, `297`
  reserved-margin failures, and `692` triangle overlaps.
- Review record:
  `validation_reviews/geometry_repair/repair_011_component_36_regional/review.json`.

State: `DONE`
