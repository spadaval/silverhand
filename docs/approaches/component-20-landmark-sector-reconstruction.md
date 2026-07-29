# Component 20 Landmark-Sector Reconstruction

Status: **active evaluation; minimal local interface reconstruction selected**

Updated: 2026-07-29

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

### Rejected seven-face retessellation

The smallest topology-changing cell was the complete seven-triangle fan around
source vertex `4863`, bounded in order by source vertices
`4860, 4861, 4864, 4865, 4866, 4867, 4869`. The cell is disjoint from every
frozen opening, ridge, and depth-break chain.

After the 31 cluster vertices were placed at the authored `1.7 mm` floor, all
`42` triangulations of that boundary were tested. None kept every replacement
triangle aligned with the source cell's winding. No evaluation object or
candidate geometry was created, saved, or submitted for image review.

Do not relax the winding gate or retry another diagonal choice inside this
same seven-face boundary. The next bounded test retains the original fan and
checks whether vertex `4863` has a cutter-safe feasible position that preserves
all seven incident triangle orientations. If that feasible region is empty,
the authored boundary must widen beyond this cell.

### Rejected single-control fan solve

A bounded half-space search retained the seven-face fan and treated vertex
`4863` as its only authored control. The other 30 cluster vertices were placed
at the `1.7 mm` floor. The best of `304` deterministic control positions:

- cleared all 31 reserved-margin failures;
- preserved all seven incident triangle orientations, with a worst normal dot
  of `0.585329`;
- preserved topology, winding counts, and the exact outside fingerprint;
- left a weak `1.314405°` minimum triangle angle;
- increased the measured local-cell overlaps from `49` to `89`;
- increased global cutter-triangle overlaps from `653` to `701`.

This proves that vertex `4863` is not the remaining control problem. The
independently clamped surrounding faces cross the curved cutter even when the
central fan is orientation-safe. Do not retry single-control positions or
submit this result for image review.

The next bounded method must coordinate the ring-4 wearer-side surface using
triangle/cutter collision evidence, not vertex margins alone. It must freeze
the named exterior landmarks and drive colliding faces outward as a coherent
local floor.

### Rejected same-topology face-aware sector

A deterministic ring-4 solver froze the exact outer transition, source-open
chain, and every named landmark, then used cutter-triangle intersections to
coordinate the remaining wearer-side vertices. Its initial `1.7 mm` floor:

- cleared all 31 cluster failures;
- reduced ring-4 overlapping faces from `77` to `70`;
- increased global overlaps from `653` to `733`;
- introduced seven source-normal reversals;
- displaced affected vertices by up to `31.396805 mm`;
- changed affected edge lengths by factors of `0.100166–3.149865`;
- preserved topology, winding counts, the outside fingerprint, and all frozen
  controls.

The first outward face-correction step could not satisfy strict orientation,
so the solver stopped without a second run. This rejects same-topology ring-4
displacement. Do not tune its step or regularization factors.

The remaining justified escalation is authored topology between preserved
exterior seams. Before changing topology, map the complete component-20 visible
shell, hidden wearer-side floor, open boundaries, and attachment seams. The
reconstruction may replace the wearer-side architecture, but must retain the
reviewed game-model exterior and intentional openings.

## Selected full inner-bowl reconstruction

Disposable high-detail review rejects rebuilding all of component `20`.
Component `20` is the recognizable upper-arm/elbow shell: both dorsal and
ventral sides carry longitudinal ribs, plates, apertures, and silhouette loops.
Those features are the game-model exterior and remain source authority.

The selected reconstruction scope floods outward from both exact failure
clusters until a source edge reaches a `35°` dihedral barrier:

- preserve `1,409` exterior-cage faces exactly;
- replace `724` wearer-facing inner-bowl faces;
- register to `127` exact seam edges across five independent groups;
- keep three seam groups as open routes with `51`, `46`, and `18` edges;
- preserve two closed aperture loops with `8` and `4` edges;
- never merge the five groups into one annulus.

