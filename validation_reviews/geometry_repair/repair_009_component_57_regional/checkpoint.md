# Repair 009 component 57 regional validation checkpoint

Mission: `geometry-repair-009-review`

Scope: independently validate only `REPAIR_009_COMPONENT_57_REGIONAL` relative
to `REPAIR_008_COMPONENT_52_REGIONAL`. This review does not promote the fitted
surface and does not modify Blender data or repair implementation.

## Claims under validation

1. The 45 mm regional field does not introduce objectionable visible
   silhouette or registration drift in the intertwined wrist detail.
2. It does not create contact, gap closure, bridge/fusion, spike, slab,
   flattening, depth inversion, altered wrist opening, or propagation into
   neighboring components.
3. Numerical evidence remains consistent with a retainable candidate:
   topology/materials unchanged, zero negative-orientation locators, tolerable
   edge deformation, and improved clearance.
4. `does_this_repair_delta_look_ass` is explicitly answered from bounded
   matched-pair visual evidence.

## Text evidence captured before image handling

- Candidate: `REPAIR_009_COMPONENT_57_REGIONAL`
- Relative key: `REPAIR_008_COMPONENT_52_REGIONAL`
- Component: 57; component vertices: 40
- Initial violating vertices: 12
- Affected regional field: 1,169 vertices; falloff: 45.0 mm
- Translation: 7.250539 mm along
  `[-0.411355, -0.780283, 0.471110]`
- Topology: 7,347 vertices and 12,564 faces before/after; face indices and
  material assignments unchanged
- Clearance: below-cutter vertices 326 -> 309; below-reserved-margin vertices
  338 -> 328; triangle overlaps 769 -> 741; component-57 below-cutter and
  below-margin vertices both end at 0
- Affected-edge ratios: min 0.768105, median 1.000347, p95 1.088616,
  max 1.213738
- Negative-orientation locators: 0
- Manifests declare matching cameras per view.

## Recovery state

State: `SANITIZED_INPUTS_READY`

Image operation completed: copied all manifest-listed local and complete PNGs,
then sanitized each copied derivative in place with
`scripts.image_sanitization.sanitize_image`. ImageMagick reported metadata
stripped, orientation normalized, sRGB, 8-bit, alpha off for every file.

Source/output mappings and sanitized byte sizes:

| source (under `regional_f45_trial/`) | sanitized output (under `sanitized_review/`) | bytes | direct review |
| --- | --- | ---: | --- |
| `local/source--dorsal.png` | `local--source--dorsal.png` | 514110 | true |
| `local/current--dorsal.png` | `local--current--dorsal.png` | 538711 | true |
| `local/source--ventral.png` | `local--source--ventral.png` | 494095 | true |
| `local/current--ventral.png` | `local--current--ventral.png` | 526039 | true |
| `local/source--medial.png` | `local--source--medial.png` | 540971 | true |
| `local/current--medial.png` | `local--current--medial.png` | 577562 | true |
| `local/source--lateral.png` | `local--source--lateral.png` | 565345 | true |
| `local/current--lateral.png` | `local--current--lateral.png` | 608216 | true |
| `local/source--wrist_axial.png` | `local--source--wrist_axial.png` | 534764 | true |
| `local/current--wrist_axial.png` | `local--current--wrist_axial.png` | 555380 | true |
| `complete/source--dorsal.png` | `complete--source--dorsal.png` | 505504 | true |
| `complete/current--dorsal.png` | `complete--current--dorsal.png` | 518554 | true |
| `complete/source--ventral.png` | `complete--source--ventral.png` | 499666 | true |
| `complete/current--ventral.png` | `complete--current--ventral.png` | 515296 | true |
| `complete/source--medial.png` | `complete--source--medial.png` | 476045 | true |
| `complete/current--medial.png` | `complete--current--medial.png` | 489722 | true |
| `complete/source--lateral.png` | `complete--source--lateral.png` | 481608 | true |
| `complete/current--lateral.png` | `complete--current--lateral.png` | 494625 | true |
| `complete/source--dorsal_lateral_three_quarter.png` | `complete--source--dorsal_lateral_three_quarter.png` | 499787 | true |
| `complete/current--dorsal_lateral_three_quarter.png` | `complete--current--dorsal_lateral_three_quarter.png` | 510062 | true |
| `complete/source--ventral_medial_three_quarter.png` | `complete--source--ventral_medial_three_quarter.png` | 483349 | true |
| `complete/current--ventral_medial_three_quarter.png` | `complete--current--ventral_medial_three_quarter.png` | 497900 | true |
| `complete/source--wrist_axial.png` | `complete--source--wrist_axial.png` | 539333 | true |
| `complete/current--wrist_axial.png` | `complete--current--wrist_axial.png` | 568463 | true |
| `complete/source--bicep_axial.png` | `complete--source--bicep_axial.png` | 512632 | true |
| `complete/current--bicep_axial.png` | `complete--current--bicep_axial.png` | 541394 | true |

