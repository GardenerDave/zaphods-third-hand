# Qwen3-1.7B Navigator CUDA Affordance Probe

Date: 2026-06-27

## Summary

A real Navigator CUDA-failure candidate was classified as a host-specific affordance problem and tested through the endpoint probe runner against Qwen3-1.7B on the GTX 1650 server.

The runner now supports Qwen no-think mode, endpoint metadata capture, structured slot-fill prompts, multiline field parsing, and nested-answer detection. Promotion remained held throughout.

## Latest endpoint result

- Run mode: endpoint
- Model: Qwen_Qwen3-1.7B-Q4_K_M.gguf
- qwen_no_think: true
- max_tokens: 256
- elapsed: 15.18s
- pass: 5 / 7
- needs_review: 2 / 7
- reasoning_content: 0
- finish_reason: stop on all prompts
- promotion_verdict: hold_pending_probe_review

## Interpretation

This demonstrates guided capability, not autonomous promotion.

The small model can use a host profile to avoid an unsafe CUDA path for `navigator_desktop` and respect split-host boundaries in most cases, but it still has formatting and boundary-explicitness failures that require review.

## Remaining failures

- `probe_002`: slot-fill failure; `ACTIVE_HOST` was left blank.
- `regression_002`: boundary-explicitness failure; answer was cautious but did not explicitly say not to apply the constraint to a different host without matching evidence.

## Boundary

This report is evidence, not promotion authority. The candidate remains held pending review.
