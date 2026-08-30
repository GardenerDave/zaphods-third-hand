# 1p7b_worker_a_correction_v4_20260830 Adjudication

This report preserves the fourth bounded Worker-A correction experiment.

## Requalification

- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Endpoint: `http://192.168.1.16:8081/v1`
- Observed context: `32768`

## Frozen patch set

The experiment retained the three previously frozen corrections and added one new correction:

- `allowed_held_mapping_v1`
- `required_fields_boolean_v1`
- `unique_json_keys_v1`
- `single_pass_json_object_v1`

Frozen semantic instructions:

> Copy the supplied allowed_targets and held_targets into the output without swapping, promoting, demoting, inferring, or adding targets. The only allowed target is docs/reports/. The held targets production automation, automatic curriculum capture, automatic promotion, and implementation_packet must remain held and must not appear in allowed_targets.
>
> required_fields_present is a boolean status field. Emit exactly true when all required fields are present. Do not emit a list of field names in required_fields_present.
>
> Emit exactly one top-level JSON object. Emit every required top-level key exactly once. Do not repeat, redefine, append a second copy of, or emit multiple occurrences of any top-level key. Before finishing, ensure the object contains one and only one occurrence of each required key.
>
> Construct the response as one JSON object in one pass. Start with {, emit each required top-level key exactly once in the exact order specified below, then close the object with }. Do not emit format, required_fields_present, reason, or any other field as a preamble before this sequence. Do not restart the object, repeat a field, or append a second copy of any field after it has already been emitted.
>
> After reason, close the JSON object immediately. Emit no additional top-level key.

## Acquisition integrity

- Corrected model-visible prompt SHA-256: `9aa0978a8b04384045778621e41af1d460f1d93c4a0f1d0ca0cc8a57fb58806d`
- Corrected raw-response SHA-256: `4eec07aec1b0fd5a29dad568d753539309b43cef0aa8223ed5d8e684348df807`
- Acquisition integrity: `PASS`

## Corrected behavior

The corrected Worker-A response preserved the earlier successful behaviors:

- `allowed_targets` was exactly `["docs/reports/"]`
- `held_targets` was exactly:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- `required_fields_present` was boolean `true`

## Remaining failure

The unchanged validator still failed. In this run, the failure shifted from duplicate-key serialization to required-field type mismatch:

- `required_field_types: failed`
- diagnostic:
  - `claims must be a list`
  - `evidence_basis must be a list`
  - `unverified_claims must be a list`

The raw response shows that the model emitted `claims`, `evidence_basis`, and `unverified_claims` as objects / string values rather than lists, while also placing the three patch IDs into the nested `claims` object.

## Raw response structure

Exact top-level key order in the raw response:

1. `allowed_targets`
2. `held_targets`
3. `scope_expansion_required`
4. `claims`
5. `evidence_basis`
6. `unverified_claims`
7. `format`
8. `required_fields_present`
9. `reason`

Top-level key occurrence counts:

- `allowed_targets`: 1
- `held_targets`: 1
- `scope_expansion_required`: 1
- `claims`: 1
- `evidence_basis`: 1
- `unverified_claims`: 1
- `format`: 1
- `required_fields_present`: 1
- `reason`: 1

The raw response contains no duplicate top-level keys.

There are repeated strings inside nested values:

- `scope_boundary_v1`: 2
- `unsupported_certainty_v1`: 2
- `output_contract_v1`: 2

Those repeats occur inside the nested `claims` / `unverified_claims` content and are not duplicate top-level JSON keys.

## Original vs corrected

Original live failure raw SHA-256:

`df7d0072ad1883ee9e7323a2edf37abc598654d326e81db9ea90a11dc5d6b302`

V2 corrected raw SHA-256:

`4e9ef87456dba6b76b9301d524bfa0b04f18ec98370187c01e2bc70a46942a1a`

V3 corrected raw SHA-256:

`6fb54324d68b8ce16b616570d469f49ad1b793131a6a7dec391cbb6dd34e31c8`

V4 corrected raw SHA-256:

`4eec07aec1b0fd5a29dad568d753539309b43cef0aa8223ed5d8e684348df807`

### Comparison table

| Criterion | Original | V2 | V3 | V4 |
| --- | --- | --- | --- | --- |
| allowed_targets | FAIL | PASS | PASS | PASS |
| held_targets | FAIL | PASS | PASS | PASS |
| required_fields_present | FAIL | PASS | PASS | PASS |
| required_field_types | FAIL | PASS | PASS | FAIL |
| target_authority | FAIL | PASS | PASS | PASS |
| duplicate_json_keys | absent | 3 duplicated keys | 1 duplicated key | absent as top-level duplicate keys |
| overall validation | FAIL | FAIL | FAIL | FAIL |

## Verdicts

- Existing correction retention: `PASS`
- `single_pass_json_object_v1` uptake: `FAIL`
- Complete Worker-A contract: `FAIL`
- Worker B: `NOT REACHED`
- Bounded correction trajectory: not claimed

## Interpretation

This run shows that the prompt stack preserved the earlier target-mapping corrections, but the model reinterpreted the structured patch sections into nested object content and failed the type requirements for `claims`, `evidence_basis`, and `unverified_claims`.

## Preservation

The experiment is durably archived under:

`docs/reports/evidence/1p7b_worker_a_correction_v4_20260830/`

Archive verification count:

- `15` entries

Archive verification result:

- `PASS`

## Proposed next step

The next question is whether syntax/shape should be handled by a constrained decoding or grammar mechanism rather than by more prompt text. That question is not answered here and no such mechanism is introduced in this experiment.

Do not run another correction automatically.
