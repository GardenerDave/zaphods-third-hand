# Qwen3 1.7B-labeled independent authorization-atoms factorial

This fresh exploratory probe followed the additive correction in
`QWEN3_1_7B_ATOMIC_SCOPE_RELATION_DECOMPOSITION_INTERPRETATION_ERRATUM_2026-08-22.md`.
It did not rerun or modify the prior 32-call decomposition, and created no Stage
B evidence.

## Binding

- Run: `.work/model_size_supplier_floor/qwen3_1_7b_independent_authorization_atoms_factorial/run_20260822T021800Z/`
- Run manifest SHA256: `99c2bd528b405003da8bd9dedcc8faa9ee78a8b47d7a61574b36f2578a7bb2fb`
- Task manifest SHA256: `6973c9e4d61eaf647ee846c47ebaf0fa9efffcec6bfc92072f93c349e88874f8`
- Candidate: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`, 2,031,739,904 operative parameters
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`

The fresh tasks cross `TARGET_ALLOWED`/`TARGET_NOT_ALLOWED`,
`OPERATION_ALLOWED`/`OPERATION_NOT_ALLOWED`, and held-distractor
presence/absence. Each target×operation cell has four tasks; each full 2×2×2
cell has two tasks. Target and operation factors are independently authored
membership judgments, not target-operation pairs.

The model-free rule was:

`scope_expansion_required = NOT (target_allowed AND operation_allowed)`.

## Atomic results

| Atom | Correct | True branch | False branch | Parse | Contract | Held present | Held absent |
|---|---:|---:|---:|---:|---:|---:|---:|
| `target_allowed` | 13/16 | 5/8 | 8/8 | 16/16 | 16/16 | 5/8 | 8/8 |
| `operation_allowed` | 10/16 | 4/8 | 6/8 | 16/16 | 16/16 | 6/8 | 4/8 |

Target confusion matrix: `TP=5, FN=3, FP=0, TN=8`.

Operation confusion matrix: `TP=4, FN=4, FP=0, TN=6`.

There were zero serialization, contract, or transport failures. All nine atom
errors were semantic judgment failures.

## Cross-factor invariance

Target membership was not invariant to the operation factor:

- target allowed: `5/8` overall; `3/4` when operation was allowed and `2/4`
  when operation was not allowed;
- target not allowed: `8/8` overall and `4/4` in both operation conditions.

Operation membership showed stronger cross-factor interference:

- operation allowed: `4/8` overall; `4/4` when target was allowed but `0/4`
  when target was not allowed;
- operation not allowed: `6/8` overall; `2/4` when target was allowed and
  `4/4` when target was not allowed.

Held-distractor conditioning was also asymmetric: target `5/8` present versus
`8/8` absent; operation `6/8` present versus `4/8` absent. These small cells
are descriptive only.

## Deterministic composition

The derived scope result was `13/16`:

- confusion matrix: `TP=10, FN=2, FP=1, TN=3`;
- `TARGET_ALLOWED + OPERATION_ALLOWED`: `3/4`;
- `TARGET_ALLOWED + OPERATION_NOT_ALLOWED`: `2/4`;
- `TARGET_NOT_ALLOWED + OPERATION_ALLOWED`: `4/4`;
- `TARGET_NOT_ALLOWED + OPERATION_NOT_ALLOWED`: `4/4`.

The natural derived-label distribution was 12 expected true and 4 expected
false; the 13/16 result is therefore not treated as a balanced aggregate
measure. The weakest cell was the allowed-target / disallowed-operation cell,
while the operation atom itself failed completely on the not-allowed-target /
allowed-operation cell.

## Interpretation

`PRIMARY_CHARACTERIZATION=CROSS_FACTOR_INTERFERENCE_DETECTED`

The independent atom design exposed meaningful membership judgments, but neither
atom was sufficiently strong and invariant across the other factor to support
`INDEPENDENT_AUTHORIZATION_ATOMS_DEMONSTRATED`. The operation-type judgment in
particular changed materially with target membership. This is not a clean
demonstration of a stable atomic architecture, and it is not a model-size floor.

`ATOMIC_ARCHITECTURE_SUPPORTED=false`

The prior corrected decomposition remains `BOTH_AUTHORIZATION_ATOMS_PARTIAL`:
it improved direct scope from 8/16 to 13/16, but its old atoms were collinear.
This fresh probe shows that independent membership representation still has
cross-factor interference; the improvement cannot yet be generalized as a
reliable component-plus-composition architecture.

## Resources and integrity

Level-2 GTX 1650 device-only telemetry at 0.25-second sampling:

| Arm | Median / mean / p95 latency (ms) | Mean / median gross J/action | Total gross J |
|---|---:|---:|---:|
| target membership | 1050.37 / 1050.027875 / 1129.628 | 30.7765625 / 29.25875 | 492.425 |
| operation membership | 956.8835 / 966.5319375 / 1097.924 | 29.47328125 / 28.07625 | 471.5725 |

Idle baseline: mean 7.379174 W, peak 7.42 W, 121 samples over 30.058041 s.
These are GPU-device measurements, not whole-system energy claims.

Execution was 32 supplier calls, zero teacher calls, retries, and escalations.
Prior raw evidence remained unchanged.

## Decision

`NEXT_DECISION=REPAIR_ATOMIC_EVIDENCE_REPRESENTATION`

The next step should address the observed cross-factor interference before any
model-size comparison. No production routing change is justified.
