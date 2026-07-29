# Component 20 Landmark-Sector Reconstruction

Status: **active evaluation; no geometry retained**

Updated: 2026-07-28

## Decision

Resolve component `20` before component `9`. Reconstruct only its two major
wearer-facing failure regions, beginning with the smaller cluster `1`.
Preserve the reviewed exterior, source ridge/depth landmarks, registration,
and intentional negative space. The clearance cutter supplies a minimum
wearer-side floor only; it does not govern the visible form.

Begin with the smallest authored patch that can absorb the required depth
change. If that transition fails, widen the patch to a complete offending
sector whose seam follows an existing open edge, ridge, valley, or concealed
boundary. Do not rebuild the entire connected component unless bounded sector
transitions repeatedly prove impossible or the retained exterior is shown to
be unusable.

## Exact working base

The active evaluation base is the post-Repair-013 scene:

- `blender_files/Johnny_geometry_repair_work.blend`;
- SHA-256
  `ff603514cacfc1b99d4ecf2c4548f1291b80164afdc16b0be0e77652c4f7942e`;
- latest active shape key
  `REPAIR_013_COMPONENT_19_CLUSTER_RIGID`;
- global clearance state: `258` cutter penetrations, `275` vertices below the
  `1.6 mm` reserved wall, and `653` cutter-triangle overlaps.

The pre-Repair-014 binary checkpoint is:

- `blender_files/checkpoints/geometry_repair/pre_repair_014_component_20_cluster_1_20260728.blend`.

## Current component classification

Component `20` has `1,189` vertices and exactly two current reserved-margin
failure clusters:

| Cluster | Reserved-margin failures | Cutter penetrations | Current minimum margin |
|---|---:|---:|---:|
| `0` | 87 | 87 | `-46.119392 mm` |
| `1` | 31 | 28 | `-8.660689 mm` |

The historical `32`-vertex cluster-1 count predates Repair 006. Its six-ring
transition moved vertex `4860` from `1.387087 mm` to `2.567371 mm`, leaving
`31` current failures.

Cluster `1` is the calibration region:

- its 31 violating vertices touch 87 source faces;
- the core has one closed 60-edge transition and no source-open boundary;
- the two-, three-, and four-face-ring sectors each have one ordered outer
  transition chain and one ordered source-open chain;
- those expanded sectors provide bounded retopology scopes without a
  full-perimeter translated-core annulus.

Stable source vertex, edge, and face IDs are recorded by
`scripts/blender/analyze_reconstruction_landmarks.py`. They remain valid only
for the exact geometry fingerprint in that report and must be regenerated
after any topology change.

## Rejected calibration control

A same-topology differential-coordinate reconstruction tested two-, three-,
and four-ring sectors with three cutter-target constraint weights. Every
variant failed the numerical gate.

The least-bad variant used the three-ring sector and weight `100`. It cleared
cluster `1`, but:

- introduced three reversed triangles;
- contracted one affected edge to `0.116897` and expanded another to
  `3.615030`;
- increased replacement-region overlaps from `128` to `146`;
- increased global overlaps from `653` to `671`.

This result activates the approved escalation rule. Do not tune the same
differential solve or submit it for image review. The next trial changes
topology inside the bounded sector.

## Rejected ruled-sector control

For each two-, three-, or four-ring calibration sector:

1. Keep the outer transition chain exactly unchanged.
2. Remove only the selected wearer-facing sector faces.
3. Replace the existing source-open path with a cutter-safe path having the
   same boundary-edge count.
4. Connect the two paths through several gradually tapered rows, avoiding a
   single fan or full-perimeter annulus.
5. Transfer the original sector's stepped differential relief onto that base.
6. Clamp only residual wearer-side violations to the `1.6 mm` reserved wall.
7. Keep every vertex and face outside the explicit sector unchanged.

The first implementation swept `18` combinations of sector size, tapered-row
count, and transferred-relief scale. None passed the numerical gate. The
least-bad four-ring candidate:

- preserved connected-component, boundary-edge, nonmanifold-edge, and
  noncontiguous-winding counts;
- preserved the complete outside-geometry fingerprint;
- cleared its replacement vertices past the reserved wall;
- reduced global penetrations from `258` to `217`;
- increased replacement-region overlaps from `133` to `155`;
- increased global overlaps from `653` to `675`;
- introduced 14 local relief reversals;
- produced triangle aspect ratios up to `16.904485` and a minimum angle of
  `0.991314°`.

This rules out a generic ruled-row parameterization. Do not tune more row,
ring, or scalar-relief combinations and do not submit this candidate for image
review.

## Active manually authored patch

The next implementation must begin from explicit source ridge curves rather
than a generic sector parameterization:

1. Map recognizable ridge peaks, valleys, depth breaks, open-edge routes, and
   hidden transition arcs to durable source vertex/edge IDs.
2. Construct a small set of authored cross-sections between those curves.
3. Triangulate each bounded cell locally so its winding and triangle quality
   are controlled rather than inherited from a zipper or fan.
4. Place the wearer-side base outside the reserved wall, then restore only the
   reviewed ridge/depth amplitudes.
5. Preserve the outer transition and intentional openings exactly.

Cosplay tolerance permits simplifying invisible micro-facets and regularizing
the wearer-facing topology. It does not permit a smooth carrier slab, filled
negative space, lost ridge routes, displaced registration, or a pressure-like
inner shelf.

## Numerical gate

A candidate may enter image review only if it:

- clears cluster `1` below both the cutter and reserved wall;
- does not increase replacement-region cutter overlaps;
- adds no reversed or noncontiguous faces;
- preserves connected-component, boundary-edge, and nonmanifold-edge counts;
- preserves the exact outer transition chain and all geometry outside the
  reconstruction sector;
- has no degenerate triangles or implausible edge/triangle-quality tail;
- records per-face material assignments and the complete changed topology.

## Visual gate

Every image operation belongs to a disposable image-validation subagent.
Generated images must be sanitized and size-checkpointed before high-detail
inspection.

The review must compare local relief and complete assembly context and reject:

- a smooth cutter-shaped carrier surface;
- a shelf, wall, fan, spike, or abrupt seam;
- flattened or missing stepped relief;
- bridged or closed negative space;
- component-9/component-20 layer inversion or fusion;
- collateral exterior or registration change.

No Repair 014 result promotes the complete fitted surface while component `20`
cluster `0` and component `9` remain unresolved.

## Evidence

- `_validation/experiments/geometry_repair/component_20_methods/repair_014_current_audit/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_landmarks_tool_test/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_relief_trial/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_sector_retopo/`
