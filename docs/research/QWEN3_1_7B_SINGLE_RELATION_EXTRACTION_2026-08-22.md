# Qwen3 1.7B-labeled single-relation extraction

This is an exploratory atomic extraction probe following the completed
multi-relation IR audit. It does not modify prior evidence.

## Binding and recovery provenance

- Supplier: Qwen3 1.7B-labeled / 2,031,739,904 operative parameters
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Effective/training context: 32768/32768
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Run: `.work/model_size_supplier_floor/qwen3_1_7b_single_relation_extraction/run_20260822T073000Z/`
- Run manifest SHA256: `54b6d9deed2e5352fe7325ade60e1d1b6c9d58b43f99f96fb100eef8a7a96151`
- Aggregate SHA256: `f7c8ab8b581e5d2c3a2b47806aa0cec84346022be989f757bd4bc4c08426176c`
- Task manifest SHA256: `3dcde17bdb19e62a6578bd7cf239e3991f885928355acef9b30438fa0d92c6ee`

The first supplier response was captured before a scorer key-lookup crash.
That response was preserved and scored model-free. A bounded continuation then
called only the remaining seven tasks. Terminal provenance is 8 unique calls,
0 replayed calls, 0 retries, 0 teachers, and 0 escalations.

Per-call energy is incomplete for the recovered first response because the
crash occurred before its power sample artifact was written. No response was
replayed to repair telemetry.

## Results

Parse-valid: **8/8**. Contract-valid: **8/8**.

| Field or metric | Result |
|---|---:|
| `action` exact | 6/8 |
| `direct_object` exact | 8/8 |
| `reference_entity` exact | 4/8 |
| All three fields exact | 2/8 |

By semantic regime:

| Regime | Action | Direct object | Reference entity | All three |
|---|---:|---:|---:|---:|
| `DIRECT_ENTITY_OBJECT` | 2/4 | 4/4 | 4/4 | 2/4 |
| `SUBOBJECT_WITH_REFERENCE` | 4/4 | 4/4 | 0/4 | 0/4 |

Failure classes:

- `SINGLE_RELATION_EXACT`: 2
- `ACTION_EXTRACTION_FAILURE`: 2
- `REFERENCE_ENTITY_EXTRACTION_FAILURE`: 4
- `DIRECT_OBJECT_EXTRACTION_FAILURE`: 0
- `MULTIPLE_SINGLE_RELATION_FIELDS_FAILED`: 0
- invalid contract: 0
- serialization failure: 0

The four subobject clauses all omitted the required `reference_entity`. The two
direct-entity action failures returned `extract` instead of the requested
operation (`inspect` and `catalog`). No reference entity was substituted into
`direct_object` in this single-relation run.

## Interpretation

`PRIMARY_CHARACTERIZATION=REFERENCE_ENTITY_EXTRACTION_FAILURE`

The three-field IR is structurally usable, and direct-object extraction was
8/8, but reference-entity extraction failed uniformly when a subobject was
present. The result does not support reliable single-relation extraction in
both regimes.

`NEXT_DECISION=REPAIR_OBJECT_REFERENCE_EXTRACTION`

The prior multi-relation overload hypothesis remains plausible but is not
isolated by this result because the reference/entity failure survives after
reducing the input to one relation.

## Resource observations

Level-2 GTX1650 device-only measurements for the seven calls with preserved
power samples:

- latency median/mean/p95: 2125.3245 / 2152.615375 / 2339.825 ms
- sampled gross energy mean/median/total: 63.2142857 / 64.2375 / 442.5 J
- all-task energy total: unavailable because the first response was recovered
  without a power artifact
- J per correct three-field extraction: unavailable because the complete
  all-task energy denominator is unavailable

## Execution invariants

- supplier calls: 8
- unique called tasks: 8
- duplicate calls: 0
- teacher calls: 0
- retries: 0
- escalations: 0
- adaptations: 0
- prior raw evidence changed: false
