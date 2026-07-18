# Triaged To Bounded Task Bridge Fixtures

This fixture pack preserves the validated messy-input-triage to bounded-task
bridge shape as deterministic, model-free evidence.

Covered cases:

- `valid_bridge_001` — a validated messy-input triage packet and matching
  bounded task packet draft.
- `invalid_source_missing_review_required` — source triage packet missing the
  required `review_required` field.
- `invalid_bounded_task_queue_inserted` — bounded task draft with queue handoff
  already inserted, which must fail closed.
- `invalid_bounded_task_unsafe_action` — bounded task draft with unsafe
  lifecycle language in `proposed_action`, which must fail closed.

Run the validators directly:

```bash
python3 local_harness/validate_messy_input_triage_packet.py --packet local_harness/fixtures/triage_to_bounded_task_bridge/valid_bridge_001.source_triage_packet.json
python3 local_harness/validate_bounded_task_packet_draft.py --packet local_harness/fixtures/triage_to_bounded_task_bridge/valid_bridge_001.bounded_task_packet_draft.json
```

Passing these fixtures does not authorize router automation, automatic queue
handoff, fixture import, training capture, promotion, deployment, or
downstream use.
