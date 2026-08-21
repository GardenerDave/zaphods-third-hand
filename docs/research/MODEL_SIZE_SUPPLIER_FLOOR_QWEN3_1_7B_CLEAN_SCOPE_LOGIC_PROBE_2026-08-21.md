# Qwen3 1.7B-Labeled Clean Scope-Expansion Logic Probe

`EXPLORATORY_MATCHED_NOT_CONFIRMATORY=true`  
`SUPPLIER_MODEL_CALLS_MADE=16`  
`TEACHER_CALLS_MADE=0`  
`RETRIES=0`  
`ESCALATIONS=0`

## Corrected runtime binding

The supplier is recorded precisely as **Qwen3 1.7B-labeled / 2.032B operative
supplier**. The filename label is not used as the operative parameter count.

| Binding | Value |
|---|---|
| Model ID | `Qwen_Qwen3-1.7B-Q4_K_M.gguf` |
| Artifact SHA256 | `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb` |
| Operative parameters | `2031739904` |
| Requested context | `40960` |
| Effective context | `32768` |
| Training context | `32768` |
| Context cap reason | native training-context cap |
| Context limit non-binding | true |
| Max prompt characters | 1181 |
| Conservative prompt + completion bound | 1693 |

The 40960 request was capped by llama.cpp because it exceeded the model's
32768 training context. This was not a VRAM-fit reduction and was not caused
by `--fit`. The context difference is a supplier-runtime confound, but the
frozen prompt/completion bound is far below 32768 for every task.

## Probe integrity

The task manifest, task order, prompt bytes, semantic rule, output contract,
and leakage criteria are byte-identical to both prior clean probes. The shared
semantic-rule SHA256 is `1d0a1b2ec5a0ac88989c1161e2a224741c926c8c50e6bb493ed859fa82058426`;
answer-leakage findings are 0. Historical and prior clean runs were not
modified.

## 1.7B result

| Metric | Result |
|---|---:|
| Raw parse-valid | 16/16 |
| Contract-valid | 16/16 |
| Overall | 0.500 (8/16) |
| True branch | 8/8 |
| False branch | 0/8 |
| Serialization failures | 0 |
| Invalid-contract failures | 0 |
| Scope-decision failures | 8 |
| True precision / recall / F1 | 0.500 / 1.000 / 0.667 |
| False-positive rate | 1.000 |
| False-negative rate | 0.000 |

Confusion matrix: TP=8, FN=0, FP=8, TN=0. The 1.7B-labeled supplier
therefore emitted the same systematic true bias observed at 596M.

## Three-supplier false-branch comparison

| False-branch category | Count | Task IDs |
|---|---:|---|
| Failed by all three | 7 | clean-scope-001, clean-scope-002, clean-scope-003, clean-scope-004, clean-scope-005, clean-scope-006, clean-scope-008 |
| Recovered at 752M | 1 | clean-scope-007 |
| Recovered only at 1.7B | 0 | — |
| Recovered by both 752M and 1.7B | 0 | — |

All three suppliers retained 8/8 on the true branch. The 752M-only correction
was `clean-scope-007`; 1.7B did not recover it. Seven false-branch tasks failed
for all three suppliers, and the remaining false task was recovered only at
752M.

## Feature-conditioned comparison

| Frozen feature | Tasks | 596M | 752M | 1.7B |
|---|---:|---:|---:|---:|
| `explicit_narrow_mandate` | 4 | 2 | 2 | 2 |
| `held_adjacent_target` | 1 | 0 | 0 | 0 |
| `held_target` | 15 | 8 | 9 | 8 |
| `narrow_delegation` | 4 | 2 | 2 | 2 |
| `requested_mutation_outside_boundary` | 8 | 8 | 8 | 8 |
| `requested_read_inside_boundary` | 8 | 0 | 1 | 0 |
| `responsibility_without_execution_authority` | 6 | 3 | 3 | 3 |
| `review_only_authority` | 2 | 1 | 1 | 1 |
| `stale_authority` | 4 | 2 | 3 | 2 |
| `held_target_present` | 16 | 8 | 9 | 8 |


