# V28 Authored Wearable Panels

Status: **active construction approach; closed physical shells accepted for next disposable iteration**

Updated: 2026-07-30

## Decision

Stop repairing the hidden C9/C20 game sheet. Preserve recognizable exterior
character and author three clean TPU panels from the fit reference. The
clearance cutter remains collision/audit geometry only.

The panels are engineering geometry. They do not inherit source faces,
directional-chart topology, or cutter triangles. Neutral zone names remain in
use until wearer landmarks authorize anatomical names.

## Starting authority

`scripts/blender/build_v28_wearable_panel_scope.py` verifies:

- the exact V27 253-face source-reference scope;
- a continuously clear 71-edge outer boundary;
- six known decorative exterior faces
  `[2219, 2220, 2221, 2225, 2233, 2276]`;
- a provisional 247-face wearer-side removal scope;
- three neutral construction zones along the cutter principal axis.

The repeat-identical authority is:

- `_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v28/v28_wearable_panel_scope_authority.json`
- SHA-256
  `4a35c5953c7a0e61233d8e3f9db218454315ab4143b7c9da981f42405927c7d3`

No geometry was emitted and the Blend was not saved.

## Construction contract

Each initial panel uses:

- five clean authored cross-sections;
- at least `1.7 mm` digital clearance;
- a nominal `4 mm` engineering seam to its neighbor;
- no source or cutter topology;
- local junctions to retained exterior forms;
- preserved intentional openings and negative space.

Add a fourth panel only for a named fit, motion, printing, or assembly reason.
Do not derive production panel count from diagnostic face clusters.

The bounded exterior review rejected the provisional 247-face removal in full.
All 253 scope faces are exterior reference evidence; none is authorized for
deletion. The exact classification is
`exterior_removal_review/classification.json`, SHA-256
`fa02e9d18ecd124bf334db8d23e2e1576d495f9f21046d54e787a3980cc0c597`.
Reference evidence may later be independently rebuilt, modestly relocated, or
trimmed where wearability requires it, but it must not be mistaken for hidden
wearer-side topology.

## Next bounded experiment

In a disposable V28 Blend:

1. create three curve or mesh-loop scaffolds from five cross-sections each;
2. keep them independent and visibly separated by the nominal seams;
3. do not add thickness, detailed junctions, or source decoration yet;
4. audit vertices, continuously sampled edges, and adaptive triangle interiors;
5. render the scaffold only after it passes those cheap geometry gates.

The scaffold is not promoted geometry. Its purpose is to validate that three
simple panels can cover the wearer-side engineering need before detail work.

## V28-SCAFFOLD-001

Checkpointed before geometry mutation on 2026-07-30.

The first scaffold is deliberately simpler than a finished sleeve:

- derive five section point clouds per panel from fit-reference/plane
  intersections;
- fit clean enclosing ellipses in one stable neutral construction frame;
- add a recorded radial engineering allowance outside those ellipses;
- inset both sides of each shared axial boundary by `2 mm`, producing the
  nominal `4 mm` seam;
- leave a provisional `40 degree` opening in every section, consistently
  oriented by the neutral construction frame;
- loft corresponding points into three independent, open, zero-thickness
  evaluation surfaces;
- do not copy source faces, fit-reference faces, cutter triangles, or
  section-segment topology;
- use the cutter only for collision and clearance auditing.

The opening is an engineering hypothesis, not an anatomical or wearer-landmark
claim. Its orientation may move after fit and motion review. The scaffold does
not claim printable solidity, thickness, closure design, junction design, or
source-detail integration.

Before the disposable Blend is saved, every candidate triangle must have:

- no exact cutter-triangle intersection;
- no nonadjacent self-overlap or cross-panel surface overlap;
- at least `1.7 mm` exact triangle-to-cutter distance;
- at least `1.7 mm` signed clearance at adaptively refined triangle-interior
  samples;
- edge coverage through the same adaptive lattice at no more than `1 mm`
  initial spacing and no more than `0.5 mm` adjacent signed-margin variation.

If a candidate fails, retain the failure as text evidence and adjust the
explicit radial allowance. Do not add local micro-patches or silently increase
panel count.

