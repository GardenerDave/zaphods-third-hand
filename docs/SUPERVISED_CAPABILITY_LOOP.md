# Supervised capability-mining loop

`local_harness/supervised_capability_loop.py` adds a bounded three-tier ladder
to the existing ZTH evidence workflow:

```text
small worker -> deterministic validator -> bounded retry
             -> local teacher/reviewer -> new worker attempt
             -> optional external teacher adapter -> new worker attempt
```

The worker is normally the local 1.7B endpoint and the local teacher is
normally the 30B endpoint. Their endpoint URLs and model IDs are explicit
environment configuration; no endpoint is silently discovered or substituted.
Existing prompt patches are resolved by ID from `PromptPatchLibrary`, checked
for stage/task/model applicability, rendered, and applied only to the
`existing_patch` attempt. Their IDs and hashes are recorded. A teacher-produced
patch must validate as a `candidate` patch and is recorded only as an
intervention for a new bounded attempt. It is never added to the library or
promoted automatically.

Each attempt and teacher response is appended to `trajectory.jsonl`, with raw
artifact references, SHA-256 hashes, model identity, escalation level,
deterministic verdict, teacher fields, review state, and available usage/timing
metadata. Existing terminal summaries make a restart idempotent; prior failed
artifacts are retained.

Fixtures select either the simple `exact_json` validator or the
`zth_output_contract` adapter, which delegates to the existing supervised ZTH
output-contract validator. The model cannot select a validator. Model claims,
teacher diagnoses, corrected references, and candidate patches are evidence
only. A successful run is `ready_for_review`; exhausted or unavailable
escalation is `unresolved`.

Durable transitions are:

```text
worker_call_started -> worker_output_captured -> worker_output_validated
  -> local_teacher_started -> local_teacher_response_captured
  -> local_teacher_retry_completed
  -> external_teacher_started -> external_teacher_response_captured
  -> external_teacher_retry_completed -> ready_for_review | unresolved
```

Raw, validation, and teacher artifacts are scanned on restart, so an
interruption between an artifact write and its trajectory append does not
repeat that model call. Failed attempts remain preserved.

External teacher boundary

There is no built-in assumption about Codex authentication or shell UX. The
external path is available only when the operator configures
`ZTH_EXTERNAL_TEACHER_COMMAND` and, optionally,
`ZTH_EXTERNAL_TEACHER_IDENTITY`. The command receives the teacher packet on
stdin and must return JSON on stdout. Missing, empty, timed-out, or non-zero
commands fail closed to `unresolved` and preserve the diagnostic.

Sequential reviewed fixture batch

The minimal overnight-compatible driver processes only explicitly supplied
fixtures, serializes with a batch lock, and emits a closeout `scorecard.json`:

```bash
python3 scripts/zth_capability_batch.py \
  local_harness/fixtures/capability_loop/reviewed_v1 \
  --out-dir .work/capability_batch_reviewed_v1 \
  --max-worker-attempts 2 \
  --max-teacher-passes 2
```

It does not read or mutate `roadmap_queue.tsv` and does not invent work.
