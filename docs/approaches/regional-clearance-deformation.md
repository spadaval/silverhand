# Regional Clearance Deformation

Status: **promising method; no geometry promoted**

Updated: 2026-07-28

## Decision

When a coherent source fragment penetrates the anatomical cutter deeply, first
test whether the surrounding fit field is locally wrong. Move the fragment and
nearby geometry through one smooth, bounded spatial field before deleting,
crushing, or rebuilding the fragment in isolation.

This is a continuation of the shared-deformation strategy in
[design.md](../design.md), not permission for automatic per-component lifting.
The field must act on every source vertex in its spatial region, preserve
nearby registration, and undergo matched-view review.

## Why this approach exists

The retained shallow rescue cleared small violations with a bounded procedural
displacement field. Remaining failures include source layers embedded much more
deeply in the prosthetic arm. Those layers cannot simply be projected onto the
cutter:

- pointwise movement collapses their depth;
- face or vertex deletion destroys recognizable surfaces;
- moving only one disconnected island creates an exploded part;
- broad global deformation damages otherwise acceptable composition.

A deep collision may therefore indicate a locally incorrect human-fit mapping,
not defective source geometry.

## Pilot evidence

The deep pilot is source component `59`, a small wrist fragment:

| Measurement | Before trial |
|---|---:|
| Vertices | 40 |
| Faces | 65 |
| Vertices inside cutter | 15 |
| Minimum cutter margin | -11.748 mm |
| Lift required for the reserved wall | 13.348 mm |

The full retained rescue candidate began with `424` vertices inside the cutter,
`433` below the reserved-wall margin, and `1,051` cutter-triangle overlaps.

### Tested methods

| Method | Clearance result | Qualitative result | Decision |
|---|---|---|---|
| Delete penetrating vertices | Removes the 15 local violations | Deletes 33 of 65 faces and leaves an obvious hole | Reject |
| Rigid component lift | Clears the pilot with a 15.2 mm translation | Preserves shape but breaks local registration | Reject in isolation |
| Uniform radial offset | Clears the pilot | Inflates the whole fragment | Reject |
| Masked radial displacement | Clears the pilot | Crushes and twists the deep profile | Reject for deep failures |
| Radial-depth compression | Clears the pilot | Preserves the outer side by collapsing axial depth | Reject |
| Rigid motion with 25 mm spatial falloff | Clears the pilot; global penetrations fall from 424 to 401 | Preserves the fragment and moves nearby geometry coherently | Continue |
| Rigid motion with 40 mm spatial falloff | Global penetrations fall to 398 | Affects too broad a region and increases reserved-margin failures to 472 | Reject |

The `25 mm` radius affected `493` nearby vertices. It is an experimental
starting value, not a durable design constant.

The masked procedural field is the useful equivalent of the proposed
texture-driven displacement map. Converting it into a bitmap texture would add
UV and sampling artifacts without changing the underlying deformation
behavior.

## Implementation constraints

The next version must:

1. Begin from the retained fitted/rescued surface, never the processed
   101-solid baseline.
2. Preserve the pilot fragment as a rigid or near-rigid landmark.
3. Use a smooth spatial field shared by all vertices in the bounded wrist
   neighborhood.
4. Anchor named neighboring rails, seams, cable routes, and silhouettes so the
   correction cannot drift freely.
5. Keep the field outside the region exactly unchanged.
6. Preserve topology, material assignment, component registration, and
   intentional negative space.
7. Remain reversible until the complete wrist region passes review.

Do not treat the current Euclidean `25 mm` falloff as the final control scheme.
The production implementation should use explicit regional landmarks or a
small deformation cage so the boundary and direction of influence are
reviewable.

## Review requirements

Before retaining a regional correction:

- compare the complete wrist region against the immutable source with matched
  dorsal, medial, lateral, and wrist-axial cameras;
- inspect the pilot and adjacent parts together, not as isolated objects;
- confirm no fragment becomes newly exploded, fused, flattened, or
  depth-inverted;
- rerun triangle-orientation and topology-invariant evidence;
- rerun cutter vertex and exact triangle-overlap evidence;
- record the regional mask, anchors, falloff, and displacement maximum.

If a coherent regional field cannot preserve the wrist composition, retain the
visible source boundary and rebuild only the hidden or wearer-facing surface.

## Checkpoint artifacts

Local, ignored Blender files:

- `blender_files/Johnny_fragment_rescue_work.blend` — retained pre-pilot
  candidate;
- `blender_files/Johnny_pilot_reconstruction_trials.blend` — borderline
  component trials;
- `blender_files/Johnny_pilot_reconstruction_component59_trials.blend` — deep
  wrist variants.
- `blender_files/archive/Johnny_regional_clearance_pilot_checkpoint_20260728.blend`
  — immutable copy of the completed deep-wrist trial.

Generated evidence:

- `_validation/pilot_reconstruction/iteration_1/`;
- `_validation/pilot_reconstruction/iteration_2_component59/build_report.json`;
- `_validation/pilot_reconstruction/iteration_2_component59/local_*`;
- `_validation/pilot_reconstruction/iteration_2_component59/context_*`.

At this checkpoint:

- tracked master SHA-256:
  `11cde6a6192bc4c10582809d6362a30b9f14d6e8fe577252771fb39413944a85`;
- retained rescue SHA-256:
  `7b41ab80f65385d6f52f944d9845a702b4ed50ed834ff9af70fec0bf2b93c512`.
- deep-wrist pilot and archived checkpoint SHA-256:
  `72116cf94c428e585af156ce6f9260a4304058011fab1a7f2e4dbb164b35afc6`.
