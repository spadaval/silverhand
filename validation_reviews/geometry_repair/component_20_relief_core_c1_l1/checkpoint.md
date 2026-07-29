# Component 20 relief core C1 L1 validation checkpoint

## Assignment

- Role: disposable image-validation subagent.
- Subskill: Agent Factory `validate`.
- Experiment: `blender_files/experiments/geometry_repair/component_20_relief_core_c1_l1.blend`.
- Before object: `EVAL_C20_RELIEF_CORE_C1_L1_BEFORE`.
- After object: `EVAL_C20_RELIEF_CORE_C1_L1_AFTER`.
- Numerical report: `_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/build_report.json`.
- Evidence destination: `validation_reviews/geometry_repair/component_20_relief_core_c1_l1/`.
- Working render destination: `_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/review/`.

## Claims under validation

1. The translated component-20 cluster-1 faceted core preserves its recognizable local relief.
2. The one-layer 60-edge/120-triangle annulus does not read as a wall or slab.
3. The delta introduces no visible seam, spike, or unintended gap closure.
4. The delta introduces no depth inversion or registration loss.
5. Intentional negative space remains undamaged.
6. Overall disposition is retain or reject; `does_this_repair_delta_look_ass` must be answered explicitly.

## Text-only preflight

- `component_20_relief_core_c1_l1.blend` exists and is 33,598,426 bytes.
- `build_report.json` exists and reports `evaluation_only_not_approved`.
- Source core: 87 faces, 91 vertices, 60 transition edges.
- Motion: rigid translation of 32.556071 mm.
- Annulus: 1 layer, 120 faces.
- Numerical delta: below-cutter vertices 309 -> 296; triangle overlaps 741 -> 704.
- Topology delta: connected components 0; boundary edges 0; nonmanifold edges 0.
- Orientation: zero noncontiguous manifold edges before and after.
- Numerical evidence alone does not settle the visual claims.

## Image-safety protocol

- No unsanitized image will be inspected.
- Every generated render will be sanitized immediately with ImageMagick: auto-orient, strip metadata/profiles, convert to sRGB, remove alpha, write 8-bit PNG.
- Sanitized size will be recorded and must be no more than 10,000,000 bytes before inspection.
- Inspection starts at high detail and uses only bounded matched views.

## Timeline

- 2026-07-28: Checkpoint created before the first image operation.
- 2026-07-28: Read the repository comparison renderer. It uses the canonical
  matched orthographic camera rig and calls the shared ImageMagick sanitizer
  immediately after each render. Selected `1000 x 1400` canonical matched
  views as the smallest existing bounded proof surface that can reveal both
  cluster-local relief and whole-arm registration.

### Next exact action

Run:

```sh
BLEND_FILE="$PWD/blender_files/experiments/geometry_repair/component_20_relief_core_c1_l1.blend" \
  ./scripts/tools/run_blender_script.sh \
  scripts/blender/render_geometry_comparison.py \
  --source EVAL_C20_RELIEF_CORE_C1_L1_BEFORE \
  --target EVAL_C20_RELIEF_CORE_C1_L1_AFTER \
  --output "$PWD/_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/review/renders" \
  --resolution-x 1000 \
  --resolution-y 1400
```

Do not inspect any output until the manifest and ImageMagick metadata/size
checks prove that each file is a safe sanitized derivative.

## 2026-07-28 matched-view render generation

`DONE`: the exact command above completed with Blender exit code `0`. It
generated sixteen canonical renders plus `manifest.json` under
`review/renders/`.

The renderer's manifest reports immediate in-place ImageMagick sanitization for
every render:

- `metadata_stripped: true`
- `orientation_normalized: true`
- `colorspace: sRGB`
- `bit_depth: 8`
- `alpha: false`
- `direct_image_model_review: true`

Reported sanitized sizes range from 910,953 to 1,073,940 bytes, all below the
10,000,000-byte limit.

Source fingerprint:
`118723ea1e1d53e35301be3db9ffbcdfbac011b740985007a70a16d3bb6479d8`

Target fingerprint:
`fdc5a353e631891ff7553de40da93661c47c7621e23effe5ab6e0b1f21e3e583`

Source and target dimensions are both
`273.384 x 343.689 x 319.263 mm`.

No image has been visually inspected.

### Next exact action

Mechanically verify all sixteen outputs with ImageMagick `identify` and file
sizes. If every file is 1000 x 1400, 8-bit sRGB PNG without alpha and no more
than 10,000,000 bytes, generate one font-free side-by-side pair per view using
ImageMagick with the same strip/orientation/sRGB/8-bit/no-alpha options. Then
verify each pair before inspection.

## 2026-07-28 render safety verification

`PASS`: manifest query found zero sanitization violations.

`PASS`: ImageMagick independently identified all sixteen renders as:

- `1000 x 1400`
- 8-bit
- sRGB
- three-channel RGB without alpha
- normalized `TopLeft` orientation

Filesystem sizes range from 910,953 to 1,073,940 bytes. No file exceeds
10,000,000 bytes.

No image has been visually inspected.

### Next exact action

For each canonical view, generate
`review/pairs/<view>--source-left-current-right.png` from the verified source
and current render using ImageMagick `+append`, with `-auto-orient -strip
-colorspace sRGB -alpha off -depth 8 PNG24:` applied in the same command.

