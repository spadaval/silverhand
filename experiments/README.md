# Experiment notebook

This directory is the lightweight human record of modeling experiments.
An experiment note explains what we tried, what we saw, and what we learned.
It is not a validation form or a release record.

## Storage convention

Use one short descriptive name across three locations:

```text
experiments/<name>/README.md
_validation/experiments/<name>/
blender_files/checkpoints/<name>.blend
```

- `experiments/<name>/README.md` is the tracked qualitative notebook entry.
- `_validation/experiments/<name>/` contains reproducible renders, a portable
  evaluated-mesh export, and any generated reports.
- `blender_files/checkpoints/<name>.blend` preserves the exact local scene.

The shared name connects the three locations. Names may be nested when that is
useful, such as `geometry_repair/component_16_ribbon`, but no fixed taxonomy,
sequence number, or date prefix is required.

The `.blend` file remains authoritative. A portable PLY or OBJ is convenient
evidence, not a substitute for shape keys, modifiers, materials, metadata, or
scene structure. Open fitted-surface experiments must not be mislabeled as STL
print candidates.

## Notebook entry

Markdown is the experiment record. Use whichever headings help explain the
work. A useful starting point is:

```markdown
# Experiment title

## Goal

What are we trying to learn or improve?

## Approach

What did we change, and why?

## Observations

What looks better? What broke? What remains uncertain?

## Conclusion

Keep, reject, revisit, or skip for now—and why?

## Next

What should the next experiment try?

## Evidence

- Scene checkpoint
- Review sheets
- Portable model
- Useful generated reports
```

These headings are prompts, not required fields. Combine, rename, or remove
them when another structure communicates the experiment better.

Quantitative tools may continue to emit JSON manifests and reports under
`_validation/`. Those files are machine evidence and implementation details;
they are not the qualitative experiment record.

## Checkpoint procedure

Checkpoint when a change is risky, when a result is worth comparing, or before
switching to another method. Do not checkpoint every trivial edit.

1. Save the current working `.blend`.
2. Choose a short descriptive experiment name.
3. Copy the saved scene to `blender_files/checkpoints/<name>.blend`.
4. Render the standard matched comparison into
   `_validation/experiments/<name>/comparison/`.
5. Export the evaluated target mesh to
   `_validation/experiments/<name>/model/` as non-production evidence.
6. Record the goal, observations, conclusion, and useful evidence links in
   `experiments/<name>/README.md`.
7. Inspect only the paginated review sheets at high detail first. Use original
   detail only when a particular sheet or crop is unclear.

The planned `scripts/tools/checkpoint_experiment.sh` helper should perform
steps 3–5 and create a starter README only when one does not already exist. Its
normal interface should require only an experiment name and working blend:

```sh
./scripts/tools/checkpoint_experiment.sh \
  geometry_repair/component_16_ribbon \
  blender_files/Johnny_geometry_repair_work.blend
```

Optional source and target object arguments are appropriate when the defaults
do not describe the experiment. The helper must not overwrite an existing
notebook entry, manufacture qualitative approval, or promote an artifact.

## After the experiment

Most experiments need no further process. Keep the note concise and move on.

When an experiment establishes a durable method boundary or project decision,
summarize that result in the appropriate durable document:

- `docs/status.md` for current authority and immediate work;
- `docs/history.md` for rejected methods and retained lessons;
- `docs/approaches/` for a method with enough evidence to guide later work;
- `validation_reviews/` only when an actual named validation gate or milestone
  needs a retained review record.
