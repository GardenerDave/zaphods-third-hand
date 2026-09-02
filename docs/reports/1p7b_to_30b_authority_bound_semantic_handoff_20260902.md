# 1.7B to 30B Authority-Bound Semantic Handoff

- date: 2026-09-02
- source_run: `.work/operational-dogfood-v1/live-cycle/20260902T180000Z`
- recipient_run: `.work/operational-dogfood-v1/live-cycle/20260902T180000Z-recipient`
- upstream_model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- recipient_model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

## Result

A bounded 1.7B semantic evidence-observation result was produced under transport-level structured output, preserved immutably, validated, and authority-bound deterministically by ZTH. A separate 30B recipient run consumed the exact generated continuation in a distinct run directory and validated successfully.

## What Changed

- Upstream model output is now treated as semantic evidence only.
- ZTH deterministically binds allowed/held scope state around the accepted semantic result.
- Recipient runs now get their own run manifest and downstream output contract.
- The recipient prompt is hash-bound to the generated continuation.

## Acceptance

- upstream semantic validation: passed
- authority binding: passed
- handoff generation: passed
- recipient transport: passed
- recipient validation: passed
- recipient review: accepted

## Notes

- The upstream model was not asked to reproduce deterministic authority facts.
- The downstream recipient consumed the generated continuation rather than a manually reconstructed prompt.
- Historical failed runs under `.work/operational-dogfood-v1/` were preserved.
