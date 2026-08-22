# Qwen3 1.7B minimal action-object atom probe

## Closeout

Supplier: Qwen3 1.7B-labeled / 2.032B operative (`2031739904` parameters).
The fresh probe used 8 tasks, one call per task, with 8/8 parse-valid and
8/8 contract-valid responses. No prior evidence was modified.

The two-field interface was:

```json
{"action":"...","direct_object":"..."}
```

The supplier selected the action correctly on 8/8 tasks. It selected the
exact direct object on 4/8 tasks, with all four direct-entity cases correct
and all four subobject cases incorrect under the frozen exact-string score.
All two fields were exact on 4/8.

## Regime results

| Regime | Tasks | Action | Direct object | Both fields | Binding |
|---|---:|---:|---:|---:|---:|
| DIRECT_ENTITY_OBJECT | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| SUBOBJECT_WITH_REFERENCE | 4 | 4/4 | 0/4 | 0/4 | 4/4 |
| Total | 8 | 8/8 | 4/8 | 4/8 | 8/8 |

In the four subobject responses, the supplier returned strings of the form
`subobject in filename`. These were not exact direct-object values and were
not rescored as correct. They did not count as exact substitution of the
mentioned entity alone (`0/8`), but they represent direct-object/reference
conflation in the subobject regime.

| Task | Regime | Expected action/object | Observed action/object | Binding |
|---|---|---|---|---:|
| minimal-atom-001 | direct | scan / opal-register.json | scan / opal-register.json | true |
| minimal-atom-002 | subobject | scan / health line | scan / health line in opal-register.json | false |
| minimal-atom-003 | direct | amend / birch-dossier.json | amend / birch-dossier.json | true |
| minimal-atom-004 | subobject | amend / change note | amend / change note in birch-dossier.json | false |
| minimal-atom-005 | direct | index / cinder-log.json | index / cinder-log.json | true |
| minimal-atom-006 | subobject | index / checksum row | index / checksum row in cinder-log.json | false |
| minimal-atom-007 | direct | dispatch / violet-packet.json | dispatch / violet-packet.json | true |
| minimal-atom-008 | subobject | dispatch / cover memo | dispatch / cover memo in violet-packet.json | false |

## Deterministic decision-critical analysis

For analysis only, requested targets were frozen as the direct object in the
direct-entity regime and as the mentioned entity in the subobject regime.
The model did not emit this boolean. Deterministic equality of the observed
`direct_object` to that target produced the expected binding classification on
8/8 tasks: true for all four direct-entity cases and false for all four
subobject cases.

This does not make the exact semantic extraction correct; it shows that the
tested downstream binding classification remained correct despite the
subobject representation errors.

## Failure localization

- `ACTION_EXTRACTION_FAILURE`: 0/8
- `DIRECT_OBJECT_EXTRACTION_FAILURE`: 4/8
- `MENTIONED_ENTITY_SUBSTITUTED_FOR_DIRECT_OBJECT`: 0/8 exact substitutions
- `INSTRUCTION_VERB_AS_ACTION`: 0/8
- invalid contracts: 0/8

The remaining defect is specific to separating a directly acted-upon
subobject from its containing or mentioned entity. The action field did not
show the prior instruction-verb contamination pattern under the declarative
prompt.

## Interpretation

`PRIMARY_CHARACTERIZATION=MINIMAL_ACTION_OBJECT_ATOM_PARTIAL`

The decision-critical two-field atom is not demonstrated as a reliable exact
semantic extractor because the subobject regime failed 0/4 on direct-object
exactness. The result does not invalidate the richer relation-object
representation; it localizes the supplier limitation to direct-object
representation in subobject clauses.

`REFERENCE_ENTITY_REQUIRED_FOR_DIRECT_TARGET_SELECTION=false` remains the
model-free policy finding. Reference/entity information is optional for the
tested equality policy, although the supplier's conflation of it with the
direct object remains an extraction defect.

`NEXT_DECISION=ISOLATE_DIRECT_OBJECT_BINDING`

This is exploratory evidence only. No production routing or Vogon Printer
change follows from this run.

## Runtime and resources

- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Operative parameters: `2031739904`
- Effective context: `32768`; native training-context cap
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Telemetry: Level 2, `gpu_device_only`, 0.25 seconds
- Latency: mean 1946.864 ms; median 1969.144 ms; p95 2128.008 ms
- Gross device energy: 458.8125 J total; 57.3516 J median task mean
- Energy per correct two-field extraction: 114.7031 J

## Provenance

- Freeze commit: `a5a2ae6c532f1f032ffb37b42238ec9bd8303cf3`
- Run directory: `.work/model_size_supplier_floor/qwen3_1_7b_minimal_action_object_atom/run_20260822T080000Z/`
- Task manifest SHA256: `61e890d33eee08f6879550d100219616df9150bcd73166757c819f6ae6fd4319`
- Schema SHA256: `01223efc8daa32d8a3e11bb77b9d836bd6783bcf0e1e99c89f3e70a71d1ea7ac`
- Response-format SHA256: `5a37e47ccfe02ac5d5bb9bba7a30156fb09525bbdec7ff767dadbd153bd0a88a`
- Driver SHA256: `6d5fe8c8c70d4f4c446069e46ab30fa47d63de9b83a94cf3111ea4b73aeed871`

Supplier calls: 8. Teacher calls: 0. Retries: 0. Escalations: 0.
