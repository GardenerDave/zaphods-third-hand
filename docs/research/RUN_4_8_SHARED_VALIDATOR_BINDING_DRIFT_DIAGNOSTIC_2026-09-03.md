# Run 4–8 Shared Validator Binding Drift — Diagnostic

- Date: 2026-09-03
- HEAD: `a34c13dcdc5dcdcdf519639b0aafadffbc61e0d3` (branch `main`, clean worktree)
- Scope: evidence-integrity diagnosis and remediation design only. No frozen artifact was modified, no frozen hash was updated, no fixture was regenerated, nothing was pushed.

## Central question

> Are the ~74 Run 4–Run 8 failures mostly many defects, or many correct detections of a small number of post-freeze implementation changes?

**Answer: many correct detections of exactly ONE post-freeze implementation change.** All seven Run 4/4A/4B/5/6/7/8 preregistrations bind the same shared module, `local_harness/supervised_attempt_output_validator.py`, and that one module changed after the experiments closed. Every Run 4–8 failure traces to that single binding mismatch, multiplied through three test-layer mechanisms. There are zero independent defects inside the Run 4–8 family.

## Failure map

### Run 4–8 family (shared binding mismatch)

Bound artifacts per preregistration (identical across all seven):

| Bound artifact | Frozen expected SHA-256 | Current SHA-256 | Status |
|---|---|---|---|
| `local_harness/supervised_attempt_output_validator.py` | `3ca42dfc6f683399752bfe4f5757b9edf4e7eafb09ac30166fe60e9f3beb0d27` | `255d121b8b4bd0157dea24123755c905af8f450a72af8ca564f2812f5f80c2e5` | **MISMATCH (all 7)** |
| `local_harness/supervised_capability_loop.py` | `23b26115201d8cba17b9da659af72793654897803988e35e28210eba02af81be` | same | match |
| `local_harness/supervised_reference_fact_validator.py` | `d86793dfde5a499988be92447f7df79da889a6074b8dc21b1c3b16bd7c60008a` | same | match |

Per-family failure counts (measured at HEAD `a34c13d`, isolated family run):

| Test file | Failures | Mechanism |
|---|---|---|
| `tests/test_run4_economic_routing.py` | 6 | CLI driver invocation fails at binding gate |
| `tests/test_run4a_driver.py` | 3 | in-process `driver._load_context` gate |
| `tests/test_run4a_preregistration.py` | 1 | direct digest assertion on `prereg["validators"]` |
| `tests/test_run4b_scope_replication.py` | 7 | CLI driver binding gate |
| `tests/test_run5_mixed_economic_routing.py` | 17 | `_context()` setup gate (incl. 8 parametrized drift-rejection tests that fail before their injected drift is exercised) |
| `tests/test_run6_sequential_economic_routing.py` | 20 | same (incl. 8 parametrized) |
| `tests/test_run7_scope_escalation.py` | 18 | same (incl. 8 parametrized) + message-order assertion |
| `tests/test_run8_scope_escalation.py` | 3 | CLI gate + `_context()` + message-order |
| **Total** | **75 measured** (74 in reported full-suite; see count reconciliation) | **one shared mismatch** |

Multiplication mechanisms:

1. **M1 — direct digest assertion**: `test_run4a_preregistration_binds_harness_and_validators` asserts `validator["sha256"] == _sha256(...)` against the live tree (1 failure).
2. **M2 — CLI binding gate**: tests invoke `scripts/zth_run*_*.py --preregistration <frozen prereg>` expecting exit 0; each driver re-verifies every binding at startup (`scripts/zth_run4a_intervention_calibration.py:172` checks validators) and exits nonzero on the validator mismatch.
3. **M3 — in-process setup gate**: run5/6/7/8 and run4a_driver tests share a `_context()` helper calling `driver._load_context(PREREG, ROOT, ...)`, which re-verifies all bindings; whole files fail at setup. This includes 24 parametrized resume-drift tests (8 each in run5/6/7) whose own injected drift is never reached — they fail *before* exercising what they test.
4. **M4 — message-order assertion**: `test_run7_historical_binding_rejects_repaired_driver_without_calls` (tests/test_run7_scope_escalation.py:115) and the second half of `test_run8_dry_run_is_zero_call_and_historical_binding_is_separate` (tests/test_run8_scope_escalation.py:108) assert the specific message `"Run 7 driver binding mismatch"`; the validator check runs first (`scripts/zth_run4a_intervention_calibration.py:172` before `:192`), so the error now reads `"Run 7 validator binding mismatch: local_harness/supervised_attempt_output_validator.py"`.

