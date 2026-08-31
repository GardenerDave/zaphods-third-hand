# Structured Worker-A Prompt

## Task
The LoRA and prompt injection work got messy. Build a bounded design packet.

## Semantic Corrections

### allowed_held_mapping_v1
Copy the supplied `allowed_targets` and `held_targets` into the output without swapping, promoting, demoting, inferring, or adding targets. The only allowed target is `docs/reports/`. The held targets `production automation`, `automatic curriculum capture`, `automatic promotion`, and `implementation_packet` must remain held and must not appear in `allowed_targets`.

### required_fields_boolean_v1
`required_fields_present` is a boolean status field. Emit exactly `true` when all required fields are present. Do not emit a list of field names in `required_fields_present`.

## Output
Return a single JSON object that satisfies the provided response schema.
Do not include `unique_json_keys_v1` or `single_pass_json_object_v1`.
