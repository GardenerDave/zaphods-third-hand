# Direct-Unit Calibration Freeze V2

Date: 2026-08-24
Status: `DIRECT_UNIT_CALIBRATION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED`

## Supersession

This additive V2 freeze supersedes the preserved V1 freeze before execution.
V1 remains immutable historical evidence:

- design commit: `f55f677c46a0746ef4ba4dda4072c4e2f452b544`
- V1 freeze commit: `850913c2c6690694c20a28a2048421b2e2d221ed`
- V1 executed: `false`
- V1 outcome contamination: `false`
- V1 superseded before execution: `true`

The correction removes only unproven execution/scoring constraints. The exact
16 case IDs, requests, ordering, selected families, supplier arms, 32-call
non-adaptive budget, Scope V0 historical input, and Stage A/Stage B firewall
are unchanged.

## Corrected semantic boundary

The preserved validator lineage checks JSON parsing, duplicate keys, required
field presence, registered serialized-output phrase facts, and exact
`review_status`. It does not reject additional properties or impose
family-specific field types on the new triage/unsupported-certainty fields.

Accordingly V2:

- does not require `additionalProperties=false`;
- does not require exact triage route labels;
- evaluates phrase facts over serialized declared output, matching the
  historical `must_include`/`must_not_include` mechanism;
- does not require the literal unsupported-certainty next step `more evidence`;
- retains the historically supported required fields and
  `review_status=ready_for_review`.

The prompt templates are recorded as compatible explicit successors that
serialize the already frozen review-only authority and direct responsibilities;
their prose is not treated as an additional scoring predicate.

## Authoritative V2 artifacts

- `DIRECT_UNIT_CALIBRATION_INTERFACE_CONTRACT_V2_2026-08-24.json`
- `DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json`
- `DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json`
- `DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json`
- `DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json`

The payload manifest freezes the canonical experiment-authored payload and one
hash per case. The same payload hash is used for local and external arms.
Evaluator expectations remain scoring-only and are absent from runtime payloads.
Supplier-native envelopes remain separately observed and are not claimed to be
frozen here.

## Controls

`new_triage_cases=8`, `new_unsupported_certainty_cases=8`,
`planned_new_supplier_calls=32`, `model_calls=0`, `teacher_calls=0`,
`tool_calls=0`, `external_inference_calls=0`. No calibration response,
outcome, replay, Scope V0 mutation, policy change, qualification, or production
routing change exists.

Primary characterization:

`DIRECT_UNIT_CALIBRATION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED`
