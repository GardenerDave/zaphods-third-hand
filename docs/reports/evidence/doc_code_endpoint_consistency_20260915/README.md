# Evidence bundle: doc_code_endpoint_consistency_20260915

Task family: `doc_code_reconciliation`. Validator: `exact_json` (8 required
fields). This is a genuine ZTH-on-ZTH dogfood run: a 1.7B worker answering a
repository question whose answer is useful to current ZTH work — not a
capability demonstration.

## Useful repository finding (leads this closeout)

`docs/SUPERVISED_CAPABILITY_LOOP.md` lines 12–13 read:

> "The worker is normally the local 1.7B endpoint and the local teacher is
> normally the 30B endpoint."

The precise problem is that the documentation **conflates the current dogfood
deployment convention with the code fallback defaults**. The two are different
things, and the doc wording mixes them.

Code fallback defaults (the actual source of truth in code, no override):

| Fallback slot | Source | Resolved model |
|---|---|---|
| worker slot `"router"` | `supervised_capability_loop.py:726` env default, resolved via `icm_spec.py:23–27` | `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M` (3B) |
| local-teacher slot `"deep"` | `supervised_capability_loop.py:729` env default, resolved via `icm_spec.py:12–17` | `Llama-3.3-70B-Instruct-Q4_K_M.gguf` (70B) |

The `DEFAULT_WORKERS` spec table has exactly five slots: `deep` (Llama-3.3-70B),
`coder` (Qwen2.5-Coder-7B), `router` (Qwen2.5-3B), `handoff` (Qwen2.5-7B), and
`qwen3_8_27b` (Qwen3.8-27B-UD-IQ4_XS). None is 1.7B or 30B.

Current dogfood deployment (explicit overrides of the fallbacks, from the run
environment): the worker is actually the 1.7B
(`Qwen_Qwen3-1.7B-Q4_K_M.gguf`) and the local teacher is actually Qwen3.8-27B
(`Qwen3.8-27B-UD-IQ4_XS.gguf`).

Evaluating each doc claim against both axes:

| Doc claim (lines 12–13) | Matches code fallback? | Matches current dogfood deployment? | Assessment |
|---|---|---|---|
| worker is normally the 1.7B endpoint | **No** (fallback is `router` → 3B) | **Yes** (deployment overrides to 1.7B) | Wording describes the deployment convention, not the code fallback; not stale for the deployment but does not describe the fallback |
| local teacher is normally the 30B endpoint | **No** (fallback is `deep` → 70B) | **No** (deployment overrides to 27B) | Stale for the current deployment (teacher is 27B, not 30B) **and** not the code fallback (70B) |

**This is the useful repository finding, established independently of the
worker's pass/fail:** the doc's "30B teacher" wording is stale for the current
deployment (the deployed local teacher is 27B, and the code fallback is 70B),
and the "1.7B worker" wording, while matching the current dogfood deployment,
does not describe the code fallback (`router` → 3B). The fix should describe
the selection mechanism (explicit worker spec / environment configuration with
deployment overrides permitted) rather than assert fixed model sizes.

Reference values for the worker's own answer (all independently re-verified
against the live source): all four match/presence booleans are `false`;
`default_worker_slot` is `"router"`; `default_teacher_slot` is `"deep"`;
`default_worker_model` is `"Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"`;
`default_teacher_model` is `"Llama-3.3-70B-Instruct-Q4_K_M.gguf"`.

## Worker / routing capability assessment

Worker: 1.7B (`Qwen_Qwen3-1.7B-Q4_K_M.gguf`). Local teacher (reference-blind,
guidance-only, `routine`): 27B (`Qwen3.8-27B-UD-IQ4_XS.gguf`). The expected
reference output was **not** inlined in the worker prompt; the worker received
all evidence (doc lines 1–14, `icm_spec.py` lines 11–60,
`supervised_capability_loop.py` lines 725–730) inlined.

Result: **failed** — 4/4 attempts parsed as valid JSON but 0/4 matched the
reference exactly. Terminal `review_state` / `disposition` is
`infrastructure_error` (driven by the external-teacher escalation, see
below), not a worker success.

### Per-attempt worker output vs. expected reference

| Field (expected) | a1 (none) | a2 (none) | a3 (local_teacher:1) | a4 (local_teacher:2) |
|---|---|---|---|---|
| worker_default_matches_doc_1_7b_claim (`false`) | true | true | **false** | **false** |
| teacher_default_matches_doc_30b_claim (`false`) | true | true | **false** | **false** |
| one_point_7b_model_in_table (`false`) | true | true | true | true |
| thirty_b_model_in_table (`false`) | **false** | **false** | true | **false** |
| default_worker_slot (`"router"`) | deep | deep | deep | deep |
| default_teacher_slot (`"deep"`) | **deep** | **deep** | **deep** | **deep** |
| default_worker_model (`Qwen2.5-3B…`) | Llama-3.3-70B… | Llama-3.3-70B… | Llama-3.3-70B… | Llama-3.3-70B… |
| default_teacher_model (`Llama-3.3-70B…`) | **Llama-3.3-70B…** | **Llama-3.3-70B…** | **Llama-3.3-70B…** | **Llama-3.3-70B…** |

