# Corrected Prospective Delegation Prediction Freeze — 2026-08-24

## Status

`PRIMARY_CHARACTERIZATION=PROSPECTIVE_DELEGATION_PREDICTION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED`

This additive correction supersedes the original unexecuted freeze as the
authoritative execution boundary. The original freeze artifacts and commit
`99babf1232ea0e80a2ec89aff579d2eafa790af1` remain preserved historical
evidence and were not edited.

## Semantic adjudication

The original contract asserted `additionalProperties:false`. The preserved
Run 4A contract declared the four required fields, and the authoritative
validator at `local_harness/supervised_attempt_output_validator.py` checks
required-field presence (`_check_required_fields`, lines 203–219), field types
(`_check_required_field_types`, lines 223–258), duplicate JSON keys, target
separation, and review semantics. It contains no unexpected-key or exact-key
set rejection. The Run 4A worker contract likewise declares `required_fields`
without an additional-property rule.

Therefore:

- `HISTORICAL_EXTRA_FIELD_POLICY=ALLOWED` (additional fields were not rejected
  by the preserved validation path).
- `HARDENED_DESIGN_EXTRA_FIELD_POLICY=UNSPECIFIED`.
- `FREEZE_INTERFACE_CONTRACT_ADDS_NEW_EXPERIMENT_SEMANTICS=true` for the
  original freeze.

The corrected V2 contract omits the unentailed exact-key-set rule and retains
the hardened design’s four required fields, field types, review-only authority
boundary, no-expansion semantics, and zero-tool/evaluator-isolation controls.
Its field-level crosswalk is embedded in
`DELEGATION_PREDICTION_PROSPECTIVE_INTERFACE_CONTRACT_V2_2026-08-24.json`.

## Runtime/evaluator boundary

The original freeze colocated per-case evaluator references with frozen case
records. That was an artifact-colocation defect, not target-outcome or
expected-answer leakage into supplier inputs. The new
`DELEGATION_PREDICTION_PROSPECTIVE_RUNTIME_MANIFEST_2026-08-24.json` is the
only intended future execution manifest. It preserves the exact 16 cases and
order, requests, contexts, candidate suppliers, predictor-visible evidence,
frozen policy outputs, and controls, while containing no evaluator reference,
expected answer, scoring, validation, or outcome field.

The evaluator remains scoring-only. The model-free isolation check proves that
perturbing evaluator expectations cannot change runtime-manifest content,
predictor decisions, supplier choices, experiment-authored payloads, or
authority/context. `RUNTIME_EVALUATOR_INFLUENCE=0`.

## Frozen cohort and policies

The cohort is unchanged: 16 cases in the original order, with 8 supplier-
selection disagreements, 8 delegate-vs-abstain disagreements, and 8 binary
expected-success disagreements. The broad aggregate-driven policy, bounded
scope/interface policy, supplier selections, thresholds, lexicographic scoring,
and execution controls are unchanged. The cohort remains deliberately
disagreement-enriched and is not incidence-representative.

## Supplier and interface provenance

The historical and prospective supplier identities are recorded as exact in
the preserved design: local Qwen3-Coder-30B via `JARVIS_LOCAL` and external
`codex-cli-0.146.0`. The prospective protocol is a compatible interface
successor to the historical Run 4A scope contract, not exact interface reuse.
The experiment-authored contract is frozen; supplier-native envelopes are not
fully frozen or observable model-free. Provider/client-native state is an
explicit uncontrolled condition, not an invented hash or an interface-
identity claim. No endpoint or Codex invocation was made.

## Contamination result

- original freeze executed: false;
- original freeze outcome contamination: false;
- original freeze superseded before execution: true;
- prospective runtime directory: absent;
- prospective responses/results: absent;
- model, teacher, tool, and external inference calls: zero;
- historical artifacts mutated: false.

The machine-readable manifest records the complete provenance, hashes, cohort
identity, controls, and audit markers.

`NEXT_DECISION=EXECUTE_FROZEN_PROSPECTIVE_DELEGATION_PREDICTION_EXPERIMENT`
