# Semantic Property Classification Cross-Model Comparison

## Smaller-Model Availability

- Endpoint: `http://192.168.1.16:8081/v1`
- Exact model identity exposed by the endpoint: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`

## Frozen Equivalence

The frozen 1.7B batch used the same:

- 11 case IDs
- candidate bytes / hashes
- gold bytes / hashes
- queried properties
- evidence IDs
- prompts
- case-specific effective schemas
- status vocabulary
- validation rules
- semantic scoring rules
- temperature `0`
- max completion tokens `64`

Only the endpoint/model identity changed.

## Measurement Summary

- Preregistration commit: `dc4c4a2a5010ebcc291978edb4a2a06195790de9`
- 30B measurement commit: `3c7ca69773a5833adef7306ccbc9ed4e26e0d9ac`
- 1.7B measurement output dir: `.work/semantic_property_classification_20260831_frozen_1p7b`
- Model calls: `11`

## Mechanical Matrix

- Mechanically scored: `11 / 11`
- Mechanically failed: `0 / 11`

## Semantic Comparison

| Case | 30B | smaller model | Gold | Mechanical | Match |
| ---- | --- | ------------- | ---- | ---------- | ----- |
| `p1_semantic_capability_established` | `established` | `established` | `established` | passed | true |
| `p2_transport_not_asserted` | `not_asserted` | `not_established` | `not_asserted` | passed | false |
| `p3_semantic_capability_not_established` | `not_established` | `not_established` | `not_established` | passed | true |
| `p4_transport_established` | `established` | `established` | `established` | passed | true |
| `p5_semantic_capability_not_asserted` | `not_asserted` | `not_asserted` | `not_asserted` | passed | true |
| `p6_transport_established` | `established` | `not_established` | `established` | passed | false |
| `p6_semantic_not_established` | `not_established` | `not_established` | `not_established` | passed | true |
| `a1_semantic_capability` | `established` | `established` | `established` | passed | true |
| `a2_semantic_capability` | `established` | `established` | `established` | passed | true |
| `a3_raw_response_integrity` | `established` | `established` | `established` | passed | true |
| `a3_semantic_acceptance` | `not_established` | `not_established` | `not_established` | passed | true |

### Synthetic

- Exact: `5 / 7`
- Scoreable: `7 / 7`

### Natural

- Exact: `4 / 4`
- Scoreable: `4 / 4`

### Overall

- Exact: `9 / 11`
- Scoreable: `11 / 11`

## Natural A1/A2 Result

The 1.7B matched the 30B on the two frozen natural `semantic_capability` cases:

- A1: `established`
- A2: `established`

It also matched the natural A3 controls.

## Decomposition Result

After decomposition, the frozen natural semantic-classification atom was demonstrated to be within the 1.7B model's capability on this corpus: `4 / 4` exact, including A1 and A2.

The same-model result remains:

- 30B recovery on the decomposed task

## Model-Floor Result

The bundled contract was unreliable on the 30B, while the decomposed contract was reliable on the 30B and remained correct on all frozen natural cases under the 1.7B.

This does **not** establish a lower model-size floor, and it does **not** establish that the 1.7B could perform the earlier bundled task.

## Decomposer Telemetry Seed

Originating bundled task:

- multi-label proposition extraction

Bifurcation signal:

- natural-case failures despite synthetic success

Proposed atomization:

- per-property classification

Prediction lineage:

- decomposition expected to recover A1/A2

Observed 30B outcome:

- recovered, `4 / 4` natural

Observed smaller-model outcome:

- `9 / 11` exact overall; `4 / 4` natural exact

Smaller-model sufficiency was observed after decomposition; pre-decomposition smaller-model requirement remained unmeasured.

## Residual Failures

The two remaining misses were the synthetic transport-context cases:

- `p2_transport_not_asserted`: gold `not_asserted`, observed `not_established`
- `p6_transport_established`: gold `established`, observed `not_established`

These suggest a candidate hypothesis of cross-property polarity interference or negative-clause/status bleed, but that is not yet established.

Possible alternative explanations include:

- lexical association with `not_established`
- recency bias toward the final negative clause
- confusion between `not_asserted` and `not_established`
- property-label semantics
- synthetic phrasing artifacts

## Bifurcation Telemetry

Parent atom:

- per-property semantic classification

Observed bifurcation:

- natural semantic-capability/integrity/acceptance cases: all correct
- simple transport P4: correct
- two transport-context cases: incorrect

Candidate hidden variable:

- distractor / cross-property semantic context

This is a decomposition signal, not proof that a new decomposition is required.

## Limits

- No deterministic checker changes were made.
- No production contract changes were made.
- No before/after 1.7B floor comparison was measured on the bundled task.
- This does not establish a global capability-floor displacement curve.
