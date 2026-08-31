# Semantic Invariant Scope Addendum

Date: 2026-08-31

## Scope defect

The evaluator originally allowed `hold` and `pass` outcomes to be produced even when the frozen invariant antecedent did not apply. That made the invariant leak outside its declared scope.

## Antecedent semantics

`antecedent_match: "all"`

Rationale:

- The frozen invariant is intentionally about the combined transport qualification + bounded handoff boundary.
- Out-of-scope evidence must resolve to `not_applicable`, not to a semantic judgment.

## Out-of-scope controls

- S0 positive: `not_applicable`
- S1 negative: `not_applicable`

## Corrected frozen matrix

- T1: hold
- T2: hold
- T3: not_applicable
- Operational in-scope assertion: pass
- In-scope capability established without capability evidence: hold
- In-scope capability not established: pass
- In-scope capability established with independent capability evidence: pass
- Out-of-scope capability established: not_applicable
- Out-of-scope capability not established: not_applicable

## Result/applicability rule

- `not_applicable` requires `applicable == false`
- `pass` requires `applicable == true`
- `hold` requires `applicable == true`

## Conclusion

The checker now both consumes epistemic polarity and respects the frozen invariant's declared evidence scope without inspecting natural language.

