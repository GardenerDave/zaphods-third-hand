# Preregistration Re-basing Provenance — 2026-09-14

## Purpose

The seven frozen preregistrations dated 2026-09-09 (themselves rebased from
the 2026-08-19/20 files, see
`PREREGISTRATION_REBASING_PROVENANCE_2026-09-09.md`) bind harness, driver, and
validator sources by sha256. Between the 2026-09-09 freeze (`3f8e56a`) and
2026-09-14, exactly one bound source changed on `main`:
`local_harness/supervised_capability_loop.py` (`validators[0]` in all 7
preregs). This document records the drift inventory, the
intentionality/compatibility verdict for each drift commit, and the re-freeze
operation that produced the seven new 2026-09-14 preregistration files.

The old 2026-09-09 files are **preserved unchanged**. No frozen evidence,
fixture pack, or historical binding was modified or deleted.

## Drift inventory (verified against current tree at re-freeze time)

Exactly one bound path drifts — a single 64-char sha mismatch per file:

| Bound path | Frozen sha256 (2026-09-09) | Current sha256 (HEAD `a348d13`) | Binds in |
| --- | --- | --- | --- |
| `local_harness/supervised_capability_loop.py` | `9eeab61da48500b60546b806b6f576cba46a6ab9f33590492c511ef83716dc56` | `2bdf2a501ce3fce24e45c3ff01250e1991beb5170cadf93b7ddf890242da975b` | `validators[0]` in all 7 preregs |

All other bound paths (drivers, attempt-output validator, reference-fact
validator, fixture packs, policy freezes, resource manifests, repair freezes,
comparative evidence freeze) are undrifted and were left untouched.

## Drift commits and verdict

Five commits landed on `local_harness/supervised_capability_loop.py` between
the 2026-09-09 freeze pin (`9eeab61da485…`, tree `3f8e56a`) and HEAD
(`2bdf2a501ce3…`, tree `4c6c54b`):

1. `70af18b` (2026-09-12) — `_parse_teacher` response normalization +
   regression tests + passing live evidence. Parser/normalization fix;
   compatible with frozen inputs (same parse outcomes for well-formed
   payloads).

2. `47cf409` (2026-09-12) — **deliberate experiment-contract fix**: the
   teacher retry prompt was leaking the reference answer
   (`corrected_reference_output` was replayed to the worker on retry). The
   guidance-only invariant now strips answer-bearing fields from the
   worker-facing retry prompt. This is not a compatible no-op: it changes
   what the worker sees on a retry pass, which is precisely the
   confound the capability-loop experiments must rule out.

3. `98020c6` (2026-09-14) — nested-fence JSON extraction fix in the teacher
   output parser. Parser/robustness fix; compatible.

4. `3b25799` (2026-09-14) — teacher-retry attribution + withholding of
   answer-bearing free-text: distinguishes `guidance_only` from
   `teacher_reference_rescue` (a pass where the worker effectively saw the
   answer is never credited as new worker capability), and
   `_strip_reference_bearing_free_text` removes reference-bearing
   `teacher_diagnosis` / `retry_guidance` / `failure_classification` text and
   all structured answer fields from the worker-facing prompt while keeping
   durable raw teacher files. Same contract family as `47cf409`; deliberate.

5. `4c6c54b` (2026-09-14) — idempotent restart for
   `infrastructure_error` (Contract A). Robustness fix (2 insertions,
   1 deletion); compatible.

**Verdict:** drift is intentional, landed on `main` by normal commit flow.
`47cf409` and `3b25799` are deliberate experiment-contract fixes in the
guidance-invariant family (the retry prompt must never carry the reference
answer, and answer-bearing rescue passes must not be credited as worker
capability); `70af18b`, `98020c6`, `4c6c54b` are
parser/robustness-compatible. Re-freezing the `validators[0]` binding is
authorized. No semantic drift beyond the recorded contract fix is present.

