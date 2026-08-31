# Dogfood Round 3 Preservation and Historian Readiness Report

Date: 2026-08-31

This report preserves the Round 3 bounded repository-observation baseline before the Historian-vs-direct-projection comparison. The raw `.work/dogfood_round3/` run directories remain unchanged.

## Preserved Baseline

Immutable raw run directories:

- `.work/dogfood_round3/task1/20260831T060000Z`
- `.work/dogfood_round3/task2/20260831T060500Z`
- `.work/dogfood_round3/task3/20260831T061000Z`

### Round 3 Task Definitions

| Task | Conceptual task | Evidence supplier | Worker |
| --- | --- | --- | --- |
| Task 1 | Roadmap-to-implementation consistency | Direct bounded file projection | `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` |
| Task 2 | Newcomer documentation/navigation inspection | Direct bounded file projection | `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` |
| Task 3 | Provenance/evidence completeness inspection | Direct bounded file projection | `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` |

### Round 3 Projected Sources

Task 1 projected:

- `docs/ROADMAP.md`
- `docs/reports/1p7b_to_30b_structured_continuous_v2_20260830.md`
- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/transaction_manifest.json`

Task 2 projected:

- `docs/README.md`
- `docs/DOGFOOD_RUNNER.md`
- `docs/SUPERVISED_HANDOFF_PACKET.md`
- `docs/SUPERVISED_REVIEW_DECISION_RECORD.md`

Task 3 projected:

- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/worker_b_local_model_call.json`
- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/worker_b_call_intent.transport_events.jsonl`
- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/transaction_manifest.json`

### Round 3 Budget Diagnostics

All three packets passed preflight.

| Task | Estimated prompt tokens | Available prompt tokens | Response reserve | Overhead | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Task 1 | 1336 | 6780 | 900 | 512 | passed |
| Task 2 | 1405 | 6780 | 900 | 512 | passed |
| Task 3 | 1169 | 6780 | 900 | 512 | passed |

The budgeting method was deterministic and conservative: `ceil(prompt_characters / 4)`.

### Round 3 Response Contract

The observation-lane contract required:

```json
{
  "format": "json",
  "required_fields": ["findings", "reason"],
  "requires_reason": true
}
```

That schema was written as `response_schema.json` in each run directory and used by the local endpoint.

## Round 3 Reconstruction

| Task | Transport | JSON parse | Observation schema | Grounding | Semantic review / downstream use |
| --- | --- | --- | --- | --- | --- |
| Task 1 | passed | passed | passed | passed | not accepted |
| Task 2 | passed | passed | passed | passed | not accepted |
| Task 3 | passed | passed | passed | failed | not accepted |

### Task 1 Summary

Task 1 produced a cautious file-grounded comparison between the roadmap and the implementation/report evidence. It passed mechanical validation and grounding, but it was not accepted for downstream use.

### Task 2 Summary

Task 2 produced documentation-navigation observations grounded in the supplied docs files. It passed mechanical validation and grounding, but it was not accepted for downstream use.

### Task 3 Summary

Task 3 produced a provenance/evidence-completeness answer, but two cited paths were not in the projected evidence set:

- `.work/operator_handoffs/1p7b_to_30b_structured_continuous_v2_20260830/20260831T020000Z/20260831T020000Z/model_prompt_packet.md`
- `.work/operator_handoffs/1p7b_to_30b_structured_continuous_v2_20260830/20260831T020000Z/20260831T020000Z/run_manifest.json`

The validator therefore failed grounding while preserving the raw output and keeping semantic acceptance separate from mechanical validation.

## Artifact Hash Inventory

