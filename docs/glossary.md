# Silverhand — Project Glossary

This glossary gives project terms one durable meaning. A tool, object name, or
conversation must not silently promote an artifact beyond these definitions.
See the [documentation index](README.md) for the other project authorities.

## Authority and result language

### Approval

A human decision that an artifact satisfies a named qualitative or physical
requirement. Scripts do not grant visual, ergonomic, structural, or production
approval.

### DONE

A tool completed its stated operation and produced its output. `DONE` says
nothing about whether the resulting evidence is favorable.

### Evidence

Recorded information used to make a decision: geometry measurements, images,
graphs, manifests, slicer layers, or physical results. Evidence is not approval.

### Failure

A named operation or gate did not satisfy its explicit requirements. A failure
must identify the operation, target, and actionable reason.

### PASS

A named gate or audit satisfied all of its explicit machine-checkable
requirements. Always name the gate: for example, “Scene integrity PASS” or
“STL topology audit PASS.” A pass does not imply general design quality.

### Qualitative review

A human or agent assessment of appearance, coherence, source fidelity, and
design character using stable evidence such as matched-view renders. It may use
a rubric, but it must not manufacture pseudo-objective visual scores.

### Valid

Acceptable against a specifically named test. Avoid unqualified statements such
as “the model is valid.”

## Artifact statuses

These are the only promotion statuses used by the project.

### Source evidence

Immutable comparison input. It can govern a named property but is not editable
production geometry.

### Visual baseline

Recognizable comparison geometry. It may be fragmented, unwearable, or
unmanufacturable.

### Fitted surface candidate

An armor-stripped source duplicate mapped toward wearer dimensions through one
shared deformation field. It remains a zero-thickness or mixed-topology review
surface and has not passed visual or clearance approval.

### Fitted surface master

A fitted surface candidate that passed transformation-integrity,
matched-source visual, and digital-clearance review. It governs the exterior
used for later hidden solidification. It is not yet printable geometry or
physical fit authority.

### Wearable panel candidate

A clean, deliberately authored wearer-facing panel built beneath the approved
exterior. It is governed by fit, seam, thickness, and attachment requirements,
not by hidden game-mesh topology. It has not yet passed complete assembly or
physical review.

### Editable main geometry

Working solids derived beneath an approved fitted surface master. They are
being thickened, connected, or locally reconstructed and do not yet form one
durable wearable network.

### Connected master

Main geometry with an intentional, documented permanent load network. Blender
object joining or incidental overlap alone does not establish this status.

### Print candidate

An explicit export that passed its named digital and slicer gates. It has not
necessarily passed physical testing.

### Physical-test candidate

A print candidate tied to a stated physical experiment and success criteria.

### Production export

A bed-ready artifact whose relevant digital, slicer, and physical claims have
all been validated.

## Scene roles

### Immutable source

An object preserved for comparison. `SRC_GAME_RAW` and `SRC_GAME_FITTED` are
immutable source evidence.

### Working solid

An editable closed constituent derived during solid construction. A working
solid may still be discarded or rebuilt. The removed
`20_SALVAGE_WORKING` collection was rejected experimental evidence and remains
recoverable at the `pre-repo-cleanup-20260730` Git tag.

### Evaluation object

A disposable review aggregation named `EVAL_*`. It can simplify rendering and
measurement but must not be edited or exported as production geometry.

### Fit reference

The named volume governing a fit pass. The first fitted surface uses the
provided anatomical reference; a later personalized fit reference uses wearer
measurements. The two claims must not be conflated.

### Clearance cutter

A non-printable expanded fit volume used for subtraction, collision evidence,
and cross-sections. It never supplies visible exterior or global backing
geometry.

### Armor source

Game or proven-print evidence for a removable rigid plate. It is not
automatically registered, attached, or print-ready.

### Validation camera

A review camera in `90_VALIDATION_CAMERAS`. It is evidence infrastructure, not
printable geometry.

## Geometry and architecture

### Carrier

A broad backing surface used to support or connect visible forms. A global
visible or hidden carrier is prohibited for the current architecture.

### Carrier-free

