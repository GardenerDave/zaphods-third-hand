# Supervised Handoff Packet

The supervised handoff packet layer sits directly after supervised downstream-use
gate records. It packages reviewed and gated output as bounded input for a next
supervised step.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> orchestration packet
  -> model prompt packet
  -> supervised model attempt record
  -> supervised attempt output validation
  -> supervised review decision record
  -> supervised downstream-use gate record
  -> supervised handoff packet (this layer)
  -> future workflow-specific supervised consumers
```

## What this layer does

`local_harness/supervised_handoff_packet.py` provides:

- `validate_supervised_handoff_packet(record)`
- `build_supervised_handoff_packet(...)`

The builder consumes:

- supervised downstream-use gate record
- explicit next-step type
- explicit next-step summary
- explicit handoff payload metadata
- explicit operator metadata
- explicit handoff reason

This handoff layer is the final bounded packaging step in the supervised
attempt path selected from the cron dogfood consolidation report. It packages
reviewed input for the next supervised consumer, not for unattended execution.

And produces a deterministic handoff packet with:

- linked IDs (`gate_id`, `decision_id`, `attempt_id`, `validation_id`, `triage_id`, `orchestration_id`)
- explicit gate and handoff statuses
- explicit handoff scope, next-step metadata, and reason
- bounded allowed downstream use entries
- explicit prohibited downstream-use entries
- explicit completion-claim status when present (`supported`, `unsupported`, or
  `refuted`)
- explicit authority boundaries
- provenance linkage back to the input gate ID

## Gate vs handoff packet

This layer preserves separation:

- downstream-use gate records whether bounded input use is allowed
- handoff packet packages bounded input for a next supervised consumer step
- prepared handoff does not imply execution or mutation authority

`handoff_status: prepared` is valid only when `gate_status: allowed`.

## Safety boundaries

This layer enforces that handoffs do not grant:

- command execution authority
- direct file modification authority
- patch application authority
- automatic patch promotion authority
- automatic training authority
- default failure-to-curriculum capture authority

Prepared handoffs remain bounded supervised input packets only.

## Renderer behavior

`local_harness/render_supervised_handoff_packet.py` renders a plain-text review
artifact with IDs, gate/handoff status, scope, next-step details, handoff
payload, operator metadata, reason, downstream-use bounds, authority
boundaries, provenance, and explicit review requirement statements.

## What this layer does not do

This layer does not:

- call models
- execute commands
- modify files
- apply patches
- promote patches
- train adapters
- capture failures into curriculum by default
- infer cleanup authority

It prepares future workflow-specific supervised consumers while preserving the
distinction between input preparation and executable authority.
