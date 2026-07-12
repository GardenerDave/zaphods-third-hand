# Qwen3 Coder Triage Router Review 2026-07-12

This report reviews `triage-router-supervised-attempts` as a feature line
against `origin/main`.

## Branch evidence

- reviewed branch: `triage-router-supervised-attempts`
- reviewed commit: `6b725bc23529b8ce9b612591d12d8bcaeb7bba2e`
- merge base with `origin/main`:
  `7ce0494ae5da9426d9838334d5d156dd27ae5504`
- divergence from `origin/main`: `0 ahead`, `34 behind`
- detached review clone:
  `/tmp/zth_triage_review_6kVfbr_clone`

## Subsystem review

The branch is coherent as a small feature line with two commits:

- `efd2870` fixes false-positive scoring in the authority probe.
- `6b725bc` adds the reusable endpoint logic-probe workflow.

The diffs are aligned around one concern: reproducible logic-probe execution
and scoring. The branch does not appear to introduce unrelated architecture.

## Findings

### Confirmed defect

- `local_harness/run_endpoint_logic_probes.sh` assumes `choices[0]` exists in
  the OpenAI-compatible response. An empty or malformed response would raise a
  runtime exception instead of producing an explicit transport/response
  failure record.

### Confirmed documentation drift

- The workflow addition is only lightly documented in the branch itself. The
  runner and fixture introduce a reusable path that benefits from a small
  operator guide describing the endpoint-backed probe flow and its evidence
  boundaries.

### Test gap

- The branch lacks focused tests for the shell runner’s error handling,
  argument validation, and response parsing edge cases.
- The scoring path is covered, but the shell-level runner behavior is not.

### Architectural concern

- The new forbidden-regex entry for `proceed with implementation` is useful,
  but it should be watched for over-broad matching in future probe expansions.
  In this branch it is a caution, not a demonstrated defect.

### Acceptable design tradeoff

- Using a hardcoded default model name for local endpoint runs is acceptable
  here because the workflow is explicitly endpoint-backed and the model is
  passed as an argument.

## Test evidence

- `python3 -m pytest local_harness/tests/test_logic_probe.py -q`
  -> `23 passed in 0.10s`
- `python3 -m pytest tests/test_run_endpoint_logic_probes.py -q`
  -> `4 passed in 0.14s`

## Review conclusion

The branch is a reasonable, narrow feature line and does not show a merge-risk
architecture problem. The strongest open issue is the runner’s optimistic
response parsing, followed by missing shell-runner edge-case tests and better
workflow documentation.

This report is evidence, not acceptance or promotion.