An architecture that preserves source forms and negative space without a
continuous backing sleeve. It may still use local structural junctions.

### Constituent

One closed solid participating in a printable artifact. Multiple constituents
may intentionally overlap, but their relationship must be declared.

### Connected component

A topologically connected set of mesh vertices and edges. It is a geometry
fact, not proof of mechanical connection after printing.

### Contact edge

An edge in the generated contact graph showing that two closed constituents
intersect or contain one another. It is not a load-path or slicer-fusion
approval.

### Contact group

A maximal set of constituents connected through contact edges.

### Isolated solid

A constituent with no contact edge to another current working solid. It must
eventually be attached, separately assembled, or explicitly discarded.

### Boundary edge

A mesh edge incident to only one face. Intended printable closed solids must
have none.

### Non-manifold edge

A mesh edge whose face incidence is not exactly two. Intended printable closed
solids must have none.

### Positive signed volume

A closed shell with consistently outward orientation according to the volume
calculation. It proves orientation, not appearance or printability.

### Negative space

An intentional gap, channel, opening, or separation contributing to source
composition and mechanical character. It must not be filled merely to simplify
union or connectivity.

### Visible source surface

The source-facing geometry that governs appearance and must be compared before
replacement.

### Hidden closure surface

Manufacturing geometry that closes or thickens a visible source form on its
wearer-facing or concealed side.

### Authored wearable panel

A coarse wearer-facing TPU constituent designed from the named fit reference
and connected to retained exterior forms through local junctions. It is not a
copy of fit/cutter triangles or a patch-by-patch repair of hidden source
topology. The cutter tests clearance; it does not generate the panel surface.

### Decorative exterior

Source-referenced visible geometry retained for silhouette and mechanical
character. It may be modestly relocated, trimmed, thickened, or locally
reattached when exact coordinates conflict with wearability.

### Engineering seam

A deliberate gap or junction between authored wearable panels. It exists for
fit, flex, donning, printing, or assembly and is distinct from accidental
cracks created by failed reconstruction.

### Local structural junction

A bounded, deliberately authored connection between nearby constituents. It
must preserve intentional negative space and serve a plausible load path.

### Tactical panel

A later, local panel used only where an armor void actually requires coverage,
registration, or attachment support. It is not a global backing.

### Armor void

Space left by removable rigid armor. An armor void is not automatically a hole
that should be filled.

### Hardpoint

A reinforced local attachment feature for a magnet or other hardware. Exact
hardpoint geometry remains physical-coupon gated.

### Closure seam

The wearer opening used to don and remove the arm.

### Bed-cut or weld seam

A manufacturing split introduced to fit the printer and reassemble the part.
It is distinct from the closure seam.

### Segmentation

Dividing approved geometry into printer-bed pieces. Construction regions are
not segmentation pieces.

## Fit, motion, and measurement

### Source centerline

The reviewed longitudinal path used to describe station, cross-section, and
depth coordinates in the armor-stripped game arm. It must follow the source
composition rather than assume that the prosthetic is straight.

### Target centerline

The fit-reference-led longitudinal path to which the source is transported. The
first target is straight and anatomically derived; later variants may encode a
wear pose or personalized landmarks.

### Straight construction pose

The canonical static pose of the first fitted surface: one straight target
centerline used for radial fitting, review, and later segmentation planning. It
is actual candidate geometry but makes no elbow-mobility claim.

### Priority wear pose

The approximately `30°` elbow bend at which the later wearable elbow must look
best. It is a future appearance and motion target, not part of the current
static fitted-surface gate.

### Straight coordinate representation

A reversible mathematical representation of source points by station, angle,
and depth around a centerline. It is not a separately approved mesh and must not
be baked and deformed again as an additional modeling stage.

### Shared deformation field

One continuous spatial mapping applied to the complete source surface. It may
bend the centerline, reparameterize length, scale cross-sections, and compress
depth, but it must not move constituents independently.

### Regional fit-field correction

A bounded refinement of the shared deformation field applied to every vertex
within one spatial region. It may preserve a deep source landmark while
blending its motion into neighboring geometry. It is not an independent
component lift and requires matched regional review.

