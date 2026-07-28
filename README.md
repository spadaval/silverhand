# Silverhand Cyberarm

A wearable Johnny Silverhand-inspired cyberarm for 3D printing. The design uses
flexible TPU structure with separate rigid PLA armor while prioritizing comfort
and source-model character over literal replica construction.

## Current direction

The active milestone is a wrist-to-upper-bicep **fitted surface master**:

- begin again from the clean armor-stripped game surface;
- map the whole surface through one shared, smooth deformation field;
- preserve topology, relative placement, depth ordering, and negative space;
- rebuild only bounded regions that cannot survive wearer fitting;
- use a wearer-clearance volume only as a Boolean cutter and collision tool;
- defer thickness, structural junctions, and printable topology until the fitted
  surface passes matched-view review.

Armor-gap panels, magnet hardpoints, closure details, segmentation, and final
exports are deliberately later milestones.

## Project authority

- [Documentation index](docs/README.md) — authority map and reading order
- [Design contract](docs/design.md) — accepted strategy and geometry contract
- [Current status](docs/status.md) — active scene and immediate work
- [Validation contract](docs/validation.md) — promotion gates
- [Glossary](docs/glossary.md) — authoritative project terminology
- [History](docs/history.md) — rejected approaches and retained lessons
- [AGENTS.md](AGENTS.md) — operating conventions

## Important files

- `reference/Johnny.blend` — tracked master scene
- `reference/johnny_silverhand_arm_scaled_up.3mf` — print-proven reference
- `validation_reviews/` — tracked qualitative review records
- `exports/current/` — production exports only; currently empty
- `exports/evidence/` — retained non-production proof artifacts

The entire project uses millimeters. Blender is configured as
`1 Blender unit = 1 mm`, and STL export scale is `1.0`.

## Validation

Validate the master scene:

```sh
blender --background reference/Johnny.blend \
  --python-exit-code 1 \
  --python scripts/blender/validate_master.py
```

Validate only the explicit current export directory:

```sh
scripts/tools/run_validation.sh
```

An empty `exports/current/` is expected until a connected main-geometry master
is approved.

## Git LFS

Install Git LFS before cloning or pulling:

```sh
git lfs install
git clone git@github.com:spadaval/silverhand.git
```

Only `reference/Johnny.blend` is tracked as a `.blend`. Working scenes and local
archives remain under the ignored `blender_files/` directory.