## V28-SCAFFOLD-001 result

The fit-derived scaffold passed its machine and independent visual checks:

- disposable Blend SHA-256:
  `e27c5632d0c5d7b60cb99f4eac87b46a143cc4a36e1caf1b36bbbea366b28c9a`;
- all `1,512` triangles pass the cutter contract;
- minimum exact triangle-to-cutter distance: `1.813721 mm`;
- minimum signed adaptive margin: `1.831561 mm`;
- nonadjacent self-overlaps: `0`;
- cross-panel overlaps: `0`;
- visual result: `ACCEPT_FOR_NEXT_DISPOSABLE_ITERATION`;
- visual classification SHA-256:
  `86645d3d8775ef60105464767ae7e06416088f9d8e02b05c7ee3c8f36bc46227`.

Seven individual sanitized views support coherent panels, two uninterrupted
axial seams, one aligned longitudinal opening, and no visible spike, twist, or
surface crossing. Exact seam width and opening angle remain machine claims.

The next experiment may add provisional outward thickness and simple edge
treatment while preserving the current panel count, seams, opening direction,
and inner scaffold surface. Do not integrate source detail or promote the
result in that experiment.

## V28-PHYSICAL-001

Checkpointed before geometry mutation on 2026-07-30.

Turn the exact accepted scaffold into three closed evaluation shells:

- use Blend SHA-256
  `e27c5632d0c5d7b60cb99f4eac87b46a143cc4a36e1caf1b36bbbea366b28c9a`
  as the sole panel-shape input;
- preserve every inner scaffold vertex exactly;
- add provisional `1.6 mm` thickness outward from the neutral construction
  axis;
- close both axial ends and both longitudinal opening lips;
- preserve three independent constituents, both `4 mm` axial seams, and the
  aligned `40 degree` opening;
- use square boundary closures in this first solid experiment.

The square edges are deliberate staging geometry, not finished wearer-contact
treatment. Rounding or rolling an edge may consume clearance or alter the
opening and therefore follows only after the closed-shell layout is accepted.
No thickness value has physical authority until a TPU process coupon is tested.

Before saving the disposable physical-shell Blend, require:

- one connected component per panel;
- positive signed volume;
- zero boundary and non-manifold edges;
- no nonadjacent self-overlap or cross-panel overlap;
- unchanged source, fit-reference, cutter, and accepted inner scaffold meshes;
- the complete evaluated shell triangle set to pass the `1.7 mm` cutter
  contract.

This experiment creates a physical mesh topology, but it does not claim a
closure system, elbow motion, exterior-detail attachment, bed segmentation,
print readiness, or production status.

## V28-PHYSICAL-001 result

The three provisional physical shells passed machine and independent visual
review:

- disposable Blend SHA-256:
  `64366dc52290552416fa7ac478d6bc289adb8ff63fa1de6ca4c84f9e1c80bd68`;
- three independent connected components, each with `640` vertices and `638`
  faces;
- zero boundary edges and zero non-manifold edges;
- positive volumes of `8675.386`, `7138.060`, and `7488.479 mm³`;
- all `3,828` evaluated triangles pass the cutter contract;
- minimum exact triangle-to-cutter distance: `1.813721 mm`;
- minimum signed adaptive margin: `1.831561 mm`;
- self-overlap pairs: `0`;
- cross-panel overlap pairs: `0`;
- independent visual result: `ACCEPT_FOR_NEXT_DISPOSABLE_ITERATION`;
- visual classification SHA-256:
  `81477f741591a705dbb64787d2fa3f0ec249ce43b5d1d1cce625c815ee78903a`.

Seven individual sanitized high-detail views show continuous inner, outer, and
square rim walls; retained axial seams and longitudinal opening; no obvious
thin or missing wall; and no visible bulge, spike, twist, fold-over, or surface
crossing.

These are real closed mesh solids, but still evaluation geometry. The next
bounded work is wearer-contact edge treatment and a small physical TPU process
coupon. Detailed exterior junctions, closure hardware, motion architecture,
and production export remain deferred.
