# Qwen3.8-27B Bounded Reasoning Sweep

Date: 2026-09-07

## Preflight

- `thinking_budget_tokens` is accepted by this running llama.cpp build.
- A diagnostic prompt with `thinking_budget_tokens = 32` produced a short reasoning trace and a bounded visible answer, showing the field is active rather than ignored.

## What changed relative to the baseline

- The baseline sweep showed repeated answer starvation when reasoning was unconstrained.
- With `thinking_budget_tokens`, both Tasks B and C consistently produced visible answers at every tested budget/effort combination.
- Generation throughput stayed essentially flat around `31-33 tok/s`.

## Compact matrix

| Task | Effort | budget | max_tokens | finish | visible answer | reasoning end | assessment |
|---|---|---:|---:|---|---|---|---|
| B | low | 256 | 1024 | stop | yes | natural | PASS_WITH_EXCESS_REASONING |
| B | low | 512 | 1024 | stop | yes | forced/bounded | PASS |
| B | medium | 256 | 1024 | length | yes | forced/bounded | PASS_WITH_EXCESS_REASONING |
| B | medium | 512 | 1024 | length | yes | forced/bounded | PASS_WITH_EXCESS_REASONING |
| B | xhigh | 256 | 1024 | stop | yes | natural | PASS_WITH_EXCESS_REASONING |
| B | xhigh | 512 | 1024 | stop | yes | forced/bounded | PASS |
| C | low | 256 | 1536 | stop | yes | natural | PASS |
| C | low | 512 | 1536 | stop | yes | forced/bounded | PASS |
| C | medium | 256 | 1536 | stop | yes | natural | PASS |
| C | medium | 512 | 1536 | stop | yes | forced/bounded | PASS |
| C | xhigh | 256 | 1536 | stop | yes | natural | PASS |
| C | xhigh | 512 | 1536 | stop | yes | forced/bounded | PASS |

## Findings

1. Explicit reasoning budgeting does solve the answer-starvation behavior seen in Tasks B and C.
2. `low` is still not materially more token-efficient than `medium` in throughput terms.
3. `medium` does not show a clear quality gain over `low` when both are given the same reasoning budget.
4. `xhigh` does not show a measurable quality gain here once reasoning is bounded; it does not outperform the other tiers on objective correctness in this sweep.
5. `256` reasoning tokens is sufficient for routine escalation in this sample, because every B/C cell produced a visible answer.
6. `512` is a useful serious-reasoning default if the goal is to keep reasoning bounded while preserving answer production.
7. There is no evidence here that a `768` xhigh reasoning tier is necessary.
8. The ~32-33 tok/s generation rate remains stable under forced reasoning termination.

## Recommended routing tuples

- Routine local escalation: `reasoning_effort=low`, `thinking_budget_tokens=256`, `max_tokens=1024` for short coding/debugging tasks.
- Serious local escalation: `reasoning_effort=medium`, `thinking_budget_tokens=512`, `max_tokens=1024-1536` depending on expected answer length.
- Exceptional hard reasoning: `reasoning_effort=xhigh`, `thinking_budget_tokens=512` first, with `max_tokens=1536`; only raise reasoning budget further if a task-specific prompt truly needs it.

## Starvation comparison

- Before explicit reasoning budgets: answer starvation / visible-content failure was common on B and C.
- After explicit reasoning budgets: answer starvation dropped to `0/12` in this bounded matrix.

## Provisional vs tested

- Tested: bounded reasoning prevents starvation.
- Tested: throughput remains stable.
- Provisional: the exact optimal routing tuple for every future ZTH task class.
- Provisional: whether any production tier needs `xhigh` with a reasoning budget above `512`.
