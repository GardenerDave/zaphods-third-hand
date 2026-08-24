# Semantic Label Counterfactual V0 Closeout

The corrected freeze was commit `0a8018567b992ed5bd79a90a97497c2d4c773ea1`
with driver SHA256
`f9a44a33f5ae7140fbe70f6879a734d441756ae2136b39c86839d626180925e8`.
The operator run was
`.work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222100Z`.

Exactly 12 responses were preserved. All were parse-valid, contract-valid,
candidate-valid, and candidate-admissible. There were 12 model calls, zero
tool calls, zero retries, zero evaluator runtime influence, and zero
model-granted authority.

Arm A (current labels) scored semantic correctness 3/6: presence 0/3 and
inspect 3/3. Arm B (neutral labels) scored 6/6: presence 3/3 and inspect 3/3.
Canonical paired transitions were `inspect -> observe_presence = 3` and
`inspect -> inspect = 3`; all other transitions were zero. All three recoveries
were the expected presence tasks.

Bounded markers:

```text
LABEL_TOKEN_EFFECT_SUPPORTED=true
NEUTRAL_LABEL_PRESENCE_RECOVERY_DEMONSTRATED=true
PRESENCE_PAIR_RECOVERY=3/3
INSPECT_PAIR_STABILITY=3/3
UNDERLYING_BOUNDED_SEMANTIC_DISTINCTION_DEMONSTRATED=true
SEMANTIC_FAILURE_LOCALIZED_TO_LABEL_INTERFACE=true
ORIGINAL_INTERFACE_SUPPRESSED_OBSERVABLE_CAPABILITY=true
```

This does not isolate `observe_presence` from `inspect` individually: both
literal labels changed together. It does not establish broad supplier
qualification or production policy. The next experiment is the four-arm
surface-label factorial.

Telemetry is descriptive only. Measurement level was 2 with boundary
`gpu_device_only`; process-level remote exclusivity was not established. Arm A
latency mean/median/p95 was 1186.989/1162.601/1301.182 ms and Arm B was
1222.490/1233.365/1252.949 ms. Overall latency was
1204.740/1205.293/1252.949 ms. Energy totals were 206.195 J for A, 219.4825 J
for B, and 425.6775 J overall.

The full paired scores and raw artifact hashes are in the [closeout matrix](SEMANTIC_LABEL_COUNTERFACTUAL_V0_MATRIX_2026-08-23.json).