## 2026-07-28 sanitized matched-pair generation

`DONE`: generated eight font-free side-by-side pair images. Every pair was
created and sanitized in the same ImageMagick command.

`PASS`: ImageMagick identified every pair as `2000 x 1400`, 8-bit sRGB,
three-channel RGB without alpha, and normalized `TopLeft` orientation.

Filesystem sizes range from 1,237,187 to 1,588,447 bytes. All are below
10,000,000 bytes and eligible for high-detail inspection.

Pair convention: source/before is left; current/after is right.

No image has been visually inspected.

### Next exact action

Inspect the sanitized dorsal pair at high detail:
`_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/review/pairs/dorsal--source-left-current-right.png`.

## 2026-07-28 dorsal high-detail observation

Source is left; current is right.

The moved core remains broadly legible, but the transition fails the visual
claim in this view. At the inner/elbow-side middle of the assembly, current
shows a conspicuous fan of long, nearly coplanar triangular faces extending
leftward from the moved mass. It reads as a broad sharp shelf/wall with several
spike-like tips, replacing the source's deeper, compact negative-space opening.
This is not ordinary shading variation: the outer silhouette gains multiple
long horizontal/diagonal projections and the transition surface dominates the
local form.

Provisional classifications from dorsal:

- Relief preservation: `pass` for the rigidly moved core itself.
- No wall/slab: `fail`.
- No spike: `fail`.
- Negative-space preservation: `fail`; the source opening is visibly
  compressed/bridged by the annulus.
- Seam, depth inversion, and registration require corroborating views.
- `does_this_repair_delta_look_ass`: provisionally `true`.

This first concrete failure is an in-scope geometry defect of the one-layer
annulus, not an image-tooling failure.

### Next exact action

Inspect the already verified sanitized ventral pair at high detail to test
whether the shelf/wall is view-dependent:
`_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/review/pairs/ventral--source-left-current-right.png`.

## 2026-07-28 ventral high-detail observation

The ventral pair independently confirms the defect. Current gains a sharp
rightward-projecting triangular shelf at the elbow/upper-forearm transition.
Its pointed silhouette has no source counterpart and reads as an artificial
spike attached to a broad planar bridge. The source retains a recessed dark
gap through this region; current visibly crowds that gap.

The core's recognizable large-scale relief and the main arm registration remain
present, but the annulus is visibly unacceptable. Dorsal findings are
confirmed:

- No wall/slab: `fail`.
- No spike: `fail`.
- Intentional negative-space preservation: `fail`.
- `does_this_repair_delta_look_ass`: `true`.

### Next exact action

Inspect the already verified sanitized medial pair at high detail to classify
depth and seam behavior:
`_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/review/pairs/medial--source-left-current-right.png`.

## 2026-07-28 medial high-detail observation

The global arm pose, upper mass, wrist opening, long rails, and broad negative
spaces remain registered. The changed transition is largely occluded in this
view; there is no evidence here of whole-object registration loss or global
depth inversion. This view does not rescue the annulus because it does not
expose the failed shelf seen dorsally and ventrally.

- Main-arm registration: `pass`.
- Global depth inversion: `pass` (not observed).
- Local seam/wall behavior: `deferred` to an exposed oblique view.

### Next exact action

Inspect the already verified sanitized lateral pair at high detail:
`_validation/experiments/geometry_repair/component_20_methods/relief_core_c1_l1/review/pairs/lateral--source-left-current-right.png`.

## 2026-07-28 early-stop decision

The validation parent confirmed that the dorsal and ventral observations are a
decisive corroborated in-scope failure and directed this disposable image
subagent not to inspect more images than needed. The Agent Factory `validate`
procedure requires naming the first concrete failure and does not require
continuing redundant proof after a terminal failure.

Therefore no further images will be inspected. The already-inspected medial
view is retained as registration evidence; the lateral and remaining
sanitized pairs were generated and verified but were **not inspected**.

Final disposition:

- Result: `fail`.
- Candidate disposition: `reject_method`.
- Continue to application candidate: `false`.
- `does_this_repair_delta_look_ass`: `true`.
- First concrete failure: the one-layer annulus creates a broad,
  long-triangulated shelf/wall with spike-like silhouette projections and
  crowds/closes the source's intentional local negative space.
- Core relief preservation: `pass` for the translated original faceted core
  itself.
- Whole-arm registration: `pass`.
- No wall/slab: `fail`.
- No spike: `fail`.
- No unintended gap closure / negative-space damage: `fail`.
- No depth inversion: `pass` at the global level; no inversion was observed in
  the three reviewed views.
- No visible seam: `fail` because the fan-like annulus reads as an explicit
  planar transition boundary rather than a coherent continuation.

### Next exact action

Write `review.json` with this evidence and disposition. Do not modify the
model, scripts, project docs, or `classification.json`.

## 2026-07-28 closeout

`DONE`: wrote
`validation_reviews/geometry_repair/component_20_relief_core_c1_l1/review.json`.

`PASS`: `jq empty` accepts the review JSON.

`DONE`: `git diff --check` reports no whitespace errors in the checkpoint or
review.

No model, script, project-document, or classification file was modified.