No sanitized derivative exceeds 10,000,000 bytes.

Next image operation:

- Build five font-free local matched-pair pages, one per view, with ImageMagick
  `+append` in source-left/current-right order.
- Sanitize each generated pair page immediately with
  `scripts.image_sanitization.py`.
- Record page sizes before opening any page.

## Local matched-pair pages

Generated font-free, source-left/current-right local pages were sanitized
immediately:

| page | bytes | direct review |
| --- | ---: | --- |
| `pair--local--dorsal.png` | 1009216 | true |
| `pair--local--ventral.png` | 971478 | true |
| `pair--local--medial.png` | 1062145 | true |
| `pair--local--lateral.png` | 1119699 | true |
| `pair--local--wrist_axial.png` | 1094083 | true |

All are below 10,000,000 bytes.

Current state: `READY_TO_INSPECT_LOCAL_DORSAL`

Next image operation:

- Inspect `pair--local--dorsal.png` at high detail. It is a bounded matched
  pair with Repair 008 on the left and Repair 009 on the right.

### Local dorsal observation

High-detail inspection completed. The repair produces a visible, smooth shift
of the lower intertwined wrist strip and nearby lower edges, consistent with a
regional translation rather than a spike or isolated pull. The principal
vertical plates retain their faceted silhouette and their narrow separations.
No new bridge/fusion, closed gap, slab, depth inversion, or obvious propagation
into the neighboring tall plates is visible. The lower opening remains present.
The shifted strip does not visibly intersect the adjacent plate.

Current state: `READY_TO_INSPECT_LOCAL_VENTRAL`

Next image operation:

- Inspect `pair--local--ventral.png` at high detail, Repair 008 left and Repair
  009 right.

### Local ventral observation

High-detail inspection completed. The broad negative-space channel beneath the
upper plate remains open after the repair. The thin horizontal wrist element
keeps a coherent thickness and remains visually separate from the larger lower
plate; its end and the small intertwined detail remain recognizable. No new
contact, bridge/fusion, spike, flattened slab, or inversion is apparent. The
lower silhouette changes smoothly over a broad area without a hard falloff
boundary.

Current state: `READY_TO_INSPECT_LOCAL_MEDIAL`

Next image operation:

- Inspect `pair--local--medial.png` at high detail, Repair 008 left and Repair
  009 right.

### Local medial observation

High-detail inspection completed. The layered, intertwined wrist strips remain
separate and preserve their ordering. The repaired broad strip remains faceted
and follows the same overall arc; adjacent narrow elements do not collapse into
it. The central and lower negative spaces remain legible. No spike, abrupt
crease at the falloff boundary, slab-like flattening, new bridge, or depth-order
inversion is visible.

Current state: `READY_TO_INSPECT_LOCAL_LATERAL`

Next image operation:

- Inspect `pair--local--lateral.png` at high detail, Repair 008 left and Repair
  009 right.

### Local lateral observation

High-detail inspection completed. The long overlapping plates preserve their
parallel visual rhythm and open seams. Their outer silhouettes remain clean and
faceted, without a new spike, kink, or broadened slab. The regional delta is
not evident as an abrupt boundary in this view, and no neighboring plate appears
dragged into contact or fused.

Current state: `READY_TO_INSPECT_LOCAL_WRIST_AXIAL`

Next image operation:

- Inspect `pair--local--wrist_axial.png` at high detail, Repair 008 left and
  Repair 009 right.

### Local wrist-axial observation

High-detail inspection completed. The wrist opening remains open and retains
its angular, layered perimeter. The intertwined dark bands preserve their
separate paths and depth ordering; no band becomes a fused bridge across the
opening. The opening shifts slightly with the regional field but does not
collapse, invert, or become visibly malformed. No needle spike or isolated
vertex pull is visible.

