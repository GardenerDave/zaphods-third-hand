# Qwen3 Coder Triage Router Review 2026-07-12

Correction note:

- The first version of this report reversed the ahead/behind interpretation of
  `git rev-list --left-right --count origin/main...triage-router-supervised-attempts`.
- The temporary clone created with `git clone . <path>` changed the meaning of
  `origin/main` and only exposed the two-commit tail of the feature line.
- This corrected report uses immutable literal hashes from the authoritative
  repository and reviews the complete 34-commit range
  `7ce0494ae5da9426d9838334d5d156dd27ae5504..6b725bc23529b8ce9b612591d12d8bcaeb7bba2e`.

## Branch evidence

- reviewed branch: `triage-router-supervised-attempts`
- reviewed tip: `6b725bc23529b8ce9b612591d12d8bcaeb7bba2e`
- authoritative base: `7ce0494ae5da9426d9838334d5d156dd27ae5504`
- merge base: `7ce0494ae5da9426d9838334d5d156dd27ae5504`
- divergence from `origin/main`: `34 ahead`, `0 behind`
- reviewed detached clone:
  `/tmp/zth_triage_review_corrected_20260712`

## Review method

This review treated the branch as one feature line and grouped commits into
subsystems using the authoritative diff and commit sequence. The supporting
evidence came from:

- `git rev-list --reverse 7ce0494ae5da9426d9838334d5d156dd27ae5504..6b725bc23529b8ce9b612591d12d8bcaeb7bba2e`
- `git diff --stat 7ce0494ae5da9426d9838334d5d156dd27ae5504..6b725bc23529b8ce9b612591d12d8bcaeb7bba2e`
- focused tests across the affected harness components
- the corrected detached clone at `/tmp/zth_triage_review_corrected_20260712`

## Subsystem map

### Dogfood and compliance evidence

- commits: `65aa73d`, `446bb7f`, `f8d0d8a`, `b83ddb6`, `efd2870`
- principal files:
  - `docs/reports/model_auditions/CODING_DELEGATION_DOGFOOD_2026-07-02.md`
  - `local_harness/logic_probes.example.json`
  - `local_harness/affordance_larql_absence_of_evidence_model_context_probe_review.py`
- contracts:
  - preserve failure evidence
  - keep authority boundaries explicit
  - keep logic-probe scoring honest
- adjacent relationship:
  - establishes the evidence baseline for later supervised workflows
- focused tests:
  - `local_harness/tests/test_logic_probe.py`
- suspected overlap:
  - none beyond the shared evidence vocabulary
- confirmed findings:
  - preserved dogfood/report artifacts are consistent with the later workflow
- unresolved questions:
  - none specific to this subsystem

### Prompt patch library and triage/router

- commits: `946a819`
- principal files:
  - `local_harness/prompt_patch_library.py`
  - `local_harness/triage_router_rules.py`
  - `tests/test_prompt_patch_library.py`
  - `tests/test_triage_router_rules.py`
  - `examples/prompt_patches/*.json`
  - `examples/triage_packets/*.json`
- contracts:
  - bounded prompt patch selection
  - explicit triage packet schema and routing rules
  - target/held separation and scope control
- adjacent relationship:
  - feeds orchestration packets and manual supervised attempts
- focused tests:
  - `tests/test_prompt_patch_library.py`
  - `tests/test_triage_packet_schema.py`
  - `tests/test_triage_router_rules.py`
- confirmed findings:
  - the library and triage rules are aligned with the repository's supervised
    scope-control vocabulary
- unresolved questions:
  - none specific to the library shape

### Orchestration boundary and prompt packet rendering

- commits: `d2fb7b9`, `331d3aa`, `425321a`
- principal files:
  - `local_harness/orchestration_packet.py`
  - `local_harness/render_orchestration_packet.py`
  - `local_harness/render_model_prompt_packet.py`
  - `tests/test_orchestration_packet.py`
  - `tests/test_render_orchestration_packet.py`
  - `tests/test_render_model_prompt_packet.py`
  - `examples/orchestration_packets/orchestration_example_001.json`
  - `examples/model_prompt_packets/model_prompt_packet_example_001.md`