The `25°` boundary leaves avoidable small inner islands. The `45°` boundary
enters a recognizable raised exterior panel, and the `60°` boundary branches.
The `35°` basin is therefore the accepted authored topology boundary, not a
tunable parameter.

Component `20` can be reconstructed independently from component `9` only with
component `9` as read-only collision context. Freeze the 15 component-20
vertices within `1 mm` of component `9`, including:

- component-20 vertex `2074` to component-9 vertex `1257` at `0.012323 mm`;
- component-20 vertex `2119` to component-9 vertex `1295` at `0.040267 mm`.

The implementation architecture is a preserved exterior cage plus a
low-complexity cutter-safe inner-bowl liner. Use a coarse radial/axial grid,
retain macro bowl and recessed-strip depth, add only local transition loops,
and preserve every opening. This is still fitted-surface work; printable wall
thickness and final structural junctions remain later milestones.

### Shared elbow-interface exception

Inner-bowl construction preflight found that two of the 15 nominally frozen
component-9 interface vertices are themselves in component-20 cluster `0`:

- component-20 vertex `2074` has cutter margin `-10.190998 mm` and requires at
  least `11.890998 mm` of motion to reach the `1.7 mm` floor;
- component-20 vertex `2119` has cutter margin `-8.024861 mm` and requires at
  least `9.724861 mm` of motion.

Freezing those vertices and clearing both component-20 clusters are mutually
exclusive. No liner geometry was created under the contradictory contract.

Treat the two near-coincident pairs as a shared elbow junction:
component-20 `2074` with component-9 `1257`, and component-20 `2119` with
component-9 `1295`. Their first bounded trial must move each pair together,
preserve its relative offset, blend through both components locally, and keep
the other 13 interface anchors exact. This does not authorize a component
fusion or a global component-9 deformation.

The selected three-ring coordinated staging move is conditionally accepted
only as input to the authored liner:

- both shared anchors reach the `1.7 mm` floor;
- both pair-relative vectors remain exact;
- the other 13 interface anchors remain exact;
- it introduces no vertex failures or orientation locators;
- affected edge ratios remain `0.522057–1.785424`;
- component-9 overlaps fall from `389` to `387`;
- component-20 overlaps rise from `264` to `266`;
- global overlaps remain `653`.

All 30 newly overlapping component-20 face/cutter pairs belong to the selected
724-face removal set; none lies on retained exterior geometry. The staging
move therefore remains a standalone `FAIL`, but is
`CONDITIONAL_PASS_FOR_COMBINED_LINER_STAGE`. Its exact ignored evaluation
checkpoint has SHA-256
`393a7c1a29c96c876fe2be849c3b9a4e42c771416cd59b3f733a7f0c65342bcd`.
The complete combined liner must revalidate every gate.

### Rejected single-chart inner-bowl liner

The first topology-changing liner treated the complete 35° basin as one
polygonal chart. It preserved the exterior fingerprint, all interface controls,
component-9 overlaps, connected-component count, and open-boundary counts.
It also reduced global cutter overlaps from `653` to `449`.

The construction is nevertheless rejected:

- replacement overlaps stalled at `48`;
- it introduced `16` noncontiguous manifold edges;
- `104` replacement triangles were degenerate;
- the replacement aspect ratio reached `1758.442672`;
- `3,713` replacement triangles opposed the removed-region mean normal.

The basin has two outer cycles sharing one articulation vertex plus two
apertures, and it is strongly nonplanar. A single-plane tessellation creates
long cross-bowl chords before subdivision. Projecting those chords onto the
curved cutter folds the patch. Do not tune the single-chart floor, subdivision,
or outward correction.

The next authored architecture must split the same 724-face basin along durable
ridge and valley routes into several locally planar charts. Charts must share
exact internal seams and collectively preserve the same 143-edge external
boundary, interface controls, source-open routes, and aperture loops.

