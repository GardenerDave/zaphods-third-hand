# 1.7B to 30B Authority-Bound Semantic Handoff Repeatability

- date: 2026-09-02
- source_run: `.work/operational-dogfood-v2/live-cycle/20260902T191000Z/20260902T050813Z`
- recipient_run: `.work/operational-dogfood-v2/live-cycle/20260902T191000Z-recipient-fixed`
- upstream_model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- recipient_model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

## Result

A second bounded run reproduced the authority-bound supervised handoff pattern on a different real task. The 1.7B worker identified one stale roadmap statement, ZTH preserved the raw semantic result, bound authoritative runtime scope deterministically, generated a transaction handoff, and a separate 30B recipient consumed the exact generated continuation and produced a validated downstream conclusion.

## What Changed

- The repeat task used roadmap maintenance rather than the original transport/authority diagnosis.
- The first downstream continuation wording was too loose about the `evidence` shape and produced a validation failure.
- The continuation renderer was tightened so the recipient prompt now says `evidence` must be a non-empty list of `{path, detail}` objects.
- The accepted recipient run then validated successfully on a fresh recipient directory.

## Acceptance

- upstream semantic validation: passed
- review decision: accepted
- transaction handoff: passed
- recipient prompt binding: passed
- recipient validation: passed
- recipient review: accepted

## Notes

- The V2 task was different from V1 and remained bounded to docs/ROADMAP.md maintenance.
- The upstream model did not need to reproduce authority-bearing runtime facts.
- The downstream recipient used the generated continuation rather than a manually reconstructed prompt.
- The remaining friction is prompt-contract wording sensitivity in the downstream continuation, now narrowed by a regression test.
