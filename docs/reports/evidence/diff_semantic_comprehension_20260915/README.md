# diff_semantic_comprehension_20260915

**Task family:** `diff_semantic_comprehension` — a bounded single-diff semantic
comprehension task: from the inlined ~10.4K-char unified diff of real commit
`47cf409` (the guidance-only teacher retry-prompt fix in
`local_harness/supervised_capability_loop.py`), extract 7 exact facts: 2 new
symbol names, 2 counts, 1 summary key/value pair, and 1 boolean.
`exact_json` validator (strict dict equality).

**Models:**
- Worker: `Qwen_Qwen3-1.7B-Q4_K_M.gguf` (toolless, coder slot, port 8081, fixture inlined)
- Local teacher: `Qwen3.8-27B-UD-IQ4_XS.gguf` (reference-blind, `guidance_only`
  intervention mode, auto-resolved `routine` policy) — **configured but never
  invoked** because the worker passed.
- External teacher: **unconfigured** (`ZTH_EXTERNAL_TEACHER_COMMAND` not set) —
  no effect, since no intervention was needed.

**Endpoint:** `JARVIS_LOCAL`
**Task id:** `diff_semantic_comprehension_20260915`
**Run date:** 2026-09-14 (UTC)
**Terminal review state:** `ready_for_review` — a genuine capability verdict
(first-attempt pass), not an infrastructure error.

## What this preserves

One genuine bounded run of the ZTH supervised capability loop over the
diff-comprehension fixture. It records a **first-attempt pass by the 1.7B
worker with zero interventions** (`model_attempt_count: 1`,
`teacher_pass_count: 0`, `first_attempt_pass: true`,
`disposition: ready_for_review`), plus the independent re-verification of all
7 reference facts against the real diff.

The expected answer was hidden from the worker; the single worker prompt
carries the full diff and definitions inline and **does not** expose
`expected_output` or any answer field. (The diff itself contains the answer
values by construction — that is the point of the task — but the exact answer
object was never pre-stated to the model.)

## Genuine 1.7B worker result: 1/1 attempt, EXACT PASS

| Field | Expected | Worker output (attempt 1) |
|-------|----------|---------------------------|
| `new_helper_function_name` | `_guidance_only_teacher_payload` | `_guidance_only_teacher_payload` ✓ |
| `new_module_constant_name` | `_REFERENCE_BEARING_FIELDS` | `_REFERENCE_BEARING_FIELDS` ✓ |
| `reference_bearing_field_count` | `3` | `3` ✓ |
| `call_sites_no_longer_serializing_full_payload` | `2` | `2` ✓ |
| `summary_key_added` | `teacher_intervention_mode` | `teacher_intervention_mode` ✓ |
| `summary_value_added` | `guidance_only` | `guidance_only` ✓ |
| `reference_still_preserved_in_teacher_records` | `true` | `true` ✓ |

Deterministic checks: `json_parse` **passed**, `reference_output_exact_match`
**passed**. `validation_status: passed`, `transport_classification:
model_response`, `finish_reason: stop`, 93 completion tokens (well within the
768 budget — no truncation).

## Reference facts independently re-verified against the real diff

All 7 expected values were re-derived directly from
`git show 47cf409 -- local_harness/supervised_capability_loop.py` (not from
the fixture):

1. **New helper function:** the diff adds `+def _guidance_only_teacher_payload`.
2. **New module constant:** the diff adds
   `+_REFERENCE_BEARING_FIELDS = frozenset({...})`.
3. **Reference-bearing field count:** the frozenset literal contains exactly
   3 quoted strings (`corrected_reference_output`, `candidate_prompt_patch`,
   `candidate_prompt_patch_raw`).
4. **Call sites no longer serializing the full payload:** exactly 2 removed
   (`-`) lines contain `json.dumps` (the two retry-prompt sites), both
   replaced by the guidance-only helper call.
5. **Summary key added:** the summary dict gains
   `+"teacher_intervention_mode": "guidance_only"`.
6. **Summary value added:** `guidance_only` (same line).
7. **Reference still preserved in teacher records:** `true` — the diff's own
   comment states the reference-bearing fields are "kept in the durable
   teacher record + curriculum"; only the *retry prompt* is sanitized.

## Capability finding (new information)

This is a **new task family** for the 1.7B capability map and the result is
the opposite of the two previously probed families:

- `local_harness_core_module_scale` (file counting over inlined directory
  evidence): 1.7B failed exact matching (misidentified max).
- `claim_supersession_reviewed_v1` (temporal current-vs-superseded
  reconciliation): 1.7B 0/4 exact.
- **`diff_semantic_comprehension` (this run): 1.7B 1/1 exact, first attempt,
  no intervention.**

Interpretation: the 1.7B's weakness is not "reading long inlined text"
(2789 prompt tokens were handled without issue) but **temporal/causal
reconciliation and cross-item comparison** (largest-of-many, current-vs-
superseded dating). Bounded *extraction from a single self-contained artifact*
— named symbols, small exact counts, a key/value pair, a boolean — is within
its demonstrated capability. This refines the routing guidance: single-diff /
single-artifact fact-extraction tasks may be assigned to the 1.7B;
comparison and temporal-reconciliation tasks remain above it.

## Teacher notes

The local 27B teacher was fully configured (`ZTH_CAPABILITY_TEACHER_NAME=
qwen3_8_27b`, base URL 8080, model `Qwen3.8-27B-UD-IQ4_XS.gguf`, max_tokens
1200, `routine` policy auto-resolved by the default-routine guard in
`icm_spec.py:resolve_worker_spec`) and would have been reference-blind
(`guidance_only` mode, per `47cf409`). It was **never invoked**: the loop
only escalates to the teacher after a failed worker attempt, and there was
exactly one (passing) attempt. No teacher artifacts exist for this run, and
none are fabricated here.

## Operational note (non-capability)

The first launch of this run used `python3 local_harness/supervised_capability_loop.py
...` (script path) and failed at import with
`ModuleNotFoundError: No module named 'local_harness'` — an invocation
convention error, not a model or framework failure. The loop imports
`local_harness.*` and must be run as `python3 -m
local_harness.supervised_capability_loop` from the repo root. Re-run with the
module invocation succeeded; the failed launch produced no run artifacts.

## Failure taxonomy for this session's run

| Item | Classification |
|------|----------------|
| First-attempt worker pass | **Capability success** (genuine; re-verified) |
| `ModuleNotFoundError` on first launch | **Operational/invocation** error (not capability, not framework defect) |
| Teacher / external escalation | **Not reached** (no failure to intervene on) |

No framework machinery was modified. No Historian infrastructure work was
required.

## Artifacts

See `genuine_raw_evidence/` (8 files; hashes in `../archive_manifest.json`):
`fixture.json`, `attempt-1.{prompt.txt,raw.json,validation.json,metadata.json}`,
`trajectory.jsonl`, `trajectory_summary.json`, `run_stdout.txt` (the
successful run's stdout; stored as `.txt` because the repo's `.gitignore`
excludes `*.log`).
