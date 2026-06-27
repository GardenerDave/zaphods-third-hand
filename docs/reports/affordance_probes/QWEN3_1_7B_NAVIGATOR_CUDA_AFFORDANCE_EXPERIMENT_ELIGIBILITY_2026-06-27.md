# Affordance Experiment Eligibility v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Repair lane: `larql_plus_lora_candidate`
Host profile ids: `navigator_desktop`

## Verdict

- Eligibility verdict: `eligible_for_experiment_proposal`
- Promotion verdict: `hold_pending_explicit_experiment_approval`
- Recommended next step: `draft_explicit_affordance_experiment_proposal_for_review`

## Checks

| Check | Passed |
|---|---:|
| `candidate_exists` | `true` |
| `candidate_parses` | `true` |
| `candidate_has_candidate_id` | `true` |
| `candidate_has_repair_lane` | `true` |
| `candidate_has_source_digests` | `true` |
| `repair_lane_supported` | `true` |
| `repeatability_report_exists` | `true` |
| `repeatability_clean_7_of_7_5_of_5` | `true` |
| `repeatability_total_passes_35_of_35` | `true` |
| `repeatability_total_needs_review_0_of_35` | `true` |
| `repeatability_no_larql_lora_mutation` | `true` |
| `repeatability_promotion_held` | `true` |

## Boundary

This is eligibility for an experiment proposal only.
It is not a LARQL patch.
It is not LoRA training.
It is not durable memory promotion.
It does not promote, approve, rank, route, or assign the candidate.
Post-injection re-audition would be required for any future experiment.

## Notes

- Eligibility is for a future experiment proposal only.
- No LARQL patch, LoRA training, durable model mutation, or promotion is performed.