### Rejected complete-boundary cycle liner

The complete removed-region boundary resolves to a `123`-edge outer cycle, an
independent `8`-edge outer cycle, and `8`- and `4`-edge aperture loops. The
123-edge outer cycle and 8-edge aperture meet at source vertex `2008`; the
trial used chart-local coincident occurrences rather than recreating source
bridge face `5798`.

Separating the complete cycles removes cross-lobe triangles but does not make
the large outer chart planar:

- the small 8-edge outer chart is cutter-clear but has nine reversals;
- the 123-edge chart stalls at 52 cutter overlaps;
- the 123-edge chart contains 3,678 reversals;
- global overlaps improve from `653` to `453`;
- retained geometry, component-9 state, and interface vectors remain exact;
- topology and triangle-quality gates fail.

Do not increase collision iterations or retry three-dimensional planar
tessellation. The next parameterization must use the arm's native axial-angle
coordinates. First prove that the 123-edge boundary and its aperture loops are
simple in unwrapped cylindrical coordinates; only then build a structured
radial/axial liner.

The cylindrical gate also rejects a single global chart. After excluding the
expected winding cut at edge `15480`, the 123-edge loop has four genuine
crossings:

- edge `8056` with `10557`;
- edge `13026` with `1560`;
- edge `19587` with `14223`;
- edge `15804` with `1203`.

The 8-edge outer loop and both aperture loops are simple. No UV liner geometry
was created.

Because this is a cosplay build and the mapped bowl carries less signature
detail than its rim and exterior cage, evaluate one deliberate destructive
simplification before authoring that seam network: remove the 724-face bowl
without filling it and retain the 1,409-face exterior cage as an open shell.
This is not automatic promotion or printable approval. It tests whether a
minimal later liner and structural junctions are preferable to reconstructing
the source bowl.

The open-cage evaluation removes exactly 724 faces and 318 vertices that become
unused, while retaining all 1,409 exterior faces and materials exactly:

- component-20 cutter penetrations fall from `110` to `0`;
- component-20 reserved-margin failures fall from `196` to `39`;
- component-20 cutter-triangle overlaps fall from `266` to `14`;
- global overlaps fall from `653` to `401`;
- component-9 remains exactly at `387` overlaps;
- 127 new boundary edges remain in the expected `51/46/18` open groups and
  `8/4` closed loops;
- the cage separates into three additional connected pieces;
- only interface vertices `5840` and `5852` remain owned by component `20`;
  the other 13 mapped interface controls disappear with the bowl.

Disposable matched-view review rejects the bare deletion as final geometry.
The exterior identity survives, including the primary silhouette, long dorsal
ribs, circular elbow aperture, and major accents. The missing bowl nevertheless
reads as a catastrophic hole: the axial view becomes an almost empty ring, the
retained islands look structurally unjoined, and no component-20 surface owns
the 13-control component-9 interface arc.

The same review passes a narrower reconstruction direction. Retain the exact
1,409-face exterior cage and keep the center open, then:

1. build a narrow, closed, positive-volume C-shaped band facing component `9`;
2. pass the band through the 13 lost component-20 interface controls
   `2054, 2055, 2058, 2060, 2062, 2064, 2074, 2108, 2111, 2114, 2115, 2118,
   2119`;
3. connect the band to each retained cage island with the shortest stable
   local ribs or tabs;
4. retain component-20 controls `5840` and `5852` as hard registration checks;
5. preserve component `9` and the exterior cage exactly.

Do not promote the bare open cage, refill the complete bowl, or create a global
backing union. The local band/junction network is the active evaluation.

The first local network is a rejected scale control. Its `1.6 mm`-wide by
`1.8 mm`-deep rail passes the machine gates with zero cutter or internal
self-intersections and restores all 13 controls exactly. High-detail review
nevertheless shows a crooked wire inside the original catastrophic opening.
Its four square links read as spikes or toothpicks, and the rail disappears
behind and re-emerges across component `9`. Do not tune that uniformly narrow
construction.

