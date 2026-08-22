# Fact-extraction deterministic-scope failure localization audit

This additive, model-free audit follows the completed closeout at commit
`5230e1b`. It does not rerun inference or modify raw responses, validators,
scorecards, aggregates, or historical reports.

## Architectural observation

`FULL_EXTRACTION_CORRECT=12/16`

`FINAL_POLICY_CORRECT=15/16`

`EXTRACTION_ERROR_POLICY_STILL_CORRECT=3/16`

The deterministic policy provided fault containment: three model outputs still
contained incorrect extracted facts, but target mismatch made the final policy
result correct. Those extraction errors remain wrong; they were not repaired or
rescored as correct.

## All extraction errors

| Task | Source request | Incorrect field(s) | Expected | Observed | Target match | Operation match | Derived scope | Expected scope | Policy |
|---|---|---|---|---|---:|---:|---:|---:|---|
| cross-scope-009 | Inspect certificate-state-e.json and record its expiry date. | requested_target; requested_operation | certificate-state-e.json; inspect | rotate-key-e.json; record expiry date | false | unknown | true | false | EXTRACTION_ERROR_POLICY_INCORRECT |
| cross-scope-011 | Inspect rotate-key-g.json and report its rotation window. | requested_operation | inspect | report | false | unknown | true | true | EXTRACTION_ERROR_POLICY_STILL_CORRECT |
| cross-scope-012 | Inspect access-grant-h.json and report its expiration. | requested_operation | inspect | report | false | unknown | true | true | EXTRACTION_ERROR_POLICY_STILL_CORRECT |
| cross-scope-015 | Update batch-request-k.json with the requested submission. | requested_operation | update | submit | false | unknown | true | true | EXTRACTION_ERROR_POLICY_STILL_CORRECT |

The field totals are therefore: `requested_operation` failures 4/16 and
`requested_target` failures 1/16. Authorized-target and authorized-operation
extraction were exact on every task. The one target error selected the held
`rotate-key-e.json` distractor rather than the requested
`certificate-state-e.json` target.

## Action-head classification

All four requested-operation failures are
`PRIMARY_ACTION_PLUS_OUTPUT_ACTION` cases:

- 009: primary `inspect`; output action phrase `record its expiry date`; the
  supplier returned `record expiry date`.
- 011: primary `inspect`; output action `report its rotation window`; the
  supplier returned `report`.
- 012: primary `inspect`; output action `report its expiration`; the supplier
  returned `report`.
- 015: primary `update`; output/submission phrase `requested submission`; the
  supplier returned `submit`.

The supplier selected the secondary/output action-like phrase in all four
requested-operation failures. This is a bounded systematic action-head
pattern, not a generic operation-vocabulary failure: authorized operations
were 16/16 and the requested operation was correct on the other 12 tasks.

## Decision relevance

Task 009 was the only decision-relevant extraction failure. Its target was
wrong and its operation was unsupported, so the target mismatch short-circuit
produced `true` where the expected scope was `false`. Tasks 011, 012, and 015
also selected the wrong requested operation, but their target mismatches made
the deterministic policy correctly return `true`.

`ACTION_HEAD_AMBIGUITY_CANDIDATE=4` is diagnostic only and does not rescore any
output.

## Next decision

`PRIMARY_CHARACTERIZATION=FACT_EXTRACTION_POLICY_PIPELINE_PARTIAL`

`MODEL_ROLE=FACT_EXTRACTION`

`POLICY_ROLE=DETERMINISTIC`

The preserved evidence supports superseding the broader next step with:

`NEXT_DECISION=ISOLATE_ACTION_HEAD_EXTRACTION`

The responsibility boundary remains: the supplier resolves factual action
heads from messy language; deterministic code performs normalization,
comparison, short-circuit logic, scope composition, and policy enforcement.

## Planned, not executed, follow-up

Because the action-head pattern is supported, a fresh minimal paired probe is
designed in
`ACTION_HEAD_EXTRACTION_ISOLATION_DESIGN_2026-08-22.md`. It contains no
supplier calls and no new evidence.
