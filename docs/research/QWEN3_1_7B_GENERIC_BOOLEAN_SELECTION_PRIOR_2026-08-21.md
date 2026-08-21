# Qwen3 1.7B Generic Boolean Selection Prior Probe

Exploratory non-semantic calibration; not scope evidence, Stage B evidence, or
production authority.

## Result

Clause order materially changed selection:

| Arm | Rule order | True selected | False selected | Correct | KAPPA correct | LAMBDA correct |
|---|---|---:|---:|---:|---:|---:|
| TF | true/KAPPA first | 16/16 | 0/16 | 8/16 | 8/8 | 0/8 |
| FT | false/LAMBDA first | 8/16 | 8/16 | 16/16 | 8/8 | 8/8 |

Both arms were 16/16 parse-valid and 16/16 contract-valid. There were no
serialization, contract, or transport failures.

The paired TF→FT results were:

- SAME_CORRECT: 8/16, all KAPPA-7 tasks;
- FLIPPED_WITH_ORDER: 8/16, all LAMBDA-4 tasks;
- SAME_INCORRECT: 0/16;
- OTHER: 0/16.

The flip count was 8/16. Every flip changed the TF incorrect TRUE response to
the FT correct FALSE response.

## Interpretation

`PRIMARY_CHARACTERIZATION=RULE_ORDER_PRIMACY`

The supplier did not show a generic TRUE selection prior across both arms:
the false-first arm selected both values correctly. Instead, the true-first
clause dominated the LAMBDA-4 cases. This is a generic calibration finding,
not a scope-semantic finding.

`GENERIC_TRUE_PRIOR=NOT_SUPPORTED`

The result identifies clause order as a material interface confound. The
existing scope rule's clause order therefore requires a paired order control
before attributing its TRUE bias to scope reasoning.

`NEXT_DECISION=CONTROL_SCOPE_RULE_CLAUSE_ORDER`

No further supplier was run.

## Fixed calibration

- tasks: 16;
- KAPPA-7: 8, expected true;
- LAMBDA-4: 8, expected false;
- field: `decision_flag`;
- scope/authority terminology findings: 0;
- worked boolean exemplars: 0;
- structure-only schema permits true and false;
- TF→FT rule-order difference was the only semantic arm change;
- arm execution order was balanced 8 TF→FT and 8 FT→TF.

## Resource measurement

Level-2 remote GTX 1650 device-only telemetry:

| Arm | Median latency ms | Mean latency ms | P95 latency ms | Mean gross J/action | Total gross J |
|---|---:|---:|---:|---:|---:|
| TF | 488.334 | 541.744 | 963.530 | 12.6122 | 201.795 |
| FT | 518.485 | 578.500 | 1008.643 | 15.5092 | 248.148 |

These are GPU-device measurements, not whole-system energy.

## Provenance and integrity

- run: `.work/model_size_supplier_floor/qwen3_1_7b_generic_boolean_selection_prior/run_20260821T083500Z/`;
- task manifest SHA256:
  `c1a025ccc700322745a403ad4008918eef7ca3ce860404ea20d52b9d41d11172`;
- probe manifest SHA256:
  `52f7945cc2d5dece86d8dbbaa90e377acaa348b64d294886f2910af84359f86a`;
- preflight SHA256:
  `93fc7f69ea93a9c866b0782623c34a8db33a5d6840959f32d4367cf317bb77ce`;
- aggregate SHA256:
  `02e91a4d1b2ac97184c7df1a8453336621905216f18df97b7a399d55ed14b760`;
- supplier calls: 32; teachers/retries/escalations: 0/0/0;
- prior evidence unchanged.
