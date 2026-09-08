# Qwen3.8 Local Capability Ladder

Date: 2026-09-08

## Starting Status

- HEAD: `ab8f5ab` (`Record direct Qwen38 policy confirmation`)
- Worktree was clean before these changes except for the edits in this turn.

## Scope

This report normalizes the current local-worker evidence for capability routing.
It keeps worker identity separate from request policy and records only evidence
that already exists in the repo.

## Normalized Metric Schema

See [`normalized_metric_schema.json`](./normalized_metric_schema.json).

## Raw Field Availability

### Qwen3.8 evidence

- Prompt token count: present.
- Prompt-eval / prefill duration: present in the curl timing payload as `prompt_ms`.
- Prefill tokens/sec: present in the curl timing payload as `prompt_per_second`; also derivable from `prompt_tokens / (prompt_ms / 1000)`.
- Completion token count: present.
- Generation/decode duration: present in the curl timing payload as `predicted_ms`.
- Decode tokens/sec: present in the curl timing payload as `predicted_per_second`.
- Total request latency: not exposed in the preserved report artifacts.
- Finish reason: present.
- Reasoning-token count: not exposed directly. The preserved evidence exposes `reasoning_content` and finish reason, but not a separate reasoning-token counter.

### 1.7B evidence

- Prompt token count: present.
- Prefill duration: not exposed in the preserved artifact.
- Prefill tokens/sec: not derivable from the preserved artifact.
- Completion token count: not exposed in the preserved artifact.
- Decode duration: not exposed in the preserved artifact.
- Decode tokens/sec: not derivable from the preserved artifact.
- Total request latency: not exposed in the preserved artifact.
- Finish reason: not exposed in the preserved artifact.
- Reasoning-token count: not exposed in the preserved artifact.

### 30B-A3B evidence

- Prompt token count: present.
- Prefill duration: not exposed in the preserved artifact.
- Prefill tokens/sec: not derivable from the preserved artifact.
- Completion token count: present.
- Decode duration: not exposed in the preserved artifact.
- Decode tokens/sec: not derivable from the preserved artifact.
- Total request latency: not exposed in the preserved artifact.
- Finish reason: present on the endpoint response.
- Reasoning-token count: not exposed in the preserved artifact.

## Qualification Status

- `qwen3_8_27b/direct`: `experimental_unqualified`
- `qwen3_8_27b/routine`: preserved as qualifying evidence on the bounded A/B/C set
- `1.7B default`: no A/B/C evidence was rerun in this turn
- `30B-A3B qualified path`: no A/B/C evidence was rerun in this turn

## Reused Evidence

- Direct confirmation: [`docs/reports/evidence/qwen38_27b_20260908_direct_policy_confirm/report.md`](../qwen38_27b_20260908_direct_policy_confirm/report.md)
- No-think comparison: [`docs/reports/evidence/qwen38_27b_20260908_no_think_compare/report.md`](../qwen38_27b_20260908_no_think_compare/report.md)
- Stage 1 sweep: [`docs/reports/evidence/qwen38_27b_20260907/report.md`](../qwen38_27b_20260907/report.md)
- 1.7B structured output evidence: [`docs/reports/evidence/1p7b_structured_output_qualification_20260830/control_constrained/local_model_call.json`](../1p7b_structured_output_qualification_20260830/control_constrained/local_model_call.json)
- 30B-A3B structured evidence: [`docs/reports/evidence/verified_compact_receiver_qualification_20260903/source_run/local_model_call.json`](../verified_compact_receiver_qualification_20260903/source_run/local_model_call.json)

## Ladder Comparison

| Task | 1.7B qualified path | Qwen3.8 routine + final-answer hint | Qwen3.8 direct | Qwen3.8 serious | 30B-A3B qualified path |
|---|---|---|---|---|---|
| A | not rerun here | unnecessary | qualified on preserved A | not rerun here | not rerun here |
| B | not rerun here | qualified on preserved B | not qualified | not rerun here | not rerun here |
| C | not rerun here | qualified on preserved C | not qualified | not rerun here | not rerun here |

