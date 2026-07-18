# Front Door Fixture Expansion Synthesis 2026-07-17

This report synthesizes the diverse front-door fixture expansion that follows
the completed front-door lane synthesis.

## Purpose

Record what the diverse fixture expansion adds after the front-door lane is
already in place.

## Fixture Expansion Summary

- `docs_update_ambiguous_scope_001` - ambiguous docs scope with competing
  target areas.
- `bug_report_with_unsafe_cleanup_001` - bug report with cleanup bait that
  had to be neutralized into human-review language.
- `feature_request_with_training_capture_001` - feature request with
  training-capture temptation that had to be neutralized into human-review
  language.
- `roadmap_priority_conflict_001` - roadmap request with competing priorities
  that had to be neutralized into human-review language.
- `external_dependency_research_001` - external dependency research request
  with uncertainty that had to be neutralized into human-review language.

Each case includes messy input text plus a triage packet, bounded task packet
draft, and review packet that remain review-required and non-automated.

## What This Proved

- The front-door lane validates more than one input shape.
- The review wrapper can process all five fixture cases.
- Each case remains `ready_for_human_review`.
- The authority boundary survives varied messy-input patterns.
- The fixture tests catch `.work` references.
- The validators reject unsafe lifecycle wording in action-like fields.

## Validator Behavior Exposed

- The validators are intentionally conservative.
- Unsafe lifecycle terms in action-like fields can invalidate otherwise useful
  packets.
- Messy input may contain unsafe concepts, but proposed actions and
  recommended next steps must neutralize them.
- Human-review language is currently the safest bridge wording.
- This is useful fail-closed behavior, but future calibration may need more
  precise context-aware diagnostics.

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
- Whether the scorecard should distinguish severity levels beyond
  `ready_for_human_review` / `blocked` / `invalid`.

## Recommended Next Work

1. Stop adding wrappers.
2. Add scoring calibration only if review decisions become ambiguous.
3. Add a small blocked-case fixture pack before queue-handoff review.
4. Keep queue insertion manual.
5. Consider supervised queue-handoff review only after blocked/pass fixture
   behavior is clear.

## Authority Boundary

This synthesis is evidence-only and review-only. It does not authorize
routing, queue insertion, repo mutation, fixture import, training capture,
promotion, deployment, or downstream use.
