# Silverhand Cyberarm — Cosplay Build Design Doc

## 1. Goals & Priorities

- Wearable cosplay piece, **not** a replica. Comfort > accuracy.
- Single pre-detailed look: all cable/fiber/panel detail comes from the 3D print, not hand fabrication.
- Two-material architecture: **PLA armor plates** (read as metal) over a **TPU inner shell** (flexible, carries detail).

## 2. Source Model Facts

- Game rip: `a0_001_ma_arms__silverhand` (Cyberpunk 2077, **damaged** variant).
- Single mesh `submesh0`: 26,120 verts / 48,297 polys, **zero wall thickness**, 300 disconnected islands (173 are floating decal planes → delete).
- Native units: **1 unit = 1 cm** (Blender scene fixed to scale_length 0.01).
- Size as ripped: ~77cm fingertip→shoulder top, bounding 51×47×57cm — skin-tight to V, **not wearable as-is**.
- Pose: slight elbow bend (good for wear), arm axis diagonal.
- Structure: finger phalanges (~15 islands), elbow cap, and big forearm plate are **separate floating shells**; armor/understructure elsewhere is texture-painted on shared shells (split per-face or along panel lines).
- Decimate modifier was removed (was hiding 80% of detail in viewport).

## 3. Fit & Scaling

Wearer measurements (cm, circumference): wrist 17.5, mid-forearm 22, widest forearm 25.5, bicep 30 (+3cm flex allowance → design 33).

**v4 resize (applied):** calibrated against the user's proven printed panels (`johnny_silverhand_arm_scaled_up.3mf`, measured via cylinder fits: rigid near-full tubes, interior ≈ body + single small ease). v3 overshot by stacking three margins (+3% ease + wall + stretch reserve) at every section — do not re-stack margins. Profile is near-uniform ~1.1 with a wrist bump; taper difference preserved at 93%.

| Control point | Model exterior perim | v4 exterior target | Scale factor |
|---|---|---|---|
| Wrist (t=-8) | 13.4 | ~17.1 (ref panel Ø5.45) | **1.28** |
| Mid-forearm (t=0) | 19.1 | ~21.0 (ref panel Ø6.7) | **1.10** |
| Widest forearm (t=8) | 26.2 | ~28.7 (ref panel Ø9.0–9.3) | **1.10** |
| Elbow (t=18) | — | blend | **1.11** |
| Bicep (t=26–30) | 28.2 | ~31.5 | **1.12** |
| Hand + fingers (t<-9.5) | 21.4 (palm) | uniform about wrist | **1.10** |
| Pauldron (t>30) | — | rigid, clearance | **1.12** |

Post-check: perimeters hit 16.8/21.0/28.1/31.6 vs targets 17.1/21.0/28.7/31.5; wrist→elbow taper diff 11.4cm (original 12.2). Wrist interior is intentionally snug (TPU stretch + slit gap absorb donning; fit ring arbitrates).

- Ease target: body + 3% (snug; TPU stretches ~15% for donning).
- Wall: 3mm TPU / 2.5mm PLA → exterior = interior + 2π×wall.
- Velcro overlap closure absorbs ±2cm residual error.
- **Must be applied before any splitting/cutting** so plates and shell stay registered.

## 4. Architecture Overview

```
PLA armor plates (paint: metallic + weathering)
   ↑ magnets / velcro, 1.5mm designed gap
TPU inner shell 95A (full arm surface, 3mm, medial slit + velcro)
   ↑ worn over
thin glove / arm of wearer
+ shoulder harness (webbing) carrying the pauldron
```

Gap by construction: TPU shell solidified fully inward (offset −1); PLA plates displaced +1.5mm outward then solidified inward → guaranteed uniform clearance, verified by Boolean INTERSECT QA (target volume ≈ 0).

## 5. Assembly & Panel Inventory

**Actual components (extracted, `COMPONENTS` collection, 46 objects):**

