# V27 C9 landing-expansion face visual checkpoint

## 2026-07-29 — assignment accepted, before any image operation

Scope is limited to visual-role classification of exact source faces:

`2220, 2221, 2222, 2224, 2225, 2226, 2233, 2284`

Authority read before image work:

- project `AGENTS.md`;
- `docs/status.md`, especially the C9 landing-expansion dependency;
- `../checkpoint.md`;
- `../c9_landing_expansion_classification_review.md`; and
- `../v27_c9_landing_expansion_classification.json`.

The frozen classification authority says all eight are
`EXTERIOR_OR_AMBIGUOUS_IMMUTABLE`, inside the existing C9 maximum mask, not
terminal-incident, and not yet authorized for reconstruction. Faces `2229`
and `2283` are already selected wearer-side authority and are outside this
visual-classification set. Face `2283` participates in the exact protected
source-open route; any recommendation about neighboring expansion must retain
that route as a hard constraint.

Image authority:

- Blend:
  `/Users/supadava/Projects/experimental/silverhand/blender_files/experiments/geometry_repair/repair_014_joint_c9_c20_elbow_v24.blend`
- Blend size: `43,314,053` bytes
- Blend SHA-256:
  `68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823`
- Source object: `EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER`
- Blender executable:
  `/Applications/Blender.app/Contents/MacOS/Blender`
- ImageMagick executable: `/opt/homebrew/bin/magick`

Planned read-only image workflow:

1. Render only the local eight-face neighborhood from the exact Blend in
   Blender background mode. The source object will be copied in memory,
   targets will receive distinct colored overlays, and no Blend will be saved.
2. Retain raw renders for humans only. Do not inspect them.
3. Sanitize every raw render independently with:
   `magick RAW -auto-orient -strip -colorspace sRGB -depth 8 PNG24:SANITIZED`.
4. Record raw and sanitized paths, dimensions, sizes, and SHA-256 hashes.
5. Inspect only sanitized derivatives no larger than `10 MB`, at high detail
   first. No contact sheet will be generated or inspected.
6. Append observations and decisions here immediately after every image read.

No image has been generated, converted, or inspected at this checkpoint.
No source geometry has been mutated and no Blend has been saved.

## 2026-07-29 — render checkpoint, immediately before image generation

- Evidence-local script: `render_faces.py`
- Script SHA-256:
  `a672556b90115f40690ca1c8da1fc6a7961b7f85f0879ef24674232ad96de9f4`
- Confirmed `raw/` contains no files.
- The render script validates the eight exact face IDs, creates only in-memory
  context copies, overlays, labels, materials, and a camera, and has no Blend
  save operation.
- Planned outputs: four local group views with eight distinct highlights and
  sixteen exact-ID close-ups (normal and oblique for each face). No contact
  sheet.
- Exact command:

```text
/Applications/Blender.app/Contents/MacOS/Blender --background \
  /Users/supadava/Projects/experimental/silverhand/blender_files/experiments/geometry_repair/repair_014_joint_c9_c20_elbow_v24.blend \
  --python /Users/supadava/Projects/experimental/silverhand/_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/c9_expansion_face_visual/render_faces.py \
  -- --out /Users/supadava/Projects/experimental/silverhand/_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/c9_expansion_face_visual/raw
```

No image has yet been generated or inspected.

## 2026-07-29 — rendering DONE, immediately after image generation

- Blender exited `0` after writing exactly `20` expected raw PNGs:
  four group views and normal/oblique close-ups for all eight face IDs.
- All exact raw output paths, `720×720` dimensions, byte counts, and SHA-256
  hashes are recorded in `raw_manifest.tsv`.
- Raw sizes range from `554,415` to `678,794` bytes.
- Raw derivatives are explicitly marked `direct_image_model_review: false`;
  none has been inspected.
- Render manifest SHA-256:
  `434d544dcdba319cff8ae38a086aff298414ac06bf444fe6efc27d47d92ad5e4`
- Post-render source Blend SHA-256 remains:
  `68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823`.
  The source file was not saved or changed.
- Next image operation will sanitize all twenty raw files independently with:

```text
/opt/homebrew/bin/magick RAW \
  -auto-orient -strip -colorspace sRGB -depth 8 PNG24:SANITIZED
```

No image has been inspected.

## 2026-07-29 — sanitization DONE, before first image inspection

- All `20` raw files were independently converted with the exact recorded
  ImageMagick command.
