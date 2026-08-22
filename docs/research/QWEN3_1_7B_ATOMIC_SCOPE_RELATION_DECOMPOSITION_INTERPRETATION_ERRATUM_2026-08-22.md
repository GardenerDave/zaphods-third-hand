# Atomic scope-relation decomposition interpretation erratum

This additive erratum corrects only the interpretation of the completed
32-call decomposition. Raw responses, validators, scorecards, aggregate, and
run files remain unchanged.

The completed result was:

- `target_authorized`: 13/16 correct, 16/16 parse-valid, 16/16 contract-valid;
- `operation_authorized`: 13/16 correct, 16/16 parse-valid, 16/16 contract-valid;
- deterministic derived scope: 13/16 correct, inside 5/8, outside 8/8;
- both atoms correct simultaneously: 11/16;
- prior direct single-predicate scope: 8/16;
- clarification-absent direct scope: 9/16.

The positive architectural observation is preserved:

`ATOMIC_DECOMPOSITION_IMPROVED_FINAL_SCOPE=true`

`DIRECT_SCOPE_CORRECT=8/16`

`DECOMPOSED_SCOPE_CORRECT=13/16`

`ABSOLUTE_IMPROVEMENT=5/16`

The primary characterization is corrected to:

`PRIMARY_CHARACTERIZATION=BOTH_AUTHORIZATION_ATOMS_PARTIAL`

and the next decision is:

`NEXT_DECISION=REDESIGN_SCOPE_FIXTURES_FOR_ATOMICITY`

Both component judgments retained material errors, and the decomposition did
not produce strong balanced final performance. The prior characterization
`ATOMS_WORK_DIRECT_SCOPE_COMPOSITION_FAILS` was too strong and is superseded
only at the interpretation layer by this erratum.

The old operation atom was defined using target authorization and therefore was
not logically independent of it. The new probe uses independent membership
atoms: `target_allowed` asks only whether the requested target is in the
allowed-target set; `operation_allowed` asks only whether the requested
operation type is in the allowed-operation set.
