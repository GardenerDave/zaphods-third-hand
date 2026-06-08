# Read-only snippet
# Source: 10_agent_runs/README.md

# Local Agent Runs

Author: [REDACTED]

This folder stores file-mediated local-agent runs for ICM and InternalCodename support work.

Use it when Codex/Nav or [REDACTED_AUTHOR] delegates a bounded task to a local model such as Gemma or Qwen. Local agents should write draft reports, summaries, fixture ideas, and analysis here. Canonical ICM files and app source files should change only after manager review.

Worker agents may process personal planner/runtime data when explicitly delegated. Keep raw personal details out of the manager Codex context by default; hand back sanitized findings, metrics, file paths, and conclusions unless [REDACTED_AUTHOR] explicitly asks for raw detail.

Qwen worker tasks should use `/no_think` or an equivalent final-answer-only request convention when final assistant content is required.

Gemma markdown-output tasks should explicitly request raw markdown and forbid enclosing code fences around the whole response.

Typical run folder:

```text
YYYY-MM-DD_short-task/
  RUN.md
  00_inputs/
  01_fast_gemma/
  02_deep_qwen/
  03_manager_review/
  FINAL_REPORT.md
```

For new single-worker supervised pilot runs, prefer:

```text
YYYY-MM-DD_###_short-task/
  TASK.md
  INPUT.md
  MODEL_REQUEST.md
  OUTPUT.md
  REVIEW.md
  METRICS.json
  ACCEPTED.md
```

`TASK.md` is the full audit record. `MODEL_REQUEST.md` is the compact prompt actually sent to the worker when the full task would waste context or trigger timeouts. `OUTPUT.md` is raw draft output. `REVIEW.md` records manager evaluation. `ACCEPTED.md` is the only promoted artifact that should feed another worker or a Codex prompt.

For this single-worker shape, run the backend validator before handoff, downstream promotion, or commit:

```text
python3 ../XX_backend/validate_agent_run.py YYYY-MM-DD_###_short-task/
```

The validator checks required file presence only. Manager review is still required before any content is promoted.


[truncated after 49 lines]
