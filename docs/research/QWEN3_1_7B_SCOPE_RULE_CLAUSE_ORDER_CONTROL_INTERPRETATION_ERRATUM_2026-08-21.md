# Erratum: clause-order control interpretation

This additive erratum corrects interpretation language only. The completed
run, raw responses, validators, aggregate, and matrix remain unchanged.

Authoritative closeout: [QWEN3_1_7B_SCOPE_RULE_CLAUSE_ORDER_CONTROL_2026-08-21.md](QWEN3_1_7B_SCOPE_RULE_CLAUSE_ORDER_CONTROL_2026-08-21.md)

The observed arms were:

- TF: TRUE 16/16, FALSE 0/16, correct 8/16, inside 0/8, outside 8/8.
- FT: TRUE 0/16, FALSE 16/16, correct 8/16, inside 8/8, outside 0/8.
- All 16 paired outputs flipped.

The existing labels remain:

`PRIMARY_CHARACTERIZATION=SCOPE_RULE_ORDER_EFFECT_PARTIAL`

`SCOPE_INTERFACE_STATE=SCOPE_INTERFACE_STILL_UNSTABLE`

Correction: `capability_under_tested_interface=true` is not supported. Neither
tested arm demonstrated balanced scope-rule application; the tested interfaces
produced constant-polarity outputs. The corrected epistemic value is:

`capability_under_tested_interface=false`

Correction: the next decision is:

`NEXT_DECISION=REPAIR_SCOPE_RULE_REPRESENTATION`

The prior `VALIDATE_CANONICAL_SCOPE_INTERFACE_STABILITY` decision was
premature because no balanced canonical candidate was found. This erratum does
not claim that clause order is the only cause; it records that the dual-clause
representation remains unresolved.

Raw evidence changed: `false`.