- `sanitized_manifest.tsv` records every sanitized path, `720×720`
  dimensions, `sRGB` colorspace, `8`-bit depth, byte count, SHA-256, and review
  eligibility.
- Sanitized sizes range from `486,114` to `639,950` bytes.
- Every sanitized derivative is below `10 MB` and marked
  `direct_image_model_review: true`.
- Raw renders remain human-only and uninspected.
- No contact sheet exists.
- The first image inspection will read only
  `sanitized/group__front.png` at high detail. Its observation will be written
  here before any subsequent image read.

## 2026-07-29 — inspected `group__front` at high detail

- Sanitized derivative:
  `sanitized/group__front.png`
- The highlighted set lies on a long, narrow diagonal strip directly across a
  broad, plainly visible exterior armor plate. Orange, red, and cyan target
  regions are visible; several exact faces overlap or are occluded at this
  group scale.
- The strip is not hidden inside the sleeve cavity in this view. Its long
  exposed edge reads as visible plate surfacing/ridge composition.
- Group-level conclusion: at least the front-visible members are exterior
  composition evidence; blanket authorization of all eight would risk changing
  the visible game-model surface.
- Exact per-face decisions remain unresolved because labels are not legible and
  not every color is separately visible.
- Next image read:
  `sanitized/group__reverse.png` at high detail.

## 2026-07-29 — inspected `group__reverse` at high detail

- Sanitized derivative:
  `sanitized/group__reverse.png`
- The arm’s opposite and cavity-facing structure is visible, but none of the
  eight colored overlays appears through the shell.
- This is consistent with the highlighted faces belonging to the one-sided
  exterior plate seen in `group__front`, rather than to an independently
  visible wearer-facing inner layer.
- Exact IDs remain to be resolved from individual views.
- Next image read:
  `sanitized/group__side_a.png` at high detail.

## 2026-07-29 — inspected `group__side_a` at high detail

- Sanitized derivative:
  `sanitized/group__side_a.png`
- This view exposes the dense mechanical/wearer-side assembly and open sleeve
  cavity, but no colored target surface is visible.
- The target set is occluded from the mechanical side and remains consistent
  with an outward plate/ridge role.
- This angle adds no exact-ID attribution.
- Next image read:
  `sanitized/group__side_b.png` at high detail.

## 2026-07-29 — inspected `group__side_b` at high detail

- Sanitized derivative:
  `sanitized/group__side_b.png`
- The target overlays are again fully occluded while another outer/side shell
  region and a large intentional opening are visible.
- Across all four group views, the eight-face neighborhood is exposed only
  from the plate-front direction. This is strong group evidence for an
  exterior visible-composition role.
- Individual exact-ID views are still required because only part of the color
  set was visible in the front overview.
- Next image read:
  `sanitized/face_2220__normal.png` at high detail.

### Face 2220 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2220__normal.png`
- The red triangular face is directly visible on the narrow diagonal
  ridge/strip crossing the broad exterior elbow plate.
- Classification: `VISIBLE_EXTERIOR_RIDGE_SURFACE`.
- Uncertainty: low. The exact face is clearly colored and exposed.
- Reconstruction-authority recommendation: **no**. Moving or deleting it would
  alter a visible compositional ridge; it could join only under an exact
  appearance-preserving constraint that retains its exterior position and
  ridge line, which would not provide the desired boundary relocation.
- The oblique view is not needed to resolve its role.
- Next image read:
  `sanitized/face_2221__normal.png` at high detail.

### Face 2221 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2221__normal.png`
- The orange triangle is plainly exposed on the same diagonal exterior strip,
  immediately adjoining face `2220`.
- Classification: `VISIBLE_EXTERIOR_RIDGE_SURFACE`.
- Uncertainty: low.
- Reconstruction-authority recommendation: **no** unless its exact visible
  position and ridge continuity remain fixed; unconstrained relocation would
  harm visible composition.
- The oblique view is not needed to resolve its role.
- Next image read:
  `sanitized/face_2222__normal.png` at high detail.

### Face 2222 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2222__normal.png`
- The expected yellow overlay is not visible, despite the camera being aligned
  to the exact polygon normal and the surrounding exterior plate being clear.
- This suggests the face is occluded/internal from its recorded normal side,
  unlike faces `2220` and `2221`, but one view is insufficient for an exact
  classification.
