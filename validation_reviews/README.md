# Validation evidence

This directory contains concise evidence, not generated-workspace history.
Ordinary modeling experiments belong in the
[experiment notebook](../experiments/README.md); they do not need a validation
record merely because a checkpoint or contact sheet exists.

- `main_geometry_baseline/` records the cleaned carrier-free visual baseline.
- `static_fit_prototype/` records the first anatomy-led reversible deformation
  and why it remains an unpromoted fitted-surface candidate.
- `fragment_rescue/` records the first reversible shallow-clearance salvage
  pass and the deep failures intentionally deferred for reconstruction.
- `geometry_repair/` records the retained stepwise fitted-surface repair chain,
  current component classification, and why the candidate is still not
  promoted.
- `layered_coupon_proof/` preserves the earlier evidence that overlapping
  closed source-detail solids can pass STL checks and slice successfully.

Current records follow the schema in
[`docs/validation.md`](../docs/validation.md). A visual baseline is not a
connected master or print approval. Generated detail views should be recreated
when needed; retain one useful contact sheet unless an individual image has
unique review value.

Automated scripts may calculate fingerprints and geometry results, but they must
never manufacture qualitative approval.

Use this directory only when retaining the review for a named validation gate
or milestone. Experiment goals, observations, failed trials, and informal
learnings should be written in Markdown under `experiments/` and promoted here
only when the work actually reaches validation review.
