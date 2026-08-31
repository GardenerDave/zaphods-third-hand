# Semantic Property Classification Preparation Report

## Corrected multi-label result

The corrected multi-label extraction run remains preserved as a clean measurement of the multi-label contract.
It is mixed/negative on the frozen natural corpus and positive on the synthetic controls.

## Remaining scoring bug and fix

The extraction probe now marks semantic scoring as `not_scored` whenever overall validation fails.
That closes the gap where mechanically invalid outputs could still be counted as semantically scored.

## Gold/source audit

Source-grounded audit v2 preserves the original multi-label gold and records the following:

- A1: candidate text clearly asserts `semantic_capability = established`, but the statement is also premise-heavy and therefore ambiguous under proposition-set extraction.
- A2: candidate text is multi-proposition and clearly asserts `semantic_capability = established` along with other properties.
- A3: candidate text cleanly asserts `raw_response_integrity = established` and `semantic_acceptance = not_established`.

## Task decomposition

- Multi-label extraction: determine the full proposition set and polarity for each proposition.
- Per-property classification: system supplies one property and the model returns `established`, `not_established`, or `not_asserted`.

## Acquisition-only status vocabulary

- `established`
- `not_established`
- `not_asserted`

`not_asserted` compiles to no deterministic IR proposition.

## Frozen next corpus

Natural cases:

- A1 `semantic_capability`
- A2 `semantic_capability`
- A3 `raw_response_integrity`
- A3 `semantic_acceptance`

Synthetic cases:

- P1 through P6 as frozen in the corpus directory.

## Model calls

`0`

## Next experimental question

When proposition selection is removed and one semantic property is queried at a time, can the 30B correctly classify what frozen natural candidate prose asserts about that property?

## What remains unsolved

- evidence-side typing
- independent typing trust
- production routing
- generalization beyond the frozen corpus
