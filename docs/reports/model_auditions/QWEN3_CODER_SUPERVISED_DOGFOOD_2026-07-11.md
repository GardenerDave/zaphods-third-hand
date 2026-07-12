# Qwen3 Coder Supervised Dogfood

This report summarizes the preserved Qwen3-Coder logic-probe evidence and the
follow-up duration-diagnostic repair. It is evidence, not promotion.

## Evidence progression

| Artifact | Supported result | Notes |
|---|---|---|
| Baseline | 2 pass, 3 mixed, 1 fail | Initial preserved scoring snapshot. |
| Prompt patch v1 | 4 pass, 1 mixed, 1 fail | Behavioral improvement over baseline. |
| Prompt patch v2 | 6 pass, 0 mixed, 0 fail | Exact-contract-compatible prompt outcome. |
| Fresh VM-owned run | 5 pass, 1 false failure | One fixture-backed false failure was later corrected. |
| Authority fixture correction | Corrected | Fixture issue resolved without changing unrelated scoring. |
| Rescored preserved raw evidence | 6 pass, 0 mixed, 0 fail | Same raw evidence rescored with the fixed scorer. |
| Duration diagnostics | Repaired | Duration samples populated from preserved raw elapsed values. |

## Distinctions preserved

- Model behavioral failures are separate from exact-contract mismatches.
- Fixture false positives are separate from model reasoning failures.
- Transport success is separate from scoring success.
- Duration diagnostics are operational evidence, not a quality score.

## Current read

- The preserved Qwen3-Coder evidence supports bounded-role review.
- The evidence does not support autonomous implementation authority.
- The fixed scorer now reports average and maximum duration for preserved raw evidence that includes usable elapsed values.

## Review notes

- Do not treat these results as training data.
- Do not treat these results as a promotion decision.
- Do not overwrite failed or corrected evidence when comparing runs.

## Related evidence

- `.work/model_auditions/logic_probe_runs/qwen3-coder-30b-a3b-20260712_015735/`
- `.work/model_auditions/logic_probe_runs/qwen3-coder-30b-a3b-promptpatch-v1-20260712_021653/`
- `.work/model_auditions/logic_probe_runs/qwen3-coder-30b-a3b-promptpatch-v2-20260712_023305/`
- `.work/model_auditions/logic_probe_runs/qwen3-coder-30b-a3b-promptpatch-v2-20260712_023305-rescored-fixed/`
- `.work/supervised_runs/20260711_duration_gap/`
