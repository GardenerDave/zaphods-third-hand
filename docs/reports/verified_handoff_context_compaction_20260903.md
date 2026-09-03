# Verified Handoff Context Compaction

Experiment date: `2026-09-03`

## Scope

This slice adds a bounded verified-compaction path for transaction handoff context. The compact packet is derived from preserved authoritative evidence and is only accepted after deterministic verification against that evidence.

## Implementation Summary

The new compact handoff packet lives in `zth.verified_compact_handoff_context.v0.1` and is built from a source transaction run:

- source transaction and run identity;
- repository binding;
- protected task state;
- authoritative evidence references;
- deterministic claims derived only from the preserved evidence.

Verification is fail-closed and checks:

- source transaction/run identifiers survive;
- repository binding survives;
- output-validation evidence still resolves;
- expected validation status is recovered from the preserved artifact;
- unsupported claims are rejected;
- missing critical references are rejected;
- altered identities are rejected;
- valid-but-wrong evidence is rejected.

The compact packet is explicitly derived context, not an authority source.

## Dogfood Evidence

### 1.7B bounded worker task

- Endpoint: `http://192.168.1.16:8081/v1`
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Prompt tokens: 43
- Raw response: [`verified_handoff_context_compaction_20260903_1p7b_raw.json`](./verified_handoff_context_compaction_20260903_1p7b_raw.json)
- Result: failed as a bounded compaction advisor
- Failure classification: context-contract mismatch and domain drift
- Supervisor correction burden: high
- Final disposition: retained as capability evidence only

### Interpretation

The worker was asked for protected handoff fields and returned unrelated medical/insurance fields. That is a useful negative example of small-model contract drift under insufficiently shaped context.

## Validation

- Focused transaction handoff tests: passed
- Evidence typing tests: passed
- Historian/context/validation adjacency tests: passed
- `git diff --check`: passed

## Evidence

- Implementation commit: current working tree after `42ceeb85b3c4a70dc6f12c77c25d0ce5c8971443`
- Durable report: [`verified_handoff_context_compaction_20260903.json`](./verified_handoff_context_compaction_20260903.json)

