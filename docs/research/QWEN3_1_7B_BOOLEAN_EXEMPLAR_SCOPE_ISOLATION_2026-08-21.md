# Qwen3 1.7B Boolean Exemplar Scope Isolation

Exploratory prompt-interface isolation; not confirmatory evidence. No teacher,
retry, escalation, prior-run modification, or production-routing change.

## Result

The one-sided boolean exemplar confound is confirmed. On the same 16 crossed
factorial tasks:

| Arm | Interface | Observed true | Observed false | Parse-valid | Contract-valid | Correct |
|---|---|---:|---:|---:|---:|---:|
| T | original `{"scope_expansion_required": true}` | 16/16 | 0/16 | 16/16 | 16/16 | 8/16 |
| F | only exemplar changed to `false` | 0/16 | 16/16 | 16/16 | 16/16 | 8/16 |
| N | no worked boolean object | 0/16 | 14/16 | 16/16 | 14/16 | 7/16 |

Arm T→F changed on all 16 tasks: `EXEMPLAR_FLIP_RATE=16/16=1.0`. The eight
false-branch tasks became correct under Arm F, while the eight true-branch
tasks became incorrect. Arm N was predominantly false; its two contract
failures were raw scalar responses (`false` for `cross-scope-002`, `true` for
`cross-scope-004`) rather than JSON objects.

## Factor-conditioned results

| Arm | Inside authority | Outside authority | READ | MUTATE | Distractor present | Distractor absent |
|---|---:|---:|---:|---:|---:|---:|
| T | 0/8 | 8/8 | 4/8 | 4/8 | 4/8 | 4/8 |
| F | 8/8 | 0/8 | 4/8 | 4/8 | 4/8 | 4/8 |
| N | 7/8 | 0/8 | 3/8 | 4/8 | 4/8 | 3/8 |

The response pattern is exemplar-driven, not an authority-rule solution. Arm
T's true exemplar induces constant true; Arm F's false exemplar induces
constant false; Arm N does not recover balanced rule application and also has
two structural contract failures.

The T→F paired classification is `FLIPPED_WITH_EXEMPLAR` for all 16 tasks.
Eight flips match the expected value and eight oppose it. A flip is therefore
not itself evidence of semantic improvement.

## Interpretation

`PRIMARY_CHARACTERIZATION=BOOLEAN_EXEMPLAR_BIAS_CONFIRMED`

The prior factorial and clean scope evidence are
`PRIOR_SCOPE_EVIDENCE=PROMPT_EXEMPLAR_CONFOUNDED` as semantic measurements,
while remaining valid observations under their original frozen interfaces.
The prior constant-true outputs cannot independently establish recognition of
the outside-authority branch.

The neutral arm does not recover the scope rule. This result does not prove a
general inability to reason about scope; it shows that the prior interface
contained a powerful one-sided output exemplar and that removing it did not
produce a clean semantic measurement in this screen.

`NEXT_DECISION=REBUILD_SCOPE_PROBE_WITH_NEUTRAL_INTERFACE`.

Any rebuilt neutral-interface probe must preserve the no-worked-object rule,
avoid scalar-only output ambiguity, and retain raw validation as authoritative.
It is not executed here.

## Frozen interface bindings

- Arm T suffix SHA256: `8366c50ec74bf035ec68b6126b471d375587f3eb51b5d542758e3cb3b180dcd8`;
- Arm F suffix SHA256: `4b3c6e2fc9c0c87f00aeeb4797c31acadf41c2aae06f72006977f59b5908bd72`;
- Arm N suffix SHA256: `4f6a4608def7da09fe09d21b5507b26e23d7189ff68f7be3927a993087390452`;
- T→F diff SHA256: `c5c705e9107daaa3282e4033f6620c8effe31200892b2fffbda69de1e619df56`;
- T→N diff SHA256: `0651764f6c9018bb8730ca5597bff36de3062ae768efedfd06d1f0a4bff5f361`;
- semantic-rule SHA256:
  `1d0a1b2ec5a0ac88989c1161e2a224741c926c8c50e6bb493ed859fa82058426`;
- crossed task manifest SHA256:
  `2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.

Arm order used the frozen seed `zth-crossed-boolean-exemplar-v1`; permutation
counts were 3, 3, 3, 3, 2, 2.

## Resource measurements

Level-2 remote GTX 1650 device-only measurements:

| Arm | Median latency ms | Mean latency ms | Mean gross J/action | Total gross J |
|---|---:|---:|---:|---:|
| T | 1280.861 | 1015.237 | 34.0075 | 544.12 |
| F | 1312.297 | 1311.930 | 44.0933 | 705.4925 |
| N | 1416.369 | 1365.713 | 41.8313 | 669.30 |

These are descriptive GPU-device measurements, not whole-system energy.

## Provenance and integrity

- run: `.work/model_size_supplier_floor/qwen3_1_7b_boolean_exemplar_scope_isolation/run_20260821T041500Z/`;
- probe manifest SHA256: `bfda106f2a3f4555cb4209b5d2948c89a0ed895363e4f69f4912e90b7d1c37d96`;
- preflight SHA256: `f29c044fd4186a263b63d7dd2be21764297640b42aeed048cdbbd44edd84f2c5`;
- response count: 48; validation count: 48; scorecard count: 48;
- supplier calls: 48; teacher calls: 0; retries: 0; escalations: 0;
- model-free aggregation closeout repaired a factor-label lookup defect after
  inference; no raw response, validator, or scorecard bytes were changed;
- prior factorial run and earlier clean runs remain unchanged.

The machine-readable per-task matrix is adjacent to this report.
