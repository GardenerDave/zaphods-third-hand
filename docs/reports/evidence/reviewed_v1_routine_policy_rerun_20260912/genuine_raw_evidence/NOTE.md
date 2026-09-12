# NOTE — `reviewed_v1` routine-policy rerun (2026-09-12)

Authoritative configuration and provenance for the raw evidence in this
directory. This is a **rerun** of the `reviewed_v1` multi-source-reconciliation
fixture, performed specifically to (1) correct the local-teacher request
policy that had been misconfigured in the comparable run, and (2) observe
whether a correctly-configured 27B local teacher rescues a subsequent 1.7B
worker attempt.

## Task and fixture (reconstructed — Option A)

- Fixture: multi-source-reconciliation over the curated corpus
  `local_harness/fixtures/capability_loop/reviewed_v1/` (24 JSON files +
  `README.md`). The worker is asked to report, as a single bounded JSON
  verdict: `total_files`, `distinct_task_families`, `filename_prefix_groups`,
  `readme_named_source_families`, and `cover_all_files`.
- **The originally frozen fixture and its raw worker prompt were lost**
  (cleaned from `/tmp`, never committed). The frozen prompt SHA
  `3f262c29…` is **unreproducible byte-exactly**. Per the binding
  instruction, this was **not** resolved by prompt-tuning. Instead the
  fixture was **task-identically reconstructed** and assigned a new SHA
  `c1197915dc6752851026d14b78436fa27467ecdee5700f82e535702dfd2c246d`.
- See `PROVENANCE` below for the SHA divergence record.

### Ground-truth reference (validator-only, not injected into the model call)

```json
{"total_files": 24, "distinct_task_families": 8,
 "filename_prefix_groups": {"blocked":4,"frontdoor":5,"logic":6,"prompt":6,"queue":3},
 "readme_named_source_families": 4, "cover_all_files": false}
```

## Exact run environment (byte-reproducible)

Invocation (from the repository root — `python3 -m`, **not** the script form):

```
ZTH_CAPABILITY_WORKER_NAME=router \
ZTH_CAPABILITY_WORKER_BASE_URL=http://192.168.137.3:8081/v1 \
ZTH_CAPABILITY_WORKER_MODEL=Qwen_Qwen3-1.7B-Q4_K_M.gguf \
ZTH_CAPABILITY_TEACHER_NAME=qwen3_8_27b \
ZTH_CAPABILITY_TEACHER_BASE_URL=http://192.168.137.3:8080/v1 \
ZTH_CAPABILITY_TEACHER_MODEL=Qwen3.8-27B-UD-IQ4_XS.gguf \
ICM_QWEN3_8_27B_REQUEST_POLICY=routine \
python3 -m local_harness.supervised_capability_loop \
    .work/dogfood/reviewedv1_recon_20260912/fixture.json \
    --out-dir .work/dogfood/reviewedv1_routine_rerun_corrected_20260912_routine
```

Exit code: **0** (iff `disposition == ready_for_review`).

### Role → endpoint mapping (confirmed)

- **Worker** (1.7B): `Qwen_Qwen3-1.7B-Q4_K_M.gguf` @
  `http://192.168.137.3:8081/v1` — worker name `router` (endpoint alias
  `JARVIS_LOCAL`).
- **Local teacher** (27B): `Qwen3.8-27B-UD-IQ4_XS.gguf` @
  `http://192.168.137.3:8080/v1` — teacher name `qwen3_8_27b`.

### Request policy (the correction under test)

- `ICM_QWEN3_8_27B_REQUEST_POLICY=routine` → teacher request uses
  `reasoning_effort=low`, `thinking_budget_tokens=256`, `max_tokens=1024`.
  This is the **`routine`** policy. In the comparable (earlier) run this
  policy was **omitted**, so the 27B fell back to `reasoning_only` — all
  output in the reasoning channel, no completion — and its intervention
  **failed to parse as JSON** (`teacher_parse_status:failed`). That run
  therefore forced a terminal `infrastructure_error`.
- Loop defaults: `--max-worker-attempts=2`, `--max-teacher-passes=2`.
- Worker sampling: `temperature=0.2`, `max_tokens=768` (no thinking budget on
  the 1.7B). System message is constant across all three worker attempts
  (`system_message_sha256 e8c1a9955d1a830189fecdfd11c537896d95cddd0419d5a63d957dd6f0fcb6c7`).

## SHA divergence record (Option A)

| item | value |
|------|-------|
| Originally frozen fixture SHA (lost, unreproducible) | `3f262c29…` (truncated in prior notes; not byte-reproducible) |
| Reconstructed fixture SHA (this run) | `c1197915dc6752851026d14b78436fa27467ecdee5700f82e535702dfd2c246d` |
| Task identity | identical (same corpus, same fields, same ground truth) |
| Raw run outputs byte-identical to the lost original run | **No** — raw outputs of this rerun are **not** byte-identical to the lost original run |

The reconstruction is **task-identical** (same corpus and same expected
verdict), not a prompt-tune. The divergence is documented, not hidden.