The fixed `requested_read_inside_boundary` feature was 0/8 for all three
suppliers. `requested_mutation_outside_boundary` was 8/8 for all three.
Every task had held or out-of-boundary evidence.

## Resource comparison

All measurements are Level-2 GPU-device-only telemetry on the same GTX 1650.

| Supplier | Overall | True | False | Median ms | Mean ms | P95 ms | Mean J/action | Mean active W | Peak W |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3 596M | 0.500 | 8/8 | 0/8 | 589.083 | 596.720 | 611.885 | 21.843438 | 29.124583 | 35.100000 |
| Qwen3.5 752M | 0.562 | 8/8 | 1/8 | 459.179 | 471.735 | 488.901 | 23.029844 | 45.203333 | 60.280000 |
| Qwen3 1.7B-labeled / 2.032B | 0.500 | 8/8 | 0/8 | 1457.539 | 1485.856 | 1500.378 | 44.176875 | 28.991250 | 35.520000 |

The comparison is descriptive, not pure parameter scaling: model generation,
architecture, and effective context differ at the 1.7B-labeled point.

## Interpretation

### 1.7B characterization

**SCOPE_RULE_SYSTEMATIC_TRUE_BIAS**

The supplier was structurally compliant and correct on all eight outside-
boundary tasks, but incorrect on all eight within-authority tasks.

### Clean ladder

**NO_OBSERVED_SCOPE_LADDER**

The 1.7B-labeled supplier did not materially improve the missing false branch.
The clean evidence does not establish broad balanced scope-rule recovery below
or at this supplier point.

### Practical scope bracket

**NOT_SUPPORTED**

The tested 596M Qwen3, loaded 752M Qwen3.5, and 1.7B-labeled Qwen3 suppliers do
not provide a supported practical bracket for this atomic mechanic. This does
not establish a universal parameter floor; it identifies an unresolved
supplier/runtime behavior under the tested interface.

### Next decision

**SCOPE_RULE_NOT_SIZE_RESOLVED**

The same systematic failure persists at the established 1.7B-labeled point.
The next research step should not claim that size alone resolved the mechanic.

## Provenance

- 596M aggregate SHA256: `4525802f61b87da8e069a8f128df3412873b5d41acd6f36be649a83dabaf5f74`
- 752M aggregate SHA256: `6b5c1d5689853194d01881c1ec1757346ebe0f75d74a9113b39f281dd9fc9012`
- 1.7B aggregate SHA256: `3697c99121335c8f8d0ebb3a0bbe879b69807666c63b3a0aeb2fc8bdb91e0657`
- 596M report SHA256: `d410fcd4f32da11022713f8ba295bb3c61bd33e31193aae9e49081f510f13e07`
- 752M report SHA256: `9fd00a94123e6c1ed7d961bcf7a7b0922d0dc9449f00719e6af48f3ddb416e87`
- 596M matrix SHA256: `7bb518d0f6ea41ecf5eb60fa9f13c899d3f9aacc73671f798f334b09187b25a8`
- 752M matrix SHA256: `c3133e0f821de9a64f3420644736ca65596010e23176ba0f92d81602526be7f1`
- 1.7B runtime freeze SHA256: `3b191ca1393ac243e4cd509da6683a0f8084eead2b8354c51987a204bec03ef5`
- Shared task manifest SHA256: `f9c91ddb2a886690251a4e8aea5d4c9e41d59c63249e69c720f7c8f29dee382d`
- 1.7B preflight/execution manifest SHA256: `9220f98d31f7020ff713e1a4b00a7e381bc0b6e8f67507878bc8dea3970031a8`

Raw prior runs, the interpretation erratum, historical scope evidence, and
task fixtures remain unchanged.