The structural-width escalation follows the corrected 21-control route,
including source control `2110`, and uses a `6.0 mm` ribbon width with
`2.4 mm` outward radial thickness. Its first numerical candidate:

- needs no local width collapse and has zero internal self-intersections;
- is closed, consistently wound, and has positive volume `1192.902715 mm³`;
- adds five individually closed local attachment solids whose contact graph
  joins the band and all four retained cage islands;
- has zero cutter overlaps, but its `1.599998 mm` minimum sampled margin misses
  the exact `1.6 mm` construction floor by `0.000002 mm`;
- preserves the 1,409-face exterior cage, component `9`, all 13 restored
  controls, controls `5840/5852`, and the `30.588488 mm` C-tip gap exactly;
- leaves global cutter overlaps at `401`, including `387` on component `9` and
  `14` on the retained component-20 cage.

Four attachment solids also each contain one degenerate audit triangle; the
optional `0.430970 mm` micro-tab reaches aspect ratio `13.909031`. The exact
machine result is therefore `gate_pass=false` on `new_vertex_margin` and
`triangle_quality`, despite the other structural and collision gates passing.

The new network also has `162` triangle contacts with component `9`. Those
contacts are not permission to fuse the 11 non-tip historical interface pairs,
whose current separations are `5.553838–10.537240 mm`. The broad candidate
remains evaluation-only.

Disposable matched-view review validates the structural concept and scale:
`INTENTIONAL_OPEN_CENTER`, `ELBOW_INTERFACE_CONTINUITY`,
`STRUCTURAL_SUBSTANTIALITY`, `EXTERIOR_IDENTITY`, and `NO_GLOBAL_BACKING` pass.
The broad rail frames the aperture as deliberate negative space and organizes
the four islands without recreating the bowl. `C9_LAYER_ORDER` and
`LOCAL_GUSSET_READ` fail: distributed rail fragments appear through component
`9` in every projection, while square-ended junctions read as blocks, hooks,
and stubs.

The v3 numerical cleanup removes the optional high-aspect micro-tab, replaces
the four degenerate attachment caps, and separates preserved source endpoints
from the `1.61 mm` new-vertex margin gate. All named machine gates then pass:
new geometry has at least `1.699992 mm` cutter margin, every constituent is
closed and internally non-self-intersecting, and attachment aspect ratio is at
most `4.881516`.

This cleanup does not solve layer order. It localizes `164` component-9
triangle contacts: `126` belong to the band and `38` to the island-1/island-3
junction. The band contacts occupy both outer anchor arcs; the middle route
from `2065→2067` through `2071→2073` is clear. A later construction must place
the broad ribbon asymmetrically on the component-20 side of its exact control
route and reroute that junction. Do not globally narrow the band or move
component `9`.

### Rejected asymmetric rail controls

The rail-only v4 sequence proves that all 13 required anchors are individually
feasible, but several straight source-control chords cross component `9`.
Bounded midpoint and two-waypoint sweeps cannot route `2064→2065` or
`2064→2067` around that barrier within `12 mm`. Progressive removal of
non-anchor route controls finds a feasible simplified route:

- replace the intermediate cross-rail controls with direct `2064→2118`;
- replace non-anchor `2110` with direct `2111→2108`;
- retain every required anchor exactly.

A rotating asymmetric rectangle on this route reduces non-tip component-9
contacts to six, all on `2111→2108`, while the rest of the non-tip rail is
clear. A later fixed-orientation detour and seven-case local width sweep from
`6.0` down to `3.0 mm` does not solve the collision and introduces `54–55`
self-overlap pairs. Width is not the blocker; the detour orientation folds the
rail.

