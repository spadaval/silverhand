# AGENTS.md

Silverhand cyberarm cosplay build — Blender-based 3D modeling for 3D printing.
Read [DESIGN.md](DESIGN.md) before making modeling decisions; it holds the design
rationale, fit/scaling math, panel inventory, and build sequence.

## Layout

- `reference/Johnny.blend` — **the master scene** (tracked via Git LFS, ~260 MB)
- `reference/johnny_silverhand_arm_scaled_up.3mf` — proven printed panels used to calibrate fit
- `blender_files/` — local Blender working iterations (gitignored, **not synced** between machines)
- `exports/sleeve/`, `exports/test_prints/` — print-ready STLs exported from the master scene
- `_stl_preview/` — rendered previews of the exported STLs
- `DESIGN.md` — the design doc (goals, scaling, components, build sequence)

## Git LFS (required)

- Install and init git-lfs **before cloning/pulling** (`git lfs install`), otherwise
  `reference/Johnny.blend` arrives as a text pointer instead of the real scene.
- `.gitattributes` routes **all** `*.blend` files through LFS.
- `.gitignore` ignores `blender_files/`, `*.blend`, and `*.blend1`, with a single
  exception: `!reference/Johnny.blend`. Only the master scene is checked in.
- To update the checked-in master scene: overwrite `reference/Johnny.blend` and commit —
  LFS storage is expected and fine for this one file.
- Do **not** force-add other `.blend` files from `blender_files/`; keep experiments
  local-only. LFS storage/bandwidth is limited (GitHub free tier: 1 GB).

## Conventions

- Blender scene units: **1 unit = 1 cm** (`scale_length = 0.01`); STL exports are scaled ×10 to mm.
- Print bed is 18×18×18 cm (A1 mini) — all exported pieces must be bed-sized.
- Design decisions, component inventory, and build-sequence status live in DESIGN.md —
  update it when any of those change, not just the scene.
