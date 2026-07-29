# Repair 013 Component 19 cluster-rigid validation checkpoint

## Assignment

- Validation-only review of
  `blender_files/experiments/geometry_repair/repair_013_component_19_cluster_rigid_r6.blend`.
- Full objects: `EVAL_REPAIR_013_COMPONENT_19_BEFORE` and
  `EVAL_REPAIR_013_COMPONENT_19_AFTER`.
- Detail objects: `EVAL_REPAIR_013_COMPONENT_19_DETAIL_BEFORE` and
  `EVAL_REPAIR_013_COMPONENT_19_DETAIL_AFTER`.
- Numerical report:
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/build_report.json`.
- Do not modify shared models, scripts, docs, or `classification.json`.

## Claims

1. Component 19 remains recognizable and registered.
2. The `5.430353 mm` cluster motion over `53` affected vertices creates no
   spike, slab, flattening, inversion, abrupt seam, fusion, gap closure, or
   collateral upper-arm damage.
3. Explicitly answer `does_this_repair_delta_look_ass`.
4. Retain or reject the candidate.

## Image-safety protocol

- Checkpoint every image operation before and after it runs.
- Immediately sanitize every generated derivative using the repository
  ImageMagick sanitizer: strip metadata/profiles, normalize orientation,
  convert to sRGB, use conventional 8-bit PNG/JPEG, and remove alpha.
- Record source and sanitized paths and file sizes.
- Never inspect a derivative larger than `10,000,000` bytes.
- Inspect only sanitized derivatives, at high detail first.

## Text-only evidence

- Topology is unchanged at `7,347` vertices and `12,564` faces; face indices
  and material assignments remain unchanged.
- The repair clears all Component 19 cutter and reserved-margin failures.
- Global cutter penetrations improve `265 -> 258`, reserved-margin failures
  improve `282 -> 275`, and triangle overlaps improve `675 -> 653`.
- No negative-orientation locator is reported.
- Affected-edge ratios are `0.827474` minimum, `0.999991` median, `1.044190`
  p95, and `1.088134` maximum.
- Text-only Blender inspection confirms the detail objects exist. Before
  dimensions are `101.480 x 82.880 x 110.732 mm`; after dimensions are
  `104.228 x 84.880 x 108.825 mm`.

## Progress

- 2026-07-28: Validation initialized. No image has been generated or inspected.

## Recovery state

State: `READY_TO_RENDER_LOCAL_DETAIL`

Next image operation:

- Run the validation-owned local renderer at
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/render_local_detail.py`.
- Render matched dorsal, ventral, medial, lateral, two three-quarter, wrist
  axial, and bicep axial views of the detail objects at `900 x 900`.
- Write images to
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/local/`.
- Immediately sanitize every render through the repository ImageMagick helper,
  then record its path and size before inspection.

## Local-detail render result

- 2026-07-28: Blender completed 16 matched local-detail renders. Manifest:
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/local/manifest.json`.
- The manifest records every render's identical source/sanitized path because
  the sanitizer replaced the newly generated file in place immediately.
- All outputs are metadata/profile stripped, normalized, sRGB, 8-bit, without
  alpha, and marked `direct_image_model_review: true`.
- Sizes range from `486,606` to `591,556` bytes; all are below
  `10,000,000` bytes.
- No image has been inspected.

State: `READY_TO_BUILD_LOCAL_PAIRS`

Next image operation:

- Build font-free source-left/current-right pairs for all eight local views
  from the already sanitized renders using ImageMagick `+append`.
- Immediately sanitize each pair through the repository helper.
- Record each pair source mapping, sanitized path, and size before inspection.

## Local matched-pair result

- 2026-07-28: Eight source-left/current-right pairs were generated from the
  sanitized source/current renders and immediately sanitized again.

| sanitized pair | bytes | direct review |
| --- | ---: | --- |
| `pair--dorsal.png` | 842358 | true |
| `pair--ventral.png` | 820194 | true |
| `pair--medial.png` | 692494 | true |
| `pair--lateral.png` | 698790 | true |
| `pair--dorsal_lateral_three_quarter.png` | 877313 | true |
| `pair--ventral_medial_three_quarter.png` | 831928 | true |
| `pair--wrist_axial.png` | 593673 | true |
| `pair--bicep_axial.png` | 588142 | true |

- Source mappings are the corresponding already sanitized
  `source--<view>.png` and `current--<view>.png` files in the same directory.
- All pairs are stripped, normalized, sRGB, 8-bit, without alpha, and below
  `10,000,000` bytes. No image has been inspected.

State: `READY_TO_INSPECT_LOCAL_DORSAL_LATERAL_THREE_QUARTER`

Next image operation:

- Inspect
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/local/pair--dorsal_lateral_three_quarter.png`
  at high detail. Source is left and Repair 013 is right.
- Test overall recognizability plus spike, slab, flattening, inversion, seam,
  fusion, and gross gap closure. Stop early on decisive failure.

### Local dorsal-lateral three-quarter observation

- 2026-07-28: High-detail inspection completed.
- The broad faceted upper-arm plate, its paired raised longitudinal ribs,
  central peaked ridge, small side fin, and stepped dark side channel remain
  recognizable and closely registered.
- The after image shows only a bounded shift within the right-side transition.
  No new spike, slab, flattening, inversion, abrupt seam, fusion, or closed
  negative space is visible.

State: `READY_TO_INSPECT_LOCAL_BICEP_AXIAL`

Next image operation:

- Inspect
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/local/pair--bicep_axial.png`
  at high detail. Source is left; Repair 013 is right.
- Test cross-sectional depth, ridge spacing, local gap preservation, and any
  fold or fusion hidden in the three-quarter projection.

### Local bicep-axial observation

