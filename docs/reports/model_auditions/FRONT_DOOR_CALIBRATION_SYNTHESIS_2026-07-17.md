# Front Door Calibration Synthesis 2026-07-17

This report records the front-door lane calibration state after adding both
passing and blocked fixture packs.

## Purpose

Capture the current calibration state for the supervised front-door lane
after the passing diverse fixture pack and the blocked/invalid fixture pack
are both in place.

## Calibration Coverage

Passing cases:

- `docs_update_ambiguous_scope_001`
- `bug_report_with_unsafe_cleanup_001`
- `feature_request_with_training_capture_001`
- `roadmap_priority_conflict_001`
- `external_dependency_research_001`

Blocked or invalid cases:

- `triage_missing_review_required_001`
- `bounded_task_queue_inserted_001`
- `review_repo_mutation_authorized_001`
- `missing_authority_boundary_term_001`
- `malformed_review_packet_001`

## What This Proves

- The review wrapper accepts multiple valid messy-input-derived chains.
- The review wrapper rejects blocked or invalid chains.
- The scorecard distinguishes `ready_for_human_review` from blocked and
  invalid outcomes.
- Diagnostics are preserved for blocked cases.
- Authority statuses remain non-authoritative at the wrapper level.
- `.work` references are rejected by fixture tests.
- Queue insertion, repo mutation, missing authority terms, missing review
  requirements, and malformed review evidence all fail closed.

## Failure Modes Covered

- missing `review_required`
- queue handoff already inserted
- repo mutation authorized
- missing `no_downstream_use_authority`
- malformed review packet
- unsafe lifecycle wording in action-like fields from the prior diverse
  fixture expansion

## What Remains Unproven

- Router automation.
- Automatic queue handoff.
- Unattended execution.
- Repo mutation authority.
- Fixture import authority.
- Training capture.
- Prompt patch promotion.
- Deployment.
- Downstream-use authority.
- Broad reliability across arbitrary messy-input domains.
- Whether scorecard severity needs finer categories.
- Whether a future supervised queue-handoff review should accept only a
  subset of ready cases.

## Recommended Next Work

1. Stop adding front-door structure unless review pain appears.
2. Add no more wrappers for now.
3. Use the pass and blocked fixture packs as calibration evidence.
4. Consider a supervised queue-handoff review design only as a document or
   spec next, not implementation.
5. Keep queue insertion manual.
6. If queue-handoff review is explored, require explicit human approval and
   a separate fail-closed validator before any queue-writing command exists.

## Authority Boundary

This synthesis is evidence-only and review-only. It does not authorize
routing, queue insertion, repo mutation, fixture import, training capture,
promotion, deployment, or downstream use.
