# Semantic fallback necessity audit

This model-free audit preserves the six historical fallback calls from the
deterministic-first and corrected-confirmation runs. It does not replay or
rescore them.

## Finding

All six requests have one safely extractable repository target and are already
classified as `PRESENCE_OBSERVATION_CONTEXT`. The historical `model_required`
decision was caused by the first-token wrapper rule: `could`, `please`, `can`,
and `would` were recognized as context cues but not as operation leads.

Under the conservative counterfactual rule—presence context, exactly one
target, and no ambiguity or risky/unsupported operation—the canonical operation
is uniquely `observe_presence` before the model call for **6/6** cases.

Therefore:

- `POLITE_WRAPPER_PRESENCE_MODEL_NECESSITY=false`
- `SEMANTIC_FALLBACK_REQUIREMENT_WAS_SYNTACTICALLY_INDUCED=true`
- `TRUE_SEMANTIC_FALLBACK_NOT_YET_DEMONSTRATED=true`
- `FALLBACK_BRANCH_EXECUTION_DEMONSTRATED=true`
- `ADDITIONAL_MODEL_CALLS_COUNTERFACTUALLY_AVOIDABLE=6`

The historical six model calls remain actual resource evidence. This projection
does not alter them. It shows that the model restated, varied, or failed to
provide a fact that deterministic context already supplied.

## Safety precedence

The proposed refinement rejects ambiguity first, then unsupported/risky
operation language, then requires presence context and one target. The
model-free negative audit covers multi-operation, mutation, archive/delete,
multiple-target, no-target, and unknown-context cases; all remain unresolved or
fail closed.

## Real fallback boundary

Future routing should be:

```text
deterministic derivation
  -> canonical operation uniquely resolved: no model
  -> otherwise, one safe target + no ambiguity/risk + bounded semantic supplier:
       request only the unresolved operation fact
  -> otherwise: ready_for_review
```

The model must not decide whether it should be called, select a tool, or grant
authority. A future true-fallback holdout should contain deterministic presence
cases, genuinely unresolved but bounded operation language, and fail-closed
cases. It should not manufacture model necessity by hiding an operation phrase
behind polite syntax.

The full six-case matrix, preserved raw-response references, post-model
normalization, authority projection, and negative-case audit are in the
[audit matrix](SEMANTIC_FALLBACK_NECESSITY_AUDIT_MATRIX_2026-08-23.json).

No model, teacher, 30B, tool, external, retry, production, or qualification
action occurred during this audit. `NEXT_DECISION=TEST_TRUE_SEMANTIC_FALLBACK_ON_GENUINELY_UNRESOLVED_OPERATION_LANGUAGE`.
