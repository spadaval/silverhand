# Component 37 repair methods

## Goal

Clear a seven-vertex deep collision on a long wrist cable/strip without
changing its exposed curve.

## Observations

The masked field clears all `7` cutter and reserved-margin failures. It affects
`45` of `114` vertices, with median displacement `0 mm`, p95 displacement
`5.804357 mm`, and maximum displacement `9.749539 mm`. No face reversals are
introduced and global cutter overlaps fall from `885` to `870`.

The isolated wrist-axial view shows a buried endpoint being flattened. In the
complete assembly that endpoint is fully occluded; the visible cable run keeps
its source curve. Three edges contract below half length and one edge expands
to `2.088288` times its prior length, so the buried endpoint remains a later
solidification watch item.

## Conclusion

Retain `REPAIR_004_COMPONENT_37_MASKED` as a reversible fitted-surface
candidate relative to `REPAIR_003_COMPONENT_25_MASKED`.

## Evidence

- Pre-experiment checkpoint:
  `blender_files/checkpoints/geometry_repair/pre_component_37.blend`
- Retained checkpoint:
  `blender_files/checkpoints/geometry_repair/component_37_masked_retained.blend`
- Generated evidence:
  `_validation/experiments/geometry_repair/component_37_methods/`
