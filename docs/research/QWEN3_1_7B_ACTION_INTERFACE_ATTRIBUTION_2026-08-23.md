# Qwen3 1.7B action-interface attribution closeout

Authoritative freeze commit: `ca37b38`. This fresh paired experiment used 24
independent local Qwen3 1.7B calls: 12 historical `action` interface calls and
12 `action_expression` interface calls. No response was replayed. Teacher,
tool, retry, escalation, 30B, and external calls were zero. Qualification and
production interface changes were false.

## Context correction

The bounded normalizer now consumes a deterministic request context. Presence
expressions normalize to `observe_presence` only in the frozen presence-query
context; direct operations remain distinct; ambiguous and unknown contexts fail
closed. The model-free invariant suite passed. This corrects the previously
unused `request_context` parameter without modifying the historical 12-call
evidence.

## Paired result

| metric | old `action` | new `action_expression` |
|---|---:|---:|
| parse valid | 12/12 | 12/12 |
| contract valid | 12/12 | 12/12 |
| object exact | 12/12 | 11/12 |
| applicable canonical operation correct | 8/8 | 5/8 |
| normalization decision correct incl. fail-closed | 12/12 | 9/12 |
| presence canonical correct | 4/4 | 1/4 |
| direct-operation canonical correct | 4/4 | 4/4 |
| safe target binding | 8/12 | 5/12 |
| authority broadening | 0 | 0 |

Ambiguous requests failed closed 2/2 in both arms; unsupported requests failed
closed 2/2 in both arms. The old arm therefore materially outperformed the new
arm on the same fresh tasks and downstream normalizer.

## Attribution

`ACTION_INTERFACE_EFFECT_ISOLATED=true` for this bounded paired comparison.
The result supports `ACTION_EXPRESSION_INTERFACE_REGRESSION_SUPPORTED=true`
and the bounded candidate
`OLD_ACTION_AS_EXPRESSION_PLUS_DETERMINISTIC_NORMALIZATION`. It does not prove
a universal supplier property, and does not promote or replace any production
interface. The new-interface supplier floor remains undemonstrated.

All 12 tasks were classifiable by the deterministic bounded request grammar,
so `DETERMINISTIC_OPERATION_DERIVATION_POSSIBLE=12/12` and
`MODEL_NECESSITY_FOR_CURRENT_OPERATION_FAMILY=false` for this task family.
This is an audit result only; routing was not changed.

## Resources

| arm | mean latency ms | median latency ms | p95 latency ms | mean gross J | median gross J | total gross J |
|---|---:|---:|---:|---:|---:|---:|
| old | 2060.986 | 2033.282 | 2198.010 | 58.469 | 56.023 | 701.628 |
| new | 2401.905 | 2324.238 | 2701.656 | 70.603 | 69.775 | 847.232 |

These are descriptive GPU-device-only measurements, not causal claims about
prompt wording or general energy behavior.

## Provenance

- responses/call-start records: 24/24;
- model calls: 24; teacher calls: 0; tool calls: 0; retries: 0;
- `MODEL_OUTPUT_GRANTED_AUTHORITY=0`;
- execution driver SHA256: `07d538916ff2c5cec521d6045bb861c4ea38bf4fa242df36866e471fc5c5213f`;
- closeout driver SHA256: `e47673dfd8c995a5a669e666d75441e4ea0735cf6e9fa2894b231545bcb81082`;
- prior normalization closeout driver SHA256: `8310757cc688ba451879336cb7f67f9a11a2b1e428e9450b452372f4711a5d88`;
- qualification change: false.

The full per-task paired rows, contamination classes, normalizer traces, and
raw response references are in the run matrix and the tracked matrix JSON.

## Next decision

`NEXT_DECISION=OLD_ACTION_AS_EXPRESSION_PLUS_DETERMINISTIC_NORMALIZATION`.
No next experiment is executed automatically.
