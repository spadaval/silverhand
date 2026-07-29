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

---

## Re-review — commit `abbb116`

Re-review role: Agent Factory `review`

Re-review started: `2026-07-29T21:18:15Z`

Re-review completed: `2026-07-29T21:19:42Z`

Scope: read-only verification of the two prior findings and preservation of the
previously verified aggregate claims. No gap solve, geometry construction,
source mutation, image work, Blend save, or promotion was authorized or
performed.

### Findings

No blocking findings.

### Prior finding resolution

- **Resolved — Stage 0 attestation.**
  `v27_input_attestation.json` records:
  - status `V27_INPUT_AUTHORITIES_FROZEN`;
  - exact input Blend path and SHA-256
    `68deef0bf80fdcfe2d592c81c1625061d93bcbc41e25e405a35d551e5dfc7823`;
  - Blender runtime `5.2.0 LTS Beta`, tuple `[5, 2, 0]`;
  - scene `Scene`, Metric/Millimeters units, and
    `scale_length = 0.0010000000474974513`;
  - exact object/datablock identities, topology counts, material-slot counts,
    and geometry fingerprints for
    `EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER` /
    `EVAL_REPAIR_014_COORDINATED_INTERFACE_AFTER_MESH` and
    `WORK_FITTED_SURFACE_CANDIDATE` /
    `WORK_FITTED_SURFACE_CANDIDATE_MESH`;
  - source fingerprints
    `aaf473c8d127896bb7fa46cee96b7b56a4a6710bac203a977051393cf3136558`
    and
    `70180fc9e48bc346e446ccf49c3d6b79b2ca8d105cc5cab3c1806c6b7beb2326`;
  - explicit false safety flags for mutation, geometry, Blend save, image
    work, and promotion.

  The aggregate builder hash-verifies the attestation at SHA-256
  `0c10b913be5647e53c623d2de62ab064874cfcc5d7a16b147f0139561e679bce`.
  Two independent background Blender replays produced that exact byte hash and
  matched the committed artifact.

- **Resolved — exact ordered aggregate boundaries.**
  Independent reconstruction from the authority proved:
  - the source aggregate boundary contains exactly 260 unique normalized
    edges;
  - the 20 emitted records contain exactly 260 normalized edges;
  - the emitted edge multiset is edge-disjoint and exactly equals the source
    aggregate-boundary edge set;
  - every record is nonempty and reports `is_simple_loop: true`,
    `is_simple_path: false`;
  - every ordered sequence closes at its first vertex, repeats no other
    vertex, traverses every member edge exactly once, and has degree two at
    every member vertex;
  - no branched or empty ordered record remains.

  This resolves
  `V27_AGGREGATE_BOUNDARY_LOOPS_NOT_MATERIALIZED`.

### Preserved claims

Direct comparison with the pre-fix committed authority confirms no change to:

- the exact 26-cell mask, its 185 C20 and 81 C9 faces, unique ownership,
  immutable overlap, or maximum-mask containment;
- any of the four complete terminal incidence records;
- all 571 negative-space incidence records;
- all 63 aggregate floor conflicts, 35 excluded conflicts, the complete
  98-record accounting, or the 12,523 excluded `NO_FLOOR` samples;
- the seven cell SCC memberships, `[7, 12, 7]` batch memberships, maximum SCC
  size seven, or batch bound;
- any safety flag or promotion state.

The dependency fingerprint changes only because the former nine branched
boundary nodes were replaced with the 20 exact loop nodes and their
dependencies.

### Repeatability and static checks

- Two independent aggregate-builder runs were byte-identical and each produced
  committed authority SHA-256
  `43c0b161d71a3ef2b6471f0ab63ab5ea71641554a5254354a2d31db58a2ed338`.
- Two independent Stage 0 background-Blender runs were byte-identical and each
  produced committed attestation SHA-256
  `0c10b913be5647e53c623d2de62ab064874cfcc5d7a16b147f0139561e679bce`.
- Commit `abbb116` contains no model, image, or Blend change. The builder
  remains a JSON-only authority operation. The attestation opens the frozen
  Blend read-only and invokes no save operator.

### Residual risk

- This audit approves only the corrected Stage 0/Stage 1 authority. It does
  not approve a flex-gap placement, candidate surface, or Gate B/D/C result.
- The deterministic cycle decomposition is valid for this exact frozen
  260-edge authority. A future changed boundary graph must repeat the exact
  exhaustive partition audit rather than generalizing this result.

### Re-review result

`PASS_V27_ORDERED_BOUNDARY_AND_STAGE0_AUDIT`

Both prior findings are resolved. The corrected read-only aggregate authority
may proceed to the separately gated exact flex-gap solve.
