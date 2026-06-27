# Affordance Experiment Plan v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Repair lane: `larql_plus_lora_candidate`
Recommended experiment type: `larql_plus_lora_comparison`
Selected plan lane: `larql_plus_lora_comparison`

## Verdict

- Plan verdict: `ready_for_execution_approval_review`
- Execution verdict: `not_approved_for_execution`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Experiment status: `plan_only`

## Checks

| Check | Passed |
|---|---:|
| `proposal_exists` | `true` |
| `proposal_parses` | `true` |
| `decision_exists` | `true` |
| `decision_parses` | `true` |
| `proposal_verdict_ready` | `true` |
| `decision_verdict_accepted` | `true` |
| `decision_allowed_next_step_ok` | `true` |
| `recommended_experiment_type_exists` | `true` |
| `proposal_promotion_held` | `true` |
| `decision_promotion_held` | `true` |

## Planned Lanes

- baseline_prompt_context_only
- larql_affordance_patch_probe_only
- lora_failure_curriculum_candidate_only

The baseline candidate remains the safe prompt-context version.
No lane is executed by this plan.
LARQL lane, LoRA lane, and any later comparison lane require separate explicit execution approval before running.

## Baseline Artifacts

- affordance_patch_candidate.json
- endpoint_probe_report
- repeatability_probe_report
- eligibility_report.json
- experiment_proposal.json
- experiment_decision.json

## Planned Artifacts

- bounded_experiment_execution_approval_record
- pre_experiment_probe_baseline_snapshot
- post_experiment_probe_report
- post_experiment_repeatability_report
- experiment_closeout_report
- larql_lane_result_report_if_separately_approved
- lora_lane_result_report_if_separately_approved
- comparison_result_report_only_after_separate_approval

## Allowed Inputs

- current affordance candidate and source digests
- held-promotion proposal and decision records
- sanitized repeatability report
- host profile facts already represented in the candidate
- operator-approved experiment execution packet if one is later created

## Pre-Experiment Checks

- Confirm proposal and decision records are still current.
- Confirm promotion and execution remain held.
- Re-run or inspect baseline probe evidence before any separately approved execution.
- Confirm private endpoint details and local paths are not committed.

## Execution Stop Rules

- Stop if explicit execution approval is absent.
- Stop if source provenance is missing or stale.
- Stop if the candidate starts generalizing host-specific affordances to unsupported hosts.
- Stop if any lane requires hidden evidence or unreviewed local output.
- Stop if any step would mutate model weights, durable memory, or LARQL state without separate approval.

## Success Criteria

- Any later approved lane preserves or improves the baseline prompt-context behavior.
- Post-experiment re-audition passes the same probe suite and repeatability checks.
- No unknown-host, different-host, split-workflow, or reverify regression appears.
- All experiment artifacts retain provenance and held-promotion language.

## Failure Criteria

- Any regression, overgeneralization, missing provenance, hidden evidence, or automatic promotion rejects the experiment.
- Any execution without separate explicit approval rejects the experiment.
- Any result that requires weakening host-profile authority rejects the experiment.

## Post-Experiment Required Audits

- Run the same affordance probe suite after any separately approved experiment.
- Run repeatability checks comparable to the clean baseline.
- Compare baseline prompt-context behavior with any LARQL, LoRA, or later comparison lane.
- Record whether context burden changed without weakening boundaries.
- Preserve a closeout report before any future acceptance discussion.

Post-experiment re-audition is required before any result can be accepted.

## Required Execution Approval

- Required: `true`
- Status: `not_granted`
- Allowed by this plan: `false`
- Required record: `explicit_bounded_affordance_experiment_execution_approval`

## Boundary

This plan is not a LARQL patch.
This plan is not LoRA training.
This plan is not model mutation.
This plan is not durable memory promotion.
This plan is not experiment execution.
This plan grants no candidate promotion.
It requires separate execution approval before anything runs.

## Disallowed Actions

- apply_larql_patch
- train_lora_adapter
- mutate_model_weights
- write_durable_memory
- execute_experiment
- promote_candidate
- treat_plan_as_execution_approval
- hide_or_drop_source_provenance

## Notes

- The baseline candidate remains the safe prompt-context version.
- No lane is executed by this plan.
- LARQL, LoRA, and any later comparison lane require separate explicit execution approval.
- Post-experiment re-audition is required before any result can be accepted.
- The comparison lane is intentionally later-only and requires separate approval after bounded LARQL and LoRA lane planning.
