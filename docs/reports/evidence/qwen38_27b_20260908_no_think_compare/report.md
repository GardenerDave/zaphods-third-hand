# Qwen3.8-27B No-Think Baseline Comparison

Date: 2026-09-07

## Starting Status

- `git status --short --branch` before changes: `## main...origin/main [ahead 17]`
- Worktree was clean aside from the edits in this task.

## Exact No-Think Mechanism

- The true no-thinking baseline on the current local Qwen3.8 path is the prompt suffix `/no_think`.
- In this repo, the mechanism is surfaced by `local_harness.icm_call.py --final-only`, which appends `/no_think` once to the user prompt.
- The request path does not currently expose a separate lower-level reasoning-disable field that supersedes the prompt contract.
- The new named Qwen3.8 request policy added here is `direct`, and it maps to `append_no_think=True` with no extra reasoning-budget controls.

## Cases Tested

- `A`: routine structured task, thread-safe counter fix.
- `B`: code/reasoning task, earliest-second-occurrence duplicate finder.
- `C`: reasoning-heavy task, zero-sum subarray count.

## Results

### No-think arm

| Task | finish | prompt tokens | completion tokens | prompt tps | gen tps | status |
|---|---|---:|---:|---:|---:|---|
| A | stop | 130 | 348 | 154.24 | 33.12 | PASS |
| B | stop | 275 | 547 | 388.90 | 32.45 | PASS |
| C | stop | 217 | 744 | 304.46 | 32.66 | PASS |

### Preserved baseline for comparison

The preserved low/256 sweep only includes `B` and `C`.

| Task | baseline | finish | prompt tokens | completion tokens | prompt tps | gen tps | rubric |
|---|---|---|---:|---:|---:|---:|---|
| B | low/256 | stop | 269 | 539 | 389.35 | 32.87 | PASS_WITH_EXCESS_REASONING |
| C | low/256 | stop | 211 | 810 | 276.23 | 32.13 | PASS |

For `A`, the closest preserved comparator is the stage1 `low/768` run, which also passed but used 653 completion tokens.

## No-Think vs Low/256

- `B`: no-think stayed correct and was slightly longer on completion tokens (`547` vs `539`), with slightly lower generation throughput but still in the same band. It remained a clean pass.
- `C`: no-think was clearly better on visible output cost (`744` vs `810` completion tokens) and slightly faster on generation throughput while preserving correctness.
- `A`: no-think produced a clean pass and was materially shorter than the nearest preserved structured-task comparator, but there is no preserved low/256 baseline row for this task.

## Interpretation

- The no-think baseline is not just a faster version of `low/256`; it is a distinct request shape with comparable or better correctness on this representative subset.
- It is especially attractive for bounded structured tasks where visible output is the goal and hidden reasoning is not needed.
- The evidence is not strong enough to claim a universal replacement for routine reasoning, because `B` did not clearly beat low/256 on token use.

## Policy Consequence

- Add a distinct Qwen3.8 request policy below `routine`: `direct`.
- Semantics: append `/no_think`, keep the output budget independent, and do not attach reasoning-effort or thinking-budget controls.
- Do not collapse this into worker eligibility or scheduling.

## Local Worker Ladder Plan

Preregister the smallest apples-to-apples comparison set for future scheduler work:

1. `A` structured thread-safety fix.
2. `B` unhashable duplicate finder.
3. `C` zero-sum subarray counter.

Run the same three tasks across:

1. 1.7B local worker.
2. Qwen3.8-27B.
3. 30B-A3B worker.

Keep the following separate in the resulting records:

- worker eligibility;
- request policy (`direct`, `routine`, `serious`, `exceptional`);
- execution outcome;
- transport/infrastructure failures.

Use the smallest worker that qualifies on the set as the default escalation candidate, and treat insufficiency as a reason to escalate only after a demonstrated miss.

## Tests

- `python3 -m pytest local_harness/tests/test_icm_call.py -q`
- Result: `23 passed`
- `git diff --check` passed after the edit set.

## Evidence Path

- `docs/reports/evidence/qwen38_27b_20260908_no_think_compare/run_no_think/`

## Ending Status

- Working tree has local edits in `local_harness/icm_spec.py`, `local_harness/icm_call.py`, `local_harness/tests/test_icm_call.py`, and the new evidence/report artifacts.
- No commit was created in this turn.
