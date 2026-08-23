# True semantic fallback V2 successor design

This design originated as a design-only successor to the partially executed V1
run. It is now implemented by `scripts/true_semantic_fallback_v2.py` and
frozen model-free by the successor freeze commit. It is not executed by this
closeout.

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

## V2 frozen implementation profile

The frozen matrix contains ten neutral-ID tasks: six genuinely unresolved
semantic tasks in presence/inspect/presence/inspect/presence/inspect order, two
deterministic controls, and two fail-closed controls. Runtime cases contain
only request text and environment authority; expected semantic classes and
terminal expectations are evaluator-only. The V2 prompt and enum are the V1
enum-only baseline interface without V1 failure-specific examples or wording.

V2 directly imports telemetry helpers from
`scripts.zth_qwen3_0_6b_clean_scope_logic_probe`; no compatibility wrapper is
part of the execution path. Supplier-counting uses explicit non-null boolean
predicates, including the uncovered `actuator.inspect` record.

## Superseding provenance correction

The unexecuted predecessor freeze `770db0ef2a5e870a9972af827ed5144e5488fac5`
is preserved and superseded before inference. Its `runtime_cases()` constructed
allowed targets from request parsing and selected some control operation
authority from request wording. This is recorded as a
`PRE_INFERENCE_CONTROL_PLANE_PROVENANCE_DEFECT`, not semantic contamination:

```text
V2_REQUEST_DERIVED_TARGET_AUTHORITY=true
V2_INDEPENDENT_TARGET_AUTHORITY_PROVENANCE=false
V2_CONTROL_OPERATION_AUTHORITY_REQUEST_DERIVED=true
SEMANTIC_CLASS_ANSWER_LEAK_FROM_AUTHORITY=false
SCIENTIFIC_MODEL_EVIDENCE_CONTAMINATED=false
```

The successor uses an explicit task-keyed runtime authority fixture table.
Requests, evaluator classes, regimes, and model output cannot construct or
mutate that table. The six semantic authority values remain the same shared
`["observe_presence", "inspect"]` set. The fresh prepared run is
`.work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z`.
