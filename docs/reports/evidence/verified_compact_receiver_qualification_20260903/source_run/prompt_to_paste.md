# ZTH Repository Observation Packet

## Role
You are a bounded model helper operating inside a supervised ZTH workflow.

## Task
Verified compaction fail-closed behavior observation

## Instructions
Identify exactly one fail-closed verification behavior enforced by the verified compact handoff context in the projected evidence file.

## Evidence Packet
```json
{
  "evidence_sources": [
    {
      "byte_length": 2257,
      "char_length": 2257,
      "excerpt": "# Verified Handoff Context Compaction\n\nExperiment date: `2026-09-03`\n\n## Scope\n\nThis slice adds a bounded verified-compaction path for transaction handoff context. The compact packet is derived from preserved authoritative evidence and is only accepted after deterministic verification against that evidence.\n\n## Implementation Summary\n\nThe new compact handoff packet lives in `zth.verified_compact_handoff_context.v0.1` and is built from a source transaction run:\n\n- source transaction and run identity;\n- repository binding;\n- protected task state;\n- authoritative evidence references;\n- deterministic claims derived only from the preserved evidence.\n\nVerification is fail-closed and checks:\n\n- source transaction/run identifiers survive;\n- repository binding survives;\n- output-validation evidence still resolves;\n- expected validation status is recovered from the preserved artifact;\n- unsupported claims are rejected;\n- missing critical references are rejected;\n- altered identities are rejected;\n- valid-but-wrong evidence is rejected.\n\nThe compact packet is explicitly derived context, not an authority source.\n\n## Dogfood Evidence\n\n### 1.7B bounded worker task\n\n- Endpoint: `http://192.168.1.16:8081/v1`\n- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`\n- Prompt tokens: 43\n- Raw response: [`verified_handoff_context_compaction_20260903_1p7b_raw.json`](./verified_handoff_context_compaction_20260903_1p7b_raw.json)\n- Result: failed as a bounded compaction advisor\n- Failure classification: context-contract mismatch and domain drift\n- Supervisor correction burden: high\n- Final disposition: retained as capability evidence only\n\n### Interpretation\n\nThe worker was asked for protected handoff fields and returned unrelated medical/insurance fields. That is a useful negative example of small-model contract drift under insufficiently shaped context.\n\n## Validation\n\n- Focused transaction handoff tests: passed\n- Evidence typing tests: passed\n- Historian/context/validation adjacency tests: passed\n- `git diff --check`: passed\n\n## Evidence\n\n- Implementation commit: current working tree after `42ceeb85b3c4a70dc6f12c77c25d0ce5c8971443`\n- Durable report: [`verified_handoff_context_compaction_20260903.json`](./verified_handoff_context_compaction_20260903.json)\n\n",
      "path": "docs/reports/verified_handoff_context_compaction_20260903.md",
      "sha256": "268175d5180a5af3cab64193fcd728314ff687c1dd82eaba46c7b85b8c640ad1",
      "truncated": false
    }
  ],
  "output_contract": {
    "format": "json",
    "required_fields": [
      "findings",
      "reason"
    ],
    "requires_reason": true
  },
  "selected_prompt_patches": [
    "scope_boundary_v1",
    "placeholder_leakage_v1",
    "output_contract_v1"
  ],
  "task_summary": "Identify exactly one fail-closed verification behavior enforced by the verified compact handoff context in the projected evidence file.",
  "task_title": "Verified compaction fail-closed behavior observation"
}
```

## Prompt Patch Instructions
[
  "scope_boundary_v1",
  "placeholder_leakage_v1",
  "output_contract_v1"
]

### Prompt Patch Provenance
The following rendered patch deltas describe how the packet was assembled.
They are provenance metadata, not citable evidence sources.
## Applied Prompt Patches

### Patch: scope_boundary_v1 (candidate)

Only include targets explicitly listed in allowed_targets. Related or plausible files must go in held_targets.

Required output fields: allowed_targets, held_targets, scope_expansion_required, reason

### Patch: placeholder_leakage_v1 (candidate)

Replace every template placeholder with real content before finishing. If a value is unknown, write 'unknown' plus the reason it is unknown. Do not emit angle-bracket placeholders, TODO stubs, or lorem-ipsum text in the final output.

Required output fields: final_content, unresolved_items, reason

### Patch: output_contract_v1 (candidate)

Return exactly one output in the declared contract format. Include every required field, even when its value is empty or unknown. Do not add fields that grant authority. Do not wrap the structured output in commentary.

Required output fields: format, required_fields_present, reason

These patches constrain output shape only. They grant no execution,
promotion, training, or curriculum-capture authority.


## Required Output Contract
```json
{
  "format": "json",
  "required_fields": [
    "findings",
    "reason"
  ],
  "requires_reason": true
}
```

## Required Response Shape
- Return only JSON matching the output contract.
- Each finding must include a claim and supporting evidence objects with path and detail fields.
- Cite only paths from the Evidence Packet; do not cite prompt patch provenance as evidence.
- Distinguish supplied evidence from model-generated claims.
- Do not claim filesystem authority or additional repository access.
- Do not include prose outside the JSON object.

## Authority Boundaries
- no filesystem authority
- no command execution authority
- no file modification authority
- no automatic patch promotion
- no automatic training
- no default failure-to-curriculum capture
