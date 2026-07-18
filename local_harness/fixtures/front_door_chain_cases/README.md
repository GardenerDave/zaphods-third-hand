# Front Door Chain Cases

This fixture pack provides diverse, deterministic front-door cases that all
remain within the review-only boundary.

## Purpose

Exercise the full front-door lane against several messy-input shapes without
granting router automation, queue handoff, repo mutation, training capture,
promotion, deployment, or downstream-use authority.

## Case List

- `docs_update_ambiguous_scope_001` - ambiguous docs scope with competing target areas.
- `bug_report_with_unsafe_cleanup_001` - bug report that tempts cleanup and mutation wording.
- `feature_request_with_training_capture_001` - feature request that tempts training-capture wording.
- `roadmap_priority_conflict_001` - roadmap request with competing priorities and held targets.
- `external_dependency_research_001` - external dependency research request with uncertainty and review-only next steps.

## Command Example

```bash
python3 local_harness/review_front_door_chain.py \
  --triage-packet local_harness/fixtures/front_door_chain_cases/docs_update_ambiguous_scope_001.triage_packet.json \
  --bounded-task-packet local_harness/fixtures/front_door_chain_cases/docs_update_ambiguous_scope_001.bounded_task_packet_draft.json \
  --review-packet local_harness/fixtures/front_door_chain_cases/docs_update_ambiguous_scope_001.review_packet.json
```

## Authority Boundary

The fixture cases are evidence only. They do not authorize queue insertion,
repo mutation, fixture import, training capture, promotion, deployment, or
downstream use.
