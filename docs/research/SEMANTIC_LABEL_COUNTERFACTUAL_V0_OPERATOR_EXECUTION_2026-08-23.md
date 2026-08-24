# Operator Execution: Semantic Label Counterfactual V0

This is a frozen, operator-run experiment. Codex must not execute inference.

Authoritative run directory:

The predecessor `bc7aaa5f959bd362456f09b68f951f03dc58d86e` remains preserved as
an unexecuted superseded pre-inference freeze. The authoritative corrected run
is:

`.work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222100Z`

The prepared run contains six paired tasks, 12 planned model calls, zero model
calls, zero tool calls, and zero response files. Verify the driver hash and
response count before execution:

```bash
sha256sum scripts/semantic_label_counterfactual_v0.py
find .work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222000Z \\
  -name response.json -type f -print
```

The response-file command must print nothing. From the normal Dev shell, run:

```bash
source config.env
PYTHONPATH=. python3 scripts/semantic_label_counterfactual_v0.py \\
  --execute \\
  --output-dir .work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222100Z
```

This consumes exactly 12 local 1.7B calls in the frozen A/B, B/A, A/B, B/A,
A/B, B/A order. There are no retries, teacher calls, 30B calls, external
calls, or tool calls. If infrastructure preflight fails before any call and no
response exists, preserve the zero-call state and stop; do not restart after a
response exists.

After execution, verify:

```bash
find .work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222100Z \\
  -name response.json -type f | wc -l
```

Expected count is 12. Close out only after preserving all responses:

```bash
PYTHONPATH=. python3 scripts/semantic_label_counterfactual_v0.py \\
  --closeout \\
  --output-dir .work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222100Z
```

No prompt, definition, enum position, authority, or model setting may be
changed after freeze.
