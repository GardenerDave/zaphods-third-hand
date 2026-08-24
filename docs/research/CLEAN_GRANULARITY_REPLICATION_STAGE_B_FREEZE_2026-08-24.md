# Clean Granularity Replication Stage B Freeze — 2026-08-24

Status: `CLEAN_GRANULARITY_REPLICATION_STAGE_B_FROZEN_UNEXECUTED`

This is a model-free freeze of 16 fresh, disagreement-focused direct-unit tasks: 8 triage-routing and 8 unsupported-certainty. No Stage B supplier calls, responses, results, or target outcomes exist.

## Frozen comparison

- Generalized: `MICRO_AGGREGATE_DIRECT`; local 5/32, external 16/32; delegate external for both families.
- Bounded: exact direct supplier × family × interface × responsibility evidence; both suppliers are `SUPPORTED_NEGATIVE` for both selected families; abstain for both.
- Disagreement: 16/16 are `DELEGATE_VS_ABSTAIN`.

The two supplier arms remain eligible counterfactual observations for every target. Policy decisions do not suppress arm execution.

## Controls

The future budget is 16 local + 16 external = 32 calls, with no retries, replays, repair, teacher/worker rescue, tools, repository/evaluator access, substitution, threshold tuning, qualification, or production routing. Acquisition must seal raw responses before evaluator access and must finalize execution status as `TERMINAL_COMPLETE` or `TERMINAL_INCOMPLETE`.

Runtime-only, scoring-only, and exact-payload manifests are separate. Evaluator corruption has no effect on runtime inputs (`RUNTIME_EVALUATOR_INFLUENCE=0`).

## Claim boundary

Any later result is limited to this prospective, disagreement-focused direct-capability cohort and is not an incidence estimate, supplier qualification, or universal claim about broad or bounded evidence.

## Provenance

Base gate: `96c7fe9a23bcfafd2e339e77a183090bc65464ea`. Stage A semantic audit: `fb21f019e08e9f7d312fa37439396e0ee509641b`. Stage A result: `6b1ec1ec3649276c3f846507cd3bb71e558ee14c`. Design: `f55f677c46a0746ef4ba4dda4072c4e2f452b544`. See the machine-readable freeze and its referenced hashes for the complete provenance record.

`NEXT_DECISION=EXECUTE_CLEAN_GRANULARITY_REPLICATION_STAGE_B`
