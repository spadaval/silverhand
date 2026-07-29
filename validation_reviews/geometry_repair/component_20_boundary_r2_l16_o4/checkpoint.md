# Component 20 boundary reconstruction review checkpoint

Mission: `component-20-boundary-r2-l16-o4-review`

Status: `COMPLETE`

## Scope and claims under validation

- Experiment scene:
  `blender_files/experiments/geometry_repair/component_20_boundary_r2_l16_o4.blend`
- Source object: `EVAL_C20_BOUNDARY_R2_L16_O4_BEFORE`
- Target object: `EVAL_C20_BOUNDARY_R2_L16_O4_AFTER`
- Numerical report:
  `_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/build_report.json`
- Working image evidence:
  `_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/`

Claims:

1. The reconstruction preserves the exterior composition and intentional
   negative space of component 20 while replacing two wearer-facing patches.
2. It introduces no new visible hole, seam, kink, bridge, carrier-like slab,
   spike, flattening, registration loss, or depth inversion.
3. The visual result supports either
   `pass/continue_to_application_candidate` or `fail/reject_method`.
4. This evaluation does not promote a fitted-surface master; exact clearance
   still fails.

Known numerical evidence from `build_report.json`:

- connected components: `64 -> 64`
- boundary/nonmanifold edges: `1756 -> 1756`
- noncontiguous manifold edges: `0 -> 0`
- cutter penetrations: `309 -> 194`
- cutter triangle overlaps: `741 -> 519`
- replacement triangle overlaps: `42`
- source faces removed: `526`
- replacement strip faces added: `1451`

## 2026-07-28 initialization

Read the Agent Factory `validate` procedure and the current project design,
status, validation, glossary, history, component-20 method history, build
report, render script, and launcher. No image has been generated, converted,
or inspected in this mission yet.

The repository already contains unrelated in-progress work. This review owns
only this checkpoint, its sibling `review.json`, and the mission's `review/`
image directory.

### Next exact action

Generate the eight matched canonical source/current view pairs at
`1000 x 1400` by running:

```sh
BLEND_FILE="$PWD/blender_files/experiments/geometry_repair/component_20_boundary_r2_l16_o4.blend" \
  ./scripts/tools/run_blender_script.sh \
  scripts/blender/render_geometry_comparison.py \
  --source EVAL_C20_BOUNDARY_R2_L16_O4_BEFORE \
  --target EVAL_C20_BOUNDARY_R2_L16_O4_AFTER \
  --output "$PWD/_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/renders" \
  --resolution-x 1000 \
  --resolution-y 1400
```

The renderer sanitizes each generated image in place. After it completes,
verify the manifest sanitization records, ImageMagick metadata, and the
10,000,000-byte limit before any inspection.

## 2026-07-28 matched-view render generation

`DONE`: the exact command above generated all sixteen expected canonical
renders and `manifest.json` under `review/renders/`. Blender exited `0`.

The manifest reports that every render was sanitized in place with
ImageMagick, metadata stripped, orientation normalized, converted to 8-bit
sRGB without alpha, and marked `direct_image_model_review: true`. Reported
sizes range from `910,953` to `1,074,293` bytes.

Source fingerprint:
`118723ea1e1d53e35301be3db9ffbcdfbac011b740985007a70a16d3bb6479d8`

Target fingerprint:
`7f2841800b12751d79af220fa5e6be1f3f37918fd7facf20a082e5bfd8775b56`

Source and target dimensions are both
`273.384 x 343.689 x 319.263 mm`.

No render has been visually inspected.

### Next exact action

Before any visual inspection, mechanically verify every rendered file against
the manifest and with ImageMagick `identify`: expected dimensions
`1000 x 1400`, PNG, 8-bit sRGB, no alpha, no embedded profiles or properties,
and file size no greater than `10,000,000` bytes. Then record the result here.

## 2026-07-28 sanitizer verification attempt 1

`FAIL`: the verification shell loop used `path` as its iterator variable under
zsh. In zsh, `path` is tied to `PATH`, so the first assignment replaced the
executable search path and caused `stat` to fail with:

```text
zsh:11: command not found: stat
```

No image was inspected by a model. The manifest-level assertions completed
before the shell error, but the per-file metadata verification did not.

### Next exact action

Repeat the same read-only verification with a non-special iterator name
(`image_file`) and absolute `/usr/bin/stat`. Do not inspect any render until
all sixteen files satisfy the checks.

## 2026-07-28 sanitizer verification attempt 2

`DONE`: all sixteen files agree with the manifest and ImageMagick reports:

