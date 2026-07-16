# Supervised Attempt Output Validation

The supervised attempt output-validation layer sits directly after supervised
model attempt recording. It validates raw model output against an explicit
output contract and produces reviewable evidence.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> orchestration packet
  -> model prompt packet
  -> supervised model attempt record
  -> supervised attempt output validation (this layer)
  -> later supervised review decision record
```

## What this layer does

`local_harness/supervised_attempt_output_validator.py` provides:

- `validate_supervised_attempt_output_validation_record(record)`
- `validate_supervised_attempt_output_against_contract(...)`

The validator takes a supervised attempt record and an output contract, then
emits one output-validation record with:

- validation identity and attempt linkage
- copied triage/orchestration/prompt packet IDs
- contract checks and diagnostics
- deterministic validation status (`passed` or `failed`)
- acceptance status fixed to `not_reviewed`
- explicit authority boundaries
- provenance and review requirement

This documentation slice was selected from the cron dogfood consolidation
report at `.work/dogfood/reviews/dogfood_packet_consolidation_20260716_0200.md`
to tighten the repo-grounded supervised attempt path.

### Contract checks

For `output_contract.format == "json"`:

- parse JSON from `raw_model_output`
- fail gracefully with diagnostics if parsing fails
- enforce `required_fields` when present
- enforce non-empty `reason` when `requires_reason: true`
- classify completion claims as `supported`, `unsupported`, or `refuted` when
  the reviewed record includes a claim verdict field or equivalent contract
  field
- require objective evidence and provenance linkage for any claim verdict

Validation passes only when all required checks pass.

Validation fails when one or more required checks fail.

## Safety boundaries

This layer enforces:

- validation is evidence, not acceptance
- no command execution authority
- no direct file modification authority
- no automatic patch promotion authority
- no automatic training authority
- no default failure-to-curriculum capture authority
- human review required before downstream use
- no automatic promotion, merge, deployment, or cleanup authority

It rejects records or content that claim acceptance authority.

## What this layer does not do

This layer does not:

- call models
- execute commands
- modify files
- accept output for use
- promote patches
- train adapters
- capture failures into curriculum by default
- infer downstream-use eligibility

It preserves raw output as evidence and does not transform model output into
approved actions.

## Why this exists

Output-contract validation provides deterministic evidence about output shape
conformance without granting authority. It prepares the next layer: supervised
review decision records.
