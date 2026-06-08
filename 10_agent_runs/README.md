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

To execute the worker call and write `OUTPUT.md` plus `METRICS.json` in one step, use `python3 local_harness/run_single_worker.py <run-folder> <worker> ...` from the repository root, then review the generated files before updating `REVIEW.md` and `ACCEPTED.md`.

For slow or small-context workers, keep `MODEL_REQUEST.md` aggressively small. The first real build-log compression pilot succeeded only after two larger prompts timed out. Later pilots validated compact requests for `coder7`, `handoff7`, and `router3`.

Validated `coder7` compression pilots:

- `LOCAL-0007`: build/test log compression, accepted without substantive correction.
- `LOCAL-0008`: error-log compression, accepted with edits.
- `LOCAL-0009`: artifact-only git-diff compression, accepted.
- `LOCAL-0017`: real app verification-log compression, accepted with risk wording correction.

For `coder7` verification-log compression, scope risk claims to the supplied log. A passing build log does not prove runtime behavior, test coverage, or security status.

Validated `handoff7` prompt-packing pilots:

- `LOCAL-0010`: accepted-artifact testing brief, accepted with manager edits.
- `LOCAL-0011`: implementation-brief compression, accepted with manager edits.

Validated `router3` routing pilots:

- `LOCAL-0013`: broad simple task classification, accepted at 7/7 correct.
- `LOCAL-0014`: handoff-readiness classification, partial at 6/8 correct.
- `LOCAL-0015`: nine-case adjacent-label contrast, failed by timeout.
- `LOCAL-0016`: compact three-case adjacent-label contrast, accepted at 3/3 correct.

For future `router3` checks, prefer compact sanitized label sets and small contrast groups. Do not repeat broad adjacent-label sweeps unless model performance or timeout strategy changes.

Track each nontrivial local-agent run in `AGENT_RUNS.csv`.
