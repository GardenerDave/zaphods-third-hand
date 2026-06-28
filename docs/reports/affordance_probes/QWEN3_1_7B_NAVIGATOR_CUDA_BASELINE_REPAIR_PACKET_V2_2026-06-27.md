# Affordance Baseline Repair Packet v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Selected lane: `baseline_prompt_context_only`

## Verdict

- Input proposal verdict: `ready_for_repair_decision`
- Input decision verdict: `accepted_for_repair_packet_drafting_only`
- Packet verdict: `ready_for_bounded_repair_application`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Repair scope: `baseline_prompt_suite_and_scorer_only`
- Allowed next step: `apply_baseline_prompt_scorer_repair_packet`
- Rerun required after repair: `true`

## Authorized Target Files

- local_harness/affordance_baseline_execution_packet.py
- local_harness/affordance_baseline_runner.py
- tests/test_affordance_baseline_execution_packet.py
- tests/test_affordance_baseline_runner.py
- docs/experiments/AFFORDANCE_BASELINE_EXECUTION_PACKET_V0.md
- docs/experiments/AFFORDANCE_BASELINE_RUNNER_V0.md

## Authorized Repair Actions

### `strengthen_split_workflow_prompt`

- Scope: `prompt_suite_and_scorer_only`
- Description: Update the structured split-workflow prompt so it requires exact labels: Local host:, Remote host:, Active execution host:, Control rule:, Candidate applies only if:.

### `repair_scorer_false_negatives`

- Scope: `prompt_suite_and_scorer_only`
- Description: Update deterministic scorer acceptance for the reviewed false-negative prompts: `baseline_no_durable_promotion`.

### `update_focused_tests`

- Scope: `tests_only`
- Description: Update focused tests for revised scorer behavior and strengthened split-workflow prompt coverage.

### `update_experiment_docs`

- Scope: `docs_only`
- Description: Update experiment docs to describe the revised baseline prompt/scorer behavior.

## Scorer Repairs

- `baseline_no_durable_promotion`: Accept language that says the run does not apply a LARQL patch, does not train LoRA, and does not perform durable memory/write/promotion.

## Prompt Repairs

- `baseline_split_workflow_active_host`: Replace the prose-only split-workflow prompt with a structured answer form requiring exact labeled lines for local host, remote host, active execution host, control rule, and candidate applicability.
  - Repair type: `structured_prompt_and_scorer_tightening`
  - Required labels:
    - Local host:
    - Remote host:
    - Active execution host:
    - Control rule:
    - Candidate applies only if:

## Required Tests

- python3 -m pytest tests/test_affordance_baseline_execution_packet.py tests/test_affordance_baseline_runner.py
- python3 local_harness/repo_health_check.py
- git diff --check

## Checks

| Check | Passed |
|---|---:|
| `repair_proposal_exists` | `true` |
| `repair_proposal_parses` | `true` |
| `repair_decision_exists` | `true` |
| `repair_decision_parses` | `true` |
| `proposal_selected_lane_baseline` | `true` |
| `decision_selected_lane_baseline` | `true` |
| `selected_lane_matches` | `true` |
| `proposal_promotion_held` | `true` |
| `decision_promotion_held` | `true` |
| `proposal_verdict_ready` | `true` |
| `decision_verdict_accepted` | `true` |
| `accepted_repair_scope_ok` | `true` |
| `runner_code_repair_not_authorized` | `true` |
| `candidate_repair_not_authorized` | `true` |
| `proposal_rerun_required_after_repair` | `true` |
| `decision_rerun_required_after_repair` | `true` |

## Boundary

This is packet only.
No repair is applied by this packet.
The original run verdict remains preserved.
The original review verdict remains preserved.
The original proposal verdict remains preserved.
The original decision verdict remains preserved.
Only the exact target files listed above are authorized.
Only the exact repair actions listed above are authorized.
Runner execution behavior is not authorized for repair.
Candidate repair is not authorized.
This packet is not a LARQL patch.
This packet is not LoRA training.
This packet is not model mutation.
This packet is not durable memory promotion.
This packet is not comparison lane execution.
This packet grants no candidate promotion.
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
- modify_original_decision_report
- modify_candidate
- modify_runner_execution_behavior
- authorize_runner_code_repair
- authorize_candidate_repair
- run_repaired_baseline_without_packet
- commit_or_push

## Notes

- Packet only; no repair is applied.
- Original run, review, proposal, and decision verdicts remain preserved.
- Runner execution behavior is not authorized for repair.
- Candidate repair is not authorized.
- Rerun is required after any accepted repair.