## Re-freeze operation

For each of the seven 2026-09-09 files, a new dated file was created in the
same directory by **surgical raw-text replacement** of exactly one sha256
string: `9eeab61da48500b60546b806b6f576cba46a6ab9f33590492c511ef83716dc56`
→ `2bdf2a501ce3fce24e45c3ff01250e1991beb5170cadf93b7ddf890242da975b` (the old
sha occurs exactly once per file, verified before replacement). All other
bytes — key order, formatting, historical blocks — are preserved. JSON-level
diff verification confirmed the exact expected key change and nothing else:

| New file (2026-09-14) | file_sha256 | Keys changed |
| --- | --- | --- |
| `RUN_4_ECONOMIC_ROUTING_PREREGISTRATION_2026-09-14.json` | `01eb5cd1887d928efb4cafce91c794ad4b74b61cef4cadbb879aa4960fe82bb0` | `validators[0].sha256` |
| `RUN_4A_PREREGISTRATION_2026-09-14.json` | `5578bc6a5b2ac71993987707628774828b6f3fe9f5d0d85a7c54ffc24db359f5` | `validators[0].sha256` |
| `RUN_4B_SCOPE_INTERVENTION_REPLICATION_PREREGISTRATION_2026-09-14.json` | `d3b28b7a92b3bccaa73e7bb6f712e29a82a18a590c21ac4f41ede732d31a2316` | `validators[0].sha256` |
| `RUN_5_MIXED_ECONOMIC_ROUTING_PREREGISTRATION_2026-09-14.json` | `0a8b01cc3a3d80011d71498bdafe1e62dbfb2423306a2fe839f538fde98f19fa` | `validators[0].sha256` |
| `RUN_6_VALIDATION_GATED_ECONOMIC_ESCALATION_PREREGISTRATION_2026-09-14.json` | `7f28966a7e167a440eb00c44e4f77cb27d4d9d8996a676fb703b8385e75eea66` | `validators[0].sha256` |
| `RUN_7_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-09-14.json` | `d79536903b0b8af6d0dddd37558668605e38825d1e3009be032fd8388ea38024` | `validators[0].sha256` |
| `RUN_8_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-09-14.json` | `c866c43b012ca0c20f467708506fe305b9680029101e4c79ea0e9a23974258e0` | `validators[0].sha256` |

No other pin in any file changed: each 2026-09-14 file is byte-identical to
its 2026-09-09 twin except for the single sha string, so `model_calls_made:
false`, all historical blocks (`historical_run7`, `repair_freeze`,
`pair_order` seeds, fixture-pack bindings) and all other validator/driver
pins are carried forward verbatim. All pins in the new files verify against
the current tree at `a348d13`.

## Test re-pointing

Test constants re-pointed to the 2026-09-14 files (binding context only):
run4 `tests/test_run4_economic_routing.py` (`PREREG`), run4a driver
`tests/test_run4a_driver.py` (`PREREG`), run4a prereg
`tests/test_run4a_preregistration.py` (`PREREG`), run4b
`tests/test_run4b_scope_replication.py` (`PREREG`), run5
`tests/test_run5_mixed_economic_routing.py` (`PREREG`), run6
`tests/test_run6_sequential_economic_routing.py` (`PREREG`), run7
`tests/test_run7_scope_escalation.py` (`PREREG_CURRENT` only; the historical
`PREREG` constant stays on the 2026-08-20 file and its sha assertions are
unchanged), run8 `tests/test_run8_scope_escalation.py` (`PREREG` only;
`HISTORICAL_PREREG` stays on the 2026-08-20 file).

## Preservation statement

- Old 2026-09-09 prereg files: **unchanged** (git-verified unmodified).
- Old 2026-08-19/20 prereg files and all policy/comparative/repair freezes:
  **unchanged**.
- No evidence, fixture pack, or historical binding was quarantined or
  deleted.
