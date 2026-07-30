# Silverhand Cyberarm — Design Contract

This document contains accepted design decisions only. Live progress belongs in
[status.md](status.md); rejected approaches and historical metrics belong in
[history.md](history.md).

## 1. Product goal

- Wearable cosplay piece, not a literal replica.
- Comfort and believable mechanical character outrank polygon fidelity.
- Printed geometry supplies the visible cables, rails, recesses, and panels.
- Flexible TPU forms the wearable structure.
- Rigid PLA armor remains removable and visually distinct.
- The hand/glove and pauldron are separate assemblies from the arm sleeve.

The current scope is the wrist crease through the upper bicep.

## 2. Units and manufacturing envelope

- Canonical unit: millimeters.
- Blender: Metric, `scale_length = 0.001`, `1 BU = 1 mm`.
- STL export scale: `1.0`.
- Printer: Bambu A1 mini, `180 × 180 × 180 mm`.
- Detail smaller than the selected nozzle/material process can reproduce is not
  a preservation requirement.

## 3. Authority by property

| Property | Authority |
|---|---|
| Visible composition | `SRC_GAME_TPU_ONLY_BASELINE`, supported by `SRC_GAME_FITTED`, and matching source comparisons |
| Initial digital fit | the provided anatomical reference and its derived fit volume |
| Personalized fit | wearer measurements and later physical fit tests |
| Clearance | the named cutter derived from the active fit reference |
| Source classification | explicit reviewed masks; material labels are supporting evidence only |
| Armor shape and scale | game source plus the proven 3MF, chosen per plate |
| Material behavior | physical TPU/PLA coupons |
| Current state | [status.md](status.md) |
| Promotion criteria | [validation.md](validation.md) |

No object name, script completion, manifold report, or slicer repair overrides
the appropriate authority above.

## 4. Fit

Wearer circumference evidence:

| Station | Measurement |
|---|---:|
| Wrist | 175 mm |
| Mid-forearm | 220 mm |
| Widest forearm | 255 mm |
| Bicep design target | 330 mm |

The first fitted surface master targets the provided anatomical reference. This
is a general human-fit prototype, not personalized-fit approval. Tailoring the
approved deformation controls to the recorded wearer measurements is a later
fit pass, followed by physical testing.

Fit, TPU stretch, closure adjustment, wall thickness, and armor clearance are
separate allowances. Do not stack the same margin more than once.

## 5. Source-to-sleeve transformation

The armor-stripped game surface is the production starting point. The
101-solid carrier-free experiment is historical evidence, not topology to
repair into the final sleeve.

The transformation is staged so fit work cannot silently perform manufacturing
work:

1. Preserve the armor-stripped source as immutable evidence.
2. Define reviewed source and anatomical target centerlines, cross-sections,
   and named landmarks.
3. Map the complete source surface through one shared, smooth deformation
   field into a fitted surface candidate.
4. Approve the initial deformation integrity and review its source fidelity and
   digital clearance before changing topology.
5. Classify the accepted fitted surface into recognizable exterior evidence
   and wearer-facing engineering geometry.
6. Remove broad wearer-facing regions that cannot clear the wearer without
   destructive distortion. The game topology does not govern those hidden
   regions.
7. Author a small number of clean wearable panels around the clearance cutter,
   with deliberate donning, flex, and construction seams.
8. Reattach retained exterior forms with local standoffs and structural
   junctions; modestly relocate or trim decorative forms when required for
   clearance.
9. Add controlled thickness, closure hardware, tactical armor panels, and
   hardpoints.
10. Segment, slice, test representative regions, and then print the complete
    wearable assembly.

The canonical fitted surface uses a straight construction pose. This simplifies
radial coordinates, cross-section editing, printer-bed segmentation, and
matched comparisons. The source surface must be transported directly from its
reviewed centerline to that straight target centerline through one shared
mapping; do not bake an intermediate straight mesh and deform it a second time.

The fitted-surface stage may use:

- rigid registration and one overall scale;
- smooth longitudinal reparameterization;
- smooth cross-section scaling at named wearer landmarks;
- one coherent centerline bend;
- bounded monotonic radial-depth compression when the prosthetic layering is
  too deep to accommodate a human arm.

Radial compression must preserve layer order: inner, middle, and outer source
details may move closer together but must never exchange order. All
constituents receive the same spatial field. Per-component, per-sector, or
collision-driven translations are prohibited.

Until the initial fitted surface passes transformation and visual review,
preserve source
vertex/face topology, material assignments, relative registration, and visible
negative space. Do not split components, delete faces, add thickness, Boolean
against the cutter, remesh, or manufacture connectivity during this stage.
After that review, topology preservation is no longer a goal for classified
wearer-facing regions. Preserve the approved exterior and negative spaces,
record the broad replacement mask, and engineer the hidden wearable structure
cleanly rather than attempting to repair every source triangle.

## 6. Main-geometry architecture

The arm is a **source-referenced exterior on an authored wearable structure**.
It is not a repaired game mesh, a sealed anatomical sleeve, or a smooth global
backing.

Valid forms include:

- closed source-derived rails and cables;
- locally thickened visible sheets;
- a small number of clean wearer-facing TPU panels;
- supported open spans;
- intentional armor voids;
- source-authentic overlaps;
- deliberate panel, flex, and donning seams;
- deliberately authored structural junctions.

The final wearable must have a durable load path after printing and assembly.
One Blender object is not proof of connectivity, and separate closed solids may
merge in the slicer or be joined deliberately. Supports never count as a
permanent connection.

