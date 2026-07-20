# Overnight Dogfood Calibration 2026-07-20

This is the model-free calibration and fixture-validation report for the July 20 hardening pass.

The local endpoint was not used for live calibration in this pass, so the calibration result is based on deterministic fixture validation and static schema checks only.

## Scope

One representative packet family was validated for each of these 12 worker families:

1. `roadmap-grounding`
2. `docs-index-consistency`
3. `dogfood-artifact-validation`
4. `prompt-patch-fixture-review`
5. `candidate-export-rehearsal`
6. `authority-boundary-wording`
7. `evidence-retention`
8. `queue-state-consistency`
9. `closeout-skeleton`
10. `failure-preservation`
11. `evidence-packet-sanity`
12. `review-bundle-completeness`

## Validation Method

- Validated the frozen overnight review schema with the repository validator.
- Preserved raw invalid output and validation diagnostics.
- Checked that controller-derived deadline facts are not delegated to the model.
- Checked that semantic completion requires concrete evidence and valid enums.
- Checked that changed-path claims are restricted to repository-relative targets inside the allowlist.
- Checked that repeated closeout work is treated as terminal-state work, not as a new stage.

## Result

- Live calibration: skipped cleanly because the endpoint was not used.
- Fixture validation: passed for the supported deterministic checks.
- Model output mutation: none.
- Tracked repository mutation: none.

## Findings

- The hardened validator rejects:
  - invented verification keys;
  - invalid enum values;
  - unsupported changed paths;
  - placeholder completion text;
  - deadline claims that contradict controller facts;
  - structurally valid but incomplete review results.
- The pipeline now preserves evidence for failures instead of replacing it.

## Limitations

- This calibration does not prove semantic quality from the model itself.
- It only proves the repository-side contract, status handling, and failure preservation.

## Verification

- `python3 -m py_compile scripts/zth_overnight_dogfood_controller.py scripts/zth_validate_overnight_review_output.py`
- `python3 -m pytest tests/test_long_duration_dogfood_scripts.py -q -k 'overnight_status or overnight_validator or overnight_dry_run'`

## Conclusion

The fixture-validation report confirms the controller and validator now enforce the bounded review contract deterministically, but it does not relabel model failure as semantic success.

