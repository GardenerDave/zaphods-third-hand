# Affordance Baseline Repair Proposal v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Selected lane: `baseline_prompt_context_only`

## Verdict

- Input result verdict: `baseline_needs_review`
- Input review verdict: `baseline_review_requires_prompt_repair`
- Proposal verdict: `ready_for_repair_decision`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Recommended repair scope: `baseline_prompt_suite_and_scorer_only`
- Allowed next step: `decide_baseline_prompt_scorer_repair`
- Rerun required after repair: `true`

## Scorer False-Negative Repairs

- none

## Prompt Weakness Repairs

### baseline_split_workflow_active_host

Repair type: `line_separated_structured_prompt_tightening`

Replace the inline structured-label prompt with a literal line-separated answer template and require the model to copy the labels exactly.

Scorer requirement: Keep the exact-label scorer strict; do not loosen scorer.

Required labels:

- Local host:
- Remote host:
- Active execution host:
- Control rule:
- Candidate applies only if:


## Repair Flags

- Runner code repair needed: `false`
- Candidate repair needed: `false`

## Checks

| Check | Passed |
|---|---:|
| `run_report_exists` | `true` |
| `run_report_parses` | `true` |
| `run_review_exists` | `true` |
| `run_review_parses` | `true` |
| `selected_lane_baseline` | `true` |
| `run_promotion_held` | `true` |
| `review_promotion_held` | `true` |
| `review_verdict_requests_repair` | `true` |
| `true_failure_count_zero` | `true` |
| `digests_verified` | `true` |
| `boundaries_preserved` | `true` |

## Boundary

This is proposal only.
The original run verdict remains preserved.
The original review verdict remains preserved.
This proposal does not modify the original run report.
This proposal does not modify the original review report.
This proposal is not a LARQL patch.
This proposal is not LoRA training.
This proposal is not model mutation.
This proposal is not durable memory promotion.
This proposal is not comparison lane execution.
This proposal grants no candidate promotion.
Repair still requires a separate decision.
Rerun is required after repair.

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
- modify_original_review_report
- apply_repair_without_decision
- commit_or_push

## Notes

- Proposal only; original run and review reports are not modified.
- Repair still requires a separate decision.
- Rerun is required after any accepted repair.
