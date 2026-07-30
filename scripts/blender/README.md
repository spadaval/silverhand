# Blender Modules

These modules are implementation entrypoints invoked through
`scripts/tools/run_blender_script.sh`.

## Authority

- `validate_master.py`
- `validation_camera_rig.py`
- `sync_validation_cameras.py`

## Analysis

- `analyze_clearance.py`
- `analyze_connectivity.py`
- `analyze_cross_section.py`
- `analyze_fit_profile.py`
- `analyze_thickness.py`

## Review and export

- `render_geometry_comparison.py`
- `render_validation_previews.py`
- `export_from_manifest.py`

The directory intentionally contains no V-numbered construction scripts.
Historical modeling methods belong to Git history, not the active execution
surface.
