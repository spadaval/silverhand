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
- `blender/try_coordinated_elbow_interface.py` — moves the two near-coincident
  component-9/component-20 elbow pairs together through the smallest bounded
  topology neighborhood and records whether the result is admissible as a
  combined-liner staging state.
- `blender/build_combined_authored_inner_bowl_liner.py` — evaluates one
  topology-changing component-20 inner-bowl liner from the coordinated elbow
  stage. Its single-chart construction is retained as a rejected control.
- `blender/build_boundary_cycle_inner_bowl_liner.py` — separates the complete
  removed-region boundary cycles and evaluates them as independent planar
  charts. Its large nonplanar chart is retained as a rejected control.
- `blender/build_cylindrical_uv_inner_bowl_liner.py` — checks whether the
  complete liner boundary is simple in the arm's axial-angle coordinates and
  refuses construction while exact crossing edges remain.
- `blender/try_remove_component20_inner_bowl.py` — evaluates the deliberate
  destructive cosplay simplification that retains the mapped exterior cage
  and removes the complete collision bowl without filling or capping it.
- `blender/build_local_elbow_interface_band.py` — builds an evaluation-only,
  closed C-shaped component-20 interface band and local cage-island junctions
  on the rejected open-cage base. It preserves the exterior cage and component
  9 exactly, keeps the central bowl open, and records clearance, registration,
  topology, volume, contact, and self-intersection gates.
- `blender/build_local_elbow_interface_band_v2.py` — evaluates the structural
  width escalation: a broad closed ribbon following the reviewed 21-control
  route plus closed local attachment solids whose contact graph joins all four
  retained cage islands. It preserves the same open center and source evidence
  and reports local width, component-9 contact, and cutter-clearance gates.
- `blender/build_local_elbow_interface_band_v3.py` — removes the v2
  attachment-cap degeneracies, omits its optional high-aspect micro-tab,
  applies a robust new-vertex clearance floor, and attributes every remaining
  component-9 overlap to a constituent and nearest band segment.
- `blender/build_asymmetric_elbow_interface_rail_v4.py` — evaluates
  component-9-side routing, exact-control feasibility, bounded chord detours,
  non-anchor route simplification, rotating cross-sections, and one local
  width sweep for a rail-only Repair-014 candidate. Its final folded detour is
  retained as a rejected control.
- `blender/build_local_c9_clear_notch_v5.py` — tests a bounded vertex-push
  notch against component 9 on the last non-folded v4 rail. The mechanism is a
  rejected control because it neither clears the collision nor preserves
  self-intersection and displacement bounds.
- `blender/build_anchor_transition_sweep_v6.py` — sweeps two local anchor
  transitions on the non-folded rail and selects the minimum-displacement
  component-9-clear result while preserving the other 11 anchors exactly.
- `blender/build_flared_gusset_network_v7.py` — retargets the required local
  cage-island gusset graph onto the v6 rail and searches a bounded direct
  island-3 connection. It is evaluation-only and does not repair the v6
  rail's inherited width collapse.
- `blender/build_parallel_transport_interface_rail_v8.py` — evaluates a fixed
  `6.0 × 2.4 mm` minimum-twist rail on the v6 route. The bounded control is
  rejected because restoring full width on one monolithic exact-control sweep
  reintroduces component-9 and self intersections.
- `blender/build_broad_constituent_network_v9.py` — replaces the monolithic
  sweep with three independently closed, fixed-width structural constituents
  and measured lap/cage contacts. Its one-direction displacement control
  clears component 9 but is rejected where the pieces enter the anatomical
  cutter or self-intersect.
- `blender/preflight_direction_field_network_v10.py` — evaluates a bounded
  normal-plane direction, distance, and roll grid for each v9 constituent and
  records Pareto evidence without emitting geometry unless the complete
  measured network is feasible.
- `blender/preflight_b2_sharp_turn_split_v11.py` — compares fixed-width right
  arc splits at V2111 and V2108 while preserving v10's feasible left and
  center placements. It isolates missing local junctions without emitting an
  incomplete network.
- `blender/build_connection_aware_network_v12.py` — jointly selects four
  admissible broad constituents and adds a bounded embedded local bridge only
  where direct overlap is unavailable. It emits review geometry only after
  the complete measured cage-rooted graph and all machine gates pass.
