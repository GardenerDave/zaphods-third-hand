# Affordance Experiment Eligibility v0

Status: experimental model-free reporting gate

Affordance Experiment Eligibility v0 reviews one affordance candidate and one
repeatability report to decide whether there is enough evidence to draft a
future LARQL/LoRA experiment proposal.

This is not promotion. It does not apply LARQL, train LoRA, mutate model
weights, write durable memory, or approve a candidate for use.

## Purpose

The gate exists after a candidate has passed supervised endpoint probes. It
checks whether the recorded evidence is strong enough to justify a separate
experiment proposal.

## Inputs

- `affordance_patch_candidate.json`
- repeatability report Markdown

The repeatability report must record clean repeated probe results and preserve
the boundary that no LARQL patch, LoRA training, or durable model mutation was
applied.

## Outputs

The helper writes:

```text
eligibility_report.json
eligibility_report.md
```

The JSON report includes the candidate id, repair lane, source failure id, host
profile ids, source digests, checks, eligibility verdict, promotion verdict,
recommended next step, and notes.

## Eligibility checks

For `eligible_for_experiment_proposal`, v0 requires:

- candidate exists and parses;
- candidate has `candidate_id`;
- candidate has `repair_lane`;
- candidate has `source_digests`;
- repair lane is `larql_candidate`, `lora_candidate`, or
  `larql_plus_lora_candidate`;
- repeatability report exists;
- repeatability report includes:
  - `Clean 7/7 runs: 5 / 5`;
  - `Total prompt passes: 35 / 35`;
  - `Total prompt needs_review: 0 / 35`;
  - `No LARQL patch, LoRA training, or durable model mutation was applied`;
  - held-promotion wording.

Any failed check keeps the candidate not eligible until evidence is completed.

## Verdicts

- `eligible_for_experiment_proposal`
- `not_eligible_needs_more_evidence`
- `not_eligible_invalid_input`

`promotion_verdict` is always:

```text
hold_pending_explicit_experiment_approval
```

## Boundary

Eligibility means only that an operator may draft a future explicit experiment
proposal for review. It is not a LARQL patch, not LoRA training, not durable
memory promotion, and not approval to inject anything.

Any future experiment would require explicit approval and post-injection
re-audition.

## Sample command

```bash
python3 local_harness/affordance_experiment_eligibility.py \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --repeatability-report docs/reports/affordance_probes/QWEN3_1_7B_NAVIGATOR_CUDA_AFFORDANCE_REPEATABILITY_2026-06-27.md \
  --out .work/affordance_experiment_eligibility/navigator_cuda_v0
```
