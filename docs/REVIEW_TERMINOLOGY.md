# Review Terminology

This document defines the preferred ZTH review terminology before any schema
or code migration changes the existing front-door chain labels.

## Purpose

Use a consistent, review-neutral vocabulary for status labels, docs, and
future APIs. The goal is to keep ZTH supervised and non-automated without
hardcoding the reviewer type into new terminology.

## Preferred Terms

Use:

- `ready_for_review`
- `review`
- `review-required`
- `review readiness`
- `queue-handoff review`
- `reviewer note`
- `explicit approval`
- `supervised review`

Avoid in new artifacts:

- `ready_for_human_review`
- `human-review readiness`
- `human queue-handoff review`
- `human approval`

## Rationale

ZTH remains supervised and non-automated.

The authority model already blocks unattended execution, queue insertion, repo
mutation, training capture, promotion, deployment, and downstream use. Status
strings should describe the review state, not the reviewer type.

Review may involve a person, a policy gate, a deterministic checker, or a
future supervised review artifact, but none of those imply execution
authority.

## Current Legacy Usage

`ready_for_review` is the current preferred status label in the front-door
chain scorecard, review wrapper, fixtures, and tests. `ready_for_human_review`
was the prior legacy label and remains part of the historical record until all
older evidence is separately migrated or retired. This document does not claim
the historical label was retroactively changed.

## Future Migration Plan

A bounded migration could have moved ZTH from `ready_for_human_review` to
`ready_for_review` in a separate commit sequence:

1. Update scorecard output.
2. Update review wrapper output expectations.
3. Update tests.
4. Update fixture expected strings.
5. Update reports and docs.
6. Preserve a backward-compatibility note if needed.
7. Run the full front-door pass/blocked fixture suites.
8. Commit the migration separately.

## Authority Boundary

Terminology cleanup does not authorize routing, queue insertion, repo
mutation, fixture import, training capture, promotion, deployment, or
downstream use.