- Classification remains `UNRESOLVED_OCCLUDED`.
- Uncertainty: medium.
- Next image read:
  `sanitized/face_2222__oblique.png` at high detail.

### Face 2222 — oblique view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2222__oblique.png`
- The yellow overlay remains fully occluded from the oblique normal-side view.
  Mechanical interior context is visible, but the exact triangle is not.
- Provisional classification:
  `CONCEALED_OR_INTERNAL`, not yet final.
- Uncertainty: medium. Two normal-side views support concealment, but a
  deliberately reversed local overlay is needed before authorizing mutation.
- Provisional reconstruction-authority recommendation: potentially **yes**,
  only if a reverse-side proof confirms it is not a visible opening/rim face
  and all barrier constraints on source edge `12914` are retained.
- Next image read:
  `sanitized/face_2224__normal.png` at high detail.

### Face 2224 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2224__normal.png`
- The green target overlay is not visible. The camera instead sees through the
  mechanical/wearer-side cavity and surrounding layered structure.
- Provisional classification: `CONCEALED_OR_INTERNAL`.
- Uncertainty: medium pending the already-sanitized oblique view.
- Next image read:
  `sanitized/face_2224__oblique.png` at high detail.

### Face 2224 — oblique view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2224__oblique.png`
- A small green triangular target is visible on an inner wall inside the large
  opening. It does not contribute the exterior arm silhouette or the broad
  outer plate, but it can be seen obliquely through intentional negative space.
- Classification: `WEARER_FACING_INNER_OPENING_SURFACE`.
- Uncertainty: low-to-medium; its inner-wall role is clear, while the exact
  degree of visibility in a worn pose is not established by this static view.
- Reconstruction-authority recommendation: conditionally **yes**. It may join
  a bounded landing reconstruction if the opening remains empty and its visible
  inner-wall continuity is reconstructed rather than filled or converted into
  a carrier.
- Next image read:
  `sanitized/face_2225__normal.png` at high detail.

### Face 2225 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2225__normal.png`
- The cyan face is a long, directly exposed triangle forming the central
  portion of the diagonal strip over the broad exterior plate.
- Classification: `VISIBLE_EXTERIOR_RIDGE_SURFACE`.
- Uncertainty: low.
- Reconstruction-authority recommendation: **no**. Its area and long edges are
  conspicuous parts of the exterior composition; relocating it would change
  the game-model-led appearance.
- The oblique view is not needed to resolve its role.
- Next image read:
  `sanitized/face_2226__normal.png` at high detail.

### Face 2226 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2226__normal.png`
- No blue target overlay is visible even in a tight normal-aligned view of the
  exterior plate.
- Provisional classification: `CONCEALED_OR_INTERNAL`.
- Uncertainty: medium pending the sanitized oblique view.
- Next image read:
  `sanitized/face_2226__oblique.png` at high detail.

### Face 2226 — oblique view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2226__oblique.png`
- The blue overlay remains fully occluded amid layered local shell geometry.
- Provisional classification:
  `CONCEALED_OR_INTERNAL`, not yet final.
- Uncertainty: medium. As with face `2222`, a reversed local overlay should
  establish whether it is a hidden/wearer-facing surface rather than a
  one-sided visible rim.
- Provisional reconstruction-authority recommendation: potentially **yes** if
  reverse-side evidence confirms concealment and the intentional opening
  remains unchanged.
- Next image read:
  `sanitized/face_2233__normal.png` at high detail.

### Face 2233 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2233__normal.png`
- A very narrow purple target is visible along the wall/rim of the large
  opening. It reads as a sliver edge surface rather than broad exterior plate.
- The frozen classification also records barrier edge `12919` between source
  faces `2233` and `2234`, increasing the importance of this rim role.
- Provisional classification: `VISIBLE_OPENING_RIM_OR_BARRIER_SURFACE`.
- Uncertainty: medium because the face is extremely narrow.
- Next image read:
  `sanitized/face_2233__oblique.png` at high detail.

### Face 2233 — oblique view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2233__oblique.png`
- The purple sliver is clearly visible beneath an exterior overhang, forming
  an underside/rim transition at the opening rather than a concealed interior
  fill surface.
- Classification: `VISIBLE_OPENING_RIM_BARRIER_SURFACE`.
- Uncertainty: low-to-medium; the narrowness is clear, but the exact face is
  nevertheless exposed in two distinct views.
