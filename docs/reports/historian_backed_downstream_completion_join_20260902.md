# Historian-Backed Downstream Completion Join

- date: 2026-09-02
- status: closeout verified and committed
- task_session: `.work/agent_tasks/historian-backed-downstream-completion-join-bc1970e0b5`
- source_run: `.work/operational-dogfood-v2/live-cycle/20260902T191000Z/20260902T050813Z`
- successful_recipient_run: `.work/operational-dogfood-v2/live-cycle/20260902T191000Z-recipient-fixed`
- rejected_recipient_run: `.work/operational-dogfood-v2/live-cycle/20260902T191000Z-recipient`
- first_worker_model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- recipient_model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

## Why Historian influenced task selection

Live Project Historian `ask` queries were used to select the next bounded ZTH
objective instead of guessing. The queries surfaced the canonical records:

- `CLM-handoff-provenance-gap`
- `CLM-qualified-evidence-boundary`
- `MIL-1p7b-to-30b-authority-bound-handoff`
- `REV-authority-bound-semantic-handoff-separation`
- `REV-source-bound-transport-qualification-provenance`

The strongest actionable finding: ZTH already had a policy consumer for
handoff-completion references (`resolve_handoff_completion_reference(...)` in
`local_harness/evidence_semantic_typing.py`), but no deterministic producer
that joined the exact prepared handoff to the separately executed, validated,
reviewed downstream completion. That asymmetry — a consumer without a
producer — was the recorded provenance gap this work closed.

## Implementation summary

### Deterministic completion join

`local_harness/transaction_handoff.py` gained `build_handoff_completion(...)`,
which produces a `handoff_completion.json` artifact
(`zth.handoff_completion.v0.1`) joining:

- the source transaction (manifest schema, lifecycle `HANDOFF`, records);
- the exact prepared handoff (`handoff_packet.json` id and `prepared` status
  matched against the manifest records);
- the prepared continuation (`next_worker_continuation.md`, hashed);
- the recipient run (separate run directory, `recipient_run_manifest.json`
  schema, transaction id, recipient identity, continuation sha);
- the recipient prompt (sha-verified against the manifest, then proven
  byte-identical to the prepared continuation);
- the source transaction binding block (attempt/validation/decision/gate/
  handoff ids, run id, transaction id, source raw output sha);
- the downstream attempt (`supervised_model_attempt.json`: acquisition request
  provenance prompt sha, preserved raw output sha, model identity);
- the downstream validation (`output_validation.json`: `passed`, bound to the
  attempt);
- the accepted review decision (`review_decision.json`: `accepted`, bound to
  the attempt and validation).

`COMPLETE` is derived only after every binding check passes, and the source
transaction manifest is never modified — the join is a separate durable
record. The artifact refuses to overwrite an existing completion, and a small
CLI (`python3 local_harness/transaction_handoff.py complete-handoff ...`)
exposes the join as the operational front door.

### Read-only Historian context adapter

`local_harness/historian_context.py` gained `bind_historian_context(...)`,
which consumes a completed Historian `ask` query directory, validates the
recorded answer contract (`schema_valid`, `grounding_valid`,
`contract_valid`), preserves query identity and provenance (query id, result
sha256, retrieval corpus fingerprint/revision, query state), resolves every
cited record id uniquely against the canonical records tree, verifies each
record's frontmatter id, hashes each cited record file, and emits
`historian_context_<query_id>.json` plus a rendered markdown view
(`zth.historian_context.v0.1`). It fails closed on missing artifacts, an
invalid contract, unresolvable or ambiguous cited ids, frontmatter mismatch,
and overwrite unless explicitly permitted. A `bind` CLI mirrors the library
function.

## Authority boundary

- The Historian answer is stored as `advisory_answer` (with its own sha256);
  the cited canonical records are stored separately as `cited_records` with
  per-file sha256. Generated prose never becomes evidence or authority.
- The context artifact grants no execution, file modification, promotion,
  training, or lifecycle authority; boundaries are embedded in the artifact
  and the markdown rendering.
- The completion join is derived deterministic state, not model output and not
  review authority. It does not promote, merge, release, clean up, or train
  anything, and it claims nothing about broader model capability or
  repeatability.
- No model-generated content became authority-bearing anywhere in this diff:
  the completion artifact contains only deterministic bindings, hashes, and
  artifact references.

## Positive completion-join result (real V2 dogfood lineage)

Evidence recorded by the previous session against the real prior V2 lineage:

- source transaction: `orch_manual_20260902t050813z`
- source handoff: `manual_handoff_20260902t050939z`
- source continuation sha256:
  `c0a2e9e4dc34071e7e798050a12cf13b0179e4c32942af8021ef7d672c450886`
- accepted recipient prompt sha256:
  `c0a2e9e4dc34071e7e798050a12cf13b0179e4c32942af8021ef7d672c450886`
  (byte-identical to the prepared continuation)
