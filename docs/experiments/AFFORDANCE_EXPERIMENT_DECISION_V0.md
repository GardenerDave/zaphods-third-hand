# Affordance Experiment Decision v0

Status: experimental model-free decision record

Affordance Experiment Decision v0 records an operator decision about an
affordance experiment proposal.

This is not a LARQL patch. It is not LoRA training. It does not mutate model
weights, write durable memory, execute the experiment, or promote the
candidate.

## Purpose

The decision record exists after an affordance experiment proposal has been
generated. It lets an operator approve only the next paperwork step, hold the
proposal for revision, or reject it.

Approval in v0 means only:

```text
approved_to_draft_experiment_plan
```

It does not approve experiment execution.

## Inputs

- `experiment_proposal.json`
- operator decision
- operator note

The proposal should have:

```text
proposal_verdict: ready_for_operator_review
promotion_verdict: hold_pending_explicit_experiment_approval
```

If the proposal is missing, invalid, or not ready, approval to draft a plan
fails closed.

## Outputs

The helper writes:

```text
experiment_decision.json
experiment_decision.md
```

The JSON report records candidate identity, proposal verdict, operator
decision, decision verdict, held promotion verdict, allowed next step,
disallowed actions, required follow-up artifacts, checks, and notes.

## Supported operator decisions

- `approved_to_draft_experiment_plan`
- `held_for_revision`
- `rejected`

## Decision verdicts

- `accepted_for_plan_drafting_only`
- `held_for_revision`
- `rejected`
- `invalid_input`

`promotion_verdict` is always:

```text
hold_pending_explicit_experiment_approval
```

## Boundary

Approval to draft a bounded experiment plan is not approval to execute the
experiment.

This record does not:

- apply LARQL;
- train LoRA;
- mutate a model;
- write durable memory;
- execute an experiment;
- promote a candidate.

Execution still requires a separate explicit approval and follow-up audit
artifacts.

## Sample command

```bash
python3 local_harness/affordance_experiment_decision.py \
  --proposal .work/affordance_experiment_proposals/navigator_cuda_v0/experiment_proposal.json \
  --decision approved_to_draft_experiment_plan \
  --operator-note "Approve drafting a bounded experiment plan only. No LARQL/LoRA execution approved." \
  --out .work/affordance_experiment_decisions/navigator_cuda_v0
```
