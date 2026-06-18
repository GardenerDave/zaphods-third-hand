# Model Audition Comparison

This report compares existing board capability cards. It does not rerun models and does not assign production roles.

## Input cards

- `cards/qwen25_3b_full_board_smoke.json`
- `cards/qwen25_coder7b_full_board_smoke.json`
- `cards/qwen25_7b_instruct_full_board_smoke.json`

## Overall ranking

| Rank | Model | Board | Overall |
|---:|---|---|---:|
| 1 | `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` | local_baseline_board_v0 | 0.991 |
| 2 | `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M` | local_baseline_board_v0 | 0.981 |
| 3 | `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M` | local_baseline_board_v0 | 0.972 |

## Suite scores

| Model | baseline_micro_v0 | coding_micro_v0 | extraction_micro_v0 | routing_micro_v0 |
| --- | ---: | ---: | ---: | ---: |
| `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` | 0.963 | 1.000 | 1.000 | 1.000 |
| `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M` | 0.925 | 1.000 | 1.000 | 1.000 |
| `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M` | 0.925 | 1.000 | 0.961 | 1.000 |

## Metric averages

| Model | completed | expected_contains | expected_field_match | json_parse | required_keys | runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` | 1.000 | 0.972 | 1.000 | 1.000 | 1.000 | 1.000 |
| `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M` | 1.000 | 0.944 | 1.000 | 1.000 | 1.000 | 1.000 |
| `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M` | 1.000 | 0.907 | 1.000 | 1.000 | 1.000 | 1.000 |

## Runtime

| Model | Total wall time seconds | Median case wall time seconds |
|---|---:|---:|
| `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` | 359.725 | 22.357 |
| `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M` | 367.400 | 23.949 |
| `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M` | 403.221 | 26.872 |

## Failure mode summary

- `expected_contains_missing`: `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`, `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M`

## Notes / caveats

- These are potential fit signals, not production assignments.
- Missing suite or metric scores are shown as absent rather than scored as zero.
- Use constrained follow-up testing before making model-role decisions.
