# Direct-Unit Calibration Stage A Semantic Validity Audit

Date: 2026-08-24

## Decision

`STAGE_A_SEMANTIC_FAILURE_RESULT_SUPPORTED`

The sealed acquisition is model-free intact: 32 response artifacts, 32 starts, 32 finishes, zero infrastructure failures, zero retries, and zero replays. The raw response manifest was sealed before evaluator loading. Response-file hashes and matched payload hashes were checked without rewriting the run.

The V2 evaluator uses only the registered keys `must_include`, `must_not_include`, and `review_status`. All are registered and compatible with the V2 interface. A synthetic canonical object was constructed for each of the 16 cases and passed through the same reference-fact validator; `16/16` passed. The closeout adapter passes the V2 expected object directly to `validate_reference_facts`; no V1 route equality, strict extra-property rejection, family-specific type constraint, or literal `more evidence` rule was reconstructed.

`review_status` is enforced by the registered direct-field reference-fact check in the semantic result. The closeout's separate `review_valid` field is redundant for the V2 cases, but does not weaken enforcement because every V2 expected object includes `review_status`.

## 32-response semantic diagnostics

All 32 new observations remain transport-valid, parse-valid, required-field-valid, protocol-valid, and semantic-invalid under the frozen V2 path. The per-case/per-arm check results and aggregate counts are in the machine-readable matrix. The failure is not a transport or contract cliff. Triage failures include missing generic serialized-output phrases and/or non-`ready_for_review` statuses. Unsupported-certainty responses generally satisfy the generic positive/negative phrase checks but fail the exact frozen `review_status` value. The eight external unsupported-certainty rows are reproduced mechanically in the matrix; no response was repaired or reclassified.

Because the V2 registry is complete, its synthetic contracts are satisfiable, and the adapter applies it correctly, the 32/32 semantic-failure result is supported by the frozen measurement. `VALIDATOR_GAP_SUPPORTED=false`.

## Stale control metadata

`execution_manifest.json` remains `status=running`. It is preserved unchanged as stale control metadata. `raw_response_manifest.json` (`SEALED_BEFORE_EVALUATION`) and `lifecycle.json` (`terminal_runtime`) are the authoritative completion evidence for this historical run. Future harnesses should finalize the execution manifest atomically at terminal acquisition.

## Supplier identity provenance

The external service identity remains `codex-cli-0.146.0` through the preserved wrapper/service mechanism. The run's stderr observably reports native model `gpt-5.6-luna`; that is recorded as provider/native provenance only and is not substituted for the frozen service identity. Audit calls: zero model, external-inference, and tool calls.

## Scientific boundary

This audit validates the semantic closeout; it does not begin Stage B, qualify either supplier, or change routing. The Stage A result remains a direct-unit calibration result with all 32 fresh semantic failures under V2, not a reason to fit a new policy.

`STAGE_B_GATE=OPEN_PENDING_STAGE_A_REVIEW`

`NEXT_DECISION=EVALUATE_DIRECT_UNIT_CALIBRATION_AND_STAGE_B_GATE`
