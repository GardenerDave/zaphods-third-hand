# Erratum: action-object relation pair classification

This additive erratum corrects terminology in the completed action-object
relation closeout. It does not modify or rescore any raw response, validator,
scorecard, aggregate, report, or historical matrix.

## Preserved evidence

The completed run remains 8/8 parse-valid and contract-valid, with exact field
metrics of `action_1=8/8`, `object_1=4/8`, `action_2=8/8`, `object_2=8/8`, all
four relation fields exact on 4/8 tasks, and deterministic selected operation
correct on 7/8 tasks.

The authoritative report and matrix hashes at audit time were:

- report: `f116bf34d647a24596076585b0c9dc799c1791507222da895e060e881f3a1196`
- matrix: `62c150e218d47f3ee0ac5b58297198e19adc6e36166ce108e262497654014075`

## Correct pair terminology

The old pair label `BOTH_RELATIONS_CORRECT` was used when both deterministic
selected operations were correct, even if one or both underlying relation
objects were not exact. The additive terminology is:

- `PAIR_SELECTED_OPERATION_BOTH_CORRECT`: **3/4 pairs**
- `PAIR_ALL_RELATION_FIELDS_BOTH_EXACT`: **0/4 pairs**

Pair audit:

| Pair | Selected operation both correct | All four relation fields exact in both tasks |
|---|---:|---:|
| relation-pair-001 | No | No |
| relation-pair-002 | Yes | No |
| relation-pair-003 | Yes | No |
| relation-pair-004 | Yes | No |

The historical `BOTH_RELATIONS_CORRECT` labels remain unchanged in the raw
closeout matrix; this note supplies the corrected interpretation.

## Object representation audit

The four preserved `object_1` mismatches classify as:

| Task | Expected `object_1` | Observed `object_1` | Classification |
|---|---|---|---|
| relation-002 | expiration detail | beacon-record.json | `REFERENCE_ENTITY_INSTEAD_OF_DIRECT_OBJECT` |
| relation-003 | revision note | revision note for cobalt.json | `DIRECT_OBJECT_PLUS_REFERENCE_ENTITY` |
| relation-006 | checksum ledger | checksum ledger for delta.json | `DIRECT_OBJECT_PLUS_REFERENCE_ENTITY` |
| relation-007 | change package | change package for echo.json | `DIRECT_OBJECT_PLUS_REFERENCE_ENTITY` |

Three errors retain the direct object head and append the parent/reference
entity. One error substitutes the reference entity for the direct object. This
supports, but does not prove exclusively, the hypothesis that collapsing a
semantic object and its owning/reference entity into one string field is part
of the remaining failure surface.

`OBJECT_REFERENCE_REPRESENTATION_CONFOUND=true`

`PRIMARY_CHARACTERIZATION=ACTION_OBJECT_RELATION_PIPELINE_PARTIAL`

`NEXT_DECISION=DEFINE_RELATION_OBJECT_IR`

No model calls were made for this audit.
