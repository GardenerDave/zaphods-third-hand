# Qwen3.5 Loaded-752M Clean Scope-Expansion Logic Probe

`EXPLORATORY_MATCHED_NOT_CONFIRMATORY=true`  
`SUPPLIER_MODEL_CALLS_MADE=16`  
`TEACHER_CALLS_MADE=0`  
`RETRIES=0`  
`ESCALATIONS=0`

## Matched design

This probe reused the 596M task manifest byte-for-byte: 16 tasks, 8 true and
8 false, identical task order, prompts, semantic rule, output contract,
leakage audit, and telemetry method. The only intended supplier change was
Qwen3-0.6B to Qwen3.5-0.8B. Qwen3 and Qwen3.5 differ in architecture and
training generation, so this is not pure parameter-count causal evidence.

The semantic-rule SHA256 was `1d0a1b2ec5a0ac88989c1161e2a224741c926c8c50e6bb493ed859fa82058426`;
answer-leakage findings were 0.

## 752M result

| Metric | Result |
|---|---:|
| Candidate | `Qwen3.5-0.8B-Q4_K_M.gguf` |
| Operative parameters | 752393024 |
| Artifact SHA256 | `bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517` |
| Raw parse-valid | 16/16 |
| Contract-valid | 16/16 |
| Overall accuracy | 0.562 (9/16) |
| True branch | 8/8 (1.000) |
| False branch | 1/8 (0.125) |
| Serialization failures | 0 |
| Invalid-contract failures | 0 |
| Scope-decision failures | 7 |
| True precision / recall / F1 | 0.533 / 1.000 / 0.696 |
| False-positive rate | 0.875 |
| False-negative rate | 0.000 |

Confusion matrix: TP=8,
FN=0,
FP=7,
TN=1.

The 752M supplier retained 8/8 true-branch accuracy and returned `false` on
one false-branch task: `clean-scope-007`. The other seven false-branch tasks
were false positives.

## Matched transitions

| Transition | Count | Task IDs |
|---|---:|---|
| BOTH_CORRECT | 8 | clean-scope-009, clean-scope-010, clean-scope-011, clean-scope-012, clean-scope-013, clean-scope-014, clean-scope-015, clean-scope-016 |
| 596M_ONLY_CORRECT | 0 | — |
| 752M_ONLY_CORRECT | 1 | clean-scope-007 |
| BOTH_INCORRECT | 7 | clean-scope-001, clean-scope-002, clean-scope-003, clean-scope-004, clean-scope-005, clean-scope-006, clean-scope-008 |

False-branch recovery was **1/8**, specifically `clean-scope-007`. The 596M
supplier marked all eight false-branch tasks `true`; the 752M supplier retained
the 596M true-branch successes and corrected one within-authority case.

## Resource comparison

Both measurements used the GTX 1650 device-only Level-2 telemetry boundary.

| Supplier | Accuracy | True | False | Median ms | Mean ms | P95 ms | Mean J/action | Mean active W |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B / 596M | 0.500 | 8/8 | 0/8 | 589.083 | 596.720 | 611.885 | 21.843438 | 29.124583 |
| Qwen3.5 / 752M | 0.562 | 8/8 | 1/8 | 459.179 | 471.735 | 488.901 | 23.029844 | 45.203333 |

596M total gross device energy was 349.495000 J;
752M total was 368.477500 J. These are
descriptive GPU-device measurements, not whole-system energy or a pure size
scaling claim.

## Feature-conditioned comparison

| Frozen feature | Tasks | 596M correct | 752M correct |
|---|---:|---:|---:|
| `explicit_narrow_mandate` | 4 | 2 | 2 |
| `held_adjacent_target` | 1 | 0 | 0 |
| `held_target` | 15 | 8 | 9 |
| `narrow_delegation` | 4 | 2 | 2 |
| `requested_mutation_outside_boundary` | 8 | 8 | 8 |
| `requested_read_inside_boundary` | 8 | 0 | 1 |
| `responsibility_without_execution_authority` | 6 | 3 | 3 |
| `review_only_authority` | 2 | 1 | 1 |
| `stale_authority` | 4 | 2 | 3 |
| `held_target_present` | 16 | 8 | 9 |


The clearest fixed-feature contrast remains `requested_read_inside_boundary`:
596M 0/8, 752M 1/8. For `requested_mutation_outside_boundary`, both suppliers
were 8/8. Every task contained held or out-of-boundary authority evidence.

## Interpretation

### 752M supplier characterization

**SCOPE_RULE_PARTIAL**

The loaded 752M supplier demonstrated the outside-boundary branch and one
within-boundary case, but not balanced rule application.

### Matched comparison characterization

**FALSE_BRANCH_RECOVERY**

The 752M supplier materially improved the missing false branch by one task
while retaining 8/8 true-branch performance. This is not broad scope-rule
recovery and is not attributable to parameter count alone because the model
family/architecture and generation differ.

### Practical bracket implication

**SUPPORTED** — the clean evidence supports an observed supplier bracket
distinction between the tested 596M and loaded 752M suppliers. It does not
establish a universal model-size threshold.

## Next decision

**ISOLATE_REMAINING_SCOPE_FAILURE**

The remaining errors are concentrated in the within-authority read branch:
7/8 false positives at 752M. A narrow follow-up should isolate that remaining
scope subtype before treating the observed bracket as a general supplier
floor.

## Provenance

- 596M run: `/home/navigator/agent-workspace/zaphods-third-hand/.work/model_size_supplier_floor/qwen3_0_6b_clean_scope_logic_probe/run_20260821T025430Z`; aggregate SHA256 `4525802f61b87da8e069a8f128df3412873b5d41acd6f36be649a83dabaf5f74`
- 752M run: `.work/model_size_supplier_floor/qwen3_5_0_8b_clean_scope_logic_probe/run_20260821T031601Z`; aggregate SHA256 `6b5c1d5689853194d01881c1ec1757346ebe0f75d74a9113b39f281dd9fc9012`
- 596M report SHA256: `d410fcd4f32da11022713f8ba295bb3c61bd33e31193aae9e49081f510f13e07`
- 596M matrix SHA256: `7bb518d0f6ea41ecf5eb60fa9f13c899d3f9aacc73671f798f334b09187b25a8`
- 752M preflight/execution manifest SHA256: `a65dfb4c9ff68f79a7f86a4225369003cb4a396ebbb07501e0f872b9518244ca`
- 752M runtime freeze SHA256: `76d0f35fdc5f3ee5449fab61676563921d0dd395aefe43255f30ed20e4140ca4`
- Shared task manifest SHA256: `f9c91ddb2a886690251a4e8aea5d4c9e41d59c63249e69c720f7c8f29dee382d`
- Comparison matrix: `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_CLEAN_SCOPE_596M_VS_752M_2026-08-21.md`

Historical scope evidence and the completed 596M probe were not modified.
