# Repair 008 qualitative validation checkpoint

- Mission: `geometry-repair-008-review`
- Assigned scope: validate `REPAIR_008_COMPONENT_52_REGIONAL` relative to
  `REPAIR_007_COMPONENT_16_HARMONIC`.
- Classification constraint: `pass/retain_candidate` or
  `fail/reject_candidate`; no fitted-surface promotion.
- Source experiment:
  `_validation/experiments/geometry_repair/component_52_methods/regional_f35_trial/`
- Sanitized working directory:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/`

## Claims under validation

1. The Repair 008 delta does not introduce an unacceptable silhouette shift,
   registration drift, gap closure, fusion/bridge, spike, slab, flattening,
   depth inversion, or alteration to neighboring components.
2. The focused component-52 wrist detail and the full 839-vertex regional
   neighborhood remain visually credible relative to Repair 007.
3. The quantitative evidence supports retaining the candidate: topology and
   assignments are unchanged, no orientation reversal is reported, edge
   deformation remains bounded, and clearance improves.
4. Explicit question: `does_this_repair_delta_look_ass`.

## Text evidence captured before image work

- Patch: component 52; 24 component vertices; 8 initially violating vertices;
  839 affected vertices; 35.0 mm falloff; 5.516737 mm translation along
  `[0.549372, -0.388937, 0.73954]`.
- Topology: 7,347 vertices and 12,564 faces before and after; face indices and
  material assignments unchanged.
- Clearance: global penetrations 334 to 326; reserved-margin violations 346 to
  338; triangle overlaps 792 to 769; component-52 penetrations and
  reserved-margin violations both end at zero.
- Affected-edge ratios: minimum 0.857286, median 1.002336, p95 1.079319,
  maximum 1.185305.
- Negative orientation locators: zero.

## Operation 001 — sanitize bounded source/current views

Status before execution: `CHECKPOINTED_NOT_STARTED`.

Command intent:

- Copy each individual PNG named by the `local/manifest.json` and
  `complete/manifest.json` into the sanitized working directory with its
  dataset prefix.
- Run `scripts/image_sanitization.py::sanitize_image` on every copied image.
- Verify each derivative is a conventional 8-bit sRGB PNG without alpha and is
  at most 10,000,000 bytes.
- Do not open or inspect any source raster.

Planned inputs:

- `local`: 10 individual matched-view images at 800 x 800.
- `complete`: 16 individual matched-view images at 700 x 1000.

Status after execution: `DONE`.

- Command: copy the 26 manifest-listed PNGs, invoke
  `scripts.image_sanitization.py::sanitize_image` once per derivative, then
  inspect derivative metadata with `magick identify`.
- Outputs: 26 sanitized PNGs under the dataset-prefixed working directories.
- Verification: every output is 8-bit sRGB PNG, reports three sRGB channels
  (no alpha), and is below 571,000 bytes. Therefore all are below the
  10,000,000-byte direct-review ceiling.
- Source rasters were not opened or submitted to an image model.

## Operation 002 — compose font-free matched-view pairs

Status before execution: `CHECKPOINTED_NOT_STARTED`.

Command intent:

- For each view, join the already-sanitized `source` and `current` derivatives
  left-to-right with ImageMagick `+append`.
- Use no labels, fonts, annotations, or unsanitized inputs.
- Sanitize each newly generated pair with
  `scripts/image_sanitization.py::sanitize_image`.
- Verify all pairs are 8-bit sRGB PNGs without alpha and no larger than
  10,000,000 bytes.

Planned outputs:

- Five local-detail pairs: dorsal, ventral, medial, lateral, wrist axial.
- Eight complete-context pairs: dorsal, ventral, medial, lateral,
  dorsal-lateral three-quarter, ventral-medial three-quarter, wrist axial,
  bicep axial.

Status after execution: `DONE`.

- Command: ImageMagick font-free `+append` using sanitized source on the left
  and sanitized current on the right, followed by
  `scripts.image_sanitization.py::sanitize_image` on every pair and
  `magick identify`.
- Outputs: 13 matched-view pair PNGs in `sanitized_review/pairs/{local,complete}`.
- Verification: every pair is an 8-bit sRGB PNG with three sRGB channels and
  no alpha. Sizes range from 662,581 to 1,022,201 bytes; every pair is below
  the 10,000,000-byte direct-review ceiling.

## Operation 003 — high-detail local dorsal review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/local/dorsal--source-left_current-right.png`
- The pair is sanitized, 1,600 x 800, 866,551 bytes, and safe for direct
  high-detail review.
