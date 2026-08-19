# Proposed Run 3: Advisory Routing Cost Experiment

Status: design only; no Run 3 tasks or model calls have been created.

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

The future treatment uses the same bounded interventions, but consults a frozen
advisory policy keyed by task family plus normalized baseline failed structural
and semantic check IDs. Evidence resolution must be frozen as exact signature,
semantic signature, deterministic failure class, or task family, in that order.
The router can recommend a cheaper supported rung, mark supported-negative
evidence as avoid, or abstain when no supported-positive evidence exists. A
broader recommendation must retain the more-specific evidence in its packet.
The recommendation is recorded before execution; it does not grant execution
authority and cannot bypass deterministic validation or review.

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

Current implementation readiness, before any policy freeze or task selection:

- [x] accounting audit separates task opportunities, worker attempts, rescues,
  teacher calls, and transport exclusions;
- [x] hierarchical evidence outputs are deterministic and provenance-backed;
- [x] router can recommend, avoid, or abstain without execution authority;
- [ ] policy and evidence-bundle hashes frozen by operator review;
- [x] router source and evidence-bundle hashes are available to record at freeze;
- [x] fresh Run 3 tasks have not been selected.

`RUN_3_ROUTING_POLICY_READY_FOR_FREEZE=true` means the implementation is ready
for that explicit review/freeze step. It does not mean Run 3 is authorized or
that routing execution is enabled.
