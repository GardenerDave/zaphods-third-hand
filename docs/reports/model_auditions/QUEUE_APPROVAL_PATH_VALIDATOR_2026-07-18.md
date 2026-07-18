# Queue Approval Path Validator

## Purpose

This report records the addition of the review-only validator scaffold for
`queue_approval_path_v1`.

## What Was Added

- Validator: `local_harness/validate_queue_approval_path.py`
- Spec: `docs/QUEUE_APPROVAL_PATH.md`
- Fixture pack: `local_harness/fixtures/queue_approval_path/`
- Tests: `tests/test_validate_queue_approval_path.py`
- Fixture tests: `tests/test_queue_approval_path_fixtures.py`

## Schema

The validator accepts review artifacts shaped like `queue_approval_path_v1`
and emits validation results shaped like
`queue_approval_path_validation_v1`.

## Allowed Statuses

- `approved_for_manual_queue_insertion_candidate`
- `rejected_before_queue_insertion`
- `needs_repair_before_queue_insertion_review`

## Required Non-Authoritative Lifecycle Statuses

- `automation_status: not_automated`
- `queue_insertion_status: not_inserted`
- `queue_writing_status: not_implemented`
- `repo_mutation_status: not_authorized`
- `downstream_use_status: prohibited_until_review`

## Tests and Fixtures

The tracked fixture pack covers:

- approved candidate review evidence
- rejected review evidence with diagnostics
- repair-needed review evidence with diagnostics
- unsafe queue-writing language
- unsafe queue-running language
- missing authority boundary terms
- bad lifecycle status
- approved candidate with diagnostics
- rejected without diagnostics
- repair-needed without diagnostics
- wrong schema
- unapproved source review status

The validator tests cover malformed JSON, non-object JSON, missing fields, bad
schemas, wrong lifecycle status, missing authority terms, unsafe queue
language, and the safe phrase allowlist.

## Validation Commands

- `python3 -m pytest tests/test_validate_queue_approval_path.py`
- `python3 -m pytest tests/test_validate_queue_approval_path.py tests/test_queue_approval_path_fixtures.py`
- `python3 local_harness/validate_queue_approval_path.py local_harness/fixtures/queue_approval_path/approved_manual_candidate_valid_001.json`

## What Remains Unimplemented

- queue insertion
- queue writing
- queue running
- router automation
- automatic queue handoff
- unattended execution
- repo mutation
- fixture import
- training capture
- promotion
- deployment
- downstream-use authority

## Authority Boundary

This scaffold is evidence-only and review-only. It does not authorize routing,
queue insertion, queue writing, queue running, repo mutation, fixture import,
training capture, promotion, deployment, or downstream use.
