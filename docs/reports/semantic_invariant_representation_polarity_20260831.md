# Semantic Invariant Representation Polarity Addendum

Date: 2026-08-31

## Why this addendum exists

The first corrected typed representation still needed one more fix: epistemic status had to be consumed by policy evaluation, not merely validated syntactically.

## Defect found

The evaluator accepted `epistemic_status` values, but the policy branch initially flattened assertions into a single property list. That allowed the checker to reason over property identity alone.

## Pre-fix control

The intended negative control for:

- evidence establishes `transport_qualification`
- evidence establishes `bounded_handoff_success`
- candidate asserts `semantic_capability = not_established`

was not clean on the first attempt because the frozen fixture was missing the typed provenance fields required by the validator.

## Corrected evaluation

The checker now keeps separate typed collections for:

- `established_asserted_properties`
- `not_established_asserted_properties`

The policy uses those collections directly.

## Evidence linkage

Each assertion must include exactly one `evidence_ref`, and it must equal the supplied `evidence_id`.

## Frozen matrix

- T1: hold
- T2: hold
- T3: not_applicable
- transport-only positive assertion: pass
- independently established semantic capability: pass
- transport evidence + semantic capability = not_established: pass

## Conclusion

The checker now actually uses epistemic polarity to distinguish an unsupported positive assertion from a correctly bounded negative assertion.

