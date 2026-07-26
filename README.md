# Silverhand Cyberarm

A wearable cosplay build of Johnny Silverhand's cyberarm from Cyberpunk 2077 —
modeled in Blender, 3D printed, and assembled as a two-material arm piece.

## Goals

- **Wearable cosplay piece, not a replica.** Comfort takes priority over screen accuracy.
- **All detail comes from the 3D print.** Cables, fibers, and panel detail are printed geometry — no hand fabrication.
- **Two-material architecture:**
  - **PLA armor plates** that read as metal (painted + weathered)
  - A flexible **TPU inner sleeve** (95A) worn underneath, carrying the plates and most of the surface detail

## Approach

- Source geometry is a game rip (`a0_001_ma_arms__silverhand`, damaged variant), rescaled per-section to the wearer's measurements in Blender.
- One welded TPU sleeve runs wrist → bicep, closed by corset lacing; PLA plates attach on top with magnets/velcro; the hand is built on a fabric mechanic's glove.
- Everything is sized for a Bambu A1 mini (18×18×18 cm bed, TPU-capable).

The full design rationale, fit/scaling math, panel inventory, and build sequence live in [DESIGN.md](DESIGN.md).

## Cloning

This repo uses **Git LFS** for the master Blender scene (`reference/Johnny.blend`, ~260 MB).
Install [git-lfs](https://git-lfs.com) *before* cloning, or that file will arrive as a small text pointer instead of the real scene:

```
git lfs install
git clone git@github.com:spadaval/silverhand.git
```
