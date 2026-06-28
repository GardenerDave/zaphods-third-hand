# AFFORDANCE_LARQL_RUNTIME_INSTALL_V0

This is a model-free runtime install step for a validated and reviewed LARQL
rule artifact.

It writes a runtime-consultation rule artifact and an install report. It does
not write durable memory, train LoRA, mutate weights, or promote the
candidate.

Inputs:

- `larql_runtime_install_packet.json`
- `larql_runtime_install_review.json`

Outputs:

- `runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json`
- `larql_runtime_install_report.json`
- `larql_runtime_install_report.md`

Sample command:

```bash
python3 local_harness/affordance_larql_runtime_install.py \
  --packet .work/affordance_larql_runtime_install_packets/navigator_cuda_larql_rule_v0/larql_runtime_install_packet.json \
  --review .work/affordance_larql_runtime_install_reviews/navigator_cuda_larql_rule_v0/larql_runtime_install_review.json \
  --out .work/affordance_larql_runtime_installs/navigator_cuda_larql_rule_v0
```

Boundary:

The runtime rule is installed for consultation only. It is not written to
durable memory, and the candidate is not promoted.
