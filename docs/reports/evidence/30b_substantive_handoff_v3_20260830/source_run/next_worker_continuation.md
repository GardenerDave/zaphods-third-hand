Continue from the accepted previous-worker result. Do not redo the original worker task.

# ZTH Executable Continuation Prompt

## Next-Worker Directive
Continue from the accepted previous-worker result. Do not redo the original worker task.

## Already Completed
- transaction_id: orch_manual_20260830t000001z
- lifecycle_state: HANDOFF
- review_decision: accepted
- validation_status: passed
- downstream_use_gate: allowed
- handoff_status: prepared
- handoff_reason: Handoff remains supervised and bounded by downstream-use gate status.
- next_step_summary: Use reviewed output as bounded input for the next supervised step.
- next_step_objective: Using the accepted previous-worker result as completed work, produce the actual review-ready downstream cleanup implementation plan now. The plan must contain: (1) an ordered sequence of concrete cleanup actions, (2) the specific files/components or artifact classes each action affects, (3) a validation criterion for each action, and (4) unresolved or held work that must not be activated. Do not recommend that another worker create this plan. Produce the plan itself in this response.

### Accepted Previous-Worker Result
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

### Bounded Original Task
```text
The LoRA and prompt injection work got messy. Build a bounded design packet.
```

### Perform Now
Using the accepted previous-worker result as completed work, produce the actual review-ready downstream cleanup implementation plan now. The plan must contain: (1) an ordered sequence of concrete cleanup actions, (2) the specific files/components or artifact classes each action affects, (3) a validation criterion for each action, and (4) unresolved or held work that must not be activated. Do not recommend that another worker create this plan. Produce the plan itself in this response.

### Transition Summary
Use reviewed output as bounded input for the next supervised step.

### Authorized Scope
bounded_supervised_input_only

### Allowed Targets
```json
[
  "docs/reports/"
]
```

### Held Targets
```json
[
  "production automation",
  "automatic curriculum capture",
  "automatic promotion",
  "implementation_packet"
]
```

### Inherited Authority Boundaries
```json
{
  "attempt": [
    "No command execution authority is granted.",
    "No direct file modification authority is granted.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Human review is required before downstream use."
  ],
  "decision": [
    "Review decision is not command execution authority.",
    "No direct file modification authority is granted.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Downstream use must remain supervised."
  ],
  "gate": [
    "Downstream-use gate is not command execution authority.",
    "Downstream-use gate is not file modification authority.",
    "Downstream-use gate is not patch application authority.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Downstream use must remain supervised."
  ],
  "handoff": [
    "Handoff packet is not command execution authority.",
    "Handoff packet is not file modification authority.",
    "Handoff packet is not patch application authority.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Next step must remain supervised."
  ],
  "validation": [
    "Validation is evidence, not acceptance.",
    "No command execution authority is granted.",
    "No direct file modification authority is granted.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Human review is required before downstream use."
  ]
}
```

### Second-Worker Output Contract
Return the downstream continuation result only.
State how you used the accepted prior result, confirm scope compliance, and report any unresolved issue preventing continuation.
Do not redo the first-worker task.

### Provenance
- transaction_id: orch_manual_20260830t000001z
- run_id: manual_supervised_attempt_20260830t000001z
- first_worker_identity: manual_operator_provided_model_output
- selected_next_worker_identity: qwen3-30b
- raw_model_output_path: .work/operator_handoffs/30b_substantive_handoff_v3_20260830/20260830T000001Z/raw_model_output.txt
- raw_model_output_sha256: adbbf7c43a9436426596e2ebd8911c4ed41d4bf7958c164f4f21469192c7f064
- handoff_packet_path: .work/operator_handoffs/30b_substantive_handoff_v3_20260830/20260830T000001Z/handoff_packet.json
- model_prompt_packet_path: .work/operator_handoffs/30b_substantive_handoff_v3_20260830/20260830T000001Z/model_prompt_packet.md

### Authority Notice
- This prompt authorizes only the stated downstream task.
- It does not grant repository modification, promotion, training, autonomous routing, or other held authority unless explicitly present in the source transaction.

### Review Boundary
- This artifact is a derived executable continuation view, not an authority source.