- 2026-07-28: High-detail inspection completed.
- The broad open U-shaped cross-section remains open. The left and right wings,
  deep central concavity, layered wall steps, and thin projecting tips retain
  their source depth ordering.
- The repaired right transition moves coherently without closing the opening,
  fusing opposite walls, reversing a layer, or forming a folded shelf.

State: `READY_TO_INSPECT_LOCAL_LATERAL`

Next image operation:

- Inspect
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/local/pair--lateral.png`
  at high detail for profile flattening, seam formation, pinching, and
  collateral movement around the repaired cluster.

### Local lateral observation

- 2026-07-28: High-detail inspection completed.
- The pointed upper fin, sloped plate, crosswise recessed channel, lower raised
  rail, and stepped lower edge remain closely matched.
- There is no visible profile flattening, pinched fold, seam, inverted surface,
  spike growth, or collateral motion outside the bounded transition.
- Local shape claims provisionally pass. Full-arm evidence remains necessary
  to verify upper-arm registration and surrounding-component separation.

State: `READY_TO_RENDER_CANONICAL`

Next image operation:

- Render all canonical matched views from
  `blender_files/experiments/geometry_repair/repair_013_component_19_cluster_rigid_r6.blend`
  using `scripts/blender/render_geometry_comparison.py`.
- Source: `EVAL_REPAIR_013_COMPONENT_19_BEFORE`; target:
  `EVAL_REPAIR_013_COMPONENT_19_AFTER`; resolution `1000 x 1400`.
- Output:
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/`.
- The renderer must immediately sanitize each PNG. Record manifest paths,
  source/sanitized mappings, and file sizes before any canonical inspection.

## Canonical render result

- 2026-07-28: Blender completed all 16 canonical renders. Manifest:
  `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/review/manifest.json`.
- Every generated path is also its sanitized path because the repository
  renderer immediately sanitized each PNG in place.
- The manifest records stripped metadata/profiles, normalized orientation,
  sRGB, 8-bit color, no alpha, and `direct_image_model_review: true`.
- Sizes range from `910,180` to `1,077,580` bytes, all under
  `10,000,000` bytes. No canonical image has been inspected.

State: `READY_TO_BUILD_CANONICAL_PAIRS`

Next image operation:

- Build source-left/current-right pairs from the already sanitized canonical
  `bicep_axial`, `dorsal_lateral_three_quarter`, and
  `ventral_medial_three_quarter` renders.
- Immediately sanitize each pair with the repository helper.
- Record sources, sanitized outputs, and sizes before high-detail inspection.

## Canonical matched-pair result

- 2026-07-28: Three canonical source-left/current-right pairs were generated
  and immediately sanitized.

| sanitized pair | bytes | direct review |
| --- | ---: | --- |
| `review/pair--bicep_axial.png` | 1502227 | true |
| `review/pair--dorsal_lateral_three_quarter.png` | 1355691 | true |
| `review/pair--ventral_medial_three_quarter.png` | 1312980 | true |

- Sources are the corresponding sanitized `source--<view>.png` and
  `current--<view>.png` files under `review/`.
- All pair outputs are stripped, normalized, sRGB, 8-bit, without alpha, and
  below `10,000,000` bytes. None has been inspected.

State: `READY_TO_INSPECT_CONTEXT_BICEP_AXIAL`

Next image operation:

- Inspect `review/pair--bicep_axial.png` at high detail. Source is left;
  Repair 013 is right.
- Test the full upper-arm opening, gaps between components, fusions, new walls,
  depth ordering, and collateral geometry.

### Canonical bicep-axial observation

- 2026-07-28: High-detail inspection completed.
- The large central upper-arm opening, layered surrounding shell, detached
  loops, side ornaments, and narrow negative-space slots remain present and
  registered.
- No component fusion, gap closure, new carrier wall, bridge, slab, spike, or
  depth-order inversion is visible. The repaired region does not produce a
  collateral silhouette change in the axial assembly.

State: `READY_TO_INSPECT_CONTEXT_DORSAL_LATERAL`

Next image operation:

- Inspect `review/pair--dorsal_lateral_three_quarter.png` at high detail for
  longitudinal registration, separation between upper-arm masses, transition
  seams, and collateral deformation.

### Canonical dorsal-lateral three-quarter observation

- 2026-07-28: High-detail inspection completed.
- The separated upper-arm masses retain their spacing, orientation, ridged
  silhouettes, and relationship to the elbow and wrist assemblies.
- No new transition seam, fused neighbor, slab, spike, gap closure, or
  collateral deformation is visible along the arm. The local move remains
  compositionally inconspicuous.

State: `READY_TO_INSPECT_CONTEXT_VENTRAL_MEDIAL`

Next image operation:

- Inspect `review/pair--ventral_medial_three_quarter.png` at high detail as the
  opposing final check for fusion, gap closure, displaced registration,
  inversion, and collateral upper-arm damage.

### Canonical ventral-medial three-quarter observation

- 2026-07-28: High-detail inspection completed.
- The opposing view preserves the upper-arm mass spacing, long raised ribs,
  fin-like edge details, elbow framing, forearm rails, and all major negative
  spaces.
- No fusion, gap closure, displaced registration, inversion, abrupt wall, or
  propagated damage is visible.

## Final classification

- `does_this_repair_delta_look_ass: false`
- Candidate disposition: `retain_candidate`
- Qualitative delta: `pass`
- Fitted-surface promotion: `deferred`
- Anatomical clearance: `fail` because the full candidate still contains
  `258` cutter penetrations, `275` reserved-margin failures, and `653`
  triangle overlaps.
- The bounded `5.430353 mm` cluster motion is visually coherent and does not
  damage the Component 19 identity or upper-arm composition.

State: `DONE`
