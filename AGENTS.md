# Silverhand project instructions

Silverhand is a Blender-based cyberarm cosplay build intended for additive
manufacturing.

Read these files before changing the model:

1. `docs/design.md` — accepted, durable design contract.
2. `docs/status.md` — current scene authority, defects, and immediate milestone.
3. `docs/validation.md` — reusable promotion gates.
4. `docs/glossary.md` — authoritative project terminology and result language.
5. `docs/history.md` — rejected approaches and lessons that must not be repeated.
6. Relevant records under `docs/approaches/` — evidence-backed method bounds.

## Units

- Blender and all project scripts use millimeters.
- Scene convention: `1 Blender unit = 1 mm` and `scale_length = 0.001`.
- STL exports use scale `1.0`; never apply a centimeters-to-millimeters export
  multiplier.
- The A1 mini build volume is `180 × 180 × 180 mm`.

## Source and scene safety

- `reference/Johnny.blend` is the tracked master scene.
- `reference/johnny_silverhand_arm_scaled_up.3mf` is print-proven scale and
  armor-shape evidence, not anatomical registration.
- Preserve `SRC_GAME_RAW` and `SRC_GAME_FITTED` as immutable source evidence.
- Do not edit or export `EVAL_*` review objects as production geometry.
- Do not delete current salvage geometry without a verified checkpoint.
- Local `.blend` experiments and archives belong under `blender_files/`, which
  is intentionally ignored.

## Image evidence safety

- Never inspect a full or archival contact sheet directly with an image model.
- Use the paginated files listed in `render.contact_sheets` or inspect
  individual matched-view images.
- Use high image detail for review sheets. Reserve original detail for a small,
  explicit crop when exact pixels are necessary.
- A full vertical contact sheet may be generated only as human archival
  evidence and must remain marked `direct_image_model_review: false`.

## Geometry rules

- The game model governs visible composition.
- The fit reference governs wearer dimensions.
- The clearance cutter is used only for subtraction and collision checks. It
  must never generate or supply a global visible carrier.
- Preserve intentional negative space.
- Every printable constituent must be a closed, consistently oriented,
  positive-volume solid.
- Supports make printing possible; they do not create permanent connections.
- Use local structural junctions, not an indiscriminate backing union.
- Main geometry comes before tactical armor panels, hardpoints, closure detail,
  and printer-bed segmentation.

## Repository rules

- Git LFS is required for the tracked master `.blend`.
- Do not force-add other `.blend` files.
- Keep rejected experiments in Git history or local archives, not in the active
  master scene.
- Errors must name the failed operation, target object/file, and actionable
  reason.
- Use `DONE` for successful tool execution. Reserve `PASS` for a named
  validation gate or audit.
