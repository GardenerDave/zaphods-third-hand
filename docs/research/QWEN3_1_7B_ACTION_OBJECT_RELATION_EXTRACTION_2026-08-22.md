# Qwen3 1.7B-labeled action-object relation extraction

This is an exploratory decomposition probe, not production-router or Stage B
evidence. It follows the completed target-bound action extraction result
(`47f300b09a96ab192346a724d900192905d6d1ba`, 5/8 scalar target-bound
operation extraction) and tests whether the supplier can emit two local
action/object relations for deterministic selection.

## Binding and provenance

- Supplier: Qwen3 1.7B-labeled / 2,031,739,904 operative parameters
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Effective context: 32768; training context: 32768
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Telemetry: Level 2, `gpu_device_only`, 0.25-second sampling
- Final run: `.work/model_size_supplier_floor/qwen3_1_7b_action_object_relation_extraction/run_20260822T061500Z/`
- Final run manifest SHA256: `6a9e129f287b5600202ff98ce65e0b691858830f8aa3037894938f433b66957a`
- Final aggregate SHA256: `761278e7b4fdbe11790938f004192c268339852e2bebe7bc6f747befd22c74ad`
- Task manifest SHA256: `0f4f8dd2191eed6067fa2af411fb17317cf20e5f7e2c65868e39f35c44368734`
- Schema SHA256: `9b821473a876e8aedf733bb99918f9c0629c8c5e58d7732df4a3614045948271`

The first prepared run, `run_20260822T060000Z`, stopped during non-generative
idle-telemetry serialization before any supplier call. It contains no response,
validator, or scorecard and is preserved as a preflight failure. The corrected
driver was committed as `72c9468` and a fresh prepared run was used for
inference.

## Design

The model returned exactly four strings: `action_1`, `object_1`, `action_2`,
and `object_2`. Deterministic code compared each extracted object with the
frozen requested target and selected the unique matching action. Zero matches
were unevaluable; multiple matches were ambiguous. No authorization, scope,
policy, membership, boolean, or worked-output decision was requested.

The fresh task set contained 8 tasks and 4 matched role-reversal pairs. Each
pair used the same target and two verbs while reversing which verb was directly
bound to the target. Expected selected positions were balanced 4 first / 4
second, with no perfect action-identity or position shortcut.

## Results

Parse-valid: **8/8**. Contract-valid: **8/8**.

| Measure | Result |
|---|---:|
| `action_1` exact | 8/8 |
| `action_2` exact | 8/8 |
| `object_1` exact | 4/8 |
| `object_2` exact | 8/8 |
| All four relations exact | 4/8 |
| Deterministic selected operation correct | 7/8 |
| Evaluable selections | 7/8 |
| Unevaluable selections | 0/8 |
| Ambiguous bindings | 1/8 |
| Secondary-action selections | 0/8 |
| Fully correct role-reversal pairs | 3/4 |

The one failed selection was `relation-002`: the supplier assigned the target
to both extracted objects, producing `AMBIGUOUS_RELATION_BINDING`. Three object
extraction errors were contained by deterministic selection:
`relation-003`, `relation-006`, and `relation-007`. In each, the supplier
included the target in the secondary object phrase, but the direct target
relation remained recoverable. No action-field errors occurred.

By expected selected position:

- first position: 4/4 selected-operation correct; 4/4 all relations exact;
- second position: 3/4 selected-operation correct; 0/4 all relations exact;
  the difference reflects object phrase resolution, not a wrong action head in
  the three evaluable cases.

Pair classifications:

- `relation-pair-001`: `ONE_DIRECTION_CORRECT`
- `relation-pair-002`: `BOTH_RELATIONS_CORRECT`
- `relation-pair-003`: `BOTH_RELATIONS_CORRECT`
- `relation-pair-004`: `BOTH_RELATIONS_CORRECT`

## Resource observations

Level-2 device-only measurements on the GTX 1650:

- latency median: 2764.4785 ms
- latency mean: 2743.5935 ms
- latency p95: 2945.141 ms
- gross energy mean: 76.22125 J/action
- gross energy median: 75.15625 J/action
- gross energy total: 609.77 J
- idle baseline: 7.359091 W mean, 7.39 W peak, 222.6125 J over 30.062816 s

These are descriptive measurements only and are not causal energy comparisons.

## Interpretation

`PRIMARY_CHARACTERIZATION=ACTION_OBJECT_RELATION_PIPELINE_PARTIAL`

The relation interface materially outperformed the prior scalar target-bound
operation result (7/8 deterministic selections here versus 5/8 scalar
selections previously), and 3/4 role-reversal pairs were fully correct. It did
not demonstrate a fully reliable relation pipeline: only 4/8 complete relation
objects were exact, one pair produced an ambiguous target binding, and object
phrase resolution remained imperfect.

The bounded architectural implication is:

`MODEL_ROLE=SEMANTIC_RELATION_EXTRACTION`

The supplier can provide useful local action relations, while deterministic
code should continue to own target matching and policy composition. The result
does not establish a universal model capability or parameter floor.

`NEXT_DECISION=REPAIR_TARGET_ACTION_BINDING_INTERFACE`

The next repair should address object-reference representation and ambiguity
before treating this intermediate representation as stable. No next probe was
executed in this closeout.

## Execution invariants

- supplier calls: 8
- teacher calls: 0
- retries: 0
- escalations: 0
- adaptations: 0
- prior evidence modified: false
- production routing changed: false

