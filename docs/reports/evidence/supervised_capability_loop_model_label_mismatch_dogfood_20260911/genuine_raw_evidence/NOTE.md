# Run 2 — genuine_raw_evidence (corrected, accepted)

## Classification

**Genuine raw-evidence interpretation by the 1.7B worker.**

This is the corrected dogfood run. The worker prompt withholds the conclusion
and the exact expected output. It supplies (a) the declared config/model fact
and (b) the raw `/v1/models` endpoint facts for ports 8080 and 8081, and asks
the worker to decide the match itself. The validator-only reference
(`expected_output`) is **not** injected into the model call.

The worker interpreted the raw facts and produced the verdict itself:

```json
{
  "declared_model": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
  "declared_base_url": "http://192.168.137.3:8080/v1",
  "actual_model_at_endpoint": "Qwen3.8-27B-UD-IQ4_XS.gguf",
  "match": false
}
```

`declared_model` ≠ `actual_model_at_endpoint`, so `match` is correctly `false`.

## Outcome

- First-attempt pass: `first_attempt_pass` `true`
- No escalation: `external_escalation_count` `0`, `teacher_pass_count` `0`,
  `external_teacher_call_count` `0`, `model_attempt_count` `1`
- Deterministic validation **passed** (`json_parse`,
  `reference_output_exact_match`)
- `disposition`: `ready_for_review`; acceptance_status `not_reviewed`,
  review_required `true` (acceptance is a separate, still-pending step)

## Provenance (from `attempt-1.metadata.json`)

- task_id: `config-env-model-label-mismatch-dogfood-raw-20260911`
- worker model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- temperature `0.2`, max_tokens `768`, finish_reason `stop`
- prompt_length `2709`
- raw_response_sha256 `39732c8f73b1709dc083b217f012a4cf430c836ec1aa94ba07ee3baf572494d0`
- prompt_sha256 `054459d304414c1207e4ba86085f95973dcc7dcdc951ac9e4f30a5cb29ff1390`
- request_body_sha256 `98aef9fdb0925f0b935d48b74607322ff31ac247ba38bf91d78ec76ae086b62b`
- validation_status `passed` (`json_parse`, `reference_output_exact_match`);
  acceptance_status `not_reviewed`, review_required `true`

Source run folder (git-ignored, disposable):
`.work/dogfood/config_env_model_label_mismatch_dogfood_raw_20260911`
