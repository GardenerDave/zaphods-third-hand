# Qwen3.8-27B Qualification Sweep

Date: 2026-09-07

## Preflight

- `GET /v1/models` succeeded.
- Returned model identity matched `Qwen3.8-27B-UD-IQ4_XS.gguf`.
- A minimal completion request succeeded.

## Result

| Task | Effort | max_tokens | finish | prompt tok | completion tok | prompt tps | gen tps | Assessment |
|---|---|---:|---|---:|---:|---:|---:|---|
| A | low | 768 | stop | 124 | 653 | 168.8 | 32.95 | PASS |
| A | medium | 768 | length | 98 | 768 | 136.1 | 32.62 | TRUNCATED_BUT_REASONING_VALID |
| A | xhigh | 768 | stop | 136 | 709 | 178.0 | 32.42 | PASS_WITH_EXCESS_REASONING |
| B | low | 768 | length | 269 | 768 | 338.6 | 32.20 | OTHER_FAILURE |
| B | medium | 768 | length | 243 | 768 | 317.4 | 32.12 | OTHER_FAILURE |
| B | xhigh | 768 | length | 281 | 768 | 351.9 | 32.00 | OTHER_FAILURE |
| C | low | 768 | length | 211 | 768 | 272.4 | 31.90 | TRUNCATED_BUT_REASONING_VALID |
| C | medium | 768 | length | 185 | 768 | 245.9 | 31.85 | OTHER_FAILURE |
| C | xhigh | 768 | length | 223 | 768 | 286.1 | 31.73 | OTHER_FAILURE |
| A | medium | 1024 | stop | 98 | 801 | 136.2 | 32.45 | PASS |
| C | low | 1024 | stop | 211 | 810 | 276.2 | 32.13 | PASS |
| C | medium | 1024 | length | 185 | 1024 | 247.8 | 31.88 | TRUNCATED_BUT_REASONING_VALID |
| C | xhigh | 1024 | length | 223 | 1024 | 286.3 | 31.76 | TRUNCATED_BUT_REASONING_VALID |
| C | xhigh | 1536 | length | 223 | 1536 | 293.9 | 31.91 | TRUNCATED_BUT_REASONING_VALID |

## Findings

- `medium` is a reasonable default for normal escalation, but it is not always enough at 768 tokens.
- `low` does not meaningfully reduce generation throughput versus `medium`; both are about 32 tok/s.
- `xhigh` did not show a quality win on Task C within this sweep. It consumed more reasoning tokens, but still truncated.
- `A-medium` and `C-low` both needed 1024 to finish cleanly.
- `C-xhigh` still truncated at 1536, though the reasoning trajectory remained productive.
- `reasoning_content` is surfaced in raw responses and can consume most or all of the budget while visible `content` remains empty.
- `cached_prompt_tokens` was zero on all first-pass calls and appeared only on `C-xhigh-1536` after the prompt was partly cached.

## Policy

- Default routing: `medium`.
- Minimum practical `max_tokens`: `low=768`, `medium=1024`, `xhigh=1536+`.
- Route `xhigh` only for tasks where long hidden reasoning is acceptable and visible answer length can be short.
- Do not route routine problems to `xhigh` by default.

## Notes

- Task B was a poor discriminator for this model under this budget: it produced reasoning-only truncations across all efforts.
- The observed generation throughput stayed essentially constant across efforts.
