# Semantic Invariant Representation Correction Addendum

Date: 2026-08-31

## Why this addendum exists

The first prototype in `580d427` is preserved as first-pass evidence, but it was premature to treat it as final sufficiency evidence because the known-good control exposed a missing epistemic dimension.

## Corrected finding

The corrected representation needs:

- a typed property
- a typed epistemic status
- an evidence linkage
- a typed evidence scope

Free-form prose remains non-authoritative.

## Corrections made

1. T3 was re-encoded so that `raw_response_integrity` is established and `semantic_acceptance` is not established.
2. T3 is now frozen to a single expected invariant outcome: `not_applicable`.
3. Assertion `evidence_refs` now resolve to a stable evidence identifier.
4. The checker emits internally consistent `result` and `applicable` values from the typed inputs.

## Frozen invariant

`transport_qualification_implies_semantic_capability_not_established_v1`

Status: `conceptual_only`

SHA-256: `66bbcd09a020d9388a9b0365eba2a6bc8e8680b563926b027eeda2dadaf74b01`

## Corrected frozen results

- T1: hold
- T2: hold
- T3: not_applicable
- Synthetic transport-only: pass
- Synthetic independently-established capability: pass

## What this still does not solve

- semantic typing acquisition/trust
- production contract changes

