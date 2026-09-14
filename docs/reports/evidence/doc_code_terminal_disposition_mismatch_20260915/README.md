# Evidence — terminal-disposition contract vs executable behavior (shape-d)

**Date:** 2026-09-15
**Task id:** `doc_code_terminal_disposition_mismatch_20260915`
**Task family:** `doc_code_reconciliation`
**Shape:** (d) contract-vs-executable-behavior mismatch
**Verdict:** **CONFIRMED, live-reproduced.** A doc-vs-code contract divergence with a concrete behavioral consequence (non-idempotent restart).
**Loop run disposition:** `infrastructure_error` (external teacher unconfigured, by design)

---

## 1. Repository finding (primary)

`docs/SUPERVISED_CAPABILITY_LOOP.md` and `local_harness/supervised_capability_loop.py`
disagree on the set of terminal dispositions, and the disagreement breaks the doc's
idempotency claim.

### Doc contract

- `docs/SUPERVISED_CAPABILITY_LOOP.md` **L27** — *"Existing terminal summaries make a
  restart idempotent; prior failed artifacts are retained."*
- **L44** (state diagram) — the terminal edge is `-> ready_for_review | unresolved`,
  i.e. the doc names **only two** terminal outcomes.
- **L57-58** (external-teacher boundary) — *"Missing, empty, timed-out, or non-zero
  commands fail closed to `unresolved` and preserve the diagnostic."*

### Code executable behavior

- `local_harness/supervised_capability_loop.py` **L40** —
  `TERMINAL_DISPOSITIONS = {"ready_for_review", "unresolved"}` (excludes a third value).
- **L1009** —
  `disposition = "ready_for_review" if final_pass else "infrastructure_error" if external_infrastructure else "unresolved"`.
  A run whose external teacher is an infrastructure failure ends in **`infrastructure_error`**,
  a value the doc never names.
- **L715-717** — the restart idempotency short-circuit fires only when
  `summary.get("disposition") in TERMINAL_DISPOSITIONS`. Because `infrastructure_error` is
  **not** in that set, an `infrastructure_error` summary is **not** skipped on restart and is
  **re-executed**.

### One-sentence mismatch

The document names only `ready_for_review` and `unresolved` as terminal dispositions and says
external-teacher infrastructure failure "fails closed to `unresolved`", but the code can also end
a run in `infrastructure_error`, which is absent from `TERMINAL_DISPOSITIONS`, so a run ending in
`infrastructure_error` is not treated as terminal on restart and is re-executed instead of skipped.

### Live reproduction (this run)

The run in this bundle ended `disposition: infrastructure_error` (external teacher unconfigured:
`ZTH_EXTERNAL_TEACHER_COMMAND is not configured`). That is exactly the state the doc's
idempotency claim (L27) does not cover. Re-running the same fixture against the same out-dir now
re-executes from scratch rather than short-circuiting, contradicting L27.

### Consequence

- The doc's "terminal summary ⇒ idempotent restart" guarantee is false for the
  `infrastructure_error` state.
- Any operator workflow that relies on "restart is idempotent" will silently re-run
  infrastructure-error runs (re-incurring model/teacher cost), or a future change that adds
  `infrastructure_error` to `TERMINAL_DISPOSITIONS` would silently alter restart semantics.

### Remediation options (not applied here; code is out of scope for this evidence bundle)

- **Fix the doc** to name `infrastructure_error` as a terminal disposition and to state whether
  it is (or is not) idempotent on restart, and to correct L57-58 (external infra failure does not
  "fail closed to `unresolved`" — it closes to `infrastructure_error`).
- **Or fix the code** by adding `infrastructure_error` to `TERMINAL_DISPOSITIONS` if the intended
  contract is that such runs are terminal-and-skipped.
  The two must be reconciled to one consistent contract.

---

## 2. Capability / routing evidence (secondary)

Full supervised loop ran genuinely. The 1.7B worker outcome is a **model-capability failure** —
not packaging, validator, or infrastructure.

| Stage | Model / spec | Transport | Outcome |
|---|---|---|---|
| Worker | `Qwen_Qwen3-1.7B-Q4_K_M.gguf` @ `http://192.168.137.3:8081/v1` (openai-chat, `router`) | `model_response` ×4 (genuine, no timeout/request error) | **failed** ×4 (valid JSON, wrong extraction) |
| Local teacher | `Qwen3.8-27B-UD-IQ4_XS.gguf` @ `http://192.168.137.3:8080/v1` (openai-chat, `qwen3_8_27b`) | reference-blind, `guidance_only` | **correct** (byte-identical to hidden `expected_output`) |
| External teacher | codex | unconfigured by design | terminal `infrastructure_error` (expected) |

