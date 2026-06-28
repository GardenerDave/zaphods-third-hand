# Affordance Baseline Repair Packet v0

Status: experimental model-free repair packet

Affordance Baseline Repair Packet v0 turns an accepted baseline
prompt/scorer repair decision into a bounded packet for later repair
application.

This is packet only. It does not call a model, rerun the baseline, modify the
original run report, modify the original review report, modify the original
proposal report, modify the original decision report, apply the repair, patch
runner or scorer code, apply LARQL, train LoRA, mutate model weights, write
durable memory, run a comparison lane, or promote the candidate.

## Purpose

The packet exists after a repair decision reaches:

```text
decision_verdict: accepted_for_repair_packet_drafting_only
accepted_repair_scope: baseline_prompt_suite_and_scorer_only
allowed_next_step: draft_baseline_prompt_scorer_repair_packet
runner_code_repair_authorized: false
candidate_repair_authorized: false
rerun_required_after_repair: true
promotion_verdict: hold_pending_explicit_experiment_approval
```

It records the exact files and repair actions a later bounded repair pass may
apply. It does not apply those changes.

## Inputs

- `baseline_repair_proposal.json`
- `baseline_repair_decision.json`

## Outputs

The helper writes:

```text
baseline_repair_packet.json
baseline_repair_packet.md
```

## Packet verdicts

- `ready_for_bounded_repair_application`
- `not_ready_missing_decision`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Authorized scope

The packet authorizes only baseline prompt-suite and scorer repair drafting
against the listed target files.

The packet mirrors the repair entries present in the repair proposal JSON. That
lets later packets reflect the current proposal shape instead of a frozen
historical list. Older v1-style proposals that omit explicit repair lists still
fall back to the original packet shape.

The target files are limited to:

- `local_harness/affordance_baseline_execution_packet.py`
- `local_harness/affordance_baseline_runner.py`
- `tests/test_affordance_baseline_execution_packet.py`
- `tests/test_affordance_baseline_runner.py`
- `docs/experiments/AFFORDANCE_BASELINE_EXECUTION_PACKET_V0.md`
- `docs/experiments/AFFORDANCE_BASELINE_RUNNER_V0.md`

Authorized repair actions are limited to:

- strengthening the `baseline_split_workflow_active_host` prompt so expected
  answers distinguish local host, remote host, active execution host, and that
  the active host profile controls which affordance applies;
- when the proposal uses `line_separated_structured_prompt_tightening`, the
  packet preserves that exact line-separated answer template and the strict
  scorer instruction instead of collapsing it into generic split-workflow
  wording;
- updating deterministic scorer false-negative handling for the scorer repair
  entries listed in the proposal JSON, whether that is the v2 single
  `baseline_no_durable_promotion` repair or the older v1 reviewer set;
- updating focused tests for that prompt/scorer behavior;
- updating experiment docs to describe the revised behavior.

When a structured split-workflow repair is present, the packet carries the
exact required labels from the proposal:

```text
Local host:
Remote host:
Active execution host:
Control rule:
Candidate applies only if:
```

Runner execution behavior repair is not authorized. Candidate repair is not
authorized.

## Boundary

The original run, review, proposal, and decision verdicts remain preserved.

The packet is not a LARQL patch, not LoRA training, not model mutation, not
durable memory promotion, not comparison-lane execution, and not candidate
promotion.

A rerun is required after any accepted repair.

## Sample command

```bash
python3 local_harness/affordance_baseline_repair_packet.py \
  --repair-proposal .work/affordance_baseline_repair_proposals/navigator_cuda_baseline_v1/baseline_repair_proposal.json \
  --repair-decision .work/affordance_baseline_repair_decisions/navigator_cuda_baseline_v1/baseline_repair_decision.json \
  --out .work/affordance_baseline_repair_packets/navigator_cuda_baseline_v1
```
