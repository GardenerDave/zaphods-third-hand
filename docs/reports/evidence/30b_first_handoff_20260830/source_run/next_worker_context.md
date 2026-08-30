# ZTH Next Worker Context

- transaction_id: orch_manual_20260707t112634z
- lifecycle_state: HANDOFF
- run_id: manual_supervised_attempt_20260707t112634z
- selected_next_worker_identity: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf

## Task State
```json
{
  "allowed_targets": [
    "docs/reports/"
  ],
  "bounded_task_request": "The LoRA and prompt injection work got messy. Build a bounded design packet.\n",
  "held_targets": [
    "production automation",
    "automatic curriculum capture",
    "automatic promotion",
    "implementation_packet"
  ],
  "orchestration_id": "orch_manual_20260707t112634z",
  "prompt_packet_id": "prompt_packet_manual_20260707t112634z",
  "run_manifest_path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/run_manifest.json",
  "source_prompt_packet_path": ".work/manual_supervised_attempts/20260707T112634Z/model_prompt_packet.md",
  "task_request": "# ZTH Model Prompt Packet\n\n## Role\nYou are a bounded model helper operating inside a supervised ZTH workflow.\n\n## Packet IDs\n- orchestration_id: orch_manual_20260707t112634z\n- triage_id: triage_manual_20260707t112634z\n\n## Task Summary\nDeterministic routing of messy input to design_packet (matched keywords: lora, prompt injection).\n\n## Workflow\n- recommended_workflow: design_packet\n- task_type: design_planning\n\n## Allowed Targets\n- docs/reports/\n\n## Held Targets\n- production automation\n- automatic curriculum capture\n- automatic promotion\n- implementation_packet\n\n## Risk Flags\n- prompt_injection_surface\n- scope_creep\n- training_pipeline_ambiguity\n\n## Prompt Patch Instructions\n- scope_boundary_v1\n- unsupported_certainty_v1\n- output_contract_v1\n\n### Rendered Patch Deltas\n## Applied Prompt Patches\n\n### Patch: scope_boundary_v1 (candidate)\n\nOnly include targets explicitly listed in allowed_targets. Related or plausible files must go in held_targets.\n\nRequired output fields: allowed_targets, held_targets, scope_expansion_required, reason\n\n### Patch: unsupported_certainty_v1 (candidate)\n\nOnly state claims supported by the evidence you were given. Mark any scope-level or repo-wide statement as unverified unless the packet includes evidence covering that scope. Prefer 'not verified in this packet' over confident generalization.\n\nRequired output fields: claims, evidence_basis, unverified_claims, reason\n\n### Patch: output_contract_v1 (candidate)\n\nReturn exactly one output in the declared contract format. Include every required field, even when its value is empty or unknown. Do not add fields that grant authority. Do not wrap the structured output in commentary.\n\nRequired output fields: format, required_fields_present, reason\n\nThese patches constrain output shape only. They grant no execution,\npromotion, training, or curriculum-capture authority.\n\n## Output Contract\n```json\n{\n  \"format\": \"json\",\n  \"required_fields\": [\n    \"allowed_targets\",\n    \"held_targets\",\n    \"scope_expansion_required\",\n    \"claims\",\n    \"evidence_basis\",\n    \"unverified_claims\",\n    \"format\",\n    \"required_fields_present\",\n    \"reason\"\n  ],\n  \"requires_reason\": true\n}\n```\n\n## Validation Hooks\n- allowed_held_target_separation\n- required_reason\n- no_execution_authority\n\n## Authority Boundaries\n- no_automatic_patch_promotion\n- no_automatic_training\n- no_default_failure_to_curriculum_capture\n- no_direct_file_modification_authority\n- no_execution_authority\n\n## Required Response Shape\n- Return only JSON matching the output contract.\n- Include a reason field when required.\n- Do not include prose outside the JSON object.\n\n## Review Requirement\n- Human review is required before any downstream model-facing action.\n",
  "triage_id": "triage_manual_20260707t112634z"
}
```

## Evidence References
```json
[
  {
    "artifact": "run_manifest",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/run_manifest.json",
    "sha256": "d4f321c905a43a746d6da918740d5785f8fa99d5c5e42bb3037cdd0c8d3b1c44"
  },
  {
    "artifact": "model_prompt_packet",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/model_prompt_packet.md",
    "sha256": "3e4c6d2cb9ab3393502769d3aaa8ce027bd8334ad6b54974c65bd21deae7d007"
  },
  {
    "artifact": "raw_model_output",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/raw_model_output.txt",
    "sha256": "adbbf7c43a9436426596e2ebd8911c4ed41d4bf7958c164f4f21469192c7f064"
  },
  {
    "artifact": "supervised_model_attempt",
    "attempt_id": "manual_attempt_20260830t201819z",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/supervised_model_attempt.json",
    "sha256": "c57c654b6139adf9204dc2ebd89ff29030869e22d52717b2a1facac6d6fdcccc"
  },
  {
    "artifact": "output_validation",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/output_validation.json",
    "sha256": "653217f87f2e3f9583b1c6950b7d7faec5d69047ed312fc8cf8eedabc4312bc4",
    "validation_id": "manual_validation_20260830t201819z"
  },
  {
    "artifact": "review_decision",
    "decision_id": "manual_decision_20260830t201819z",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/review_decision.json",
    "sha256": "aab640710bf974ccb5cf533ff53244c447f54571800b75ed84a4091061cc966d"
  },
  {
    "artifact": "downstream_use_gate",
    "gate_id": "manual_gate_20260830t201819z",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/downstream_use_gate.json",
    "sha256": "ff85584b88d981c07159cc9881bfb060ac8fce13a3cbdcce5384e0867b76c6c5"
  },
  {
    "artifact": "handoff_packet",
    "handoff_id": "manual_handoff_20260830t201819z",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/handoff_packet.json",
    "sha256": "c5cffeb8efbbba96ac9530cf3cac7940021ee60b56ac0187909767c6d3fcc25b"
  }
]
```

## Authority Boundaries
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

## Previous Attempt
```json
{
  "attempt_id": "manual_attempt_20260830t201819z",
  "result_reference": {
    "raw_output_artifact": {
      "artifact": "raw_model_output",
      "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/raw_model_output.txt",
      "sha256": "adbbf7c43a9436426596e2ebd8911c4ed41d4bf7958c164f4f21469192c7f064"
    },
    "raw_output_reference": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/raw_model_output.txt"
  }
}
```

## Validation
```json
{
  "validation_id": "manual_validation_20260830t201819z",
  "validation_report_reference": "supervised_attempt_output_validation",
  "validation_status": "passed"
}
```

## Review
```json
{
  "decision": "accepted",
  "decision_id": "manual_decision_20260830t201819z",
  "decision_reason": "Output satisfies the contract and remains within scope."
}
```

## Downstream-Use Gate
```json
{
  "gate_id": "manual_gate_20260830t201819z",
  "gate_reason": "Downstream use remains bounded to supervised next-step input handling.",
  "gate_status": "allowed"
}
```

## Handoff
```json
{
  "handoff_id": "manual_handoff_20260830t201819z",
  "handoff_packet_reference": {
    "artifact": "handoff_packet",
    "handoff_id": "manual_handoff_20260830t201819z",
    "path": ".work/operator_handoffs/30b_first_handoff_20260830/source_run/handoff_packet.json",
    "sha256": "c5cffeb8efbbba96ac9530cf3cac7940021ee60b56ac0187909767c6d3fcc25b"
  },
  "handoff_reason": "Handoff remains supervised and bounded by downstream-use gate status.",
  "handoff_status": "prepared"
}
```

## Constraints
```json
{
  "allowed_targets": [
    "docs/reports/"
  ],
  "authority_boundaries": [
    "Handoff packet is not command execution authority.",
    "Handoff packet is not file modification authority.",
    "Handoff packet is not patch application authority.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Next step must remain supervised."
  ],
  "handoff_reason": "Handoff remains supervised and bounded by downstream-use gate status.",
  "held_targets": [
    "production automation",
    "automatic curriculum capture",
    "automatic promotion",
    "implementation_packet"
  ],
  "next_step_scope": "bounded_supervised_input_only"
}
```

## Review Boundary
- This bundle is a next-worker input only.
- It does not grant execution, file modification, promotion, or training authority.
- It does not select a worker semantically.
