# Operator Execution: Semantic Inspect Label Robustness V0

This is a frozen model-free preparation. Do not execute from Codex.

Authoritative predecessor freeze:

`e40ffca5ebaf0a56cbf242c1e5632a0a21197ad9` (unexecuted, superseded
pre-inference analysis omission)

Freeze driver SHA256:

`2deff9cacf71c6d402b51c4347a5d2bb45c93b0cb9f98344c42be334c2d73bfd`

Run directory:

`.work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z`

The run contains 12 fresh tasks, four arms, 48 planned calls, zero model
calls, zero tool calls, and zero response files. Verify before execution:

```bash
sha256sum scripts/semantic_inspect_label_robustness_v0.py
find .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z \\
  -name response.json -type f -print
```

The response command must print nothing. Execute exactly once from the normal
Dev shell:

```bash
source .env.local
```

Read-only endpoint preflight:

```bash
curl -sS --max-time 5 "${ZTH_CAPABILITY_WORKER_BASE_URL}/models" | head
```

Then execute exactly once from the normal Dev shell:

```bash
PYTHONPATH=. python3 scripts/semantic_inspect_label_robustness_v0.py \\
  --execute \\
  --output-dir .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z
```

There are no retries, teacher calls, 30B calls, external calls, or tool calls.
After execution, preserve responses and verify:

```bash
find .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z \\
  -name response.json -type f | wc -l
```

Expected count is 48. Run closeout only after all responses are preserved:

```bash
PYTHONPATH=. python3 scripts/semantic_inspect_label_robustness_v0.py \\
  --closeout \\
  --output-dir .work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z
```
