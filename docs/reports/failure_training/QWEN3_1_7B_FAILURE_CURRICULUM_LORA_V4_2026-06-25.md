# Qwen3-1.7B ZTH Failure Curriculum Adapter — v4 Result

Adapter: zth-qwen3-1p7b-failure-curriculum-r8-v4-nothink

Training:
- LoRA rank: 8
- Non-thinking mode: yes
- Epochs: 2
- NaN/nonfinite failure: none
- Final eval loss: 1.8110

Held-out sample, n=10:

| Metric | Base | v4 Adapter |
|---|---:|---:|
| JSON valid | 3/10 | 10/10 |
| Top-level key match | 3/10 | 9/10 |
| Exact match | 0/10 | 4/10 |

Conclusion:
The v4 adapter produced a clear behavior-level improvement. It learned raw JSON-only output and substantially improved schema obedience. Remaining failure modes include semantic drift, extra list items, and non-exact phrasing.

## Full validation result

Held-out validation, n=36:

| Metric | Base | v4 Adapter | Lift |
|---|---:|---:|---:|
| JSON valid | 18/36 | 36/36 | +18 |
| Top-level key match | 17/36 | 31/36 | +14 |
| Exact match | 3/36 | 10/36 | +7 |

Conclusion:
The improvement held across the full validation set. The adapter fully corrected raw JSON parseability on this validation split, substantially improved top-level schema obedience, and more than tripled exact-match outputs.

## Boundary

This report is evidence for supervised review. It shows measured improvement in
structured-output behavior on the recorded held-out validation split. It does
not establish production readiness, broad autonomous project understanding, or
authority to deploy the adapter without operator review.
