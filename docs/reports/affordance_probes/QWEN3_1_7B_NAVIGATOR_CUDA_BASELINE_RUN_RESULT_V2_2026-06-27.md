# Baseline Affordance Lane Result Report

Model id: `qwen3-1.7b-gpu-40k`
Endpoint host: `http://<redacted-host>`
Candidate id: `larql_affordance_candidate_48efff9852ea`
Selected lane: `baseline_prompt_context_only`
Verdict: `baseline_needs_review`
Promotion verdict: `hold_pending_explicit_experiment_approval`

## Digests

- Candidate digest: `c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520`
- Candidate digest verified: `true`
- Prompt-suite digest: `d87cdfa829cdc8dcfff26d1b5ded0b742bd632e8d136f32f53cddaa834a4010e`
- Prompt-suite digest verified: `true`

## Prompt Results

| Prompt | Coverage | Verdict | Model call |
|---|---|---|---:|
| `baseline_direct_cuda_on_navigator` | direct CUDA-on-Navigator question | `pass` | `true` |
| `baseline_cross_host_boundary` | cross-host boundary | `pass` | `true` |
| `baseline_unknown_host_reverify` | unknown-host refusal/reverify | `pass` | `true` |
| `baseline_split_workflow_active_host` | split workflow where local and remote hosts differ | `needs_review` | `true` |
| `baseline_reverify_before_action` | reverify-before-action behavior | `pass` | `true` |
| `baseline_no_durable_promotion` | no durable promotion behavior | `needs_review` | `true` |
| `baseline_provenance_digest_awareness` | provenance/source-digest awareness | `pass` | `true` |

## Boundary

- baseline lane only
- no LARQL
- no LoRA
- no model mutation
- no durable memory
- no comparison lane
- no candidate promotion
- no repo modification
- no commit or push

## Notes

- Runner does not apply LARQL, train LoRA, mutate models, write durable memory, modify repo files, commit, push, or promote candidates.