Do not tune more global asymmetry or taper values. Return to the last
self-intersection-free simplified route and locally notch, miter, or bevel only
the remaining component-9 collision neighborhood against an explicit clearance
envelope. A bounded movement of the adjacent non-tip controls is acceptable
only if exact preservation is proven incompatible with a clean local notch.

The exact-anchor vertex-push notch is also rejected. It leaves all six non-tip
component-9 contacts, introduces one self-overlap, collapses the inherited
adaptive width to `1.008416 mm`, and either exceeds the `2 mm` movement bound or
stalls at the bound without improvement.

A two-anchor transition sweep provides the first component-9-clear rail:

- `63` of `81` cases pass every named machine gate;
- the minimum change keeps `V2111` exact and moves only `V2108` by `0.5 mm`
  away from component `9`;
- the adjacent two rings blend through `0.333333 mm` and `0.166667 mm`;
- all remaining non-tip component-9 contacts fall to zero;
- the other 11 required anchors remain exact;
- the rail remains closed, consistently wound, positive-volume,
  self-intersection-free, and cutter-clear;
- minimum cutter margin is `1.699990 mm`, minimum angle is `4.406157°`, and
  maximum aspect ratio is `6.570828`.

This is a rail-routing machine pass, not visual or structural promotion. It
inherits the non-folded v4f adaptive width profile of
`1.008416–6.000003 mm`; therefore it does not yet satisfy the visually
validated substantial-width contract across the full route. Restore a
non-folding full-width sweep before final visual review.

The matching local-gusset evaluation also remains blocked. Its island-3 edge
and each constituent's topology, self-clearance, cutter clearance, margin, and
quality can pass independently. The two required rail-to-island landings
cannot: corrected direct, bounded midpoint, and historical-route-prepend
searches each retain exactly five component-9 overlaps. Do not treat the prior
v7 report or copied Blend as current result evidence. The rail and cage
junctions must be reconstructed as one obstacle-aware structural system.

A deterministic minimum-twist reconstruction shows that frame continuity
alone cannot restore that width on the monolithic exact-control route. Of 24
bounded global rolls, only `60°` and `75°` admit complete fixed-width,
cutter-clear ring fields, and neither produces a passing rail. The least-bad
case restores width to `5.999994–6.000005 mm` and thickness to
`2.399993–2.400007 mm`, remains cutter-clear with `1.699990 mm` minimum
margin, and preserves the retained cage, hard controls, 11 unaffected
anchors, tip gap, and selected V2108 transition. It nevertheless has:

- `134` non-tip component-9 overlap pairs;
- `69` self-overlap pairs;
- `2.680580°` minimum triangle angle;
- `15.361248` maximum triangle aspect ratio.

Do not expand the global/local roll search or reintroduce adaptive narrowing.
The combined v4–v8 evidence rejects a single broad strip constrained through
all legacy interface controls. The next structural candidate may relax those
controls explicitly and use a small connected set of broad, closed local
plates or rails. It must report every relaxed control and displacement,
preserve the visible cage and open center, and pass the same component-9,
cutter, topology, wall-margin, and quality gates before visual review.

The first three-constituent realization proves that this partition can clear
component `9` and form a measured structural graph, but not with one scalar
translation direction per constituent. Its least-bad selection has zero
component-9 overlaps and measured contact counts of `18` for the B0 cage
landing, `27` for B0–B1, and `39` for B1–B2. Every constituent is closed,
positive-volume, contiguous, nondegenerate, fixed at approximately
`6.0 × 2.4 mm`, and within the triangle-quality bounds. It still fails:

- B0 enters the cutter in `9` pairs and reaches `-2.848886 mm` margin;
- B1 has `2` self-overlap pairs and only `0.334421 mm` cutter margin;
- B2 enters the cutter in `4` pairs, reaches `-1.638994 mm` margin, and has
  `18` self-overlap pairs.