### Radial depth stack

The ordered inner-to-outer layering of cybernetic source details around a
centerline. Preserving the stack means retaining both its order and its
recognizable relative relief.

### Monotonic radial-depth compression

A shared mapping that reduces excessive prosthetic depth while preserving the
inner-to-outer order of every affected source layer. It may flatten relief but
must not invert or reorder it.

### Profile ring

One ordered cross-section of the fit or cutter mesh. The inherited baseline has
77 rings. A ring index is not an anatomical landmark.

### Station

A position along the fit centerline. A station becomes a wearer landmark only
after explicit mapping.

### Wearer landmark

A named anatomical or measurement position such as wrist, widest forearm, an
elbow transition, or bicep. It is supplied by wearer evidence, not inferred
from a convenient mesh index.

### Anatomical digital fit

Clearance against the provided anatomical reference. It is the target of the
first fitted surface and does not approve fit for the specific wearer.

### Personalized fit

A later deformation pass tailored to the recorded wearer measurements and
ultimately judged by a physical fit test.

### Clearance margin

The intended separation between wearer fit and printable geometry. Fit,
material stretch, wall thickness, and armor allowance are separate quantities.

### Clearance violation

A geometric intersection with, or penetration into, the named clearance
cutter. It is a collision fact, not proof that a collision-free design is
comfortable.

### Cross-section evidence

The intersection of named geometry with a named plane. It supports review but
does not approve fit or select a production cut.

### Thickness estimate

An advisory ray or line-intersection measurement on a constituent. It can flag
suspicious regions but does not establish print viability without a physical
process minimum.

### Elbow flex zone

The region intended to accommodate bending. No rigid armor, hardpoint, weld, or
thick continuous cable may bridge it.

### Elbow transition

One of the regions connecting the flex zone to forearm or bicep geometry. Both
must be reviewed for collision, pinch, and buckling.

## Review and reconstruction

### Source fidelity

Preservation of recognizable silhouette, mass distribution, landmarks, layered
relationships, and negative space from the game source. It is a qualitative
judgment supported by matched views.

### Mechanical character

The believable arrangement of rails, cables, recesses, overlaps, junctions, and
voids that makes the arm read as the intended cybernetic design. Terms such as
“cyberpunk” describe this qualitative character; they are not code metrics.

### Contact sheet

A stable set of matched source/current views. The active review form is a
paginated packet listed under `render.contact_sheets`; each page is bounded for
safe image-model inspection. A full vertical sheet is human archival evidence
only. Neither form performs the qualitative review.

### Geometry fingerprint

A hash of named geometry and transforms used to tie evidence to an exact
checkpoint. Matching fingerprints show identity, not quality.

### Keep

Retain a source-derived form substantially as visible material.

### Re-engineer underneath

Preserve the approved visible surface while replacing hidden closure,
thickness, perimeter, or attachment geometry.

### Reconstruct

Replace visible geometry because it is missing, damaged, flattened, or
mechanically unusable. The replacement must pass matched-view comparison and
demonstrate a manufacturing benefit.

### Historical transformation evidence

A rejected processed artifact retained to explain failure modes or compare
metrics. The current 101-solid carrier-free baseline has this role; it is not a
production starting point or salvage obligation.

### Discard

Explicitly remove a form after review establishes that it is noise, invalid
classification, unrecoverable damage, or unnecessary detail.

### `does_this_look_ass`

The deliberately plain-language final qualitative check. `false` must be
entered by a reviewer; geometry code cannot calculate it.

## Manufacturing

### Component policy

The export declaration describing whether an STL must be one connected solid or
may contain intentional overlapping solids.

### Bed policy

The export declaration describing whether an artifact must fit the
`180 × 180 × 180 mm` bed or is explicitly unsegmented evidence.

### Reimport check

Reading an exported file back as geometry evidence and comparing dimensions to
the evaluated Blender source at STL scale `1.0`.

### Slicer fusion

Layer evidence that intentional overlapping solids produce continuous printed
material. Geometric overlap alone does not prove it.

### Support

Temporary print material that makes fabrication possible. Support never counts
as a permanent structural connection.
