# LARQL Machinery Quickstart

This is the shortest path for a new reader to understand and run the completed LARQL machinery.

The LARQL machinery is supervised guided capability: it packages bounded failure patterns into reviewable rule trials, preserves evidence, and keeps install and probe authority explicit and separate.

It is not a training system, not an unattended runtime-governance system, and not a claim that the model or repo is now fully autonomous.

## What it is

The completed machinery now includes:

- a rule registry manifest
- a registry status generator
- a one-command evidence packet collector
- a lifecycle status driver
- a concise completed-rule demo

The three completed registered rules are:

1. `absence_of_evidence_file_authority_v0`
2. `unsupported_certainty_scope_claim_v0`
3. `unsupported_file_target_authority_v0`

## What it is not

This machinery does not:

- create new runtime rules
- run live probes by itself
- write training data
- write dataset artifacts
- write durable memory
- promote a candidate
- mutate model weights
- install or modify runtime rules
- perform automatic failure-to-curriculum capture

Failure-to-curriculum capture remains opt-in only and was not performed by this machinery.

## Recommended path for a new reader

1. Read `docs/LARQL_COMPLETED_RULE_DEMO.md` for one completed end-to-end example.
2. Read `docs/reports/affordance_larql/LARQL_LIFECYCLE_STATUS.md` for a compact lifecycle summary.
3. Read `docs/reports/affordance_larql/LARQL_MACHINERY_PACKAGING_AUDIT_2026-06-29.md` for the packaging direction.
4. Use the commands below to regenerate registry, packet, and lifecycle summaries as needed.

## Regenerate registry status

```bash
python3 local_harness/larql_rule_registry.py \
  --registry docs/reports/affordance_larql/larql_rule_registry.json \
  --out docs/reports/affordance_larql/LARQL_RULE_REGISTRY_STATUS.md
```

## Generate an evidence packet for the unsupported-file-target rule

```bash
python3 local_harness/larql_evidence_packet.py \
  --registry docs/reports/affordance_larql/larql_rule_registry.json \
  --rule-id unsupported_file_target_authority_v0 \
  --out .work/larql_evidence_packets/unsupported_file_target_authority_v0
```

## Regenerate lifecycle status

```bash
python3 local_harness/larql_lifecycle_status.py \
  --registry docs/reports/affordance_larql/larql_rule_registry.json \
  --packet-root .work/larql_evidence_packets \
  --out docs/reports/affordance_larql/LARQL_LIFECYCLE_STATUS.md
```

## Where generated outputs go

- registry status: `docs/reports/affordance_larql/LARQL_RULE_REGISTRY_STATUS.md`
- evidence packet manifest: `.work/larql_evidence_packets/<rule_id>/evidence_packet_manifest.json`
- evidence packet summary: `.work/larql_evidence_packets/<rule_id>/evidence_packet_summary.md`
- lifecycle status: `docs/reports/affordance_larql/LARQL_LIFECYCLE_STATUS.md`

## What remains intentionally held

The machinery keeps these boundaries explicit:

- no model call is made by the status or packaging drivers
- no training data is written
- no dataset artifact is written
- no durable memory is written
- no candidate is promoted
- no model weights are mutated
- no runtime rules are installed or modified
- no automatic failure-to-curriculum capture is performed

## Next project step

The next project step is a small reusable navigation layer on top of the registry, evidence packet collector, and lifecycle status driver. That layer should summarize what is complete or held without re-running the whole workflow and without adding another hand-built LARQL rule.

