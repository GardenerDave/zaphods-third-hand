# Semantic Invariant Transport-Capability Probe 2026-08-31

This report preserves the deterministic-enforcement probe for the frozen
transport-versus-capability positive control.

## Existing deterministic machinery

The repository already has machine validators for:

- epistemic observation output structure
- review output structure
- downstream review/gate artifacts

Those validators enforce shape and provenance, but they do not expose typed
semantic claim classes.

## Invariant

Frozen invariant ID:

- `transport_qualification_implies_semantic_capability_not_established_v1`

Frozen artifact:

- [`semantic_invariant_transport_capability_20260831.json`](semantic_invariant_transport_capability_20260831.json)

Hash:

- `0faa1d47b95b603ef48e8ba201958c0cad1dd024e3628c44689d4ceb672f0193`

Abstract rule:

- bounded transport qualification and supervised handoff evidence must not be
  treated as sufficient for semantic/general capability unless the supplied
  evidence explicitly establishes that stronger property.

## Machine-readability assessment

The current worker artifacts are not sufficient for deterministic enforcement.

Observed limitation:

- candidate outputs expose free-form `claim` strings and `reason` text
- candidate outputs do not expose a trusted typed semantic layer for what the
  candidate asserts
- candidate outputs do not expose a trusted typed semantic layer for what the
  evidence establishes
- code would have to interpret natural language to compare asserted and
  established properties

Minimum missing representation:

- a typed assertion/evidence layer

Candidate-side semantic representation:

- `asserted_property`

Evidence-side semantic representation:

- `established_properties`

Recommended starting vocabulary:

- `transport_qualification`
- `semantic_capability`
- `bounded_handoff_success`
- `authority_boundary`
- `review_eligibility`

Trust caveat:

- If the producing model supplies both the free-form claim and its semantic
  type, a deterministic checker can enforce consistency only against the
  model's declared type.
- It cannot independently verify that the type correctly characterizes the
  prose without semantic interpretation.
- For stronger deterministic enforcement, the evidence-side typing should come
  from a trusted source outside the candidate's free-form assertion.

## D1

- Applicability: the invariant conceptually applies
- Result: not mechanically enforceable from the current artifact structure

## D2

- Applicability: the invariant conceptually applies
- Result: not mechanically enforceable from the current artifact structure

## D3

- Applicability: not applicable or outside the frozen scope for the good
  control
- Result: the current artifacts still lack a typed basis for deterministic
  applicability testing

## Causal answer

ZTH cannot yet enforce this invariant deterministically without another model.
The missing piece is a machine-readable claim/property typing layer.

## Next action

Introduce the minimum typed claim metadata needed to distinguish transport
qualification from semantic capability without natural-language interpretation.

## Repository state

This turn made documentation-only additions under `docs/reports/`.
