# Qwen3 1.7B Neutral Constrained Scope Probe

Exploratory atomic evidence; not Stage B confirmation and not production
authority.

## Result

The value-neutral prompt plus structure-only JSON Schema constraint removed the
two scalar object-contract failures from the prior neutral arm, but did not
remove the semantic TRUE bias:

- true selected: 16/16;
- false selected: 0/16;
- parse-valid: 16/16;
- contract-valid: 16/16;
- overall correct: 8/16;
- inside authority: 0/8;
- outside authority: 8/8.

| Cell | Correct |
|---|---:|
| READ + INSIDE | 0/4 |
| READ + OUTSIDE | 4/4 |
| MUTATE + INSIDE | 0/4 |
| MUTATE + OUTSIDE | 4/4 |

READ and MUTATE were each 4/8. Distractor-present and distractor-absent were
each 4/8. The confusion matrix was TP=8, FN=0, FP=8, TN=0. There were zero
serialization, contract, or transport failures; all eight errors were scope
decision failures.

## Interface comparison

| Arm | Raw semantic observation | Contract-valid parsed values | Correct |
|---|---|---|---:|
| T, true exemplar | true 16/16 | true 16/16 | 8/16 |
| F, false exemplar | false 16/16 | false 16/16 | 8/16 |
| N, unconstrained neutral | raw literals true=1, false=1, other=14 | true=0, false=14, invalid=2 | 7/16 |
| Neutral constrained | true 16/16 | true 16/16 | 8/16 |

The constrained interface fixed the neutral arm's structural failures but its
semantic selection remained constant TRUE. No worked boolean object, default,
const, example, or enum restriction appeared in the prompt/schema. The
schema's boolean property allowed both values.

## Interpretation

`PRIMARY_CHARACTERIZATION=NEUTRAL_CONSTRAINED_TRUE_BIAS`

The output syntax is now deterministic and structurally valid, but the
supplier still selects TRUE for every task. This is not a clean demonstration
of authority-rule application. The result supports a general TRUE selection
prior under the neutral interface, in addition to the previously confirmed
worked-exemplar sensitivity.

The prior exemplar-based scope evidence remains
`PROMPT_EXEMPLAR_CONFOUNDED` as semantic capability measurement, without
rescoring historical outputs.

`NEXT_DECISION=ISOLATE_BOOLEAN_SELECTION_PRIOR`.

The next experiment should isolate value selection from authority reasoning;
no additional supplier was run here.

## Frozen bindings

- supplier: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`;
- operative parameters: 2,031,739,904;
- artifact SHA256:
  `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`;
- effective context: 32,768, native training-context cap;
- task manifest SHA256:
  `2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`;
- semantic-rule SHA256:
  `1d0a1b2ec5a0ac88989c1161e2a224741c926c8c50e6bb493ed859fa82058426`;
- neutral prompt suffix SHA256:
  `388ac630153ce01948c088f09853713cb1d89e77dec258ed80ca93fae453599b`;
- structure-only schema SHA256:
  `5b9aef0b84726bd3ad42147d84d73d332e69241966301aeb5b4f0dc5881193c5`;
- response-format binding SHA256:
  `99fecf522400406cfedeacb54cc3f3025cc4243b49d3edb3c8ef0b7ed4f3f14a`;
- worked boolean exemplars: 0;
- constraint allows true: true; allows false: true.

## Resource measurement

Level-2 remote GTX 1650 device-only telemetry:

- median/mean/p95 latency: 1384.001 / 1485.953 / 1791.960 ms;
- mean/median gross energy: 46.0052 / 44.1813 J/action;
- total gross energy: 736.0825 J.

These are GPU-device measurements, not whole-system energy.

## Provenance and integrity

- run: `.work/model_size_supplier_floor/qwen3_1_7b_neutral_constrained_scope_probe/run_20260821T082500Z/`;
- probe manifest SHA256:
  `5256a35387db10b91b29071bc049101604b0faee4a201ee2519df6356513e94d`;
- preflight SHA256:
  `8efd03738c300da725f29cd1313debd66cd4f453251ab74170a591427d5f63f6`;
- aggregate SHA256:
  `6e171573feb7bf7b010c6be1777355e6d367930ea05052fdb1a3cb56854ed545`;
- responses/validators/scorecards: 16/16/16;
- supplier calls: 16; teachers/retries/escalations: 0/0/0;
- prior runs and historical evidence unchanged.