- Reconstruction-authority recommendation: **no**. Preserve face `2233` and
  barrier edge `12919`; moving it would change an exposed opening/overhang
  boundary.
- Next image read:
  `sanitized/face_2284__normal.png` at high detail.

### Face 2284 — normal view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2284__normal.png`
- No magenta target overlay is visible in the normal-aligned close-up.
- Provisional classification: `CONCEALED_OR_INTERNAL`.
- The frozen classification records barrier edge `10392` between faces `2167`
  and `2284`; a hidden classification cannot override that exact barrier.
- Uncertainty: medium pending the sanitized oblique view.
- Next image read:
  `sanitized/face_2284__oblique.png` at high detail.

### Face 2284 — oblique view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2284__oblique.png`
- The magenta overlay remains fully occluded in a view that exposes much of the
  wearer-side mechanical assembly.
- Provisional classification:
  `CONCEALED_OR_INTERNAL`, not yet final.
- Uncertainty: medium. A reversed overlay is warranted because the face is
  completely hidden from both recorded normal-side views.
- Provisional reconstruction-authority recommendation: potentially **yes** if
  reverse-side evidence confirms an internal role, but barrier edge `10392`
  must remain exact.

## 2026-07-29 — targeted reverse-render decision, before image generation

Faces `2222`, `2226`, and `2284` remain uncolored/occluded in both normal and
oblique views. A bounded second render will place the overlay `0.15 mm` toward
the reverse side and align the camera to `-normal`. This is needed to
distinguish a concealed/wearer-side triangle from an unresolved visible rim.
No other faces will be rendered.

No second-round image has yet been generated, converted, or inspected.

## 2026-07-29 — targeted reverse-render checkpoint, immediately before image generation

- Script: `render_reverse_faces.py`
- Script SHA-256:
  `b8fea98385465470d008b0abae333b68bfa07c942cf2b7cc9075669d2384a542`
- Confirmed no exact-face `face_<id>__reverse.png` outputs exist.
- Exact command:

```text
/Applications/Blender.app/Contents/MacOS/Blender --background \
  /Users/supadava/Projects/experimental/silverhand/blender_files/experiments/geometry_repair/repair_014_joint_c9_c20_elbow_v24.blend \
  --python /Users/supadava/Projects/experimental/silverhand/_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/c9_expansion_face_visual/render_reverse_faces.py \
  -- --out /Users/supadava/Projects/experimental/silverhand/_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/c9_expansion_face_visual/raw
```

Expected outputs are three raw `720×720` PNGs. They will remain uninspected
until independently sanitized and size-checked.

## 2026-07-29 — targeted reverse rendering DONE, before sanitization

- Blender exited `0` and wrote exactly:
  - `raw/face_2222__reverse.png` — `586,406` bytes, SHA-256
    `bc483ed275b8c63c75369d0c1eaabacb10c70312b977109fbd965c8abd8bcb18`;
  - `raw/face_2226__reverse.png` — `683,025` bytes, SHA-256
    `722b5a1c3a7bcd187bbe8273631fbe056e049d97d1f24a1a96dcbc1a2c8dcacd`;
  - `raw/face_2284__reverse.png` — `617,390` bytes, SHA-256
    `2b3d8b6e5c58c3792e74d64308bc2e16d3abc2b34b91309b2966db6af10941da`.
- The same records were appended to `raw_manifest.tsv` with
  `direct_image_model_review: false`.
- Reverse render manifest SHA-256:
  `2d3f1420b3357ab972056f8a2a6befca2e76d9f201968212055d2b872a103beb`.
- Source Blend SHA-256 remains unchanged:
  `68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823`.
- No raw image has been inspected.
- Next image operation: sanitize these three files independently with the
  recorded ImageMagick command.

## 2026-07-29 — targeted reverse sanitization DONE, before inspection

- `sanitized/face_2222__reverse.png` — `720×720`, sRGB, 8-bit,
  `526,555` bytes, SHA-256
  `14cdde3bd6a213d05a451ba93444202b7d7e1d8166cc42e637a2d87e142a1597`.
- `sanitized/face_2226__reverse.png` — `720×720`, sRGB, 8-bit,
  `648,110` bytes, SHA-256
  `ad1f77edae0f11db7454770e32609362cdf46ecec3b669ffb1d828314fb31585`.
- `sanitized/face_2284__reverse.png` — `720×720`, sRGB, 8-bit,
  `563,161` bytes, SHA-256
  `d622aceff4d88e7ce744da61e07dd81342de8d578abf31b4b597d33baf5a728d`.
