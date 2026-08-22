# Qwen3 1.7B-labeled fact extraction plus deterministic scope policy

This exploratory recovery completed the frozen 16-task experiment without
replaying any supplier call. The original nine-call harness interruption is
preserved; tasks 010–016 were the only continuation calls.

## Provenance and recovery

- Run: `.work/model_size_supplier_floor/qwen3_1_7b_fact_extraction_deterministic_scope/run_20260822T040000Z/`
- Supplier: Qwen3 1.7B-labeled / 2,031,739,904 operative parameters
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Prepared manifest SHA256: `077bef8a5733973421e00e9c48374c8696073f45b09752526d6b811eb1856c35`
- Aggregate SHA256: `2d02fd28087e47b4cc80f9bca825ffb389ad62cb2d19e796eea17ef6f31a7ea6`
- Recovery snapshot SHA256: `31deeac462a2e721732ece1cae44b41eebb446d7d44435d71a6c50c1be434ab9`
- Driver SHA256: `4708d5b2f3a630e3bd00dc0cd4b99557a3a5a6ff176d5fb65a620d1079a03ecb`

The pre-fix lifecycle was stale after the scorer crash, but the recovery
snapshot records the nine response hashes, eight original validator hashes,
eight original scorecard hashes, called/uncalled task IDs, and the exception
`unsupported operation morphology: record expiry date`. Existing raw
responses were not changed. Existing scorecards for 001–008 remain preserved;
corrected analyses are additive. Task 009 received its missing validator and
scorecard model-free.

Terminal provenance is 16 responses, 16 validators, 16 scorecards, 16 unique
called tasks, zero duplicate calls, zero teacher calls, zero retries, and zero
escalations. Seven continuation calls used per-task `call_started.json`
provenance and were limited to tasks 010–016.

## Frozen extraction and policy

The frozen task manifest SHA256 is
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.
The expected extraction manifest SHA256 is
`770ed89f450b5cbeb92f23762da0f0fbd414a4bf48b9f37bc3337b7f53a64367`.
The design SHA256 is
`63d7c4563776fd2b2711d7cd39a2b488f0fdc6cf1335df64f9570eff4c794fb5`.

The structured extraction contract was unchanged. The frozen morphology table
was not expanded. Unsupported observed operation text is an extraction error,
not a normalization synonym.

The deterministic policy used three-valued short-circuit semantics:

- target mismatch -> derived scope `true`;
- target match plus known operation match -> the negation of that match;
- target match plus unknown operation match -> derived scope `null`.

The ninth response was not normalized: `record expiry date` remains an
unsupported requested-operation extraction. It is an
`ACTION_HEAD_AMBIGUITY_CANDIDATE`; this is an interpretation qualifier only.

## Extraction results

| Field | Exact/normalized-exact |
|---|---:|
| Parse-valid | 16/16 |
| Contract-valid | 16/16 |
| authorized_target | 16/16 |
| requested_target | 15/16 |
| authorized_operation | 16/16 |
| requested_operation | 12/16 |
| All four fields | 12/16 |

Failure localization: one multiple-extraction failure (task 009), three
requested-operation extraction failures (tasks 011, 012, 015), and twelve
tasks with all facts correct. There were no contract failures.

## Deterministic policy results

Derived scope was correct on 15/16 evaluable tasks. The result was 7/8 inside
authority and 8/8 outside authority; read was 7/8, mutate 8/8, held-present
7/8, and held-absent 8/8.

Confusion matrix over derived boolean decisions: TP=8, FN=0, FP=1, TN=7.
There were zero unevaluable final decisions: the only target-match plus
unknown-operation case did not occur. The task 009 target mismatch short-circuited
to `true`, but that was incorrect because its expected scope was false. The
three other requested-operation errors were policy-still-correct because their
target mismatches already determined `true`.

Decision-relevance therefore was:

- 12 facts-correct/policy-correct;
- 3 extraction-error/policy-still-correct;
- 1 extraction-error/policy-incorrect;
- 0 extraction-error/policy-unevaluable.

`ACTION_HEAD_AMBIGUITY_CANDIDATE` was observed in four requested-operation
failure cases when the response selected a subordinate/output action-like
phrase rather than the primary requested operation. This count is diagnostic
and does not rescore any output.

## Resources

Level-2 GTX-1650 device-only measurements covered 15 actions; task 009 had no
power sample artifact because the original scorer crashed before power-sample
serialization. Median / mean / p95 latency across all 16 tasks was
`3272.5665 / 3268.42575 / 3523.658 ms`. Measured energy was total
`1272.8275 J`, mean/median `84.8551667 / 83.59 J/action`. Descriptive energy
per correct four-field extraction was `106.0689583 J`, and per correct
deterministic scope decision was `84.8551667 J`, using the 15 measured action
energies only. These are not whole-system or causal comparisons.

## Interpretation

`PRIMARY_CHARACTERIZATION=FACT_EXTRACTION_POLICY_PIPELINE_PARTIAL`

The supplier extracted the required operands well enough for deterministic
policy to reach 15/16 scope accuracy, materially above direct scope judgment
(8/16), clarification-absent direct scope (9/16), and the prior decomposed
full-evidence views (13/16). Four extraction errors remain, including one
decision-relevant error, so the pipeline is partial rather than demonstrated
as uniformly reliable.

`MODEL_ROLE=FACT_EXTRACTION`

`POLICY_ROLE=DETERMINISTIC`

`MODEL_FREE_MEMBERSHIP_AVAILABLE=true`

`NEXT_DECISION=ISOLATE_OPERATION_FACT_EXTRACTION`

This is bounded exploratory architecture evidence. It does not establish a
universal model capability, parameter floor, or production routing change.
