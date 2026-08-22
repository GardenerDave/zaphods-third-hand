# Independent authorization-atoms factorial interpretation erratum

This additive erratum corrects the operation confusion matrix in the
independent-factorial closeout. The preserved raw responses, validators,
scorecards, telemetry, aggregate, and run files are unchanged.

The operation scorecards were audited directly. The correct matrix is:

`TP=4, FN=4, FP=2, TN=6`.

The two false-positive observations are `independent-atom-004` and
`independent-atom-012`, both expected `operation_allowed=false` but observed
`true`. The previously reported matrix omitted those two false positives and
therefore summed to 14 rather than 16.

The preserved primary characterization remains:

`PRIMARY_CHARACTERIZATION=CROSS_FACTOR_INTERFERENCE_DETECTED`

The architectural wording is bounded as:

`ATOMIC_ARCHITECTURE_NOT_YET_DEMONSTRATED`

This replaces any stronger implication that atomic architecture itself was
false. The full-evidence atom prompts exposed irrelevant factors, and the
operation atom was especially asymmetric by latent target factor. The next
probe therefore tests evidence projection using the same frozen tasks.
