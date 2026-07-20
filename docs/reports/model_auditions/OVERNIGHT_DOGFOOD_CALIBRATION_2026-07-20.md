# Overnight Dogfood Calibration 2026-07-20

This calibration is deterministic and model-free. The live endpoint was not probed for this pass, so the validation artifact records fixture-only executions.

## Result

- Distinct executions preserved: 12
- Live endpoint availability check: not performed
- Tracked repository mutation during calibration: none

## Records

- `roadmap-grounding`: fixture `docs/reports/model_auditions/calibration_roadmap-grounding.json`, expected `ready_for_review`, validator `ready_for_review`, ready_for_review `true`, errors `none`
- `docs-index-consistency`: fixture `docs/reports/model_auditions/calibration_docs-index-consistency.json`, expected `ready_for_review`, validator `ready_for_review`, ready_for_review `true`, errors `none`
- `dogfood-artifact-validation`: fixture `docs/reports/model_auditions/calibration_dogfood-artifact-validation.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `none`
- `prompt-patch-fixture-review`: fixture `docs/reports/model_auditions/calibration_prompt-patch-fixture-review.json`, expected `structure_valid`, validator `structure_valid`, ready_for_review `false`, errors `verification_keys, narrowest_relevant_local_checks_enum`
- `candidate-export-rehearsal`: fixture `docs/reports/model_auditions/calibration_candidate-export-rehearsal.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `deadline_contradiction`
- `authority-boundary-wording`: fixture `docs/reports/model_auditions/calibration_authority-boundary-wording.json`, expected `ready_for_review`, validator `semantic_validation_failed`, ready_for_review `false`, errors `changed_paths_allowlist`
- `evidence-retention`: fixture `docs/reports/model_auditions/calibration_evidence-retention.json`, expected `ready_for_review`, validator `semantic_validation_failed`, ready_for_review `false`, errors `changed_paths_allowlist`
- `queue-state-consistency`: fixture `docs/reports/model_auditions/calibration_queue-state-consistency.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `changed_paths_repo_relative`
- `closeout-skeleton`: fixture `docs/reports/model_auditions/calibration_closeout-skeleton.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `evidence_required`
- `failure-preservation`: fixture `docs/reports/model_auditions/calibration_failure-preservation.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `placeholder_notes`
- `evidence-packet-sanity`: fixture `docs/reports/model_auditions/calibration_evidence-packet-sanity.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `deadline_contradiction`
- `review-bundle-completeness`: fixture `docs/reports/model_auditions/calibration_review-bundle-completeness.json`, expected `semantic_validation_failed`, validator `semantic_validation_failed`, ready_for_review `false`, errors `changed_paths_allowlist`

## Conclusion

The calibration confirms the repository-side contract distinguishes completion, incompletion, malformed output, deadline contradiction, allowlist failure, evidence requirements, and placeholder text without relabeling failure as success.
