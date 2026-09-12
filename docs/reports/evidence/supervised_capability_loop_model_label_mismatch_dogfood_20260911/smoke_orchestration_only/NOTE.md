# Run 1 — smoke_orchestration_only (earlier, spoon-fed)

## Classification

**Orchestration / instruction-following smoke. NOT genuine worker reasoning.
Must not be used as capability evidence.**

This run's worker prompt handed the model both the conclusion and the exact
expected output. From `attempt-1.prompt.txt` (verbatim excerpts):

> The declared model (Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf) does NOT match
> what port 8080 actually serves (Qwen3.8-27B-UD-IQ4_XS.gguf). Therefore a
> mismatch is detected.
>
> Output EXACTLY this JSON object and nothing else (no markdown, no code
> fences, no prose, no extra or missing keys, values verbatim):
> {
>   "declared_model": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
>   "declared_base_url": "http://192.168.137.3:8080/v1",
>   "actual_model_8080": "Qwen3.8-27B-UD-IQ4_XS.gguf",
>   "actual_model_8081": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
>   "mismatch_detected": true
> }

Because the target object was printed inside the prompt, the first-attempt
pass proves only that the 1.7B worker can follow instructions and reproduce a
given JSON shape through the ZTH orchestration path — not that it can
interpret raw evidence to reach the verdict itself.

## Why retained

This run exposed the **evaluation-design error** in the original dogfood: the
"expected output" was not merely withheld from the model, it was literally
presented in the prompt. It is preserved as the concrete, auditable
demonstration of that error so the corrected design (see
`../genuine_raw_evidence/`) is auditable in contrast.

## Provenance (from `attempt-1.metadata.json`)

- task_id: `config-env-model-label-mismatch-dogfood-20260911`
- worker model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- temperature `0.2`, max_tokens `768`, finish_reason `stop`
- prompt_length `1423`
- raw_response_sha256 `d7a1438c8d83151091ce0c2c2cc2e6215d5a0d10b2ca057a5c17b085d83affab`
- prompt_sha256 `3a29e2ea045a03f634b507acddac64a0549ce147d6b97ca29785a353ebe28c54`
- request_body_sha256 `295645ef24c42faa0ad5177f4144dd8ea65edba2a51f111a32bc7383f17ec990`
- validation_status `passed` (`json_parse`, `reference_output_exact_match`);
  acceptance_status `not_reviewed`, review_required `true`
- disposition `ready_for_review`; first_attempt_pass `true`;
  external_escalation_count `0`; teacher_pass_count `0`; model_attempt_count `1`

Source run folder (git-ignored, disposable):
`.work/dogfood/config_env_model_label_mismatch_20260911`
