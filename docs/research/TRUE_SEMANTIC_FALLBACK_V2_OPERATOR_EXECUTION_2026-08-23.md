# True semantic fallback V2 operator execution

This document is execution instructions only. The V2 freeze is model-free and
must be executed later from the normal Dev host network namespace.

This supersedes the unexecuted predecessor freeze
`770db0ef2a5e870a9972af827ed5144e5488fac5`, which had a pre-inference
request-derived authority provenance defect. No model or tool calls were made
by that predecessor.

Freeze commit: resolve with `git rev-parse HEAD` after the superseding freeze
commit.

Prepared driver SHA256: `c7c0114b3c80d0f56b31ae2be29fb038b5978d8c872678544435664047b1112e`

Frozen driver:

`scripts/true_semantic_fallback_v2.py`

Frozen run directory:

`.work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z`

Before execution, verify the frozen driver hash from the V2 manifest:

```bash
python3 - <<'PY'
import hashlib, json
from pathlib import Path
p = Path("scripts/true_semantic_fallback_v2.py")
m = json.loads(Path(".work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z/router_manifest.json").read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest() == m["driver_sha256"]
print(m["driver_sha256"])
PY
```

Verify that no response exists before execution:

```bash
find .work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z -name response.json -print
```

Expected output is empty. Execute exactly:

```bash
source config.env
PYTHONPATH=. python3 scripts/true_semantic_fallback_v2.py \
  --execute \
  --output-dir .work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z
```

Use no wrapper and no compatibility monkey patch. The driver directly imports
`telemetry_base_url()` and `telemetry_preflight()` from
`scripts.zth_qwen3_0_6b_clean_scope_logic_probe`.

After execution, count responses and calls:

```bash
find .work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z -name response.json | wc -l
python3 - <<'PY'
import json
from pathlib import Path
p = Path(".work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z/lifecycle.json")
print(json.loads(p.read_text()))
PY
```

The frozen budget is six 1.7B model calls for the six true-fallback tasks, zero
model calls for four controls, no retries, no teacher, no 30B, no external
inference, and no qualification or production changes.