Solidification and connectivity are separate operations. Closing every source
sheet does not attach floating details. After the fitted exterior is approved,
discard unusable hidden source sheets, build the wearable panels independently,
and connect retained exterior constituents with bounded structural junctions.

Three coarse panels are the default starting point for a difficult wrapped
region. Add a panel only when a named fit, motion, printing, or assembly
constraint requires it. Automated face clustering must not turn diagnostic
complexity into dozens of production pieces.

The intended result is one continuous worn sleeve assembly. It may contain
multiple deliberately overlapping constituents and will require printer-bed
segments; it need not be one topological Blender component or one print job.

## 7. Clearance cutter rule

The fit volume may be expanded into a clearance cutter and used for:

- bounded Boolean subtraction;
- collision review;
- cross-section inspection;
- validating inward clearance.

It must not:

- become part of the final printed geometry;
- generate the visible exterior;
- be copied wholesale as a continuous hidden sleeve;
- fill source gaps automatically;
- justify a global union or remesh.

During fitted-surface work, a clearance violation triggers a shared-field
adjustment or classification of a broad wearer-facing replacement region. It
must not trigger per-component lifting or an unreviewed global Boolean. During
main-geometry work, the cutter may govern clearance for manually authored local
panels and bounded subtraction, but source topology and cutter triangles must
not be copied into the result.

## 8. Preservation and reconstruction policy

Begin from the clean source surface. Do not spend the current milestone
classifying or repairing the 101 processed solids. They remain recoverable
evidence of a failed transformation approach.

### Keep

Preserve a source-derived form when it:

- retains a recognizable source landmark or line route;
- survives wearer clearance without broad destructive editing;
- can receive controlled local thickness;
- can connect through a small number of mechanically plausible junctions;
- has a credible printing and support strategy.

### Re-engineer underneath

Preserve the visible source surface while replacing its hidden closure,
perimeter, thickness, or attachment geometry. This is the default treatment for
good-looking but poorly manufactured source sheets. When a large hidden region
is unwearable, delete it broadly and replace it with a small number of clean
authored panels. Do not preserve hidden source topology merely because it
exists.

### Reconstruct visibly

Rebuild a visible region only when the existing version is clearly damaged,
missing, flattened, or mechanically unusable. A modest relocation or trim is
also allowed when a cosplay detail otherwise conflicts with the wearer
envelope. Reconstruction must:

- begin from intact source evidence;
- preserve named silhouette, panel, cable, junction, and depth landmarks;
- avoid deriving appearance from the clearance cutter;
- pass an identical-camera comparison against the retained alternative;
- demonstrate a fit or manufacturing benefit before replacing the source-led
  alternative.

## 9. Construction regions

Construction regions organize editing and review; they are not printer-bed
pieces:

1. wrist interface;
2. distal forearm;
3. proximal forearm;
4. distal elbow transition;
5. elbow flex zone;
6. proximal elbow transition;
7. bicep interface.

The current processed solids have provisional centroid assignments, but those
assignments do not govern the new source-derived fitted surface. Regions must
be reassigned using wearer landmarks and recognizable source transitions.

## 10. Elbow

The current fitted-surface milestone is static and straight. It makes no elbow
mobility claim.

Approximately `30°` is the later priority wear pose: the arm must look good
there even if the eventual motion range is narrower than the aspirational
`30–120°` target. Elbow mobility is a separate redesign problem and may use:

- a separate flexible elbow assembly;
- a deliberately open inner-elbow gap;
- independently flexible dorsal cables and rails;
- another bounded solution that preserves the approved static composition.

- No rigid armor, hardpoint, bed weld, or thick continuous cable may bridge the
  flex crease.
- The flex zone and its two transitions are authored engineering geometry.
- A straight construction pose is not an articulation solution.
- Establish elbow behavior before locking surrounding connectivity.

## 11. Armor voids and attachments — deferred contract

Do not fill removed-armor gaps indiscriminately.

Later, each armor void may receive the minimum required combination of:

- a source-led visible rim;
- a thin tactical panel constrained by the clearance cutter;
- discrete reinforced attachment landings;
- local structural junctions.

Major armor is planned around magnet-to-magnet clamping with mechanical
registration and shear restraint. Exact magnet size, count, capture, membrane
thickness, and hardpoint geometry remain coupon-gated. Velcro remains available
for small, curved, lightweight, or highly flexible parts.

Attachment points and tactical panels are explicitly outside the current
main-geometry milestone.

## 12. Closure and segmentation — deferred constraints

The arm requires a concealed medial donning opening. Its closure must eventually
have a deliberate longitudinal load path, an inner pressure-distribution
tongue, and a liftable outer cover.

Exact bed cuts are deferred, but main geometry must leave viable weld corridors,
support access, and no-cut hero regions. Closure seams and bed-cut/weld seams are
different concepts and must remain named separately.

## 13. Prohibited shortcuts

- Global carrier union or global anatomical backing
- Global voxel remesh as exterior construction
- Per-fragment nearest-surface projection
- Destructive baked straightening followed by a second deformation
- Per-component or per-sector collision-driven lifting
- Automatic deletion of intersecting, internal, or small source faces
- Non-monotonic radial remapping that reorders source depth layers
- Solidification or connectivity work before fitted-surface approval
- Material-label-only armor classification
- Datablock joining presented as physical connectivity
- Slicer repair presented as design repair
- Manifold topology presented as visual approval
- Premature tactical panels or hardpoints used to hide unresolved main geometry
