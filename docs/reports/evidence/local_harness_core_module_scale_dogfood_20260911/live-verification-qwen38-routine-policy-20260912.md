# Live verification — `qwen3_8_27b` `routine` request policy (teacher-intervention smoke)

Date: 2026-09-12
Fix under verification: `92f9fa4` (`ICM_QWEN3_8_27B_REQUEST_POLICY="routine"`, config-only)
Endpoint: `JARVIS_LOCAL` = `http://192.168.137.3:8080/v1` (model `Qwen3.8-27B-UD-IQ4_XS.gguf`)
Teacher limit: 1200 completion tokens (loop `call_worker(spec, prompt, 1200)`)

## Scope

Bounded live smoke of the **exact** loop teacher wiring
(`supervised_capability_loop._teacher_prompt` → `call_worker(spec, prompt, 1200)` →
`_parse_teacher`), command-scoped to `ICM_QWEN3_8_27B_REQUEST_POLICY=routine`, against the
live 27B endpoint. Closes out the missing live verification for the config-only fix `92f9fa4`.

## Result: FAIL on 1 of 6 proof points (5/6 pass)

| # | Proof point | Result |
|---|-------------|--------|
| 1 | Request policy bound to `routine` | **PASS** — `spec.request_policy_name=routine`, `spec.request_policy_env=routine` |
| 2 | `reasoning_effort=low` | **PASS** — `chat_template_kwargs.reasoning_effort="low"` |
| 3 | `thinking_budget_tokens=256` | **PASS** — provenance `thinking_budget_tokens=256` |
| 4 | Response NOT `reasoning_only` | **PASS** — `status=ok`, `finish_reason=stop`, 688 completion tokens |
| 5 | Visible final completion | **PASS** — `message.content` non-empty and contains the JSON object |
| 6 | `_parse_teacher` accepts it | **FAIL** — `json.loads` on whole content → `Expecting value` → `teacher_parse_status=failed` |

**Bottom line:** the `routine` policy **empirically bounds reasoning and eliminates the
`reasoning_only` / budget-exhaustion failure mode** that broke teacher intervention pre-fix
(points 1–5 verified against the live endpoint). But `_parse_teacher` still rejects the
response (point 6), so the teacher intervention is **not** accepted end-to-end. Do **not**
read this as "the intervention now works".

## Concrete parse-failure diagnosis (point 6, diagnose-only)

The 27B's `message.content` is **not bare JSON**. It is:

1. A **reasoning preamble** — the model's chain-of-thought emitted *into the visible content*
   (e.g. "The worker incorrectly identified `zth_task.py` … Now I need to produce a JSON
   response … Let me construct this carefully.").
2. A literal `
</think>

` thinking tag, also in the visible content.
3. A **markdown code fence** (triple-backtick `json` block) wrapping a **valid, correct** JSON object.

`_parse_teacher` (`local_harness/supervised_capability_loop.py:300-320`) runs a strict
`json.loads` on the *entire* `content`. Because the content starts with the reasoning preamble
(not an opening brace), `json.loads` fails with `Expecting value` and `teacher_parse_status` is
recorded as `failed` — even though the JSON object inside the fence is valid and all five allowed
fields are correct (`file_count=10`, largest `run_manual_supervised_attempt.py`/2269, smallest
`icm_spec.py`/230).

Root cause: the live 27B endpoint does **not** separate the model's reasoning into a distinct
`reasoning_content` channel; thinking is emitted inline into `message.content` (with the
`
</think>

` tag) and the model additionally wraps its JSON answer in a markdown fence. This is a
**distinct** failure from the original `reasoning_only` bug and is neither exhibited nor
resolved by the `routine` policy, which only bounds the reasoning budget.

## Preserved exact response (verbatim)

- `request_body_sha256`: `e62febf0191825f81c0fe79ea00e50d401fce86e6e03dcb8ecd0a736eeccd90b`
- `raw_response_sha256`: `c1a73bb376d1c6dcb8c72c0336ac4b7004c6376ddb15f302031d01da02c9d5c6`
- `prompt_sha256`: `d62cc203fafae3af17b096cc639fc23e55297890d107663e56638d697002a6bb`
- `request_policy_env`: `routine` · `reasoning_effort`: `low` · `thinking_budget_tokens`: `256` · `max_tokens`: `1200`
- `status`: `ok` · `finish_reason`: `stop` · usage: `prompt_tokens=767`, `completion_tokens=688`
- `elapsed_ms`: `28202.485`
- `teacher_parse_status`: `failed` · `teacher_diagnosis`: `Teacher output was not JSON: Expecting value`

Exact `message.content` (verbatim, including the leaked reasoning preamble, the `
</think>

` tag, and the markdown fence):

````text
: 230

The worker incorrectly identified `zth_task.py` (1515 lines) as the largest file, when in fact `run_manual_supervised_attempt.py` (2269 lines) is the largest. The worker likely stopped scanning early or misread the list.

Now I need to produce a JSON response with the allowed fields:
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
  "teacher_diagnosis": "The worker correctly identified file_count=10 and smallest_file=icm_spec.py (230 lines), but misidentified the largest file as zth_task.py (1515 lines) instead of run_manual_supervised_attempt.py (2269 lines). The worker appears to have stopped scanning the evidence list before reaching the final entry, treating the last value it processed (1515) as the maximum rather than continuing to the actual last line of the block (2269). This is a bounded extraction failure, not a prompt ambiguity issue.",
  "candidate_prompt_patch": "Add an explicit instruction: 'Scan ALL ten lines of the evidence block before determining the maximum and minimum. The list is sorted by filename, NOT by line count, so the largest file is not necessarily the last entry, but you must check every entry.'",
  "retry_guidance": "Retry with the patched prompt. The task is deterministic and the evidence is fully provided inline; no external state is needed. Expect exact match on all five fields.",
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

## Closeout status

- Points 1–5 are **empirically verified** on the live endpoint: the `routine` policy bounds
  reasoning (`reasoning_effort=low`, `thinking_budget_tokens=256`) and the response completes
  visibly (`finish_reason=stop`, 688 completion tokens) rather than exhausting into
  `reasoning_only`.
- Point 6 **fails**: the intervention is still not accepted by `_parse_teacher` because the 27B
  leaks its reasoning (plus the `
</think>

` tag and a markdown fence) into `message.content`, so the content is not bare JSON.
- No documentation was flipped to "empirically verified" for an "intervention now succeeds"
  claim, because the acceptance proof (point 6) failed. No committed doc over-claims success:
  `config.example.env` (the `routine` policy comment) and this evidence dir's `README.md` (the
  pre-fix `reasoning_only` run record) are both accurate as-is.
- `genuine_raw_evidence/` and `archive_manifest.json` were **not** altered.