- Review target: component-52 detail displacement, dorsal silhouette,
  registration drift, gap closure, fusion/bridge, spike, slab, flattening,
  depth inversion, and neighboring-component alteration.

Status after execution: `DONE`.

Observation:

- Source is left in gray; current is right in cyan.
- The focused small wrist detail remains separated and recognizably the same
  thin angular part. Its visible shift is modest and coherent with a rigid
  clearance move.
- The surrounding lower edge and adjacent vertical/faceted constituents retain
  their silhouettes and open gaps. No new bridge, fused contact, spike, slab,
  flattening, or depth inversion is visible.
- No obvious neighboring-component deformation is visible in this view.

## Operation 004 — high-detail local lateral review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/local/lateral--source-left_current-right.png`
- The pair is sanitized, 1,600 x 800, 1,022,201 bytes, and safe for direct
  high-detail review.
- Review target: component-52 side profile, local spacing and registration,
  bridge/fusion, spike, slab, flattening, depth inversion, and neighboring
  parts.

Status after execution: `DONE`.

Observation:

- The local assembly remains an intentionally layered set of separate angular
  constituents. The repaired detail and its regional neighborhood show a small
  position change, but their edge character and thickness remain credible.
- Existing dark negative-space channels remain open. There is no new permanent
  contact, bridge, fusion, isolated spike, broad slab, obvious flattening, or
  reversed depth ordering.
- Adjacent rails and faceted plates retain their shapes; the delta does not
  visibly propagate as a kink into neighboring components.

## Operation 005 — high-detail local medial review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/local/medial--source-left_current-right.png`
- The pair is sanitized, 1,600 x 800, 1,004,904 bytes, and safe for direct
  high-detail review.
- Review target: medial outline and depth relationships, local gap preservation,
  registration drift, fusion/bridge, spike, slab, flattening, depth inversion,
  and neighboring parts.

Status after execution: `DONE`.

Observation:

- The repaired area retains the same compact, faceted medial profile. Fine
  pointed forms and long seams visible before the repair remain present after
  it; no novel spike appears.
- The narrow negative-space seams around the detail remain legible. No new
  closure, bridge, or fusion is visible.
- The repair does not turn the region into a slab or visibly flatten its
  multi-plane surface. Foreground/background ordering is consistent, with no
  apparent depth inversion or neighbor distortion.

## Operation 006 — high-detail local ventral review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/local/ventral--source-left_current-right.png`
- The pair is sanitized, 1,600 x 800, 809,130 bytes, and safe for direct
  high-detail review.
- Review target: wearer-facing silhouette and gaps, registration drift,
  fusion/bridge, spike, slab, flattening, depth inversion, and neighboring
  parts.

Status after execution: `DONE`.

Observation:

- The dominant wearer-facing plate and long channel above it retain the same
  broad outline and planar character. The repair does not create a new bulge,
  pinch, or slab.
- Small lower-edge constituents remain visibly separate; the pointed detail
  changes position modestly without closing adjacent negative space.
- No fusion, bridge, novel spike, flattening, depth inversion, or alteration to
  the large neighboring surface is visible.

## Operation 007 — high-detail local wrist-axial review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/local/wrist_axial--source-left_current-right.png`
- The pair is sanitized, 1,600 x 800, 994,221 bytes, and safe for direct
  high-detail review.
- Review target: component-52 wrist-detail outline and axial registration,
  closure of intentional openings, fusion/bridge, spike, slab, flattening,
  depth inversion, and neighboring parts.

Status after execution: `DONE`.

Observation:

