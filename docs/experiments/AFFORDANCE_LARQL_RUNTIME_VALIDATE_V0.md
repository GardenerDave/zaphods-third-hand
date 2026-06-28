# AFFORDANCE_LARQL_RUNTIME_VALIDATE_V0

This is a model-free validator for a runtime-install consultation artifact.

It confirms the runtime rule remains consultation-only and internally
consistent. It does not call a model, write durable memory, train LoRA, mutate
weights, or promote the candidate.

Inputs:

- `runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json`
- `larql_runtime_install_report.json`

Outputs:

- `larql_runtime_install_validation_report.json`
- `larql_runtime_install_validation_report.md`

Sample command:

```bash
python3 local_harness/affordance_larql_runtime_validate.py \
  --runtime-rule .work/affordance_larql_runtime_installs/navigator_cuda_larql_rule_v0/runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json \
  --install-report .work/affordance_larql_runtime_installs/navigator_cuda_larql_rule_v0/larql_runtime_install_report.json \
  --out .work/affordance_larql_runtime_validations/navigator_cuda_larql_rule_v0
```

Boundary:

The validator only records whether the consultation-only runtime rule is
internally consistent. It does not authorize durable memory writes, candidate
promotion, LoRA training, model mutation, or model calls.
