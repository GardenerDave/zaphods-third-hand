# Additive audit for the minimal action-object atom

The completed single-relation result remains unchanged: parse/contract 8/8,
action 6/8, direct object 8/8, reference entity 4/8, and all three fields
exact 2/8.

The two action errors emitted `extract`, matching the imperative used in the
prior prompt. This is recorded only as:

`INSTRUCTION_VERB_CONTAMINATION_CANDIDATE=true`

It is diagnostic and not a causal or rescoring claim.

The deterministic target-binding policy uses only:

`normalized(direct_object) == normalized(requested_target)`

It does not require `reference_entity`. Therefore:

`REFERENCE_ENTITY_REQUIRED_FOR_DIRECT_TARGET_SELECTION=false`

The three-field relation IR remains a valid richer representation. This probe
tests the decision-critical two-field atom (`action`, `direct_object`) without
deleting or changing that richer design.

`NEXT_DECISION=TEST_MINIMAL_ACTION_OBJECT_ATOM`

No model calls were made for this audit.
