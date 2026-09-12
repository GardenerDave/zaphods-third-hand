# ZTH Supervised Capability Loop — Local Harness Core-Module-Scale Dogfood (2026-09-11)

This directory durably preserves one bounded, read-only, repository-observation
run of the ZTH supervised capability loop. The task: **count the curated core
`local_harness/*.py` modules and name the largest and smallest by `wc -l` line
count, emitting a single bounded JSON verdict.** The worker was driven by the
default 1.7B worker model (`Qwen_Qwen3-1.7B-Q4_K_M.gguf`, endpoint alias
`JARVIS_LOCAL`) against a raw-evidence prompt. The validator-only reference
(`expected_output`) is **not** injected into the model call.

The run did **not** pass, and its terminal disposition is an
**infrastructure/config artifact**, not a worker-success signal — see the
"Reading this run" section before using it as any kind of capability claim.

## The task (raw evidence, no conclusion)

- **Classification: genuine raw-evidence interpretation by the 1.7B worker.**
- The prompt hands the worker raw `wc -l` output for the 10 curated
  `local_harness/*.py` modules (ascending filename order, as `wc` emits) and
  asks it to report `file_count`, the largest file + line count, and the
  smallest file + line count. It does **not** state the answer.
- The true reference (validator-only):
  `{"file_count":10, "largest_file":"run_manual_supervised_attempt.py",
  "largest_lines":2269, "smallest_file":"icm_spec.py", "smallest_lines":230}`.

## What actually happened (verbatim)

- The 1.7B worker produced, **identically on all four model attempts**:
  ```json
  {"file_count": 10, "largest_file": "zth_task.py", "largest_lines": 1515,
   "smallest_file": "icm_spec.py", "smallest_lines": 230}
  ```
- Deterministic validation: `json_parse` **passed**;
  `reference_output_exact_match` **failed**.
- The worker got `file_count` (10) and the smallest
  (`icm_spec.py` / 230, the first row of the ascending-sorted evidence) right,
  but **misidentified the largest file**: it reported `zth_task.py` / 1515
  (the second-to-last row) instead of the true maximum
  `run_manual_supervised_attempt.py` / 2269 (the last row). A classic small-model
  max-scan failure on a filename-ascending numeric list: it latched onto a late
  row rather than the actual maximum.

## Routing behaviour (the loop's own mechanism under test)

The loop's routing tiers executed exactly as designed; no manual
pre-escalation was applied:

1. **Worker baseline** (attempts 1–2): 1.7B worker, no intervention, exact-match
   failed both times.
2. **Local teacher** (attempts 3–4): the 27B teacher
   (`Qwen3.8-27B-UD-IQ4_XS.gguf`) was consulted **twice** (`teacher_pass_count:2`).
   On **both** passes the teacher emitted `reasoning_only` (all output in the
   reasoning channel, no completion), so its intervention **failed to parse as
   JSON** (`teacher_parse_status:failed`) and was not applicable. The worker was
   retried **unchanged** and reproduced the same output.
3. **External teacher** (terminal tier): **unconfigured** —
   `adapter_identity:codex-unconfigured`,
   `error:"external teacher unavailable: ZTH_EXTERNAL_TEACHER_COMMAND is not
   configured"`. Because the terminal tier could not run, the loop forced
   `disposition:infrastructure_error`.

## Summary of counts (from `trajectory_summary.json`)

- `disposition`: `infrastructure_error`; `pass:false`; `unresolved:false`
- `first_attempt_pass`: `false`
- `attempt_count`: `4`; `model_attempt_count`: `4`; `teacher_pass_count`: `2`;
  `external_escalation_count`: `1`; `external_teacher_call_count`: `1`
- `successful_intervention_source`: `none`
- `review_state`: `infrastructure_error`

## Reading this run

- **The capability verdict** is about the 1.7B worker: it **failed exact-match
  on the largest-file field** (picked a late row over the true max). That is the
  genuine, reproducible capability boundary this run isolates.
- **The `infrastructure_error` disposition is a routing/config artifact**, not a
  model-success signal. It is caused by the **unconfigured external-teacher
  tier** forcing a terminal failure once the worker's baseline and the local
  teacher's (unparseable) intervention were both exhausted. It must not be read
  as "the worker succeeded" or as a defect in the worker.
- **The teacher finding** is also genuine: the 27B teacher **reasoned** the
  filename-sorting misread correctly but emitted **reasoning-only output** (no
  completion), so the loop could not use its intervention. This is a real
  observation about the local-teacher path on this model, preserved verbatim in
  `local-teacher-1.json` / `local-teacher-2.json`.

## Preserved artifacts

`genuine_raw_evidence/` contains the exact audit trail, copied byte-identically
from the source scratch run (verified by SHA-256 in `archive_manifest.json`):

- `fixture.json` — the capability-loop fixture, including the validator-only
  `expected_output` reference (never injected into the model call).
- `attempt-{1..4}.prompt.txt` — the exact prompts written to the worker,
  verbatim (attempts 3–4 differ only in the local-teacher retry framing).
- `attempt-{1..4}.raw.json` — the raw worker response envelope (`content`,
  `metadata`, `status`).
- `attempt-{1..4}.metadata.json` — request provenance: model, temperature,
  max_tokens, message structure, and the
  `raw_response_sha256` / `prompt_sha256` / `request_body_sha256` hashes.
- `attempt-{1..4}.validation.json` — deterministic validation result and checks.
- `local-teacher-{1,2}.json` — the two 27B local-teacher responses (both
  `reasoning_only`, unparseable intervention).
- `external-teacher.infrastructure.json` — the terminal-tier infrastructure
  failure record (unconfigured external teacher).
- `trajectory.jsonl` — the event-level trajectory.
- `trajectory_summary.json` — the pass/escalation/disposition summary.

## Audit index

- `archive_manifest.json` — machine-readable manifest of every preserved file
  with `sha256`, byte `size`, and the `source_path` in the original (scratch)
  run, using the repository's existing `docs/reports/evidence/.../
  archive_manifest.json` schema.
- `genuine_raw_evidence/NOTE.md` — the run classification note.

## Scope of this commit

This directory only preserves existing, already-run evidence. It changes no ZTH
machinery, reruns nothing, and adds no infrastructure. The source scratch run
(`/tmp/zth_dogfood/local_harness_core_module_scale_dogfood_20260911/`) remains
in place and untouched; this is its durable, tracked record.
