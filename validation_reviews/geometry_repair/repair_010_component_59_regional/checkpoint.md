# Repair 010 component 59 regional validation checkpoint

Mission: `geometry-repair-010-review`

Scope: independently validate only `REPAIR_010_COMPONENT_59_REGIONAL` relative
to `REPAIR_009_COMPONENT_57_REGIONAL`. This review does not promote the fitted
surface and does not modify Blender data or repair implementation.

## Claims under validation

1. The component-59 cuff brace keeps its recognizable shape and registration
   against neighboring wrist layers.
2. The repair introduces no unacceptable gap closure, fusion, spike, carrier
   slab, flattening, depth inversion, or collateral wrist damage.
3. Numerical evidence remains compatible with a retainable candidate:
   topology and materials unchanged, zero negative-orientation locators,
   bounded edge deformation, and improved clearance.
4. `does_this_repair_delta_look_ass` is explicitly answered from the smallest
   bounded matched-view evidence that genuinely tests the claims.

## Text evidence captured before image handling

- Candidate: `REPAIR_010_COMPONENT_59_REGIONAL`
- Relative key: `REPAIR_009_COMPONENT_57_REGIONAL`
- Component: 59; component vertices: 40
- Initial violating vertices: 15
- Affected regional field: 1,018 vertices; falloff: 40.0 mm
- Translation: 14.739078 mm along
  `[0.724094, 0.671417, -0.157757]`
- Topology: 7,347 vertices and 12,564 faces before/after; face indices and
  material assignments unchanged
- Clearance: below-cutter vertices 309 -> 282; below-reserved-margin vertices
  328 -> 305; triangle overlaps 741 -> 701; component-59 below-cutter and
  below-margin vertices both end at 0
- Affected-edge ratios: min 0.506504, median 1.000260, p95 1.159507,
  max 1.475953
- Negative-orientation locators: 0

## Recovery state

State: `READY_TO_RENDER`

Next image operation:

- Render the canonical matched source/current views from
  `blender_files/experiments/geometry_repair/repair_010_component_59_regional_f40.blend`
  using `scripts/blender/render_geometry_comparison.py`, with source
  `EVAL_REPAIR_010_COMPONENT_59_BEFORE`, target
  `EVAL_REPAIR_010_COMPONENT_59_AFTER`, resolution 1000 x 1400, and output
  `_validation/experiments/geometry_repair/component_59_methods/repair_010_f40/review`.
- The renderer sanitizes each generated PNG immediately through
  `scripts.image_sanitization.sanitize_image` (ImageMagick: auto-orient, sRGB,
  metadata/profile stripping, 8-bit TrueColor PNG, alpha off).
- After the command, record its result, all generated paths, sanitization
  metadata, and file sizes before any image-model inspection.

## Canonical render result

Image operation completed successfully with Blender 5.2.0 LTS Beta. The
renderer wrote and immediately sanitized all 16 source/current PNGs. Manifest:

`_validation/experiments/geometry_repair/component_59_methods/repair_010_f40/review/manifest.json`

The manifest records matching cameras, source/current geometry fingerprints,
ImageMagick sanitization with metadata stripped, orientation normalized, sRGB,
8-bit TrueColor PNG, and alpha disabled.

| source / sanitized output | bytes | direct review |
| --- | ---: | --- |
| `source--dorsal.png` | 1029957 | true |
| `current--dorsal.png` | 1074493 | true |
| `source--ventral.png` | 1006773 | true |
| `current--ventral.png` | 1057496 | true |
| `source--medial.png` | 910953 | true |
| `current--medial.png` | 933067 | true |
| `source--lateral.png` | 919971 | true |
| `current--lateral.png` | 942152 | true |
| `source--dorsal_lateral_three_quarter.png` | 964402 | true |
| `current--dorsal_lateral_three_quarter.png` | 984200 | true |
| `source--ventral_medial_three_quarter.png` | 933125 | true |
| `current--ventral_medial_three_quarter.png` | 963134 | true |
| `source--wrist_axial.png` | 1020860 | true |
| `current--wrist_axial.png` | 1068587 | true |
| `source--bicep_axial.png` | 979423 | true |
| `current--bicep_axial.png` | 1030926 | true |

Every sanitized derivative is below 10,000,000 bytes. No image has been
opened yet.

State: `SANITIZED_CANONICAL_INPUTS_READY`

Next non-image operation:

- Inspect Blender object names and dimensions as text to resolve the supplied
  detail objects and choose a bounded local render before visual inspection.

## Detail-object resolution

Text-only Blender inspection found:

- `EVAL_REPAIR_010_COMPONENT_59_DETAIL_BEFORE`: 19.132 x 25.910 x 22.791 mm
- `EVAL_REPAIR_010_COMPONENT_59_DETAIL_AFTER`: 19.132 x 25.910 x 22.791 mm

The earlier `regional_f40_after009` experiment has the same build report as
Repair 010 except for the experiment file path. Its complete-view geometry
fingerprints exactly match the Repair 010 canonical render:

- source: `118723ea...6479d8`
- current: `c87f96f...ab0fb5`

