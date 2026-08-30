# Live 1.7B Handoff Validation Failure

Date: 2026-08-30

This report preserves the first live 1.7B continuous-lineage negative experiment for the V2 supervised production handoff path.

## Verdict

- Worker-A acquisition: PASS
- Worker-A contract validation: FAIL
- Worker-B: NOT REACHED
- True supervised model-to-model production handoff: NOT ACHIEVED
- Continuous lineage: NOT REACHED END-TO-END

The transaction lineage itself did not fail. The run remained continuous from live acquisition through captured-model ingest and validation, and downstream review/gate/handoff were correctly not entered because Worker A failed validation.

## Experiment Scope

- Experiment ID: `1p7b_to_30b_production_handoff_v2_20260830`
- Run: `.work/operator_handoffs/1p7b_to_30b_production_handoff_v2_20260830/20260830T000001Z`
- Worker A: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Worker A endpoint: `http://192.168.1.16:8081/v1`
- Observed Worker A context: `32768`
- Worker B: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- Worker B endpoint: `http://192.168.1.16:8080/v1`
- Observed Worker B context: `8192`

## Acquisition Integrity

- Model prompt SHA-256: `63b0ecd15b1aba9ed7900fc2b49968bed09fd2a1ea046362158bd77139643dc4`
- Prompt-to-paste SHA-256: `63b0ecd15b1aba9ed7900fc2b49968bed09fd2a1ea046362158bd77139643dc4`
- Metadata SHA-256: `89882c9793f04b519a3d19115f75741feaf79d2bafda1655bc54dc602300caa0`
- Raw Worker-A SHA-256: `df7d0072ad1883ee9e7323a2edf37abc598654d326e81db9ea90a11dc5d6b302`

The acquisition metadata matched the run prompt and raw response exactly.

## Worker-A Prompt Evidence

The model-visible prompt contained:

- the exact allowed target set: `docs/reports/`
- the exact held target set:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- prompt patch instructions:
  - `scope_boundary_v1`
  - `unsupported_certainty_v1`
  - `output_contract_v1`
- output contract requirements:
  - `allowed_targets`
  - `held_targets`
  - `scope_expansion_required`
  - `claims`
  - `evidence_basis`
  - `unverified_claims`
  - `format`
  - `required_fields_present`
  - `reason`
- explicit structural guidance that those patches constrain output shape only and grant no execution, promotion, training, or curriculum-capture authority

The prompt therefore exposed the correct allowed/held distinction and the required output keys/types.

## Worker-A Raw Response

The raw response preserved in `.work` and the archive is a JSON object whose critical fields were:

- `required_fields_present`: an array, not boolean `true`
- `allowed_targets`:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- `held_targets`:
  - `docs/reports/`
- `scope_expansion_required`: `false`
- `claims`: generic statements about the packet and matched keywords
- `evidence_basis`: generic statements repeating the prompt summary
- `unverified_claims`: repeated claims
- `reason`: present and non-empty

## Validator Failure Analysis

### Required Output Contract

| Required field | Worker A emitted | Expected constraint | PASS / FAIL | Validator reason |
| --- | --- | --- | --- | --- |
| `allowed_targets` | list of strings | present, list | PASS | required field present |
| `held_targets` | list of strings | present, list | PASS | required field present |
| `scope_expansion_required` | `false` | present, boolean | PASS | required field present |
| `claims` | list of strings | present, list | PASS | required field present |
| `evidence_basis` | list of strings | present, list | PASS | required field present |
| `unverified_claims` | list of strings | present, list | PASS | required field present |
| `format` | `"json"` | present, string | PASS | required field present |
| `required_fields_present` | list of field names | boolean `true` | FAIL | `required_fields_present must be boolean true` |
| `reason` | non-empty string | present, non-empty | PASS | Non-empty reason field is present |

### Allowed Targets

- Authorized allowed-target set: `docs/reports/`
- Worker A emitted allowed-target set:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- Unauthorized extra targets:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- Missing authorized targets:
  - `docs/reports/`

### Held Targets

- Expected held-target set:
  - `production automation`
  - `automatic curriculum capture`
  - `automatic promotion`
  - `implementation_packet`
- Worker A treatment:
  - moved the held set into `allowed_targets`
  - moved `docs/reports/` into `held_targets`
- This is a scope-classification failure, not a pure type failure.

### All Failing Checks

- `required_field_types`: `required_fields_present must be boolean true`
- `target_authority`: `Unauthorized allowed target in raw model output: automatic curriculum capture, automatic promotion, implementation_packet, production automation`

## Failure Classification

Worker A failure class: `MIXED_FAILURE`

Why:

- `OUTPUT_SHAPE_FAILURE`: `required_fields_present` had the wrong type
- `SCOPE_CLASSIFICATION_FAILURE`: the model promoted held targets into `allowed_targets` and moved the allowed target into `held_targets`
- `TASK_UNDERSTANDING_FAILURE`: not required as a separate class; the response still demonstrated the task domain, but it violated the frozen contract in two independent ways

## Prompt Safeguards Visible to Worker A

The prompt clearly exposed:

- the exact allowed targets
- the exact held targets
- the instruction that scope patch instructions constrain output shape only and grant no authority
- required output keys
- required types via the contract and validation hooks

The prompt did not hide the allowed/held distinction. The failure therefore appears to be a model contract-compliance failure, not an absence-of-information problem.

## Lineage / Provenance

This experiment preserved the same transaction identity from live acquisition through validation:

- `run_id`: `manual_supervised_attempt_20260830t000001z`
- `orchestration_id`: `orch_manual_20260830t000001z`
- `triage_id`: `triage_manual_20260830t000001z`
- `prompt_packet_id`: `prompt_packet_manual_20260830t000001z`
- `attempt_id`: `model_attempt_20260830t230134z`
- `validation_id`: `manual_validation_20260830t230134z`

The raw result SHA remained the exact captured Worker-A SHA through supervised attempt ingest and validation:

- `df7d0072ad1883ee9e7323a2edf37abc598654d326e81db9ea90a11dc5d6b302`

## What Succeeded

- live 1.7B runtime acquisition
- same-run acquisition
- truthful captured-model ingest
- actual worker identity preservation
- acquisition/raw-result provenance checks
- continuous transaction identity through validation
- fail-closed validator behavior

## What Failed

- Worker A did not satisfy the frozen output contract.

## What Was Not Reached

- review acceptance
- downstream gate
- handoff packet
- Worker-B generated continuation
- 30B acquisition
- A → B semantic dependence
- complete model-to-model handoff

## Archive Preservation

Durable archive:

- `docs/reports/evidence/1p7b_to_30b_production_handoff_v2_20260830/`

Archive manifest:

- `docs/reports/evidence/1p7b_to_30b_production_handoff_v2_20260830/archive_manifest.json`

This archive is a byte-for-byte preservation of the preserved run artifacts plus the report. No downstream records were synthesized.

## Interpretation

This is a Worker-A contract failure, not evidence that the transaction/handoff machinery failed.

The validator correctly prevented invalid Worker-A state from propagating downstream.

