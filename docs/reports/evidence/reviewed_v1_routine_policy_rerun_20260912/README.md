# ZTH Supervised Capability Loop — `reviewed_v1` Routine-Policy Rerun (2026-09-12)

This directory durably closes out the `reviewed_v1` multi-source-reconciliation
dogfood. It preserves one bounded rerun of the ZTH supervised capability loop
whose sole purpose was to **correct the local-teacher request policy** that had
been misconfigured in the comparable run, and to observe whether a
correctly-configured 27B local teacher rescues a subsequent 1.7B worker
attempt. The rerun's raw run outputs are preserved byte-identically in
`genuine_raw_evidence/`, and this README is the closeout reading.

The run **passed**, and its terminal disposition is a **`ready_for_review`**
terminal state — but the honest mechanism must be stated before it is used as
any kind of capability claim. **Correction (2026-09-13):** that "pass" is a
**pre-invariant teacher-reference echo**, not a 27B-guidance rescue and not 1.7B
capability. It reproduces **only** under the pre-`47cf409` prompt builder that
leaked `corrected_reference_output` into the worker retry prompt. A rerun under
the current HEAD (guidance-only invariant) **does not** reproduce it. See
"Reading this run" and "Post-invariant confirmation".

## Task and fixture

- **Classification: genuine raw-evidence interpretation by the 1.7B worker.**
  The prompt hands the worker the curated corpus
  `local_harness/fixtures/capability_loop/reviewed_v1/` (24 JSON files +
  `README.md`) and asks it to report, as a single bounded JSON verdict:
  `total_files`, `distinct_task_families`, `filename_prefix_groups`,
  `readme_named_source_families`, and `cover_all_files`. It does **not** state
  the answer.
- The validator-only reference (`expected_output`) is **not** injected into the
  model call. Ground truth:
  ```json
  {"total_files": 24, "distinct_task_families": 8,
   "filename_prefix_groups": {"blocked":4,"frontdoor":5,"logic":6,"prompt":6,"queue":3},
   "readme_named_source_families": 4, "cover_all_files": false}
  ```