- This is the clearest visible delta: the compact component-52 cluster shifts
  coherently in the expected clearance direction relative to the broad curved
  surface. Its internal faceting, thin pointed feature, and rectangular
  neighboring elements remain recognizable rather than stretching into a new
  form.
- The move enlarges rather than closes the dominant dark negative-space region.
  It does not create a new bridge or fusion.
- No isolated spike, slab, flattening, or depth inversion is apparent. The
  magnitude is noticeable in this deliberately tight axial crop, so complete
  context is required to determine whether it reads as unacceptable
  registration drift.

## Operation 008 — high-detail complete wrist-axial review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/wrist_axial--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 860,133 bytes, and safe for direct
  high-detail review.
- Review target: contextual acceptability of the axial wrist-detail shift,
  negative-space preservation, neighboring-component registration, and any
  new silhouette or depth defect.

Status after execution: `DONE`.

Observation:

- In complete wrist-axial context, source and current retain the same overall
  circumference, opening shape, layered rim, external loops, and internal
  constituent arrangement.
- The tight-crop component shift does not read as a broken registration at arm
  scale. The principal intentional opening remains open and no new fused mass,
  silhouette protrusion, depth inversion, or altered neighbor is apparent.

## Operation 009 — high-detail complete dorsal review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/dorsal--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 754,275 bytes, and safe for direct
  high-detail review.
- Review target: full-arm dorsal silhouette, wrist registration, preserved
  negative space, and any regional falloff kink or neighboring-component
  alteration.

Status after execution: `DONE`.

Observation:

- Full dorsal silhouettes match. The wrist opening, outer loop, long rails,
  separated forearm/upper-arm constituents, and intentionally open gaps remain
  aligned and legible.
- No falloff boundary, kink, new protrusion, gap closure, fusion, flattening, or
  neighboring-component change is visible at full-arm scale.

## Operation 010 — high-detail complete ventral review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/ventral--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 744,634 bytes, and safe for direct
  high-detail review.
- Review target: wearer-facing full-arm silhouette, regional transition,
  negative-space preservation, and neighboring-component alteration.

Status after execution: `DONE`.

Observation:

- Source and current preserve the same wearer-facing outline, wrist aperture,
  circular and rail details, and large intentional separations between
  constituents.
- No visible regional transition line, registration break, newly closed gap,
  fused bridge, spike, slab, flattening, depth inversion, or neighboring change
  appears at complete scale.

## Operation 011 — high-detail complete medial review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/medial--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 662,581 bytes, and safe for direct
  high-detail review.
- Review target: medial wrist/forearm registration, silhouette and negative
  space, falloff distortion, and neighboring-component alteration.

Status after execution: `DONE`.

Observation:

- Medial silhouettes and the large inter-constituent openings match. The long
  lower rails, wrist cluster, forearm panels, and upper-arm surfaces remain
  registered as the same composition.
- No visible kink at the 35 mm falloff, local fusion, gap loss, spike, slab,
  flattening, depth inversion, or neighbor displacement appears.

## Operation 012 — high-detail complete lateral review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/lateral--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 669,082 bytes, and safe for direct
  high-detail review.
- Review target: lateral wrist/forearm registration, silhouette and negative
  space, falloff distortion, and neighboring-component alteration.

Status after execution: `DONE`.

Observation:

- Lateral outer contours, central wrist assembly, long connecting rails, and
  large intentional gaps remain visually equivalent.
- No unacceptable registration drift, falloff kink, new contact, bridge,
  spike, slab, flattening, depth inversion, or neighboring-component
  alteration is visible.

## Operation 013 — high-detail complete dorsal-lateral three-quarter review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/dorsal_lateral_three_quarter--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 711,343 bytes, and safe for direct
  high-detail review.
- Review target: oblique wrist depth, regional transition, silhouettes,
  openings, bridges/fusions, and neighboring-component registration.

Status after execution: `DONE`.

Observation:

- Oblique depth relationships around the wrist and long constituent spans remain
  consistent. Circular details, layered wrist pieces, and open spaces retain
  their ordering and recognizable shapes.
