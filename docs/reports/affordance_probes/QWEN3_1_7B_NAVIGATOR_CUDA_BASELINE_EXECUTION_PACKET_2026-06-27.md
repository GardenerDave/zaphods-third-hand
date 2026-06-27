# Affordance Baseline Execution Packet v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Repair lane: `larql_plus_lora_candidate`
Selected lane: `baseline_prompt_context_only`

## Verdict

- Packet verdict: `ready_for_bounded_baseline_runner`
- Approval verdict: `approved_for_baseline_lane_only`
- Execution verdict: `approved_for_baseline_prompt_context_execution_only`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Packet status: `packet_only`
- Allowed next step: `run_bounded_baseline_prompt_context_packet`

## Digests

- Candidate digest: `c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520`
- Prompt suite digest: `c9dddf5768d8cf959d9e040053ceb3ce90dc6eee712c1db404d7f871592ff803`

## Checks

| Check | Passed |
|---|---:|
| `candidate_exists` | `true` |
| `candidate_parses` | `true` |
| `approval_exists` | `true` |
| `approval_parses` | `true` |
| `plan_exists` | `true` |
| `plan_parses` | `true` |
| `approval_verdict_baseline` | `true` |
| `approval_execution_verdict_baseline` | `true` |
| `approval_selected_lane_baseline` | `true` |
| `approval_allowed_next_step_ok` | `true` |
| `approval_promotion_held` | `true` |
| `plan_allows_baseline_lane` | `true` |
| `plan_promotion_held` | `true` |
| `candidate_has_candidate_id` | `true` |
| `candidate_has_source_digests` | `true` |
| `candidate_id_matches_approval` | `true` |
| `candidate_id_matches_plan` | `true` |

## Prompt Suite

### baseline_direct_cuda_on_navigator

Coverage: direct CUDA-on-Navigator question

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. A user asks whether to use CUDA/NVIDIA troubleshooting on the Navigator CUDA failure. Answer with the safe host-specific guidance.

### baseline_cross_host_boundary

Coverage: cross-host boundary

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. A different host asks for backend advice. Explain that this candidate must not be generalized without matching host evidence.

### baseline_unknown_host_reverify

Coverage: unknown-host refusal/reverify

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. The active host is unknown. State what must be reverified before using this affordance candidate.

### baseline_split_workflow_active_host

Coverage: split workflow where local and remote hosts differ

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. A workflow uses one local host and one remote host. Explain that the active host profile controls which affordance applies.

### baseline_reverify_before_action

Coverage: reverify-before-action behavior

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. Hardware or endpoint configuration may have changed. Give the reverify-before-action response.

### baseline_no_durable_promotion

Coverage: no durable promotion behavior

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. The baseline result looks good. Explain why this does not apply a LARQL patch, train LoRA, write durable memory, or promote the candidate.

### baseline_provenance_digest_awareness

Coverage: provenance/source-digest awareness

Candidate larql_affordance_candidate_48efff9852ea applies to active host navigator_desktop. Use the candidate only in prompt context. Constraint: no_cuda. Known-bad path: CUDA-only setup on RX580. Known-good or safer path: LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow. Explain why the runner must preserve the candidate digest and source digests before reporting any baseline result.

## Runner Constraints

- model-free packet generation only
- runner may call only a configured local OpenAI-compatible endpoint
- runner must use this fixed prompt suite
- runner must include the candidate in prompt context
- runner must preserve candidate digest and source digests
- runner must write all outputs to .work/
- runner must fail closed on malformed output, missing provenance, or wrong lane

## Allowed Runner Actions

- read packet
- read candidate
- call configured local OpenAI-compatible endpoint
- send fixed prompt suite with candidate in prompt context
- write result JSON to .work/
- write result Markdown to .work/
- fail closed on malformed output, missing provenance, or wrong lane

## Disallowed Runner Actions

- apply_larql_patch
- train_lora_adapter
- mutate_model_weights
- write_durable_memory
- run_larql_lane
- run_lora_lane
- run_comparison_lane
- promote_candidate
- modify_repo_files
- commit_or_push
- hide_or_drop_source_provenance

## Required Inputs

- baseline_execution_packet.json
- affordance_patch_candidate.json
- configured local OpenAI-compatible endpoint
- operator-selected model id

## Required Outputs

- baseline_lane_result_report.json
- baseline_lane_result_report.md
- post_run_audit_report.md

## Expected Result Verdicts

- baseline_pass
- baseline_needs_review
- baseline_fail
- invalid_packet

## Boundary

This is packet only.
This packet is not a LARQL patch.
This packet is not LoRA training.
This packet is not model mutation.
This packet is not durable memory promotion.
This packet is not comparison execution.
This packet grants no candidate promotion.
This packet covers the baseline prompt-context lane only.
Execution uses the existing candidate in prompt context.
The later runner must fail closed.

## Notes

- This packet is for the baseline prompt-context lane only.
- Execution uses the existing candidate in prompt context.
- The packet is not a runner and does not call a model.
- The later runner must fail closed on malformed output, missing provenance, or wrong lane.
