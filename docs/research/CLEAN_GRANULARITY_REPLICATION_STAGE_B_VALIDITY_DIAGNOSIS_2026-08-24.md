# Clean Granularity Replication Stage B Validity Diagnosis — 2026-08-24

## Preserved result

The frozen policy result remains `BOUNDED`, with 16 bounded justified abstentions and 16 generalized false-positive delegations. The raw acquisition is intact: 32 starts, 32 terminal responses, 16 local, 16 external, zero infrastructure failures, zero retries/replays, and `TERMINAL_COMPLETE` / `SEALED_BEFORE_EVALUATION`.

## Acquisition firewall

The original harness at `7939f84c42653f96f235426311129760891d53c8` read evaluator bytes while `execute()` verified frozen hashes. It did not parse evaluator JSON, load expectations, use evaluator content to construct payload/order, or expose it to suppliers. Therefore `EVALUATOR_FILE_BYTES_ACCESSED_DURING_ACQUISITION=true`, but `SUPPLIER_OUTCOME_CONTAMINATION_SUPPORTED=false`. The additive harness fix separates preflight scoring-hash verification from acquisition input construction; the missing-evaluator regression passes.

Historical `evaluator_loaded_during_acquisition=false` is interpreted as “semantic evaluator not loaded,” not “no evaluator file bytes were accessed.”

## Supplier-visible construct

The prompt exposed JSON-only output, field names, review-only context, and no-execution/broad-claim boundaries. It did not expose the literal `ready_for_review` value or the evaluator’s `must_include`/`must_not_include` phrases. Those remain scoring-only.

All 32 responses contained the required fields and passed transport, parsing, and protocol checks, but none used the exact `ready_for_review` value. Triage also failed its positive reference phrases for both arms. Unsupported-certainty failed one positive-reference case per arm; the other seven passed positive references but still failed exact review status.

## Failure interpretation

The dominant dimensions are `HIDDEN_ONTOLOGY_MISMATCH` on all 32 arms and `HIDDEN_LITERAL_REFERENCE_MISMATCH` on the triage cases plus unsupported-certainty case 001. No explicit structural-contract, protocol, or independently scored authority-boundary failure was observed. Stage B replicates Stage A’s core must-include/review-status failure signature, although unsupported-certainty must-not behavior differs.

## Claim adjudication

- Level 1, strict frozen-validator validation prediction: `SUPPORTED`.
- Level 2, interface competence: `INCONCLUSIVE`.
- Level 3, underlying semantic capability: `INCONCLUSIVE`.

Construct classification: `INTERFACE_CONVENTION_DOMINATED`. The frozen winner is preserved, but the result does not cleanly isolate benchmark granularity from uncommunicated interface conventions.

External stderr showed model-manager refresh errors and one provider websocket/503 error while all 16 stdout responses remained transport-valid; content impact is `inconclusive`, not a model-failure classification.

## Prospective remediation

The acquisition harness now avoids opening scoring-only evaluator/policy artifacts during `execute()`; preflight verifies their hashes before the harness commit. A regression proves acquisition input construction succeeds when those artifacts are absent. Stage B was not rerun.

`NEXT_DECISION=DESIGN_EXPLICIT_INTERFACE_REPLICATION`