- All are below `10 MB`; `sanitized_manifest.tsv` marks each
  `direct_image_model_review: true`.
- Raw reverse files remain uninspected.
- Next image read:
  `sanitized/face_2222__reverse.png` at high detail.

### Face 2222 — reverse view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2222__reverse.png`
- A tiny yellow target is visible only from the reverse side, recessed inside a
  layered notch. It does not form the broad exterior plate or the arm
  silhouette.
- Classification: `RECESSED_WEARER_SIDE_OR_INTERNAL_NOTCH_SURFACE`.
- Uncertainty: medium-low; the recessed role is visible, but the target is
  small at this framing.
- Reconstruction-authority recommendation: conditionally **yes**, provided
  barrier edge `12914` and the notch/open-space boundary are preserved. It
  should not be treated as permission to fill the recess.
- Next image read:
  `sanitized/face_2226__reverse.png` at high detail.

### Face 2226 — reverse view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2226__reverse.png`
- The blue overlay is still fully occluded even when both overlay offset and
  camera direction are reversed. The view clearly exposes the sleeve cavity
  and layered rim around it.
- Classification: `FULLY_CONCEALED_INTERNAL_SURFACE`.
- Uncertainty: medium. The evidence is absence-based, but it is consistent
  across normal, oblique, reverse, and group views.
- Reconstruction-authority recommendation: conditionally **yes**. A bounded
  reconstruction of this face is unlikely to harm visible composition, but it
  must not fill or shrink the surrounding intentional opening.
- Next image read:
  `sanitized/face_2284__reverse.png` at high detail.

### Face 2284 — reverse view inspected at high detail

- Sanitized derivative:
  `sanitized/face_2284__reverse.png`
- A possible very thin magenta trace appears along the left inner rim, but it
  is too small to distinguish confidently from antialiasing or neighboring
  dark geometry.
- Provisional classification:
  `POSSIBLE_VISIBLE_OPENING_RIM_BARRIER_SURFACE`.
- Uncertainty: high. Barrier edge `10392` argues for preservation, but the
  high-detail view is not visually decisive.
- Per project rules, original detail is now justified for this specific
  sanitized derivative because high detail is unclear.
- Next image read:
  the same `sanitized/face_2284__reverse.png` at original detail.

### Face 2284 — reverse view inspected at original detail

- Sanitized derivative:
  `sanitized/face_2284__reverse.png`
- Original detail does not resolve the possible magenta trace. No confident
  exact-face visual claim can be made from this framing.
- Classification remains unresolved with high uncertainty.
- Decision: generate a bounded three-ring topology cutaway for face `2284`
  only. The cutaway will retain exact source coordinates and winding, show
  adjacent faces in grey, and place magenta overlays on both sides of the
  target so its local opening/barrier role is observable. This is an
  in-memory evidence copy, not source mutation.
- No cutaway image has yet been generated, converted, or inspected.

## 2026-07-29 — face 2284 cutaway checkpoint, immediately before image generation

- Script: `render_2284_cutaway.py`
- Script SHA-256:
  `67baef311d5f9aa61ff18eaf758ebfa4c3d2931f4ad6b80c0a2e39e184a9f51a`
- Confirmed no `face_2284__local*.png` outputs exist.
- Exact command:

```text
/Applications/Blender.app/Contents/MacOS/Blender --background \
  /Users/supadava/Projects/experimental/silverhand/blender_files/experiments/geometry_repair/repair_014_joint_c9_c20_elbow_v24.blend \
  --python /Users/supadava/Projects/experimental/silverhand/_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/c9_expansion_face_visual/render_2284_cutaway.py \
  -- --out /Users/supadava/Projects/experimental/silverhand/_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v27/c9_expansion_face_visual/raw
```

Expected output: two local, individual PNGs and one text topology manifest.
Raw images will remain uninspected.

## 2026-07-29 — face 2284 cutaway rendering DONE, before sanitization

- Blender exited `0` and wrote:
  - `raw/face_2284__local_reverse.png` — `444,698` bytes, SHA-256
    `eb6afcb7745d1234b1a02365cc82c733e06effc615da2cd545a5141d262d0062`;
  - `raw/face_2284__local_oblique.png` — `440,868` bytes, SHA-256
    `c1f9de8ecf205094f9b804d9ba4e2908c70a79697c658d7429e895590c293521`.