- contracts:
  - orchestration packets remain bounded evidence
  - rendered prompt packets preserve selected patches and validation hooks
  - patch-required fields are merged into prompt contracts
- adjacent relationship:
  - connects triage/router output to supervised model attempts
- focused tests:
  - orchestration and prompt-packet renderer tests above
- suspected overlaps:
  - renderer and packet builder share vocabulary but remain separated by file
  - the merge of required fields into prompt contracts is intentional
- confirmed findings:
  - docs and code agree on bounded packet assembly
- unresolved questions:
  - none material

### Supervised model-attempt recording and output validation

- commits: `d83df8c`, `5002ad6`, `c5b40a3`, `24192b0`
- principal files:
  - `local_harness/supervised_model_attempt.py`
  - `local_harness/render_supervised_model_attempt.py`
  - `local_harness/supervised_attempt_output_validator.py`
  - `tests/test_supervised_model_attempt.py`
  - `tests/test_render_supervised_model_attempt.py`
  - `tests/test_supervised_attempt_output_validator.py`
  - `examples/supervised_model_attempts/supervised_model_attempt_example_001.json`
  - `examples/supervised_attempt_validations/supervised_attempt_output_validation_example_001.json`
- contracts:
  - record attempt evidence
  - validate output shape and required fields
  - reject duplicate JSON keys and wrong field types
- adjacent relationship:
  - the validator is the gate between raw attempt evidence and later review
- focused tests:
  - `tests/test_supervised_model_attempt.py`
  - `tests/test_supervised_attempt_output_validator.py`
- confirmed findings:
  - duplicate-key rejection and field-type validation are deliberately covered
- unresolved questions:
  - none material

### Review decisions, downstream-use gates, and handoff packets

- commits: `61f12f1`, `ffc174f`, `903a9a5`
- principal files:
  - `local_harness/supervised_review_decision.py`
  - `local_harness/supervised_downstream_use_gate.py`
  - `local_harness/supervised_handoff_packet.py`
  - `local_harness/render_supervised_review_decision.py`
  - `local_harness/render_supervised_downstream_use_gate.py`
  - `local_harness/render_supervised_handoff_packet.py`
  - `tests/test_supervised_review_decision.py`
  - `tests/test_supervised_downstream_use_gate.py`
  - `tests/test_supervised_handoff_packet.py`
- contracts:
  - validation is evidence, not acceptance
  - downstream-use gate remains separate from review decision
  - handoff packet remains separate from gate and review
- adjacent relationship:
  - packages reviewed evidence for the next supervised step
- focused tests:
  - the review, gate, and handoff test files above
- confirmed findings:
  - acceptance and downstream-use authority are intentionally separated
- unresolved questions:
  - none material

### Supervised chain smoke

- commits: `8242ae3`, `4d1f9b6`
- principal files:
  - `local_harness/supervised_chain_smoke.py`
  - `local_harness/run_supervised_chain_smoke.py`
  - `local_harness/render_supervised_chain_smoke_report.py`
  - `tests/test_supervised_chain_smoke.py`
  - `tests/test_run_supervised_chain_smoke.py`
  - `tests/test_render_supervised_chain_smoke_report.py`
- contracts:
  - preserve the chain from model attempt through handoff
  - maintain evidence-only semantics through every layer
- adjacent relationship:
  - proves the packets compose into an auditable supervised chain
- focused tests:
  - the chain smoke tests above
- confirmed findings:
  - the chain smoke layer is coherent with the decision/gate/handoff layers
- unresolved questions:
  - none material

### Manual supervised attempt runner, session mode, local calls, retry contracts, and pattern export

- commits: `cf42a91`, `e3ee046`, `8ab3fdb`, `7df2078`, `043188f`, `f8d0d8a`, `9505d78`, `dd8042f`, `039a4de`, `c23adf5`, `92cb71f`, `f873bfd`, `64fda01`, `0901faf`
- principal files:
  - `local_harness/run_manual_supervised_attempt.py`
  - `local_harness/run_manual_supervised_attempt_batch.py`
  - `tests/test_run_manual_supervised_attempt.py`
  - `tests/test_run_manual_supervised_attempt_batch.py`
  - `examples/supervised_training_patterns/*.json`
  - `examples/supervised_training_patterns/README.md`
