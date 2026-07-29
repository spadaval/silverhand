# Component 9 repair methods

## Goal

Classify the largest remaining source component and determine whether its
`163` cutter penetrations can be repaired without deforming its visible
wrist-to-forearm shell.

The experiment begins from retained
`REPAIR_005_COMPONENT_42_MASKED`. The active retained work scene was not
changed.

## Classification

Component `9` is a large connected structural surface with `2,508` vertices
and `4,497` faces. It spans much of the wrist and forearm, so treating the
entire connected component as one movable fragment is incorrect.

Its `163` penetrating vertices form six disconnected topological clusters.
Two clusters contain `154` of them:

| Cluster | Vertices | Station range | Minimum margin | Faces touching the cluster |
|---|---:|---:|---:|---:|
| proximal inner wall | 86 | 226.809–288.965 mm | -43.069797 mm | 238 |
| wrist inner wall | 68 | 2.261–55.708 mm | -27.095947 mm | 193 |

Individual high-detail classification views show that both dominant clusters
belong to wearer-facing interior sheets around the lumen. The recognizable
outer shell and most exterior details are not the colliding surface. Component
`20` is the closest neighboring component at `0.012323 mm` and occupies much
of the adjacent inner structure.

## Tested controls

The ordinary component-level methods are rejected:

- deleting the `163` penetrating vertices removes `466` faces; complete
  exterior views remain nearly unchanged, confirming the interior
  classification, but the result contains large open lumen holes;
- a nominal `30 mm` rigid lift is not radial across this large component and
  creates `670` component-9 penetrations rather than clearing it;
- radial-depth compression clears component `9` but moves its vertices by
  `14.523225 mm` at the median and `44.669798 mm` at maximum, with `11`
  reversed faces;
- uniform radial offset introduces `9` reversed faces;
- the ordinary masked field introduces `58` reversed faces.

A wider geodesic diffusion sweep also fails. Variants from `12` to `60`
iterations with factors from `0.85` to `0.95` clear the penetrating vertices
but increase the orientation failures to `90–125`. Smoothing the same
pointwise projection cannot turn it into a valid reconstruction.

## Conclusion

Do not move or compress component `9` as a whole. Do not retain the deletion
control.

The two dominant collision clusters are suitable candidates for tactical
hidden-surface reconstruction:

1. preserve the visible exterior, openings, rims, and boundary landmarks;
2. remove only the classified wearer-facing patch;
3. derive a local replacement surface from the clearance cutter plus the
   `1.6 mm` reserved wall;
4. connect and edit that patch locally rather than generating a global
   carrier;
5. validate the wrist and proximal clusters separately.

Component `20` should be classified before designing either replacement,
because it is nearly coincident with component `9` and may define which
interior layers are redundant.

## Resume point

Start the next thread from
`blender_files/Johnny_geometry_repair_work.blend`. Its SHA-256 is
`b508e2370ae4ba9eddf77a5b18962394a1f31da81d4a776a01e4cb349eced8a1`.

First classify component `20` and its violation clusters. Then compare the
component-9 and component-20 inner sheets before creating any patch geometry.
Do not rerun whole-component displacement or the diffusion sweep.

Inspect only individual RGB images at high detail. Do not replay a contact
sheet or all images at once; the prior image-heavy thread ended with a
malformed historical base64 image payload during context compaction.

## Evidence

- Exact retained/pre-experiment checkpoint:
  `blender_files/checkpoints/geometry_repair/pre_components_9_20.blend`
- Classification:
  `_validation/experiments/geometry_repair/component_9_methods/classification/`
- Dominant violation clusters:
  `_validation/experiments/geometry_repair/component_9_methods/cluster_0/`
  and `_validation/experiments/geometry_repair/component_9_methods/cluster_1/`
- Control trials:
  `_validation/experiments/geometry_repair/component_9_methods/trials/build_report.json`
- Diffusion sweep:
  `_validation/experiments/geometry_repair/component_9_methods/trials/diffusion_sweep_report.json`
- Deletion classification control:
  `_validation/experiments/geometry_repair/component_9_methods/delete_context/`
