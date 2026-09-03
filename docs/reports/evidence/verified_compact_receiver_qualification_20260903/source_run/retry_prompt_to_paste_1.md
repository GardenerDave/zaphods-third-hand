Supervised Retry Prompt

Validation failure summary:
- validation_status: failed

Validator checks:
- parse_json: passed - Raw model output parsed as JSON.
- required_fields: passed - All required fields are present.
- required_field_types: passed - Required fields have valid types and values.
- observation_grounding: failed - finding[0].evidence[0].path is not in the projected evidence set.
- observation_grounding: failed - finding[1].evidence[0].path is not in the projected evidence set.
- observation_grounding: failed - finding[2].evidence[0].path is not in the projected evidence set.
- observation_findings: passed - findings is a list.
- observation_grounding: failed - Some cited evidence paths were not in the projected evidence set.
- target_authority: not_applicable - Target authority is not applicable to repository observation output.
- requires_reason: passed - Non-empty reason field is present.

Validator diagnostics:
- cited evidence path not projected: evidence_sources/byte_length
- cited evidence path not projected: evidence_sources/byte_length
- cited evidence path not projected: evidence_sources/byte_length

Previous failed output
{
  "findings": [
    {
      "claim": "The compact packet ensures that the source transaction and run identity are preserved during compaction.",
      "evidence": [
        {
          "detail": "The compact packet explicitly derives from the preserved authoritative evidence, ensuring that the source transaction and run identity survive.",
          "path": "evidence_sources/byte_length"
        }
      ]
    },
    {
      "claim": "The compact packet maintains the repository binding integrity during compaction.",
      "evidence": [
        {
          "detail": "The repository binding is preserved and not altered during the compaction process.",
          "path": "evidence_sources/byte_length"
        }
      ]
    },
    {
      "claim": "The compact packet ensures that the output-validation evidence still resolves as expected.",
      "evidence": [
        {
          "detail": "The output-validation evidence still resolves and the expected validation status is recovered from the preserved artifact.",
          "path": "evidence_sources/byte_length"
        }
      ]
    }
  ],
  "reason": "The compact packet is explicitly derived from the preserved authoritative evidence, e
...[trimmed]

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
