# Silverhand — Rework History

This file preserves lessons from rejected approaches without keeping their
geometry, scripts, and binaries in the active workflow. Historical dimensions
were recorded in centimeters before the 2026-07-27 millimeter migration.
Current authority remains in [design.md](design.md) and
[status.md](status.md).

## Original extracted model

- Game rip of Johnny Silverhand’s damaged cyberarm.
- Zero-thickness render geometry with hundreds of disconnected islands.
- `arm_fitted_master` remains the visible source authority.
- The proven 3MF established useful wearer scale and armor-shape evidence, but
  its build-plate transforms are not anatomical registration.

## Legacy segmented sleeve

An early smooth half-shell sleeve was split into wrist, forearm, elbow, and
bicep exports. The elbow loft crossed into a fan/slab and several outputs were
open or degenerate.

Lesson: bed fit and manifold reports cannot rescue incorrect construction.

## Carrier-backed source overlays

Small source fragments were projected onto a smooth anatomical sleeve. The
result lost most source detail and produced a generic cyber-sleeve appearance.

Lesson: the fit envelope cannot govern the visible exterior.

## V2 global voxel sleeve

A source-derived exterior was voxel-unioned with a backing and cut to a clean
lumen. It became one manifold object, but visible detail was melted or
misclassified.

Lesson: one watertight mesh is not proof of source fidelity.

## Boolean V3 sleeve

Dozens of closed source operands were Booleaned into an engineered backing. The
result avoided global voxel remesh but inherited a destructive straight-axis
crop and lost visible prepared surfaces during union.

Lesson: exact Boolean operations can still destroy the design; visible surfaces
must be approved before manufacturing cleanup.

## V4 reconstruction experiments

Piecewise cropping, exterior filtering, relief conformation, and surface-master
assemblies improved individual failure modes but continued to rely on a broad
backing and ambiguous material classification.

Lesson: iterative repair of the wrong exterior architecture compounds debt.

## Single-depth reconstruction coupon

A continuous radial relief coupon produced clean manufacturing geometry but
could not represent the region’s multiple depth layers.

Lesson: a single-valued height field is useful for shallow relief and tactical
repair, not as the complete representation.

## Layered carrier-backed coupon

Six preserved detail solids overlapped a recessed carrier. The STL passed
geometry checks and Bambu Studio sliced it successfully with support warnings.

Lesson retained: overlapping closed solids are slicer-viable. The carrier is
not retained as the full-arm architecture.

## Carrier-free baseline

The latest experiment preserved source rails, cables, mechanical masses, and
negative space more convincingly. Its editable result contained 101 closed
detail solids, but remained split into many overlap groups with isolated parts.

Subsequent matched-camera review rejected it as the production starting point.
The source/current contact sheet shows exploded component placement, lost
registration, severe bicep/shoulder compression, unexpected warping, and
floating fragments.

The generator combined several operations before visual approval:

- hard-coded straight-axis source coordinates;
- piecewise longitudinal compression and expansion;
- radial-depth compression;
- eight independently lifted forearm sectors;
- collision-driven per-component translation;
- automatic internal, axis-spanning, collision, and tiny-face removal;
- local sheet solidification into 101 closed constituents.

Lesson: source fitting, visual reconstruction, solidification, and connectivity
must be separate promotion stages. A zero-collision manifold result cannot
rescue a failed source transformation. The 101-solid scene remains historical
transformation evidence, not a salvage library.

## 2026-07-27 reset

Approved strategic changes:

- migrate the entire project to millimeters;
- use wearer-first fit authority;
- use the fit volume only as a clearance cutter/collision tool;
- preserve good visible source geometry but freely re-engineer hidden
  manufacturing topology;
- reconstruct visible regions only through bounded source-comparison;
- defer tactical armor panels and hardpoints until main geometry is correct;
- plan major armor around magnet-to-magnet clamping plus mechanical
  registration.

The source-first transformation strategy was then tightened after review of the
clean-source/current contact sheet:

- restart production work from the clean armor-stripped source;
- use straightening only as a reversible coordinate representation;
- apply one shared smooth deformation to the entire source;
- preserve topology and relative registration through fitted-surface approval;
- allow only monotonic radial-depth compression;
- forbid automatic face deletion and per-component collision lifting;
- solve visible fit before solidification and connectivity;
- treat shoulder, elbow, and deeply embedded failures as bounded
  reconstruction regions.