## Tuple Results

### A

- Smallest qualifying tuple: `Qwen3.8/direct`
- Next successful escalation tuple: not needed from preserved evidence
- Additional reasoning changed correctness: no preserved evidence of a correctness change for A
- Latency/cost penalty of escalation: not applicable from preserved evidence

### B

- Smallest qualifying tuple: `Qwen3.8 routine + final-answer hint`
- Next successful escalation tuple: no stronger tuple was rerun in this turn
- Additional reasoning changed correctness: yes, direct regressed to `reasoning_only`
- Latency/cost penalty of escalation: direct did not qualify; routine remained qualified and is the bounded comparator

### C

- Smallest qualifying tuple: `Qwen3.8 routine + final-answer hint`
- Next successful escalation tuple: no stronger tuple was rerun in this turn
- Additional reasoning changed correctness: no preserved evidence that more reasoning improves correctness over routine for C
- Latency/cost penalty of escalation: routine used 744 completion tokens in the preserved no-think comparison versus 810 in low/256

## Capability vs Infrastructure

- Qwen3.8 stage1 sweep: infrastructure failure only, because the stage1 curl files in the preserved run all returned `URLError` and the summary captured only that transport failure state.
- Direct-policy confirmation: capability failure on B and C, not infrastructure failure.
- No-think comparison: capability success on A/B/C, with bounded visible-output cost differences.

## Scheduler Readiness

The current evidence is enough to justify a first pluggable `smallest-qualified`
policy for the Qwen3.8 family only at the level of:

1. honor capability eligibility;
2. treat direct as experimental/unqualified;
3. prefer routine + final-answer hint where it is the smallest qualified tuple;
4. keep room for later escalation to serious or 30B-A3B when lower-cost tuples fail.

It is not enough yet to justify a fully general scheduler across the whole local
stack, because the A/B/C ladder was not rerun contemporaneously for the 1.7B and
30B-A3B workers in this turn.

## Contemporaneous Run Attempt

The missing 1.7B/router and 30B-A3B/handoff tuples were attempted on the exact
A/B/C prompts, but all six calls failed before model response with
`No route to host`.

- 1.7B/router:
  - A: transport failure
  - B: transport failure
  - C: transport failure
- 30B-A3B/handoff:
  - A: transport failure
  - B: transport failure
  - C: transport failure

Because these were uniform preflight/network failures, they do not change
capability qualification. The evidence proves:

- configured endpoint unreachable;
- current binding unverified.

It does not by itself prove `.env.local` was stale or that a replacement
endpoint exists.

## Validation

- `python3 -m pytest local_harness/tests/test_icm_call.py -q`
- `git diff --check`

## Evidence Paths

- [`docs/reports/evidence/qwen38_local_capability_ladder_20260908/normalized_metric_schema.json`](./normalized_metric_schema.json)
- [`docs/reports/evidence/qwen38_27b_20260908_direct_policy_confirm/`](../qwen38_27b_20260908_direct_policy_confirm/)
- [`docs/reports/evidence/qwen38_27b_20260908_no_think_compare/`](../qwen38_27b_20260908_no_think_compare/)
- [`docs/reports/evidence/qwen38_27b_20260907/`](../qwen38_27b_20260907/)
- [`docs/reports/evidence/1p7b_structured_output_qualification_20260830/control_constrained/local_model_call.json`](../1p7b_structured_output_qualification_20260830/control_constrained/local_model_call.json)
- [`docs/reports/evidence/verified_compact_receiver_qualification_20260903/source_run/local_model_call.json`](../verified_compact_receiver_qualification_20260903/source_run/local_model_call.json)

## Ending Status

- Working tree updated with the minimal policy-status correction, schema artifact,
  ladder artifact, transport-failure evidence, and documentation language fix.
- No automatic scheduling implementation was added.
