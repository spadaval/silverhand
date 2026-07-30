# Silverhand Cyberarm

A wearable Johnny Silverhand-inspired cyberarm for additive manufacturing.
The intended result is a source-led mechanical exterior supported by hidden
wearable engineering—not a generic anatomical sleeve with decoration attached.

## Current state

`reference/Johnny.blend` is the tracked authority. It contains:

- immutable game/source evidence;
- the anatomical fit reference and non-printable clearance cutter;
- `WORK_FITTED_SURFACE_CANDIDATE`, including retained Repairs 001–013;
- three closed V28 wearer-side engineering prototypes with live rim bevels;
- six deferred rigid-armor reference objects;
- the canonical validation cameras.

The scene is an engineering checkpoint. It is not yet wearable, articulated,
segmented, or a production export.

The next milestone is a coarse whole-arm structural mockup that preserves the
source silhouette, layers, rails, cables, armor voids, and intentional negative
space while adding only the minimum hidden structure needed for wearability.

## Authority

- [Design contract](docs/design.md)
- [Current status](docs/status.md)
- [Validation gates](docs/validation.md)
- [Glossary](docs/glossary.md)
- [History and rejected methods](docs/history.md)
- [Agent instructions](AGENTS.md)

## Repository layout

```text
reference/            tracked master Blend and source reference
docs/                 durable decisions and current status
scripts/              active tools only
validation_reviews/   concise milestone evidence
exports/current/      production exports only
exports/evidence/     deliberately retained non-production exports
.work/                ignored local scenes, runs, renders, and reports
```

Keep each local run self-contained under `.work/runs/<name>/`. Generated
evidence is disposable unless its conclusion is promoted into
`validation_reviews/` or the durable documentation.

## Validation

Validate the master:

```sh
blender --background reference/Johnny.blend \
  --python-exit-code 1 \
  --python scripts/blender/validate_master.py
```

Validate explicit production STL exports:

```sh
scripts/tools/run_validation.sh
```

The repository uses millimeters: `1 Blender unit = 1 mm`, scene
`scale_length = 0.001`, and STL export scale `1.0`.

## Recovery

The repository state before the 2026-07-30 simplification is tagged
`pre-repo-cleanup-20260730`. Only `reference/Johnny.blend` is tracked through
Git LFS; temporary Blend files belong under `.work/`.
