# Architectural note: operation membership

The completed operation-membership lexical counterbalance remains valid
supplier evidence: 14/16 correct, with 8/8 member and 6/8 non-member
judgments. The archive-specific non-member errors preserve
`PRIMARY_CHARACTERIZATION=OPERATION_LEXICAL_EFFECT_DETECTED`.

The task presented normalized allowed-operation values and a normalized
requested operation. Exact membership over those values is deterministic and
does not require model inference. Therefore the higher-value architectural
responsibility is to use the supplier for factual extraction from evidence and
let deterministic code perform normalization, comparison, and policy
composition.

`MODEL_FREE_MEMBERSHIP_AVAILABLE=true`

`NEXT_DECISION=TEST_FACT_EXTRACTION_PLUS_DETERMINISTIC_POLICY`

This note changes the responsibility assignment for the next exploratory test;
it does not weaken, rescore, or modify the completed lexical experiment or its
raw evidence.
