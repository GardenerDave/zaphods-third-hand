# True semantic fallback V2 successor design

This is a design-only successor to the partially executed V1 run. It is not a
freeze and is not executed by this closeout.

## Purpose

Run a fresh baseline for genuinely unresolved operation-class semantics using
the repaired planner. The successor must distinguish semantic supplier output
from downstream execution coverage and must not reuse the partially consumed V1
holdout.

## Preserved controls

V2 retains:

- neutral repository-relative target names with no semantic class labels;
- runtime/evaluator manifests physically separated;
- one independently authored authority record allowing both
  `observe_presence` and `inspect` for semantic tasks;
- two real safe candidate classes plus `unresolved`;
- enum-only model output containing only `operation_class_candidate`;
- exactly one deterministic target, with target extraction outside the model;
- deterministic eligibility requiring unresolved operation semantics, no risk,
  no ambiguity, and both safe candidates remaining plausible;
- interleaved semantic class order;
- no teacher, no retries, no 30B, no external inference, and no production or
  qualification changes.

## Planner repair

The V1 post-model defect is repaired before any V2 freeze. Optional supplier
records are counted with explicit boolean predicates:

```python
selected_supplier is not None and selected_supplier["supplier_type"] == kind
```

MODEL, TOOL, and DETERMINISTIC_CODE counts therefore remain integers when an
actuator supplier is absent. A correct `inspect` classification must proceed to
`NO_QUALIFIED_EXECUTION_SUPPLIER` and `ready_for_review`; it must not crash.

## Fresh experiment shape

Use a new neutral-target holdout, with balanced and interleaved presence and
inspect paraphrases that do not match the frozen deterministic grammar. Include
deterministic and fail-closed controls. Freeze runtime cases, evaluator cases,
authority, prompts, schema, order, and call budget before inference.

The semantic score is independent of authority, tool availability, terminal
state, and evaluator expectations. A wrong safe class remains semantically
wrong even if downstream containment is safe. A correct inspect class is a
successful semantic/routing result even when execution coverage is incomplete.

## Required V2 checks

Before inference:

- all true-fallback tasks are genuinely eligible;
- runtime authority is identical and class-independent;
- target names are semantically neutral;
- evaluator corruption leaves runtime artifacts unchanged;
- `plan()` returns integer supplier counts for covered and uncovered records;
- no V1 response or remaining V1 task is reused.

Closeout must report semantic classifications separately from execution path
completion and task terminal success. V2 should only claim
`TRUE_SEMANTIC_FALLBACK_DEMONSTRATED` if at least one fresh correct semantic
classification completes the bounded transition without a harness failure.

`NEXT_DECISION=RUN_FRESH_TRUE_SEMANTIC_FALLBACK_BASELINE_WITH_REPAIRED_HARNESS`
