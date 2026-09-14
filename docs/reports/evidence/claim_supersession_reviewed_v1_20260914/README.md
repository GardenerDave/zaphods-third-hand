# claim_supersession_reviewed_v1_20260914

**Task family:** `current_vs_superseded_claim` — a temporal / current-vs-superseded
claim-reconciliation task (dated position statements + a factual evidence block;
`exact_json` validator).

**Models:**
- Worker: `Qwen_Qwen3-1.7B-Q4_K_M.gguf` (toolless, fixture inlined)
- Local teacher: `Qwen3.8-27B-UD-IQ4_XS.gguf` (reference-blind, `guidance_only`
  intervention mode)
- External teacher: **unconfigured** (`ZTH_EXTERNAL_TEACHER_COMMAND` not set)

**Endpoint:** `JARVIS_LOCAL`
**Task id:** `claim_supersession_reviewed_v1_20260914`
**Run date:** 2026-09-14 (UTC)
**Terminal review state:** `infrastructure_error` (external-teacher unconfigured masked the
worker verdict) — **NOT** a capability verdict.

## What this preserves

One genuine bounded run of the ZTH supervised capability loop over the reviewed_v1
temporal-reconciliation fixture. Two things are recorded here:

1. **The genuine 1.7B worker result** (4/4 valid JSON, **0/4 exact**).
2. **The 27B teacher's failure mode, reclassified** from "response truncation (packaging)"
   to **a config/omission failure — NOT a model-capability failure**. This is the exact bug
   fixed by the default-`routine` guard in `icm_spec.py:resolve_worker_spec` (see "27B
   teacher" below and `../README.md`).

The expected answer is hidden from the worker; all four worker prompts carry the fixture
inline and **do not** expose `expected_output` or any `S*` / `pivotal_commit` answer field.

## Genuine 1.7B worker result (4/4 valid JSON, 0/4 exact)

The 1.7B produced a well-formed `exact_json` object on **all four** attempts and matched
the expected answer on **none**. Per-field pattern across attempts 1–4:

| Field | Expected | Worker pattern |
|-------|----------|----------------|
| `S1` | `superseded` | `superseded` on all 4 (**correct** — the one stable win) |
| `S2` | `superseded` | `current` on all 4 (**wrong**) |
| `S3` | `current` | `superseded` on all 4 (**wrong**) |
| `S4` | `current` | flips `current`/`superseded` (wrong on the attempts that mattered) |
| `pivotal_commit` | `47cf409` | `002a1b7` (attempts 1–2) then `7c68f2b` (attempts 3–4); **never** `47cf409` |

The weakness is **temporal/causal reconciliation**: the 1.7B does not correctly separate
*current* from *superseded* positions, and it cannot identify the invariant-establishing
commit (`47cf409`) — it reaches for the most recent commit in the evidence block instead.
`S1` is the only stable correct field. The parse itself is never the problem (4/4 valid
JSON); the *reconciliation* is.

## 27B local teacher: config/omission, NOT model-capability failure

In the comparable run (`docs/reports/evidence/reviewed_v1_routine_policy_rerun_20260912`)
the 27B teacher was correctly configured and produced a parseable intervention. In this
run it did **not**, and the failure was originally mislabeled as "response truncation
(evidence-packaging/infrastructure)". On inspection the truncation has a concrete,
deterministic cause that is **config/omission**, not the model's ability:

**Root cause.** The loop invoked the teacher via `resolve_worker_spec` with **no**
`request_policy_name`, and `ICM_QWEN3_8_27B_REQUEST_POLICY` was **unset**. With no policy
name resolved, `resolved_request_policy_name` was `None`, so **no request policy was bound**
to the teacher call. The `request_provenance` of both teacher passes records this directly:

- `thinking_budget_tokens: null` (should be `256` under `routine`)
- `chat_template_kwargs: null` (should be `{"reasoning_effort": "low"}` under `routine`)
- `max_tokens: 1200` — the caller argument the loop passes to the teacher, **not** a policy cap

**Consequence.** With `thinking_budget_tokens` unbounded and `reasoning_effort` unbounded,
the 27B poured its entire 1200-token `max_tokens` budget into the **reasoning channel** and
never finished emitting the structured JSON. Both passes:

- `finish_reason: "length"`
- `status: "reasoning_only"`
- `usage.completion_tokens: 1200` (hit the cap)
- `content` cut off mid-JSON (`"candidate_prompt_patch": "` / `"failure_classification": "`)

The harness parser then captured only `{"teacher_parse_status": "passed"}` from the
near-empty structured part, so **no actionable guidance reached the worker**. The `passed`
parse status reflects *parseability* of the truncated output, not a capability signal.

**Why this is not a model-capability failure.** The 27B's *reasoning channel* — the part
that survived truncation — actually **solved the task correctly in both passes**: it
explicitly derived `47cf409` as the pivotal invariant ("the pivotal invariant is 47cf409"),
correctly identified the S2/S3/S4 supersession logic, and framed the worker's error as a
temporal-reconciliation mistake. The model understood the answer; the missing policy
(unbounded reasoning) simply let it spend its whole token budget deliberating instead of
emitting the bounded JSON the worker needed. A model-capability failure would have been a
wrong or incoherent answer *given a properly bounded request*; this is a truncated one
*because the request was misconfigured*.

**Fix (applied this session).** `icm_spec.py:resolve_worker_spec` now defaults to the
`routine` policy when the worker advertises one and neither an explicit `request_policy_name`
arg nor an `ICM_<WORKER>_REQUEST_POLICY` env override is supplied:

```
explicit arg  >  env var  >  `routine` default
```

`routine` = `{chat_template_kwargs: {reasoning_effort: "low"}, thinking_budget_tokens: 256,
max_tokens: 1024}` (the payload `max_tokens` remains the caller argument). With the default
bound, a plain `qwen3_8_27b` invocation can no longer silently fall back to an unbounded
no-policy request, so the reasoning budget is capped and the structured answer fits.
Precedence and the legacy-worker carve-out are covered by the regression tests in
`local_harness/tests/test_icm_call.py` and
`tests/test_supervised_capability_loop.py`.

**External teacher.** The terminal `infrastructure_error` is separate and expected: the
external teacher was never configured in this run, so its single escalation was recorded as
an infrastructure failure (`zth_external_teacher_infrastructure_failure_v1`,
`ZTH_EXTERNAL_TEACHER_COMMAND is not configured`) rather than a model verdict. No external-
teacher configuration was added.

## Files

```
archive_manifest.json          — durable-archive manifest (zth_evidence_archive_v1)
README.md                      — this file
genuine_raw_evidence/
  fixture.json                 — the task fixture (prompt, output contract, expected_output)
  attempt-1.metadata.json      — 1.7B attempt 1 metadata
  attempt-1.prompt.txt         — 1.7B attempt 1 prompt (fixture inline; answer NOT exposed)
  attempt-1.raw.json           — 1.7B attempt 1 raw response
  attempt-1.validation.json    — 1.7B attempt 1 validation (valid_json=true, exact_match=false)
  attempt-2.metadata.json / .prompt.txt / .raw.json / .validation.json
  attempt-3.metadata.json / .prompt.txt / .raw.json / .validation.json
  attempt-4.metadata.json / .prompt.txt / .raw.json / .validation.json
  local-teacher-1.json         — 27B teacher pass 1 (finish_reason=length, reasoning_only,
                                 thinking_budget_tokens=null, chat_template_kwargs=null)
  local-teacher-2.json         — 27B teacher pass 2 (same failure mode)
  external-teacher.infrastructure.json — unconfigured external-teacher infrastructure record
  trajectory.jsonl             — full per-event trajectory
  trajectory_summary.json      — summary (review_state=infrastructure_error, pass=false)
  NOTE.md                      — raw-evidence provenance + reclassification pointer
```

## Reproduction

```
python3 local_harness/supervised_capability_loop.py \
  --task-id claim_supersession_reviewed_v1_20260914 \
  --task-family current_vs_superseded_claim \
  --fixture .work/dogfood/claim_supersession_reviewed_v1_20260914/fixture.json \
  --worker qwen3_1_7b --teacher qwen3_8_27b \
  --endpoint JARVIS_LOCAL --output .work/dogfood/claim_supersession_reviewed_v1_20260914/run
```

(As run, with no `ICM_QWEN3_8_27B_REQUEST_POLICY` set — which is what triggered the
config-omission teacher truncation recorded above. With the fix applied, a plain
`qwen3_8_27b` teacher invocation now defaults to `routine`.)
