# Operator Execution: Semantic Label Factorial V0

This is a frozen model-free preparation. Do not execute from Codex.

Run directory:

`.work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T230100Z`

The prepared run contains six tasks, four arms, 24 planned model calls, zero
model calls, zero tool calls, and zero response files. Verify the frozen driver
and zero-response state:

```bash
sha256sum scripts/semantic_label_factorial_v0.py
find .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T230100Z \\
  -name response.json -type f -print
```

The response command must print nothing. From the normal Dev shell, execute
only the frozen schedule:

```bash
source config.env
PYTHONPATH=. python3 scripts/semantic_label_factorial_v0.py \\
  --execute \\
  --output-dir .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T230100Z
```

This consumes 24 local 1.7B calls in the prepared Latin-style schedule. There
are no retries, teacher calls, 30B calls, external calls, or tool calls. After
execution, preserve responses and verify:

```bash
find .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T230100Z \\
  -name response.json -type f | wc -l
```

Expected count is 24. Run closeout only after all responses are preserved:

```bash
PYTHONPATH=. python3 scripts/semantic_label_factorial_v0.py \\
  --closeout \\
  --output-dir .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T230100Z
```
