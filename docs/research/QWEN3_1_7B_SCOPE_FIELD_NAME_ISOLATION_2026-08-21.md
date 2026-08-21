# Qwen3 1.7B-labeled scope field-name isolation

`EXPLORATORY_NOT_CONFIRMATORY`

This paired experiment changed only the output field label in the completed
single-predicate scope representation. It did not modify prior runs or create
Stage B evidence.

## Binding

Supplier: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`; operative parameters: `2031739904`;
artifact SHA256:
`72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`.

Run: `.work/model_size_supplier_floor/qwen3_1_7b_scope_field_name_isolation/run_20260821T200423Z/`

The exact task manifest SHA256 was
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.
The predicate text SHA256 was
`e4f8ed438ccd3fca6d660e4575ce8f3c8931c5818cedc2b21da8869015df21c3`.
The S schema SHA256 was
`5b9aef0b84726bd3ad42147d84d73d332e69241966301aeb5b4f0dc5881193c5`.
The N schema SHA256 was
`b38168065059cf9dec63368bdc93c3023fbd112632644a89639636510c4d0a23`.
The normalized rename diff SHA256 was
`ba199b0bd31052ac60122ae8b1c97f75935c6b85748426eee6082c37be529db6`.

The response-format wrapper name was common across arms. All prompt and schema
differences were attributable to `scope_expansion_required` → `decision_flag`.
The semantic predicate sentence and held-target clarification were unchanged.
No worked boolean exemplar, default, const, or enum was present.

## Execution

There were 32 supplier calls: 16 per arm, with eight S→N and eight N→S
orders. Teacher calls, retries, and escalations were zero. All 32 responses,
validators, and scorecards were preserved. Both arms were 16/16 parse-valid and
16/16 contract-valid.

## Arm results

| Measure | S: `scope_expansion_required` | N: `decision_flag` |
|---|---:|---:|
| TRUE selected | 0/16 | 1/16 |
| FALSE selected | 16/16 | 15/16 |
| Correct | 8/16 | 7/16 |
| Inside-authority correct | 8/8 | 7/8 |
| Outside-authority correct | 0/8 | 0/8 |
| READ correct | 4/8 | 3/8 |
| MUTATE correct | 4/8 | 4/8 |
| Held distractor present correct | 4/8 | 3/8 |
| Held distractor absent correct | 4/8 | 4/8 |
| TP / FN / FP / TN | 0 / 8 / 0 / 8 | 0 / 8 / 1 / 7 |
| Serialization failures | 0 | 0 |
| Contract failures | 0 | 0 |
| Scope-decision failures | 8 | 9 |

Cells:

| Cell | S | N |
|---|---:|---:|
| READ + INSIDE | 4/4 | 3/4 |
| READ + OUTSIDE | 0/4 | 0/4 |
| MUTATE + INSIDE | 4/4 | 4/4 |
| MUTATE + OUTSIDE | 0/4 | 0/4 |

## Paired analysis

There was one S→N output flip, on `cross-scope-009`: S was FALSE and correct;
N was TRUE and incorrect. The paired classifications were:

- `SAME_CORRECT`: 7
- `SAME_INCORRECT`: 8
- `SEMANTIC_CORRECT_NEUTRAL_INCORRECT`: 1
- `SEMANTIC_INCORRECT_NEUTRAL_CORRECT`: 0
- `OUTPUT_FLIP_NO_ACCURACY_CHANGE`: 0

The neutral field did not recover any outside-authority case. Its one TRUE
output was a false positive on an inside-authority task, so it is not evidence
of balanced authority-rule application.

## Resource measurements

Measurements were Level 2, remote read-only, GTX 1650 device-only telemetry at
0.25-second sampling. The 30-second idle baseline averaged 7.363554 W with a
7.38 W peak.

| Measure | S | N |
|---|---:|---:|
| Median latency | 671.954 ms | 1,066.872 ms |
| Mean latency | 737.189 ms | 1,067.860 ms |
| P95 latency | 1,219.916 ms | 1,098.368 ms |
| Mean gross GPU J/action | 22.5145 J | 32.9503 J |
| Median gross GPU J/action | 20.8750 J | 33.0088 J |
| Total gross GPU energy | 360.2325 J | 527.2050 J |

These are descriptive device measurements and do not establish an energy
causal effect of field naming.

## Interpretation

Primary characterization: `SCOPE_FIELD_NAME_EFFECT_NOT_SUPPORTED`.

Interface state: `SCOPE_FIELD_NAME_NOT_CAUSAL`.

The semantic field remained all-FALSE and the neutral field was also
overwhelmingly FALSE. The one neutral-arm TRUE was an inside-branch false
positive and reduced accuracy. Thus field naming does not materially explain
the scope-specific polarity failure in this sample.

Next decision: `ISOLATE_HELD_CLARIFICATION_POSITION`.

The next experiment should preserve the predicate and field contract while
isolating the position/wording of the final held-target clarification. No model
size change is indicated by this result.

`SCOPE_FIELD_NAME_ISOLATION_COMPLETE=true`