- format: PNG
- dimensions: `1000 x 1400`
- depth: 8-bit
- colorspace: sRGB
- channels: sRGB without alpha
- normalized orientation: `TopLeft`
- embedded profiles: none
- embedded properties: none
- largest file: `1,074,293` bytes

All files are below `10,000,000` bytes and are eligible for direct
high-detail image-model review. No render has been visually inspected yet.

## Pair-page generation pre-checkpoint

The next image operation will create eight bounded, font-free pair pages under
`review/pairs/`, one per canonical view. Each page will place the already
sanitized source render on the left and the already sanitized current render
on the right. ImageMagick will write each page as a stripped, auto-oriented,
8-bit sRGB `PNG24` image without alpha. No archival or full vertical contact
sheet will be created.

### Next exact action

For each canonical view, run ImageMagick `+append` on
`source--VIEW.png` and `current--VIEW.png`, followed in the same operation by
`-strip -auto-orient -colorspace sRGB -depth 8 -alpha off PNG24:OUTPUT`.
Then size- and metadata-check all eight pair pages before inspection.

## 2026-07-28 pair-page generation

`DONE`: generated and sanitized eight bounded pair pages under
`review/pairs/`. Each contains exactly one canonical source/current pair;
source is left and current is right. No labels, fonts, archive sheet, or
multi-row sheet were used. No pair page has been inspected yet.

### Next exact action

Use ImageMagick `identify` and filesystem sizes to verify all eight pair pages
are `2000 x 1400`, 8-bit sRGB PNGs without alpha, profiles, or properties and
no larger than `10,000,000` bytes. Only after that verification, inspect each
pair page at high detail.

## 2026-07-28 pair-page sanitizer verification

`DONE`: all eight pair pages are `2000 x 1400`, 8-bit sRGB PNGs without alpha,
profiles, or properties. Sizes range from `1,232,513` to `1,585,235` bytes.
All are below `10,000,000` bytes and eligible for high-detail review.

## Dorsal inspection pre-checkpoint

No image has yet been visually inspected. The next image operation is one
high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--dorsal.png`

Source is left; current is right. After inspection, write the observation
immediately before opening another image.

## Dorsal observation

High-detail review completed. The source and current outer silhouette, upper
mass, elbow framing, wrist cuff, long vertical rails, looped side cable, and
large central negative spaces remain registered. No new exterior hole, seam,
bridge, carrier-like slab, spike, flattening, or obvious depth inversion is
visible from this view. The current has a slightly brighter broad triangular
faceting area at the upper inner forearm, but its outline and neighboring rail
routes align; this view alone does not show whether that is a harmful inner
surface change.

Provisional dorsal classification: `pass`.

## Ventral inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--ventral.png`

Source is left; current is right. Write the observation immediately afterward.

## Wrist-axial crop observation

High-detail review completed. The current preserves the main upper-right
opening, inner rim, external loops, outer layered circumference, and depth
ordering around the rim. The large central wearer-facing surface already
exists in the source; the reconstruction changes its triangulation, contour,
and shading into a somewhat smoother form but does not close the adjacent
negative space or create a new global backing across the whole cross-section.
There is no obvious new hole, free edge, spike, or detached strip. The local
surface is flatter, but this wrist view alone does not make the result
unacceptable.

Wrist-axial crop classification: `pass_with_visible_change`.

## Bicep-axial crop inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/crops/crop--bicep_axial.png`

Source is left; current is right. This crop decides whether the broad
cutter-conforming area is a bounded acceptable inner-surface replacement or a
visually destructive flattened carrier-like slab. Write the observation
immediately afterward.

## Bicep-axial crop observation

High-detail review completed. The crop confirms the failure seen in the
canonical bicep-axial page. The source inner surface contains pronounced
angular depth breaks, a central ridge network, and multiple stepped facets.
The current replaces most of that visible depth structure with one broad,
smooth, convex cutter-shaped field spanning nearly the entire center of the
cross-section. A small angular island remains near the lower-left/center, but
it reads as a detail placed on top of the new smooth carrier rather than
preserved layered composition.

The outer circumference, loops, rim, and gross registration remain aligned,
and no new free hole or spike is visible. Those successes do not offset the
large visible flattening and carrier-like slab. The visual defect is directly
within the requested rejection criteria and is clearer at high detail than at
complete-view scale.

Bicep-axial crop classification: `fail`.

`does_this_reconstruction_look_ass: true`

## Final classification

Result: `fail/reject_method`

Line-by-line claim results:

1. Exterior silhouette and major complete-view negative spaces:
   `pass`.
2. No new hole, gross seam, bridge across a major gap, spike, exploded
   component, or exterior registration loss: `pass`.