- contracts:
  - manual prepare/session/call-local/retry/ingest flow
  - preserved failed evidence for retries
  - explicit downstream-use and handoff gates
  - candidate-pattern export remains evidence-only
  - batch execution records retry freshness and ledger state
- adjacent relationship:
  - this is the main supervised operator workflow around the model endpoint
- focused tests:
  - the manual runner and batch runner tests above
- confirmed findings:
  - the retry contract preserves failure evidence and prompts
  - pattern export remains candidate-only
- unresolved questions:
  - whether additional shell-level error handling should be hardened further

### Endpoint logic probes

- commits: `efd2870`, `6b725bc`
- principal files:
  - `local_harness/run_endpoint_logic_probes.sh`
  - `local_harness/logic_probes.example.json`
  - `tests/test_run_endpoint_logic_probes.py`
  - `local_harness/tests/test_logic_probe.py`
- contracts:
  - validate probe fixtures before execution
  - write raw response evidence with elapsed timing
  - score logic probes from preserved raw records
- adjacent relationship:
  - reusable endpoint-backed diagnostic workflow
- focused tests:
  - `tests/test_run_endpoint_logic_probes.py`
  - `local_harness/tests/test_logic_probe.py`
- confirmed findings:
  - the branch's logic-probe workflow is coherent and test-covered
- unresolved questions:
  - shell runner error paths remain a candidate for deeper negative testing

## Findings classification

### Confirmed defect

- none confirmed from the full 34-commit review after empirical testing.

### Confirmed documentation drift

- the report family needed correction because the first version reviewed the
  wrong comparison and reversed the divergence interpretation.

### Test gap

- the logic-probe shell runner still benefits from deeper negative coverage for
  malformed endpoint responses and transport failures.
- the shell runner's error-handling path is narrower than the Python-side
  validation coverage.

### Architectural concern

- the shell runner assumes a conventional OpenAI-compatible response shape.
  That is acceptable for the current workflow but should remain monitored.

### Unsupported model suspicion

- the generic architectural risks produced by the adversarial review model were
  not evidence-specific and were treated as unsupported suspicion only.

### Acceptable design tradeoff

- the feature line intentionally uses many small packets and renderers rather
  than one large monolithic workflow.
- the pattern-export path remains candidate-only and evidence-only.

### Blocked by missing evidence

- no branch-wide blocker remained after the full-range tests passed.

## Test evidence

Focused tests:

- `python3 -m pytest --import-mode=importlib tests/test_prompt_patch_library.py tests/test_triage_packet_schema.py tests/test_triage_router_rules.py tests/test_orchestration_packet.py tests/test_render_model_prompt_packet.py tests/test_supervised_model_attempt.py tests/test_supervised_attempt_output_validator.py tests/test_supervised_review_decision.py tests/test_supervised_downstream_use_gate.py tests/test_supervised_handoff_packet.py tests/test_supervised_chain_smoke.py tests/test_run_manual_supervised_attempt.py tests/test_run_manual_supervised_attempt_batch.py tests/test_run_endpoint_logic_probes.py local_harness/tests/test_logic_probe.py -q`
- result: `436 passed in 8.47s`

Broad suite:

- `python3 -m pytest --import-mode=importlib tests local_harness/tests -q`
- result: `2432 passed, 2 skipped, 12 subtests passed in 51.45s`

## Review conclusion

The full 34-commit feature line is coherent. It is a layered supervised
workflow stack that moves from prompt-patch selection through orchestration,
attempt recording, output validation, review/gating, handoff, batch execution,
pattern export, and endpoint-backed logic probes.

The main correction from the first report is provenance, not architecture:
the first review used the wrong reference resolution and therefore only
described the two-commit tail. The corrected review confirms the broader line
is well aligned, with remaining concerns limited to shell-runner hardening and
documentation drift rather than a merge-blocking architectural flaw.

This report is evidence, not acceptance or promotion.
