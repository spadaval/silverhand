# V27 aggregate authority independent review

Reviewed commit: `88d9f4c8111986319be7c6c21048954cf18c1427`

Review role: Agent Factory `review`

Review started: `2026-07-29T21:07:46Z`

Scope: independent read-only review of the V27 26-cell aggregate checkpoint,
builder, authority, receipt, frozen V26 inputs, and applicable design,
validation, history, and status contracts.

## Findings

- **High — the emitted aggregate-boundary nodes are not the exact boundary
  loops required by the V27 DAG contract.**
  `scripts/blender/build_v27_aggregate_authority.py:238-323` groups every
  vertex-connected boundary edge into one component in
  `build_boundary_components()`. Four of the nine emitted records are branched
  graphs, not loops or paths:

  | Record | Edge count | Vertex degrees | Loop | Path |
  | --- | ---: | --- | --- | --- |
  | `AGGREGATE_BOUNDARY_C20_000` | 65 | `2, 4` | false | false |
  | `AGGREGATE_BOUNDARY_C20_003` | 48 | `2, 4` | false | false |
  | `AGGREGATE_BOUNDARY_C20_004` | 33 | `2, 4` | false | false |
  | `AGGREGATE_BOUNDARY_C9_000` | 79 | `2, 4` | false | false |

  The checkpoint requires “the exact immutable-complement boundary loops
  adjacent to each cell” as DAG nodes and requires Stage 1 to derive boundary
  loops. Merging cycles that merely touch at a vertex loses the exact ordered
  loop identity needed later for complementary winding and cumulative boundary
  evaluation. The current `ordered_vertex_ids` for all four records is empty,
  so the authority cannot supply that identity. This invalidates the claimed
  `PASS_V27_AGGREGATE_AUTHORITY_INVARIANT_AUDIT` and blocks reliance on the
  reported DAG/batches for construction.

  Exact counterexample:
  `AGGREGATE_BOUNDARY_C20_000` contains degree-4 vertices and reports both
  `is_simple_loop: false` and `is_simple_path: false`, despite being emitted as
  one `IMMUTABLE_COMPLEMENT_BOUNDARY` DAG node.

  Required correction: deterministically decompose the boundary edge graph
  into exact ordered loops (and explicitly classified source-open chains where
  the source topology genuinely has an open chain), give each loop/chain its
  own identity, rebuild cell dependencies, SCCs, and batches, and repeat this
  audit before flex-gap solving.

- **Medium — the required Stage 0 attestation was not materialized.**
  The checkpoint at `checkpoint.md:133-140` requires the V27 artifact to record
  the Blender version, scene units, object identities, source mesh
  fingerprints, and the named result `V27_INPUT_AUTHORITIES_FROZEN`. The
  authority records the code hash, input file hashes, and no-mutation state,
  but contains no Blender-version, units, or object-identity fields and the
  checkpoint never records the Stage 0 result. Hashing the frozen authorities
  is strong integrity evidence, but it does not satisfy the explicit durable
  attestation/resume schema. Add the named provenance fields from the frozen
  authorities (without opening or mutating the Blend), then regenerate the
  authority and receipt.

## Verified evidence

- The builder and every frozen input hash named in the checkpoint match.
- The exact selected set is the frozen 23 seed-covering cells plus only
  `EXPOSURE_CELL_C20_007`, `EXPOSURE_CELL_C20_009`, and
  `EXPOSURE_CELL_C20_011`.
- The aggregate contains 185 C20 faces and 81 C9 faces with unique cell
  ownership, zero reviewed-ambiguous overlap, and zero face outside the frozen
  maximum masks.
- All four frozen terminal incidences are complete:
  C20 lower uses faces `3102/3103` in cells `011/012`; C20 upper uses faces
  `2995/3052` in cells `007/009`; C9 lower uses face `1673` in cell `002`; C9
  upper uses face `1621` in cell `001`.
- The full floor ledger contains 91 flex-gap source-floor conflicts and seven
  layer-order inversions. The authority accounts for all 98 as 63
  aggregate-touched and 35 excluded records.
- The compact floor authority reports all 12,523 intentional non-gap
  `NO_FLOOR` samples excluded from mask derivation.
- The authority reports 571 exact keepout-incidence records. No keepout or
  gap-solving claim is made by this milestone.
- Re-executing the builder twice to distinct temporary outputs produced the
  committed authority SHA-256
  `552544386bb3f3012527b2bfd819986c1c7b3f82d5d4585b01feb426e4ad78af`
  both times. Receipt semantics were identical; byte differences between
  receipts written to different temporary paths were limited to the recorded
  `authority_path`, as designed.
- Independent inspection confirms seven cell SCCs with maximum cell count
  seven and batch cell counts `[7, 12, 7]`; no SCC is split and no batch
  exceeds 12. These batches remain unapproved because their boundary-node
  authority is incomplete.
- Commit `88d9f4c` changes only text/JSON authority, the read-only builder, and
  status documentation. The builder opens no Blend and imports no Blender or
  image API. The authority and receipt explicitly record no flex-gap solve,
  geometry emission, source mutation, image work, Blend save, or promotion.

## Open questions

- The contract names only boundary loops, while the source may also contain
  genuine source-open chains. The correction should durably classify those
  chains instead of representing every vertex-connected boundary graph as a
  loop-like aggregate component.

## Residual risk

- This review did not validate a flex-gap placement, candidate geometry, Gate
  B, Gate D, or Gate C; all are correctly deferred.
- Exact geometric keepout intersections were reviewed as authority
  incidences, not as a future candidate-clearance proof.

## Review result

`V27_AGGREGATE_BOUNDARY_LOOPS_NOT_MATERIALIZED`

The named aggregate-authority audit does **not** pass. Do not begin flex-gap
solving or candidate construction from this DAG.

Review completed: `2026-07-29T21:08:28Z`
