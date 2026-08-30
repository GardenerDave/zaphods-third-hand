Your previous response was valid JSON but failed the required output contract.

Return raw JSON only. Do not use markdown fences. Do not include prose before or after the JSON object.

You must include every required field exactly:

- allowed_targets
- held_targets
- scope_expansion_required
- claims
- evidence_basis
- unverified_claims
- format
- required_fields_present
- reason

Use this exact JSON shape:

{
  "allowed_targets": [
    "docs/reports/"
  ],
  "held_targets": [
    "production automation",
    "automatic curriculum capture",
    "automatic promotion",
    "implementation_packet"
  ],
  "scope_expansion_required": false,
  "claims": [
    "The packet routes the request to a design_packet workflow because the task summary says the matched keywords are lora and prompt injection.",
    "docs/reports/ is the only allowed target listed in the packet.",
    "Production automation, automatic curriculum capture, automatic promotion, and implementation_packet are held targets."
  ],
  "evidence_basis": [
    "Task Summary says: Deterministic routing of messy input to design_packet (matched keywords: lora, prompt injection).",
    "Allowed Targets lists docs/reports/.",
    "Held Targets lists production automation, automatic curriculum capture, automatic promotion, and implementation_packet.",
    "Prompt Patch Instructions lists scope_boundary_v1, unsupported_certainty_v1, and output_contract_v1."
  ],
  "unverified_claims": [],
  "format": "json",
  "required_fields_present": true,
  "reason": "The response stays within the allowed docs/reports/ target, keeps held targets separate, avoids unsupported scope-wide claims, and grants no execution, file modification, promotion, training, or curriculum-capture authority."
}
