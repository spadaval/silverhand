# Component 36 repair methods

## Goal

Test whether a visible wrist hook/cable can clear its seven deep penetrations
without changing the exposed hook profile.

## Observations

- Masked radial displacement clears the collision but introduces three
  reversed faces.
- Radial-depth compression preserves orientation but visibly changes the
  wrist-axial hook curve and its placement in the complete assembly.
- A `13.5 mm` rigid lift would move the whole exposed component and was not
  retained.
- Deleting the penetrating vertices removes `19` of `146` faces.

## Conclusion

Park component `36`. Its collision reaches visible source geometry, and the
tested automatic fields either fold topology or alter the recognizable hook.
Revisit it with a controlled visible reconstruction.

The active retained scene was not changed.

## Evidence

- Pre-experiment checkpoint:
  `blender_files/checkpoints/geometry_repair/pre_component_36.blend`
- Generated evidence:
  `_validation/experiments/geometry_repair/component_36_methods/`
