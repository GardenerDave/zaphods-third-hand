# Clean Scope-Rule Ladder: 596M, 752M, and 1.7B-Labeled Suppliers

This is an exploratory, matched, descriptive comparison using the same 16
tasks and semantic rule.

| Supplier | Operative params | Effective context | True | False | Overall |
|---|---:|---:|---:|---:|---:|
| Qwen3 | 596049920 | 40960 | 8/8 | 0/8 | 8/16 |
| Qwen3.5 | 752393024 | 40960 | 8/8 | 1/8 | 9/16 |
| Qwen3 1.7B-labeled | 2031739904 | 32768 | 8/8 | 0/8 | 8/16 |

False-branch outcomes: seven tasks failed for all three; one task was
recovered only by 752M; none was recovered only by 1.7B or by both 752M and
1.7B. The true branch was retained at 8/8 for all suppliers.

The measured 1.7B context was capped by the model's native training context,
not by VRAM fit. The frozen probe inputs fit comfortably below 32768, but the
context difference remains a runtime confound. Qwen3 and Qwen3.5 also differ
in architecture and training generation.

Disposition:

```text
SCOPE_CHARACTERIZATION=SCOPE_RULE_SYSTEMATIC_TRUE_BIAS
CLEAN_SCOPE_LADDER=NO_OBSERVED_SCOPE_LADDER
PRACTICAL_SCOPE_BRACKET=NOT_SUPPORTED
NEXT_DECISION=SCOPE_RULE_NOT_SIZE_RESOLVED
```

Bound runs:

- 596M: `/home/navigator/agent-workspace/zaphods-third-hand/.work/model_size_supplier_floor/qwen3_0_6b_clean_scope_logic_probe/run_20260821T025430Z`; aggregate `4525802f61b87da8e069a8f128df3412873b5d41acd6f36be649a83dabaf5f74`
- 752M: `/home/navigator/agent-workspace/zaphods-third-hand/.work/model_size_supplier_floor/qwen3_5_0_8b_clean_scope_logic_probe/run_20260821T031601Z`; aggregate `6b5c1d5689853194d01881c1ec1757346ebe0f75d74a9113b39f281dd9fc9012`
- 1.7B: `.work/model_size_supplier_floor/qwen3_1_7b_clean_scope_logic_probe/run_20260821T034507Z`; aggregate `3697c99121335c8f8d0ebb3a0bbe879b69807666c63b3a0aeb2fc8bdb91e0657`
- Shared task manifest: `f9c91ddb2a886690251a4e8aea5d4c9e41d59c63249e69c720f7c8f29dee382d`
