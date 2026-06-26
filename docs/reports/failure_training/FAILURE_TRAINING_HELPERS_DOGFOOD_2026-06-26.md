# Failure-Training Helper Scripts Dogfood

Status: completed

## Scope

This report records a dogfood pass of the model-free helper scripts added for
the supervised failure-curriculum workflow.

The helper scripts were run against the real v6 failure-curriculum artifacts,
not only test fixtures.

## Inputs

- Dataset: v6_mixed
- Train rows: 177
- Validation rows: 48
- Eval rows: 48
- Base model: Qwen3-1.7B
- Adapter: zth-qwen3-1p7b-failure-curriculum-r8-v6-exact-key-no-extra
- Final eval loss: 1.3099

## Helper Commands Exercised

- validate_jsonl.py
- score_eval_jsonl.py
- extract_non_exact_review.py
- extract_extra_field_review.py
- write_round_report.py

## Validation Result

The mixed v6 training and validation JSONL files passed structural validation
with JSON assistant targets required.

| Split | Rows | Assistant JSON parseable | Assistant non-JSON |
|---|---:|---:|---:|
| Train | 177 | 177 | 0 |
| Validation | 48 | 48 | 0 |

## Evaluation Metrics

| Metric | Base | Adapter |
|---|---:|---:|
| JSON valid | 18/48 | 48/48 |
| Top-level key match | 17/48 | 43/48 |
| Exact match | 3/48 | 23/48 |
| Extra-field rows | 1/48 | 5/48 |
| Type match | 17/48 | 43/48 |
| Array-count match | 18/48 | 43/48 |

## Review Scaffold Results

The non-exact review helper produced 25 review sections.

The extra-field review helper produced 5 review sections. The extra-field rows
matched the previously observed persistent miss classes:

- generic placeholder schema substitution for `{"count": 3}`;
- prefixed-key substitution for `{"blocked": true}`;
- generic key substitution for `{"accepted": false}`;
- source-content leakage after a correct `files_changed` answer.

## Interpretation

The helper scripts reproduced the manual v6 scoring and review workflow on real
artifacts. This validates the helper layer as reusable workflow support for the
failure-curriculum loop.

The result does not change the model boundary. The adapter shows measured
structured-output improvement on this validation split, but remaining failures
still require supervised review and targeted curriculum design.

## Boundary

This report is supervised evidence. It does not establish deployment readiness,
autonomous capability, or authority to deploy the adapter without operator
review.
