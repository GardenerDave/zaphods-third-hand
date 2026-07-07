# Supervised Training Pattern Candidates

Supervised training patterns in ZTH are explicit operator-exported candidates.

They preserve:

- failure output evidence
- failure validation diagnostics
- correction/retry prompt evidence
- successful output evidence
- successful validation evidence

These artifacts are evidence-only records.

They are not automatically training data.
They are not automatically curriculum.
They are not adapter material by default.

Any future use in SFT, LoRA, or other training workflows requires separate explicit review and authorization.

They can also be reused as:

- prompt-patch regression fixtures
- validator regression fixtures
- supervised workflow learning evidence

## Export command

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

## Safety boundaries

Export is explicit opt-in only.

Export does not:

- call models
- call endpoints
- execute model output
- modify files from model output
- apply patches
- promote patches
- train adapters or models
- auto-capture curriculum

Export writes one candidate JSON artifact only.
