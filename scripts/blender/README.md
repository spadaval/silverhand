# Blender script routing

Blender scripts are implementation entrypoints. Read `docs/status.md` before
running one; script existence does not make a method active.

## Active Repair 014 workflow

- `build_v28_wearable_panel_scope.py` — verifies the broad V27 wearer-side
  evidence and produces the read-only three-panel V28 construction contract.
  It does not mutate a mesh, copy source topology, copy cutter topology, emit
  geometry, or save a Blend.
- `build_v28_three_panel_scaffold.py` — consumes that exact authority and
  creates three independent open loft scaffolds from five clean fit-reference
  measurements each. It copies no source, fit, or cutter topology; the cutter
  is collision/audit geometry only. It runs exact surface-overlap and adaptive
  clearance gates before mutation and saves only a disposable evaluation
  Blend.

The scaffold is not production geometry. Do not add thickness, closures,
junctions, or source detail until its independent layout review is recorded.

- `build_v28_three_panel_physical_shells.py` — consumes only the exact
  independently accepted scaffold Blend, preserves its inner vertices, and
  creates three closed outward-thickness evaluation shells. It requires one
  positive-volume manifold component per panel plus complete cutter and
  surface-overlap gates before saving.

The physical shells still have square staging rims. They are not closure,
motion, source-junction, print, or production authority.

- `build_v28_reversible_edge_softening.py` — duplicates the exact accepted
  physical shells, adds live angle-limited Bevel modifiers, and audits the
  evaluated result for closed positive volume, cutter clearance, and
  self/cross-panel overlap. It never applies a modifier or edits the accepted
  shell objects.

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
