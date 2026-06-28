# Affordance Baseline Repair Proposal v0

Status: experimental model-free repair proposal

Affordance Baseline Repair Proposal v0 drafts prompt/scorer repair
recommendations from a completed baseline run and its review record.

This is proposal only. It does not call a model, rerun the baseline, modify
the original run report, modify the original review report, patch runner or
scorer code, apply LARQL, train LoRA, mutate model weights, write durable
memory, run a comparison lane, or promote the candidate.

## Purpose

The proposal exists after a baseline run review recommends:

```text
draft_baseline_prompt_or_scorer_repair
```

It separates likely scorer false negatives from a real prompt/model weakness
so an operator can decide whether to repair the baseline prompt suite, scorer
checks, or both.

## Inputs

- `baseline_lane_result_report.json`
- `baseline_run_review.json`

Both inputs must preserve held promotion and the baseline prompt-context lane.

## Outputs

The helper writes:

```text
baseline_repair_proposal.json
baseline_repair_proposal.md
```

## Proposal verdicts

- `ready_for_repair_decision`
- `not_ready_missing_review`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## v0 repair scope

For the current baseline run shape, the recommended repair scope is:

```text
baseline_prompt_suite_and_scorer_only
```

The proposal recommends scorer repairs for conservative false negatives around
CUDA avoidance, cross-host boundary wording, revalidation/reverify wording, and
no-durable-promotion wording.

It recommends a prompt/scorer repair for the split-workflow active-host prompt
so expected answers explicitly distinguish:

- local host;
- remote host;
- active execution host;
- active host profile controls which affordance applies.

For a second-round split-workflow review where the first louder prose prompt
still leaves the local/remote/active-host distinction weak, v0 may propose a
structured prompt/scorer repair. That repair requires exact labeled lines:

```text
Local host:
Remote host:
Active execution host:
Control rule:
Candidate applies only if:
```

The paired scorer repair should require those labels plus active-host/profile
control language.

For a later v3 review shape where the structured prompt is already present but
the answer template is still too inline, v0 may propose a narrower formatting
repair. That repair replaces the inline structured-label prompt with a literal
line-separated answer template and requires the model to copy the labels
exactly:

```text
Local host:
Remote host:
Active execution host:
Control rule:
Candidate applies only if:
```

The scorer remains strict for the exact labels and active-host/profile control
language. This is a formatting repair, not a scorer relaxation.

The no-durable-promotion scorer repair may accept LoRA wording such as
`train LoRA`, `does not train LoRA`, `not train LoRA`, `no LoRA`, or
`LoRA training` when the answer clearly preserves the no-training boundary.

## Not sufficient conditions

If true failures are present, v0 does not treat scorer relaxation as
sufficient. Candidate or packet repair may be needed before another run.

If model calls, digests, output files, or boundaries were not preserved, v0
does not treat this as a simple prompt/scorer repair.

## Boundary

Repair still requires a separate decision. Rerun is required after any accepted
repair. This proposal does not modify original evidence or apply the repair.

No LARQL, LoRA, model mutation, durable memory, comparison lane, candidate
promotion, commit, or push is authorized by this proposal.

## Sample command

```bash
python3 local_harness/affordance_baseline_repair_proposal.py \
  --run-report .work/affordance_baseline_runs/navigator_cuda_baseline_v1/baseline_lane_result_report.json \
  --run-review .work/affordance_baseline_run_reviews/navigator_cuda_baseline_v1/baseline_run_review.json \
  --out .work/affordance_baseline_repair_proposals/navigator_cuda_baseline_v1
```
