# Active Tools

Only current, reusable tools belong here. Versioned reconstruction experiments
were removed from the active branch and remain recoverable at
`pre-repo-cleanup-20260730`.

## Runtime split

```text
scripts/
├── blender/   modules executed by Blender; may import bpy
├── tools/     host commands and shell entrypoints
└── examples/  declarative inputs
```

Use the shell commands under `scripts/tools/` for normal work.

## Master and evidence

- `blender/validate_master.py` — validates the consolidated source evidence,
  fitted candidate, three retained engineering prototypes, units, cameras, and
  absence of retired evaluation/salvage collections.
- `tools/sync_validation_cameras.sh` — repairs the canonical matched-view
  camera rig.
- `tools/render_geometry_comparison.sh [OUTPUT_DIR]` — renders the immutable
  TPU source and fitted candidate through matched cameras. Every generated
  image is sanitized immediately. Image inspection remains subagent-only.
- `tools/build_contact_sheet.py` — creates bounded review pages from a render
  manifest; generated sheets are archival or delegated-review inputs, never
  parent-agent image inputs.

Default generated evidence goes under `.work/evidence/`.

## Geometry audits

- `tools/analyze_clearance.sh [OUTPUT_JSON]`
- `tools/analyze_connectivity.sh [OUTPUT_JSON]`
- `tools/analyze_fit_profile.sh [OUTPUT_JSON]`
- `tools/analyze_thickness.sh [OUTPUT_JSON]`
- `tools/analyze_cross_section.sh STATION_INDEX OBJECT...`

Clearance uses `20_FITTED_SURFACE` by default. Connectivity and thickness use
`25_ENGINEERING_PROTOTYPES` by default. These tools report geometry evidence;
they do not approve wearer fit, comfort, material behavior, or load paths.

## Export

- `tools/export_from_manifest.sh MANIFEST OUTPUT_DIR` — exports only explicitly
  named objects as binary millimeter STL at scale `1.0`, then audits topology,
  bed fit, and reimported dimensions.
- `tools/run_validation.sh` — audits `exports/current/`.
- `tools/render_validation_previews.sh [OUTPUT_DIR]` — renders explicit current
  STL exports for delegated review.
- `tools/validate_stl_exports.py` — host-side STL audit.
- `examples/export_manifest.example.json` — manifest template.

An empty `exports/current/` is valid until a production print candidate exists.

## Reference armor

- `tools/inventory_reference_3mf.py` — inventories the proven 3MF without
  treating it as anatomical authority.
- `tools/extract_reference_3mf_armor.py` — extracts local donor meshes to
  `.work/reference_3mf_armor_donors/`.

## Image sanitation

`image_sanitization.py` is the shared ImageMagick boundary. Generated images
must be stripped, orientation-normalized, converted to sRGB, and written as
ordinary 8-bit PNG/JPEG derivatives. Files over 10 MB are never submitted to
an image model.
