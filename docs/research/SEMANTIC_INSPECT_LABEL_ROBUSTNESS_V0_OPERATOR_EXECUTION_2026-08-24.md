# Operator Execution: Semantic Inspect Label Robustness V0

This is a frozen model-free preparation. Do not execute from Codex.

Freeze driver SHA256:

`c6f5c16e8e418ffc1bbac346b1c5051b00417093e8d6f078603011c5243ae308`

Run directory:

`.work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T021000Z`

The run contains 12 fresh tasks, four arms, 48 planned calls, zero model
calls, zero tool calls, and zero response files. Verify before execution:

```bash
sha256sum scripts/semantic_inspect_label_robustness_v0.py
find .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T021000Z \\
  -name response.json -type f -print
```

The response command must print nothing. Execute exactly once from the normal
Dev shell:

```bash
source config.env
PYTHONPATH=. python3 scripts/semantic_inspect_label_robustness_v0.py \\
  --execute \\
  --output-dir .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T021000Z
```

There are no retries, teacher calls, 30B calls, external calls, or tool calls.
After execution, preserve responses and verify:

```bash
find .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T021000Z \\
  -name response.json -type f | wc -l
```

Expected count is 48. Run closeout only after all responses are preserved:

```bash
PYTHONPATH=. python3 scripts/semantic_inspect_label_robustness_v0.py \\
  --closeout \\
  --output-dir .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T021000Z
```
