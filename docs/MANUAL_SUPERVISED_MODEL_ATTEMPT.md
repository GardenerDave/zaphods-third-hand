# Manual Supervised Model Attempt Runner

This runner is the first practical operator loop for real model use under supervision.

It is manual and model-free from the harness perspective:

- no model calls are made by this runner
- no endpoint calls are made by this runner
- no command execution is performed from model output
- no file modification is performed from model output
- no patch application is performed
- no automatic patch promotion is performed
- no automatic training is performed
- no default failure-to-curriculum capture is performed

## Pipeline position

```text
messy input
  -> model_prompt_packet.md
  -> operator manually pastes packet into model
  -> operator saves raw_model_output.txt
  -> supervised_model_attempt.json
  -> output_validation.json
  -> optional review_decision.json
  -> optional downstream_use_gate.json
  -> optional handoff_packet.json
```

## CLI

Script:

```text
local_harness/run_manual_supervised_attempt.py
```

Modes:

- `prepare`
- `ingest`

### Prepare

Prepare creates a timestamped run directory with:

- `messy_input.txt`
- `model_prompt_packet.md`
- `operator_instructions.txt`
- `run_manifest.json`
- `output_contract.json`

Example:

```bash
python3 local_harness/run_manual_supervised_attempt.py prepare \
  --messy-input "The LoRA and prompt injection work got messy. Build a bounded design packet." \
  --out-dir .work/manual_supervised_attempts
```

### Ingest

Ingest reads operator-provided raw model output and writes:

- `raw_model_output.txt`
- `supervised_model_attempt.json`
- `output_validation.json`
- `output_validation_report.txt`

If explicit review metadata is provided, ingest also writes:

- `review_decision.json`
- `downstream_use_gate.json`
- `handoff_packet.json`

Example:

```bash
python3 local_harness/run_manual_supervised_attempt.py ingest \
  --run-dir .work/manual_supervised_attempts/<timestamp> \
  --raw-output-file .work/manual_supervised_attempts/<timestamp>/raw_model_output.txt \
  --decision accepted \
  --decision-reason "Output satisfies the contract and remains within scope." \
  --operator manual
```

Without explicit review metadata, ingest stops after validation and reports that review is required before downstream use.

## Contract source and provenance

Ingest validates against the exact `output_contract.json` created during prepare.

Attempt provenance is recorded as manual operator-provided model output using:

```text
manual_operator_pasted_model_output
```

This is not synthetic fixture output.
