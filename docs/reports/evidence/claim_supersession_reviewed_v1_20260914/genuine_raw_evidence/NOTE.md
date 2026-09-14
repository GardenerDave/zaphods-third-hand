# genuine_raw_evidence — provenance note

These files are the **byte-identical raw artifacts** of the 2026-09-14 (UTC) run
`claim_supersession_reviewed_v1_20260914`, copied without modification from the untracked
run directory:

```
.work/dogfood/claim_supersession_reviewed_v1_20260914/
  fixture.json
  run/
    attempt-{1,2,3,4}.metadata.json
    attempt-{1,2,3,4}.prompt.txt
    attempt-{1,2,3,4}.raw.json
    attempt-{1,2,3,4}.validation.json
    local-teacher-{1,2}.json
    external-teacher.infrastructure.json
    trajectory.jsonl
    trajectory_summary.json
```

The `run.log` harness log is intentionally **not** archived here (it is not raw model
evidence); the comparable tracked records do not archive it either.

## What is genuine and what is reclassified

- **Genuine, preserved verbatim:** all four 1.7B worker attempts
  (`attempt-{1..4}.*`). These are the real bounded worker outputs of the
  `current_vs_superseded_claim` task — 4/4 valid JSON, 0/4 exact. Do not edit.

- **Reclassified in `../README.md` (not edited here):** the two 27B local-teacher
  artifacts (`local-teacher-1.json`, `local-teacher-2.json`) record a **config/omission
  failure, not a model-capability failure**. Both passes ran with **no request policy
  bound** — `request_provenance` shows `thinking_budget_tokens: null` and
  `chat_template_kwargs: null` — because the loop invoked the teacher with no
  `request_policy_name` and `ICM_QWEN3_8_27B_REQUEST_POLICY` was unset, so
  `resolve_worker_spec` resolved `resolved_request_policy_name=None`. Unbounded reasoning
  then consumed the entire 1200-token `max_tokens` budget in the reasoning channel
  (`finish_reason: "length"`, `status: "reasoning_only"`, `usage.completion_tokens: 1200`),
  cutting the structured JSON off mid-emission. The 27B's reasoning channel nevertheless
  derived the correct pivotal commit (`47cf409`); the model was capable — the request
  configuration was not. This is fixed by the default-`routine` guard in
  `local_harness/icm_spec.py:resolve_worker_spec` (precedence: explicit arg > env var >
  `routine`). The raw files are left unmodified so the misconfiguration is inspectable in
  the archive.

- **Infrastructure:** `external-teacher.infrastructure.json` records that the external
  teacher was unconfigured in this run (`ZTH_EXTERNAL_TEACHER_COMMAND` not set); this is
  the terminal `infrastructure_error` and is expected, not a model verdict.