All 13 legacy interface controls are therefore explicitly relaxed in this
failed result; six are coordinate-coincident but belong to an infeasible
constituent and are not claimed exact. Keep the three-piece partition as
useful evidence, but reject the single away-from-component-9 displacement
field. A later preflight may search bounded directions in the local normal
plane to determine whether component-9 clearance and cutter margin can coexist
at full width before another mesh is built.

That direction-field preflight evaluates `4,896` fixed-section candidates per
constituent. It proves full-width placement is feasible for the left arc and
center bridge: B0 has five admissible candidates and B1 has nine. Their
least-bad passing cases have zero component-9, cutter, and self overlaps with
minimum cutter margins of `5.228782 mm` and `4.069370 mm`, respectively.

The right arc B2 is the isolated blocker. None of its `4,896` cases passes.
Its least-bad case clears both component `9` and the cutter, but has `10`
self-overlap pairs, a `-0.541454 mm` cutter margin, and maximum aspect ratio
`17.033039`. No v10 geometry is emitted. Preserve the feasible B0/B1 evidence
and split only B2 at a natural legacy control before changing section width or
expanding displacement bounds.

Splitting B2 at V2111 leaves the terminal piece infeasible (`16/0`
admissible candidates). Splitting at V2108 makes both pieces independently
feasible (`2/45` admissible candidates), so the sharp-turn decomposition is
accepted as the next structural partition. Direct overlap is not a valid
junction mechanism, however: the preserved B0/B1 pair has zero overlaps, and
none of the admissible V2108-split B2a/B2b pairs overlap. No v11 geometry is
emitted. Keep the four feasible broad constituents and evaluate short,
separately closed local bridge junctions between them.

### Connection-aware machine pass

Joint selection of all admissible broad pieces produces the first complete
machine-pass network. Four fixed-width constituents form two direct overlaps;
a single short local bridge closes the remaining B2a–B2b gap:

- B0 cage landing: `152` measured overlaps;
- B0–B1: `19` measured overlaps;
- B1–B2a: `27` measured overlaps;
- B2a–bridge and bridge–B2b: `11` and `37` measured overlaps.

The bridge spans a `9.879956 mm` endpoint gap. It is `6.0 mm` wide at its
`1.5 mm` embedded terminal flares, narrows to `4.5 mm` internally, and remains
`2.4 mm` thick. It has zero component-9, cutter, and self overlaps,
`4.617902 mm` minimum cutter margin, `13.415411°` minimum triangle angle, and
`4.310167` maximum aspect ratio.

The complete network passes all named machine gates:

- all four broad pieces and the bridge are closed, positive-volume,
  contiguous, and internally self-clear;
- component-9 and network cutter overlaps are zero;
- minimum constituent cutter margin is `2.088698 mm`;
- broad width is `5.999992–6.000006 mm` and thickness is
  `2.399993–2.400006 mm`;
- aggregate minimum angle is `4.070079°`, maximum aspect is `11.670955`, and
  there are no degenerate triangles;
- the retained 1,409-face cage/material fingerprint, hard controls V5840 and
  V5852, open center, and `30.588488 mm` tip gap remain exact.

This result explicitly relaxes all 13 legacy interface controls by
`4.5–8.0 mm`; they are registration evidence, not retained geometry. The
network remains evaluation-only until disposable high-detail review passes
exterior identity, intentional negative space, substantiality, component-9
layer order, and local bridge/junction read.

Disposable review confirms the machine validity but rejects promotion.
`EXTERIOR_IDENTITY`, `STRUCTURAL_SUBSTANTIALITY`, `C9_LAYER_ORDER`,
`NO_GLOBAL_BACKING`, and `NO_NEW_SILHOUETTE_REGISTRATION_DAMAGE` pass.
`INTENTIONAL_OPEN_CENTER`, `ELBOW_INTERFACE_CONTINUITY`,
`LOCAL_JUNCTION_BRIDGE_READ`, and `NO_CATASTROPHIC_OPENING` fail.

