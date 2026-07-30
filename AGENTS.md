# Silverhand project instructions

Silverhand is a Blender-based cyberarm cosplay build intended for additive
manufacturing.

Read these files before changing the model:

1. `docs/design.md` — accepted, durable design contract.
2. `docs/status.md` — current scene authority, defects, and immediate milestone.
3. `docs/validation.md` — reusable promotion gates.
4. `docs/glossary.md` — authoritative project terminology and result language.
5. `docs/history.md` — rejected approaches and lessons that must not be repeated.

## Units

- Blender and all project scripts use millimeters.
- Scene convention: `1 Blender unit = 1 mm` and `scale_length = 0.001`.
- STL exports use scale `1.0`; never apply a centimeters-to-millimeters export
  multiplier.
- The A1 mini build volume is `180 × 180 × 180 mm`.

## Source and scene safety

- `reference/Johnny.blend` is the tracked master scene and contains the current
  fitted candidate plus retained engineering prototypes.
- `reference/johnny_silverhand_arm_scaled_up.3mf` is print-proven scale and
  armor-shape evidence, not anatomical registration.
- Preserve `SRC_GAME_RAW` and `SRC_GAME_FITTED` as immutable source evidence.
- Do not edit or export `EVAL_*` review objects as production geometry.
- Do not delete `WORK_FITTED_SURFACE_CANDIDATE` or
  `PROTOTYPE_V28_WEARABLE_PANEL_*` without a verified checkpoint.
- Local scenes, generated evidence, and temporary exports belong under
  `.work/`, which is intentionally ignored.
- Keep one self-contained directory per active run. Do not scatter one
  experiment across parallel repository trees.

## Image evidence safety

- Image tooling is extremely fragile. All image generation, conversion,
  inspection, and comparison must be delegated to a subagent. A parent agent
  must never read an image directly.
- Treat every image subagent as disposable: it may terminate at any image
  operation, without returning a useful result. The parent agent must be able
  to resume by starting a fresh subagent, even if this must be repeated hundreds
  or thousands of times.
- Image subagents must immediately write every useful observation, command,
  output path, and decision to a durable text checkpoint. Do not defer
  documentation until a batch or review is complete. The parent agent must
  coordinate from those checkpoints rather than from image contents.
- Sanitize every generated image with ImageMagick before it enters any
  downstream image workflow. Produce a deliberately plain derivative: strip
  metadata and profiles, normalize orientation, convert to sRGB, and write a
  conventional 8-bit PNG or JPEG. Record the source and sanitized output paths
  in the checkpoint. An image subagent may read only the sanitized derivative.
- Check the sanitized file size before attempting image-model review. Never
  submit an image larger than 10 MB to an image model. Oversized images may
  still be generated and retained for human review, but must be marked
  `direct_image_model_review: false`; create smaller sanitized derivatives for
  model review.
- Never inspect a full or archival contact sheet directly with an image model.
- Use the paginated files listed in `render.contact_sheets` or inspect
  individual matched-view images.
- Always inspect images at high detail first. Use original detail only when the
  high-detail version of that specific image or crop is not clear enough.
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
- Keep rejected experiments in Git history or a deliberate external archive,
  not in the active master scene or active script tree.
- Errors must name the failed operation, target object/file, and actionable
  reason.
- Use `DONE` for successful tool execution. Reserve `PASS` for a named
  validation gate or audit.
