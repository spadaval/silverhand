# Component 39 repair methods

## Goal

Test whether a compact visible wrist detail can clear its ten deep
penetrations without losing its source shape or registration.

## Observations

- Masked radial displacement clears the collision but introduces one reversed
  face.
- Radial-depth compression preserves orientation but visibly flattens and
  rotates the wrist detail; `22` edges fall outside the `0.7–1.4` ratio range.
- A `13.9 mm` rigid lift preserves the component itself but visibly relocates
  it relative to the surrounding wrist structure.
- Deleting the penetrating vertices removes `23` of `182` faces.

## Conclusion

Park component `39`. None of the tested deformation methods preserve both
topology integrity and visible registration. Revisit it with bounded
hidden-surface reconstruction or an explicitly controlled local cage.

The active retained scene was not changed.

## Evidence

- Pre-experiment checkpoint:
  `blender_files/checkpoints/geometry_repair/pre_component_39.blend`
- Generated evidence:
  `_validation/experiments/geometry_repair/component_39_methods/`
