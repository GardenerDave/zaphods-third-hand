# Queue Approval Path Calibration Synthesis

## Purpose

Record the calibration state after adding the queue approval path validator,
tracked pass fixtures, blocked fixtures, and regression tests.

## Calibration Stack

- Spec: `docs/QUEUE_APPROVAL_PATH.md`
- Validator: `local_harness/validate_queue_approval_path.py`
- Direct validator tests: `tests/test_validate_queue_approval_path.py`
- Fixture pack: `local_harness/fixtures/queue_approval_path/`
- Fixture tests: `tests/test_queue_approval_path_fixtures.py`
- CLI validation: `python3 local_harness/validate_queue_approval_path.py <fixture>`

## Passing Fixture Coverage

- `approved_manual_candidate_valid_001`
- `rejected_before_insertion_valid_001`
- `needs_repair_before_insertion_valid_001`

These cases prove the validator can represent approved/manual candidate,
rejected, and repair-needed review evidence without queue writing.

## Blocked Fixture Coverage

- `unsafe_queue_written_language_001`
- `unsafe_queue_running_language_001`
- `missing_authority_term_001`
- `bad_lifecycle_status_001`
- `approved_candidate_with_diagnostics_001`
- `rejected_without_diagnostics_001`
- `needs_repair_without_diagnostics_001`
- `wrong_schema_001`
- `unapproved_source_status_001`

These cases prove the validator fails closed on unsafe queue-writing or
queue-running language, missing authority terms, bad lifecycle status,
unexpected diagnostics, missing diagnostics, wrong schema, and incorrect
source review status.

## What This Proves

- `queue_approval_path_v1` can be validated deterministically.
- Approved/manual candidate, rejected, and repair-needed states can be
  represented as review evidence.
- An approval candidate remains non-inserting.
- Unsafe queue-writing and queue-running language fails closed.
- Missing authority terms fail closed.
- Bad lifecycle statuses fail closed.
- Source queue-handoff status is enforced for approval.
- Safe phrases such as `not_inserted` and `not_implemented` do not trigger
  false positives.

## What Remains Unimplemented

- queue insertion
- queue writing
- queue running
- queue runner
- queue processor
- router automation
- automatic queue handoff
- unattended execution
- repo mutation
- fixture import
- training capture
- prompt patch promotion
- deployment
- downstream-use authority

## Recommended Next Work

- Stop expanding approval-path structure unless review pain appears.
- Keep the queue writer unimplemented for now.
- Consider a queue approval review command only if it stays read-only and
  combines validation/reporting without insertion.
- Before any queue-writing implementation exists, require another explicit
  design/review step.

## Authority Boundary

This synthesis is evidence-only and review-only. It does not authorize queue
insertion, queue writing, queue running, automatic handoff, router automation,
repo mutation, fixture import, training capture, promotion, deployment, or
downstream use.
