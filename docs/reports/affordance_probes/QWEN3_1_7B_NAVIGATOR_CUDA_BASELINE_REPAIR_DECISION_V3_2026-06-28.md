# Affordance Baseline Repair Decision v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Selected lane: `baseline_prompt_context_only`

## Verdict

- Input proposal verdict: `ready_for_repair_decision`
- Input recommended repair scope: `baseline_prompt_suite_and_scorer_only`
- Operator decision: `accept_prompt_scorer_repair_for_packet_drafting`
- Decision verdict: `accepted_for_repair_packet_drafting_only`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Accepted repair scope: `baseline_prompt_suite_and_scorer_only`
- Allowed next step: `draft_baseline_prompt_scorer_repair_packet`
- Rerun required after repair: `true`

## Operator Rationale

Accept the v3 proposal for bounded line-separated split-workflow prompt repair packet drafting only. Baseline v3 reached six passing prompts with no scorer false negatives or true failures. The remaining issue is a formatting compliance weakness in baseline_split_workflow_active_host, so the next repair should replace inline labels with a literal line-separated answer template while keeping the exact-label scorer strict.

## Authorization Flags

- Runner code repair authorized: `false`
- Candidate repair authorized: `false`

## Checks

| Check | Passed |
|---|---:|
| `repair_proposal_exists` | `true` |
| `repair_proposal_parses` | `true` |
| `selected_lane_baseline` | `true` |
| `proposal_verdict_ready` | `true` |
| `recommended_repair_scope_ok` | `true` |
| `promotion_held` | `true` |
| `runner_code_repair_not_needed` | `true` |
| `candidate_repair_not_needed` | `true` |
| `rerun_required_after_repair` | `true` |

## Boundary

This is decision only.
The original run verdict remains preserved.
The original review verdict remains preserved.
The original proposal verdict remains preserved.
No repair is applied by this record.
This decision is not a LARQL patch.
This decision is not LoRA training.
This decision is not model mutation.
This decision is not durable memory promotion.
This decision is not comparison lane execution.
This decision grants no candidate promotion.
Repair packet is still required before any code, prompt, or scorer change.
Rerun is required after any accepted repair.

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
- modify_original_proposal_report
- apply_repair_without_packet
- apply_repair_without_decision
- run_repaired_baseline_without_packet
- commit_or_push

## Notes

- Decision only; no repair is applied.
- Original run, review, and proposal verdicts remain preserved.
- Repair packet is still required before any code, prompt, or scorer change.
- Rerun is required after any accepted repair.