3. No flattening or carrier-like slab: `fail`.
4. Continue to application candidate: `fail`.
5. Fitted-surface promotion: `not-applicable`; this was evaluation-only and
   exact clearance remains failed.

First concrete failure: the bicep-axial canonical view and bounded crop show
that the cutter-conforming replacement erases the source's angular inner depth
structure and replaces it with a broad smooth convex carrier-like field. This
is an in-scope method defect, not an image/tooling failure.

Numerical evidence remains valuable but cannot override the visual failure:
the method preserves `64` connected components, `1,756` boundary/nonmanifold
edges, and zero noncontiguous manifold edges while reducing penetrations
`309 -> 194` and overlaps `741 -> 519`; `42` replacement overlaps and exact
clearance failures remain.

No model, script, status, history, classification, or experiment file was
modified.

### Next exact action

Write sibling `review.json` with this classification, evidence inventory,
view results, numerical facts, explicit
`does_this_reconstruction_look_ass: true`, unresolved failures, and
application/promotion status. Then validate the JSON and owned-file diff.

## Ventral-medial crop observation

High-detail review completed. The crop confirms preservation of the major
wearer-facing composition and negative spaces. The current does not create a
bridge across the long arm opening or shoulder separation. Outer panels,
rails, the elbow cage, forearm contours, and wrist termination remain
registered. No new silhouette hole, seam, spike, or projecting slab edge is
visible. As in the complete view, the central inner replacement is mainly
occluded and must be judged axially.

Ventral-medial crop classification: `pass`.

## Wrist-axial crop inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/crops/crop--wrist_axial.png`

Source is left; current is right. Write the observation immediately afterward.

## Medial crop observation

High-detail review completed. The crop confirms the complete medial
registration and preservation of the long open span, cable routes, forearm
shell, upper ribbed mass, and rim boundaries. No new gross transition seam,
projecting kink, hole, bridge, slab edge, spike, or displaced element appears
in silhouette. It does not expose the central inner replacement as clearly as
the axial views.

Medial crop classification: `pass`.

## Ventral-medial crop inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/crops/crop--ventral_medial_three_quarter.png`

Source is left; current is right. Write the observation immediately afterward.

## Wrist-axial observation

High-detail review completed. The complete circumference, external loops,
outer layered rim, large internal opening, and internal depth order remain
registered. No new cap closes the main opening and no exterior spike or
exploded element appears. The large wearer-facing polygonal surface is present
in both source and current, but its triangulated contour/faceting changes
noticeably in the current. It does not obviously expand into a global carrier
or bridge the surrounding dark gaps, yet this is likely the reconstruction
region and requires a bounded crop before accepting the transition quality.

Provisional wrist-axial classification: `pass`, with a bounded crop required.

## Bicep-axial inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--bicep_axial.png`

This is a priority view. Source is left; current is right. Write the
observation immediately afterward.

## Bicep-axial observation

High-detail review completed. This view exposes the material visual change.
The source has an angular, visibly stepped and faceted wearer-facing inner
surface with several strong depth breaks. The current replaces much of that
with a broad, smooth, near-elliptical cutter-conforming surface. Although the
outer rim, loop features, circumference, and exterior registration remain
aligned, the current reads as substantially flatter and more carrier-like
across the center. This is not merely a color difference: the internal
silhouette, shading breaks, and depth landmarks change over a large visible
area.

Provisional bicep-axial classification: `fail` for visible flattening and a
carrier-like inner slab. A bounded high-detail crop is required to confirm
before final classification.

## Bounded crop generation pre-checkpoint

All eight canonical pair pages have now been reviewed at high detail. The
complete views preserve the exterior silhouette and large negative spaces, but
medial, lateral, ventral-medial, wrist-axial, and especially bicep-axial need
closer transition evidence.

The next image operation will create four font-free crop pairs from the
already-sanitized individual renders:

- `crop--medial.png`: `960 x 800+20+250` from each side
- `crop--ventral_medial_three_quarter.png`: `900 x 1200+50+50`
  from each side
- `crop--wrist_axial.png`: `880 x 980+60+140` from each side
- `crop--bicep_axial.png`: `880 x 1220+60+40` from each side

Each source crop will be placed left and its exact-coordinate current crop
right. ImageMagick will strip, auto-orient, convert to 8-bit sRGB PNG24, and
remove alpha. No archive sheet will be made.

### Next exact action

Generate these four crop pairs under `review/crops/`, then verify dimensions,
metadata, and the `10,000,000`-byte limit before inspection.

## 2026-07-28 bounded crop generation

`DONE`: all four specified crop pairs were generated and sanitized under
`review/crops/`. No crop has been inspected.

### Next exact action

Use ImageMagick `identify` and filesystem sizes to verify:

- medial: `1920 x 800`
- ventral-medial three-quarter: `1800 x 1200`
- wrist axial: `1760 x 980`
- bicep axial: `1760 x 1220`

Every file must be an 8-bit sRGB PNG without alpha, profiles, or properties and
no larger than `10,000,000` bytes. Do not inspect a crop until all checks pass.

## 2026-07-28 bounded crop sanitizer verification

`DONE`: all four crop pairs have the expected dimensions, are 8-bit sRGB PNGs
without alpha, profiles, or properties, and are below `10,000,000` bytes. The
largest is `1,308,796` bytes.

## Medial crop inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/crops/crop--medial.png`

Source is left; current is right. Write the observation immediately afterward.

## Dorsal-lateral three-quarter observation

High-detail review completed. The separated upper fragment, shoulder opening,
elbow mechanism, long structural gap, forearm silhouette, cable bundle, and
wrist edge remain in the same composition. The current does not introduce a
new connection between separated regions or fill a major negative space. No
new exterior hole, slab, spike, flattening, registration loss, or depth
inversion is visible.

Provisional dorsal-lateral three-quarter classification: `pass`.

## Ventral-medial three-quarter inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--ventral_medial_three_quarter.png`

This is a priority view. Source is left; current is right. Write the
observation immediately afterward.

## Ventral-medial three-quarter observation

High-detail review completed. The wearer-facing complete composition remains
registered: separated shoulder fragment, upper ribs, broad inner elbow mass,
long open forearm span, rails/cables, forearm shell, and wrist opening retain
their outlines and relative depth. The reconstruction does not visibly span
the large open arm gap or fill another intentional void. No new exterior hole,
spike, carrier-like slab, gross seam, flattening, registration loss, or depth
inversion is apparent at canonical scale. The exact transition strip remains
too small to exclude a subtle local kink.

Provisional ventral-medial three-quarter classification: `pass`, with a
bounded crop required.

## Wrist-axial inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--wrist_axial.png`

Source is left; current is right. Write the observation immediately afterward.

## Ventral observation

High-detail review completed. The broad upper-arm panels, diagonal rails,
elbow wheel, cage/loop assembly, forearm shell, wrist opening, and all visible
gaps align closely. The reconstructed area is not expressed as a new outer
slab or silhouette bulge. No new hole, open seam, kink, bridge across negative
space, spike, flattening, registration loss, or depth inversion is apparent.

Provisional ventral classification: `pass`.

## Medial inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--medial.png`

This is a priority view. Source is left; current is right. Write the
observation immediately afterward.

## Lateral observation

High-detail review completed. Overall silhouette, shoulder ribs, upper void,
elbow cage, circular junction, forearm shell, long cable routes, and wrist
edge remain aligned. The visible openings remain open and no new carrier-like
surface crosses them. No new exterior hole, slab, spike, exploded piece,
flattened mass, registration loss, or obvious depth inversion is visible.
Like the medial view, the local inner transition is too small for a confident
seam/kink judgment.

Provisional lateral classification: `pass`, with a bounded crop required.

## Dorsal-lateral three-quarter inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--dorsal_lateral_three_quarter.png`

Source is left; current is right. Write the observation immediately afterward.

## Medial observation

High-detail review completed. The paired arm is small in the canonical frame,
but the complete medial silhouette, upper ribbed mass, elbow voids, forearm
shell, longitudinal cables, wrist termination, and major negative spaces
remain registered. No new projecting slab, bridge, hole, spike, displaced
component, or obvious depth-order reversal is visible. The bounded
reconstruction itself is not legible enough at this scale to rule out a local
transition seam or kink.

Provisional medial classification: `pass`, with a bounded crop required.

## Lateral inspection pre-checkpoint

The next image operation is one high-detail inspection of:

`_validation/experiments/geometry_repair/component_20_methods/boundary_r2_l16_o4/review/pairs/pair--lateral.png`

This is a priority view. Source is left; current is right. Write the
observation immediately afterward.

## 2026-07-28 interrupted-run closeout

The preceding entries were appended as individual image operations completed,
so their order in this checkpoint is not chronological. The durable record is
nevertheless complete: all eight canonical pair pages and all four bounded
crop pages were sanitized, size-verified, and reviewed at high detail before
the original worker was interrupted.

No additional image was opened during closeout. The decisive existing
bicep-axial page and crop observations establish
`does_this_reconstruction_look_ass: true` because the method replaces the
source's stepped inner depth structure with a broad smooth carrier-like field.

`DONE`: wrote sibling `review.json` with result `fail`, disposition
`reject_method`, explicit visual-failure evidence, numerical facts, and
non-promotion status.