Implementation scope was then narrowed further:

- use the provided anatomical reference for the first general human-fit
  surface, with wearer-specific tailoring deferred;
- make the straight construction pose the canonical static model and later
  segmentation basis;
- treat approximately `30°` as the future priority appearance pose;
- defer mobility until after static source fidelity and anatomical fit;
- allow a separate elbow assembly, an open inner-elbow gap, and flexible dorsal
  cables as candidate motion architectures rather than forcing a continuous
  closed elbow.

## First anatomy-led static-fit prototype

The first post-reset implementation used a shape key rather than a cage,
remesh, or destructive bake. The source already follows a reviewed straight
axis, so every source vertex could be mapped directly into a straight
anatomical coordinate field while preserving the exact source as the Basis.

This established a useful positive result: one shared deformation field keeps
all `64` disconnected source components registered. The result is recognizable,
has no exploded pieces, and preserves source topology and material assignment
exactly. This is a much better implementation foundation than the rejected
processed baseline.

Several automatic clearance strategies were then rejected:

- An angular percentile field preserved overall size but followed gaps between
  disconnected source pieces and introduced local ripples.
- A station-only baseline reduced clearance failure to six components and a
  `-11.754 mm` minimum vertex margin, but inflated the complete sleeve and
  damaged mass distribution.
- A low-frequency angular field restored a more source-faithful silhouette but
  exposed the prosthetic model's deep internal layers: `19` components and
  `743` vertices remained inside the cutter.
- Strong asymmetric inward-depth compression reduced the remaining vertex
  failure to `16` vertices within `-0.956 mm`, but visibly collapsed axial depth
  and negative space.

Lesson: the shared field can establish registration and broad human proportion,
but it cannot simultaneously preserve every prosthetic depth layer and create a
human lumen. Clearance must not be won by globally inflating the silhouette or
flattening the source. Preserve the best visual shared-field candidate, then
classify and reconstruct the bounded interior, shoulder, elbow, and wrist
failures under matched-view review.

## First bounded clearance rescue

The static-fit failures were approached as a reversible second shape key rather
than destructive topology repair. Several variants were rejected:

- pointwise projection cleared all violating vertices but ironed interior
  layers onto the cutter and created `80` negative-orientation locators;
- connected-patch depth preservation produced visible spikes and layered
  protrusions;
- protecting every externally visible face left most of the actual failure
  untouched and increased triangle overlaps;
- a plain `5 mm` lift cap preserved the silhouette but left `13` local
  orientation locators;
- a global `2 mm` cap removed those locators but rescued only `304` vertices.

The retained experiment combines the `5 mm` cap with an automatic,
topology-driven deferral rule. Tentative triangles that rotate more than
90 degrees from the pre-rescue surface are treated as review failures; their
vertices are locked and the field is rebuilt. This retained `566` shallow
rescue vertices while reducing new orientation locators to zero. The exterior
matched views remain effectively unchanged.

Lesson: shallow failures can be rescued by a bounded global rule, but deep
prosthetic interior layers cannot be made wearable by continuing to push them
radially. Stop when the lift or local-orientation bound is reached and classify
the remainder for explicit reconstruction.

## Direct deep-clearance Boolean trial

An exact Boolean difference against `CUT_CLEARANCE_ANATOMY_STRAIGHT` was tested
on a baked copy of the fitted/rescued surface.

The normal Exact mode interpreted the open source sheets as ambiguous solids,
grafted large cutter walls and end caps into the result, increased
non-manifold edges from `1,756` to `2,865`, and increased cutter overlaps from
`1,051` to `1,714`.

Exact mode with hole-tolerant processing avoided the full cutter shell but tore
large visible holes through the arm. It increased non-manifold edges to `2,546`
and still left `932` cutter overlaps.

Preconditioning the candidate with a `1 mm` Voxel Remesh made every generated
piece closed and manifold, but turned the open render sheets into `3,409`
separate thin solids. The subsequent Boolean produced `92` closed solids and
visually removed almost the entire arm, leaving cables and scattered exterior
fragments.

