# Regional Clearance Deformation

Status: **retained reversible repair method; fitted surface not promoted**

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

## Component 1 confirmation

A second bounded experiment tested component `1`, a `107`-vertex perforated
plate visible from the ventral side and nested only `0.277824 mm` from component
`25`.

Deletion removed `30` visible faces. Isolated rigid lifting opened the
component-25 relationship to `4.887856 mm`. Masked radial movement introduced
three orientation failures, and depth compression visibly changed the plate.

A shared `35 mm` regional field was retained as
`REPAIR_002_COMPONENT_1_REGIONAL`:

- the component receives an `8.2 mm` near-rigid correction;
- `1,471` weighted neighboring vertices share the smooth falloff;
- component `1` clears the cutter and reserved margin;
- global penetrations fall from `422` to `397`;
- triangle overlaps fall from `1,037` to `978`;
- the component-25 relationship remains approximately `0.277 mm`;
- no negative-orientation locators appear;
- high-detail local and complete review shows no new silhouette or
  registration failure.

The affected-edge ratio range is `0.723772–1.312896`, so this remains a
reversible candidate rather than a general rule. It confirms that a regional
correction can work outside the wrist, but also confirms that falloff radius is
a real locality-versus-distortion tradeoff.

## Hidden-side masked-repair boundary

Components `25`, `37`, and `42` show a narrower valid use for masked radial
displacement. Each has a recognizable exposed form but concentrates its
collision on a buried branch or wearer-facing surface. After matched isolated
and assembly review, their bounded masks were retained as Repairs 003–005:

- `43` cutter penetrations were cleared in total;
- global cutter overlaps fell from `978` to `837`;
- source topology and materials remained unchanged;
- no orientation reversals were introduced;
- visible source composition remained intact in the reviewed views.

This method is not valid merely because a component is small. Components `36`
and `39` are similarly sized but their collision reaches visible wrist
geometry. Their masked trials introduced three and one reversed faces
respectively, while compression and isolated-lift alternatives visibly changed
their form or registration. Those method families remain rejected even though
later shared regional fields cleared both components.

The practical rule is therefore: use a masked field only when the displaced
surface is demonstrably buried in assembly context, not as an automatic repair
for a low vertex count.

Later retained repairs refine the regional-field boundary:

- component `16` uses a topology-local harmonic field rather than a regional
  rigid translation; this preserves the narrow ribbon that the earlier radial
  patch visibly collapsed;
- component `52` uses a `35 mm` regional rigid field affecting `839` vertices;
- component `57` uses a `45 mm` regional rigid field affecting `1,169`
  vertices.

The component-52 and component-57 fields clear their target violations without
closing wrist gaps, fusing neighboring parts, or exposing a falloff boundary
in sanitized high-detail matched views. Their affected-edge ratios remain
bounded at `0.857286–1.185305` and `0.768105–1.213738`. These are reviewed
local decisions, not reusable radius constants.

Three additional reviewed regional fields extend that evidence:

- component `59`: `40 mm` falloff, `14.739078 mm` target motion, `1,018`
  affected vertices, edge ratios `0.506504–1.475953`;
- component `36`: `30 mm` falloff, `4.382899 mm` target motion, `1,195`
  affected vertices, edge ratios `0.811078–1.197074`;
- component `39`: `25 mm` falloff, `13.094812 mm` target motion, `790`
  affected vertices, edge ratios `0.369226–1.736243`.

All three clear their targets without orientation reversals. Independent
sanitized local and assembly review retains their recognizable shapes,
registration, and negative spaces. The wider distortion tails on components
`59` and `39` remain explicit watch items; visual review, not a universal edge
ratio threshold, is what permits these reversible candidates.

Component `19` establishes a related but narrower method. A whole-component
regional direction cannot clear its broad wrapping plate within `50 mm`.
Instead, one seven-vertex collision cluster moves as a coherent rigid core by
`5.430353 mm`; a six-ring topology-local harmonic transition affects only 53
vertices. The target clears with no reversed faces and edge ratios of
`0.827474–1.088134`. Sanitized high-detail review preserves the faceted plate,
ridges, side fin, open U-shaped cross-section, and upper-arm registration.
This cluster-rigid method is valid here because the motion and transition are
small. It does not rehabilitate the same method for component `20`'s
`32–48 mm` major-cluster motions.

Component `9` establishes the large-component boundary. Although its dominant
collisions are buried inner walls, the connected source surface wraps across
multiple stations and radial directions. Whole-component regional motion is
therefore undefined, and masked projection produces `58` reversed faces.
Wider diffusion increases that failure to `90–125` reversed faces. For this
case, “regional” means a classified surface patch with explicit boundary
landmarks, not the entire connected component.

Component `20` establishes the deep-visible-cluster boundary. Its major
clusters need `48.205661 mm` and `32.556071 mm` of coherent motion to clear.
Pointwise harmonic projection reverses `8–22` faces and reaches an `11.8664`
edge ratio. Treating each cluster as a rigid core preserves relief, but
harmonically blending those full motions reverses faces in every tested
variant; fully clearing variants reverse `43–202`. A broad cutter-conforming
replacement preserves topology but fails visually as a smooth carrier-like
slab. This case requires a new local transition annulus around a
relief-preserving core, not a wider deformation field.

The first such closed-core annulus is also rejected. It preserves the smaller
cluster's original `87`-face relief and all audited topology counts, but its
continuous `60`-edge transition becomes a visible shelf/wall and bridges
intentional negative space. The next method boundary is therefore stricter:
reconstruct cutter-safe outward relief from the source's ridge landmarks
without translating the whole patch or connecting its full perimeter.

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
- `_validation/experiments/geometry_repair/component_1_methods/`;
- `experiments/geometry_repair/component_1_methods/README.md`.
- `_validation/experiments/geometry_repair/component_59_methods/repair_010_f40/`;
- `_validation/experiments/geometry_repair/component_36_methods/repair_011_f30/`;
- `_validation/experiments/geometry_repair/component_39_methods/repair_012_f25/`;
- `_validation/experiments/geometry_repair/component_19_methods/repair_013_r6/`.

At this checkpoint:

- tracked master SHA-256:
  `11cde6a6192bc4c10582809d6362a30b9f14d6e8fe577252771fb39413944a85`;
- retained rescue SHA-256:
  `7b41ab80f65385d6f52f944d9845a702b4ed50ed834ff9af70fec0bf2b93c512`.
- deep-wrist pilot and archived checkpoint SHA-256:
  `72116cf94c428e585af156ce6f9260a4304058011fab1a7f2e4dbb164b35afc6`.
