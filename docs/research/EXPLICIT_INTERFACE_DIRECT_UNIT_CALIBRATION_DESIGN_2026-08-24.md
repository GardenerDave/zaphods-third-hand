# Explicit-Interface Direct-Unit Calibration

Date: 2026-08-24
Status: frozen, unexecuted, model-free

## Purpose and scientific boundary

The completed Stage B result was valid at the frozen-validator decision level,
but its construct was `INTERFACE_CONVENTION_DOMINATED`: exact review ontology
and literal reference predicates were not fully supplier-visible. This program
creates a new competence unit in which every semantic condition capable of
failing direct capability is visible in the experiment-authored payload.

`EXPLICIT_INTERFACE_IS_NEW_COMPETENCE_UNIT=true`
`OLD_INTERFACE_BOUNDED_EVIDENCE_TRANSFER_TO_EXPLICIT_INTERFACE_PERMITTED=false`

The old Stage A/Stage B hidden-interface 0/8 observations remain historical
evidence about the old interface and are not pooled into the explicit-interface
direct rate or used as predictors here.

The calibration measures direct competence under an explicit contract. It does
not yet test whether bounded evidence is superior to broad evidence and does
not create a Stage C policy-comparison holdout.

## Frozen competence unit

`supplier × capability_family × explicit_interface × direct_responsibility × validated_direct_artifact`

Both suppliers are `DIRECT_RESPONDER`; `downstream_dependencies=[]`. The
validated artifact is the supplier's own JSON response. Deterministic parsing
and evaluation are validation infrastructure, not a downstream model.

Suppliers remain `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf via JARVIS_LOCAL`
and `codex-cli-0.146.0 via the preserved service mechanism`. Provider-native
state remains best-available observation and is not used to rewrite this
freeze.

## Explicit interfaces

`duc_explicit_triage_direct_json_v1` requires JSON with `route`, `rationale`, and
`review_status`; `route` must equal visible `review` and `review_status` must
equal visible `ready_for_review`. The prompt visibly lists every case-specific
rationale fact and prohibited fact. `additional_properties=allowed`.

`duc_explicit_unsupported_certainty_direct_json_v1` requires JSON with `known_facts`, `uncertainty`,
`review_status`, and `next_step`; `review_status=ready_for_review` is visible.
The prompt visibly lists the fact, uncertainty, next evidence, and prohibited
broad claim. No hidden literal or ontology requirement remains.

Validation dimensions are kept separate: transport, parse, required fields,
explicit-interface validity, task-semantic validity, review status, protocol,
and direct capability.

`SCORING_ONLY_SEMANTIC_PREDICATES=0`
`UNCOMMUNICATED_LITERAL_REQUIREMENTS=0`
`UNCOMMUNICATED_ONTOLOGY_VALUES=0`

## Frozen calibration cohort and controls

- 8 fresh triage-routing cases;
- 8 fresh unsupported-certainty cases;
- 16 cases × 2 suppliers = 32 planned future calls;
- no response directory or outcome exists;
- no adaptive extension, retry, replay, repair, teacher, worker, tools,
  repository access, qualification, or production-routing change.

Case generation is deterministic and model-free, uses new source anchors, and
does not reuse Stage A/Stage B or Scope V0 IDs/text. Supplier weakness was not
used for selection. The payload manifest contains exact canonical payloads;
the runtime manifest contains no evaluator expectations.

## Aggregation and future gate

After this calibration is executed and sealed, report exact family rates plus
`MICRO_AGGREGATE_DIRECT_EXPLICIT` and
`FAMILY_MACRO_AGGREGATE_DIRECT_EXPLICIT`. Neither is automatically a routing
policy. A future replication is conditional on naturally identifiable broad
and bounded policies and fresh holdout space:

`FUTURE_REPLICATION_CONDITIONAL_ON_NATURAL_DISAGREEMENT=true`
`MANUFACTURED_POLICY_DISAGREEMENT_PERMITTED=false`

## Firewall

Preflight may verify evaluator hashes. Acquisition is designed to run without
opening evaluator, scoring-policy, or expected-result artifacts. The additive
missing-evaluator regression is part of the freeze validation. Historical
`evaluator_loaded_during_acquisition=false` is preserved but ambiguous: the
prior harness accessed evaluator bytes for hashing while loading no evaluator
semantics. See the additive firewall-marker erratum.

## Provenance and characterization

Design base commit: `fc32912bd03c32c8c70980edcb345e773b275ca8`
Prior Stage B result commit: `8f828328a0aeb4062de83e17a16a2aef0b6f4631`
Prior Stage B validity diagnosis commit: `fc32912bd03c32c8c70980edcb345e773b275ca8`

`NEW_INTERFACE_ID=true`
`OLD_BOUNDED_EVIDENCE_TRANSFERRED=false`
`EVALUATOR_SYNTHETIC_SATISFIABILITY=16/16`
`TARGETS_FRESH=true`
`TARGET_OUTCOMES=0`
`SUPPLIER_CALLS=0`
`MODEL_CALLS=0`
`FUTURE_REPLICATION_CONDITIONAL_ON_NATURAL_DISAGREEMENT=true`

`PRIMARY_CHARACTERIZATION=EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FROZEN_UNEXECUTED`

Artifact hashes are recorded in the machine-readable freeze:

```text
{
  "interface": "7ca9d62424f421d58cc8710c06e585419dd14f67e2bad531c04ae99737d6fef3",
  "runtime_manifest": "d375eb7639582d942a437a3d743280c4fd2a3c7ab7477321e20bf6e712fab19c",
  "evaluator_cases": "31f91f9768e37c8e9cf4718497fe2f74633c5453b77f853cf160525e088f2427",
  "payload_manifest": "117dba94861d1d454c46e787bcaa0ec57783f448b3fe430aa2400c09e158cd08",
  "freshness_audit": "d0d1aa93ef21ff758a7d47078662471076f3b6779801d115dc5d0f89916d7955"
}
```
