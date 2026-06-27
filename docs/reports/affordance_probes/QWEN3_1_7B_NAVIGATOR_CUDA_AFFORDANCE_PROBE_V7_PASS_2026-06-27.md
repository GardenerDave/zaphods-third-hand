# Qwen3-1.7B Navigator CUDA Affordance Probe v7 Pass

Date: 2026-06-27

## Summary

A real Navigator CUDA-failure affordance candidate was tested through the endpoint probe runner against Qwen3-1.7B on the GTX 1650 server.

This run produced a clean deterministic probe pass while keeping promotion held for review.

## Endpoint result

- Run mode: endpoint
- Model: Qwen_Qwen3-1.7B-Q4_K_M.gguf
- Candidate ID: larql_affordance_candidate_48efff9852ea
- Host profile IDs: navigator_desktop
- qwen_no_think: True
- max_tokens: 256
- elapsed: elapsed_seconds=13.64
- prompt_count: 7
- probe_prompt_count: 3
- regression_prompt_count: 4
- pass: 7 / 7
- needs_review: 0 / 7
- overall_verdict: pass
- promotion_verdict: hold_pending_probe_review

## Per-prompt verdicts

- probe_001 (probe): pass [finish_reason=stop, reasoning_content_present=False]
- probe_002 (probe): pass [finish_reason=stop, reasoning_content_present=False]
- probe_003 (probe): pass [finish_reason=stop, reasoning_content_present=False]
- regression_001 (regression): pass [finish_reason=stop, reasoning_content_present=False]
- regression_002 (regression): pass [finish_reason=stop, reasoning_content_present=False]
- regression_003 (regression): pass [finish_reason=stop, reasoning_content_present=False]
- regression_004 (regression): pass [finish_reason=stop, reasoning_content_present=False]

## Remaining failures

- None in this run.

## Interpretation

This demonstrates guided capability under supervision. The model used the shaped host-affordance record to answer the probe and regression prompts successfully when run with explicit endpoint controls.

This is not autonomous promotion and not proof that LARQL was applied. No LARQL patch, LoRA training, or durable model mutation was performed in this run.

The result shows that the failure record can be shaped into a candidate affordance form that Qwen3-1.7B can use correctly when the affordance is supplied in context.

## Boundary

This report is evidence, not promotion authority. The candidate remains held pending review.

## Source digests

- classifier_version: larql_affordance_probe.v0
- failure_note_sha256: ce43f4f26887d93ca033cbf4219c53296d841ace59e6a345927528edb6f9f3a5
- host_profile_sha256: dd0f5769d33a66ebaf25a99e67ff2357fbb2f9a265774e54cf035993a8c0a06c
