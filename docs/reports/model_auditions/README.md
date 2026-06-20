# Model Audition Reports

This directory contains durable snapshots from ZTH model audition runs.

Model audition reports compare models on repeatable prompts, fixtures, scorer profiles, suites, and boards. They are useful for tracking model behavior over time, but they are not production role assignments.

Some reports use the optional small-model harness, which can download candidate
GGUFs and manage temporary local llama.cpp servers for exploratory evaluation.
That server lifecycle is evidence-gathering support only; it is not production
model-server management or evidence of production readiness.

## Two Audition Evidence Sources

- [`local_harness/auditions/`](../../../local_harness/auditions/README.md) is
  the board/capability-card workflow. Its durable evidence includes capability
  cards and board comparison reports, and it can optionally consume preflight
  manifests.
- [`local_harness/model_auditions/`](../../../local_harness/model_auditions/README.md)
  is the exploratory small-model harness. Its evidence includes raw prompt
  responses, mechanical scores, rollups, and summaries; it does not currently
  consume preflight gates.

The output schemas differ. Keep their disposable run evidence in separate
directories before selecting sanitized reports for this shared report area.
Neither source workflow promotes, approves, assigns, or production-certifies a
model.

## In Plain English

A model audition report says:

> These models were tested this way, on these small probes, and this is what happened.

It does not say:

> This model is now approved as the router, coder, reviewer, or production agent.

That decision belongs to later human review and policy layers.

## What to Preserve

When saving audition results, prefer preserving:

- from the board/capability-card workflow:
  - `comparison.md`
  - `comparison.json`
  - selected `board_capability_card.json` files
  - selected `board_capability_card.md` files
- from the exploratory small-model workflow:
  - a sanitized `summary.md`
  - a sanitized `rollup.json` when machine-readable evidence matters
  - short notes explaining the setup and observed failure modes
- for either workflow:
  - short notes explaining why the result mattered

Do not mix files from the two schemas into one run folder. Avoid preserving
every raw scratch run. Keep `.work/` disposable unless a result has review
value, and do not publish raw responses without explicit sanitization.

The folder example below uses the board/capability-card schema.

## Suggested Report Folder Shape

Use a dated folder name when the report represents a specific comparison run.

Example:

    docs/reports/model_auditions/qwen_local_models_2026-06-18/

Suggested files:

    comparison.md
    comparison.json
    cards/
      qwen25_3b_full_board_smoke.json
      qwen25_coder7b_full_board_smoke.json
      qwen25_7b_instruct_full_board_smoke.json

## How to Read a Comparison Report

Look for:

- overall score;
- suite-level score;
- failure modes;
- runtime;
- missing outputs;
- scorer mismatches;
- prompt or endpoint compatibility problems.

A lower score is not always a worse model. It may indicate:

- the prompt was not appropriate for that model family;
- the output budget was too small;
- the endpoint returned reasoning in a separate channel;
- the scorer expected a stricter shape than the model produced;
- the model was too slow for the current runtime profile.

## Useful Questions

When reviewing a report, ask:

- Did the model actually fail, or did the harness/prompt profile not fit it?
- Were failures deterministic scoring failures or runtime failures?
- Did the model produce useful content in the wrong channel?
- Did the result expose a missing diagnostic?
- Should this become a regression fixture?
- Should the model be retested with a different prompt, timeout, or output budget?

## Current Reports

- `qwen_local_models_2026-06-18/` — comparison of local Qwen model candidates across the baseline audition board.
- `SMALL_MODEL_AUDITION_2026-06-19.md` — exploratory small-model GGUF, endpoint, and prompt observations.

## Safety Reminder

Model audition reports are candidate fit evidence.

They can inform routing, role design, model selection, and future MTNG/ZTH policy layers, but they do not automatically assign production responsibilities.
