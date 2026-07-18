# Queue Approval Path Fixtures

These fixtures exercise `queue_approval_path_v1` validation.

They sit after `queue_handoff_review_v1` as review-artifact evidence only.
They do not insert queues, write queues, run queues, automate handoff, mutate
repositories, train, promote, deploy, or grant downstream-use authority.

## Case List

- `approved_manual_candidate_valid_001`
- `rejected_before_insertion_valid_001`
- `needs_repair_before_insertion_valid_001`
- `unsafe_queue_written_language_001`
- `unsafe_queue_running_language_001`
- `missing_authority_term_001`
- `bad_lifecycle_status_001`
- `approved_candidate_with_diagnostics_001`
- `rejected_without_diagnostics_001`
- `needs_repair_without_diagnostics_001`
- `wrong_schema_001`
- `unapproved_source_status_001`

## Command Example

```bash
python3 local_harness/validate_queue_approval_path.py \
  local_harness/fixtures/queue_approval_path/approved_manual_candidate_valid_001.json
```

## Authority Boundary

These fixtures are evidence only. They do not authorize queue insertion,
queue writing, queue running, automatic queue handoff, routing, execution,
repo mutation, fixture import, training capture, promotion, deployment, or
downstream use.
