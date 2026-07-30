# V28 Authored Wearable Panels

Status: **active construction approach; scope ready, geometry not emitted**

Updated: 2026-07-30

## Decision

Stop repairing the hidden C9/C20 game sheet. Preserve recognizable exterior
character, remove the broad wearer-side failure region after exterior review,
and author three clean TPU panels around the clearance cutter.

The panels are engineering geometry. They do not inherit source faces,
directional-chart topology, or cutter triangles. Neutral zone names remain in
use until wearer landmarks authorize anatomical names.

## Starting authority

`scripts/blender/build_v28_wearable_panel_scope.py` verifies:

- the exact V27 253-face source-reference scope;
- a continuously clear 71-edge outer boundary;
- six known decorative exterior faces
  `[2219, 2220, 2221, 2225, 2233, 2276]`;
- a provisional 247-face wearer-side removal scope;
- three neutral construction zones along the cutter principal axis.

The repeat-identical authority is:

- `_validation/experiments/geometry_repair/component_20_methods/repair_014_joint_c9_c20_elbow_v28/v28_wearable_panel_scope_authority.json`
- SHA-256
  `9e0930ff1a72eba6744a80ef3e6cdcbde900f7a34152af9114534cfa5b8cad2c`

No geometry was emitted and the Blend was not saved.

## Construction contract

Each initial panel uses:

- five clean authored cross-sections;
- at least `1.7 mm` digital clearance;
- a nominal `4 mm` engineering seam to its neighbor;
- no source or cutter topology;
- local junctions to retained exterior forms;
- preserved intentional openings and negative space.

Add a fourth panel only for a named fit, motion, printing, or assembly reason.
Do not derive production panel count from diagnostic face clusters.

The six known exterior faces remain reference evidence. The other 247 faces
are only provisionally removable until a bounded exterior review confirms that
no additional recognizable exterior form would be discarded. Modest relocation
or trimming is allowed when a retained decorative form conflicts with the
wearer envelope.

## Next bounded experiment

In a disposable V28 Blend:

1. create three curve or mesh-loop scaffolds from five cross-sections each;
2. keep them independent and visibly separated by the nominal seams;
3. do not add thickness, detailed junctions, or source decoration yet;
4. audit vertices, continuously sampled edges, and adaptive triangle interiors;
5. render the scaffold only after it passes those cheap geometry gates.

The scaffold is not promoted geometry. Its purpose is to validate that three
simple panels can cover the wearer-side engineering need before detail work.
