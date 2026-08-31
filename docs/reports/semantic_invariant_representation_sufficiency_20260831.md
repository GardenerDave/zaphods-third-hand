# Semantic Invariant Representation Sufficiency

Date: 2026-08-31

## Deterministic Finding

The current free-form worker/evidence artifacts are insufficient for deterministic enforcement because they do not expose a trusted typed representation of:

- what property the evidence establishes
- what property the candidate asserts
- the permitted relationship between those properties

## Minimum Missing Layer

The minimal missing layer is a typed assertion/evidence representation, not a broader ontology.

### Candidate-side typing

Use a controlled `asserted_property` field with a minimal vocabulary such as:

- `transport_qualification`
- `bounded_handoff_success`
- `semantic_capability`
- `raw_response_integrity`
- `semantic_acceptance`

### Evidence-side typing

Use a controlled `evidence_scope.established_properties` field with explicit provenance.

## Trust Caveat

If the producing model supplies both free-form claim text and semantic type, a deterministic checker can only enforce consistency against the declared type. It cannot independently verify that the type correctly characterizes the prose without semantic interpretation.

For stronger deterministic enforcement, the evidence-side typing must come from a trusted source outside the candidate's prose.

## Frozen Invariant

`transport_qualification_implies_semantic_capability_not_established_v1`

Status: `conceptual_only`

SHA-256: `b70b9d1e1a271153cde1e1039cb57fcdaa07f538bce39a2cff4b6f2a3c951f28`

## Typed Fixtures

- T1: hold
- T2: hold
- T3: pass
- Synthetic transport-only control: pass
- Synthetic semantic-capability control: pass

## Conclusion

Given trusted typed semantic inputs, the minimal assertion/evidence representation is sufficient to evaluate the frozen transport-versus-capability invariant without interpreting natural language.

## What This Does Not Establish

- It does not establish semantic typing acquisition.
- It does not establish that a model can self-report the correct typed properties honestly.
- It does not change production observation contracts.

