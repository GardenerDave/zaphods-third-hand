# Affordance LARQL Dry-Run Packet v0

Status: experimental model-free dry-run packet

Affordance LARQL Dry-Run Packet v0 drafts an inert LARQL-rule-shaped packet
from an accepted baseline affordance candidate and a completed baseline result.

This is dry-run packet only. It does not apply LARQL, train LoRA, mutate
models, write durable memory, or promote the candidate.

## Purpose

The packet exists after a baseline pass and post-run audit confirm that the
candidate was reviewed under the baseline prompt-context lane and that the
promotion verdict remains held.

It records a draft LARQL rule shape for later review. It does not authorize
application.

## Inputs

- `affordance_patch_candidate.json`
- `baseline_lane_result_report.json`
- `post_run_audit_report.md`

## Outputs

The helper writes:

```text
larql_dry_run_packet.json
larql_dry_run_packet.md
```

## Packet verdicts

- `ready_for_larql_dry_run_review`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Draft LARQL rule

The packet contains an inert rule draft with:

- a rule id;
- the conditions under which the rule would apply;
- what it would block or warn on;
- what it would recommend;
- when it would require reverify.

The rule is not applied by this packet.

## Boundary

This is a dry-run packet only. It is not an applied LARQL patch, not durable
memory, not LoRA training, and not promotion.

It exists so a reviewer can decide whether a later LARQL apply packet should
be drafted.

## Sample command

```bash
python3 local_harness/affordance_larql_dry_run_packet.py \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --baseline-result .work/affordance_baseline_runs/navigator_cuda_baseline_v5/baseline_lane_result_report.json \
  --post-run-audit .work/affordance_baseline_runs/navigator_cuda_baseline_v5/post_run_audit_report.md \
  --out .work/affordance_larql_dry_run_packets/navigator_cuda_larql_dry_run_v0
```
