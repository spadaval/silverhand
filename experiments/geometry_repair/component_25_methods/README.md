# Component 25 repair methods

## Goal

Classify component `25` and determine whether its remaining cutter collision
can be resolved without disturbing the visible component-1 plate or the large
neighboring source surfaces.

The experiment begins from retained
`REPAIR_002_COMPONENT_1_REGIONAL`. Component `25` currently has `306`
vertices, `475` faces, `29` vertices inside the cutter, and a minimum cutter
margin of `-11.292559 mm`.

## Initial evidence

The component spans approximately `74.7 × 67.5 × 74.5 mm` over stations
`238.9–289.0 mm`. Component `20` is now its closest neighbor at `0.112249 mm`.

Programmatic visibility sampling finds `101` faces touching a penetrating
vertex, but only a small subset is directly visible from the standard exterior
directions. This suggests that hidden-side reconstruction may be preferable to
another broad regional lift, but the classification images must confirm that.

## Observations

Component `25` is a visible mechanical cradle/rail assembly, not disposable
interior debris. Deleting its penetrating vertices removes `101` faces, while
rigid and uniform offsets move the whole assembly by roughly `13–16 mm`.

The bounded masked field clears all `29` cutter penetrations and all `32`
reserved-margin failures. It affects `238` of the component's `306` vertices,
but the median displacement is only `0.013778 mm`; the maximum is
`12.892555 mm` on the buried side. It introduces no orientation reversal.
Matched isolated and assembly views show no obvious silhouette or registration
break. Global cutter overlaps fall from `978` to `885`.

Five local edges contract below half their prior length, with a minimum ratio
of `0.280396`. These are hidden-side detail watch items for later
solidification rather than evidence that the surface repair is print-ready.

## Conclusion

Retain `REPAIR_003_COMPONENT_25_MASKED` as a reversible fitted-surface
candidate relative to `REPAIR_002_COMPONENT_1_REGIONAL`.

This result does not approve component `25` as printable geometry. Its
wearer-facing surface and its overlaps with neighboring source layers still
need structural interpretation during solidification.

## Evidence

- Pre-experiment checkpoint:
  `blender_files/checkpoints/geometry_repair/pre_component_25.blend`
- Retained checkpoint:
  `blender_files/checkpoints/geometry_repair/component_25_masked_retained.blend`
- Generated evidence:
  `_validation/experiments/geometry_repair/component_25_methods/`
