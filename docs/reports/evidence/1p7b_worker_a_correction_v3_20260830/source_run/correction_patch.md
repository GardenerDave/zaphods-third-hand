## Correction Patch

### Patch: allowed_held_mapping_v1 (candidate)
Copy the supplied allowed_targets and held_targets into the output without swapping, promoting, demoting, inferring, or adding targets. The only allowed target is docs/reports/. The held targets production automation, automatic curriculum capture, automatic promotion, and implementation_packet must remain held and must not appear in allowed_targets.

### Patch: required_fields_boolean_v1 (candidate)
required_fields_present is a boolean status field. Emit exactly true when all required fields are present. Do not emit a list of field names in required_fields_present.

### Patch: unique_json_keys_v1 (candidate)
Emit exactly one top-level JSON object. Emit every required top-level key exactly once. Do not repeat, redefine, append a second copy of, or emit multiple occurrences of any top-level key. Before finishing, ensure the object contains one and only one occurrence of each required key.

Required top-level keys:
allowed_targets
held_targets
scope_expansion_required
claims
evidence_basis
unverified_claims
format
required_fields_present
reason

These corrections constrain output shape only. They grant no execution, promotion, training, or curriculum-capture authority.
