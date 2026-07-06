# Supervised Downstream-Use Gate Record

The supervised downstream-use gate layer sits directly after supervised review
decision records. It records whether a reviewed output may be used as bounded
input for a next supervised step.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> orchestration packet
  -> model prompt packet
  -> supervised model attempt record
  -> supervised attempt output validation
  -> supervised review decision record
  -> supervised downstream-use gate record (this layer)
  -> future supervised handoff layers
```

## What this layer does

`local_harness/supervised_downstream_use_gate.py` provides:

- `validate_supervised_downstream_use_gate_record(record)`
- `build_supervised_downstream_use_gate_record(...)`

The builder consumes:

- supervised review decision record
- explicit requested downstream use
- explicit operator metadata
- explicit gate reason

And produces a deterministic gate record with:

- linked IDs (`decision_id`, `attempt_id`, `validation_id`, `triage_id`, `orchestration_id`)
- explicit gate status (`allowed` or `blocked`)
- explicit gate scope and reason
- bounded allowed downstream use entries
- explicit prohibited downstream-use entries
- explicit authority boundaries
- provenance linkage to the input decision ID

## Review decision vs downstream-use gate

This layer preserves separation:

- review decision records review outcome
- downstream-use gate records eligibility for bounded next-step supervised input
- accepted review decision does not imply execution authority

`gate_status: allowed` is valid only when `review_decision: accepted`.

## Safety boundaries

This layer enforces that gates do not grant:

- command execution authority
- direct file modification authority
- patch application authority
- automatic patch promotion authority
- automatic training authority
- default failure-to-curriculum capture authority

Allowed gates remain bounded supervised input gates, not execution or mutation
authority.

## Renderer behavior

`local_harness/render_supervised_downstream_use_gate.py` renders a plain-text
review artifact with gate IDs, review decision, downstream-use request, gate
status and scope, operator metadata, gate reason, allowed/prohibited downstream
use, authority boundaries, provenance, and explicit review requirement
statements.

## What this layer does not do

This layer does not:

- call models
- execute commands
- modify files
- apply patches
- promote patches
- train adapters
- capture failures into curriculum by default

It prepares future supervised handoff layers while keeping reviewed output and
executable authority distinct.
