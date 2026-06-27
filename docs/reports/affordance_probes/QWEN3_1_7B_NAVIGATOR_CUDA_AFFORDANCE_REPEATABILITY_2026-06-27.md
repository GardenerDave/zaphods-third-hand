# Qwen3-1.7B Navigator CUDA Affordance Repeatability Probe

Date: 2026-06-27

## Summary

This report repeats the clean v7 endpoint affordance probe configuration to check whether the 7/7 pass is stable across multiple runs.

No LARQL patch, LoRA training, or durable model mutation was applied. The model was given the affordance candidate in context and evaluated with deterministic scoring.

## Configuration

- Candidate: `.work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json`
- Endpoint mode: true
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- qwen_no_think: true
- max_tokens: 256
- Promotion behavior: held for review

## Aggregate result

- Repeat runs found: 5
- Clean 7/7 runs: 5 / 5
- Total prompt passes: 35 / 35
- Total prompt needs_review: 0 / 35

## Per-run results

| Run | Overall verdict | Promotion verdict | Pass | Needs review | Elapsed |
|---|---:|---:|---:|---:|---:|
| run_01 | pass | hold_pending_probe_review | 7 / 7 | 0 / 7 | elapsed_seconds=8.44 |
| run_02 | pass | hold_pending_probe_review | 7 / 7 | 0 / 7 | elapsed_seconds=8.30 |
| run_03 | pass | hold_pending_probe_review | 7 / 7 | 0 / 7 | elapsed_seconds=8.35 |
| run_04 | pass | hold_pending_probe_review | 7 / 7 | 0 / 7 | elapsed_seconds=8.31 |
| run_05 | pass | hold_pending_probe_review | 7 / 7 | 0 / 7 | elapsed_seconds=8.58 |

## Non-pass details

- None. All repeated prompts passed.

## Interpretation

This is a repeatability check for guided capability under supervision. A stable repeat result strengthens the evidence that the shaped host-affordance candidate is usable by the small model when supplied in context.

This remains evidence, not promotion authority. Passing repeat probes does not mean LARQL was applied, LoRA training occurred, or the candidate should be promoted automatically.

## Boundary

The candidate remains held pending review. Any future injection, LARQL patch, LoRA training, or durable memory promotion requires a separate explicit step and post-injection re-audition.
