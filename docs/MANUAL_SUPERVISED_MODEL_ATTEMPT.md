# Manual Supervised Model Attempt Runner

This runner is the first practical operator loop for real model use under supervision.

It is supervised with explicit authority boundaries:

- model calls are manual by default and endpoint calls occur only in explicit `call-local` mode
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
- `session`
- `call-local`
- `export-pattern`
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

### Simpler session mode

Session mode prepares the run and prints exactly what to do next.

Example:

```bash
python3 local_harness/run_manual_supervised_attempt.py session \
  --messy-input "The LoRA and prompt injection work got messy. Build a bounded design packet." \
  --out-dir .work/manual_supervised_attempts
```

Session writes:

- `messy_input.txt`
- `model_prompt_packet.md`
- `prompt_to_paste.md`
- `raw_model_output.txt`
- `operator_instructions.txt`
- `run_manifest.json`
- `output_contract.json`

Workflow:

- open or copy `prompt_to_paste.md`
- paste it into your model manually
- save the exact model response to `raw_model_output.txt`
- run the printed ingest command

Optional prompt print mode:

```bash
python3 local_harness/run_manual_supervised_attempt.py session \
  --messy-input "The LoRA and prompt injection work got messy. Build a bounded design packet." \
  --out-dir .work/manual_supervised_attempts \
  --print-prompt
```

The runner still does not call models and does not execute model output.

### Local endpoint call mode

`call-local` is explicit opt-in local model calling for OpenAI-compatible local servers.
It calls only the endpoint supplied by the operator and writes raw model output for ingest.

Example:

```bash
python3 local_harness/run_manual_supervised_attempt.py call-local \
  --run-dir .work/manual_supervised_attempts/<timestamp> \
  --endpoint http://<local-endpoint>/v1 \
  --model qwen3-1.7b-gpu-40k
```

Behavior:

- reads `prompt_to_paste.md`
- posts to `<endpoint>/chat/completions` with a single user message containing the exact prompt packet
- defaults to `temperature=0` and `max_tokens=1024`
- writes assistant content exactly to `raw_model_output.txt`
- writes call metadata to `local_model_call.json`
- prints the next ingest command

Optional flags:

- `--temperature`
- `--max-tokens`
- `--timeout-seconds`
- `--overwrite` to replace a non-empty `raw_model_output.txt`

This mode does not validate acceptance by itself. The operator must still run ingest.
Review is still required. No execution, file mutation, patch application, promotion, training, or curriculum capture occurs.
Timeout failures are preserved as failed-call evidence and do not authorize acceptance, promotion, training, model materialization, or automatic failure-to-curriculum capture.

### Supervised retry helper

When validation fails, use `retry-contract` to snapshot the failed attempt before any overwrite:

```bash
python3 local_harness/run_manual_supervised_attempt.py retry-contract \
  --run-dir .work/manual_supervised_attempts/<run> \
  --retry-id 1
```

Then run the next manual local retry:

```bash
python3 local_harness/run_manual_supervised_attempt.py call-local \
  --run-dir .work/manual_supervised_attempts/<run> \
  --endpoint http://<local-endpoint>/v1 \
  --model qwen3-1.7b-gpu-40k \
  --max-tokens 4096 \
  --overwrite
```

The retry helper prepares a stronger supervised retry prompt and snapshots failure evidence. It includes a JSON skeleton derived from the output contract, the previous failed output, and validator diagnostics. The skeleton is a payload shape only and is not permission to fabricate evidence.
It still does not call a model, accept output, promote output, train, materialize adapters, or perform automatic failure-to-curriculum capture.

### Export training pattern candidate mode

`export-pattern` is explicit opt-in evidence export from a supervised failure->correction->success run.
It does not train anything and does not auto-capture curriculum.

Example:

```bash
python3 local_harness/run_manual_supervised_attempt.py export-pattern \
  --run-dir .work/manual_supervised_attempts/<timestamp> \
  --failure-raw raw_model_output.failed_001.txt \
  --failure-validation output_validation.failed_001.json \
  --retry-prompt retry_prompt_to_paste_001.md \
  --success-raw raw_model_output.success_001.txt \
  --success-validation output_validation.success_001.json \
  --out-dir examples/supervised_training_patterns \
  --pattern-id zth_contract_missing_fields_retry_001
```

`export-pattern` writes one candidate JSON artifact and preserves failed/success raw outputs, correction prompt, and validation evidence exactly.
It is marked as a candidate only (`not_training_data_until_reviewed: true`, `not_automatic_curriculum_capture: true`).

### Mini-batch runner

`run_manual_supervised_attempt_batch.py` orchestrates existing `session -> call-local -> ingest` commands for a bounded task list and writes batch ledger and summary artifacts.
It does not accept outputs automatically, export patterns automatically, execute or apply model output, train, promote, materialize adapters, or add automatic failure-to-curriculum capture.

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
Validation checks required field presence and basic required field types, including that `required_fields_present` is boolean `true`.
Validation also rejects duplicate JSON keys because they create provenance and contract ambiguity.
When structured run artifacts provide authorized targets, validation can also reject `allowed_targets` values that exceed that authority.

Attempt provenance is recorded as manual operator-provided model output using:

```text
manual_operator_pasted_model_output
```

This is not synthetic fixture output.
Validation remains evidence, not acceptance, and does not authorize promotion, training, model materialization, or automatic failure-to-curriculum capture.
Target authority checks are evidence, not acceptance, and do not authorize file edits, promotion, training, model materialization, or automatic failure-to-curriculum capture.
