# AFFORDANCE_LARQL_RUNTIME_CONSULTATION_PROBE_V0

This is a model-free consultation probe for a validated runtime rule.

It checks whether the runtime rule should consult a CUDA/NVIDIA-style user
input on a no_cuda host. It does not call a model, write durable memory, train
LoRA, mutate weights, or promote the candidate.

Inputs:

- `runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json`
- `larql_runtime_install_validation_report.json`
- active host id
- host constraint
- user input text

Outputs:

- `larql_runtime_consultation_probe.json`
- `larql_runtime_consultation_probe.md`

Sample command:

```bash
python3 local_harness/affordance_larql_runtime_consultation_probe.py \
  --runtime-rule .work/affordance_larql_runtime_installs/navigator_cuda_larql_rule_v0/runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json \
  --validation .work/affordance_larql_runtime_validations/navigator_cuda_larql_rule_v0/larql_runtime_install_validation_report.json \
  --active-host navigator_desktop \
  --host-constraint no_cuda \
  --input "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?" \
  --out .work/affordance_larql_runtime_consultation_probes/navigator_cuda_larql_rule_v0
```

Boundary:

The probe only records whether the runtime rule should be consulted for a
CUDA/NVIDIA troubleshooting input. It does not authorize durable memory,
candidate promotion, LoRA training, model mutation, or model calls.
