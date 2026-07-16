# Supervised Review Decision Record

The supervised review decision layer sits directly after supervised attempt
output-contract validation. It records explicit operator review decisions as a
separate artifact.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> orchestration packet
  -> model prompt packet
  -> supervised model attempt record
  -> supervised attempt output validation
  -> supervised review decision record (this layer)
  -> future supervised downstream-use layers
```

## What this layer does

`local_harness/supervised_review_decision.py` provides:

- `validate_supervised_review_decision_record(record)`
- `build_supervised_review_decision_record(...)`

The builder consumes:

- supervised model attempt record
- output validation record
- explicit reviewer metadata
- explicit decision (`accepted`, `rejected`, `revision_requested`)
- explicit decision reason

The review decision record is the human/operator decision layer for the
supervised attempt path selected in the cron dogfood consolidation report. It
captures the review boundary but does not imply downstream execution.

And produces a deterministic decision record with:

- linked IDs (`attempt_id`, `validation_id`, `triage_id`, `orchestration_id`)
- preserved `validation_status` as evidence
- explicit decision scope and reason
- allowed/prohibited downstream use lists
- explicit completion-claim status when present (`supported`, `unsupported`, or
  `refuted`)
- explicit authority boundaries
- provenance linkage to both input artifacts

## Validation vs acceptance

This layer enforces separation:

- validation is evidence
- review is a human/operator decision
- acceptance is never inferred automatically from validation status

A failed validation cannot be marked `accepted`.

## Safety boundaries

This layer enforces that decisions do not grant:

- command execution authority
- direct file modification authority
- automatic patch promotion authority
- automatic training authority
- default failure-to-curriculum capture authority

Accepted decisions are bounded supervised review artifacts, not autonomous
execution authority.

## Renderer behavior

`local_harness/render_supervised_review_decision.py` renders a plain-text review
artifact with decision IDs, decision details, validation evidence, reviewer
metadata, reason, downstream-use bounds, authority boundaries, provenance, and
review requirement statements.

## What this layer does not do

This layer does not:

- call models
- execute commands
- modify files
- promote patches
- train adapters
- capture failures into curriculum by default

It prepares future supervised downstream-use layers, still behind explicit
review and authority gates.
