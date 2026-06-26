# Failure Training Reports

This directory is for curated reports produced by failure curriculum runs.

Typical report artifacts include:

- cycle summaries
- reviewed curriculum summaries
- dataset manifests
- SFT export manifests
- adapter manifests
- before/after evaluation reports
- regression reports

Generated run outputs should usually live under `.work/failure_training/` or a
private local training workspace.

Curated summaries may be copied here when they are useful as project evidence.
Raw generated datasets should generally stay out of docs unless they are
intentionally tiny fixtures.

## Current Reports

- [`JARVIS_LOCAL_FIRST_SMOKE_SUMMARY.md`](JARVIS_LOCAL_FIRST_SMOKE_SUMMARY.md)
  — local-first evidence-loop smoke summary with private paths generalized.
- [`QWEN3_1_7B_FAILURE_CURRICULUM_LORA_V4_2026-06-25.md`](QWEN3_1_7B_FAILURE_CURRICULUM_LORA_V4_2026-06-25.md)
  — v4 Qwen3-1.7B LoRA rank-8 non-thinking adapter result.
- [`QWEN3_1_7B_FAILURE_CURRICULUM_V4_V5_V6_2026-06-26.md`](QWEN3_1_7B_FAILURE_CURRICULUM_V4_V5_V6_2026-06-26.md)
  — compact v4/v5/v6 comparison and current stopping point.

These reports are evidence for supervised review. They do not promote,
approve, route, rank, or assign a model or adapter.