Local matched-pair evidence therefore shows a coherent regional movement, not a
destructive local deformation. A complete-view check is still required for
silhouette and propagation.

Current state: `READY_TO_BUILD_COMPLETE_PAIRS`

Next image operation:

- Build font-free source-left/current-right complete matched pairs for dorsal,
  ventral, dorsal-lateral three-quarter, ventral-medial three-quarter, and
  bicep-axial views with ImageMagick `+append`.
- Sanitize every generated page immediately and record sizes before inspection.

### Complete matched-pair pages

Generated pages were sanitized immediately:

| page | bytes | direct review |
| --- | ---: | --- |
| `pair--complete--dorsal.png` | 754881 | true |
| `pair--complete--ventral.png` | 745514 | true |
| `pair--complete--dorsal_lateral_three_quarter.png` | 712397 | true |
| `pair--complete--ventral_medial_three_quarter.png` | 688051 | true |
| `pair--complete--bicep_axial.png` | 805451 | true |

All are below 10,000,000 bytes.

Current state: `READY_TO_INSPECT_COMPLETE_DORSAL`

Next image operation:

- Inspect `pair--complete--dorsal.png` at high detail, Repair 008 left and
  Repair 009 right.

### Complete dorsal observation

High-detail inspection completed. Overall arm silhouette, wrist opening,
forearm/body registration, and the major negative spaces are visually
unchanged. No visible displacement propagates into the upper arm or distal
forearm, and no new bridge or slab appears at full-model scale.

Current state: `READY_TO_INSPECT_COMPLETE_VENTRAL`

Next image operation:

- Inspect `pair--complete--ventral.png` at high detail, Repair 008 left and
  Repair 009 right.

### Complete ventral observation

High-detail inspection completed. The ventral silhouette, circular wrist
detail, cage-like negative spaces, and forearm separation remain visually
stable. The regional adjustment is not visible as an objectionable global
registration shift, and there is no new connection to neighboring components.

Current state: `READY_TO_INSPECT_COMPLETE_DORSAL_LATERAL_3Q`

Next image operation:

- Inspect `pair--complete--dorsal_lateral_three_quarter.png` at high detail,
  Repair 008 left and Repair 009 right.

### Complete dorsal-lateral three-quarter observation

High-detail inspection completed. The wrist assembly retains its layered
composition, floating parts, and open structural gaps. The full-arm silhouette
and the separation between major constituents remain stable. No new fusion,
spike, or visible propagation appears in this oblique view.

Current state: `READY_TO_INSPECT_COMPLETE_VENTRAL_MEDIAL_3Q`

Next image operation:

- Inspect `pair--complete--ventral_medial_three_quarter.png` at high detail,
  Repair 008 left and Repair 009 right.

### Complete ventral-medial three-quarter observation

High-detail inspection completed. Open channels through the wrist and forearm
remain present; neighboring plates retain their spacing and recognizable
silhouettes. The repair does not read as a slab, an indiscriminate backing
surface, or a registration shift across the assembly.

Current state: `READY_TO_INSPECT_COMPLETE_BICEP_AXIAL`

Next image operation:

- Inspect `pair--complete--bicep_axial.png` at high detail, Repair 008 left and
  Repair 009 right, specifically to check distal propagation.

### Complete bicep-axial observation

High-detail inspection completed. The distant upper-arm perimeter, broad
central facets, layered constituents, loops, and openings are visually
equivalent. No component-57 repair effect propagates into this distal region.

## Final classification

State: `COMPLETE`

- Scenario result: `pass`
- Candidate disposition: `retain_candidate`
- Fitted-surface promotion: `false`
- `does_this_repair_delta_look_ass`: `false`
- Qualitative delta: `pass`
- Anatomical clearance: `fail` (309 cutter penetrations, 328 reserved-margin
  violations, and 741 triangle overlaps remain globally)

Reason: the visible delta is a coherent regional motion of the component-57
wrist detail. The wrist opening, intertwined strips, intentional negative
spaces, neighboring-component registration, and full-arm silhouette remain
credible across five tight local pairs and five complete orthogonal/oblique/
distal pairs. This visual result is consistent with unchanged topology and
materials, zero negative-orientation locators, a near-unity median edge ratio,
and improved component/global clearance. The edge extremes remain a later
physical-detail watch item, not a visible retain/reject failure.

Durable result: `review.json`
