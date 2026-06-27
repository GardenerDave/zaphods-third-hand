# Affordance Experiment Decision v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Repair lane: `larql_plus_lora_candidate`
Recommended experiment type: `larql_plus_lora_comparison`

## Decision

- Operator decision: `approved_to_draft_experiment_plan`
- Decision verdict: `accepted_for_plan_drafting_only`
- Proposal verdict: `ready_for_operator_review`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Experiment status: `decision_only`
- Allowed next step: `draft_bounded_affordance_experiment_plan`

## Operator Note

Approve drafting a bounded experiment plan only. No LARQL/LoRA execution approved.

## Checks

| Check | Passed |
|---|---:|
| `proposal_exists` | `true` |
| `proposal_parses` | `true` |
| `proposal_verdict_ready` | `true` |
| `proposal_promotion_held` | `true` |
| `proposal_has_recommended_experiment_type` | `true` |

## Boundary

This decision record is not a LARQL patch.
This decision record is not LoRA training.
This decision record is not model mutation.
This decision record is not durable memory promotion.
This decision record is not experiment execution.
This decision record grants no candidate promotion.
Execution still requires a separate explicit approval.

Approval to draft a plan is not approval to execute the experiment.

## Disallowed Actions

- apply_larql_patch
- train_lora_adapter
- mutate_model_weights
- write_durable_memory
- execute_experiment
- promote_candidate
- move_lifecycle_state_without_separate_approval

## Required Follow-Up Artifacts

- bounded_affordance_experiment_plan
- explicit_experiment_execution_approval_record_before_any_execution
- post_experiment_reaudition_report_if_execution_is_later_approved

## Notes

- This records an operator decision about proposal handling only.
- Approval to draft a plan is not approval to execute the experiment.
- Execution still requires a separate explicit approval.
