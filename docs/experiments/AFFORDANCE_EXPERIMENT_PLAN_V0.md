# Affordance Experiment Plan v0

Status: experimental model-free plan scaffold

Affordance Experiment Plan v0 drafts a bounded experiment plan from a ready
proposal and an accepted operator decision record.

This is not a LARQL patch. It is not LoRA training. It does not mutate model
weights, write durable memory, execute an experiment, or promote the
candidate.

## Purpose

The plan exists after an operator has approved only this next paperwork step:

```text
draft_bounded_affordance_experiment_plan
```

It defines what a future execution-approval reviewer would need to inspect
before any LARQL lane, LoRA lane, or later comparison lane could run.

## Inputs

- `experiment_proposal.json`
- `experiment_decision.json`

The proposal should have:

```text
proposal_verdict: ready_for_operator_review
promotion_verdict: hold_pending_explicit_experiment_approval
```

The decision should have:

```text
decision_verdict: accepted_for_plan_drafting_only
allowed_next_step: draft_bounded_affordance_experiment_plan
promotion_verdict: hold_pending_explicit_experiment_approval
```

## Outputs

The helper writes:

```text
experiment_plan.json
experiment_plan.md
```

The JSON report records candidate identity, proposal and decision verdicts,
held promotion and execution verdicts, allowed lanes, selected plan lane,
baseline artifacts, planned artifacts, allowed inputs, disallowed actions,
pre-experiment checks, stop rules, success/failure criteria, required audits,
execution-approval requirements, checks, and notes.

## Plan verdicts

- `ready_for_execution_approval_review`
- `not_ready_missing_decision`
- `invalid_input`

`execution_verdict` is always:

```text
not_approved_for_execution
```

`promotion_verdict` is always:

```text
hold_pending_explicit_experiment_approval
```

## Lanes

For `larql_plus_lora_comparison`, v0 defines bounded lanes:

- `baseline_prompt_context_only`
- `larql_affordance_patch_probe_only`
- `lora_failure_curriculum_candidate_only`

The comparison lane is intentionally later-only. It requires separate
execution approval after the bounded LARQL and LoRA lane plan is reviewed.

The baseline candidate remains the safe prompt-context version. No lane is
executed by this plan.

## Boundary

This scaffold drafts a plan only.

It does not:

- apply LARQL;
- train LoRA;
- mutate a model;
- write durable memory;
- execute an experiment;
- promote a candidate.

LARQL lane, LoRA lane, and any later comparison lane require separate explicit
execution approval before running.

Post-experiment re-audition is required before any result can be accepted. Any
regression, overgeneralization, missing provenance, hidden evidence, or
automatic promotion rejects the experiment.

## Sample command

```bash
python3 local_harness/affordance_experiment_plan.py \
  --proposal .work/affordance_experiment_proposals/navigator_cuda_v0/experiment_proposal.json \
  --decision .work/affordance_experiment_decisions/navigator_cuda_v0/experiment_decision.json \
  --out .work/affordance_experiment_plans/navigator_cuda_v0
```
