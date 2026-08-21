# Erratum: Calibrated Clean Scope-Rule Interpretation

This additive erratum supersedes only the interpretation labels in the
matched clean-scope closeout. It does not alter any raw response, task
manifest, validator artifact, aggregate, measured metric, or historical run.

## Corrected disposition

```text
SCOPE_CHARACTERIZATION=SCOPE_RULE_PARTIAL
MATCHED_COMPARISON=PARTIAL_SCOPE_GAIN
PRACTICAL_SCOPE_BRACKET=PARTIAL
NEXT_DECISION=RUN_CLEAN_SCOPE_PROBE_AT_1_7B
```

## Evidence preserved

| Supplier | True branch | False branch | Overall |
|---|---:|---:|---:|
| Qwen3-0.6B / 596M | 8/8 | 0/8 | 8/16 |
| Qwen3.5 / loaded 752M | 8/8 | 1/8 | 9/16 |

The 752M supplier produced one supplier-only correction, `clean-scope-007`,
while seven false-branch tasks remained incorrect. It retained 8/8 true-
branch performance.

This supports a directional improvement over 596M and a partial scope gain.
It does not satisfy the defined meaning of `FALSE_BRANCH_RECOVERY`, which
requires material recovery of the missing branch. One recovered observation
out of eight is insufficient to establish a stable practical supplier bracket.

The one recovered task is not labeled noise. This sample cannot distinguish a
stable supplier improvement from stochastic variation strongly enough to
support the prior stronger label. The loaded 752M supplier remains materially
deficient on the target mechanic.

The exact matched clean probe at the established 1.7B supplier is therefore
more informative than decomposing the single exceptional 752M success.

## Confound and scope

Qwen3 and Qwen3.5 differ in architecture and training generation. The result
is not a pure parameter-count causal comparison and does not establish a
universal model-size threshold. The corrected practical statement is an
observed partial supplier bracket requiring a matched 1.7B comparison.

## Immutable bindings

- 596M run aggregate SHA256: `4525802f61b87da8e069a8f128df3412873b5d41acd6f36be649a83dabaf5f74`
- 752M run aggregate SHA256: `6b5c1d5689853194d01881c1ec1757346ebe0f75d74a9113b39f281dd9fc9012`
- Shared task manifest SHA256: `f9c91ddb2a886690251a4e8aea5d4c9e41d59c63249e69c720f7c8f29dee382d`
- Original matched comparison: `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_CLEAN_SCOPE_596M_VS_752M_2026-08-21.md`
- Original 752M report/matrix remain unchanged.

`MODEL_CALLS_MADE=false` for this correction pass. `RAW_EVIDENCE_CHANGED=false`.
