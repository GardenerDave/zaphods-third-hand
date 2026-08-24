# Direct-Unit Calibration Freeze Semantic Audit

Date: 2026-08-24

## Decision

The V1 freeze at `850913c2c6690694c20a28a2048421b2e2d221ed` is preserved as
immutable, unexecuted historical evidence. It added consequential semantics:
strict extra-property rejection, exact route labels, family-field-scoped
literal predicates, family-field type requirements, and the literal
`more evidence` next-step requirement were not established by the design or
the preserved validator path.

The historical validator checks required-key presence, duplicate JSON keys,
registered reference facts, and exact `review_status`; it does not reject
additional keys or enforce family-specific field types. Historical phrase
facts are evaluated over the serialized declared output, not a selected field.

The corrected V2 therefore preserves all 16 case IDs, request text, order,
families, supplier arms, 32-call budget, non-adaptive sampling, and Stage A /
Stage B firewall, while using the historical permissive structural and generic
semantic boundary. It does not require exact route labels or `more evidence`.

## Provenance

- design commit: `f55f677c46a0746ef4ba4dda4072c4e2f452b544`
- original freeze commit: `850913c2c6690694c20a28a2048421b2e2d221ed`
- original freeze executed: `false`
- original freeze outcome contamination: `false`
- original freeze superseded before execution: `true`
- historical extra-field policy: `ALLOWED_OR_UNRESTRICTED`
- hardened design extra-field policy: `UNSPECIFIED`

## Field-level adjudication

| Family/rule | Historical basis | Classification |
|---|---|---|
| Triage required keys | Run 5 `required_fields` | faithful serialization |
| Triage `additional_properties=false` | absent; no validator rejection | new experiment semantic |
| Triage exact route labels | no preserved route equality | new experiment semantic |
| Triage field-scoped phrase predicates | historical scope is serialized output | new experiment semantic |
| Triage `review_status` | historical direct-field check | faithful serialization |
| Unsupported required keys | Run 4A `required_fields` | faithful serialization |
| Unsupported `additional_properties=false` | absent; no validator rejection | new experiment semantic |
| Unsupported field-scoped phrase predicates | historical scope is serialized output | new experiment semantic |
| Unsupported literal `more evidence` | absent from preserved contract | new experiment semantic |
| Unsupported `review_status` | historical direct-field check | faithful serialization |
| Exact prompt prose | authority/responsibility fixed, wording not exact | compatible explicit successor |

## Runtime boundary

The V2 payload manifest is a deterministic, evaluator-free serialization of
the frozen requests, authority context, prompt, and permissive output contract.
It records one payload hash per case and the same payload for both supplier
arms. Supplier-native envelopes remain a separate, best-observed condition.

## Controls

`new_triage_cases=8`, `new_unsupported_certainty_cases=8`,
`planned_new_supplier_calls=32`, `model_calls=0`, `teacher_calls=0`,
`tool_calls=0`, and `external_inference_calls=0`. No response, result, case,
Scope V0 artifact, policy, qualification, or production-routing change exists.

Authoritative corrected freeze:
`docs/research/DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json`

The machine-readable crosswalk is in
`DIRECT_UNIT_CALIBRATION_FREEZE_SEMANTIC_MATRIX_2026-08-24.json`.
