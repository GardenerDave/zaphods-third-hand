# AFFORDANCE_LARQL_APPLY_V0

This is a model-free, bounded apply step for a reviewed LARQL dry-run packet.
It is the first step allowed to write a LARQL rule artifact.

It is not an applied rule in durable memory.
It is not LoRA training.
It is not model mutation.
It is not candidate promotion.
It does not modify runtime behavior.

The apply tool consumes:

- a validated LARQL apply packet
- an approved LARQL apply review

and writes:

- `larql_rule.json`
- `larql_rule.md`
- `larql_apply_report.json`
- `larql_apply_report.md`

The rule artifact is written as an inert bounded artifact only. Runtime
installation is not performed.

Sample command:

```bash
python3 local_harness/affordance_larql_apply.py \
  --apply-packet .work/affordance_larql_apply_packets/navigator_cuda_larql_apply_v0/larql_apply_packet.json \
  --apply-review .work/affordance_larql_apply_reviews/navigator_cuda_larql_apply_v0/larql_apply_review.json \
  --out .work/affordance_larql_applied_rules/navigator_cuda_larql_rule_v0
```

Boundary:

This packet writes a bounded LARQL rule artifact for later validation only.
It does not install the rule into durable memory, train LoRA, promote the
candidate, or modify runtime behavior.
