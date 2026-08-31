# Structured Worker-A Semantic Experiment

## Verdict

- Structured-output request integrity: PASS
- Schema conformance: PASS
- Supervised-ingest provenance: INVALID for captured-model evidence; the archived supervised attempt was recorded as manual/operator-pasted output, not captured-model output.
- Semantic correction retention: FAIL
- Complete Worker-A frozen contract: FAIL

## Summary

The qualified JSON-schema transport worked, but the archived supervised attempt was not recorded as truthful captured-model ingest. The preserved live acquisition evidence is still valid, but the committed supervised-attempt record uses manual/operator provenance.

The 1.7B response itself did not satisfy the frozen semantic contract. It preserved the allowed target `docs/reports/` and the boolean `required_fields_present`, but it misclassified the held targets and reused those held-target strings in `claims`, `evidence_basis`, and `unverified_claims`.

## Experiment Identity

- Experiment ID: `1p7b_worker_a_structured_v1_20260830`
- Implementation HEAD: `53a74fcf9ebcd7be8d9445d713445414076ea05d`
- Worker: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Endpoint: `http://192.168.1.16:8081/v1`
- Observed context: `32768`

## Frozen Semantic Corrections

- `allowed_held_mapping_v1`
- `required_fields_boolean_v1`

Syntax-only correction instructions were not applied in the archived prompt projection; their IDs were only mentioned in an exclusion instruction. The archived `prompt_to_paste.md` was hand-authored rather than projected from the canonical packet.

## Schema

- Schema SHA-256: `d8d12808b6e22935dffc678b0b78d9bf1f14950cbefdbd63fa1f13d75382ba7f`
- Schema byte length: `1028`

## Prompt / Request / Response

- Prompt SHA-256: `689d1c2d2b8517e2bfd3c71bae3e4432e12a0ddf6e2f305a86517cfe9b9266b0`
- Prompt length: `898`
- Request-body SHA-256: `97844974b83a1b5759170b52b5eccbd153de1119276113503ca78544c47aab05`
- Request-body length: `1882`
- Raw-response SHA-256: `6680bcbea410993104bea8a810e9abab954ca8bf1faca3124e89b3f5b7cc379b`
- Raw-response length: `1057`

## Actual Output

- `allowed_targets`: `['docs/reports/']`
- `held_targets`: `['docs/reports/production automation', 'docs/reports/automatic curriculum capture', 'docs/reports/automatic promotion', 'docs/reports/implementation_packet']`
- `required_fields_present`: `True` (`bool`)
- `scope_expansion_required`: `False` (`bool`)
- `format`: `json`

## Validator Result

The unchanged validator passed on structural checks and accepted the structured JSON output as valid, but that did not establish semantic correctness.

## Semantic Assessment

- allowed/held mapping: FAIL
- required_fields_present boolean: PASS
- claims/evidence_basis/unverified_claims: FAIL
- overall semantic contract: FAIL

## Forensic Adjudication

- Live structured acquisition: VALID
- Supervised ingest provenance: INVALID
- Prompt-projection design deviation: the archived prompt_to_paste.md did not preserve the canonical prompt packet as a machine-projected view; it was hand-authored and omitted baseline material that was present in model_prompt_packet.md.
- Intended structured Worker-A semantic hypothesis: INCONCLUSIVE because the prompt projection was not cleanly generated from the canonical prepared packet.

The observed raw-model behavior remains real: the held-target reproduction failed.

## Comparison

| Criterion | Structured V1 |
| --- | --- |
| allowed_targets | PASS |
| held_targets | FAIL |
| required_fields_present | PASS |
| required_field_types | PASS |
| target_authority | FAIL |
| schema conformance | PASS |
| overall validation | FAIL |

## Archive Manifest

- Entry count: `14`
- Manifest: `docs/reports/evidence/1p7b_worker_a_structured_v1_20260830/archive_manifest.json`

## Closeout

The structured-output transport boundary is reproducibly intact. The archived supervised-attempt provenance is manual/operator-pasted rather than captured-model ingest, the prompt projection deviated from the canonical packet, and the observed raw model output still failed the frozen semantic contract.
