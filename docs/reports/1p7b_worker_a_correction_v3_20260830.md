# 1p7b_worker_a_correction_v3_20260830 Adjudication

This report preserves the third bounded Worker-A correction experiment.

## Result summary

- Existing-patch retention: `PASS`
- `unique_json_keys_v1` uptake: `FAIL`
- Complete Worker-A contract: `FAIL`
- Worker B: `NOT REACHED`

## Frozen corrections

The experiment retained the two previously successful corrections unchanged and added one new correction:

- `allowed_held_mapping_v1`
- `required_fields_boolean_v1`
- `unique_json_keys_v1`

Frozen semantic instructions:

> Copy the supplied allowed_targets and held_targets into the output without swapping, promoting, demoting, inferring, or adding targets. The only allowed target is docs/reports/. The held targets production automation, automatic curriculum capture, automatic promotion, and implementation_packet must remain held and must not appear in allowed_targets.
>
> required_fields_present is a boolean status field. Emit exactly true when all required fields are present. Do not emit a list of field names in required_fields_present.
>
> Emit exactly one top-level JSON object. Emit every required top-level key exactly once. Do not repeat, redefine, append a second copy of, or emit multiple occurrences of any top-level key. Before finishing, ensure the object contains one and only one occurrence of each required key.

## Requalification

- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Endpoint: `http://192.168.1.16:8081/v1`
- Observed context: `32768`

## Acquisition integrity

- Corrected model-visible prompt SHA-256: `debd19ba1975df4c12dacc504972af7c0d223c6ddb8b7443b3c7f459f5db8a56`
- Corrected raw-response SHA-256: `6fb54324d68b8ce16b616570d469f49ad1b793131a6a7dec391cbb6dd34e31c8`
- Acquisition integrity: `PASS`

## Corrected behavior

The corrected Worker-A response retained the two previously fixed behaviors:

- `allowed_targets` was exactly `["docs/reports/"]`
- `held_targets` was exactly:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- `required_fields_present` was boolean `true`

## Remaining failure

The corrected response still failed the unchanged validator because the raw JSON contained a duplicate top-level key:

- `format` occurred twice

The validator reported:

- `duplicate_json_keys: failed`
- diagnostic: `Duplicate JSON key in raw model output: format`

No other duplicate top-level keys were present in this corrected response.

## Duplicate-key analysis

### Corrected raw response

Raw response SHA-256:

`6fb54324d68b8ce16b616570d469f49ad1b793131a6a7dec391cbb6dd34e31c8`

Top-level key occurrences in order:

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

Duplicate key:

- `format`
  - occurrence count: 2
  - first value: `"json"`
  - later value: `"json"`
  - values identical

### Original live failure

The preserved original live failure raw response had no duplicate keys.

Original raw response SHA-256:

`df7d0072ad1883ee9e7323a2edf37abc598654d326e81db9ea90a11dc5d6b302`

Top-level key occurrences in order:

1. `format`
2. `required_fields_present`
3. `allowed_targets`
4. `held_targets`
5. `scope_expansion_required`
6. `claims`
7. `evidence_basis`
8. `unverified_claims`
9. `reason`

Duplicate-key classification:

- `NEWLY_EXPOSED`

Evidence:

- original live failure: no duplicate top-level keys
- corrected V3 response: duplicate `format`

## Comparison

| Criterion | Original live result | Correction V2 | Correction V3 |
| --- | --- | --- | --- |
| allowed_targets | FAIL | PASS | PASS |
| held_targets | FAIL | PASS | PASS |
| required_fields_present | FAIL | PASS | PASS |
| required_field_types | FAIL | PASS | PASS |
| target_authority | FAIL | PASS | PASS |
| duplicate_json_keys | PASS / absent | FAIL | FAIL |
| overall validation | FAIL | FAIL | FAIL |

## Verdicts

- Existing-patch retention: `PASS`
- `unique_json_keys_v1` uptake: `FAIL`
- Complete Worker-A contract: `FAIL`
- Bounded correction trajectory: not claimed; the run preserved the corrected target/type behavior but did not satisfy the full contract

## Preservation

The experiment is durably archived under:

`docs/reports/evidence/1p7b_worker_a_correction_v3_20260830/`

Archive verification count:

- `15` entries

Archive verification result:

- `PASS`

## Proposed next step

If a future correction is attempted, it should preserve the three frozen patches unchanged and focus only on preventing the remaining duplicate-key emission. The next experiment ID can be:

`1p7b_worker_a_correction_v4_20260830`

No next experiment is executed in this task.
