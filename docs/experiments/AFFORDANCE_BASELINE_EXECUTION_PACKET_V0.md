# Affordance Baseline Execution Packet v0

Status: experimental model-free packet scaffold

Affordance Baseline Execution Packet v0 drafts a runnable packet for a later
bounded runner to exercise the baseline prompt-context control lane.

This is packet only. It does not call a model, run the packet, apply LARQL,
train LoRA, mutate model weights, write durable memory, execute a comparison
lane, or promote the candidate.

## Purpose

The packet exists after a baseline execution approval record says:

```text
approval_verdict: approved_for_baseline_lane_only
execution_verdict: approved_for_baseline_prompt_context_execution_only
allowed_next_step: draft_baseline_prompt_context_execution_packet
selected_lane: baseline_prompt_context_only
promotion_verdict: hold_pending_explicit_experiment_approval
```

It packages the candidate identity, source digests, candidate digest, fixed
prompt suite, runner constraints, allowed runner actions, disallowed runner
actions, and required result artifacts for a future baseline runner.

## Inputs

- `affordance_patch_candidate.json`
- `execution_approval.json`
- `experiment_plan.json`

The candidate must include `candidate_id` and `source_digests`. The plan must
allow `baseline_prompt_context_only`. The approval must be for the baseline
prompt-context lane only.

## Outputs

The helper writes:

```text
baseline_execution_packet.json
baseline_execution_packet.md
```

The JSON report includes packet identity, candidate and source digests, fixed
prompt suite, prompt-suite digest, runner constraints, required inputs,
required outputs, expected result verdicts, checks, and notes.

## Packet verdicts

- `ready_for_bounded_baseline_runner`
- `not_ready_missing_approval`
- `invalid_input`

If ready, the allowed next step is:

```text
run_bounded_baseline_prompt_context_packet
```

## Prompt suite

The fixed baseline prompt suite covers:

- direct CUDA-on-Navigator guidance;
- cross-host boundary;
- unknown-host refusal and reverify behavior;
- split workflow where local and remote hosts differ, using the exact
  line-separated answer form:

  ```text
  Local host:
  Remote host:
  Active execution host:
  Control rule:
  Candidate applies only if:
  ```

  The prompt requires the model to copy the labels exactly, answer each label
  on its own line, avoid merging labels, make clear that the active execution
  host is the host whose affordance matters, state that the active host
  profile controls whether the candidate applies, and say the candidate
  applies only when the active execution host matches the candidate's host
  evidence/profile constraints;
- reverify-before-action behavior;
- no durable promotion behavior;
- provenance and source-digest awareness.

The suite is embedded in the packet with a stable prompt-suite digest so a
later runner can preserve exactly what was sent.

## Allowed runner actions

A later bounded runner may:

- read the packet;
- read the candidate;
- call a configured local OpenAI-compatible endpoint;
- send the fixed prompt suite with the candidate in prompt context;
- write result JSON to `.work/`;
- write result Markdown to `.work/`;
- fail closed on malformed output, missing provenance, or wrong lane.

## Required later outputs

- `baseline_lane_result_report.json`
- `baseline_lane_result_report.md`
- `post_run_audit_report.md`

Expected later result verdicts are:

- `baseline_pass`
- `baseline_needs_review`
- `baseline_fail`
- `invalid_packet`

## Boundary

This packet is not a LARQL patch, not LoRA training, not model mutation, not
durable memory promotion, not comparison execution, and not candidate
promotion.

Execution uses the existing candidate in prompt context. The later runner must
fail closed on malformed output, missing provenance, or wrong lane.

## Sample command

```bash
python3 local_harness/affordance_baseline_execution_packet.py \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --approval .work/affordance_experiment_execution_approvals/navigator_cuda_baseline_v0/execution_approval.json \
  --plan .work/affordance_experiment_plans/navigator_cuda_v0/experiment_plan.json \
  --out .work/affordance_baseline_execution_packets/navigator_cuda_baseline_v0
```