### Non-family failures (three independent causes)

| Test | Failures | Root cause |
|---|---|---|
| `tests/test_transaction_handoff.py` | 2 | `local_harness/transaction_handoff.py` executed directly as a CLI cannot import `local_harness.*`: commit `a32d0b5` (2026-09-03, "Add verified handoff context compaction") introduced the file's first package-absolute import (`from local_harness.evidence_semantic_typing import ...`, line 14) without the repo-root `sys.path` bootstrap its sibling `local_harness/run_manual_supervised_attempt.py` has (line 21). Current production regression. |
| `tests/test_long_duration_dogfood_scripts.py` | 1 | `test_tick_once_creates_run_dir_and_summary` (line 182) asserts `summary["branch"] == "dogfood/overnight-20260718"`, a hard-coded July 2026 campaign branch (ref still exists; tip `6083dc1`, 2026-07-20). The snapshot is a `git clone --local` of the current repo (line 66-67), whose HEAD is on `main`; the tick script faithfully records the actual branch (`scripts/zth_long_duration_dogfood_tick.sh:288`). Stale environment-coupled expectation. |
| `scripts/test_explicit_interface_direct_unit_calibration_v2_execution_harness.py` | 3 | Frozen V2 execution harness pins `"expected_codex_cli_version": "codex-cli 0.146.0"` (`docs/research/EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_EXECUTION_HARNESS_FREEZE_2026-08-24.json:26`); installed CLI is `codex-cli 0.152.1`; `validate_external_mechanism` correctly refuses. Expected environment drift. (The V3 freeze pins no codex version; its tests pass.) |

## History

### Frozen state

- `3ca42dfc...` is the file state introduced by `b83ddb6` (2026-07-08, "Validate supervised attempt target authority") and unchanged through the freeze window: no commit touched the file between 2026-07-08 and 2026-08-30 (verified via `git log --follow`).
- All seven preregistrations were created and last touched on 2026-08-19/20, i.e. **before** the validator changed, and each experiment was executed and closed in that window:
  - RUN_4: frozen `591dcb0` (+ same-day pre-execution hardening `f8e8a95`); recorded `b3ad77c`
  - RUN_4A: frozen `50fdb2e` lineage (`eca143c`, `65a805f`, `15dd84c`, all 2026-08-19); closed `53bb707`
  - RUN_4B: preregistered `b50bc0e`, hardened `b32ff64`; closed `b79ef5e`
  - RUN_5: prepared `4116676`, hardened `5497bbc`; closed `a96bade`
  - RUN_6: prepared `8bf19f3`; closed `beaee09`
  - RUN_7: prepared `7b5685e`, repaired `6ff7570`, preserved `da438c3` (all 2026-08-20); closed `8976d66`
  - RUN_8: frozen `b326244`; closed `a7ee03e`
- **Post-freeze mutation audit**: `git log` on each of the seven prereg JSONs shows the last touch ≤ 2026-08-20. Nothing modified them after the validator drift. The frozen digests are internally correct: they match the actual file bytes at freeze time (`git show b83ddb6:local_harness/supervised_attempt_output_validator.py | sha256sum` = `3ca42dfc...`).

### Changing commits (all after closeout, 2026-08-30/31)

| Commit | Date | Subject | Validator delta | Qualified |
|---|---|---|---|---|
| `ec091c8` | 2026-08-30 | Enforce held-target preservation and prompt projection | +45 lines | tests in same commit |
| `d7d66f7` | 2026-08-30 | Harden evidence budgeting and observation validation | +241 lines; new `schemas/repo_observation_output_schema.json` | tests in same commit |
| `a205456` | 2026-08-30 | Make observation validation separate from target authority | +9/-1 | (refactor of same-day work) |
| `1e76a28` | 2026-08-31 | Support explicit observation schema selection | +46/-9 | tests in same commit |
| `4d5181f` | 2026-08-31 | Fix epistemic observation contract dispatch | +2 | tests in same commit |

