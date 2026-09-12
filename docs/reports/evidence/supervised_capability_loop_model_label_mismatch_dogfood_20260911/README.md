# ZTH Supervised Capability Loop — Model-Label-Mismatch Dogfood (2026-09-11)

This directory durably preserves two bounded local-worker runs of the ZTH
supervised capability loop on the same task: **verify one config/env/model-label
consistency fact about the local ZTH fleet and emit a single bounded JSON
verdict.** Both runs were driven by the same ZTH worker model
(`Qwen_Qwen3-1.7B-Q4_K_M.gguf`) against the same endpoint.

The two runs are deliberately preserved together because they form the
before/after pair of an **evaluation-design correction**. They must be read
separately and must not be conflated.

## Run 1 — `smoke_orchestration_only/` (earlier, spoon-fed)

- **Classification: orchestration / instruction-following smoke. NOT genuine
  worker reasoning. Must not be used as capability evidence.**
- The worker prompt handed the model the conclusion and the exact expected
  output. The prompt explicitly states the declared model "does NOT match what
  port 8080 actually serves", asserts "Therefore a mismatch is detected", and
  then says "Output EXACTLY this JSON object and nothing else" with the full
  target object (including `"mismatch_detected": true`) already written out.
- The first-attempt pass therefore proves the 1.7B worker can **follow
  instructions and reproduce a given JSON shape** (the ZTH orchestration path:
  prompt write, model call, deterministic validation, trajectory,
  `ready_for_review`). It does **not** prove the worker can interpret raw
  evidence and reach the verdict itself.
- Why retained: this run exposed an **evaluation-design error** in the original
  dogfood — the "expected output" was not merely hidden from the model; it was
  literally printed inside the prompt. It is preserved as the concrete
  demonstration of that error so the corrected design (Run 2) is auditable in
  contrast.
- Provenance: source run `.work/dogfood/config_env_model_label_mismatch_20260911`
  (git-ignored, disposable; this copy is the durable record).
- Key hashes: `raw_response_sha256` `d7a1438c…` (see `attempt-1.metadata.json`
  and `archive_manifest.json` for full values).

## Run 2 — `genuine_raw_evidence/` (corrected, accepted)

- **Classification: genuine raw-evidence interpretation by the 1.7B worker.**
- The worker prompt withholds the conclusion and the exact expected output. It
  gives the worker (a) the declared config/model fact and (b) the raw
  `/v1/models` endpoint facts for ports 8080 and 8081, and asks the worker to
  decide the match itself and emit the verdict. `expected_output` (the
  validator-only reference) is **not** injected into the model call.
- The worker interpreted the raw facts, produced
  `"actual_model_at_endpoint":"Qwen3.8-27B-UD-IQ4_XS.gguf"`,
  `"declared_model":"Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"`,
  `"match":false`, and the run passed on the **first attempt** with **no
  escalation**.
- Outcome: deterministic validation **passed** (`json_parse` +
  `reference_output_exact_match`), `first_attempt_pass:true`,
  `external_escalation_count:0`, `teacher_pass_count:0`,
  `disposition:ready_for_review`.
- Provenance: source run
  `.work/dogfood/config_env_model_label_mismatch_dogfood_raw_20260911`
  (git-ignored, disposable; this copy is the durable record).
- Key hashes: `raw_response_sha256` `39732c8f…` (full values in
  `attempt-1.metadata.json` and `archive_manifest.json`).

## Preserved artifacts per run

Each run subdirectory contains the exact audit trail, copied byte-identically
from the source `.work/` run (verified by SHA-256):

- `fixture.json` — the capability-loop fixture, including the validator-only
  `expected_output` reference (never injected into the model call).
- `attempt-1.prompt.txt` — the exact prompt written to the worker, verbatim.
- `attempt-1.raw.json` — the raw worker response envelope (`content`,
  `metadata`, `status`).
- `attempt-1.metadata.json` — request provenance: model, temperature,
  max_tokens, finish_reason, message structure, and the
  `raw_response_sha256` / `prompt_sha256` / `request_body_sha256` hashes.
- `attempt-1.validation.json` — deterministic validation result and checks.
- `trajectory.jsonl` — the event-level trajectory.
- `trajectory_summary.json` — the pass/escalation/disposition summary.

## Audit index

- `archive_manifest.json` — machine-readable manifest of every preserved file
  with `sha256`, byte `size`, and the `source_path` in the original
  (git-ignored) `.work/` run, using the repository's existing
  `docs/reports/evidence/.../archive_manifest.json` schema.
- `smoke_orchestration_only/NOTE.md` — the smoke-run classification note.
- `genuine_raw_evidence/NOTE.md` — the genuine-run classification note.

## Scope of this commit

This directory only preserves existing, already-run evidence. It changes no
ZTH machinery, reruns nothing, and adds no infrastructure. The source `.work/`
runs remain in place and untouched; this is their durable, tracked record.
