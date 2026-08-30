# 1p7b_worker_a_correction_v2_20260830 Adjudication

This report preserves and adjudicates the Worker-A correction experiment for the preserved live 1.7B validation failure.

## Original failure

The preserved live failure showed two independent defects:

- `allowed_targets` contained held targets:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- `held_targets` incorrectly contained the allowed target `docs/reports/`
- `required_fields_present` was emitted as a list of field names instead of boolean `true`
- overall Worker-A validation failed

## Frozen correction

The experiment applied only the following frozen corrections:

- `allowed_held_mapping_v1`
- `required_fields_boolean_v1`

Frozen correction text:

> Copy the supplied allowed_targets and held_targets into the output without swapping, promoting, demoting, inferring, or adding targets. The only allowed target is docs/reports/. The held targets production automation, automatic curriculum capture, automatic promotion, and implementation_packet must remain held and must not appear in allowed_targets.
>
> required_fields_present is a boolean status field. Emit exactly true when all required fields are present. Do not emit a list of field names in required_fields_present.

## Corrected behavior

The corrected Worker-A response followed both targeted corrections:

- `allowed_targets` was exactly `["docs/reports/"]`
- `held_targets` was exactly:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- `required_fields_present` was boolean `true`

That is a bounded correction success on the preserved Worker-A failure class for the two demonstrated defects.

## Remaining failure

The corrected response still failed validation because it emitted duplicate top-level JSON keys:

- `format` appeared twice
- `required_fields_present` appeared twice
- `reason` appeared twice

The unchanged validator reported:

- `duplicate_json_keys: failed`
- diagnostic: `Duplicate JSON key in raw model output: format`
- diagnostic: `Duplicate JSON key in raw model output: reason`
- diagnostic: `Duplicate JSON key in raw model output: required_fields_present`

The corrected run therefore still fails the full Worker-A contract.

## Duplicate-key analysis

### Corrected raw response

Raw response SHA-256:

`4e9ef87456dba6b76b9301d524bfa0b04f18ec98370187c01e2bc70a46942a1a`

Exact top-level keys in order:

1. `format`
2. `required_fields_present`
3. `reason`
4. `allowed_targets`
5. `held_targets`
6. `scope_expansion_required`
7. `claims`
8. `evidence_basis`
9. `unverified_claims`
10. `format`
11. `required_fields_present`
12. `reason`

Duplicated keys and values:

- `format`
  - occurrence count: 2
  - first value: `"json"`
  - later value: `"json"`
  - values identical
- `required_fields_present`
  - occurrence count: 2
  - first value: `true`
  - later value: `true`
  - values identical
- `reason`
  - occurrence count: 2
  - first value: `"All required fields are present and meet the constraints of the ZTH model prompt packet."`
  - later value: `"All required fields are present and meet the constraints of the ZTH model prompt packet."`
  - values identical

JSON parsing retained only the final occurrence of each duplicate key, but the validator correctly rejected the raw text because the duplicate keys exist in the preserved bytes.

### Original live failure

The preserved original live failure did not contain duplicate top-level keys.

Original raw response SHA-256:

`df7d0072ad1883ee9e7323a2edf37abc598654d326e81db9ea90a11dc5d6b302`

The original raw response had exactly one occurrence of each top-level key, and the failure was purely the allowed/held inversion plus `required_fields_present` being a list.

### Duplicate-key classification

The duplicate-key behavior in the corrected response is:

`NEWLY_EXPOSED`

evidence:

- present in corrected raw response
- absent from the preserved original live failure raw response

## Contract verdicts

- Targeted correction uptake: `PASS`
- Preserved original failure class: `CORRECTED FOR THIS CASE`
- Full Worker-A contract: `FAIL`
- Worker B: `NOT REACHED`
- Model-to-model handoff: `NOT REACHED`

## Comparison

| Criterion | Original live result | Corrected result |
| --- | --- | --- |
| allowed_targets | FAIL: held targets promoted | PASS |
| held_targets | FAIL: docs/reports/ held | PASS |
| required_fields_present | FAIL: list | PASS: boolean true |
| required_field_types | FAIL | PASS |
| target_authority | FAIL | PASS |
| duplicate_json_keys | not present in raw evidence | FAIL |
| overall Worker-A validation | FAIL | FAIL |

## Verification summary

- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Endpoint: `http://192.168.1.16:8081/v1`
- Observed context: `32768`
- Corrected prompt SHA-256: `34220099c71033e1f488ab855d5ad147e5fc8292161ff278cc19cbc209d5017c`
- Corrected raw-response SHA-256: `4e9ef87456dba6b76b9301d524bfa0b04f18ec98370187c01e2bc70a46942a1a`
- Archive verification: passed for all 15 entries

## Preservation status

The corrected experiment is durably preserved under:

`docs/reports/evidence/1p7b_worker_a_correction_v2_20260830/`

## Proposed next correction, not run

The next correction should keep both successful patches unchanged and add exactly one new correction for duplicate keys:

- proposed patch ID: `unique_json_keys_v1`
- proposed semantic instruction:
  - `Emit exactly one top-level JSON object. Emit every required key exactly once. Do not repeat, redefine, append a second copy of, or emit multiple occurrences of any top-level key. Before finishing, ensure the object contains one and only one occurrence of each required key.`

Suggested next experiment ID:

`1p7b_worker_a_correction_v3_20260830`

This proposal is not executed in this task.
