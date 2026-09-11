# Preregistration Re-basing Provenance — 2026-09-09

## Purpose

The seven frozen preregistrations dated 2026-08-19/20 bind harness, driver, and
validator sources by sha256. Between their freeze and 2026-09-09, three bound
sources changed on `main`. This document records the drift inventory, the
intentionality/compatibility verdict for each drift, and the rebasing operation
that produced the seven new 2026-09-09 preregistration files.

The old files are **preserved unchanged**. No frozen evidence, fixture pack, or
historical binding was modified or deleted.

## Drift inventory (verified against current tree at rebase time)

Exactly three bound paths drift, all 64-char sha mismatches:

| Bound path | Frozen sha256 | Current sha256 | Binds in |
| --- | --- | --- | --- |
| `local_harness/supervised_capability_loop.py` | `23b26115201d8cba17b9da659af72793654897803988e35e28210eba02af81be` | `9eeab61da48500b60546b806b6f576cba46a6ab9f33590492c511ef83716dc56` | `validators[0]` in all 7 preregs |
| `local_harness/supervised_attempt_output_validator.py` | `3ca42dfc6f683399752bfe4f5757b9edf4e7eafb09ac30166fe60e9f3beb0d27` | `255d121b8b4bd0157dea24123755c905af8f450a72af8ca564f2812f5f80c2e5` | `validators[2]` in all 7 preregs |
| `scripts/zth_run7_scope_escalation.py` | `f1bdac815109a2dce473529ae14ddc24d60b048b74f3268e25fa6f9d9b1ad547` | `e52511f73461a122b5849dc6ba661008b31567fd0ab0c629c5ba507bf7d92337` | `driver` in RUN_7 prereg only |

All other bound paths (drivers, reference-fact validator, fixture packs,
policy freezes, resource manifests) are undrifted and were left untouched.
Drift scan and per-run detail: `/tmp/dsh_drift_inventory.txt` (scan:
`/tmp/dsh_drift_scan.py`).

## Intentionality and semantic compatibility verdict

**Verdict: all three drifts are intentional, landed on `main` by normal commit
flow, and semantically compatible with the originally preregistered threads.
Re-baselining the bindings is authorized; no semantic drift is suspected.**

1. **Capability loop** — three post-freeze commits:
   - `2b0d3ec` (2026-09-07)
   - `a07d764` (2026-09-08)
   - `3f8e56a` (2026-09-08)

   Purely additive: +114 lines, zero removed lines. Introduces
   `binding_preflight.py` and opt-in kwargs/artifacts. Existing call
   signatures and frozen behavior are unchanged; the pre-frozen contract
   still executes identically for frozen inputs.

2. **Attempt output validator** — five post-freeze commits:
   - `ec091c8`, `d7d66f7`, `a205456`, `1e76a28`, `4d5181f`

   Hardening/restructuring: exactly 10 removed lines, all relocated. The
   observation-contract checks now live in `_is_observation_contract`
   (L266), `_is_epistemic_observation_contract` (L276), and
   `_check_observation_output` (L292), with epistemic validation delegated
   to `validate_epistemic_observation_output` (L590). The pre-frozen check
   functions still exist (L222, L432) and are still called (L613). No
   acceptance criterion was dropped or inverted.

3. **Run 7 driver** — repair commit `6ff7570` (2026-08-20 10:15) landed
   **before** the prereg freeze `da438c3` (2026-08-20 10:24). The RUN_7
   prereg's `driver.sha256` deliberately pins the **pre-repair** hash — this
   is the historical repair-freeze pattern, with the repaired hash pinned in
   the RUN_8 prereg's `repair_freeze.repaired_driver_sha256`
   (= `e52511f73461…`, matching the current tree). The RUN_7 file is
   therefore a historical artifact of a known, intentional mismatch.

## Rebase operation

For each of the seven old files, a new dated file was created in the same
directory by **surgical raw-text replacement** of the drifted sha256 strings
only (each old sha string occurs exactly once in its file, verified before
replacement). All other bytes — key order, formatting, historical blocks —
are preserved. JSON-level diff verification confirmed the exact expected key
changes and nothing else:

