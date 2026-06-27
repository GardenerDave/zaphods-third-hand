# Affordance Experiment Proposal v0

Status: experimental model-free proposal scaffold

Affordance Experiment Proposal v0 turns an affordance candidate, an
eligibility report, and repeatability evidence into a reviewable proposal for
a future explicit experiment.

This is not a LARQL patch. It is not LoRA training. It does not mutate model
weights, write durable memory, promote a candidate, or approve any experiment.

## Purpose

The proposal artifact exists after a candidate has already passed supervised
probe and eligibility gates. It records what would need to be true before an
operator could separately approve a LARQL-style patch probe, a LoRA
failure-curriculum candidate, or a comparison of both.

The current affordance candidate remains usable in prompt context. The
proposed experiment asks whether LARQL-style patching, LoRA fine-tuning, or
both can improve behavior without requiring the full affordance record in that
prompt context.

## Inputs

- `affordance_patch_candidate.json`
- `eligibility_report.json`
- repeatability report Markdown

The repeatability report must preserve the boundary that no LARQL patch, LoRA
training, or durable model mutation has already occurred.

## Outputs

The helper writes:

```text
experiment_proposal.json
experiment_proposal.md
```

The JSON report includes candidate identity, source digests, eligibility
verdict, proposal verdict, held promotion verdict, experiment type options,
preconditions, boundaries, success/failure criteria, required post-experiment
audits, rollback or rejection rules, and notes.

## Proposal verdicts

- `ready_for_operator_review`
- `not_ready_missing_eligibility`
- `not_ready_invalid_input`

`promotion_verdict` is always:

```text
hold_pending_explicit_experiment_approval
```

## Experiment type options

- `larql_affordance_patch_probe`
- `lora_failure_curriculum_candidate`
- `larql_plus_lora_comparison`

For a `larql_plus_lora_candidate`, v0 recommends
`larql_plus_lora_comparison`.

## Minimum readiness checks

For `ready_for_operator_review`, v0 requires:

- candidate exists and parses;
- eligibility report exists and parses;
- eligibility verdict is `eligible_for_experiment_proposal`;
- eligibility promotion verdict is held;
- candidate has source digests;
- repair lane is `larql_candidate`, `lora_candidate`, or
  `larql_plus_lora_candidate`;
- repeatability report exists;
- repeatability report includes `Total prompt passes: 35 / 35`;
- repeatability report states that no LARQL patch, LoRA training, or durable
  model mutation was applied.

Any failed check keeps the proposal not ready and lists the missing evidence.

## Boundary

This scaffold drafts a proposal only. Any injection, training, durable-memory
write, adapter creation, or LARQL patch application must be explicitly
approved separately.

Post-experiment re-audition must include the same probe suite and repeatability
checks. Any regression, overgeneralization to other hosts, missing provenance,
or promotion without review rejects the experiment.

## Sample command

```bash
python3 local_harness/affordance_experiment_proposal.py \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --eligibility-report .work/affordance_experiment_eligibility/navigator_cuda_v0/eligibility_report.json \
  --repeatability-report docs/reports/affordance_probes/QWEN3_1_7B_NAVIGATOR_CUDA_AFFORDANCE_REPEATABILITY_2026-06-27.md \
  --out .work/affordance_experiment_proposals/navigator_cuda_v0
```
