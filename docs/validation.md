# Silverhand — Validation Contract

Validation is a sequence of promotion gates. Passing a later mechanical check
does not excuse a failed source-comparison or clearance gate.

## Artifact statuses

Use only these status meanings:

- **source evidence** — immutable comparison input;
- **visual baseline** — recognizable geometry, not necessarily manufacturable;
- **fitted surface candidate** — topology-preserving source deformation under review;
- **fitted surface master** — visually approved, digitally clear surface authority for solid construction;
- **wearable panel candidate** — clean authored wearer-facing structure under an approved exterior;
- **editable main geometry** — regional working solids;
- **connected master** — one durable assembled load network;
- **print candidate** — explicit export that passes digital and slicer review;
- **physical-test candidate** — print candidate tied to a stated experiment;
- **production export** — physically validated and bed-ready.

Do not use “complete,” “approved,” or “print-ready” without naming the passed
status and evidence.

## Gate A — Scene integrity

- Metric units, `scale_length = 0.001`, millimeters.
- Required source, fit, fitted-surface, engineering-prototype, deferred-armor,
  and validation-camera collections exist.
- `SRC_GAME_RAW` and `SRC_GAME_FITTED` are preserved.
- No missing external files.
- No accidental shared editable mesh data.
- No cameras, exports, `EVAL_*`, `REG_*`, or retired salvage collections
  masquerade as active geometry.
- Current object names agree with [status.md](status.md).

Failure blocks all later gates.

## Gate B — Fitted-surface transformation integrity

Before reconstruction, compare the initial fitted surface candidate to its
exact source input and confirm:

- vertex, face, loop, material-slot, and material-assignment counts are
  unchanged;
- no source face was deleted or split;
- no thickness, Boolean, remesh, or connectivity geometry was introduced;
- all vertices were mapped through one documented shared deformation field;
- no constituent received an independent transform or collision-driven lift;
- longitudinal mapping and cross-section scaling remain smooth;
- radial-depth mapping is monotonic and preserves layer order;
- displacement, edge-stretch, triangle-orientation, and local distortion
  evidence is recorded for review.

A mathematically straight coordinate representation is allowed. A separately
baked straight mesh followed by another deformation is not.

Failure blocks exterior approval; adjust the shared field and repeat this gate.
After the exterior is approved, classified wearer-facing replacement regions
leave Gate B topology authority. Record their broad masks, preserve Gate B
invariants everywhere else, and validate authored panels under Gates C–G.

## Gate C — Fitted-surface visual review

Review the actual fitted surface candidate against immutable source evidence:

- dorsal;
- ventral;
- medial;
- lateral;
- dorsal-lateral three-quarter;
- ventral-medial three-quarter;
- wrist axial;
- bicep axial;
- region close-ups.

Confirm:

- recognizable silhouette and mass distribution;
- major rails, cables, recesses, junctions, and negative spaces survive;
- rigid armor is absent from the TPU-only review;
- no generic carrier surface fills source structure;
- no unexplained slab, spike, melted form, or implausible angle;
- no exploded component, lost registration, or unexpected depth-layer
  inversion;
- any visible reconstruction is demonstrably better than the source-led
  alternative.

The reviewer must explicitly answer `does_this_look_ass: false`. Geometry checks
cannot manufacture this answer.

Generate the standard comparison with:

```sh
./scripts/tools/render_geometry_comparison.sh
```

The command produces a two-page review packet with four semantic views per
page. Image-model review must use the files listed in
`render.contact_sheets` at high detail, or individual matched-view images.
Full vertical contact sheets are optional human archival evidence and must not
be inspected directly by an image model.

The canonical cameras live in `90_VALIDATION_CAMERAS`. Source and current
geometry use the exact same orthographic camera transform and framing for each
view. Regenerate or repair the rig with:

```sh
./scripts/tools/sync_validation_cameras.sh
```

Validation cameras are review infrastructure, never printable geometry.

## Gate D — Fit and clearance

- Use one named anatomical fit reference for the first fitted surface.
- Use one named expanded clearance cutter.
- Inspect wrist, mid-forearm, widest forearm, both elbow transitions, and bicep
  cross-sections.
- Account for intended hidden wall thickness without counting the same
  allowance twice.
- Record intentional snug regions.
- Resolve fitted-surface violations through shared-field adjustment or bounded
  authored panel reconstruction; do not lift constituents automatically.
- For every retained boundary and authored panel, verify clearance at vertices,
  continuously sampled boundary edges, and adaptive triangle-interior samples.
  Clear endpoints do not establish a clear segment or surface.
