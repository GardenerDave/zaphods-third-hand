# Affordance Baseline Run Review v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Selected lane: `baseline_prompt_context_only`

## Verdict

- Input result verdict: `baseline_needs_review`
- Input audit verdict: `audit_needs_review`
- Review verdict: `baseline_review_requires_prompt_repair`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Recommended next step: `draft_baseline_prompt_or_scorer_repair`

## Operator Summary

Baseline run completed with all model calls OK and boundaries preserved. Most review flags are scorer wording false negatives; split workflow active-host answer remains a real weak answer requiring prompt/scorer follow-up.

## Aggregate Review

- `pass_count`: `2`
- `scorer_false_negative_count`: `4`
- `model_weakness_count`: `1`
- `true_failure_count`: `0`
- `not_reviewed_count`: `0`
- `all_model_calls_ok`: `True`
- `digests_verified`: `True`
- `promotion_held`: `True`
- `boundaries_preserved`: `True`

## Prompt Adjudications

| Prompt | Input verdict | Adjudication |
|---|---|---|
| `baseline_direct_cuda_on_navigator` | `needs_review` | `scorer_false_negative` |
| `baseline_cross_host_boundary` | `needs_review` | `scorer_false_negative` |
| `baseline_unknown_host_reverify` | `pass` | `pass` |
| `baseline_split_workflow_active_host` | `needs_review` | `model_weakness` |
| `baseline_reverify_before_action` | `needs_review` | `scorer_false_negative` |
| `baseline_no_durable_promotion` | `needs_review` | `scorer_false_negative` |
| `baseline_provenance_digest_awareness` | `pass` | `pass` |

## Checks

| Check | Passed |
|---|---:|
| `run_report_exists` | `true` |
| `run_report_parses` | `true` |
| `post_run_audit_exists` | `true` |
| `selected_lane_baseline` | `true` |
| `promotion_held` | `true` |
| `candidate_digest_verified` | `true` |
| `prompt_suite_digest_verified` | `true` |

## Boundary

This is review only.
The original run verdict remains preserved.
This review does not modify the original run report.
This review is not a LARQL patch.
This review is not LoRA training.
This review is not model mutation.
This review is not durable memory promotion.
This review is not comparison lane execution.
This review grants no candidate promotion.
Promotion remains held.

## Disallowed Actions

- apply_larql_patch
- train_lora_adapter
- mutate_model_weights
- write_durable_memory
- run_larql_lane
- run_lora_lane
- run_comparison_lane
- promote_candidate
- modify_original_run_report
- commit_or_push

## Notes

- Review only; original run report is not modified.
- Original run verdict remains preserved.
- Promotion remains held.
