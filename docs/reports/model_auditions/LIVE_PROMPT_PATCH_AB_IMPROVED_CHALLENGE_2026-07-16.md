# Live Prompt Patch A/B Improved Challenge Closeout

This report records a supervised live prompt patch A/B challenge where the combined patch stack improved behavior.

- Run directory: `.work/prompt_patch_ab_live/20260716_211808`
- `case_id`: `scope_boundary_live_smoke_005`
- Model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- `prompt_patch_id`: `scope_boundary_v1+output_contract_v1`
- `generated_case_status`: `harness_valid`
- Harness result: `improved`
- Baseline status: `failed`
- Patched status: `passed`
- Baseline failure: `missing required held target: training/`
- Review bundle produced: `.work/prompt_patch_ab_live/20260716_211808/prompt_patch_ab_review_bundle.json`

Interpretation:

- `scope_boundary_v1` alone was insufficient in the earlier unchanged-fail style result because the model explained the boundary but did not populate `held_targets`.
- `scope_boundary_v1+output_contract_v1` fixed both the scope decision and the structured output materialization.

This is evidence only.
It is not prompt-patch promotion.
It does not authorize downstream use.
It does not train or capture data for training.
It proves one supervised live challenge where the combined patch stack improved behavior.

## Rerunnable Inspection Commands

```bash
python3 -m json.tool .work/prompt_patch_ab_live/20260716_211808/evidence/prompt_patch_ab_live_record.json
python3 -m json.tool .work/prompt_patch_ab_live/20260716_211808/harness_result.json
python3 -m json.tool .work/prompt_patch_ab_live/20260716_211808/prompt_patch_ab_review_bundle.json
```

The raw evidence remains local under `.work/` and is not committed.
