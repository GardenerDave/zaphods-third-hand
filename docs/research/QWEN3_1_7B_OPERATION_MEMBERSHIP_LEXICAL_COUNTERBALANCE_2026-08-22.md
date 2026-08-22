# Qwen3 1.7B-labeled operation-membership lexical counterbalance

This fresh exploratory operation-only probe followed the additive correction of
the evidence-projection next decision. It did not rerun or modify the prior
projection inference and created no Stage B evidence.

## Binding and fixture correction

The projection closeout is corrected additively to
`NEXT_DECISION=ISOLATE_OPERATION_NEGATIVE_BRANCH` in
`QWEN3_1_7B_ATOMIC_EVIDENCE_PROJECTION_INTERPRETATION_ERRATUM_2026-08-22.md`.

The prior projected operation prompt confounded membership with token identity:
inspect/update were always members, archive/delete always non-members. This
probe uses every token in both states.

- Task manifest SHA256: `ff5f72fddea9d003ef7a1a92efc96048435eb94c0933073b058545267d7df29b`
- Run: `.work/model_size_supplier_floor/qwen3_1_7b_operation_membership_lexical_counterbalance/run_20260822T024500Z/`
- Run manifest SHA256: `33ab0e7640adc9df2990b05115b4bce662a375adf4746401e2c5f8c532b97cf4`
- Candidate: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`, 2,031,739,904 operative parameters
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`

Each of inspect, update, archive, and delete occurred twice as a member and
twice as a non-member. Every allowed set had length two and each token occurred
eight times in allowed sets.

## Results

| Measure | Result |
|---|---:|
| Correct | 14/16 |
| MEMBER correct | 8/8 |
| NON_MEMBER correct | 6/8 |
| Parse-valid | 16/16 |
| Contract-valid | 16/16 |
| True selected | 10/16 |
| False selected | 6/16 |
| Confusion matrix | TP=8, FN=0, FP=2, TN=6 |

There were zero serialization, contract, or transport failures.

## Operation-token results

| Requested token | Correct | Member | Non-member | Confusion matrix |
|---|---:|---:|---:|---|
| inspect | 4/4 | 2/2 | 2/2 | TP=2, FN=0, FP=0, TN=2 |
| update | 4/4 | 2/2 | 2/2 | TP=2, FN=0, FP=0, TN=2 |
| archive | 2/4 | 2/2 | 0/2 | TP=2, FN=0, FP=2, TN=0 |
| delete | 4/4 | 2/2 | 2/2 | TP=2, FN=0, FP=0, TN=2 |

Both errors were archive non-member observations emitted as `true`. The same
requested token changed correctly for inspect, update, and delete, but not for
archive.

## Paired analysis

- `BOTH_CORRECT`: 6/8 pairs;
- `MEMBER_ONLY_CORRECT`: 2/8 pairs, both archive pairs;
- `NON_MEMBER_ONLY_CORRECT`: 0/8;
- both same true: 0/8;
- both same false: 0/8.

The matched pairs show that membership state generally controlled the output,
but archive retained a token-specific positive response in its non-member
condition.

## Interpretation

`PRIMARY_CHARACTERIZATION=OPERATION_LEXICAL_EFFECT_DETECTED`

The supplier no longer shows a universal TRUE-selection prior in this probe,
and membership performance is mostly strong. However, the archive-specific
non-member failure means behavior still tracks one operation token more than
membership. This is not clean operation-membership demonstration and does not
support a universal capability or parameter-floor claim.

`ATOMIC_ARCHITECTURE_NOT_YET_DEMONSTRATED`

The projected target atom remains 16/16 from the prior probe, while operation
membership remains short of stable lexical invariance.

## Resources and integrity

Level-2 GTX 1650 device-only telemetry at 0.25-second sampling:

- median / mean / p95 latency: `964.1875 / 828.669125 / 1023.812 ms`;
- mean / median gross energy: `25.22578125 / 26.2575 J/action`;
- total gross energy: `403.6125 J`;
- idle baseline: mean `7.376777 W`, peak `7.41 W`, 121 samples over
  `30.068173 s`.

These are GPU-device measurements, not whole-system energy claims.

Execution was 16 supplier calls, zero teacher calls, retries, and escalations.
Prior evidence remained unchanged.

## Decision

`NEXT_DECISION=REPAIR_OPERATION_MEMBERSHIP_QUERY`

The remaining issue is a token-specific operation-membership error, not a
general TRUE-selection collapse. It should be repaired or isolated before
testing projected composition or changing model size.