That experiment already contains five tightly framed, matched-camera local
renders of the identical numerical candidate. Its old manifest predates
mandatory sanitization and records `sanitization: null`, so those files are
unsafe to inspect directly.

State: `READY_TO_DERIVE_SANITIZED_LOCAL_PAIRS`

Next image operation:

- Copy the five source/current local views from
  `_validation/experiments/geometry_repair/component_59_methods/regional_f40_after009/local/`
  into the Repair 010 `review/sanitized_local/` directory.
- Immediately sanitize every copied derivative in place with
  `scripts.image_sanitization.sanitize_image`.
- Build font-free source-left/current-right pages with ImageMagick `+append`,
  immediately sanitize every page again, and record all mappings and sizes.
- Do not inspect any old source file, copied file, or pair page until its
  sanitized size has been recorded as no more than 10,000,000 bytes.

## Sanitized local matched-pair result

Image operation completed. Every copied derivative and every generated
source-left/current-right pair was sanitized with ImageMagick before review.

| sanitized output under `review/sanitized_local/` | bytes | direct review |
| --- | ---: | --- |
| `source--dorsal.png` | 487928 | true |
| `current--dorsal.png` | 513234 | true |
| `pair--dorsal.png` | 881988 | true |
| `source--ventral.png` | 459446 | true |
| `current--ventral.png` | 492511 | true |
| `pair--ventral.png` | 830861 | true |
| `source--medial.png` | 473780 | true |
| `current--medial.png` | 515390 | true |
| `pair--medial.png` | 847621 | true |
| `source--lateral.png` | 456203 | true |
| `current--lateral.png` | 486343 | true |
| `pair--lateral.png` | 802419 | true |
| `source--wrist_axial.png` | 525334 | true |
| `current--wrist_axial.png` | 519817 | true |
| `pair--wrist_axial.png` | 1053941 | true |

All sanitized derivatives are 8-bit sRGB TrueColor PNGs without metadata,
profiles, orientation ambiguity, or alpha, and all are below 10,000,000 bytes.
No image has been opened yet.

State: `READY_TO_INSPECT_LOCAL_DORSAL`

Next image operation:

- Inspect `review/sanitized_local/pair--dorsal.png` at high detail. The source
  is left and Repair 010 is right.

### Local dorsal observation

High-detail inspection completed. The central cuff brace remains a coherent
faceted loop/bridge form. Its upper dark opening remains open, the front ledge
retains angular depth, and the flanking vertical plates remain separate. The
repair causes a broad outward shift and a modestly wider lower opening, but no
new fusion, spike, carrier slab, flattening, inverted depth order, or hard
falloff seam is visible. Registration against the long neighboring rails still
reads as intentional layered construction.

State: `READY_TO_INSPECT_LOCAL_VENTRAL`

Next image operation:

- Inspect `review/sanitized_local/pair--ventral.png` at high detail, source
  left and Repair 010 right.

### Local ventral observation

High-detail inspection completed. The cuff’s stepped underside and short
vertical struts remain recognizable and separately layered. Existing
horizontal channels beneath the large upper plate remain open; no brace is
dragged into the adjacent lower rail. The delta is broad and smooth rather than
an isolated pull. There is no visible new fusion, closed gap, needle spike,
backing slab, flattened brace, or depth-order reversal.

State: `READY_TO_INSPECT_LOCAL_MEDIAL`

Next image operation:

- Inspect `review/sanitized_local/pair--medial.png` at high detail, source left
  and Repair 010 right.

### Local medial observation

High-detail inspection completed. The large beveled cuff face keeps its
polygonal volume and rim; the long recessed channel beside it remains open and
continuous. The repaired assembly shifts outward and exposes somewhat more
negative space, but its faceted silhouette and depth hierarchy remain
coherent. No new interpenetration, fusion, abrupt spike, carrier wall, collapsed
channel, flattening, or inversion is visible.

State: `READY_TO_INSPECT_LOCAL_LATERAL`

Next image operation:

- Inspect `review/sanitized_local/pair--lateral.png` at high detail, source
  left and Repair 010 right.

### Local lateral observation

High-detail inspection completed. The cuff’s polygonal shell, inset border,
lower tabs, and adjacent pointed flange retain their original vocabulary. The
regional field increases separation between upper and lower wrist layers, but
does not close negative space or create a new connection. The pre-existing
pointed flange remains recognizable rather than becoming a needle-like
deformation. No flattened slab, fused edge, inverted layer order, or abrupt
falloff crease is apparent.

State: `READY_TO_INSPECT_LOCAL_WRIST_AXIAL`

Next image operation:

- Inspect `review/sanitized_local/pair--wrist_axial.png` at high detail, source
  left and Repair 010 right.

### Local wrist-axial observation

High-detail inspection completed. This is the largest visible delta: the cuff
brace and the broad neighboring wrist plate move outward by a substantial
fraction of the local 19–26 mm detail scale, consistent with the reported
14.739 mm translation. The wrist opening remains open and the layered pieces
remain separate, but their registration shifts enough that the repaired broad
plate occupies much more of the local frame while the opening moves toward the
outer edge. No fusion, spike, slab generation, flattening, or depth inversion
is visible. This view does not by itself establish whether the registration
change is acceptable at whole-wrist scale; a full wrist-axial pair is required.

