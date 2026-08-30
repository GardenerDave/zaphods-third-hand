## Correction Patch

### Patch: allowed_held_mapping_v1 (candidate)
Copy the supplied allowed_targets and held_targets into the output without swapping, promoting, demoting, inferring, or adding targets. The only allowed target is docs/reports/. The held targets production automation, automatic curriculum capture, automatic promotion, and implementation_packet must remain held and must not appear in allowed_targets.

### Patch: required_fields_boolean_v1 (candidate)
required_fields_present is a boolean status field. Emit exactly true when all required fields are present. Do not emit a list of field names in required_fields_present.

### Patch: unique_json_keys_v1 (candidate)
Emit exactly one top-level JSON object. Emit every required top-level key exactly once. Do not repeat, redefine, append a second copy of, or emit multiple occurrences of any top-level key. Before finishing, ensure the object contains one and only one occurrence of each required key.

### Patch: single_pass_json_object_v1 (candidate)
Construct the response as one JSON object in one pass. Start with {, emit each required top-level key exactly once in the exact order specified below, then close the object with }. Do not emit format, required_fields_present, reason, or any other field as a preamble before this sequence. Do not restart the object, repeat a field, or append a second copy of any field after it has already been emitted.

Required top-level order:
1. allowed_targets
2. held_targets
3. scope_expansion_required
4. claims
5. evidence_basis
6. unverified_claims
7. format
8. required_fields_present
9. reason

After reason, close the JSON object immediately. Emit no additional top-level key.

These corrections constrain output shape only. They grant no execution, promotion, training, or curriculum-capture authority.
