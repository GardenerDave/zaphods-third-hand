# Qwen3 1.7B-labeled fresh relation-object IR extraction

This is an exploratory fresh generalization probe. It does not modify or
rescore the prior action-object relation run.

## Binding

- Supplier: Qwen3 1.7B-labeled / 2,031,739,904 operative parameters
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Effective context: 32768; training context: 32768
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Telemetry: Level 2, `gpu_device_only`, 0.25-second sampling
- Run: `.work/model_size_supplier_floor/qwen3_1_7b_relation_object_ir_extraction/run_20260822T070000Z/`
- Run manifest SHA256: `2f793004e7334e8b6b8f3827a9953592c0ee12bb29a20317429b6971c785825d`
- Aggregate SHA256: `e401100d4f601ead712669859fa307f79ca5036b18e5a0c5582d9fd02f1a086e`
- Fresh task manifest SHA256: `ad255da0a25d61f76224e5402bcd5ae770f4962dc1ebd53cc460ba8dc43b5469`

## Results

All 8 responses were parse-valid and contract-valid.

| Field or metric | Result |
|---|---:|
| `action_1` | 6/8 |
| `direct_object_1` | 4/8 |
| `reference_entity_1` | 5/8 |
| `action_2` | 6/8 |
| `direct_object_2` | 6/8 |
| `reference_entity_2` | 2/8 |
| Both action fields correct | 6/8 |
| Both direct-object fields correct | 3/8 |
| Both reference fields correct | 1/8 |
| All six fields correct | 0/8 |
| Deterministic selected operation correct | 5/8 |
| Evaluable | 5/8 |
| No direct binding | 0/8 |
| Ambiguous direct binding | 3/8 |
| Selected operation correct in both pair directions | 2/4 |
| All six fields exact in both pair directions | 0/4 |

Fault-containment classes:

- `IR_EXACT_SELECTION_CORRECT`: 0
- `IR_ERROR_SELECTION_STILL_CORRECT`: 5
- `IR_ERROR_SELECTION_INCORRECT`: 0
- `IR_ERROR_SELECTION_UNEVALUABLE`: 3
- invalid contract: 0
- serialization failure: 0

The five decision-correct tasks contained representation errors. The three
unevaluable tasks had multiple direct-target matches after extraction.

## Failure localization

Binding-level observations were:

- `REFERENCE_ENTITY_SUBSTITUTED_FOR_DIRECT_OBJECT`: 4
- `DIRECT_OBJECT_PLUS_REFERENCE_ENTITY_CONFLATION`: 1
- `MULTIPLE_IR_FIELD_FAILURES`: 1
- reference-entity field failures: 2
- action extraction failures: 0

The supplier frequently placed the requested target into a secondary relation's
`direct_object`, causing ambiguity. It also omitted or shifted reference
entities. The refined IR made the failure explicit, but did not eliminate it.

## Resource observations

Level-2 GTX1650 device-only measurements:

- latency median: 4400.784 ms
- latency mean: 4492.03875 ms
- latency p95: 5399.979 ms
- mean gross energy: 110.425 J/action
- median gross energy: 111.05625 J/action
- total gross energy: 883.4 J
- J per correct six-field extraction: not defined (0/8)
- J per correct deterministic selection: 176.68 J

These are descriptive measurements only.

## Interpretation

`PRIMARY_CHARACTERIZATION=REFERENCE_ENTITY_EXTRACTION_FAILURE`

`CANDIDATE_ROUTER_SEMANTIC_IR=false`

The flat six-field contract was structurally reliable, but the semantic IR did
not generalize strongly enough. Reference-entity separation and direct-target
binding remain unstable, with 3/8 ambiguous selections and only 5/8 correct
deterministic selections. This does not establish a generalized router IR.

`NEXT_DECISION=REPAIR_RELATION_BINDING_INTERFACE`

The next repair should prevent reference/entity information from being emitted
as an additional direct target relation before any router integration claim.

## Execution invariants

- supplier calls: 8
- unique called tasks: 8
- duplicate called tasks: 0
- teacher calls: 0
- retries: 0
- escalations: 0
- adaptations: 0
- prior raw evidence changed: false
