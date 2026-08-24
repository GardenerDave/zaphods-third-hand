# Operator Execution: Semantic Label Factorial V0

This is the hardened frozen model-free preparation. Do not execute from Codex.

The predecessor `8e846966876625926e20eafa74ec25058155ed85` and hardened
predecessor `8834ff90162aa296970f38c3ea254afc25c256cd` are preserved as
unexecuted superseded pre-inference freezes. The hardened predecessor's model
evidence is empty; its schedule and model inputs were valid, but its analysis
logic overclaimed interaction. The final successor repairs only that
analysis logic and keeps the frozen evaluator as the sole scoring authority.

Run directory:

`.work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260824T003000Z`

The prepared run contains six tasks, four arms, 24 planned model calls, zero
model calls, zero tool calls, and zero response files. Verify the frozen driver
and zero-response state:

```bash
sha256sum scripts/semantic_label_factorial_v0.py
find .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260824T003000Z \\
  -name response.json -type f -print
```

The response command must print nothing. From the normal Dev shell, execute
only the frozen schedule. The final successor driver SHA256 is
`263c2f3c55e9831587b5ee8a85446bd605c47f9d4b4f5bf57166bddb29285509`.

The exact class-stratified order is:

```text
001 A B C D
002 D C B A
003 B C D A
004 C B A D
005 C D A B
006 B A D C
```

Execute only the frozen schedule:

```bash
source config.env
PYTHONPATH=. python3 scripts/semantic_label_factorial_v0.py \\
  --execute \\
  --output-dir .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260824T003000Z
```

This consumes 24 local 1.7B calls in the prepared Latin-style schedule. There
are no retries, teacher calls, 30B calls, external calls, or tool calls. After
execution, preserve responses and verify:

```bash
find .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260824T003000Z \\
  -name response.json -type f | wc -l
```

Expected count is 24. Run closeout only after all responses are preserved:

```bash
PYTHONPATH=. python3 scripts/semantic_label_factorial_v0.py \\
  --closeout \\
  --output-dir .work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260824T003000Z
```
