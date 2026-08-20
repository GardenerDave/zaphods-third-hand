# Run 8 Sequential-Cost Aggregation Erratum

This is a model-free accounting correction for future outputs. It does not
alter Run 8 raw evidence, its historical aggregate, or any scientific result.

## Historical binding

- Execution: `.work/run8_scope_escalation/run_20260820T150846Z/`
- Execution manifest SHA256: `312463d5825f3928d37449b63542d2bd55adf71cb5567ec9647c5fa3f21d3610`
- Raw aggregate: `.work/run8_scope_escalation/run_20260820T150846Z/aggregate.json`
- Raw aggregate SHA256: `225f1afaba0aa05212eb241481002ac1d6515575a139b894c3b5d5f466c7538d`
- Raw `treatment_post_baseline_elapsed_ms`: `313,690.136 ms`
- Review-only sequential value: `338,286.365 ms`

The raw aggregate hash and contents remain frozen.

## Confirmed defect

The prior treatment aggregation used the scorecard's final treatment-stage
elapsed value. For a local-pass task this is the local-first elapsed value.
For an escalated task it is only the external escalation elapsed value, so it
omits the already-spent local-first stage.

Run 8 omitted `13,176.262 ms + 11,419.967 ms = 24,596.229 ms` across its two
escalated tasks.

## Future repair

Future Run 8-style review aggregation now uses:

- local-pass task: local-first elapsed once;
- escalated task: local-first elapsed plus escalation elapsed.

The implementation is intentionally separate from the historical Run 8 and
Run 7 drivers:

- `local_harness/sequential_cost.py`
- `scripts/zth_run8_scope_aggregation.py`

Physical execution-resource history remains separate and is not recalculated
from policy scorecards.

## Verification

Model-free tests cover local-pass, mixed, all-escalate, the exact Run 8
undercount shape, no double counting, and separation from physical execution
cost. Historical Run 8 evidence was not opened for rewriting or recomputed.
