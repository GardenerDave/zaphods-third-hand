# Semantic Inspect Label Robustness V0 Closeout

Model-free closeout from preserved raw artifacts. No replay or raw-artifact mutation.

## Provenance

- Freeze commit: `e69c2d3c0470cf7add591471b881fc52d12cc268`
- Frozen driver SHA256: `2deff9cacf71c6d402b51c4347a5d2bb45c93b0cb9f98344c42be334c2d73bfd`
- Run: `.work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z`
- Evaluator source: `SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_EVALUATOR_CASES_2026-08-24.json`
- `qualification_change=false`

## Integrity

| Artifact | Count |
|---|---:|
| `call_started.json` | 48/48 |
| `candidate_validation.json` | 48/48 |
| `power_samples.json` | 48/48 |
| `response.json` | 48/48 |
| `runtime_result.json` | 48/48 |

Lifecycle: `{"model_calls": 48, "model_output_granted_authority": 0, "retries": 0, "runtime_evaluator_influence": 0, "status": "terminal_runtime", "tool_calls": 0}`

All 48 calls were parse-valid, contract-valid, candidate-valid, and candidate-admissible.

## Arm metrics

| Arm | Semantic | Presence | Inspect | Presence outputs | Inspect outputs | Unresolved/rejected |
|---|---:|---:|---:|---:|---:|---:|
| A | 6/12 | 0/6 | 6/6 | 0 | 12 | 0 |
| B | 10/12 | 4/6 | 6/6 | 4 | 8 | 0 |
| C | 9/12 | 6/6 | 3/6 | 9 | 3 | 0 |
| D | 11/12 | 6/6 | 5/6 | 7 | 5 | 0 |

## All pairwise comparisons

| Pair | Output changed | Presence changed | Inspect changed | Overall Δ | Presence Δ | Inspect Δ |
|---|---:|---:|---:|---:|---:|---:|
| A_vs_B | 4/12 | 4/6 | 0/6 | 4 (0.333333) | 4 (0.666667) | 0 (0.000000) |
| A_vs_C | 9/12 | 6/6 | 3/6 | 3 (0.250000) | 6 (1.000000) | -3 (-0.500000) |
| A_vs_D | 7/12 | 6/6 | 1/6 | 5 (0.416667) | 6 (1.000000) | -1 (-0.166667) |
| B_vs_C | 5/12 | 2/6 | 3/6 | -1 (-0.083333) | 2 (0.333333) | -3 (-0.500000) |
| B_vs_D | 3/12 | 2/6 | 1/6 | 1 (0.083333) | 2 (0.333333) | -1 (-0.166667) |
| C_vs_D | 4/12 | 0/6 | 4/6 | 2 (0.166667) | 0 (0.000000) | 2 (0.333333) |

## Replacement-vector and frozen markers

```json
{
  "ALL_REPLACEMENT_CANONICAL_VECTORS_IDENTICAL": false,
  "B_C_CANONICAL_VECTOR_IDENTICAL": false,
  "B_D_CANONICAL_VECTOR_IDENTICAL": false,
  "C_D_CANONICAL_VECTOR_IDENTICAL": false
}
```

```json
{
  "ALL_ARMS_INSPECT_STABLE": false,
  "CLASS_BETA_PRESENCE_IMPROVEMENT": true,
  "CLASS_BETA_SPECIFIC_EFFECT_PLAUSIBLE": false,
  "EXAMINE_TARGET_PRESENCE_IMPROVEMENT": true,
  "HUMAN_READABLE_INSPECT_REPLACEMENT_SUPPORTED": false,
  "INSPECT_LABEL_REPLACEMENT_ROBUSTNESS_DEMONSTRATED": false,
  "LITERAL_INSPECT_LABEL_INTERFERENCE_REPLICATED": false,
  "MULTIPLE_INSPECT_LABEL_REPLACEMENTS_RECOVER_PRESENCE": false,
  "NEUTRAL_LABEL_REPLACEMENT_EFFECT_SUPPORTED": false,
  "OPERATION_TWO_PRESENCE_IMPROVEMENT": true,
  "ORIGINAL_CONTROL_PERFECT_ON_HOLDOUT": false,
  "ORIGINAL_CONTROL_PRESENCE_ERRORS_OBSERVED": true
}
```

## Bounded descriptive interpretation

The original literal `inspect` arm produced 0/6 correct presence decisions while preserving inspect at 6/6. Every replacement improved presence: `class_beta` reached 4/6 while retaining inspect at 6/6; `operation_two` reached 6/6 presence but fell to 3/6 inspect; and `examine_target` reached 6/6 presence but fell to 5/6 inspect. No tested interface achieved 12/12.

Surface-label representation materially changed the semantic decision boundary. The literal `inspect` interface strongly favored inspect decisions on this fresh holdout. Replacements recovered presence to different degrees, with tradeoffs against inspect classification. The stricter frozen composite markers remain false because replacement inspect performance was not uniformly preserved.

The prior factorial Arm A was presence 2/3 and inspect 3/3; this fresh Arm A was presence 0/6 and inspect 6/6. This is descriptive task-set variability, not an IID pooled benchmark.

## Emerging research hypothesis: generic benchmark insufficiency

`GENERIC_BENCHMARK_INSUFFICIENCY_HYPOTHESIS` is an emerging hypothesis, not a
demonstrated general conclusion. The same supplier and bounded semantic
distinction produced materially different observed competence when only the
interface representation changed. This suggests that a generalized
supplier-level benchmark can conceal responsibility-specific and
interface-specific competence.

The candidate ZTH direction is **degeneralizing benchmarks**: progressively
decompose broad benchmark or capability claims into bounded supplier,
capability, interface, authority-context, and evidence units. This does not
make generic benchmarks useless, and this experiment does not establish a
complete benchmark methodology.

## Telemetry

Supplementary descriptive telemetry only; measurement level 2 and boundary `gpu_device_only`. No causal performance inference is made.

| Group | Latency mean ms | Median ms | P95 nearest-rank ms | Energy total J | Mean J | Median J |
|---|---:|---:|---:|---:|---:|---:|
| A | 1115.999 | 1113.050 | 1190.145 | 411.097 | 34.258 | 34.541 |
| B | 1178.687 | 1157.189 | 1255.440 | 445.837 | 37.153 | 35.947 |
| C | 1164.211 | 1166.091 | 1253.592 | 437.400 | 36.450 | 35.399 |
| D | 1175.825 | 1152.898 | 1251.877 | 436.595 | 36.383 | 35.388 |
| overall | 1158.681 | 1148.753 | 1271.796 | 1730.930 | 36.061 | 35.064 |

Per-call hashes for `call_started.json`, `response.json`, `candidate_validation.json`, `runtime_result.json`, and `power_samples.json` are preserved in `SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_MATRIX_2026-08-24.json`.

No qualification or production routing change was made.
