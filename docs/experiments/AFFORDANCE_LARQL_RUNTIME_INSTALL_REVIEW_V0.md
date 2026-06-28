# AFFORDANCE_LARQL_RUNTIME_INSTALL_REVIEW_V0

This is a model-free review recorder for a runtime-install packet.

It is review only.
No runtime rule is installed.
No durable memory is written.
No candidate promotion is granted.
No LoRA training is authorized.

Inputs:

- `larql_runtime_install_packet.json`

Outputs:

- `larql_runtime_install_review.json`
- `larql_runtime_install_review.md`

Approval only authorizes a later install step. It does not install the rule.

Sample command:

```bash
python3 local_harness/affordance_larql_runtime_install_review.py \
  --packet .work/affordance_larql_runtime_install_packets/navigator_cuda_larql_rule_v0/larql_runtime_install_packet.json \
  --decision approve_runtime_install \
  --operator-summary "Approve runtime installation for consultation only. The rule is scoped to navigator_desktop or matching host evidence/profile constraints, blocks CUDA/NVIDIA troubleshooting on RX580/no_cuda, recommends LM Studio endpoint only under matching evidence, and requires reverify for unknown/split/stale/digest mismatch conditions. Do not authorize durable memory, candidate promotion, LoRA, or model mutation." \
  --out .work/affordance_larql_runtime_install_reviews/navigator_cuda_larql_rule_v0
```

Boundary:

This review only records whether later runtime installation should be
authorized. It does not install the rule, write durable memory, train LoRA, or
promote the candidate.