- No regional crease, silhouette change, closed opening, bridge/fusion, spike,
  slab, flattening, depth inversion, or neighbor drift is visible.

## Operation 014 — high-detail complete ventral-medial three-quarter review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/ventral_medial_three_quarter--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 687,198 bytes, and safe for direct
  high-detail review.
- Review target: complementary oblique wrist depth, wearer-facing transition,
  negative-space preservation, and neighboring-component registration.

Status after execution: `DONE`.

Observation:

- Complementary oblique context preserves the same arm composition, wrist
  depth, upper/lower constituent separation, long negative spaces, and outer
  silhouette.
- No visible falloff transition, gap closure, bridge/fusion, spike, slab,
  flattening, depth inversion, or neighbor alteration is present.

## Operation 015 — high-detail complete bicep-axial review

Status before execution: `CHECKPOINTED_NOT_STARTED`.

- Input:
  `_validation/geometry_repair/repair_008_component_52_regional/sanitized_review/pairs/complete/bicep_axial--source-left_current-right.png`
- The pair is sanitized, 1,400 x 1,000, 805,451 bytes, and safe for direct
  high-detail review.
- Review target: distant upper-arm stability and absence of unintended regional
  propagation or neighboring-component alteration.

Retry checkpoint (`geometry-repair-008-review-resume`):

- Prior validator stalled during Operation 015 after Operations 001–014 were
  durably completed. Those operations will not be replayed.
- Text and filesystem verification confirm the exact input above is the
  already-sanitized derivative: PNG, 8-bit, sRGB, three color channels without
  alpha, 1,400 x 1,000, and 805,451 bytes.
- The input is below the 10,000,000-byte direct-review ceiling.
- Status before retry: `CHECKPOINTED_RETRY_NOT_STARTED`.

Status after retry: `DONE`.

Observation:

- The distant bicep-axial composition is visually stable between the gray
  source on the left and cyan current on the right. The dominant central
  faceted plate, perimeter layering, circular side detail, and open loop
  elements retain matching silhouettes, proportions, and depth ordering.
- No unintended regional propagation reaches the upper arm. There is no new
  kink, bulge, gap closure, bridge/fusion, spike, slab, flattening, depth
  inversion, or neighboring-component alteration visible in this view.

## Operation 016 — synthesis and retain/reject decision

Status: `DONE`.

- Operations 003–007 show that the focused component-52 wrist detail remains
  a recognizable thin, faceted constituent. The most visible change is a
  coherent clearance-direction shift in the tight wrist-axial crop; it
  enlarges the dominant negative space rather than closing it.
- Operations 008–015 show that the local shift remains compositionally
  credible in complete axial, orthogonal, oblique, and distant upper-arm
  context. No unacceptable registration break, falloff boundary, silhouette
  change, fusion/bridge, spike, slab, flattening, depth inversion, gap closure,
  or neighboring-component alteration is visible.
- Text evidence is compatible with retention: topology, face indices, and
  material assignments are unchanged; zero orientation reversals are reported;
  affected-edge ratios remain bounded; component-52 clearance violations reach
  zero; and global penetrations, reserved-margin violations, and triangle
  overlaps all improve.
- Explicit answer: `does_this_repair_delta_look_ass: false`.
- Result: `pass`.
- Candidate disposition: `retain_candidate`.
- Fitted-surface promotion remains false. The candidate still has 326 global
  cutter penetrations, 338 reserved-margin violations, and 769 triangle
  overlaps, so anatomical clearance remains a failing gate.
- Durable result:
  `validation_reviews/geometry_repair/repair_008_component_52_regional/review.json`.
- Validation: JSON parsing, required decision assertions, all 13 evidence-path
  byte-size matches, the 10,000,000-byte ceiling, and `git diff --check`
  completed successfully.
- Validation command retry note: the first size-check loop used zsh's special
  variable name `path`, which replaced the executable search path and caused
  `stat` to fail with `command not found`. Renaming the variable to
  `image_file` resolved the tooling error without changing evidence or result.
