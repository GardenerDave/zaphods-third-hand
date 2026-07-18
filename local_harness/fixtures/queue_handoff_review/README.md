# Queue Handoff Review Fixtures

These fixtures exercise `queue_handoff_review_v1` validation.

They do not represent queue insertion.
They do not authorize queue writing, routing, execution, repo mutation,
fixture import, training capture, promotion, deployment, or downstream use.

## Case List

- `approved_candidate_valid_001`
- `rejected_valid_001`
- `needs_repair_valid_001`
- `unsafe_queue_writing_language_001`
- `missing_authority_term_001`
- `bad_lifecycle_status_001`
- `approved_candidate_with_diagnostics_001`
- `rejected_without_diagnostics_001`
- `needs_repair_without_diagnostics_001`
- `wrong_schema_001`

## Command Example

```bash
python3 local_harness/validate_queue_handoff_review.py \
  local_harness/fixtures/queue_handoff_review/approved_candidate_valid_001.json
```

## Authority Boundary

These fixtures are evidence only. They do not authorize queue insertion,
queue writing, routing, execution, repo mutation, fixture import, training
capture, promotion, deployment, or downstream use.