Representative SHA-256 values for the preserved Round 3 artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `.work/dogfood_round3/task1/20260831T060000Z/evidence_projection.json` | `40c5b2216788beaefc49594f33ebdecd5934c3fa44fff98fd82014d0b196bcb8` |
| `.work/dogfood_round3/task1/20260831T060000Z/model_prompt_packet.md` | `bf695dba5b3577921a58682122a1c59fa1d165d2ecd8f2cb33bcbbd47b042234` |
| `.work/dogfood_round3/task1/20260831T060000Z/output_validation.json` | `5b8dde855cad9485a21de39405923e7743017b2661c15775c36edc54508c4d30` |
| `.work/dogfood_round3/task1/20260831T060000Z/raw_model_output.txt` | `c099115140d2a4d34c3759694197cc868d9f6a425703eaa4fcd8c2a8da85fcb3` |
| `.work/dogfood_round3/task1/20260831T060000Z/run_manifest.json` | `8aff0eb8bf3b02e2d63315c4406fcb82a20de4bafb0fcec5b5ce2cfd53183eb1` |
| `.work/dogfood_round3/task1/20260831T060000Z/prompt_projection_summary.json` | `a981fec44443a9e7f5fa6c3fab4631e6289d727ac829013be1b080157c180379` |
| `.work/dogfood_round3/task2/20260831T060500Z/evidence_projection.json` | `8ffec578101cc0bb84bdc40e30253bcd3c54e3d4ba2fa2c68e51e60b2fd85ba8` |
| `.work/dogfood_round3/task2/20260831T060500Z/model_prompt_packet.md` | `cfab8f147caca705944155029a26beea451285bf89d909412758c2e0420075d0` |
| `.work/dogfood_round3/task2/20260831T060500Z/output_validation.json` | `5546217ce236b2ddbc3ece7876320e2db424e2c87337a26ab44e6b39a7025855` |
| `.work/dogfood_round3/task2/20260831T060500Z/raw_model_output.txt` | `e4d1f53948d85b98e4c22325d6cbdd0ba1493363f834b9388f58b1bcfdacde2d` |
| `.work/dogfood_round3/task2/20260831T060500Z/run_manifest.json` | `aae37fe07a9f44dc4667d4fb1c6d6ea1714185991d1fcfcb69bf69e5c8e5b880` |
| `.work/dogfood_round3/task2/20260831T060500Z/prompt_projection_summary.json` | `1e02caf18e3cfdce83257f0b095e9d789474fff90076b17126c0afdec72242dc` |
| `.work/dogfood_round3/task3/20260831T061000Z/evidence_projection.json` | `a0daaad35a1adcda4b15150b246be844ac69ce34552e8c26ae75923de3adb905` |
| `.work/dogfood_round3/task3/20260831T061000Z/model_prompt_packet.md` | `4d4ad4b3244697163b64efe14aacb9c00ef6877f5ddd56c8797542a7f838e1f3` |
| `.work/dogfood_round3/task3/20260831T061000Z/output_validation.json` | `9a9d75559832c9d648b3c72305891b4128c1d5c76d5afbb475f8795c86b2238f` |
| `.work/dogfood_round3/task3/20260831T061000Z/raw_model_output.txt` | `c46a0e214737005d2f1c5dd10c058ddbfb82e731eedb2643b468dc8df5c999be` |
| `.work/dogfood_round3/task3/20260831T061000Z/run_manifest.json` | `14ff9095c74e55444dc9c2ff5911308ee111fdc98654e6bb481ea33f11d82db0` |
| `.work/dogfood_round3/task3/20260831T061000Z/prompt_projection_summary.json` | `af927730675493862c9e804394026cf1a0146b32826cc998c0eb873a0b56b699` |

## Historian Readiness Audit

### Implementation Discovered

The repository does not currently expose a repo-native Python source implementation for `historian`. The `historian/` directory contains compiled `.pyc` artifacts only, and importing `historian` yields an empty module surface in this workspace.

### Usable Historian Evidence

The repository does contain an archived Historian run bundle under:

- `.work/historian_dynamic_two_tier_escalation_v1/`

That bundle provides:

- read-only worker prompts
- structured evidence packets
- historical record IDs
- retrieval provenance
- request/response hashes
- validation state
- fallback failure evidence

### Read-Only Query Capability

The archived bundle shows a read-only Historian worker contract, but it is not a live repo-native query interface. No source-level adapter for querying Historian from ZTH was found in the checked-in code.

### Constraints

- No repo-native Historian source files were available to inspect.
- No direct live Historian query API was discoverable from the checked-in code.
- The archived bundle is suitable as evidence, not as a reusable query surface.

### Minimal Adapter Assessment

Because no callable repo-native Historian source path was found, any live comparison integration would require a small adapter or wrapper around the archived Historian contract. That is not yet present in the repository.

## Commit Record

- Preservation report commit: pending at time of file creation

## Interpretation

Round 3 established a workable direct bounded-projection baseline. The remaining question for the next experiment is whether Historian can be made into a comparable bounded evidence supplier without changing the worker contract, budget, or review rubric.