(Bold = matches reference. `Qwen2.5-3B…` = `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`.)

Failure pattern (consistent across all 4 attempts): the worker latched onto
the most salient 70B entry and assigned it to **both** the worker and teacher
slots, answering `default_worker_slot = "deep"` and
`default_worker_model = "Llama-3.3-70B…"` every time. It never resolved the
worker slot to `router` / the 3B model, even after two rounds of prompt-patch
guidance. The local teacher's patches corrected the two doc-match booleans
(a3/a4 → `false`) but did **not** correct the slot/model lookup — the
recurring failure was resolving the multi-hop default-slot → worker-spec/model
relationship ("env default → spec-table slot → model" chain).

**Bounded negative precedent, not broad inability.** The evidence was actually
inlined, 4/4 1.7B attempts produced parseable JSON, and 0/4 matched the hidden
reference exactly — the recurring failure is specifically multi-hop
doc/code reconciliation across inlined code excerpts, not a general inability.
This is the counter-boundary to the Task 1 positive precedent (1.7B passed
single-diff 7-fact extraction first attempt, zero interventions). 27B guidance
improved some fields but did not rescue the task.

### Three-class failure classification (kept separate)

1. **Model-capability (root cause, genuine 1.7B gap):** worker resolved
   `default_worker_slot` to `"deep"` (the teacher's default) in all 4 attempts
   and answered the worker model as the 70B `Llama-3.3-70B…` in all 4; the
   table-presence booleans were wrong in every attempt
   (`one_point_7b_model_in_table: true` on all 4, where the reference is
   `false`; `thirty_b_model_in_table: true` on a3 only). Pattern: latches
   onto the most salient 70B entry and assigns it to both slots. Teacher guidance fixed the comparison
   booleans but not the slot/model lookup.
2. **Infrastructure (expected in this deployment):** after local-teacher
   exhaustion, the external-teacher escalation fired once but
   `ZTH_EXTERNAL_TEACHER_COMMAND` is unset →
   `external_teacher_infrastructure_error` (`adapter_identity:
   "codex-unconfigured"`, error `external teacher unavailable: ZTH_EXTERNAL_TEACHER_COMMAND
   is not configured`). This drives the terminal `review_state` /
   `disposition = infrastructure_error`. Not a framework bug.
3. **27B teacher truncation (teacher-side artifact):** `local-teacher-2.json`
   truncated at `max_tokens: 1200` (`finish_reason: "length"`, parse failed,
   unterminated string). `local-teacher-1.json` succeeded with a valid
   structured response (`failure_classification:
   "model_capability_insufficient"`) whose diagnosis matches the independent
   reading above. The loop handled the truncation gracefully; no validator or
   evidence-packaging failure occurred.

Note: the reference-blind local teacher's pass-1
`corrected_reference_output` (recorded in `candidate_curriculum_examples`,
`intervention_id: "local_teacher:1"`) independently reproduced the exact
expected reference object — confirming the reference is derivable and that the
worker's failure is a model-capability gap, not an under-specified prompt.

## Run environment (Task 1 & 2 identical)

`ZTH_PUBLIC_HOST_ALIAS=JARVIS_LOCAL`, worker
`Qwen_Qwen3-1.7B-Q4_K_M.gguf` @ `http://192.168.137.3:8081/v1`, local teacher
`Qwen3.8-27B-UD-IQ4_XS.gguf` @ `http://192.168.137.3:8080/v1`.

Terminal summary (see `trajectory_summary.json`): `pass: false`,
`review_state: "infrastructure_error"`, `model_attempt_count: 4`,
`teacher_pass_count: 2`, `external_escalation_count: 1`,
`teacher_intervention_mode: "guidance_only"`,
`successful_intervention_source: "none"`, `first_attempt_pass: false`.

## Provenance note

The `task_id` date suffix `20260915` reflects the authoring date and is kept
consistent with the Task 1 convention. The run itself actually executed on
**2026-09-14** (see `generated_at` and the trajectory transition
timestamps). This is a note, not a rename.

## Raw evidence

`genuine_raw_evidence/` holds the genuine raw artifacts. `archive_manifest.json`
records `zth_evidence_archive_v1` entries (archive_path / sha256 / size /
source_path).
