# Clean Scope-Rule Supplier Comparison: 596M versus Loaded 752M

This descriptive matched comparison uses the same 16-task manifest and frozen
semantic rule. It is exploratory, not confirmatory, and Qwen3 versus Qwen3.5
architecture/training differences remain a confound.

| Supplier | Operative params | Overall | True branch | False branch | Transition result |
|---|---:|---:|---:|---:|---|
| Qwen3-0.6B | 596049920 | 8/16 | 8/8 | 0/8 | systematic true bias |
| Qwen3.5-0.8B | 752393024 | 9/16 | 8/8 | 1/8 | partial false-branch recovery |

Task transitions: BOTH_CORRECT=8,
596M_ONLY_CORRECT=0,
752M_ONLY_CORRECT=1,
BOTH_INCORRECT=7.

The sole 752M-only correction was `clean-scope-007`; seven false-branch tasks
remained incorrect. Both suppliers were 8/8 on the outside-boundary mutation
branch. The observed distinction is therefore a supported supplier bracket,
not a universal parameter floor.

Bound runs:

- 596M: `/home/navigator/agent-workspace/zaphods-third-hand/.work/model_size_supplier_floor/qwen3_0_6b_clean_scope_logic_probe/run_20260821T025430Z`; aggregate `4525802f61b87da8e069a8f128df3412873b5d41acd6f36be649a83dabaf5f74`
- 752M: `.work/model_size_supplier_floor/qwen3_5_0_8b_clean_scope_logic_probe/run_20260821T031601Z`; aggregate `6b5c1d5689853194d01881c1ec1757346ebe0f75d74a9113b39f281dd9fc9012`
- Shared task manifest: `f9c91ddb2a886690251a4e8aea5d4c9e41d59c63249e69c720f7c8f29dee382d`
