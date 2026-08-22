# Qwen3 1.7B-labeled held-clarification position/presence isolation

`EXPLORATORY_NOT_CONFIRMATORY`

This paired three-arm experiment varied only the position or presence of the
held-target clarification in the completed single-predicate scope interface.
It did not modify prior evidence or create Stage B evidence.

## Binding

Supplier: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`; operative parameters: `2031739904`;
artifact SHA256:
`72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`.

Run: `.work/model_size_supplier_floor/qwen3_1_7b_held_clarification_position_isolation/run_20260822T004908Z/`

The exact task manifest SHA256 was
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.
The main predicate SHA256 was
`6374ed0659f09f20ee33377f5da145035d8bbeadddf7d66e998d24bb3a61af0c`.
The mapping sentence SHA256 was
`a2dc46ba3dd2394963bd7f9cf9cc591ce8866e3108e2e11172109ffbef05c8af`.
The clarification sentence SHA256 was
`6a9cc9d36dd7001af8342650c19caf33268568deca4321f2c93d0627e4410950`.
The L/M/A diff hashes were, respectively:

- L→M: `e37f67e9c8ccb527b311d088df775a375a448b657a9353aae596e5a907866c92`
- M→A: `24eb92a1fdeaf387fc2ae1e39a65c8ebb74f6eb1ed61e9c8c63d68b9ec16596d`
- L→A: `e045e380aec1b3cae550f98ac2560a4dbd316200425696ea67fae6356a740aad`

Arm L matched the completed single-predicate prompt byte-for-byte. Arm M
moved only the identical clarification before the output-mapping sentence.
Arm A removed only the clarification. The output field, schema, predicate
meaning, and task evidence were fixed. No worked boolean exemplar was present.

## Execution

There were 48 supplier calls: 16 per arm, with six temporal permutations
assigned as 3/3/3/3/2/2. Teacher calls, retries, and escalations were zero.
All 48 responses, validators, and scorecards were preserved. Every arm was
16/16 parse-valid and 16/16 contract-valid.

## Arm results

| Measure | L: clarification last | M: clarification before mapping | A: clarification absent |
|---|---:|---:|---:|
| TRUE selected | 0/16 | 0/16 | 1/16 |
| FALSE selected | 16/16 | 16/16 | 15/16 |
| Correct | 8/16 | 8/16 | 9/16 |
| Inside-authority correct | 8/8 | 8/8 | 8/8 |
| Outside-authority correct | 0/8 | 0/8 | 1/8 |
| READ correct | 4/8 | 4/8 | 4/8 |
| MUTATE correct | 4/8 | 4/8 | 5/8 |
| Held distractor present correct | 4/8 | 4/8 | 5/8 |
| Held distractor absent correct | 4/8 | 4/8 | 4/8 |
| TP / FN / FP / TN | 0 / 8 / 0 / 8 | 0 / 8 / 0 / 8 | 1 / 7 / 0 / 8 |
| Serialization failures | 0 | 0 | 0 |
| Contract failures | 0 | 0 | 0 |
| Scope-decision failures | 8 | 8 | 7 |

Cells:

| Cell | L | M | A |
|---|---:|---:|---:|
| READ + INSIDE | 4/4 | 4/4 | 4/4 |
| READ + OUTSIDE | 0/4 | 0/4 | 0/4 |
| MUTATE + INSIDE | 4/4 | 4/4 | 4/4 |
| MUTATE + OUTSIDE | 0/4 | 0/4 | 1/4 |

## Pairwise and distractor analysis

Pairwise output flips were:

- L→M: 0/16;
- M→A: 1/16;
- L→A: 1/16.

The only flip was `cross-scope-007`: L and M emitted FALSE incorrectly, while
A emitted TRUE correctly. It was an outside-authority MUTATE task with a held
distractor. No other outside-authority task was recovered.

For held-distractor-present tasks, L and M were 4/8 correct and A was 5/8;
A selected TRUE once and FALSE seven times. For distractor-absent tasks, all
three arms were 4/8 correct and selected FALSE on every task. The single
recovery therefore occurred in the presence stratum, but one observation is
insufficient to establish a stable interaction.

## Resource measurements

Telemetry was Level 2, remote read-only, GTX 1650 device-only at 0.25-second
sampling. The 30-second idle baseline averaged 7.381074 W with a 7.39 W peak.

| Measure | L | M | A |
|---|---:|---:|---:|
| Median latency | 1,004.053 ms | 1,056.424 ms | 864.987 ms |
| Mean latency | 885.802 ms | 1,060.877 ms | 944.251 ms |
| P95 latency | 1,035.181 ms | 1,083.062 ms | 1,122.133 ms |
| Mean gross GPU J/action | 28.5673 J | 33.2825 J | 28.0020 J |
| Median gross GPU J/action | 32.6663 J | 33.6300 J | 28.0663 J |
| Total gross GPU energy | 457.0775 J | 532.5200 J | 448.0325 J |

These are descriptive device measurements and do not establish causal energy
effects of prompt position or presence.

## Interpretation

Primary characterization: `HELD_CLARIFICATION_EFFECT_PARTIAL`.

Position effect: not observed. L and M were identical on every task. Removing
the clarification in A produced one correct outside-authority TRUE response,
but seven outside-authority failures remained. Thus clarification presence
changed one observation, while neither position nor presence yielded balanced
authority-rule application.

No canonical scope interface was found. The result does not support a clean
recency effect, and it does not justify a model-size change.

Next decision: `REPAIR_HELD_CLARIFICATION_WORDING`.

The clarification remains a plausible, semantically useful interface factor,
but its causal effect is only partial in this sample. A future wording repair
must preserve the intended safeguard while testing whether the supplier can
still select the outside-authority branch.

`HELD_CLARIFICATION_POSITION_ISOLATION_COMPLETE=true`
