# Erratum: held-clarification isolation interpretation

This additive erratum corrects interpretation language only. The held-
clarification run, raw responses, validators, aggregate, and matrix remain
unchanged.

Observed results were:

- L, clarification last: FALSE 16/16, correct 8/16, outside 0/8.
- M, clarification before mapping: FALSE 16/16, correct 8/16, outside 0/8.
- A, clarification absent: FALSE 15/16, TRUE 1/16, correct 9/16, outside 1/8.
- L→M flips: 0/16; M→A flips: 1/16; L→A flips: 1/16.

The corrected interpretation is:

`PRIMARY_CHARACTERIZATION=HELD_CLARIFICATION_EFFECT_NOT_SUPPORTED`

`SCOPE_INTERFACE_CANDIDATE_FOUND=false`

`NEXT_DECISION=DECOMPOSE_SCOPE_RELATION`

Clarification position had no observed effect. Removing the clarification
produced one changed observation, but that single observation does not
establish a stable presence effect; seven of eight outside-authority cases
still failed. The broader whole-relation failure remains unresolved.

No raw evidence changed: `false`.

