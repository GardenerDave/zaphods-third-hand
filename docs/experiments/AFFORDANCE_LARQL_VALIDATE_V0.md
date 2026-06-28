# AFFORDANCE_LARQL_VALIDATE_V0

This is a model-free validator for an applied bounded LARQL rule artifact.

It verifies that the rule artifact and application report remain bounded and
consistent. It does not install the rule into runtime memory, does not write
durable memory, does not train LoRA, and does not promote the candidate.

Inputs:

- `larql_rule.json`
- `larql_apply_report.json`

Outputs:

- `larql_rule_validation_report.json`
- `larql_rule_validation_report.md`

The validator checks:

- the rule artifact reports itself as an applied bounded artifact
- runtime installation is not installed
- durable memory is not written
- the candidate is not promoted
- the rule blocks/warns on CUDA/NVIDIA troubleshooting
- the rule recommends the LM Studio OpenAI-compatible endpoint path
- the rule requires reverify for unknown, split, stale, or digest mismatch conditions

Sample command:

```bash
python3 local_harness/affordance_larql_validate.py \
  --rule .work/affordance_larql_applied_rules/navigator_cuda_larql_rule_v0/larql_rule.json \
  --apply-report .work/affordance_larql_applied_rules/navigator_cuda_larql_rule_v0/larql_apply_report.json \
  --out .work/affordance_larql_rule_validations/navigator_cuda_larql_rule_v0
```

Boundary:

This validator only records whether the bounded rule artifact is internally
consistent. It does not authorize runtime installation, durable memory writes,
LoRA training, or candidate promotion.
