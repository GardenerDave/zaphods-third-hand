# Affordance Experiment Execution Approval v0

Status: experimental model-free execution approval record

Affordance Experiment Execution Approval v0 records approval status for one
bounded affordance experiment lane.

This is not a LARQL patch. It is not LoRA training. It does not mutate model
weights, write durable memory, execute an experiment, or promote the
candidate.

## Purpose

The approval record exists after a bounded experiment plan reaches:

```text
plan_verdict: ready_for_execution_approval_review
execution_verdict: not_approved_for_execution
promotion_verdict: hold_pending_explicit_experiment_approval
```

For v0, only the safest control lane can be approved:

```text
baseline_prompt_context_only
```

The LARQL and LoRA lanes deliberately remain unsupported until separate
lane-specific approval support is added.

## Inputs

- `experiment_plan.json`
- selected lane
- approval decision
- operator note

## Outputs

The helper writes:

```text
execution_approval.json
execution_approval.md
```

The JSON report records candidate identity, selected lane, plan verdict,
approval decision, approval verdict, execution verdict, held promotion verdict,
allowed next step, allowed actions, disallowed actions, runner constraints,
required pre-run artifacts, required post-run artifacts, checks, and notes.

## Supported lanes

- `baseline_prompt_context_only`
- `larql_affordance_patch_probe_only`
- `lora_failure_curriculum_candidate_only`

Only `baseline_prompt_context_only` may be approved in v0.

## Supported approval decisions

- `approved_for_bounded_lane_execution`
- `held_for_revision`
- `rejected`

## Approval verdicts

- `approved_for_baseline_lane_only`
- `held_for_revision`
- `rejected`
- `invalid_input`
- `unsupported_lane_requires_separate_approval`

For approved baseline lane execution, `execution_verdict` is:

```text
approved_for_baseline_prompt_context_execution_only
```

For every other case, `execution_verdict` is:

```text
not_approved_for_execution
```

`promotion_verdict` is always:

```text
hold_pending_explicit_experiment_approval
```

## Approved baseline scope

Baseline lane approval allows only:

- use the existing candidate in prompt context;
- run bounded baseline probe prompts;
- write a baseline lane result report;
- write a post-run audit report.

It does not authorize LARQL, LoRA, a comparison lane, durable memory, model
mutation, or candidate promotion.

## Required runner constraints

Any later runner using this approval must:

- perform no mutation;
- depend on no network beyond an already configured local endpoint;
- use a fixed prompt suite or explicitly record the prompt suite digest;
- preserve the source candidate digest;
- write all outputs to `.work/`;
- produce Markdown and JSON result reports;
- fail closed on missing provenance or unexpected lane.

## Boundary

This scaffold records approval status only. It does not run the experiment.

The LARQL and LoRA lanes remain held for later, lane-specific approval support.

## Sample command

```bash
python3 local_harness/affordance_experiment_execution_approval.py \
  --plan .work/affordance_experiment_plans/navigator_cuda_v0/experiment_plan.json \
  --lane baseline_prompt_context_only \
  --approval-decision approved_for_bounded_lane_execution \
  --operator-note "Approve the baseline prompt-context control lane only. No LARQL patch, LoRA training, comparison lane, durable memory write, or promotion approved." \
  --out .work/affordance_experiment_execution_approvals/navigator_cuda_baseline_v0
```
