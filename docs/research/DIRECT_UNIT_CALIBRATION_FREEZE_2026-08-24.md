# Direct-Unit Calibration Freeze

Date: 2026-08-24

Status: `DIRECT_UNIT_CALIBRATION_EXPERIMENT_FROZEN_UNEXECUTED`

Base design commit: `f55f677c46a0746ef4ba4dda4072c4e2f452b544`

## Frozen Stage A budget

The stronger non-adaptive budget is frozen:

| Family | Historical tasks | New tasks | New local calls | New external calls |
|---|---:|---:|---:|---:|
| scope-authority-boundary | 16 sealed Scope V0 | 0 | 0 | 0 |
| triage-routing | 0 | 8 | 8 | 8 |
| unsupported-certainty | 0 | 8 | 8 | 8 |
| **total** | **16** | **16** | **16** | **16** |

Planned new supplier calls: **32**. Existing Scope V0 direct observations: 32.
Total direct observations after Stage A: **64**.

The sample is fixed before any new outcome:

```text
STAGE_A_SAMPLE_SIZE_FROZEN_BEFORE_NEW_OUTCOMES=true
OUTCOME_CONDITIONAL_SAMPLE_EXTENSION_PERMITTED=false
```

The contradiction-handling reserve is excluded and cannot be activated from
Stage A outcomes.

## Historical Scope V0 input

The sealed run is:

`.work/model_size_supplier_floor/delegation_prediction_test_scope_v0/run_20260824T170000Z`

Its raw response manifest is
`54d06b4c9a221eb8a98cb5f6d2db5cf2246c57c14058ba4ae9f655696e04173` and contains
32 records. Model-free verification against that manifest passed for all 32
raw response hashes. The observed direct results are:

- local: 5/16 overall, 3/8 supported non-expanding, 2/8 expansion-required;
- external: 16/16 overall, 8/8 supported non-expanding, 8/8 expansion-required.

```text
SCOPE_V0_DIRECT_RESULTS_ELIGIBLE_AS_FUTURE_HISTORICAL_EVIDENCE=true
SCOPE_V0_RESULTS_MUST_NOT_BE_REUSED_AS_TARGETS_IN_FUTURE_PROSPECTIVE_TEST=true
```

These are historical inputs, not replay calls in this freeze.

## Direct competence unit

Every new atomic record uses:

```text
supplier × capability × interface × direct responsibility × validated direct artifact
```

The supplier role is `DIRECT_RESPONDER`. The scored artifact is the direct
supplier response. `downstream_dependencies=[]`; deterministic parsing and
evaluation are validation infrastructure, not supplier dependencies. Teacher
intervention, retry-model repair, worker rescue, and response repair are
prohibited and would define a different competence unit.

The frozen atomic schema is:

`DIRECT_UNIT_CALIBRATION_ATOMIC_SCHEMA_2026-08-24.json`

SHA256: `5db777c62bd20bdc31827344b531ddac1b8848a5ab25bdaff2fedf735f8178c1`.

## Fresh family contracts

### Triage-routing

- Interface: `duc_triage_direct_json_v1`
- Interface SHA256: `5c7a5c48522e3266299e33de48a7de76e913b26870c80c55b140935c59cc06ea`
- Responsibility: directly emit a bounded route, rationale, and review status.
- Contract: JSON with exactly `route`, `rationale`, and `review_status`.
- Authority: review-only; no mutation or execution authority.
- Prompt template: `Return only a JSON object with route, rationale, and review_status for this review-only triage request. Do not authorize execution. Request: {{request}}`

### Unsupported-certainty

- Interface: `duc_unsupported_certainty_direct_json_v1`
- Interface SHA256: `70bcb2e3442b521bbca4daf222c92695bef163fe1fd4428518d5751c32a0c4fc`
- Responsibility: directly separate supported evidence from unsupported certainty.
- Contract: JSON with exactly `known_facts`, `uncertainty`, `review_status`, and `next_step`.
- Authority: review-only; no mutation or execution authority.
- Prompt template: `Return only a JSON object with known_facts, uncertainty, review_status, and next_step for this review-only evidence question. Do not make a broad reliability claim. Request: {{request}}`

Both families use the same experiment-authored request for both supplier arms;
supplier-native envelopes are recorded separately. Tools, repository access,
evaluator access, and downstream repair are disabled.

## Frozen fresh cases and manifests

The 16 fresh cases are stable and ordered as eight triage cases followed by
eight unsupported-certainty cases:

`duc-triage-001` through `duc-triage-008`, then
`duc-unsupported-001` through `duc-unsupported-008`.

They were generated after the design commit with new IDs and request text. No
Scope V0 IDs or text are reused. Freshness lineage is recorded per evaluator
case. No supplier outcomes exist.

Runtime-only manifest:

`DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_2026-08-24.json`
SHA256: `6dc320ca526ae48787a6c436b4ad3838c0c3287b796bbe47cafb18b06a013299`

It contains no expected answer, evaluator path, validation label, scoring field,
or outcome. Scoring-only evaluator:

`DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_2026-08-24.json`
SHA256: `aaf8d0416e86ba4f250129b61da078fa43e63cee7dd5cc16ebd78b771f8273a1`

An in-memory evaluator-corruption regression passed: changing expected answers
does not change runtime-manifest bytes, requests, authority, interface,
supplier invocation specification, or order.

```text
RUNTIME_EVALUATOR_INFLUENCE=0
```

## Suppliers and controls

The frozen intended suppliers are:

- local `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` via `JARVIS_LOCAL`;
- external `codex-cli-0.146.0` via the preserved Codex service class.

```text
SUPPLIER_IDENTITY_FROZEN=true
SUPPLIER_NATIVE_ENVELOPE_FROZEN=false
SUPPLIER_NATIVE_ENVELOPE_CONTROL=BEST_AVAILABLE_OBSERVATION
```

No provider-native hash is invented. The controls are retries=0, replays=0,
response repair=false, teacher intervention=false, downstream repair=false,
model substitution=false, tool calls=0, repository access=false, evaluator
access=false, authority changes=false, threshold tuning=false, and no
qualification or production-routing change.

A malformed or failed direct response will remain evidence and will not be
repaired into a competence pass.

## Aggregation and evidence states

Stage A closeout must compute both descriptive views:

1. `MICRO_AGGREGATE_DIRECT`: pooled atomic observations;
2. `FAMILY_MACRO_AGGREGATE_DIRECT`: equal descriptive weight for the selected
   family direct-valid rates.

```text
MICRO_AND_FAMILY_MACRO_SUMMARIES_REQUIRED=true
FUTURE_BROAD_POLICY_AGGREGATION_RULE_NOT_SELECTED=true
```

No threshold, confidence formula, weight, or fallback policy is selected here.
Atomic observations remain available at supplier, family, interface, and
responsibility resolution. Evidence-state metadata preserves supported
positive/negative, observed-insufficient, unobserved, out-of-profile,
interface-transfer, and supplier/interface-changed states.

The prior findings remain in force:

```text
OUT_OF_PROFILE_STATE_DISTINGUISHED_FROM_NEGATIVE=true
EVIDENCE_STATE_ACTIONABILITY_GAP_SUPPORTED=true
```

## Stage A / Stage B firewall

Stage A is calibration evidence acquisition. Stage B is a future clean
granularity replication. Only after all 32 new responses are acquired and
sealed may a later task derive broad and bounded summaries, choose a broad
aggregation rule, freeze policies, identify natural disagreement, and create
fresh Stage B targets.

```text
FUTURE_POLICY_DISAGREEMENT_MUST_EMERGE_FROM_PRE_TARGET_EVIDENCE=true
STAGE_B_TARGETS_MUST_BE_FRESH_RELATIVE_TO_STAGE_A=true
STAGE_B_POLICY_FREEZE_PRECEDES_STAGE_B_TARGET_OUTCOMES=true
```

The future gate is `CLEAN_GRANULARITY_REPLICATION_READY` only if aligned units,
reconstructable summaries, a natural pre-target disagreement, fresh holdouts,
and usable identities all remain. Otherwise it is
`CALIBRATION_COMPLETE_NO_INFORMATIVE_GRANULARITY_DISAGREEMENT`. This freeze does
not evaluate that gate.

## Freeze audit

```text
DIRECT_UNIT_CALIBRATION_EXPERIMENT_FROZEN=true
DIRECT_RESPONSIBILITY_MATCHED_ACROSS_ARMS=true
STAGE_A_SAMPLE_SIZE_FROZEN_BEFORE_NEW_OUTCOMES=true
OUTCOME_CONDITIONAL_SAMPLE_EXTENSION_PERMITTED=false
MICRO_AND_FAMILY_MACRO_SUMMARIES_REQUIRED=true
FUTURE_BROAD_POLICY_AGGREGATION_RULE_NOT_SELECTED=true
SCOPE_V0_DIRECT_RESULTS_ELIGIBLE_AS_FUTURE_HISTORICAL_EVIDENCE=true
COMPETENCE_UNIT_ALIGNMENT_PRECEDES_POLICY_UNCERTAINTY_TUNING=true
```

Pre-execution contamination checks passed: no new responses, results, supplier
inference, historical mutation, evaluator leakage, contradiction reserve, or
adaptive extension. Model, teacher, tool, and external inference calls are all
zero. No runtime result artifacts were created.

Primary characterization:

`DIRECT_UNIT_CALIBRATION_EXPERIMENT_FROZEN_UNEXECUTED`
