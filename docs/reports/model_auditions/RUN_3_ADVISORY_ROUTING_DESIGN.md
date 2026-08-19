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
and semantic check IDs. The router can recommend a cheaper supported rung or
leave the fixed ladder in place when evidence is only observed/insufficient.
The recommendation is recorded before execution; it does not grant execution
authority and cannot bypass deterministic validation or review.

## Prerequisites and measurements

Freeze the card bundle, thresholds, resource order, router hash, and a fresh
reviewed fixture pool before task selection. Preregister task IDs, novelty and
family labels, validators, model identities, ladder ceilings, transport rules,
and success/cost metrics. Compare final deterministic pass rate, unresolved
count, worker calls, local-teacher calls, external-teacher calls, and tasks
stopping at each tier. Fewer calls are not an improvement if final validated
solve rate falls.

No automatic patch promotion, training, queue insertion, acceptance, or
model-authorized routing is part of this design.
