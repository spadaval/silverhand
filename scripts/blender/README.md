# Blender script routing

Blender scripts are implementation entrypoints. Read `docs/status.md` before
running one; script existence does not make a method active.

## Active Repair 014 workflow

- `build_v28_wearable_panel_scope.py` — verifies the broad V27 wearer-side
  evidence and produces the read-only three-panel V28 construction contract.
  It does not mutate a mesh, copy source topology, copy cutter topology, emit
  geometry, or save a Blend.

The next geometry builder must consume that authority and create clean
cross-section/loft scaffolds in a disposable V28 Blend. It must not infer
production panels from V27 diagnostic face charts.

## Historical V27 evidence

The following scripts remain runnable only to reproduce rejected evidence:

- `solve_v27_c9_split_surface_family.py`
- `audit_v27_c9_split_fixed_boundary.py`
- `audit_v27_c9_proximal_mask_boundary.py`
- `solve_v27_c9_proximal_surface_family.py`
- `solve_v27_c9_subdivided_retopology_family.py`
- `build_v27_c9_directional_chart_authority.py`
- `solve_v27_c9_directional_panels.py`

Do not refine, emit, or promote their split vertices, harmonic surfaces,
subdivision surfaces, charts, or panels. Their active lesson is that hidden
game topology is not wearable-structure authority.

Accidental execution is blocked. Set
`SILVERHAND_ALLOW_HISTORICAL_V27=1` only when deliberately reproducing frozen
historical evidence.
