# Executable Handoff Integrity Replay

Experiment date: `2026-09-03`

## Scope

This report records the evidence-driven replay and the next executable-handoff slice that qualifies evidence/test artifacts for downstream reachability and claim recovery.

## Implementation Summary

The implementation adds a conservative evidence-artifact qualification path for `output_validation.json`:

- `OutputValidationRef`
- `OutputValidationVerification`
- `resolve_output_validation_reference(...)`

This extends qualification beyond file existence and hash identity so that a receiver must also recover the expected validation claim/status from the artifact.

## Dogfood Evidence

### Initial 1.7B attempt

- Endpoint: `http://192.168.1.16:8081/v1`
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Approximate prompt size: 149 prompt tokens
- Raw response: [`executable_handoff_integrity_replay_20260903_1p7b_raw.json`](./executable_handoff_integrity_replay_20260903_1p7b_raw.json)
- Result: failed qualification
- Interpretation: partially correct semantic judgment, but the proposed negative control was not valid or constructible

### 30B escalation

- Endpoint: `http://192.168.1.16:8080/v1`
- Model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- Raw response: [`executable_handoff_integrity_replay_20260903_30b_raw.json`](./executable_handoff_integrity_replay_20260903_30b_raw.json)
- Result: passed qualification
- Interpretation: positive precedent for the bounded repository-binding audit task under its supplied context

### Controlled 1.7B replay

- Endpoint: `http://192.168.1.16:8081/v1`
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Approximate prompt size: 550 prompt tokens
- Prompt intent: [`executable_handoff_integrity_replay_20260903_1p7b_request_intent.json`](./executable_handoff_integrity_replay_20260903_1p7b_request_intent.json)
- Request metadata: [`executable_handoff_integrity_replay_20260903_1p7b_metadata.json`](./executable_handoff_integrity_replay_20260903_1p7b_metadata.json)
- Raw response: [`executable_handoff_integrity_replay_20260903_1p7b_response.json`](./executable_handoff_integrity_replay_20260903_1p7b_response.json)
- Result: passed qualification
- Interpretation: the earlier 1.7B miss is better explained by context insufficiency / context-contract mismatch than by a demonstrated hard capability boundary

## Evidence Interpretation

The replay supports a more precise precedent shape:

`worker + capability + context contract + qualification`

This is evidence for future routing and qualification work, not a generalized capability registry.

## Validation

- Focused tests: 61 passed
- Repo health: 525 passed
- Diff check: passed

## Evidence Provenance

- Current implementation commit: `e2b3b04ab2820f433604f4308e274a133143d12a`
- Durable JSON summary: [`executable_handoff_integrity_replay_20260903.json`](./executable_handoff_integrity_replay_20260903.json)
- Preserved `.work/` originals remain available for local recovery, but the repository-tracked copies above are the durable record.