These are intentional, test-accompanied feature commits on a live production module (manual supervised attempts / observation validation), touching only `local_harness/`, `tests/`, `schemas/`, and `docs/MANUAL_SUPERVISED_MODEL_ATTEMPT.md` — no `docs/research` frozen evidence. Current digest `255d121b...` = state at `4d5181f`.

### Repo precedent for the correct pattern

- `da438c3` (2026-08-20, "Preserve Run 7 historical preregistration") established the separation contract when a driver changed post-freeze: `RUN_7_ESCALATION_PATH_REPAIR_FREEZE_2026-08-20.json` records `historical_run7` vs `repair` bindings side by side; `test_run7_historical_binding_rejects_repaired_driver_without_calls` asserts the historical prereg **rejects** current code; current code is exercised only through `_repair_validation_preregistration()`, a `/tmp`-derived copy of the payload with the driver digest updated (tests/test_run7_scope_escalation.py).
- Run 8's test `test_run8_dry_run_is_zero_call_and_historical_binding_is_separate` follows the same shape.
- The 2026-08-24 freeze family records this validator under `source_provenance` with role `design_or_historical_validator_lineage` / `"historical model-free output validator; required fields/types without exact-key rejection"` (e.g. `DELEGATION_PREDICTION_PROSPECTIVE_FREEZE_V2_2026-08-24.json:37`, `DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json:101-103`) — a non-asserted lineage role, which is why those suites pass unchanged.

## Classification

| Cause | Failures | Classification | Rationale |
|---|---|---|---|
| Run 4–8 validator binding mismatch | 75 measured / 74 reported | **expected historical drift** (evidence layer) carried by a **stale executable test expectation** (test layer) | Frozen preregs correctly detect that the current implementation differs from the frozen experiment. The five changing commits are intentional and qualified; the experiments are closed; the frozen digests are internally correct and must not be updated. The red tests are stale in expecting closed historical experiments to keep live-validating against current mutable code — the repo's own Run 7/Run 8 precedent shows the intended separation. |
| `transaction_handoff` CLI import | 2 | **unintended production drift** | Regression introduced by `a32d0b5` (2026-09-03): first package-absolute import in a directly-executed CLI module, missing the sibling scripts' repo-root `sys.path` bootstrap. Not historical; current bug. |
| Dogfood branch assertion | 1 | **stale executable test expectation** (environment-coupled) | Test hard-codes a transient July 2026 branch; the snapshot mechanism (`git clone --local` of current repo) can only reproduce it while HEAD sat on that branch. The tick script is faithful. |
| Explicit-interface V2 harness codex pin | 3 | **expected environment drift** (subclass of expected historical drift) | Frozen harness binds the external mechanism identity `codex-cli 0.146.0`; installed CLI is 0.152.1; the frozen check correctly refuses. The repository did not drift; the environment did. |
| Evidence corruption / inconsistency | 0 found | none | Preregistrations untouched since ≤ 2026-08-20; frozen digests match freeze-time file bytes; A/B run at the pre-fix clean HEAD reproduced the same failure set, ruling out the capability-loop test fix as a cause. |

## Recommended remediation (smallest correct next slice)

**Run 4–8 family — test layer only, Run 7 pattern, no re-freeze:**

1. In each Run 4–8 test file, add a local derived-prereg helper mirroring run7's `_repair_validation_preregistration()`: copy the frozen prereg payload to `/tmp` and update **only** the digests of post-freeze-changed bound artifacts (the output validator) to current values. All execution-semantics tests (dry-runs, stub executions, resume/corruption tests) use this derived, non-historical prereg. The seven frozen files remain byte-identical.
2. Keep one explicit historical-rejection assertion per family: the frozen prereg must reject the current tree, with the error naming `local_harness/supervised_attempt_output_validator.py`.
3. Fix the two message-order assertions (tests/test_run7_scope_escalation.py:115, tests/test_run8_scope_escalation.py:108) to expect the validator mismatch (validators are checked before the driver at `scripts/zth_run4a_intervention_calibration.py:172` vs `:192`), since both driver and validator have now drifted.
4. Do **not** update any `3ca42dfc...` digest and do **not** re-freeze Run 4–8: they are closed historical experiments; re-freezing would falsify history.

