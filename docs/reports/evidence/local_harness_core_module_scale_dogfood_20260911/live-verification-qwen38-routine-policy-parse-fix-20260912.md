# Live verification — `qwen3_8_27b` `routine` request policy (teacher-intervention smoke, post-fix)

Date: 2026-09-12 (run at 2026-09-12T07:33:29Z)
Fix under verification: the `_parse_teacher` response-normalization (tiered JSON extraction) fix, this commit
Endpoint: `JARVIS_LOCAL` = `http://192.168.137.3:8080/v1` (model `Qwen3.8-27B-UD-IQ4_XS.gguf`)
Teacher limit: 1200 completion tokens (loop `call_worker(spec, prompt, 1200)`)
Companion evidence: `live-verification-qwen38-routine-policy-20260912.md` (the pre-fix 5/6 run that this fix resolves)

## Scope

The capability-loop live smoke was re-run after the `_parse_teacher` fix, against the **live** `qwen3_8_27b` endpoint (http://192.168.137.3:8080/v1, model `Qwen3.8-27B-UD-IQ4_XS.gguf`), using the exact loop teacher wiring: `request_policy_name="routine"`, `request_policy.max_tokens=1024`, and the loop's 1200-token ceiling. No external-teacher config, no 1.7B worker change, no escalation-redesign change.

The pre-fix run (companion file) recorded **5/6** proof points passing; the 6th (`parse_teacher_passed`) failed because the live 27B emits a prose preamble, then a `
<thinking>
` open tag, a short reasoning run, a `
</thinking>
` close tag, then a ```json-fenced object — and strict `json.loads` on the whole `message.content` rejected it. The fix recovers the embedded top-level JSON object without weakening the strict schema validation.

## Request policy (bound, routine)

- `ICM_QWEN3_8_27B_REQUEST_POLICY=routine` → spec `request_policy_name="routine"`
- `chat_template_kwargs.reasoning_effort="low"` (bound; NOT `high`/`max`)
- `thinking_budget_tokens=256` (bound; NOT the reasoning-only 8192 default)
- `max_tokens=1024` in spec; the loop's 1200-token ceiling was the effective completion limit
- `append_no_think=False` (no no-think marker injected)
- `finish_reason="stop"` — a normal, complete completion (not a token-limit truncation)

## Provenance (policy-relevant request body, live)

- `request_body_sha256` = `e62febf0191825f81c0fe79ea00e50d401fce86e6e03dcb8ecd0a736eeccd90b`
- `prompt_sha256` = `d62cc203fafae3af17b096cc639fc23e55297890d107663e56638d697002a6bb`
- `raw_response_sha256` = `45da5ea68019f77db0b3f925de8f0245dfb19459c3543c060dacf5f2108c37b0`
- `raw response content sha256` = `fc10ed282beb9c4f88fd823f33411325e1f548ee5ddead2f278926f2546756ae` (computed over the exact `message.content` embedded below)
- prompt length 2774 chars; request body 3260 chars
- `endpoint_alias=JARVIS_LOCAL`, `transport_classification=model_response`
- prompt tokens 767, completion tokens 678, total tokens 1445, cached tokens 0
- server prompt 1664.2 ms; server generation 24042.8 ms; end-to-end 27.3 s

## Proof points (this run)

| # | Proof point | Result |
|---|---|---|
| 1 | `policy_bound_routine` (spec request_policy_name is `routine`) | PASS |
| 2 | `reasoning_effort_low` (chat_template_kwargs.reasoning_effort is `low`) | PASS |
| 3 | `thinking_budget_256` (thinking_budget_tokens is 256) | PASS |
| 4 | `not_reasoning_only` (NOT reasoning-only / not 8192 default) | PASS |
| 5 | `visible_final_completion` (non-empty completion + `stop`) | PASS |
| 6 | `parse_teacher_passed` (strict schema-valid teacher object recovered) | PASS |

**All six proof points pass** (`all_pass=true`). The 6th point — `parse_teacher_passed` — is the one the pre-fix run failed; this run recovers the object.

## Teacher parse (the concrete diagnosis)

The live response again emitted a prose preamble, then the `
<thinking>
` open tag, a short reasoning run, the `
</thinking>
` close tag, and a ```json-fenced object. `_parse_teacher` recovered the embedded top-level JSON object and validated it against the strict teacher schema:

- `teacher_parse_status` = `passed`
- `failure_classification` = `extraction_error_incomplete_scan`
- `teacher_diagnosis` = 'Worker identified zth_task.py (1515 lines) as the largest file, but the evidence block clearly lists run_manual_supervised_attempt.py at 2269 lines as the maximum. The worker appears to have terminated its scan prematurely or failed to compare all ten entries, selecting a locally large value rather than the global maximum. The smallest_file and smallest_lines were correct (icm_spec.py, 230).'
- `retry_guidance` = 'On retry, the worker must compare all ten line counts against each other before selecting the maximum. The correct largest file is run_manual_supervised_attempt.py at 2269 lines. Do not stop scanning after finding a value above 1500.'

The recovered `corrected_reference_output` object:

```json
{
  "file_count": 10,
  "largest_file": "run_manual_supervised_attempt.py",
  "largest_lines": 2269,
  "smallest_file": "icm_spec.py",
  "smallest_lines": 230
}
```

(`candidate_patch_status='invalid_candidate'` is expected here: this prompt is a review-only diagnosis request, so no candidate patch is produced; that field is not one of the six proof points.)

## Preserved exact response (verbatim, byte-for-byte)

The full `message.content` from the live completion is embedded below unchanged (sha256 `fc10ed282beb9c4f88fd823f33411325e1f548ee5ddead2f278926f2546756ae`):

````text
: 230

The worker incorrectly identified `zth_task.py` (1515 lines) as the largest file, when in fact `run_manual_supervised_attempt.py` (2269 lines) is the largest. The worker likely stopped scanning after finding a large file or misread the list.

Now I need to produce a review-only intervention in JSON with the allowed fields:
- failure_classification
- teacher_diagnosis
- candidate_prompt_patch
- retry_guidance
- corrected_reference_output

Let me construct this carefully.
</think>

```json
{
  "failure_classification": "extraction_error_incomplete_scan",
  "teacher_diagnosis": "Worker identified zth_task.py (1515 lines) as the largest file, but the evidence block clearly lists run_manual_supervised_attempt.py at 2269 lines as the maximum. The worker appears to have terminated its scan prematurely or failed to compare all ten entries, selecting a locally large value rather than the global maximum. The smallest_file and smallest_lines were correct (icm_spec.py, 230).",
  "candidate_prompt_patch": "Add an explicit instruction: 'Before emitting output, verify your largest_file by confirming no other listed file has a higher line count. Re-scan all ten entries from top to bottom and confirm the maximum.'",
  "retry_guidance": "On retry, the worker must compare all ten line counts against each other before selecting the maximum. The correct largest file is run_manual_supervised_attempt.py at 2269 lines. Do not stop scanning after finding a value above 1500.",
  "corrected_reference_output": {
    "file_count": 10,
    "largest_file": "run_manual_supervised_attempt.py",
    "largest_lines": 2269,
    "smallest_file": "icm_spec.py",
    "smallest_lines": 230
  }
}
```
````

Note the shape: the content leads with a prose preamble, contains a `
<thinking>
…
</thinking>
` reasoning run, and ends with a ```json-fenced object. Pre-fix, the strict parse of the whole content failed on this shape; the fix recovers the fenced/embedded object.

## Result

**PASS** — all six proof points hold on the live `qwen3_8_27b` `routine` endpoint after the `_parse_teacher` fix. The live 27B produces a `
<thinking>
…
</thinking>
`-then-fenced shape; the fix recovers the strict schema-valid teacher object from it. `raw_response_sha256` is preserved above for byte-level audit.

## Closeout status

Live smoke re-run post-fix: **6/6 proof points PASS** (pre-fix was 5/6). The teacher-intervention parse path now handles the live 27B's `
<thinking>
…
</thinking>
` + fenced-JSON shape without weakening the strict schema validation, and the raw response is preserved.