- A failed directional exit is a failed preflight. Do not substitute an
  arbitrary displacement sentinel and continue geometry scoring.
- Record that this gate establishes anatomical digital fit, not personalized or
  physical fit.
- Tailor to wearer measurements only after the anatomical fitted surface is
  approved.

The clearance cutter is never printable geometry.

For a broad wearer-facing replacement, Gate D evaluates the complete authored
panel assembly, not the deleted source patch and not a diagnostic face
partition. The panel count must be justified by fit, motion, printing, or
assembly needs.

Current evidence tools:

```sh
./scripts/tools/analyze_fit_profile.sh
./scripts/tools/analyze_clearance.sh
./scripts/tools/analyze_cross_section.sh STATION_INDEX OBJECT...
```

The inherited ring indices are deliberately unlabelled. Do not call a station
wrist, widest forearm, elbow transition, or bicep until wearer landmarks make
that mapping explicit.

## Gate E — Elbow and motion architecture

- This gate is deferred during the static fitted-surface milestone; promotion
  through Gate D grants no motion claim.
- Use approximately `30°` as the priority appearance pose when elbow work
  begins.
- No rigid armor, hardpoint, weld, or thick cable crosses the flex crease.
- Review approximately `30–120°` motion.
- Inspect both transition zones for buckling, pinch points, and collisions.
- Establish the flex architecture before locking surrounding solidification and
  connectivity.
- Digital motion is investigative; physical TPU is authoritative.

## Gate F — Solid construction

For every intended printable solid:

- positive signed volume;
- zero boundary edges;
- zero non-manifold edges;
- controlled local thickness;
- no accidental inward protrusion;
- no unexplained tiny components;
- source-facing and hidden closure surfaces have consistent roles.

An evaluated joined mesh must not hide invalid constituent solids.

Current evidence tools:

```sh
./scripts/tools/analyze_connectivity.sh
./scripts/tools/analyze_thickness.sh
```

Thickness results remain advisory until physical process coupons establish a
minimum.

## Gate G — Connectivity and loads

- Every retained final detail has a documented permanent connection.
- Supports do not count.
- Slicer overlap counts only when layer inspection demonstrates fusion.
- Structural junctions preserve intentional negative space.
- Closure, armor, and weld loads follow deliberate paths.
- Isolated decorative forms are either attached, separately assembled, or
  discarded explicitly.

Generate geometric contact evidence with:

```sh
./scripts/tools/analyze_connectivity.sh
```

Its graph is not a structural or slicer-fusion approval.

## Gate H — Export and slicer

Validate only an explicit current-export manifest or `exports/current/`.

Every STL must report:

- intended connected-component policy;
- positive orientation;
- zero non-manifold edges;
- zero degenerate triangles;
- dimensions in millimeters;
- `≤ 180 mm` on every bed axis unless explicitly labeled unsegmented evidence;
- reimported dimensions matching the Blender source at scale `1.0`.

Slicer review must confirm:

- orientation;
- supports and supported spans;
- fusion of intentional overlaps;
- viable weld surfaces;
- no accidental floating islands;
- magnet or hardware pauses only when that milestone includes them.

Exports are manifest-driven:

```sh
./scripts/tools/export_from_manifest.sh MANIFEST OUTPUT_DIR
```

The exporter ignores selection, blocks source/review/cutter objects, writes at
scale `1.0`, runs the STL audit, and verifies reimported dimensions.

## Gate I — Physical authority

Physical tests decide:

- minimum detail and wall survival;
- fit and comfort;
- TPU flex and fatigue;
- closure and weld strength;
- structural-junction durability;
- armor hardpoint peel, shear, and removal cycles;
- final segmented assembly behavior.

A digital pass cannot promote claims that depend on material behavior.

## Evidence record

Each review JSON must include:

- target role and exact object/export name;
- exact source object and source topology counts;
- shared deformation method and parameters;
- any bounded reconstruction masks and reasons;
- geometry fingerprint;
- milestone status;
- date;
- units;
- source comparison completed;
- views examined;
- geometry results;
- qualitative assessment;
- `does_this_look_ass`;
- unresolved failures;
- exact worst clearance witness: panel/object, face or triangle, sample type,
  coordinate, cutter triangle, and measured margin;
- physical test status;
- next gate.

Generated views may be regenerated. Keep the JSON record and the useful review
packet pages per milestone in Git unless a detailed view has unique review
value. A full archival sheet is optional and does not replace the paginated
review packet.
