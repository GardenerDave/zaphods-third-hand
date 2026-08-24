# Operator Execution: Semantic Enum Order Counterfactual V0

This is a frozen, operator-run experiment. Codex did not execute inference.

Run directory:

`.work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T203000Z`

The prepared run must contain six task pairs, 12 planned calls, zero response
files, and zero tool calls before execution. Verify the frozen driver and
prepared artifacts before starting:

```bash
sha256sum scripts/semantic_enum_order_counterfactual_v0.py
find .work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T203000Z \\
  -name response.json -type f -print
```

The response-file command must print nothing. Do not use a compatibility
wrapper. From the normal Dev shell, execute exactly:

```bash
source config.env
PYTHONPATH=. python3 scripts/semantic_enum_order_counterfactual_v0.py \\
  --execute \\
  --output-dir .work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T203000Z
```

This consumes exactly 12 local 1.7B calls: six tasks in each enum-order arm.
There are no retries, teacher calls, 30B calls, external calls, or tool calls.
If preflight fails before any call and no response artifact exists, preserve the
zero-call state and stop for operator review; do not restart after a response
exists.

After execution, verify the response count:

```bash
find .work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T203000Z \\
  -name response.json -type f | wc -l
```

Expected count is 12. Run the driver closeout only after all responses are
preserved:

```bash
PYTHONPATH=. python3 scripts/semantic_enum_order_counterfactual_v0.py \\
  --closeout \\
  --output-dir .work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T203000Z
```

The freeze commit is the commit containing this document, the driver, the
fresh manifests, and the prepared run. The exact driver SHA256 is recorded in
`router_manifest.json` and must match the operator's preflight hash.