Lesson: Boolean subtraction cannot reliably classify inside and outside on this
open, disconnected render topology. A global remesh only makes the malformed
interpretation manifold; it does not create the intended sleeve volume. The
remaining deep failures need explicit surface classification and bounded
reconstruction before a cutter can be used as a reliable manufacturing
Boolean.

## Deep-fragment reconstruction pilot

One borderline fragment and one deeply embedded wrist fragment were tested
without changing the retained rescue candidate.

The borderline case confirmed that a procedural per-vertex displacement field
can resolve a very small violation with negligible visible change. That does
not generalize to deep failures.

On the deep wrist fragment:

- deleting penetrating vertices destroyed about half the surface;
- uniform radial offset inflated the fragment;
- masked displacement and radial-depth compression cleared the cutter by
  collapsing the fragment's depth;
- rigid translation preserved its form but displaced it by `15.2 mm`.

Spreading that rigid translation into all nearby geometry with a smooth spatial
falloff was more promising than editing the fragment alone. A `25 mm` falloff
preserved the fragment and improved the global clearance count without the
wide collateral effects of a `40 mm` falloff, but it remains an unapproved
fit-field experiment.

Lesson: a deep collision can be evidence that the regional fit field is wrong,
not that the isolated source island is defective. Test a bounded shared
deformation first. Rebuild visible or hidden surfaces only when coherent
regional motion cannot preserve source registration.

See the
[regional clearance-deformation approach](approaches/regional-clearance-deformation.md)
for the pilot evidence, method bounds, and continuation plan.

## First stepwise geometry-repair pass

The retained rescue was copied into a fresh ignored repair scene. Remaining
components were then approached one at a time, with a checkpoint before each
saved change and early rejection when a numerical or visual failure appeared.

Component `0` was the only retained patch. A reversible masked shape key clears
its two remaining penetrations without changing topology, materials, or the
reviewed silhouette. It reduces total cutter penetrations from `424` to `422`
and triangle overlaps from `1,051` to `1,037`.

The same method does not generalize:

- component `16` visibly narrows and contracts one edge to `27%`;
- component `19` introduces a negative-orientation locator;
- component `52` introduces two negative-orientation locators and extreme edge
  distortion;
- component `59` is a visible cuff brace layered against a neighboring clear
  surface, so neither isolated movement nor pointwise projection preserves it.

Lesson: “shallow” is not a sufficient repair classification. A bounded patch
must pass local edge/orientation evidence and high-detail perceptual review.
Stop reusing a method as soon as its failure pattern changes; park the region
for another reconstruction strategy.

## Hidden-side masked repair trials

After the retained component-1 regional correction, the remaining medium and
small failures were tested one at a time.

Masked displacement was retained for components `25`, `37`, and `42` because
their moved surfaces are buried in complete assembly views. These three repairs
clear `43` cutter penetrations without changing topology or introducing face
reversals.

The same method was rejected for two visible wrist components:

- component `36` introduces three reversed faces; the smooth compression
  alternative visibly changes the hook profile;
- component `39` introduces one reversed face; compression flattens and
  rotates the detail, while a rigid lift visibly relocates it.

Lesson: hidden-side visibility is the deciding constraint. A low vertex count,
small penetrating set, or clean numerical clearance result does not justify a
masked deformation when its effect reaches recognizable exterior geometry.

## Component 9 structural-inner-wall trials

The largest remaining failure was classified before further repair.
Component `9` spans most of the wrist and forearm in one connected
`2,508`-vertex surface, while its `163` penetrating vertices concentrate in
two dominant wearer-facing inner-wall clusters.

Every whole-component deformation is rejected:

- a rigid direction cannot represent a component that wraps around multiple
  stations and radial directions, and creates hundreds of new penetrations;
- radial compression and uniform offset clear the cutter but reverse faces;
- masked projection reverses `58` faces;
- increasing diffusion to spread the projection raises the failure to
  `90–125` reversed faces.

Deleting the penetrating vertices removes `466` mostly interior faces without
an obvious complete-view silhouette change. This is useful classification
evidence, not a repair: the open holes still require a deliberate local inner
surface.

