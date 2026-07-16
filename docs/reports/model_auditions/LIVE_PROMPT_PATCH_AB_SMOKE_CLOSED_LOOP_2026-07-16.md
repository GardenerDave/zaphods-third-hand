# Live Prompt Patch A/B Smoke Closeout

This report records the first successful supervised live prompt patch A/B smoke trial.

- Run directory: `.work/prompt_patch_ab_live/20260716_210930`
- `case_id`: `scope_boundary_live_smoke_003`
- Model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- `generated_case_status`: `harness_valid`
- Harness result: `unchanged_pass`
- Baseline status: `passed`
- Patched status: `passed`
- Review bundle produced: `.work/prompt_patch_ab_live/20260716_210930/prompt_patch_ab_review_bundle.json`

This is not prompt-patch promotion.
It does not authorize downstream use.
It does not prove patch improvement because the baseline prompt also passed.
It does prove that the live A/B evidence loop can complete end to end under supervision.

## Rerunnable Inspection Commands

```bash
python3 -m json.tool .work/prompt_patch_ab_live/20260716_210930/evidence/prompt_patch_ab_live_record.json
python3 -m json.tool .work/prompt_patch_ab_live/20260716_210930/harness_result.json
python3 -m json.tool .work/prompt_patch_ab_live/20260716_210930/prompt_patch_ab_review_bundle.json
```

The raw evidence remains local under `.work/` and is not committed.
