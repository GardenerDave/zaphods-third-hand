# Affordance Baseline Repair Decision v0

Status: experimental model-free decision record

Affordance Baseline Repair Decision v0 records whether a baseline
prompt/scorer repair proposal may move to repair packet drafting.

This is decision only. It does not call a model, rerun the baseline, modify
the original run report, modify the original review report, modify the
proposal report, patch runner or scorer code, apply LARQL, train LoRA, mutate
model weights, write durable memory, run a comparison lane, or promote the
candidate.

## Purpose

The decision exists after a repair proposal reaches:

```text
proposal_verdict: ready_for_repair_decision
recommended_repair_scope: baseline_prompt_suite_and_scorer_only
allowed_next_step: decide_baseline_prompt_scorer_repair
runner_code_repair_needed: false
candidate_repair_needed: false
rerun_required_after_repair: true
promotion_verdict: hold_pending_explicit_experiment_approval
```

It records whether the operator accepts repair packet drafting, rejects the
proposal, or holds for more review.

## Inputs

- `baseline_repair_proposal.json`
- operator decision
- operator rationale

## Outputs

The helper writes:

```text
baseline_repair_decision.json
baseline_repair_decision.md
```

## Allowed decisions

- `accept_prompt_scorer_repair_for_packet_drafting`
- `reject_repair_proposal`
- `hold_for_more_review`

## Decision verdicts

- `accepted_for_repair_packet_drafting_only`
- `rejected_repair_proposal`
- `held_for_more_review`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Accepted scope

An accepted decision allows only:

```text
draft_baseline_prompt_scorer_repair_packet
```

It does not authorize runner code repair, candidate repair, direct prompt or
scorer edits, rerun, LARQL, LoRA, durable memory, comparison, or promotion.

## Boundary

Repair packet drafting is still required before any code, prompt, or scorer
change. Rerun is required after any accepted repair.

This decision preserves the original run, review, and proposal verdicts. It
does not modify original evidence.

## Sample command

```bash
python3 local_harness/affordance_baseline_repair_decision.py \
  --repair-proposal .work/affordance_baseline_repair_proposals/navigator_cuda_baseline_v1/baseline_repair_proposal.json \
  --decision accept_prompt_scorer_repair_for_packet_drafting \
  --operator-rationale "Accept the proposal for bounded prompt/scorer repair packet drafting only. The baseline run had no true failures, preserved digests and boundaries, and identified one split-workflow prompt weakness plus four scorer false negatives." \
  --out .work/affordance_baseline_repair_decisions/navigator_cuda_baseline_v1
```