| Object | Role | Notes |
|---|---|---|
| `INNER_A2_forearm_core` | TPU forearm+hand core | mixed faces, needs per-face ARMOR/INNER pass |
| `INNER_A4_bicep_core` | TPU bicep/shoulder core | same |
| `ARMOR_P1_forearm_plate` | PLA hero plate | ready for solidify |
| `ARMOR_P2_elbow_cap` + `ARMOR_P2_elbow_ring_a/b` | PLA elbow assembly | joint articulation watch item |
| `ARMOR_P4_pauldron_top` | PLA pauldron piece | more gores come from bicep core face-split |
| `ARMOR_P5_knuckle_plate` | PLA knuckle/dorsal plate | |
| `phalange_<finger>_<n>` ×27 | finger segments | ~2 shells per anatomical segment (dorsal/palmar) — merge or print as-is; verify thumb/finger mapping visually |
| `REVIEW_<region>_i*` ×10 | unidentified mid-size islands | visual identification needed |
| `fragments_review` | 82 tiny islands merged | likely detail greebles; review before deleting |

Planned per-face splits (classifier-assisted, panel lines hand-tuned): bicep plates P3 from `INNER_A4`, dorsal hand plates P5 from `INNER_A2`, phalange dorsal caps P6 (optional).

### TPU inner shell (95A; bicep section may use foaming TPU)

| ID | Piece | Span (t along axis) | Closure | Notes |
|---|---|---|---|---|
| A1 | Hand shell (palm+dorsal) | CUT_D (−8) → CUT_E (−15) | medial slit + velcro | worn over glove |
| A2 | Forearm shell | CUT_D (−8) → CUT_C (+14) | medial slit + velcro overlap | densest cable detail; carries forearm plate magnets |
| A3 | Elbow band | CUT_C (+14) → CUT_B (+22) | none (pure flex zone) | no plates may bridge; overlap-joined to A2/A4 |
| A4 | Bicep shell | CUT_B (+22) → CUT_A (+30) | medial slit + velcro | foaming TPU candidate; top rim carries D-ring tabs |
| A5 | Finger phalanges ×15 | fingertips → CUT_E | cord + elastic hinges | TPU for comfort; linked over glove |

### PLA plates

| ID | Piece | Source geometry | Attachment | Notes |
|---|---|---|---|---|
| P1 | Forearm hero plate | existing floating shell (island 88) | 6×3mm magnets ×4–6 + 1 anti-shear peg | largest plate |
| P2 | Elbow cap | existing shell (island 89) | magnets to A2 side only + peg | must not bridge joint; watch item in wear test |
| P3 | Bicep plates (2–4) | panel-line cuts of upper-arm shell | magnets + peg | sized to avoid bicep flex zone |
| P4 | Pauldron bell | shoulder shell, cut into 3 gores → glued rigid | strap + side-release buckles to harness; 2 magnets for positioning | heaviest piece; paint tan/olive per reference |
| P5 | Dorsal hand + knuckle plates | panel-line cuts | velcro | conform to hand curvature |
| P6 | Phalange dorsal plates ×~10 | split from phalange shells | velcro to phalanges | optional accuracy pass |

### Soft goods & hardware

| ID | Item | Purpose |
|---|---|---|
| H1 | Shoulder harness: 1" webbing, side-release buckles, D-rings | carries pauldron, stabilizes bicep shell top |
| H2 | Mechanic/tactical glove | base for fingers |
| H3 | 6×3mm N52 magnets (~40) | hero plate attachment |
| H4 | Adhesive velcro + E6000 flexible adhesive | shell closure, small plates |
| H5 | Cord + elastic (finger hinges) | phalange articulation |

## 6. Wrap-Around Panel Strategy

**Decision: segmented shingles, no hinges** (except fingers, already cord-hinged).

- Hinges solve donning, but donning is already solved by the TPU slit — plates attach *after* the shell is on.
- Rule: no single PLA piece spans more than **~90–120°** of limb circumference in flex zones; larger coverage → split into segments with shingle-style overlap along the game's panel lines.
- Pauldron exception: shoulder perimeter is near-static → 3 gores glued into one rigid bell.
- Plate edges chamfered so segments can't catch on each other during motion.

## 7. Attachment & Closure Summary

**Sleeve architecture (decided): ONE welded TPU sleeve, wrist→CUT_A.** 5 bed-sized pieces (seams at ~t=-2, t=10, t=24; elbow band t=14–22 printed whole — no welds in the flex zone), **TPU pen-welded** (3D pen + TPU filament; CA glue fatigues in flex zones — fallback only, with stitch-holes). Weld over a form at wearer circumference. No hand shell (cancelled — see glove). Workflow: pull on sleeve → lace up → snap plates.

