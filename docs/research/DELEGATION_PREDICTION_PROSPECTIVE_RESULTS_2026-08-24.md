# Prospective Delegation Prediction Results — 2026-08-24

Run: `.work/model_size_supplier_floor/delegation_prediction_test_scope_v0/run_20260824T170000Z`

## Integrity

The frozen 32-opportunity acquisition completed before evaluator access: 32 local/external call starts, 32 responses, zero retries, zero replays, zero tool calls, and `runtime_evaluator_influence=0`. Raw responses were sealed before evaluation.

## Supplier arms

- local: 5/16 bounded-capability-valid; parse 16/16; contract 6/16.
- external: 16/16 bounded-capability-valid; parse 16/16; contract 16/16.

## Frozen policy outcomes

- generalized: `{"delegated": 16, "delegated_coverage": 1.0, "false_positive_delegations": 0, "justified_abstentions": 0, "selected_supplier_validation_rate": 1.0, "selected_valid": 16, "successful_delegations": 16, "unnecessary_abstentions": 0}`
- degeneralized: `{"delegated": 8, "delegated_coverage": 0.5, "false_positive_delegations": 5, "justified_abstentions": 0, "selected_supplier_validation_rate": 0.375, "selected_valid": 3, "successful_delegations": 3, "unnecessary_abstentions": 8}`
- lexicographic result: `DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED`

- winning tier: `false_positive_avoidance`
- capability-equivalent cost cases: 3; generalized lower-cost selections: 0; degeneralized lower-cost selections: 3

Markers: `GENERALIZED_MORE_SUCCESSFUL_DELEGATIONS=true`, `GENERALIZED_FEWER_FALSE_POSITIVE_DELEGATIONS=true`, `GENERALIZED_FEWER_UNNECESSARY_ABSTENTIONS=true`; cost markers are derived from the frozen resource-weight artifact.

The lexicographic ordering was applied exactly as preregistered: false-positive avoidance, successful delegation, abstention quality, then cost only for capability-equivalent choices. The generalized policy therefore wins this cohort because it has zero false-positive delegations versus five for the degeneralized policy. This disagreement-enriched cohort is not incidence-representative and does not qualify suppliers or alter production routing.

## Telemetry

Latency is descriptive. Gross GPU-device energy was unavailable for all 32 calls; energy fields are therefore null. Measurement boundary: level 2, GPU-device-only.

Per-call hashes and classifications are in the machine-readable matrix.

`qualification_change=false`

`production_routing_change=false`
