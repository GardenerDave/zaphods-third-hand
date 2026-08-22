# Qwen3 1.7B-labeled atomic evidence-projection probe

This fresh exploratory probe reused the frozen independent authorization
factorial. It did not rerun or modify the prior inference, call a teacher, or
create Stage B evidence.

## Binding and correction

The prior operation confusion matrix was audited directly from preserved
scorecards and corrected additively to `TP=4, FN=4, FP=2, TN=6` in
`QWEN3_1_7B_INDEPENDENT_AUTHORIZATION_ATOMS_FACTORIAL_INTERPRETATION_ERRATUM_2026-08-22.md`.

- Task manifest SHA256: `6973c9e4d61eaf647ee846c47ebaf0fa9efffcec6bfc92072f93c349e88874f8`
- Run: `.work/model_size_supplier_floor/qwen3_1_7b_atomic_evidence_projection/run_20260822T023000Z/`
- Run manifest SHA256: `9c1f773f40b542a9c80618ab3c9fd9f26fda98f99eed2f5aafc81c9afdb4d649`
- Candidate: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`, 2,031,739,904 operative parameters
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`

The projected target prompt contained only allowed targets and requested target.
The projected operation prompt contained only allowed operations and requested
operation. Model-free irrelevant-factor leakage was zero in both arms.

## Results

| Projected atom | Correct | True branch | False branch | Parse | Contract | Confusion matrix |
|---|---:|---:|---:|---:|---:|---|
| `target_allowed` | 16/16 | 8/8 | 8/8 | 16/16 | 16/16 | TP=8, FN=0, FP=0, TN=8 |
| `operation_allowed` | 8/16 | 8/8 | 0/8 | 16/16 | 16/16 | TP=8, FN=0, FP=8, TN=0 |

There were zero serialization, contract, or transport failures. The operation
atom emitted `true` on all 16 projected calls; its allowed-operation branch was
perfect while its not-allowed branch was universally incorrect.

## Cross-factor comparison

Target membership was fully invariant after projection:

- latent operation allowed: 8/8;
- latent operation not allowed: 8/8;
- latent held distractor present: 8/8;
- latent held distractor absent: 8/8.

Operation membership was not repaired by projection on its negative branch:

- latent target allowed: 4/8;
- latent target not allowed: 4/8;
- operation allowed: 8/8;
- operation not allowed: 0/8;
- held distractor present: 4/8;
- held distractor absent: 4/8.

Compared with the prior full-evidence operation arm (`10/16`, with
`TP=4,FN=4,FP=2,TN=6`), projection removed the target-conditioned collapse on
the positive operation branch (`0/4` became `4/4` when target was not allowed),
but the projected operation query became universally true on the negative
operation branch.

## Deterministic composition

Using `NOT(observed_target_allowed AND observed_operation_allowed)` without a
new model call produced `12/16` final scope correctness:

- confusion matrix: `TP=8, FN=4, FP=0, TN=4`;
- `TARGET_ALLOWED + OPERATION_ALLOWED`: 4/4;
- `TARGET_ALLOWED + OPERATION_NOT_ALLOWED`: 0/4;
- `TARGET_NOT_ALLOWED + OPERATION_ALLOWED`: 4/4;
- `TARGET_NOT_ALLOWED + OPERATION_NOT_ALLOWED`: 4/4.

The 12 expected-true / 4 expected-false label imbalance is retained; cell
performance is the primary interpretation. The sole weak cell is the
target-allowed / operation-not-allowed cell, caused by the operation atom's
all-true negative branch.

## Interpretation

`PRIMARY_CHARACTERIZATION=ATOMIC_EVIDENCE_PROJECTION_PARTIAL`

Projection materially improved target membership from 13/16 to 16/16 and
removed its latent operation-factor dependence. It did not produce a reliable
operation membership atom: operation allowed was 8/8, but operation not allowed
was 0/8. Therefore projection is informative but does not demonstrate a stable
two-atom architecture.

`ATOMIC_ARCHITECTURE_SUPPORTED_UNDER_PROJECTED_EVIDENCE=false`

The bounded result supports an evidence-firewall effect for target membership,
while leaving operation-query polarity/representation unresolved. It is not a
universal capability claim, parameter floor, or production-routing result.

## Resources and integrity

Level-2 GTX 1650 device-only telemetry at 0.25-second sampling:

| Arm | Median / mean / p95 latency (ms) | Mean / median gross J/action | Total gross J |
|---|---:|---:|---:|
| projected target | 1022.278 / 1032.841125 / 1076.107 | 34.0953125 / 34.57625 | 545.525 |
| projected operation | 958.012 / 806.4891875 / 966.478 | 25.56859375 / 27.0725 | 409.0975 |

Idle baseline: mean 7.379 W, peak 7.4 W, 120 samples over 30.001337 s.
These are GPU-device measurements, not whole-system energy claims.

Execution: 32 supplier calls, 0 teacher calls, 0 retries, 0 escalations.
Prior raw evidence remained unchanged.

## Decision

`NEXT_DECISION=ISOLATE_OPERATION_POSITIVE_BRANCH`

The remaining defect is confined to operation membership selection under the
projected query's negative branch. It should be isolated before any model-size
comparison or production change.
