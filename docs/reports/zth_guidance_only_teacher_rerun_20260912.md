# ZTH supervised loop — contaminated-reference mechanism + guidance-only rerun

Date: `2026-09-12`. Fixture: `.work/dogfood/controlflow_branch_enumeration_20260912/fixture.json`
(`task_id: terminal-disposition-literals`, `validator.kind: exact_json`,
expected `dispositions = ["infrastructure_error","ready_for_review","unresolved"]`).
This note is the durable record of one attribution bug and its honest rerun.

## The mechanism (the bug)

In `local_harness/supervised_capability_loop.py`, BOTH teacher retry paths
(local and external) serialized the **entire parsed teacher object** into the
worker's retry prompt. That object includes `corrected_reference_output` —
the deterministic expected answer. So whenever a teacher supplied a reference,
the 1.7B saw the exact answer before its retry, and any subsequent pass was a
**teacher-reference rescue (3)**, not a guidance-only success (2).

- Local-teacher retry prompt = `patched_prompt + "\n\n## Local teacher intervention\n" + json.dumps(parsed)`,
  where `parsed` (from `_parse_teacher`) copies `corrected_reference_output`.
- External-teacher retry prompt = the same, from the external parsed payload.
- `corrected_reference_output` is legitimately **kept** in teacher evidence and
  provenance (the `local-teacher-*.json` records and the summary); only the
  **retry prompt** must not carry it.

## The fix

`_guidance_only_teacher_payload(parsed)` strips the reference-bearing fields
(`corrected_reference_output`, `candidate_prompt_patch`, `candidate_prompt_patch_raw`)
before the retry prompt is built, at both sites. It keeps `failure_classification`,
`teacher_diagnosis`, `retry_guidance`, `teacher_parse_status` (and a
separately-validated JSON-object patch). The summary now documents the invariant
with `teacher_intervention_mode: "guidance_only"`. 47/47 tests pass, including
3 new regressions asserting the retry prompts carry no `corrected_reference_output`
and no exact expected array, on both the local and external paths.

## Prior run (`out/`) — reclassified as (3), not a clean (2)

The earlier `out/` run (pre-fix; `teacher_intervention_mode` absent) is a (3):
`attempt-3.prompt.txt` carried
`corrected_reference_output: {"dispositions": ["infrastructure_error","ready_for_review","unresolved"]}`
verbatim. Its (2)-style `pass_after_local_teacher_intervention: true` /
`successful_intervention_source: local_teacher` was therefore a **reference-in-the-loop
rescue**, not a clean guidance-only pass. Full prior detail:
`.work/dogfood/controlflow_branch_enumeration_20260912/PROVENANCE.md` (untracked, `out/`).

## Guidance-only rerun (`out-guidance-only-rerun/`) — honest (2)

Reran the **same fixture unchanged** (same worker prompt, expected output, raw
evidence, worker/teacher models, validator) through the corrected path into a
fresh out dir. Same env: worker `Qwen3-1.7B-Q4_K_M.gguf` @ 192.168.137.3:8081,
teacher `Qwen3.8-27B-UD-IQ4_XS.gguf` @ 192.168.137.3:8080, policy `routine`.

Sequence (3 model attempts, 1 teacher pass):

1. **Attempts 1 & 2 (baseline) failed identically** — `reference_output_exact_match: failed`,
   1.7B emitted the 2-literal `["infrastructure_error","ready_for_review"]`, dropping `"unresolved"`
   from the chained ternary in Excerpt B.
2. **Local teacher pass 1** diagnosed it correctly
   (`failure_classification: model_capability_limit`; diagnosis names the dropped
   `"unresolved"`). Its `candidate_prompt_patch` was prose → `invalid_candidate`;
   no structured patch applied.
3. **Attempt 3 (guidance-only retry) passed** — `reference_output_exact_match: passed`.

Cleanliness of the retry prompt (`out-guidance-only-rerun/attempt-3.prompt.txt`):
- contains **no** `corrected_reference_output` and **no** exact expected array
  `["infrastructure_error","ready_for_review","unresolved"]`;
- contains the allowed guidance fields (`failure_classification`, `teacher_diagnosis`,
  `retry_guidance`, `teacher_parse_status`);
- the literal `unresolved` named in the diagnosis was **already present in the raw
  evidence** (Excerpt B, `... else "unresolved"`) from attempt 1, so the guidance
  points at existing source the 1.7B already saw, not an injected answer.

`trajectory_summary.json`: `disposition=ready_for_review`, `pass=true`,
`first_attempt_pass=false`, `pass_after_local_teacher_intervention=true`,
`successful_intervention_source=local_teacher`, `teacher_intervention_mode=guidance_only`,
`teacher_pass_count=1`, `model_attempt_count=3`, `unresolved=false`.

**Honest classification: (2) — 1.7B success after guidance-only retry.** With the
reference stripped, the 1.7B genuinely re-derived the third literal from the
existing raw evidence on the guidance-only retry. This is a clean guidance-only
capability pass, **not** a reference rescue.

## Standing rule

A post-intervention pass with the reference answer present in the retry prompt is
always (3), never credit as 1.7B capability. After this fix the retry prompt can
no longer carry the reference, so (2)-labeled results are trustworthy.
