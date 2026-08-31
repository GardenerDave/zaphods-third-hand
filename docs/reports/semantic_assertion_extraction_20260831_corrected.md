# Semantic Assertion Extraction Addendum

## Pilot integrity finding

The first extraction pass was a protocol-hardening pilot, not the final candidate-only measurement.

The pilot prompt exposed evidence prose to the model, so the natural cases were not clean candidate-only extractions.
The pilot also used a completion budget of 256 tokens, which was too tight for the natural A2 case.

## Corrected protocol

The corrected extraction prompt exposed only:

- candidate prose
- the fixed evidence ID
- the controlled property vocabulary
- the epistemic-status vocabulary

The prompt did not expose:

- evidence file contents
- gold labels
- invariant or routing logic
- reviewer verdicts

The schema enforced the same five-property controlled vocabulary and required exactly one evidence reference per assertion.

## Completion budget

The corrected rerun used a fixed `max_tokens` value of 512 across all seven cases.

## Pilot versus corrected counts

- Pilot model calls: 7
- Corrected model calls: 7

## Pilot interpretation

- A1: semantically mismatched extraction, but under the evidence-content contamination confound.
- A2: mechanical truncation, so semantic scoring was not meaningful.
- A3: valid but incomplete under the same confound.
- X1-X4: clean synthetic successes.

## Corrected seven-case result

### Natural cases

- A1: mechanically valid, but extracted `transport_qualification = established` instead of the frozen gold `semantic_capability = established`.
- A2: mechanically valid, but over-extracted all five controlled properties as established rather than extracting the frozen gold `semantic_capability = established`.
- A3: mechanically valid and exactly matched the frozen gold `raw_response_integrity = established` and `semantic_acceptance = not_established`.

### Synthetic controls

- X1: exact match
- X2: exact match
- X3: exact match
- X4: exact match

## Clean conclusion

Under the corrected candidate-only protocol, the current 30B accurately populated the assertion-side typed IR on the synthetic controls and the good natural control, but it did not reliably reproduce the frozen natural candidate gold for the two bad natural cases.

This is a clean negative for the frozen natural corpus and a clean positive for the synthetic controls.

## What remains unsolved

- evidence-side typing acquisition
- independent typing trust
- production routing
- generalization beyond this frozen corpus
