# Review-to-Candidates Helper Dogfood

Status: completed

## Scope

This report records a small dogfood pass of
`review_to_curriculum_candidates.py`.

The helper was run against a completed sample review containing three known v6
failure rows. The sample was created under `.work/` and was not committed as a
canonical artifact.

## Input Sample

Rows exercised:

- Row 7: placeholder schema substitution
- Row 33: prefixed-key substitution
- Row 36: source-content leakage after correct scalar answer

Each row had completed review fields:

- classification
- likely cause
- keep for next curriculum
- corrected target needed

## Candidate Output Result

The helper produced three draft candidate rows.

Observed result:

- candidate rows: 3
- skipped rows: 0
- warnings: none

The generated rows were marked as draft curriculum candidates, not final training
data.

Required safety metadata was present:

- `candidate_status: draft`
- `requires_human_review: true`
- `not_final_training_data: true`

The assistant target JSON was preserved from the reviewed target blocks:

- `{"count":3}`
- `{"blocked":true}`
- `{"files_changed":2}`

The generated user prompt intentionally retained a TODO requiring operator
replacement before training.

## Fail-Closed Check

A second sample review with `classification: TODO` was passed to the helper.

Observed result:

- the helper exited with an error;
- no output JSONL was written;
- the failure identified the incomplete classification field.

This confirms that incomplete review scaffolds do not silently become curriculum
candidates.

## Interpretation

The helper successfully converts completed review scaffolds into draft
curriculum-candidate JSONL while refusing incomplete review input.

This closes another supervised workflow gap:

review scaffold -> completed review -> draft curriculum candidates

The result does not create final training data and does not authorize training,
adapter promotion, or deployment.

## Boundary

This report is supervised workflow evidence. It does not establish deployment
readiness, autonomous capability, or authority to train or deploy an adapter
without operator review.
