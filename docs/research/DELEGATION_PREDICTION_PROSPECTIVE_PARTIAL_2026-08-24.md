# Prospective Delegation Prediction — Interim Partial Observation

The corrected frozen experiment began at:

`.work/model_size_supplier_floor/delegation_prediction_test_scope_v0/run_20260824T170000Z`

An interim monitor observed the acquisition after ten supplier calls had been
started:

- `dpt-scope-001`: local response, external response;
- `dpt-scope-002`: local response, external response;
- `dpt-scope-003`: local response, external response;
- `dpt-scope-004`: local response, external response;
- `dpt-scope-005`: local response, external call started without a durable response.

Nine `response.json` artifacts and ten `call_started.json` artifacts are
preserved at that interim observation. The original one-shot process was still
running; it subsequently completed all 32 opportunities. No retry, replay,
repair, or resume was performed.

The scoring-only evaluator was never loaded. No case was scored, no delegation
outcome was inferred, and no predictor or policy was changed. Tool calls,
teacher intervention, and evaluator influence were zero.

This interim record is superseded by the completed raw seal and results matrix.
It is retained to document the asynchronous observation and must not be read as
the final execution count or a second execution.

`SUPERSEDED_BY=DELEGATION_PREDICTION_PROSPECTIVE_RESULTS_MATRIX_2026-08-24.json`
