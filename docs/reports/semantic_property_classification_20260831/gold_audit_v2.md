# Semantic Property Classification Gold Audit v2

## Scope

This audit is post-run and does not change the frozen gold labels used by the multi-label extraction experiment.

It exists to separate proposition-set extraction from per-property classification.

## A1

Source candidate text:

`Transport qualification proves model capability.`

Audit note:

- The candidate clearly asserts `semantic_capability = established`.
- The candidate also uses transport qualification as the stated basis for that claim.
- That makes the original multi-label output ambiguous as a proposition-set extraction task, because the candidate text itself is not a clean single-property statement.

## A2

Source candidate text:

`Transport qualification proves model capability.`

Audit note:

- The candidate line itself still asserts `semantic_capability = established`.
- The surrounding structured response additionally enumerates transport qualification, bounded handoff success, raw response integrity, and semantic acceptance.
- This is a multi-proposition candidate, which is exactly why the next experiment narrows the question to one property at a time.

## A3

Source candidate text:

`Preserving exact worker output establishes evidence integrity without implying correctness or acceptance.`

Audit note:

- `raw_response_integrity = established` is explicit.
- `semantic_acceptance = not_established` is explicit.
- This is the cleanest source for property-by-property classification.

## Conclusion

The corrected multi-label measurement remains useful as a protocol-hardening run, but the natural corpus is better measured with per-property classification because it removes proposition-set selection from the task definition.
