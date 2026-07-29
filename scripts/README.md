# Active scripts

The active workflow is separated by runtime:

```text
scripts/
├── blender/   Python loaded inside Blender; may import bpy
├── tools/     Host Python and user-facing shell entrypoints
└── examples/  Declarative example inputs
```

Use the shell entrypoints under `scripts/tools/` for normal work. Files under
`scripts/blender/` are implementation modules, not commands to run with the
system Python.

The pre-reset experimental generators remain recoverable in
`blender_files/archive/rework_evidence_pre_cleanup_20260727.tar.gz`. They are
intentionally absent from the active workflow because they encode centimeter
units, rejected carrier-backed architectures, or non-reproducible V2/V3/V4
lineages.

## Primary commands

- `tools/refresh_main_geometry_evidence.sh` — executes the complete
  current-milestone evidence refresh. Each successful operation reports `DONE`;
  only named validation gates and audits may report `PASS`.
- `tools/sync_validation_cameras.sh` — creates or repairs the eight canonical
  semantic cameras and saves them in `90_VALIDATION_CAMERAS`.
- `tools/render_geometry_comparison.sh` — renders the immutable TPU-only source
  and current evaluation through identical cameras, then builds two annotated,
  bounded Pillow review pages with `uv`.
- `tools/inventory_working_geometry.sh` — records every `REG_*` constituent,
  region, disposition, topology, bounds, metadata, and fingerprint.
- `tools/analyze_clearance.sh` — records cutter topology, fit/cutter surface
  relationships, exact surface intersections, and advisory signed vertex
  clearance. It does not approve wearer fit.
- `tools/analyze_connectivity.sh` — builds contact groups, isolate lists,
  cross-region edges, JSON, and Graphviz DOT. Contact is not load-path approval.
- `tools/analyze_thickness.sh` — emits advisory line-intersection thickness
  measurements. No threshold has authority until a physical process coupon
  establishes one.
- `tools/analyze_fit_profile.sh` — extracts all 77 inherited fit/cutter rings to
  JSON and CSV without inventing wearer landmarks.
- `tools/analyze_cross_section.sh` — intersects explicit objects with an
  unlabelled fit station. The underlying Blender script also accepts arbitrary
  planes. It does not split or cap geometry.
- `tools/export_from_manifest.sh` — exports only explicit manifest objects to
  binary millimeter STL, blocks source/review/cutter objects, runs the STL
  audit, and verifies reimported dimensions. See
  `examples/export_manifest.example.json`.
- `tools/run_validation.sh` — audits `exports/current/` only.
- `tools/render_validation_previews.sh` — renders current STL preview evidence.
- `blender/build_static_fit_prototype.py` — builds the reversible anatomy-led
  fitted-surface experiment in an ignored working `.blend`, preserving the
  immutable source as the Basis shape key and reporting topology, distortion,
  triangle-orientation locators, clearance, and affected connected components.
- `blender/rescue_clearance_fragments.py` — adds a reversible bounded-clearance
  shape key to the local fitted-surface candidate. It can defer excessive lifts
  and any topology neighborhood that would rotate a triangle more than
  90 degrees from the pre-rescue surface; it never promotes the result.
- `blender/apply_bounded_clearance_patch.py` — applies one explicitly selected
  shallow component mask as a reversible relative shape key, refuses an
  exceeded displacement cap, and records topology, clearance, edge, and
  orientation evidence. It never selects or visually approves a component.
- `blender/create_clearance_patch_review.py` — creates disposable `EVAL_*`
  pre/post objects for one patch so the existing matched-view renderers can
  perform qualitative review.
- `blender/analyze_component_proximity.py` — measures whether an explicit
  clearance-failure cluster is actually coincident with another source
  component. It is diagnostic-only and saves no geometry.
- `blender/analyze_cluster_transition_topology.py` — inventories closed,
  open, and branched face-transition graphs around explicit violation
  clusters before a reconstruction assumes a loop topology.
- `blender/analyze_reconstruction_landmarks.py` — verifies an explicit active
  repair checkpoint and records stable source vertex, edge, and face IDs,
  topology-ring boundary candidates, source open-boundary contacts, geometric
  cues, and cutter margins for one bounded reconstruction region. It is
  diagnostic-only and saves no geometry.
- `blender/try_landmark_relief_reconstruction.py` — tests fixed-boundary
  differential-coordinate reconstruction against explicit cutter-floor
  constraints. It creates evaluation objects only and never promotes a result.
- `blender/try_landmark_sector_retopology.py` — tests topology-changing,
  tapered-row reconstruction between an exact retained transition and
  source-open path while transferring bounded source relief. It creates
  evaluation objects only and never promotes a result.
- `blender/try_authored_landmark_patch.py` — tests the smallest authored
  component-20 floor cell by exhaustively checking its boundary
  triangulations. It records a construction blocker without saving geometry
  when no winding-compatible result exists.
