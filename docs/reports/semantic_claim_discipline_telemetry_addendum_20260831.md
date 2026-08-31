# Semantic Claim Discipline Telemetry Addendum

Date: 2026-08-31

This addendum records the follow-up reproduction after closing the local model-call observability gap.

## What changed

The local-call success artifact now preserves endpoint completion telemetry when the local OpenAI-compatible response includes it:

- `finish_reason`
- `usage.prompt_tokens`
- `usage.completion_tokens`
- `usage.total_tokens`
- response envelope identity fields when present
- response body SHA-256

This is recorded in `local_harness/run_manual_supervised_attempt.py` and covered by canonical regression tests in `tests/test_run_manual_supervised_attempt.py`.

## Telemetry gap

Before this fix, ZTH preserved the raw worker artifact but not enough completion telemetry to distinguish truncation from malformed generation.

After the fix, the preserved success artifact includes the endpoint response summary.

## Clean Task A reproduction

Run directory:

- `.work/semantic_claim_discipline_recheck_20260831/20260831T150200Z_baseline`
- `.work/semantic_claim_discipline_recheck_20260831/20260831T150200Z_patched`

Controls:

- same two evidence sources
- identical projected evidence excerpts between arms
- same worker: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- same endpoint: `http://192.168.1.16:8080/v1`
- same observation schema
- same total prompt budget: `4096`
- same response reserve: `900`
- same completion limit: `900`

Evidence hashes:

- `[docs/reports/1p7b_to_30b_structured_continuous_v2_20260830.md](/home/navigator/agent-workspace/zaphods-third-hand/docs/reports/1p7b_to_30b_structured_continuous_v2_20260830.md)` SHA-256 `9b8d8943dd387a140ce980a50a01affb18d21af590a57b77c3cf9dadf8bc4807`
- `[docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/transaction_manifest.json](/home/navigator/agent-workspace/zaphods-third-hand/docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/transaction_manifest.json)` SHA-256 `753be2d27cd671492f6d6337f8abb28efe60f99fea27617e6169ec5a42fa1467`

Prompt hashes:

- Baseline prompt SHA-256 `a4cd8ac069c81bc4c8f862e9ee121b3f2b5fa4e0100838f1fb106d6080c27d6e`
- Patched prompt SHA-256 `ae6bd68d31faf6c4f7f5dffb2a504fa560c72ea6486908dfd4d0127672a90e06`

Request hashes:

- Baseline request SHA-256 `c5d1ae6eadd1b726fb61c73fe6bc7753b17f223e9f1536a258a769a4609be013`
- Patched request SHA-256 `3f009e5ef1c4d5a176e62768e019a247d05b2e42552bffd19d0df834b98f5d16`

## Baseline A0

Transport and telemetry:

- `finish_reason`: `stop`
- `prompt_tokens`: `3943`
- `completion_tokens`: `675`
- `total_tokens`: `4618`

Validation:

- parse_json: passed
- observation_schema: passed
- observation_grounding: passed

Semantic result:

- main claim: `Transport qualification proves model capability.`
- classification: `mixed`
- notes: the response still included the boundary claim that transport qualification only establishes semantic evaluation can occur, but it also retained the overclaim.

## Patched A1

Transport and telemetry:

- `finish_reason`: `stop`
- `prompt_tokens`: `4106`
- `completion_tokens`: `464`
- `total_tokens`: `4570`

Validation:

- parse_json: passed
- observation_schema: passed
- observation_grounding: passed

Semantic result:

- main claim: `Transport qualification proves model capability.`
- classification: `overclaim`
- notes: the patch did not produce a clean boundary correction in the final structured output, although the raw text remained more cautious than the baseline.

## Conclusion

The observability gap is closed.

The clean reproduction does not support declaring `unsupported_certainty_v1` a reliable fix for the transport-qualification overclaim.

It also does not support blaming completion truncation:

- both runs finished with `finish_reason: stop`
- both runs completed below the configured max token limit
- both runs produced valid JSON and passed the canonical observation validator

The remaining issue is semantic, not transport truncation.