### Why the 1.7B failed (precise)

All 4 attempts passed `json_parse` and failed only `reference_output_exact_match`. Attempt 1
correctly read the doc side but missed the code's third disposition and inverted the mismatch:

| field | expected | got (attempt 1) |
|---|---|---|
| `doc_terminal_dispositions` | `["ready_for_review","unresolved"]` | ✅ same |
| `code_terminal_dispositions` | `["infrastructure_error","ready_for_review","unresolved"]` | `["ready_for_review","unresolved"]` ✗ (missed `infrastructure_error`) |
| `code_value_absent_from_doc` | `"infrastructure_error"` | `"unresolved"` ✗ |
| `in_terminal_set` | `false` | `true` ✗ |
| `idempotent_return_on_infrastructure_error` | `false` | ✅ same |
| `external_infra_disposition` | `"infrastructure_error"` | `"unresolved"` ✗ |
| `doc_external_failure_close_matches_code` | `false` | `true` ✗ |
| `mismatch_summary` | (names the non-idempotent-restart consequence) | inverted — claimed doc/code disagree about `unresolved` ✗ |

The 27B teacher, working reference-blind, produced the byte-exact reference
(`candidate_curriculum_examples[0].corrected_reference_output == expected_output`), proving the
task is well-posed and solvable from the inlined evidence alone. The 1.7B failure is therefore a
genuine capability boundary, not a leaky or broken fixture.

### Deployment note (env-only, no code change)

The live 27B is an **openai-chat** endpoint, so the correct teacher spec is `qwen3_8_27b`
(openai-chat, `base_url …/8080/v1`). The legacy `deep` spec is **native-completion** (only
accepts `spec.url`), which is incompatible with the openai base_url override and raises
`ValueError: deep is missing a completion URL`. Selecting `qwen3_8_27b` via
`ZTH_CAPABILITY_TEACHER_NAME` is deployment configuration of an already-supported spec — no
framework machinery was changed.

---

## 3. Fixture integrity (leak-free)

- Worker prompt byte length: **8491** (fixture == `attempt-1.prompt.txt`, identical).
- The worker is **tool-less**; all evidence is inlined as code/doc excerpts.
- The required 8 field **names** are present in the prompt (required for the worker to emit the
  schema).
- The hidden **answer artifacts are absent**: the two sorted disposition lists and the
  `mismatch_summary` prose are all `False` (not present). The scalar strings `infrastructure_error`
  and `false` do appear, but only inside the **inlined code excerpt** (the L1009 line literally
  contains `"infrastructure_error"`), which is the required evidence, not a leak of the answer.

---

## 4. Artifacts

| file | content |
|---|---|
| `README.md` | this file |
| `fixture.json` | task fixture (prompt, hidden `expected_output`, `exact_json` validator) |
| `build_fixture.py` | generator that built `fixture.json` (with leakage checks) |
| `trajectory.jsonl` | full per-event loop trajectory (worker attempts, teacher passes, external failure, transition) |
| `trajectory_summary.json` | `supervised_capability_trajectory_v2` summary (disposition `infrastructure_error`) |
| `attempt-{1..4}.prompt.txt` | exact worker prompt per attempt (byte-identical) |
| `attempt-{1..4}.raw.json` | raw 1.7B worker output per attempt |
| `attempt-{1..4}.validation.json` | deterministic `exact_json` validation per attempt |
| `attempt-{1..4}.metadata.json` | request provenance / transport per attempt |

### Live endpoints (deployment, not code)

- Worker 1.7B: `http://192.168.137.3:8081/v1` — `Qwen_Qwen3-1.7B-Q4_K_M.gguf` (openai-chat).
- Local teacher 27B: `http://192.168.137.3:8080/v1` — `Qwen3.8-27B-UD-IQ4_XS.gguf` (openai-chat, spec `qwen3_8_27b`).
- External teacher: unconfigured (`ZTH_EXTERNAL_TEACHER_COMMAND` unset) → terminal `infrastructure_error`.

---

## 5. Failure classification (per binding rule)

- **1.7B worker failure = model-capability** (valid JSON every time; wrong extraction; consistent
  inversion across 4 attempts). Not packaging, not validator, not infrastructure.
- **External teacher `infrastructure_error` = expected by design** (unconfigured). It is the
  exact disposition the doc mismatch concerns.
- **No framework machinery changed.** The run fix was env-only (`ZTH_CAPABILITY_TEACHER_NAME=qwen3_8_27b`).
