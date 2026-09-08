# Qwen3.8-27B Direct Policy Confirmation

Date: 2026-09-07

## Rendered Direct Request

The direct policy rendered a request with:

- `/no_think` present exactly once in the user prompt;
- `chat_template_kwargs` absent;
- `thinking_budget_tokens` absent;
- `max_tokens=1024` explicit.

## Direct Results

| Task | finish | status | completion tokens | prompt tokens | prompt tps | gen tps |
|---|---|---|---:|---:|---:|---:|
| A | stop | PASS | 348 | 130 | 154.24 | 33.12 |
| B | reasoning_only | FAIL | n/a | n/a | n/a | n/a |
| C | reasoning_only | FAIL | n/a | n/a | n/a | n/a |

## Comparison

- Compared to the preserved routine `/no_think` evidence:
  - `A` remains correct.
  - `B` and `C` regress to `reasoning_only`.
- Compared to preserved routine low/256 results:
  - `B` and `C` do not qualify as equivalent because they fail to produce visible content.
  - The direct request envelope therefore does not improve on the prior routine/no-think behavior for this bounded set.

## Conclusion

- `direct` is not empirically qualified for this task set yet.
- Preserve the result as negative evidence.
- Do not promote `direct` as a bounded routing tier based on this confirmation run.
- Do not run the local-worker ladder in this turn.

## Evidence Path

- `docs/reports/evidence/qwen38_27b_20260908_direct_policy_confirm/run_direct/`

## Ending Status

- No code changes were made in this turn.
- `fc1d81b` remains intact.
