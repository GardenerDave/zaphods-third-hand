# Evidence Side Trust Audit 2026-08-31

## Evidence inventory

The preserved natural A1/A2/A3 bundles expose structured artifacts and provenance, but not a trusted typed layer for transport qualification or semantic capability.

### A1

- Evidence ID: `case_a1_evidence`
- Projected evidence: `.work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/evidence_projection.json`
- Source type: `model_produced_and_evaluator_produced`
- Structured fields available: `budget`, `evidence_sources`, `output_contract`, `rendered_patch_deltas`, `selected_prompt_patches`, `task_summary`, `task_title`
- Derived properties:
  - `raw_response_integrity` via `raw_response_integrity_v1`
- Unknown properties:
  - `transport_qualification`
  - `bounded_handoff_success`
  - `semantic_capability`
  - `semantic_acceptance`

### A2

- Evidence ID: `case_a2_evidence`
- Projected evidence: `.work/semantic_claim_discipline_final_20260831/task_a/patched/20260831T133000Z/evidence_projection.json`
- Source type: `model_produced_and_evaluator_produced`
- Structured fields available: same experiment-transaction fields as A1
- Derived properties:
  - none
- Unknown properties:
  - `transport_qualification`
  - `bounded_handoff_success`
  - `semantic_capability`
  - `raw_response_integrity`
  - `semantic_acceptance`

### A3

- Evidence ID: `case_a3_evidence`
- Projected evidence: `.work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/evidence_projection.json`
- Source type: `model_produced_and_evaluator_produced`
- Structured fields available: same experiment-transaction fields as A1
- Derived properties:
  - `raw_response_integrity` via `raw_response_integrity_v1`
- Unknown properties:
  - `transport_qualification`
  - `bounded_handoff_success`
  - `semantic_capability`
  - `semantic_acceptance`

### Structured handoff line

The handoff bundle exposes a bounded reviewer/gate lane, but not a proven downstream success lane:

- `semantic_acceptance` is present as an advisory reviewer-derived property
- `bounded_handoff_success` is not established from the preserved artifacts

That lane does not provide transport qualification or semantic capability for the natural A1/A2/A3 evidence lineage.

## Property coverage

| Property | System-derivable? | Structured source | Deterministic rule | Trust class | Remaining semantic gap |
| --- | --- | --- | --- | --- | --- |
| `transport_qualification` | No | None in the preserved natural bundles | None | `unknown` | No trusted evidence-side transport layer is present for A1/A2/A3 |
| `bounded_handoff_success` | No | None in the preserved handoff bundle | None | `unknown` | Prepared handoff is not downstream success |
| `semantic_capability` | No | None in the preserved natural bundles | None | `unknown` | Semantic capability remains untyped on the evidence side |
| `raw_response_integrity` | Yes | Raw output + local call + validation artifacts | `raw_response_integrity_v1` | `system_derived` | Preservation integrity only |
| `semantic_acceptance` | Yes, but only advisory | Structured reviewer/gate bundle | `semantic_acceptance_v1` | `advisory` | Reviewer disposition is not machine-ground truth |

## Existing Transport Qualification Search

The repository does contain earlier transport-qualification artifacts in the explicit-interface V3 lineage:

- `docs/research/EXPLICIT_INTERFACE_V3_TRANSPORT_QUALIFICATION_2026-08-24.md`
- `docs/research/EXPLICIT_INTERFACE_V3_TRANSPORT_REQUALIFICATION_FINAL_2026-08-24.md`
- `docs/research/EXPLICIT_INTERFACE_V3_TRANSPORT_REQUALIFICATION_FINAL_2026-08-24.json`

Those artifacts establish that the 192.168.1.16 / `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` path was transport-qualified for the explicit-interface V3 calibration lane, with `TRANSPORT_OK` observed on the qualified transport control.

They do **not** bind to the preserved natural A1/A2/A3 evidence lineage:

- different task family
- different qualification scope
- no direct causal linkage to the natural candidate bundles

So they are useful transport history, but not a trusted transport-qualification representation for the natural transport-versus-capability invariant replay.

## Deterministic replay status

The frozen deterministic invariant cannot be replayed end-to-end for the natural A1/A2/A3 lineages because the required trusted evidence-side transport qualification layer is missing.

This is a partial recomposition result, not a full end-to-end success.

## Conclusion

The current structured artifacts are partially sufficient. They support trusted evidence typing for raw response preservation and advisory reviewer/gate provenance, but they do not expose enough trusted evidence-side semantic structure to drive the frozen transport-versus-capability invariant for the natural candidate lineage without another semantic source.

## Next action

Improve source instrumentation rather than asking a model to guess evidence semantics.