- `blender/try_authored_fan_feasibility.py` — retains that source fan and
  searches one interior control point against explicit cutter-floor and
  orientation constraints. It records why a winding-safe fan still fails the
  triangle-overlap gate.
- `blender/try_face_aware_sector_reconstruction.py` — tests one deterministic
  ring-4 wearer-side displacement driven by cutter-triangle collisions while
  freezing the reviewed landmark and boundary controls.
- `blender/try_authored_inner_bowl_liner.py` — verifies the selected
  component-20 inner-bowl reconstruction authority and refuses construction
  when a frozen interface anchor is also a mandatory clearance failure.
- `blender/sweep_cluster_rigid_clearance.py` — tests coherent rigid motion of
  explicit violation clusters with topology-local harmonic transition
  weights. It is diagnostic-only and saves no geometry.
- `blender/apply_cluster_rigid_clearance.py` — applies one explicitly selected
  cluster as a coherent rigid core with a topology-local harmonic transition
  in a reversible relative shape key.
- `blender/try_relief_preserving_core_reconstruction.py` — creates
  evaluation-only geometry by translating one closed faceted source patch
  rigidly and reconnecting it through an explicit annulus. It never edits the
  active candidate.

## Host-side Python

- `tools/build_contact_sheet.py` — Pillow/`uv` review-packet composer. It puts
  at most four views on each page, uses two matched view-pairs per row, and
  caps review pages at `2000 px`. A full vertical sheet requires the explicit
  `--archival-output` option and is not suitable for direct image-model review.
- `tools/validate_stl_exports.py` — dependency-free binary STL audit.
- `tools/inventory_reference_3mf.py` — inventory of the proven 3MF.
- `tools/extract_reference_3mf_armor.py` — extraction of millimeter-native armor
  donors into ignored local working storage.

## Blender modules

Files under `blender/` implement scene validation, camera synchronization,
rendering, geometry evidence, fit profiling, cross-sections, and export. They
run inside Blender's bundled Python process.

There is deliberately no authoritative production-geometry generator. The
cleaned scene preserves both the clean source and the rejected 101-solid
experiment. `build_static_fit_prototype.py` is an experimental fitted-surface
generator: it begins from `SRC_GAME_TPU_ONLY_BASELINE`, applies one shared
deformation field, and preserves source topology. Its output remains a
candidate until the named promotion gates pass. The current `REG_*` inventory
tools remain useful for historical evidence and later solid-construction work;
they do not promote the existing processed baseline.

## Running scripts

Normal evidence refresh:

```sh
./scripts/tools/refresh_main_geometry_evidence.sh
```

Direct Blender execution remains available:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python-exit-code 1 \
  reference/Johnny.blend \
  --python scripts/blender/render_geometry_comparison.py \
  -- --output _validation/main_geometry_comparison
```

Rebuild the current static-fit experiment in an ignored working copy:

```sh
BLEND_FILE="$PWD/blender_files/Johnny_static_fit_prototype.blend" \
  ./scripts/tools/run_blender_script.sh \
  scripts/blender/build_static_fit_prototype.py \
  --anatomy-checkpoint \
  "$PWD/blender_files/archive/Johnny_pre_cleanup_20260727.blend" \
  --report \
  "$PWD/_validation/static_fit_prototype/iteration_6/build_report.json" \
  --save
```

Rebuild the selected bounded fragment rescue:

```sh
BLEND_FILE="$PWD/blender_files/Johnny_fragment_rescue_work.blend" \
  ./scripts/tools/run_blender_script.sh \
  scripts/blender/rescue_clearance_fragments.py \
  --report \
  "$PWD/_validation/fragment_rescue/iteration_10/build_report.json" \
  --reserved-margin-mm 1.6 \
  --maximum-hard-lift-mm 5 \
  --depth-preservation 0 \
  --diffusion-iterations 3 \
  --diffusion-factor 0.55 \
  --defer-negative-orientation \
  --orientation-deferral-rings 0 \
  --save
```

`tools/run_blender_script.sh` resolves Blender from `BLENDER_PATH`, the shell
`PATH`, or the standard macOS application path. Blender script arguments follow
the `--` separator.

The host contact-sheet helper uses a PEP 723 Pillow dependency managed by `uv`;
it does not install Pillow into Blender.

All raster-producing scripts require ImageMagick's `magick` executable. Set
`MAGICK_PATH` when it is not on `PATH`. Each generated image is immediately
replaced with an 8-bit, metadata-free, orientation-normalized sRGB derivative;
sanitization failure stops the producing operation with the failed command and
target path. Sanitized outputs larger than 10,000,000 bytes are marked unsafe
for direct image-model review.

By default it creates `comparison_review_sheet-01.png` and
`comparison_review_sheet-02.png` for the eight canonical views. The manifest
lists these under `render.contact_sheets` with the `high` detail hint. Do not
open a full archival sheet through an image-model inspection tool.
