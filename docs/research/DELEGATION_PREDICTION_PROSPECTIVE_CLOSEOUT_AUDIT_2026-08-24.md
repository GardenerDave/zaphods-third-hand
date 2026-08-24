# Prospective Delegation Prediction — Final Closeout Audit

## Raw acquisition

The sealed run contains 32 call-start records, 32 terminal responses, 16 local
arms, and 16 external arms. Both arms are present for every frozen case, and
the per-case experiment-authored payload hash matches across arms. Retries,
replays, response repair, tool calls, and evaluator access during acquisition
were zero/false. The raw-response manifest records sealing before evaluation.
The retained `execution_manifest.json` still reports `running`; it was not
rewritten, and the sealed raw-response manifest plus terminal lifecycle are the
authoritative completion records for this audit.

`PROSPECTIVE_RAW_ACQUISITION_INTEGRITY_DEMONSTRATED=true`

## Interim observer event

Commit `3385b9d` was created at 11:39:34 EDT while the one-shot acquisition was
still running. An interim observer therefore classified the run as partial;
the process later completed all 32 opportunities. This was an observation
misclassification, not a supplier retry, replay, or resume. Evaluation had not
started at that point.

The repository HEAD changed during acquisition, but the audit finds no
supplier-input contamination: all payload files had already been materialized,
their hashes remained invariant across arms, local calls used the frozen
payload projection, and external calls ran through the preserved no-tool
wrapper from `/tmp`. No evaluator data, Git metadata, interim report, or
changed repository context was supplied as task input.

## Post-seal scoring correction

The first closeout attempt compared already-array evaluator fields against
extra-wrapped arrays. This occurred after raw sealing, caused no supplier call,
and changed no raw response or evaluator artifact. No erroneous closeout file
was committed. The corrected comparator uses the evaluator arrays directly.

`CLOSEOUT_TARGET_ARRAY_SHAPE_BUG_CORRECTED_POST_SEAL=true`

## Cost and lexicographic hardening

Cost markers now derive from the frozen Run 4 resource-weight artifact. Among
the eight supplier-selection cases: 3 had both suppliers valid, 0 were local-
only, 5 were external-only, and 0 had neither valid. The three capability-
equivalent comparisons favor the lower frozen local expected cost
(16,220.624 ms versus 28,704.012 ms), but cost is tier four and does not rescue
an invalid selection.

The explicit comparison function applies all four tiers. Synthetic tests pass.
The actual winner is decided at tier one, false-positive avoidance; therefore
the result does not depend on cost.

## Stable result

The hardened closeout preserves the prior core result:

- local capability-valid: 5/16;
- external capability-valid: 16/16;
- generalized policy: 16 successful delegations, 0 false positives;
- degeneralized policy: 3 successful delegations, 5 false positives, 8
  unnecessary abstentions;
- winner: `DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED`.

In this prospective, disagreement-enriched bounded scope cohort, the selected
broad aggregate-driven policy produced better delegation decisions than the
tested responsibility/interface-conditioned bounded-evidence policy. This does
not establish representative incidence, universal benchmark superiority,
benchmark invalidity, population superiority, production qualification, or
cross-capability generalization.

No inference, network operation, supplier qualification, or production-routing
change occurred during this hardening pass.

`NEXT_DECISION=DIAGNOSE_BOUNDED_EVIDENCE_TRANSFER_AND_COVERAGE_CALIBRATION`