- **Fixture provenance (Option A):** the originally frozen fixture and its raw
  worker prompt were lost (cleaned from `/tmp`, never committed); the frozen
  SHA `3f262c29…` is unreproducible byte-exactly. Per the binding instruction
  ("if the SHA cannot be reproduced byte-exactly, STOP and report the
  fixture-loss blocker rather than tuning the prompt"), this was **not**
  resolved by prompt-tuning. The fixture was **task-identically reconstructed**
  under a new SHA `c1197915dc6752851026d14b78436fa27467ecdee5700f82e535702dfd2c246d`,
  documented as diverging from the lost frozen SHA. The raw run outputs of this
  rerun are **not** byte-identical to the lost original run. See
  `genuine_raw_evidence/NOTE.md` for the full divergence record.

## What actually happened (verbatim)

- **Worker baseline (attempts 1–2):** the 1.7B worker produced, **identically
  in parsed content on both attempts** (raw bytes differ, parsed JSON is the
  same):
  ```json
  {"total_files": 5, "distinct_task_families": 3,
   "filename_prefix_groups": {"capability_loop":3,"reviewed":2,"test":0},
   "readme_named_source_families": 2, "cover_all_files": true}
  ```
  Deterministic validation: `json_parse` **passed**; `reference_output_exact_match`
  **failed**. **Corrected characterization (2026-09-13):** this is **not** a
  counting error and not a conflation of `task_family` values with filename
  prefix groups. The worker is a **pure LLM call with no filesystem access and
  no tools**; it has never observed the corpus. It **hallucinates** a plausible
  directory listing from the path string in the prompt (`total_files:5`,
  phantom prefix groups `capability_loop`/`reviewed`/`test` inferred from the
  path components) instead of the true 24 / 8 with the real prefix groups
  (`blocked`, `frontdoor`, `logic`, `prompt`, `queue`). The 27B teacher's own
  `teacher_diagnosis` names this: the model "has no filesystem access". This is
  the genuine 1.7B capability boundary, preserved in both runs.
- **Local teacher (pass 1):** the 27B teacher
  (`Qwen3.8-27B-UD-IQ4_XS.gguf`), under the **`routine`** request policy,
  emitted a **parseable** intervention
  (`teacher_parse_status:passed`) — the exact inversion of the comparable run.
  Its `failure_classification` was `model_capability_insufficient`. Its
  `candidate_prompt_patch` was `null` (`candidate_patch_status:invalid_candidate`)
  — i.e. the teacher itself determined that **no prompt modification** would
  resolve the task. Its `teacher_diagnosis` correctly named the 1.7B
  hallucination (5 files / 3 families / phantom prefixes vs the true 24 / 8 /
  `blocked`-`frontdoor`-`logic`-`prompt`-`queue`), and its `retry_guidance` was
  "No prompt modification will resolve this…" — explicitly recommending
  pre-computing / embedding the answer.
- **Worker rerun (attempt 3):** the loop re-ran the worker with
  `patched_prompt + "\n\n## Local teacher intervention\n" + json.dumps(parsed)`.
  The 1.7B produced:
  ```json
  {"total_files": 24, "distinct_task_families": 8,
   "filename_prefix_groups": {"blocked":4,"frontdoor":5,"logic":6,"prompt":6,"queue":3},
   "readme_named_source_families": 4, "cover_all_files": false}
  ```
  Validation **passed**; the output is **byte-identical to the
  `corrected_reference_output`** the teacher had computed and embedded in the
  intervention.

## Routing behaviour (the loop's own mechanism under test)

The loop's routing tiers executed exactly as designed; no manual
pre-escalation was applied:

1. **Worker baseline** (attempts 1–2): 1.7B worker, no intervention,
   exact-match failed both times. `intervention_source: none`.
2. **Local teacher** (pass 1): the 27B teacher was consulted **once**
   (`teacher_pass_count:1`). Under the `routine` policy it produced a
   **parseable** intervention (`teacher_parse_status:passed`),
   `failure_classification: model_capability_insufficient`,
   `candidate_prompt_patch: null` (no patch). The teacher's answer was **not**
   used as the result directly.
3. **Worker rerun** (attempt 3): the worker re-ran against the patched prompt
   (original + embedded teacher intervention). It **passed**.
   `successful_intervention_source: local_teacher`.
4. **External teacher** (terminal tier): **never reached** —
   `external_escalation_count:0`, `external_teacher_call_count:0`.

## Summary of counts (from `trajectory_summary.json`)

- `disposition`: `ready_for_review`; `pass: true`; `unresolved: false`
- `first_attempt_pass`: `false`
- `pass_after_local_teacher_intervention`: `true`
- `successful_intervention_source`: `local_teacher`
- `intervention_outcome`: `helped`
- `attempt_count`: `3`; `model_attempt_count`: `3`; `teacher_pass_count`: `1`;
  `external_escalation_count`: `0`
- `review_state`: `ready_for_review`

## Reading this run (the closeout)

**(a) The original `reasoning_only` 27B attempt was a misconfigured
escalation, NOT a teacher regression.** In the comparable run the
`ICM_QWEN3_8_27B_REQUEST_POLICY=routine` policy was omitted, so the 27B fell
back to `reasoning_only` (all output in the reasoning channel, no completion)
and its intervention failed to parse (`teacher_parse_status:failed`). The
27B was never given a chance to emit a parseable intervention. That run's
`infrastructure_error` was therefore a **configuration artifact** — the absence
of the `routine` request policy — not evidence that the 27B regressed or
cannot solve the task. This rerun, with the policy set, inverts that: one
teacher pass produced a fully parseable, correctly-classified intervention.

**(b) The rerun outcome is a pre-invariant teacher-reference echo (not a
reproducible "rescue").** With the correct `routine` policy, one local-teacher
pass produced a parseable intervention, and the 1.7B passed the patched prompt
on rerun (`pass_after_local_teacher_intervention: true`,
`successful_intervention_source: local_teacher`, `intervention_outcome: helped`).
**Correction (2026-09-13):** that pass is not a durable property of a
correctly-configured 27B teacher. It exists **only** because the pre-`47cf409`
prompt builder leaked the teacher's `corrected_reference_output` verbatim into
the worker's retry prompt, which the 1.7B then echoed. Under the current
guidance-only invariant that leak is stripped, so the same fixture + same
teacher produces **no** pass (see section (g)). Calling this a "successful
rescue" is therefore misleading: the 27B supplied the reference answer, the
1.7B copied it, and the loop's `successful_intervention_source: local_teacher`
correctly attributes the answer to the 27B — not to 1.7B capability. The
comparable run's terminal `infrastructure_error` is reversed to
`ready_for_review` **only under the pre-invariant builder**.

**The honest mechanism (stated plainly):** the "rescue" works because the 27B
**computed the correct answer itself** and **embedded it as the
`corrected_reference_output`** in the intervention prompt; the 1.7B then
**echoed** it (attempt-3 output is byte-identical to the teacher's
`corrected_reference_output`). The teacher's own `retry_guidance`
("No prompt modification will resolve this…") recommended exactly this:
pre-computing and embedding the answer. The loop's
`successful_intervention_source: local_teacher` correctly attributes the
correct answer to the 27B, not to the 1.7B.

**(c) The capability boundary stands.** `first_attempt_pass: false` in **both**
the original run and this rerun. The 1.7B **cannot solve the task on its own**
(phantom prefix groups, 5/3 vs 24/8). The pass on attempt 3 came **from the
27B's supplied reference answer**, not from the 1.7B acquiring the
capability. This is a rescue-by-teacher-supplied-reference, not a
worker-capability gain. The genuine 1.7B counting/grounding failure is
preserved as durable capability-boundary evidence.

**(d) Routing lesson (now evidenced).** A local-teacher failure is
**configuration before model**: a missing `routine` request policy silently
degrades the 27B to `reasoning_only`, making its intervention unparseable and
forcing a spurious `infrastructure_error`. With
`ICM_QWEN3_8_27B_REQUEST_POLICY=routine`, one teacher pass produced a
parseable, correctly-classified intervention and the 1.7B passed the patched
prompt on rerun (pre-invariant reference leak only — see (b)/(g)). The correct
diagnosis of the earlier failure is **misconfigured-escalation** (omitted
`routine` policy), not teacher regression.

**(d, updated 2026-09-13 — post-invariant routing lesson).** Under the current
guidance-only framework, a local-teacher pass that does **not** change the
worker outcome (because the reference is stripped) correctly falls through the
escalation chain to the next tier. When the terminal tier (external teacher) is
**unconfigured** (`ZTH_EXTERNAL_TEACHER_COMMAND` unset), the expected terminal
state is `infrastructure_error` — a framework escalation artifact, **not** a 27B
failure and **not** a capability verdict (`capability_verdict_available:false`).
A worker pass that only exists because the teacher's reference leaked into the
retry prompt must **never** be credited as 1.7B capability; under guidance-only
that pass does not reproduce, which is exactly what (g) shows.

**(e) Fixture-loss blocker record (Option A).** The frozen fixture + raw worker
prompt were lost (cleaned `/tmp`, never committed); the frozen SHA
`3f262c29…` is unreproducible byte-exactly. Per the binding instruction, this
was reported as a fixture-loss blocker rather than resolved by prompt-tuning.
Resolution: task-identical reconstruction, new SHA
`c1197915dc6752851026d14b78436fa27467ecdee5700f82e535702dfd2c246d`, documented
as diverging from the lost frozen SHA. The raw rerun outputs are **not**
byte-identical to the lost original run. Full record in
`genuine_raw_evidence/NOTE.md`.

**(f) No external teacher pursued.** The local 27B teacher, correctly
configured, was sufficient to close out the run (`ready_for_review`). Per the
binding instruction, the external teacher was **not** pursued because the
local teacher works. `external_escalation_count:0`,
`external_teacher_call_count:0`.

**(g) Post-invariant confirmation (2026-09-13).** A bounded rerun of the
**same** task-identical fixture, same raw worker prompt, same 1.7B worker
endpoint, same 27B teacher endpoint, same `routine` policy, and the existing
`_parse_teacher` fix — but under the **current HEAD `47cf409`**
(guidance-only invariant, committed 2026-09-12 11:16, **after** the passing
run at 08:36) — **does not** reproduce the "rescue". Source run folder (scratch,
disposable, **not** committed):
`.work/dogfood/reviewedv1_routine_verify_20260912_routine`. Results:

- `disposition`: `infrastructure_error`; `pass: false`; `unresolved: false`
- `first_attempt_pass`: `false`
- `pass_after_local_teacher_intervention`: `false`
- `successful_intervention_source`: `none`
- `intervention_outcome`: `not-applicable`
- `teacher_intervention_mode`: `guidance_only`
- `teacher_pass_count`: `2`; `attempt_count`: `4`
- `external_escalation_count`: `1`; `external_teacher_call_count`: `1`
- All **four** worker attempts hallucinated `total_files:5` (no reference to
  echo). `candidate_curriculum_examples`: `local_teacher:1 →
  subsequent_worker_result: failed`.

Two consequences:

1. **The 1.7B capability boundary is now confirmed under guidance-only mode.**
   With the reference stripped from the retry prompt, the 1.7B has nothing to
   echo and genuinely fails (4/4 attempts). The prior "pass" is proven to be the
   reference leak, not a capability the 1.7B ever had.
2. **The terminal `infrastructure_error` is a framework escalation artifact, NOT
   a 27B failure.** The loop exhausted its tiers as designed: worker baseline
   failed → local 27B teacher (parseable, `guidance_only`) → post-teacher worker
   retry failed (×2 passes) → escalated to the **unconfigured** external teacher
   (`ZTH_EXTERNAL_TEACHER_COMMAND` unset) → `infrastructure_error`. The 27B
   teacher was consulted and parsed correctly (`teacher_parse_status:passed`);
   it did not fail. The `infrastructure_error` is the expected terminal state of
   the escalation chain when the external teacher is unconfigured, not evidence
   that the 27B regressed or cannot solve the task.

The full (unstripped) teacher payload — including `corrected_reference_output` —
is preserved unchanged in the durable teacher record `local-teacher-1.json`;
only the **worker-facing** retry prompt is stripped by
`_guidance_only_teacher_payload`.

## Provenance (from `attempt-3.metadata.json` and the run environment)

- Worker model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf` (endpoint alias `JARVIS_LOCAL`,
  base_url `http://192.168.137.3:8081/v1`, worker name `router`).
- Local teacher: `Qwen3.8-27B-UD-IQ4_XS.gguf`
  (base_url `http://192.168.137.3:8080/v1`, teacher name `qwen3_8_27b`).
- Teacher request policy: `routine` (`reasoning_effort=low`,
  `thinking_budget_tokens=256`, `max_tokens=1024`).
- Worker sampling: `temperature 0.2`, `max_tokens 768`, `finish_reason stop`;
  constant system message across all three attempts
  (`system_message_sha256 e8c1a9955d1a830189fecdfd11c537896d95cddd0419d5a63d957dd6f0fcb6c7`).
- Baseline prompt (attempts 1–2): `prompt_sha256
  845d723b159f7a1aaee3ba44c454b20782d272ea353a719c68c5779e1a8aed78`,
  `request_body_sha256 355ab5bf91568de2ea6e3488d8b11cfd7af46338c1e337eba3cac5cf47c1d1e6`,
  prompt length 1679.
- Rerun prompt (attempt 3): `prompt_sha256
  61fecce737c550f7b6d4423fb6a48cd592992248cc171777a840582c8286096c`
  (baseline + embedded teacher intervention), prompt length 3453,
  `request_body_sha256 4950b03984837421f433479b8a94f2c0df34abed232bee9d411ff7d3aadcd968`.
- Teacher intervention artifact: `local-teacher-1.json`
  (`teacher_parse_status:passed`, `failure_classification:
  model_capability_insufficient`, `candidate_prompt_patch: null`).
- Reconstructed fixture: `genuine_raw_evidence/fixture.json`
  (`sha256 c1197915dc6752851026d14b78436fa27467ecdee5700f82e535702dfd2c246d`).

Source run folder (scratch, disposable):
`.work/dogfood/reviewedv1_routine_rerun_corrected_20260912_routine`
Source reconstructed fixture (scratch, disposable):
`.work/dogfood/reviewedv1_recon_20260912/fixture.json`
