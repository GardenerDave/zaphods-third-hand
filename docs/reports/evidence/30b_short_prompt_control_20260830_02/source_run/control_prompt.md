DO THIS NOW
Using the accepted design packet above, produce a bounded downstream recommendation identifying the next supervised action, the evidence from the accepted result supporting it, and any unresolved constraint that must remain held.
Do not redo the task that produced the accepted result below. Use that result as completed work.

ACCEPTED PRIOR RESULT
```text
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
```

CONSTRAINTS
- authorized_scope: bounded_supervised_input_only
- allowed_targets:
  - docs/reports/
- held_targets:
  - production automation
  - automatic curriculum capture
  - automatic promotion
  - implementation_packet
- authority_boundaries:
  - No command execution authority is granted.
  - No direct file modification authority is granted.
  - No automatic patch promotion authority is granted.
  - No automatic training authority is granted.
  - No default failure-to-curriculum capture authority is granted.
  - Human review is required before downstream use.

DELIVERABLE
1. Recommended next supervised action
2. Evidence from accepted result
3. Unresolved constraint that must remain held

Produce the recommendation itself. Do not propose creating another report merely to answer this request. Do not restate the upstream task.
