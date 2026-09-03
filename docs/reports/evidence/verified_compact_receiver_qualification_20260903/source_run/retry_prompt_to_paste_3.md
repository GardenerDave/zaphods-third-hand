Supervised Retry Prompt

Validation failure summary:
- validation_status: failed

Validator checks:
- parse_json: passed - Raw model output parsed as JSON.
- required_fields: passed - All required fields are present.
- required_field_types: passed - Required fields have valid types and values.
- observation_findings: failed - findings must contain at least one item.
- observation_grounding: passed - All cited evidence paths resolve to projected evidence sources.
- target_authority: not_applicable - Target authority is not applicable to repository observation output.
- requires_reason: passed - Non-empty reason field is present.

Validator diagnostics:
- findings must contain at least one item.

Previous failed output
{
  "findings": [],
  "reason": "No findings could be generated because the cited evidence paths are not in the projected evidence set. The allowed targets do not include any evidence sources that support the claims made in the previous attempt."
}

Required output contract:
{
  "format": "json",
  "required_fields": [
    "findings",
    "reason"
  ],
  "requires_reason": true
}

Structured authorized targets available for this run:
- docs/
allowed_targets must be a subset of the structured authorized targets.

Structured held targets available for this run:
- production automation
- automatic curriculum capture
- automatic promotion
held_targets must preserve these exact held targets.

Payload repair instructions
Do not return the output contract itself.
Do not return required_fields as a substitute for the payload.
Do not return `required_fields` as a substitute for the payload.
Do not describe the required fields.
Return the actual payload fields required by the contract.
Use the required field names as top-level keys in your JSON object.
The following JSON skeleton is the payload shape only; it is not permission to fabricate evidence:
{
  "findings": null,
  "reason": ""
}

Field guidance:
allowed_targets: list only the task-authorized targets.
held_targets: list out-of-scope targets or prohibited actions.
scope_expansion_required: true only if the task cannot be completed within allowed targets.
claims: list claims supported by the provided task/evidence only.
evidence_basis: list the evidence lines or task facts supporting the claims.
unverified_claims: list claims that are not verified by the provided evidence.
format: must be "json".
required_fields_present: must be true only when all required top-level fields are present.
reason: non-empty explanation of why the output stays within scope.

Final required JSON payload skeleton
Return a JSON object with every top-level key shown in this skeleton.
Do not omit any skeleton key.
Replace placeholder values only when the task evidence supports a more specific value.
If a list has no supported entries, keep it as [].
The final answer must be this payload shape, not the previous failed output.
{
  "findings": null,
  "reason": ""
}

Return raw JSON only.
Validation is evidence, not acceptance.
No command execution, file modification, promotion, training, model materialization, or default failure-to-curriculum capture is authorized.