Lesson: a connected source component is not necessarily one deformation
region. For a large structural shell, preserve the visible exterior and
replace only the classified wearer-facing patches with local cutter-derived
geometry. Classify nearly coincident neighboring layers before rebuilding so
the same lumen is not constructed twice.

## Component 20 classification and Repairs 006–009

Component `20` was classified before reconstructing the nearly coincident
component-9 inner wall. Its `135` reserved-margin failures form six clusters.
A six-ring harmonic field was retained only for minor clusters 2–5. The two
major wearer-facing clusters contain `87` and `32` failures and are not valid
whole-component deformation targets.

Three previously parked visible components were then revisited with different
methods:

- an eight-ring harmonic field clears component `16` without repeating the
  severe ribbon narrowing caused by the earlier radial patch;
- a `35 mm` shared regional field clears component `52` while preserving its
  wrist gaps and neighboring registration;
- a `45 mm` shared regional field clears component `57` while preserving the
  intertwined wrist strips and opening.

Repairs 006–009 preserve topology and materials, introduce no
negative-orientation locators, and pass bounded sanitized local and complete
matched-view review. They reduce global cutter penetrations from `354` to
`309` and overlaps from `837` to `741`. They remain reversible fitted-surface
candidates, not promotion.

The first cutter-derived replacements for component-20 major clusters are
rejected as transition-topology implementations. The raw patch splits the
candidate into four additional components. Boundary-bridged and conforming
variants retain the component count but increase boundary edges instead of
joining the source transition chains cleanly.

Lesson: a cutter-derived wearer-facing patch can identify the correct clearance
surface without supplying a valid boundary transition. A retained replacement
must preserve the reviewed exterior and must not increase either connected
components or boundary-edge count.

A later boundary-count-preserving strip satisfies those topology invariants:
it keeps `64` connected components, `1,756` boundary/nonmanifold edges, and
zero noncontiguous manifold edges while reducing penetrations from `309` to
`194` and overlaps from `741` to `519`. It is still rejected. Sanitized
high-detail bicep-axial review shows that the broad cutter-conforming strip
replaces the source's stepped angular inner depth with a smooth convex
carrier-like slab; `42` replacement overlaps also remain.

Lesson: topology preservation and improved clearance are necessary but not
sufficient. A wearer-facing reconstruction must carry forward the source's
local relief and depth landmarks rather than using the cutter itself as the
entire visible replacement surface.

Two direct attempts to preserve that relief without changing topology are
also rejected. Pointwise projection clears the two major component-20
clusters but introduces `8–22` reversed triangles and an `11.8664` maximum
edge ratio. Moving each cluster as a rigid core preserves its internal shape,
but the required `48.205661 mm` and `32.556071 mm` translations cannot be
harmonically blended back into the source: all tested blends reverse faces,
and the fully clearing variants reverse `43–202`.

A nearest-surface audit further rejects the hypothesis that component `20`
can simply be deleted as a duplicate of component `9`. Their closest points
reach `0.012323 mm`, but only two of the 118 major-cluster vertices lie within
`0.1 mm`; the median nearest distance is `10.186440 mm`.

Lesson: retain the original faceted cluster core under a coherent motion, but
make the transition a bounded topology problem. Reconstruct only a narrow
annulus between the translated core and retained source boundary instead of
smearing the full motion through existing faces.

That closed-core annulus was then tested on the smaller major cluster `1`.
Numerically it is clean: the original `87`-face core moves rigidly, connected
components and boundary counts are unchanged, winding remains contiguous,
penetrations fall from `309` to `296`, and overlaps fall from `741` to `704`.
Visually it is rejected. The `60`-edge, `120`-triangle annulus reads as a long
planar shelf/wall with spike-like tips and partially bridges the source's
local negative space. The translated core itself retains recognizable relief.

Lesson: the source relief is useful evidence, but moving the complete patch
and reconnecting its whole perimeter is not. Transfer the ridge/depth
landmarks as cutter-safe outward relief; do not span the local gap with a
continuous annulus.

The active master was reduced from 533 to 162 objects. Legacy collections,
duplicate references, cameras, missing image dependencies, and unused datablocks
were removed after creating:

- `blender_files/archive/Johnny_pre_cleanup_20260727.blend`
- `blender_files/archive/rework_evidence_pre_cleanup_20260727.tar.gz`
