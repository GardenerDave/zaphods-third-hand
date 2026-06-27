# Affordance Experiment Execution Approval v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Repair lane: `larql_plus_lora_candidate`
Recommended experiment type: `larql_plus_lora_comparison`
Selected lane: `baseline_prompt_context_only`

## Verdict

- Approval decision: `approved_for_bounded_lane_execution`
- Approval verdict: `approved_for_baseline_lane_only`
- Execution verdict: `approved_for_baseline_prompt_context_execution_only`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Experiment status: `execution_approval_only`
- Allowed next step: `draft_baseline_prompt_context_execution_packet`

## Operator Note

Approve the baseline prompt-context control lane only. No LARQL patch, LoRA training, comparison lane, durable memory write, or promotion approved.

## Checks

| Check | Passed |
|---|---:|
| `plan_exists` | `true` |
| `plan_parses` | `true` |
| `plan_verdict_ready` | `true` |
| `plan_execution_not_approved` | `true` |
| `plan_promotion_held` | `true` |
| `lane_supported` | `true` |
| `lane_allowed_by_plan` | `true` |
| `lane_is_baseline_prompt_context` | `true` |

## Allowed Actions

- use_existing_candidate_in_prompt_context
- run_bounded_baseline_probe_prompts
- write_baseline_lane_result_report
- write_post_run_audit_report

## Disallowed Actions

- apply_larql_patch
- train_lora_adapter
- mutate_model_weights
- write_durable_memory
- run_larql_lane
- run_lora_lane
- run_comparison_lane
- promote_candidate
- hide_or_drop_source_provenance

## Required Runner Constraints

- no mutation
- no network dependency beyond already configured local endpoint
- fixed prompt suite or explicitly recorded prompt suite digest
- source candidate digest preserved
- write all outputs to .work/
- produce Markdown and JSON result reports
- fail closed on missing provenance or unexpected lane

## Required Pre-Run Artifacts

- execution_approval.json
- experiment_plan.json
- affordance_patch_candidate.json with source digests
- fixed prompt suite or prompt suite digest

## Required Post-Run Artifacts

- baseline_lane_result_report.json
- baseline_lane_result_report.md
- post_run_audit_report.md

## Boundary

This approval record is not a LARQL patch.
This approval record is not LoRA training.
This approval record is not model mutation.
This approval record is not durable memory promotion.
This approval record is not comparison execution.
This approval record grants no candidate promotion.
For v0, approval can cover the baseline lane only.

## Notes

- This records approval status for one bounded lane only.
- Baseline lane approval does not authorize LARQL, LoRA, comparison, durable memory, model mutation, or candidate promotion.
