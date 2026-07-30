# Current Production Exports

This directory contains only explicit production print candidates.

It is intentionally empty. The current tracked master is an engineering
checkpoint, not a complete wearable or segmented print assembly.

Every future STL must be named in an export manifest, produced at millimeter
scale `1.0`, and pass:

```sh
scripts/tools/run_validation.sh
```
