# Component 1 repair methods

## Goal

Determine what source component `1` represents, whether its penetrating
surface is visible or wearer-facing, and which bounded repair method can
improve anatomical clearance without breaking nearby registration.

The experiment begins from the retained `REPAIR_001_COMPONENT_0` candidate.
Component `1` has `107` vertices, `8` vertices inside the cutter, and a minimum
cutter margin of `-6.536619 mm`. Its previously affected station range is
approximately `248.8–292.6 mm`.

## Approach

First review the component alone, in local context, and against the clearance
cutter. Then test a few reversible alternatives in separate local Blender
copies. Do not reuse the rejected shallow automatic radial-patch method as an
assumed solution.

Candidate approaches:

- preserve the component nearly rigidly while testing a bounded outward move;
- blend the required motion through nearby geometry as a shared regional
  correction;
- if the collision is confined to a hidden surface, preserve the visible
  boundary and reconstruct only the wearer-facing patch.

Any approach that visibly explodes the component, inflates the regional
silhouette, crushes its profile, reverses triangles, or causes severe local
edge distortion will be rejected or parked.

## Observations

Component `1` is a broad perforated mechanical plate rather than a small
hidden fragment. It is largely occluded from dorsal and medial views, but `85`
of its `156` faces are visible ventrally and `22` of the `30` faces touching a
penetrating vertex are visible from that direction. Its closest source
neighbor is component `25`, only `0.277824 mm` away.

The first trial set produced clear method boundaries:

- deleting the `8` penetrating vertices removes `30` visible faces;
- an isolated `8.2 mm` rigid lift preserves the plate but opens its nearest
  relationship with component `25` to `4.887856 mm`;
- masked radial displacement introduces `3` local orientation failures;
- radial-depth compression clears the cutter but changes the visible plate
  profile and increases the nearest component-25 distance to `1.63456 mm`;
- shared regional rigid fields clear component `1` while keeping its
  relationship with component `25` near `0.278 mm`.

Regional falloffs from `25–40 mm` were compared. Larger falloffs distribute
distortion more gently but move more of the surrounding source:

| Falloff | Moved vertices | Minimum edge ratio | Maximum edge ratio | Global vertices inside cutter |
|---:|---:|---:|---:|---:|
| 25 mm | 1,035 | 0.636845 | 1.446186 | 398 |
| 30 mm | 1,234 | 0.690783 | 1.370588 | 397 |
| 35 mm | 1,471 | 0.723772 | 1.312896 | 397 |
| 40 mm | 1,707 | 0.755038 | 1.277828 | 393 |

The `35 mm` version is the selected compromise. It:

- clears all `8` component-1 penetrations and its reserved-margin failures;
- reduces global cutter penetrations from `422` to `397`;
- reduces reserved-margin failures from `431` to `411`;
- reduces cutter triangle overlaps from `1,037` to `978`;
- preserves topology, material assignments, and the component-25 relationship;
- introduces no negative-orientation locators;
- also reduces component `25` from `40` to `29` penetrations, component `9`
  from `168` to `163`, and component `20` from `134` to `133`.

High-detail local and complete matched views show no new exploded part, spike,
slab, silhouette break, or depth inversion. The patch delta does not look ass.
The complete fitted surface still fails anatomical clearance.

## Conclusion

Keep `REPAIR_002_COMPONENT_1_REGIONAL` as a reversible fitted-surface
candidate, relative to `REPAIR_001_COMPONENT_0`.

This is evidence that a visible nested component can sometimes be rescued by a
shared regional fit-field correction. It is not a general automatic lifting
rule, and the simple Euclidean falloff is not promoted as the final control
architecture. The `0.723772–1.312896` affected-edge range and the `1,471`
weighted vertices remain explicit watch items.

Component `25` is the logical next classification target because it is the
plate's immediate neighbor and the selected regional field already improves
its collision substantially without clearing it.

## Evidence

- Scene checkpoint:
  `blender_files/checkpoints/geometry_repair/component_1_methods.blend`
- Retained scene checkpoint:
  `blender_files/checkpoints/geometry_repair/component_1_regional_35_retained.blend`
- Generated evidence:
  `_validation/experiments/geometry_repair/component_1_methods/`
- Selected build report:
  `_validation/experiments/geometry_repair/component_1_methods/selected_report.json`
- Selected local review packet:
  `_validation/experiments/geometry_repair/component_1_methods/selected/local/`
- Selected complete review packet:
  `_validation/experiments/geometry_repair/component_1_methods/selected/full/`
- Portable before/selected meshes:
  `_validation/experiments/geometry_repair/component_1_methods/model/`
