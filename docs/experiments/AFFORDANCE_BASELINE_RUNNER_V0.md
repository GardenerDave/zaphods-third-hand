# Affordance Baseline Runner v0

Status: experimental bounded endpoint-backed runner

Affordance Baseline Runner v0 consumes a ready baseline prompt-context
execution packet and writes result/audit reports for that baseline control
lane.

It may call only an operator-configured local OpenAI-compatible endpoint. It
does not apply LARQL, train LoRA, mutate model weights, write durable memory,
run LARQL/LoRA/comparison lanes, modify repository files, commit, push, or
promote the candidate.

## Purpose

The runner exists after a packet reaches:

```text
packet_verdict: ready_for_bounded_baseline_runner
allowed_next_step: run_bounded_baseline_prompt_context_packet
packet_type: baseline_prompt_context_only
promotion_verdict: hold_pending_explicit_experiment_approval
```

It verifies the candidate digest and prompt-suite digest, sends the fixed
prompt suite with the candidate in prompt context, and writes reviewable local
evidence.

## Inputs

- `baseline_execution_packet.json`
- `affordance_patch_candidate.json`
- local OpenAI-compatible endpoint URL
- model id

The endpoint URL is used only for the local run. Reports record a redacted
endpoint host rather than the full URL.

## Outputs

The runner writes:

```text
baseline_lane_result_report.json
baseline_lane_result_report.md
post_run_audit_report.md
```

These should be written under `.work/` during operational use.

## Result verdicts

- `baseline_pass`
- `baseline_needs_review`
- `baseline_fail`
- `invalid_packet`

The promotion verdict remains:

```text
hold_pending_explicit_experiment_approval
```

## Fail-closed checks

The runner returns `invalid_packet` without model calls when:

- packet or candidate JSON is missing or invalid;
- packet verdict is not `ready_for_bounded_baseline_runner`;
- selected lane is not `baseline_prompt_context_only`;
- candidate digest does not match the packet;
- prompt-suite digest does not match the packet;
- required disallowed actions are missing.

If any endpoint call fails, the result is `baseline_fail`. If calls succeed
but heuristic checks are weak, the result is `baseline_needs_review`.

The deterministic baseline scorer accepts the reviewed prompt/scorer repair
cases for this lane:

- direct Navigator CUDA answers may pass when they say to avoid CUDA-only setup
  and mention host-specific evidence such as `no_cuda`, `CUDA-only`, `RX580`,
  `AMD`, or `non-NVIDIA`;
- cross-host boundary answers may pass on wording such as “not generalizable to
  other profiles without matching evidence”;
- reverify-before-action answers may use `revalidation` as equivalent to
  `reverify`;
- no-durable-promotion answers may pass when they state that the run does not
  apply a LARQL patch, does not train LoRA, not train LoRA, has no LoRA, or
  mentions LoRA training as a boundary phrase while still preserving the no-
  training boundary, and does not perform durable memory/write/promotion.

The split-workflow prompt now requires the exact labeled answer form:

```text
Local host:
Remote host:
Active execution host:
Control rule:
Candidate applies only if:
```

The prompt tells the model to use a line-separated template, copy the labels
exactly, answer each label on its own line, and avoid merging labels. The
scorer requires those labels plus active-host/profile-control language.
It also accepts active-host applicability phrasing such as:

- `active host is navigator_desktop`
- `constraints (no_cuda) are met`
- `Candidate applies only if: active host is ... and constraints ... are met`

## Boundary

This runner is for the baseline prompt-context lane only.

It does not:

- apply LARQL;
- train LoRA;
- mutate a model;
- write durable memory;
- run a comparison lane;
- promote a candidate;
- modify repo files;
- commit or push.

Passing the baseline runner is evidence only. It does not approve LARQL,
LoRA, durable memory, comparison, or promotion.

## Sample command

```bash
python3 local_harness/affordance_baseline_runner.py \
  --packet .work/affordance_baseline_execution_packets/navigator_cuda_baseline_v0/baseline_execution_packet.json \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --endpoint-url "$ZTH_ENDPOINT_URL" \
  --model-id "$ZTH_MODEL_ID" \
  --out .work/affordance_baseline_runs/navigator_cuda_baseline_v0 \
  --max-tokens 512 \
  --timeout 120
```
