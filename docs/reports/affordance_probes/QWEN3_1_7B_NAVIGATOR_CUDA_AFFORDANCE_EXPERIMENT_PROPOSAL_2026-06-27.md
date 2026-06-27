# Affordance Experiment Proposal v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Repair lane: `larql_plus_lora_candidate`
Recommended experiment type: `larql_plus_lora_comparison`

## Verdict

- Proposal verdict: `ready_for_operator_review`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Experiment status: `proposal_only`

## Checks

| Check | Passed |
|---|---:|
| `candidate_exists` | `true` |
| `candidate_parses` | `true` |
| `eligibility_report_exists` | `true` |
| `eligibility_report_parses` | `true` |
| `repeatability_report_exists` | `true` |
| `eligibility_verdict_is_eligible` | `true` |
| `eligibility_promotion_held` | `true` |
| `candidate_has_source_digests` | `true` |
| `repair_lane_supported` | `true` |
| `repeatability_total_passes_35_of_35` | `true` |
| `repeatability_no_larql_lora_mutation` | `true` |

## Proposed Experiment

The current candidate is already usable in context.
The proposed experiment is to compare whether LARQL-style patching, LoRA fine-tuning, or both improve behavior without needing the full affordance record in prompt context.
Any injection/training must be explicitly approved separately.

## Preconditions

- Operator has reviewed the candidate, repeatability report, and eligibility report.
- Any injection, training, or durable-memory experiment has separate explicit approval.
- Private endpoint details, host paths, and raw local evidence remain uncommitted unless sanitized.

## Boundaries

- Proposal only; no LARQL patch is applied.
- No LoRA training is started.
- No model weights, adapters, vindexes, or durable memory are mutated.
- No candidate is promoted or accepted by this artifact.
- The current candidate is already usable in prompt context; the experiment asks whether another lane reduces that context burden safely.

This proposal is not a LARQL patch.
This proposal is not LoRA training.
This proposal is not durable memory promotion.
This proposal is not model mutation.
It requires explicit approval before any injection, training, or durable-memory step.

## Success Criteria

- Post-experiment probe suite matches the baseline affordance probe suite.
- Repeatability checks meet or exceed the 35 / 35 prompt-pass baseline.
- No regression on unknown-host, different-host, split-workflow, or reverify prompts.
- Provenance remains attached to any experimental patch or training artifact.

## Failure Criteria

- Any regression, overgeneralization to other hosts, missing provenance, or promotion without review rejects the experiment.
- Any automatic application, training, durable memory write, or lifecycle movement outside explicit approval rejects the experiment.
- Any need to hide or omit source evidence rejects the experiment.

## Post-Experiment Required Audits

- Run the same affordance probe suite after the experiment.
- Run repeatability checks comparable to the 5 clean-run baseline.
- Review outputs for host confusion and overgeneralization.
- Record whether context burden changed without weakening safety boundaries.

Any future experiment requires post-experiment re-audition.

## Rollback / Rejection Rules

- Reject rather than repair in place if provenance is missing.
- Reject if the candidate generalizes host-specific affordances to unsupported hosts.
- Reject if post-experiment probes fail or require waived promotion.
- Keep the original prompt-context candidate as the safe baseline.

## Notes

- The current candidate is already usable in prompt context.
- The proposed experiment compares whether LARQL-style patching, LoRA fine-tuning, or both improve behavior without needing the full affordance record in prompt context.
- Any injection or training must be explicitly approved separately.