State: `READY_TO_BUILD_COMPLETE_WRIST_PAIR`

Next image operation:

- Build a font-free source-left/current-right pair from the already sanitized
  Repair 010 canonical `source--wrist_axial.png` and
  `current--wrist_axial.png` using ImageMagick `+append`.
- Immediately sanitize the generated pair and record its size before
  inspection.

## Complete wrist-axial pair result

The generated source-left/current-right page was immediately sanitized:

- `review/pair--wrist_axial.png`
- size: 1,582,004 bytes
- metadata/profiles stripped; orientation normalized; sRGB; 8-bit TrueColor
  PNG; alpha off
- `direct_image_model_review: true`

State: `READY_TO_INSPECT_COMPLETE_WRIST_AXIAL`

Next image operation:

- Inspect `review/pair--wrist_axial.png` at high detail, source left and Repair
  010 right.

### Complete wrist-axial observation

High-detail inspection completed. At whole-wrist scale the opening remains
large, open, and continuous; the surrounding rings, side loops, and lower
layered details preserve their recognizable ordering. The repaired side is
somewhat fuller across the central inner plate and the upper-right opening
changes shape modestly, but the overall cuff silhouette and attachment rhythm
remain coherent. There is no closed aperture, fusion, new carrier slab, spike,
or depth inversion. The large local-frame shift does not read as objectionable
collateral damage at assembly scale.

State: `READY_TO_BUILD_COMPLETE_PROPAGATION_PAIRS`

Next image operation:

- Build font-free source-left/current-right complete pairs for dorsal,
  ventral, and dorsal-lateral-three-quarter views from the already sanitized
  canonical inputs.
- Immediately sanitize each generated pair and record its size before
  inspection.

## Complete propagation-pair result

All generated pages were immediately sanitized:

| page under `review/` | bytes | direct review |
| --- | ---: | --- |
| `pair--dorsal.png` | 1552785 | true |
| `pair--ventral.png` | 1510983 | true |
| `pair--dorsal_lateral_three_quarter.png` | 1345356 | true |

Each is metadata-free, orientation-normalized, 8-bit sRGB TrueColor PNG without
alpha, and below 10,000,000 bytes.

State: `READY_TO_INSPECT_COMPLETE_DORSAL`

Next image operation:

- Inspect `review/pair--dorsal.png` at high detail, source left and Repair 010
  right.

### Complete dorsal observation

High-detail inspection completed. The full arm silhouette, long dorsal rails,
upper-arm mass, elbow openings, wrist cuff, and major negative spaces remain
visually registered. The Repair 010 delta is confined to the wrist vicinity
and is not visible as an abrupt assembly-wide distortion. No collateral bridge,
slab, spike, or shifted upper-arm constituent is visible.

State: `READY_TO_INSPECT_COMPLETE_VENTRAL`

Next image operation:

- Inspect `review/pair--ventral.png` at high detail, source left and Repair 010
  right.

### Complete ventral observation

High-detail inspection completed. The ventral full-arm outline, circular wrist
detail, cage-like side loop, long lower rails, and open elbow separation remain
visually stable. The repaired wrist detail does not visibly fuse to the nearby
brace or drag the forearm shell. No new shelf, carrier surface, spike, or
propagated silhouette damage is apparent.

State: `READY_TO_INSPECT_COMPLETE_DORSAL_LATERAL_THREE_QUARTER`

Next image operation:

- Inspect `review/pair--dorsal_lateral_three_quarter.png` at high detail,
  source left and Repair 010 right.

### Complete dorsal-lateral three-quarter observation

High-detail inspection completed. The wrist assembly retains its nested rings,
small circular plates, side cage, long hanging rails, and intentional gaps.
The repair does not create an obvious kink at the wrist-to-forearm transition
or propagate into the separated upper shell. The full silhouette and component
rhythm remain credible.

## Final classification

- Claim 1, recognizable cuff-brace shape and neighboring registration:
  `pass`
- Claim 2, no unacceptable closure/fusion/spike/slab/flattening/inversion or
  collateral wrist damage: `pass`
- Claim 3, numerical evidence compatible with retention: `pass`
- Claim 4, sufficient bounded evidence to answer the qualitative prompt:
  `pass`
- `does_this_repair_delta_look_ass`: `false`
- Candidate disposition: `retain_candidate`
- Fitted-surface promotion: `deferred`
- Anatomical clearance: `fail` because 282 cutter penetrations, 305 reserved
  wall-margin failures, and 701 triangle overlaps remain globally

Important uncertainty: the local wrist-axial delta is large and the minimum
affected-edge ratio of 0.506504 represents nearly 49.4% contraction. The
assembly-scale views show no corresponding objectionable artifact, but Repair
010 should remain reversible until later structural and physical-detail gates.

State: `COMPLETE`

Durable result: `review.json` in this directory.
