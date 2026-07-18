# Queue Approval Review Command Calibration Synthesis

## Purpose

Record the calibration state after adding the read-only queue approval review
command, its direct tests, and the smoke output evidence.

## Calibration Stack

- Validator: `local_harness/validate_queue_approval_path.py`
- Review command: `local_harness/review_queue_approval_path.py`
- Direct tests: `tests/test_review_queue_approval_path.py`
- Source fixture pack: `local_harness/fixtures/queue_approval_path/`
- Command report: `docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_2026-07-18.md`

## What `queue_approval_path_review_v1` Proves

- Approved queue approval artifacts can become
  `ready_for_manual_queue_insertion_review` review artifacts.
- Rejected artifacts remain `rejected_before_queue_insertion`.
- Repair-needed artifacts remain `needs_repair_before_queue_insertion_review`.
- Invalid artifacts become `blocked_needs_repair`.
- Validator `diagnostic_codes` and `diagnostics` are preserved in blocked
  review output.
- Stdout and the written review artifact match.

## Output Path Safety

The command refuses output paths that:

- are under `queue/` or `queues/`
- are under `.work/queues/`
- are under `local_harness/fixtures/`
- match the input path
- point to a directory

It only writes the explicit review output requested by the operator.

## Exit Status Behavior

- Approved manual-candidate review returns zero.
- Rejected, needs-repair, blocked, and unsafe-output-path cases return
  nonzero.
- Failed validation still writes blocked review output when the output path is
  safe.

## Non-Authoritative Statuses

- `not_automated`
- `not_inserted`
- `not_implemented`
- `not_run`
- `explicit_review_output_only`
- `not_imported`
- `not_captured`
- `not_promoted`
- `not_deployed`
- `prohibited_until_review`

## What Remains Unimplemented

- queue insertion
- queue writing
- queue running
- queue runner
- queue processor
- automatic queue handoff
- router automation
- unattended execution
- repo mutation beyond explicit review output
- fixture import
- training capture
- prompt patch promotion
- deployment
- downstream-use authority

## Recommended Next Work

- Stop adding one-off stale guards after this path.
- Replace nested long-duration recommender branches with a declarative
  milestone map.
- Have the milestone map list the target title, category, required evidence
  files, prompt, and next target.
- Preserve the existing no-queue-writing boundary.

## Authority Boundary

This synthesis is evidence-only and review-only. It does not authorize queue
insertion, queue writing, queue running, automatic handoff, router
automation, repo mutation beyond explicit review output, fixture import,
training capture, promotion, deployment, or downstream use.