- `face_2284_cutaway_manifest.txt` records the exact `88` source faces and `60`
  source vertices in the three-ring context. Manifest SHA-256:
  `d6218746a815eb5a5f907f797c596da0be721de87e133d10b7d406dd7000a69b`.
- The raw records were appended to `raw_manifest.tsv` and marked
  `direct_image_model_review: false`.
- Source Blend SHA-256 remains unchanged:
  `68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823`.
- No raw cutaway has been inspected.
- Next image operation: sanitize both cutaways independently with the recorded
  ImageMagick command.

## 2026-07-29 — face 2284 cutaway sanitization DONE, before inspection

- `sanitized/face_2284__local_reverse.png` — `720×720`, sRGB, 8-bit,
  `349,928` bytes, SHA-256
  `759bfc72beea55b15450adcd21e2433721529c1810bf1cc977744c765448adec`.
- `sanitized/face_2284__local_oblique.png` — `720×720`, sRGB, 8-bit,
  `344,743` bytes, SHA-256
  `e0edf4e9c141f31354cbbda144a59f99b565a2901cee3aa9db4d2ea2ce0ea464`.
- Both are below `10 MB` and marked
  `direct_image_model_review: true` in `sanitized_manifest.tsv`.
- Raw cutaways remain uninspected.
- Next image read:
  `sanitized/face_2284__local_reverse.png` at high detail.

### Face 2284 — local reverse cutaway inspected at high detail

- Sanitized derivative:
  `sanitized/face_2284__local_reverse.png`
- The magenta target is a substantial triangular underside face within the
  bounded three-ring patch, adjoining a sharp folded boundary rather than an
  isolated buried triangle.
- This resolves the prior visibility failure as full-scene occlusion, not
  degenerate area.
- Its exact role relative to the fold/opening boundary will be checked in the
  already-sanitized local oblique view.
- Next image read:
  `sanitized/face_2284__local_oblique.png` at high detail.

### Face 2284 — local oblique cutaway inspected at high detail

- Sanitized derivative:
  `sanitized/face_2284__local_oblique.png`
- The magenta triangle is an inward/underside fold face. It is structurally
  adjacent to a sharp local boundary but was occluded in every full-scene
  normal, oblique, reverse, and group view.
- Classification: `CONCEALED_INNER_FOLD_BARRIER_SURFACE`.
- Uncertainty: low-to-medium. The local role is clear; visibility evidence is
  based on repeated full-scene occlusion.
- Reconstruction-authority recommendation: conditionally **yes**, provided
  exact barrier edge `10392` remains coincident and the neighboring face
  `2283` source-open-route constraint remains untouched. Expansion must not
  bridge, fill, or narrow that protected route.
- No further image operation is needed.

## 2026-07-29 — final durable checkpoint

Machine-readable conclusion: `classification.json`.

Text conclusion: `conclusion.md`.

Final face sets:

- keep immutable: `2220, 2221, 2225, 2233`;
- conditional authority-expansion candidates:
  `2222, 2224, 2226, 2284`;
- unresolved: none.

No recommendation authorizes automatic mask expansion. Conditional candidates
retain their exact barrier and negative-space constraints. Face `2284` also
retains neighboring face `2283`'s protected source-open-route constraint:
never bridge, fill, or narrow that route.

Evidence/provenance audit:

- JSON syntax audit: DONE.
- Raw PNG count: `25`.
- Sanitized PNG count: `25`.
- Missing sanitized derivatives: none.
- Extra sanitized derivatives: none.
- Maximum sanitized size: `648,110` bytes, below `10 MB`.
- Raw images inspected: false.
- Contact sheet generated or inspected: false.
- Source geometry changed: false.
- Blend saved: false.
- Classification SHA-256:
  `462cb09cb55aba274612363f6af8d2f7be23b966b88e1d1df867bcc37cfeb48c`.
- Conclusion SHA-256:
  `2e1601c5f041aecdd07ec01b9f9738af52d58d2fbcc2798b5033884f710936f7`.
- Raw manifest SHA-256:
  `d2e79d3db9d30a2e9243b729dc1158b4d7527a0f093c15f24b5b7bcc3add84de`.
- Sanitized manifest SHA-256:
  `a70d08c65f94e2334d5447423a5db07c2fef686a5ae00f0d9e5b839c992a178c`.

Artifacts remain uncommitted for the parent to review and integrate.
