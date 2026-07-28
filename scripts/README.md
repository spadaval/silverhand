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

By default it creates `comparison_review_sheet-01.png` and
`comparison_review_sheet-02.png` for the eight canonical views. The manifest
lists these under `render.contact_sheets` with the `high` detail hint. Do not
open a full archival sheet through an image-model inspection tool.
