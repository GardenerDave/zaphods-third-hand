# AFFORDANCE_LARQL_ABSENCE_OF_EVIDENCE_FILE_AUTHORITY_V0

This is a model-free scaffold for the failure class where absence of evidence
is mistakenly treated as authority to assert absence, delete, promote,
canonicalize, overwrite, or clean up.

The core rule idea is:

`absence_of_evidence_is_not_evidence_of_absence`

Absence from search is not proof of absence.

This scaffold is intentionally narrow. It holds lifecycle authority until
targeted inspection or review evidence exists.

## Purpose

- preserve evidence boundaries;
- prevent absence claims from incomplete search or file-limited evidence;
- recommend targeted inspection before irreversible state changes; and
- keep promotion and cleanup held pending review evidence.

## What it is not

- not a model call;
- not training data;
- not a dataset artifact;
- not a runtime-rule modification;
- not a promotion decision; and
- not authorization to delete, canonicalize, or overwrite based on missing
  search results alone.

## Rule sketch

The initial rule draft should state that when evidence is incomplete, stale,
file-limited, search-limited, or otherwise bounded:

- do not claim a file, rule, test, artifact, path, branch, or record does not
  exist merely because it was not found;
- do not treat missing search results as authority to delete, promote,
  canonicalize, overwrite, or clean up;
- state the evidence boundary explicitly;
- recommend a targeted inspection command or review step; and
- keep lifecycle authority held until review evidence exists.

## Suggested initial pipeline shape

1. collect the failure seed;
2. draft the absence-of-evidence candidate packet;
3. review the packet;
4. keep all promotion and lifecycle authority held until review evidence exists.

## Boundary

- No durable memory unless explicitly approved.
- No automatic failure-to-curriculum capture.
- No LoRA training unless explicitly approved.
- No model weight mutation unless explicitly approved.
- No candidate promotion unless explicitly approved.
- No runtime rule modification unless explicitly approved.

## Suggested CLI

```bash
python3 local_harness/affordance_larql_absence_of_evidence_packet.py \
  --source-failure-id absence_of_evidence_file_authority.real \
  --candidate-id absence_of_evidence_file_authority \
  --rule-id absence_of_evidence_file_authority_v0 \
  --behavior-note "Evidence is bounded. Absence from search is not proof of absence. Use a targeted inspection command or review step. Keep lifecycle authority held until review evidence exists." \
  --out .work/absence_of_evidence_file_authority_v0
```

## Current stop condition

This scaffold stops at a reviewable packet. It does not move into runtime
installation, model probing, curriculum capture, or training-run approval.
