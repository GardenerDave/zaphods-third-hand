# Bounded Task Review Packet Fixtures

This fixture pack preserves the validated bounded-task-review handoff shape as deterministic, model-free evidence.

Covered cases:

- `valid_review_packet_001` — a bounded task review packet that records the validated bounded task draft as reviewed evidence.
- `invalid_review_packet_queue_inserted` — review packet with queue handoff already inserted, which must fail closed.
- `invalid_review_packet_repo_mutation_authorized` — review packet with repo mutation authorized, which must fail closed.
- `invalid_review_packet_unsafe_next_step` — review packet with unsafe lifecycle language in `recommended_next_step`, which must fail closed.

Run the validator directly:

```bash
python3 local_harness/validate_bounded_task_review_packet.py --packet local_harness/fixtures/bounded_task_review_packet/valid_review_packet_001.json
```

Passing these fixtures does not authorize queue insertion, repo mutation, fixture import, training capture, promotion, deployment, or downstream use.