- accepted recipient raw output sha256:
  `60701fe169ded382fdad14ad15f8dead73078ed826975f324869ed70a5fb99d7`
- first-worker model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- recipient model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

The successful recipient produced all required completion bindings
(separate recipient run, prompt/continuation byte identity, downstream
execution provenance, preserved raw output, passed validation, accepted
review) and the join derived `COMPLETE` without touching the source
transaction manifest.

## Negative fail-closed control

The earlier recipient run
(`.../20260902T191000Z-recipient`) used a prompt whose sha256
(`846a4922147d3e2b7ba771977d330881ad6f29bb63a8e9b096548cfd66d0cba5`) did not
equal the final prepared continuation hash, failed validation, and had no
accepted review decision. The completion join rejected it and wrote no
completion artifact. Fixture tests additionally lock in fail-closed behavior
for tampered prompts, non-continuation prompts, missing review, rejected
review, wrong source lifecycle, missing recipient manifests, recipient-run
self-joins, and completion overwrite attempts.

## Closeout verification (independent session)

- `python3 -m pytest tests/test_historian_context.py tests/test_transaction_handoff.py tests/test_run_manual_supervised_attempt.py -q`:
  **144 passed** (15 + 40 + 89).
- `python3 -m pytest tests/test_transaction_handoff.py -q`: **40 passed**
  (39 inherited from the implementation session plus one closeout-added
  regression test for the separate-recipient-run guard).
- `python3 -m pytest tests/test_historian_context.py -q`: **15 passed**.
- `python3 -m pytest tests/test_evidence_semantic_typing.py -q`: **16
  passed** — the produced completion artifact resolves through the existing
  `resolve_handoff_completion_reference(...)` consumer with
  `artifact_integrity`, `completion_detected`, `handoff_match`,
  `downstream_attempt_match`, `endpoint_match`, `model_match`, and
  `policy_usable` all true (also covered by
  `test_handoff_completion_is_policy_consumable`).
- `python3 local_harness/agent_task_session.py validate .work/agent_tasks/historian-backed-downstream-completion-join-bc1970e0b5`:
  **VALID**.
- `python3 local_harness/transaction_handoff.py --help`: works (subcommand
  `complete-handoff`).
- `git diff --check`: clean.

## Defects found and repaired during independent review

- The completion join did not structurally reject a self-join where the
  recipient run directory is the source run directory. Repaired narrowly: the
  join now requires the resolved recipient run dir to differ from the source
  run dir, with a regression test
  (`test_handoff_completion_fails_closed_when_recipient_run_is_the_source_run`).
  Attempt-id inequality was deliberately not used as the guard because attempt
  ids are second-resolution timestamps and genuinely separate runs within the
  same second can legitimately share one (see limitations).

## Broad-suite baseline comparison (disposition)

The implementation session reported: modified tree 2777 passed / 76 failed;
after stashing, clean baseline HEAD ran 2751 passed / 76 failed with an
identical failing set — i.e. the 76 failures pre-existed and the new work
added 26 passing tests and zero new failures. This closeout did not rerun the
full suite. Credibility was checked independently instead: the diff is purely
additive (the new symbols are referenced only by the new modules and tests),
all focused suites pass, and a pre-existing collection error exists unchanged
at HEAD (`tests/test_supervised_capability_loop.py` imports
`_request_provenance` from `local_harness/icm_call.py`, which does not define
it), consistent with a pre-existing failure set unrelated to this work.
Current collection on the modified tree: 2855 tests plus that one
pre-existing collection error.

## Limitations

- Attempt ids are second-resolution timestamps, so id-string uniqueness is
  not a proof of separation; separation is proven structurally (distinct run
  directories) plus by prompt/output provenance binding.
- The Historian context adapter binds record identity and sha256 at bind
  time; it cannot detect pre-bind tampering of canonical record content
  without an external hash anchor (the retrieval corpus fingerprint is
  preserved for cross-checking).
- The completion join verifies artifacts and hashes; it cannot re-execute the
  recipient model. It relies on the unchanged supervised runner having
  faithfully produced the recipient artifacts, which the join re-verifies
  against the actual files.
- One real positive lineage plus fixture evidence; no claim of
  arbitrary-task generalization, universal routing, or unattended operation.
- `COMPLETE` is derived state recorded in the completion artifact only; no
  automatic lifecycle promotion exists anywhere in this diff.

## Exact capability claim earned

ZTH can deterministically bind an exact prepared handoff to a separately
executed, validated, reviewed downstream recipient result and produce a
completion artifact compatible with the existing evidence-semantic consumer.
Historian can provide grounded canonical project context to ZTH through a
provenance-preserving advisory context artifact without transferring
authority to generated prose.

Not claimed: arbitrary autonomous handoff completion, universal model
reliability, automatic lifecycle promotion, human-independent review, or
Historian reasoner output as canonical authority.