The problem is now the graph contract, not section size or obstacle clearance.
The reported B0 cage landing tests overlap against the union of all retained
cage faces. In matched views, the complete new network reads as a robust loop
in one lower/side region; it does not visibly reach the upper major cage island
and therefore leaves the decisive upper-to-lower discontinuity intact.
Square caps, hooks, rectangular nubs, a cross-shaped block, and a thin sliver
also keep the local junctions from reading as deliberate structure.

A subsequent terminal audit finds that the v12 landing gate was weaker still:
it tested B0 against the complete 11,840-face open-scene object, not the
1,409-face retained component-20 cage. The cage resolves into four explicit
terminals:

- `T_CAGE_0`: `376` vertices, `553` faces;
- `T_CAGE_1`: `466` vertices, `814` faces;
- `T_CAGE_2`: `25` vertices, `40` faces;
- `T_CAGE_3`: `4` vertices, `2` faces.

V12 B0 has zero triangle overlaps with every terminal. Its reported `152`
“cage” pairs are entirely nonterminal: `64` hit source component `0` and `88`
hit source component `25`. The abstract v12 cage-root gate is invalid and the
network is not physically rooted in retained component `20`, despite its
internally connected new-constituent graph.

Sanitized five-view terminal mapping assigns `T_CAGE_1` to the upper major
island, `T_CAGE_0` to the lower major island and its connected brace/arch,
`T_CAGE_2` to the small diagonal-middle lozenge, and `T_CAGE_3` to the
two-face side remnant. The required wearable terminal pair is therefore
`T_CAGE_1 ↔ T_CAGE_0`; the smaller terminals cannot substitute for either.

The next candidate must replace the abstract `B(root)` node with named
retained-cage connected components. Require measured terminal contact and an
explicit path from the upper major island through the network to the lower
major island. Preserve v12's section dimensions and collision gates; replace
only the topology and terminal/junction shapes. Use embedded flared saddles or
gussets, not another free loop, and reject exposed square, hooked, stubbed, or
spiked ends.

The exact V5702/V1784 representatives provide a first machine-pass explicit
terminal bridge. A direct seven-ring saddle at `120°` roll embeds `1.5 mm`
into both `T_CAGE_1` and `T_CAGE_0`, with three measured overlaps at each end.
All six full-scene contacts belong to those selected terminals; unrelated
source, T2, T3, component-9, cutter, and self overlaps are zero.

The bridge is `6.0 mm` wide at its embedded ends, transitions through
`5.25 mm`, narrows to `4.5 mm` internally, and remains `2.4 mm` thick. Minimum
cutter margin is `2.703769 mm`; it is closed, contiguous, and positive-volume
with `13.643691°` minimum angle, `4.239386` maximum aspect ratio, and no
degenerate triangles. The retained cage fingerprint/materials, component `9`,
open center, tip gap, and hard controls remain exact. This is the first result
with an authoritative `upper major → bridge → lower major` graph, but it
remains evaluation-only.

The v14 qualitative review rejects promotion despite that machine pass. Four
sanitized orthogonal terminal overlays independently show the exposed bridge
as a short tab, nub, shim, or shelf. Its numerical end flare is buried inside
the retained terminals, so neither landing visibly spreads load into the cage
and the large opening still reads as catastrophic rather than deliberately
framed. Preserve the proven V5702→V1784 route and midspan, but rebuild only its
terminal transitions as surface-following fan saddles approximately `10 mm`
wide by `8 mm` long, with at least `1.5 mm` measured embed and rounded or
mitered exposed shoulders. Recheck the four orthogonal views before spending
an image operation on the elbow-axial gate.

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
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_authored_patch/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_authored_fan_feasibility/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_face_aware_sector/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_full_recon_map/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_authored_inner_bowl/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_coordinated_interface/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_combined_inner_bowl_liner/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_boundary_cycle_liner/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_cylindrical_uv_liner/`
- `_validation/experiments/geometry_repair/component_20_methods/repair_014_open_cage_simplification/`
