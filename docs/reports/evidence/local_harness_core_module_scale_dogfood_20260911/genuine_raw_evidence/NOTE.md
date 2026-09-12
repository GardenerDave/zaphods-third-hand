# Run — genuine_raw_evidence (single run, not passed)

## Classification

**Genuine raw-evidence interpretation by the 1.7B worker.** Read-only
repository-observation dogfood. The worker prompt withholds the conclusion and
the exact expected output. It supplies raw `wc -l` output for the 10 curated
`local_harness/*.py` modules (ascending filename order) and asks the worker to
report `file_count`, the largest file + line count, and the smallest file + line
count. The validator-only reference (`expected_output`) is **not** injected into
the model call.

## What the worker produced (verbatim, identical on all 4 attempts)

```json
{
  "file_count": 10,
  "largest_file": "zth_task.py",
  "largest_lines": 1515,
  "smallest_file": "icm_spec.py",
  "smallest_lines": 230
}
```

True reference (validator-only):
`file_count:10`, `largest_file:run_manual_supervised_attempt.py` / `2269`,
`smallest_file:icm_spec.py` / `230`.

The worker got `file_count` and the **smallest** (`icm_spec.py`/`230`) correct
but **misidentified the largest file**: it reported `zth_task.py`/`1515` — the
8th of the 10 presented rows — instead of the true maximum
`run_manual_supervised_attempt.py`/`2269` — a small-model max-selection
failure: it failed to select the actual maximum.

## Outcome

- First-attempt pass: `first_attempt_pass` `false`
- Deterministic validation: `json_parse` **passed**,
  `reference_output_exact_match` **failed**
- `attempt_count` `4`, `model_attempt_count` `4`, `teacher_pass_count` `2`,
  `external_escalation_count` `1`, `external_teacher_call_count` `1`
- `successful_intervention_source`: `none`
- `pass` `false`; `unresolved` `false`; `disposition`: **`infrastructure_error`**

## Routing path (the loop's own mechanism, no manual pre-escalation)

1. **Worker baseline** (attempts 1–2): exact-match failed both times.
2. **Local teacher** (attempts 3–4): the 27B teacher was consulted twice
   (`teacher_pass_count:2`); **both** passes returned `reasoning_only` (all
   output in the reasoning channel, no completion) → intervention failed to parse
   as JSON (`teacher_parse_status:failed`) → worker retried **unchanged**,
   reproducing the same output.
3. **External teacher** (terminal tier): **unconfigured**
   (`adapter_identity:codex-unconfigured`; `error:"external teacher
   unavailable: ZTH_EXTERNAL_TEACHER_COMMAND is not configured"`) → forced
   terminal `disposition:infrastructure_error`.

## Provenance (from `attempt-1.metadata.json`)

- task_id: `local-harness-core-module-scale-dogfood-20260911`
- worker model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf` (endpoint alias `JARVIS_LOCAL`,
  base_url `http://192.168.137.3:8081/v1`)
- local teacher: `Qwen3.8-27B-UD-IQ4_XS.gguf`
  (base_url `http://192.168.137.3:8080/v1`)
- temperature `0.2`, max_tokens `768`, finish_reason `stop`,
  prompt_length `1459`
- raw_response_sha256 `9fd1b3255eca696eb068ced47301a00992bfcb91e819ecc3c4ccde52fdc86559`
- prompt_sha256 `495144cf0c5184a47adb8da1e81cd3dfdf11fc7cfbec0a9b282657589848d8d2`
- request_body_sha256 `fa355c6f164ea55a6810910f84c06966f84357b070b5678f7f336e2b0096d0ff`
- validation_status `failed` (`json_parse` passed, `reference_output_exact_match`
  failed)

Source run folder (scratch, disposable):
`/tmp/zth_dogfood/local_harness_core_module_scale_dogfood_20260911`
