# 1p7b_to_30b_structured_continuous_v1_20260830

Date: 2026-08-30

## Outcome

This fresh structured continuous-lineage experiment successfully completed Worker-A acquisition, captured-model ingest, validation, explicit review, gate, and handoff generation.

Worker-B was not reached in the fresh run. No `worker_b_local_model_call.json` or equivalent 30B acquisition artifact was produced, and no 30B raw response exists for this experiment.

Final classification:

- Worker-A structured acquisition integrity: PASS
- Worker-A captured-model provenance: PASS
- Worker-A complete contract: PASS
- Explicit post-validation review: PASS
- Gate: PASS
- Automatic handoff/context/continuation generation: PASS
- Worker-B acquisition integrity: NOT REACHED
- Worker-B downstream production: NOT REACHED
- Authority preservation across handoff: PASS
- Continuous lineage: NOT ACHIEVED END-TO-END
- Complete experiment: INCOMPLETE / FAIL FOR FULL HANDOFF

## Frozen Worker-A configuration

- Base task: `The LoRA and prompt injection work got messy. Build a bounded design packet.`
- Canonical baseline patches:
  - `scope_boundary_v1`
  - `unsupported_certainty_v1`
  - `output_contract_v1`
- Explicit semantic patches:
  - `allowed_held_mapping_v1`
  - `required_fields_boolean_v1`
- Syntax-only patches superseded by deterministic structured decoding:
  - `unique_json_keys_v1`
  - `single_pass_json_object_v1`
- Structured-output schema SHA-256: `8a0eefccc8738cb56dbd83b9a908ed459f865149cd6482c5db767e81c3e65b59`

## Worker-A runtime qualification

- Endpoint: `http://192.168.1.16:8081/v1`
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Observed context: `32768`

## Worker-A acquisition integrity

- Model-visible prompt SHA-256: `3e2576c2fb201c1a7e29fc9473c74c2d226a29f42597faa4daa089c6a9455d55`
- Request-body SHA-256: `beb200d919b8a1aaf85379709523a64aa108225df4d59e195ca5be77510d8e0c`
- Raw response SHA-256: `c8ea66f83e9376053a68b6f8833809c08208121c55971ef017cf5f4e2e9fb43c`
- Call status: `completed`

## Worker-A semantic result

The raw response satisfied the unchanged validator and preserved the frozen authority split:

- `allowed_targets`: `["docs/reports/"]`
- `held_targets`:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- `scope_expansion_required`: `false`
- `required_fields_present`: `true`
- `format`: `json`

Validator checks passed:

- `parse_json`
- `required_fields`
- `required_field_types`
- `allowed_held_target_separation`
- `held_target_preservation`
- `target_authority`
- `requires_reason`

## Captured-model provenance

The supervised attempt was recorded as a captured local model result, not manual operator output.

- Model ID: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Provider: `local_model_call`
- Provenance source: captured model output
- Acquisition request provenance: present
- Structured-output provenance: present
- Model-call metadata SHA/path: present

## Review / gate / handoff

The fresh run produced:

- `review_decision.json`
- `downstream_use_gate.json`
- `handoff_packet.json`
- `transaction_manifest.json`
- `next_worker_context.json`
- `next_worker_context.md`
- `next_worker_continuation.md`

These artifacts resolve to the same fresh Worker-A result and preserve the authoritative allowed/held targets and bounded downstream objective.

## Worker-B status

Worker-B acquisition did not complete in this run.

No 30B raw response, request metadata, or downstream artifact exists for this experiment.

## Interpretation

This run is a successful fresh structured Worker-A handoff preparation with validated review/gate/handoff generation, but it is not a completed continuous 1.7B -> ZTH -> 30B production handoff because the 30B acquisition was not reached.

