# Component 42 repair methods

## Goal

Resolve a seven-vertex upper-arm collision while preserving the visible cable
composition.

## Observations

The masked field clears all `7` cutter and reserved-margin failures. It affects
`40` of `104` vertices, with median displacement `0 mm`, p95 displacement
`6.382983 mm`, and maximum displacement `14.491501 mm`. No face reversals are
introduced and global cutter overlaps fall from `870` to `837`.

The extracted component shows a displaced buried branch. Dorsal, lateral, and
bicep-axial assembly views occlude that branch and show no new silhouette or
registration break. Edge distortion is localized: only three edges fall
outside the `0.7–1.4` ratio range and the minimum ratio is `0.448621`.

## Conclusion

Retain `REPAIR_005_COMPONENT_42_MASKED` as a reversible fitted-surface
candidate relative to `REPAIR_004_COMPONENT_37_MASKED`.

## Evidence

- Pre-experiment checkpoint:
  `blender_files/checkpoints/geometry_repair/pre_component_42.blend`
- Retained checkpoint:
  `blender_files/checkpoints/geometry_repair/component_42_masked_retained.blend`
- Generated evidence:
  `_validation/experiments/geometry_repair/component_42_methods/`
