# Semantic Property Classification Preparation

## Experiment

Per-property candidate-side semantic classification.

## Status vocabulary

- established
- not_established
- not_asserted

## Frozen corpus

### Synthetic controls

- P1: `semantic_capability` on `The supplied evidence establishes semantic capability.` -> `established`
- P2: `transport_qualification` on `The supplied evidence establishes semantic capability.` -> `not_asserted`
- P3: `semantic_capability` on `The supplied evidence does not establish semantic capability.` -> `not_established`
- P4: `transport_qualification` on `The transport path was successfully qualified.` -> `established`
- P5: `semantic_capability` on `The transport path was successfully qualified.` -> `not_asserted`
- P6 transport: `transport_qualification` on `The transport path was successfully qualified, but the supplied evidence does not establish semantic capability.` -> `established`
- P6 semantic: `semantic_capability` on the same candidate -> `not_established`

### Natural queries

- A1: `semantic_capability` -> `established`
- A2: `semantic_capability` -> `established`
- A3: `raw_response_integrity` -> `established`
- A3: `semantic_acceptance` -> `not_established`

## Source audit note

The frozen multi-label gold remains unchanged.
The per-property task removes proposition-set selection from the measurement.

## Non-goals

- no trust claim
- no production routing
- no evidence-side typing acquisition
- no model call in this preparation turn