Optional follow-up slice (separate authorization): a non-historical lineage freeze JSON (modeled on `RUN_7_ESCALATION_PATH_REPAIR_FREEZE_2026-08-20.json`) recording historical `3ca42dfc...` ↔ current `255d121b...` and the five qualifying commits, giving the historical/current distinction a durable home.

**Non-family causes (each a separate, small, non-evidence slice):**

- `transaction_handoff`: add the repo-root `sys.path` bootstrap to `local_harness/transaction_handoff.py` (same two lines as `run_manual_supervised_attempt.py:20-21`), or invoke it as a module. Trivial current-bug fix; touches no evidence.
- Dogfood: assert the snapshot's actual branch (derive from the snapshot) instead of the hard-coded `dogfood/overnight-20260718`.
- V2 harness codex: environment-qualified skip with an explicit reason when installed `codex-cli` ≠ frozen `0.146.0` (or pin the environment to 0.146.0). Do not touch the frozen harness or weaken `validate_external_mechanism`.

## Count reconciliation

- Reported full-suite (prior session, same HEAD): 3537 passed / 80 failed / 2 skipped / 12 subtests (implies 3619 collected).
- This diagnostic (two split runs, same HEAD): `tests/` 2986+78+2 = 3066 collected; `scripts/` + `local_harness/tests/` 546+3 = 549 collected, 12 subtests; combined 3532 / 81 / 2.
- Delta collected: +4 = `XX_backend/tests/test_validate_agent_run.py` (4 tests), outside my split scope, presumably collected by the prior root-level invocation.
- Delta failed: ±1 (one Run 4–8 family test: 74 reported vs 75 measured), consistent with order/environment dependence of driver CLI tests that use fixed `/tmp` output directories (e.g. `/tmp/run8-scope-dry`, `/tmp/run7-scope-dry`); not exactly reconciled because full-suite reruns are out of scope for this slice. Immaterial to the common-cause conclusion: 74 or 75, the entire family is explained by the single validator binding mismatch.

## Worker evidence (local models)

| # | Worker | Task | Result | Supervisor correction |
|---|---|---|---|---|
| 1 | 1.7B | Digest-timeline qualification (4 questions) | 3/4 correct; wrong digest→commit mapping (`c5b40a3`); did not name first changing commit | Correct answer `b83ddb6`, verified directly via `git show <c>:<file> \| sha256sum`; workers not trusted for precise table lookups |
| 2 | 1.7B | Shared-dependency identification (3 questions) | 3/3 correct: one mismatching bound file; one file can fail many test files via driver re-verification; "one shared change" not 74 defects | Matches supervisor analysis; no correction |
| 3 | 1.7B | Remediation mutation review (3 questions) | 2/3; Q1 wrongly answered "yes, frozen prereg is edited" | Correct answer: **no** — the Run 7 pattern writes only a `/tmp` copy; frozen `docs/research` files are read-only in this remediation |
| 4 | 30B (escalation of #1's failed sub-question) | Digest→commit mapping + first post-freeze change + consistency inference | 2/3; both mappings correct (`b83ddb6`, `ec091c8`); consistency inference wrongly "no" | Correct answer: **yes** — no commit touched the file between 2026-07-08 and 2026-08-30, so the frozen digest matched the freeze-time tree; frozen evidence is internally correct |

Raw worker transcripts preserved in `/tmp/zth_worker_evidence/` (q1–q4 prompts and responses).

## Explicit non-actions

No frozen hash updated. No preregistration or freeze artifact edited. No fixture regenerated. No integrity check weakened. No unrelated implementation modified. Nothing pushed. Remediation implementation awaits separate authorization.