- `blender/preflight_distinct_cage_terminals_v13.py` — extracts the four
  connected components of the retained 1,409-face component-20 cage,
  attributes known source controls, and audits prior landing evidence against
  explicit terminal IDs without emitting geometry.
- `blender/build_upper_lower_terminal_bridge_v14.py` — searches an explicitly
  attributed flared saddle between the upper and lower major component-20
  terminals and rejects contact with every unrelated source component.
- `blender/build_surface_following_fan_saddles_v15.py` — preserves v14's
  proven T1-to-T0 route and midspan while rebuilding only the two terminal
  transitions as broad, embedded, two-stage fan saddles.
- `blender/build_projected_terminal_surface_pads_v16.py` — evaluates
  independently projected T1/T0 surface pads and rejects emission unless their
  terminal-local footprints, narrow shared route, and shoulder topology clear
  every collision, self-overlap, quality, and preservation gate.
- `blender/build_three_constituent_lap_network_v17.py` — preserves the
  terminal-local pads and narrow route as three independently closed solids,
  accepting only measured local pad/bridge laps that complete the explicit
  T1-to-T0 structural graph without a boolean union or global backing.
- `blender/preflight_second_terminal_pair_v18.py` — performs the read-only
  exhaustive 98×68 opposite-perimeter terminal-pair and bounded-route search,
  with durable staging/prefix checkpoints and no geometry or Blend save.
- `blender/build_local_destructive_landing_relief_v19.py` — resolves and
  fingerprints the strictly bounded destructive landing masks, stopping before
  mutation when either the primary or sole fallback violates a hard mask gate.
- `blender/build_elevated_surface_saddles_v20.py` — evaluates the exact
  six-solid two-branch elevated-saddle search at V1780/V1789, preserving the
  v16 scene authority and emitting nothing unless every contact, clearance,
  topology, quality, graph, cross-over, and preservation gate passes.
- `blender/build_full_authored_frame_v21.py` — checkpoints the exact four-face
  topology mask and immutable cage complement, reconstructs the proven v12
  broad C-band corridor, and exhausts the bounded upper/lower Hermite approach
  searches before permitting any evaluation-copy topology replacement.
- `blender/build_joint_c9_c20_elbow_v22.py` — reconstructs and attributes every
  upper/lower v21 approach overlap to exact C9/C20 source faces and vertices,
  verifies the authoritative proximal C9 wearer classification, and forbids
  channel preflight or mutation until one lower variant passes the fixed
  clearance, quality, and classification gates.
- `blender/preflight_free_space_lower_route_v23.py` — checkpoints the exact
  B2b/T0 portals and obstacle catalogs, runs the bounded orientation-aware
  lower-route and exterior-C20-relaxed fallback ledgers, and emits only
  checksummed read-only route/allowlist decisions.
- `blender/preflight_b2b_exit_v24.py` — checkpoints all ten exact v12 B2b
  rings, evaluates the ordered R8→R5 trims, then resumably exhausts the bounded
  R5/R6/R7 terminal-subsegment family and reruns the lower-route contract from
  each admitted portal without granting mutation authority.
- `blender/preflight_authored_tail_v25.py` — checkpoints the exact combined
  B2a/turn-bridge/B2b authority, resolves the bounded A0–A3 anchor ledger, and
  exhausts the hash-locked authored-tail escape and route contract through
  atomic, resumable shards. It uses a validated radius-`1.2 mm` inscribed
  capsule only as a necessary no-path prefilter; capsule success never grants
  a rectangular-rail result. The tool is read-only and emits no geometry.
- `blender/preflight_open_bay_joint_v26.py` — checkpoints exact C9/C20,
  negative-space, cutter, and immutable-complement authority before testing a
  finite source-led two-cell static interface family with an explicit flex
  gap. It records face-level hidden-floor ownership and sampled Gate-B/Gate-D
  evidence only; it emits no geometry and grants no mutation, volume,
  connectivity, or motion claim.
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
- `tools/merge_v25_route_shards.py` — verifies and merges the three completed
  V25 capsule-route shards, then writes the final route, allowlist, and build
  reports without changing Blender geometry.
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