| Interface | Method |
|---|---|
| TPU sleeve donning slit (medial, full length — the only line never welded) | **corset lacing**: hand-set metal grommets through both flaps + rat-tail cord + printed tongue panel stitched to one side (continuous adjustment, distributes pressure, on-theme). Velcro demoted to small-plate duty only |
| TPU sleeve bed-seams | TPU pen weld (permanent) |
| Elbow band flexibility | wall thinned to ~2mm + ventral relief gills + model's own dorsal ribbing as bellows; wrist/shoulder standard 3mm |
| Hero plates ↔ shell | magnets (TPU side in printed membrane pocket; PLA side glued cap/pause-insert) + 1 anti-shear peg per plate |
| Small/curved plates | velcro |
| Pauldron ↔ body | harness straps + buckles; magnets for positioning only |
| Elbow hardware | dorsal-only cap + blades, partial rings, standoff 5–8mm (redesign task — joint clearance) |
| **Glove** | **100% fabric base** (mechanic/tactical glove); dorsal hand plate P5 + knuckle plate velcroed to glove back; phalanges cord+elastic linked over glove fingers. NO TPU glove |

**Printer: A1 mini, 18×18×18cm, direct drive (TPU-capable).** Cut policy: structural cuts → mechanical joins; PLA bed-cuts → CA-fuse with printed alignment keys; TPU bed-cuts → weld.

## 8. Validation Plan

- **Clearance:** Boolean INTERSECT on every plate↔shell pair after solidify; require volume ≈ 0.
- **Per-piece printability:** 3D Print Toolbox checks (manifold, intersections, wall thickness).
- **Rigid-body physics:** *skipped for static fit* (designed 1.5mm gap + boolean QA is deterministic and equivalent). Reserved as phase-2 option for finger-hinge motion validation; a physical test print is the cheaper check anyway.
- **Test prints first:** (1) 5cm forearm fit ring, (2) one phalange pair with hinge gap 0.4–0.6mm, (3) one magnet pocket pair.

## 9. Manufacturing Parameters

- Nozzle 0.4mm; features <0.5mm will merge; normal-map detail does not print (geometry only).
- TPU 95A, 3 walls, ~15% gyroid; foaming TPU only for bicep section.
- PLA plates 2.5mm, 4 walls; orient for metallic-paint surface quality (outer face up).
- Est. pieces: TPU ~7 + phalanges 15; PLA ~15–20; print time ~3–5 days total.

## 10. Build Sequence

1. ✔ Per-section radial fit (v4, calibrated to reference 3MF)
2. ✔ Decal delete; loose-parts split → 46 named components
3. ✔ Sleeve extraction (wrist→CUT_A): S1/S2 forearm + S3 elbow band (lofted, 2mm) + S4 bicep, each split into A/B half-shells at the 227° medial closure line, solidified (3mm / 2mm band)
4. ✔ Features: eyestrips (solid — **punch grommet holes at assembly**, printed holes failed in TPU boolean), cover flaps (hide lace fully), magnet pockets (Ø6.2×2.5mm + 0.5mm membrane, dorsal θ=47°), anti-shear holes (Ø6.2 through), elbow gills (12×1.5mm, ventral ±35°, t=14/17/20)
5. ✔ Exports: `exports/sleeve/*.stl` (20 files), `exports/test_prints/*.stl` (fit ring A/B, 2 phalanges, magnet coupon) — all cm→mm ×10
6. ⬜ **TEST PRINTS** (order): magnet coupon → fit ring A/B → phalange pair → S3 elbow band halves
7. ⬜ Full sleeve print → weld → fit → armor pass (reuse reference 3MF panels where possible) → paint → wear test

**Assembly notes:** eyestrips weld to half-shell edges (TPU pen); cover flap welds along ONE edge only, closes over the lace (low-profile velcro dot or magnet pair at ends); grommets = hand-set metal kit + leather punch; elbow gills span wall — verify they don't tear under flex (increase slot spacing if so).
