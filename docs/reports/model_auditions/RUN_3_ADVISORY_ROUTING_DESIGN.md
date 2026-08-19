# Run 3: Advisory Routing Cost Experiment

Status: preregistered and frozen for review; no Run 3 model calls have been made.

The formal policy freeze is recorded in
[`RUN_3_ROUTING_POLICY_FREEZE_2026-08-18.json`](../../research/RUN_3_ROUTING_POLICY_FREEZE_2026-08-18.json),
and the preregistration is recorded in
[`RUN_3_PREREGISTRATION_2026-08-18.json`](../../research/RUN_3_PREREGISTRATION_2026-08-18.json).

## Question

Can a routing policy frozen from Run 1 and Run 2 capability cards reduce
intervention cost on genuinely fresh reviewed tasks without reducing final
deterministically validated solve rate?

## Arms

Control uses the existing fixed supervised ladder:

```text
1.7B baseline -> deterministic retry -> 30B local teacher
                 -> external teacher -> review/unresolved
```

The treatment uses the same bounded interventions, but consults the frozen
advisory policy keyed by task family plus normalized baseline failed structural
and semantic check IDs. Evidence resolution is exact signature, semantic
signature, deterministic failure class, or task family, in that order. A
recommendation is recorded before execution; it does not grant authority
outside this explicitly authorized comparison and cannot bypass deterministic
validation or review.

Treatment semantics are fixed before calls: a supported-positive deterministic
retry is run first; a supported-positive local-teacher recommendation skips the
deterministic retry and starts the local ladder; a supported-positive external
recommendation may skip both cheaper rungs; `avoid` skips only the avoided
deterministic retry and continues the normal teacher ladder; and `abstain` uses
the fixed ladder unchanged. If no supported-positive recommendation exists,
the fixed ladder is the conservative fallback. All actions and policy hashes
are recorded as experiment evidence; this does not enable autonomous routing.

## Prerequisites and measurements

Freeze the card bundle and its hash, thresholds, resource order, router hash,
resolution hierarchy, and a fresh reviewed fixture pool before task selection.
First pass the accounting audit for task opportunities, worker attempts, task
rescues, teacher calls, and transport exclusions. Preregister task IDs, novelty and
family labels, validators, model identities, ladder ceilings, transport rules,
and success/cost metrics. Compare final deterministic pass rate, unresolved
count, worker calls, local-teacher calls, external-teacher calls, and tasks
stopping at each tier. Fewer calls are not an improvement if final validated
solve rate falls.

No automatic patch promotion, training, queue insertion, acceptance, or
model-authorized routing is part of this design.

## Readiness gate

Run 3 readiness after the model-free freeze step:

- [x] accounting audit separates task opportunities, worker attempts, rescues,
  teacher calls, and transport exclusions;
- [x] hierarchical evidence outputs are deterministic and provenance-backed;
- [x] router can recommend, avoid, or abstain without execution authority;
- [x] policy and evidence-bundle hashes frozen in review-only artifacts;
- [x] router source and evidence-bundle hashes are available to record at freeze;
- [x] fresh Run 3 tasks were selected only after the policy freeze;
- [x] reviewed_v3 fixtures are satisfiable and preregistered;
- [x] execution order, transport rules, success thresholds, and stop
  conditions are preregistered;
- [x] no Run 3 model calls have occurred.

`RUN_3_ROUTING_POLICY_READY_FOR_FREEZE=true` remains true as an implementation
readiness marker. The experiment is now fully preregistered, but execution and
autonomous routing remain disabled pending operator review.