| New file (2026-09-09) | file_sha256 | Keys changed |
| --- | --- | --- |
| `RUN_4_ECONOMIC_ROUTING_PREREGISTRATION_2026-09-09.json` | `390197f1d62fa132c54f97caf956f3ba9cde7d01a24364b0a1330d3115ecc400` | `validators[0].sha256`, `validators[2].sha256` |
| `RUN_4A_PREREGISTRATION_2026-09-09.json` | `deab903d382767f7bc314ab12f6e5923ce199c6dace48e8eb52d81804db6c225` | same 2 |
| `RUN_4B_SCOPE_INTERVENTION_REPLICATION_PREREGISTRATION_2026-09-09.json` | `4996fa7611e70d29c0aa138c4772ac95a2c1e75915bdd72e47e7292513559907` | same 2 |
| `RUN_5_MIXED_ECONOMIC_ROUTING_PREREGISTRATION_2026-09-09.json` | `71c21cf36f48bbfa39e09db0f9b9c7ca5fff00a2b70837a671ebdcb6d715ed23` | same 2 |
| `RUN_6_VALIDATION_GATED_ECONOMIC_ESCALATION_PREREGISTRATION_2026-09-09.json` | `e7cfddcfcecb022c360f19dc352c5158d2dc8a73f1ca5be4ebf036380698c121` | same 2 |
| `RUN_7_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-09-09.json` | `963adc7c0d2db23bf13d72b4865da75b59aeab98b0bce1ec835d7cc796e31939` | same 2 + `driver.sha256` (repaired driver) |
| `RUN_8_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-09-09.json` | `7748d3f4e79657a62364b1a62a81e876abb289fc9df150934c02dcf89ed346f9` | same 2 only |

RUN_7 new file additionally pins `driver.sha256` to the repaired driver
(`e52511f73461…`) so that the repair-path validation context loads directly
against the current tree. Its historical facts are intact:
`pair_order.seed=20260826`, `fixture_pack.candidate_count=24`,
`fixture_pack.target_included_count=20`,
`fixture_pack.manifest_sha256=f708ce62…`.

RUN_8 new file: `historical_run7` block
(`preregistration_sha256=1c45ce7be83194d4adfb5cf1af6b04d90495712b6779956bc6f7691ac4055de6`,
`driver_sha256=f1bdac815109…`) and `repair_freeze` block are **byte-identical**
to the old file; the run8 driver sha (`b84937934071…`) is undrifted and
untouched.

## Why the old RUN_7 file stays historical

`tests/test_run7_scope_escalation.py::test_run7_historical_binding_rejects_repaired_driver_without_calls`
runs the **real** run7 driver subprocess against the **old** RUN_7 prereg and
asserts failure with `"Run 7 driver binding mismatch"` (returncode != 0).
That test documents the repair-freeze history and must stay red-on-mismatch:
its `PREREG` constant therefore continues to point at the 2026-08-20 file.
The 2026-09-09 RUN_7 file serves the repair-validation context path
(`_repair_validation_preregistration`), which now loads the rebased bindings
directly.

The old file's sha (`1c45ce7be831…`) and its pre-repair driver sha
(`f1bdac815109…`) are also asserted verbatim in
`tests/test_run7_scope_escalation.py` (L130-137) and
`tests/test_run8_scope_escalation.py` (L88-89) — both assertions target the
preserved old file / RUN_8's historical block and remain valid.

## Test re-pointing

Test constants re-pointed to the 2026-09-09 files (binding context only):
run4 `tests/test_run4_economic_routing.py`, run4a driver
`tests/test_run4a_driver.py`, run4a prereg
`tests/test_run4a_preregistration.py`, run4b
`tests/test_run4b_scope_replication.py`, run5
`tests/test_run5_mixed_economic_routing.py`, run6
`tests/test_run6_sequential_economic_routing.py`, run8
`tests/test_run8_scope_escalation.py` (its `HISTORICAL_PREREG` stays on the
old RUN_7 file). Run7 test: new constant `PREREG_CURRENT` added and used only
in `_repair_validation_preregistration()`; the historical `PREREG` constant
and the L128-137 sha assertions are unchanged.

## Preservation statement

- Old 2026-08-19/20 prereg files: **unchanged** (git-verified unmodified).
- `RUN_4A_COMPARATIVE_EVIDENCE_FREEZE_2026-08-19.json`,
  `RUN_7_ESCALATION_PATH_REPAIR_FREEZE_2026-08-20.json`,
  `RUN_4_RESOURCE_WEIGHTS_FREEZE_2026-08-19.json` and all policy/comparative
  freezes: undrifted, **unchanged**.
- No evidence, fixture pack, or historical binding was quarantined or deleted.
