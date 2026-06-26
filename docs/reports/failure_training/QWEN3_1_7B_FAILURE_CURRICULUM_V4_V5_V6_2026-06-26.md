# Qwen3-1.7B Failure-Curriculum v4/v5/v6 Comparison

Status: completed evidence summary

## Summary

The v4, v5, and v6 adapter sequence demonstrated a repeatable supervised loop
for turning reviewed small-model failure evidence into measurable improvement
on bounded structured-output behavior.

This is evidence for operator review. It does not promote, approve, route,
rank, assign, or deploy the adapter.

## Scope

Model family:

```text
Qwen3-1.7B
```

Training style:

```text
4-bit base model + LoRA adapter
rank 8
non-thinking mode
masked prompt loss
assistant-target-only training
FP32 trainable LoRA weights
NaN/nonfinite guards
```

Hardware class proven:

```text
NVIDIA GTX 1650 4GB
```

## Measured Behavior

| Run | Validation set | JSON validity | Top-level key match | Exact match | Extra fields | Value type match | Array count match |
|---|---:|---:|---:|---:|---:|---:|---:|
| v4 | 36 rows | 36/36 | 31/36 | 10/36 | not recorded | not recorded | not recorded |
| v5 | 42 rows | 42/42 | 37/42 | 17/42 | 5/42 | 37/42 | 37/42 |
| v6 | 48 rows | 48/48 | 43/48 | 23/48 | 5/48 | 43/48 | 43/48 |

## Interpretation

- v4 produced the JSON-validity breakthrough.
- v5 improved structured precision.
- v6 further improved exact-match and contract-fidelity behavior.

v6 improved general contract fidelity but did not fix the persistent
extra-field/key-substitution attractors.

## Persistent Failures

- `count` → `key1`/`key2`/`key3`
- `blocked` → `key_blocked`
- `accepted` → `key`
- `files_changed` plus source code → `file1` leakage

These failures likely need a different tactic than another small weighted
dataset.

## Current Stopping Point

Pause training after v6.

The sequence proves the supervised failure-curriculum loop. The remaining
failure modes are narrow and stubborn enough that the next useful work is
miss-review, scorer/tooling support, and a different curriculum tactic rather
than immediately launching another adapter run.

## Safety Boundary

This comparison demonstrates supervised guided capability improvement on
bounded structured-output behavior. It does not demonstrate broad independent
project judgment, deployment readiness, or unsupervised model improvement.
