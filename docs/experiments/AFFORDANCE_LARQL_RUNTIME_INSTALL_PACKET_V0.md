# AFFORDANCE_LARQL_RUNTIME_INSTALL_PACKET_V0

This is a model-free runtime install packet draft for a validated bounded
LARQL rule artifact.

It is packet only.
The runtime rule is not installed.
Durable memory is not written.
The candidate is not promoted.
LoRA is not trained.

Inputs:

- `larql_rule.json`
- `larql_rule_validation_report.json`

Outputs:

- `larql_runtime_install_packet.json`
- `larql_runtime_install_packet.md`

The packet is a draft for later review of whether runtime installation should
be authorized.

Sample command:

```bash
python3 local_harness/affordance_larql_runtime_install_packet.py \
  --rule .work/affordance_larql_applied_rules/navigator_cuda_larql_rule_v0/larql_rule.json \
  --validation .work/affordance_larql_rule_validations/navigator_cuda_larql_rule_v0/larql_rule_validation_report.json \
  --out .work/affordance_larql_runtime_install_packets/navigator_cuda_larql_rule_v0
```

Boundary:

This packet only drafts a runtime-install step. It does not install the rule,
write durable memory, train LoRA, or promote the candidate.
