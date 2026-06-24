# Failure Curriculum Loop

The failure curriculum loop turns failed model audition/probe rows into supervised training artifacts.

It is intentionally conservative:

- failed rows become normalized `failure_event` records
- failures are classified by deterministic rules
- classified failures become curriculum candidates
- candidates must be reviewed before training
- only `accepted` rows may enter train/validation datasets
- `holdout_locked` rows are reserved for evaluation and must not be trained on

## Data flow

```text
raw probe rows
  -> failure_events.jsonl
  -> classified_failure_events.jsonl
  -> candidates.jsonl
  -> review split
  -> train / validation / holdout
  -> SFT chat-message exports

## Explicit review flow

Generated candidates are not training data until a reviewer explicitly promotes them.

A review decision file uses JSONL rows with this shape:

```json
{"candidate_id":"candidate_id_here","review_status":"accepted","reviewer":"dave","review_notes":"Gold answer checked."}
