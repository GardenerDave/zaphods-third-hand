# Operator-Useful Development v1: Agent Task Session Execution and Review Records

- date: 2026-09-02
- status: implementation complete; execution evidence recorded (derived stage `executed`); human review pending; commit for preservation follows this report
- phase_workspace: `.work/operator-useful-development-v1`
- task_session: `.work/agent_tasks/add-agent-task-session-execution-and-review-reco-0d22aa0090`
- zth_baseline_head: `48d89939496aee716faa12f00fd0d346e699ebb5`
- historian_baseline_head: `0285c4de2f44e7a85f4d3d3bef5fe325538bb598`

## Why Historian influenced task selection

Live Project Historian `ask` queries were used to select the next bounded ZTH
objective instead of guessing. Five discriminating questions were asked against
the canonical corpus (48/48 canonical and projected records validated, retrieval
state current) and the materially relevant results were bound into phase-local
context artifacts via `local_harness/historian_context.py bind` (five artifacts
under `.work/operator-useful-development-v1/historian_context/`):

- `op-c21aac5c` — no session execution-evidence or status-recording mechanism
  has been attempted or rejected; the constraints are the authority/semantic
  separation, immutable raw output, and distinct grading/review/closeout
  decisions.
- `op-27990bfe` — the completion-join provenance gap the corpus records as open
  is already closed at HEAD (commit `48d8993`); the historically repeated
  operator interventions were harness defects since repaired.
- `op-0315d0cd` — model transport consolidation is heavily constrained by the
  source-bound, transaction-bound, fail-closed transport qualification
  revision; the V2 transport failure (unmeasured capability, zero retries) must
  not be repeated.
- `op-237fcb2e` — no consolidation of the ask-then-bind workflow has been
  attempted.
- `op-db0c884c` — no recorded decision note treats operator manual steps as
  the problem to solve; the boundaries any consolidation must preserve are
  transport qualification as a prerequisite, semantic capability separate,
  immutable raw output with deterministic authority binding.

The selection (`selection.json` in the phase workspace) weighed five
candidates. The chosen objective was candidate A: the Agent Task Session
execution/closeout evidence gap. Historian prevented two wrong choices
(transport consolidation this phase, and a handoff-repeatability repeat that
would be theater) and confirmed the chosen territory is genuinely open, with
the authority boundaries any implementation must preserve.

## The gap closed

Agent Task Sessions had a create/validate front door and nothing after it: the
packet stays `draft` forever, execution evidence was dropped ad-hoc into an
unvalidated `evidence/` folder, and review outcomes were recorded nowhere.
That is the missing middle of the eventual `zth task "<objective>"` lifecycle
(create -> execute -> record -> review -> closeout) and matches the ROADMAP
strategic-order item to reduce operator choreography and improve
task/status/review UX.

## Implementation summary

New sibling module `local_harness/agent_task_session_record.py` (model-free,
fail-closed, stdlib-only) plus `local_harness/tests/test_agent_task_session_record.py`.

### Execution evidence records

`record-execution <session>` writes `execution/execution_<stamp>.json`
(`zth.agent_task_session_execution_record.v0.1`):

- validates the base packet first and fails closed if invalid;
- requires exactly one recorded outcome per packet required check, in packet
  order (outcomes are recorded operator/agent input, not tool-verified
  results);
- binds each evidence file by resolved path, repo-relative path, size, and
  sha256;
- binds the record to the exact `task.yaml` sha256 at record time;
- carries fixed authority-boundary language in every record.

### Review decision records

`record-review <session>` writes `review/review_<stamp>.json`
(`zth.agent_task_session_review_record.v0.1`):

- requires execution evidence to exist first (fail closed);
- binds to a specific execution record (explicit) or the latest (recorded as
  such), carrying the bound execution record's sha256;
- records the decision (`accepted`/`rejected`/`revision_requested`),
  reviewer identity (recorded as supplied input, never tool-verified), and
  reason;
- requires a superseding decision to explicitly supersede the latest review
  id, producing an ordered chain.

### Extended validation and derived stage

`validate <session>` validates the packet plus every record:

- every execution record must match the packet's required checks exactly, in
  order; every bound evidence file must still exist with the recorded sha256
  and size; `task.yaml` must match the hash recorded at record time;
- review records must bind known execution ids, carry matching hashes, and
  form an unbroken supersede chain;
- derives the session stage `draft` -> `executed` -> `reviewed` plus the
  effective review decision, as recorded evidence, not lifecycle promotion.

Same-second record id collisions (execution or review recorded twice within
one clock second, common in fast rework loops) are handled deterministically
with a zero-padded `-NNNNNN` suffix that keeps lexicographic id order equal
to chronological order.

## Boundaries preserved

- `task.yaml` and every builder-generated packet file are never mutated; the
  packet remains a draft review packet and no authority is granted.
- Records are evidence, not authority; no merge, release, promotion, cleanup,
  deletion, or lifecycle authority is granted by recording.
- Review decisions are human-supplied records; reviewer identity is supplied
  input, not tool-verified identity.
- Outcomes are recorded input describing observed results; the recorder
  executes no checks, agents, shell commands, or Git operations.
- Privacy is preserved: records live untracked under `.work/`, and no tracked
  code hardcodes private absolute paths or the reasoner endpoint.

## Verification evidence

Focused and regression runs at the time of recording:

- `python3 -m pytest local_harness/tests/test_agent_task_session_record.py -q`
  — 30 passed (happy paths, packet immutability, fail-closed paths for
  missing/invalid sessions, outcome-count mismatch, blank outcomes, missing
  evidence files, evidence drift/deletion, task.yaml byte and content drift,
  tampered authority boundaries, stray files, review-before-execution, bad
  decisions, blank reviewer/reason, unknown execution ids, supersede-chain
  violations, same-second collisions, CLI coverage including JSON output).
- `python3 -m pytest local_harness/tests/test_agent_task_session.py local_harness/tests/test_repo_health_check.py -q`
  — 38 passed, 12 subtests passed (existing session surface unchanged).
- `python3 -m pytest tests/test_historian_context.py tests/test_transaction_handoff.py -q`
  — 55 passed (adjacent surfaces).
- Broad suites: `python3 -m pytest local_harness/tests/ -q` completed with
  **520 passed, 12 subtests passed** (no code changed after that run). The
  top-level `tests/` suite has a pre-existing collection defect:
  `tests/test_supervised_capability_loop.py` imports `_request_provenance`
  from `local_harness/icm_call.py`, which does not exist at baseline HEAD
  `48d8993` either (reproduced in a clean-baseline worktree). This change
  touches neither file.
- A broader comparison excluding that known-broken module ran to completion
  in the background after a tool/app interruption: modified tree
  **76 failed, 2778 passed, 2 skipped**; clean-baseline worktree
  **254 failed, 2597 passed, 5 skipped**. The worktree count is confounded by
  missing untracked `.work/` operational state that top-level tests depend
  on, and the preserved log tails hold final counts only, not failure lists.
  The modified tree's 76 failures match the clean-baseline failure count
  documented in the prior closeout report, so no evidence attributes those
  failures to this change.
- Live dogfood: this phase's own task session
  (`add-agent-task-session-execution-and-review-reco-0d22aa0090`) recorded
  its execution evidence through the new recorder: `record-execution` with
  one truthful observed outcome per packet required check (recorder suite
  30 passed; existing session suite 23 passed, 12 subtests; recorder CLI
  help exit 0; `git diff --check` clean), binding this report, the phase
  `selection.json`, `friction.json`, the recorder module, and its test file
  as sha256-bound evidence; `validate` then derived `stage=executed`.
- No review decision was recorded. Review records are human-supplied
  attestations, and the coding agent is not the human operator, so human
  review remains pending. This is the intended separation in action:
  execution evidence records mechanically while acceptance stays a separate
  human review action. `task.yaml` remains an immutable draft packet.

## Friction log

`.work/operator-useful-development-v1/friction.json` records six friction
entries, two of them negative results: the reasoner endpoint env var is not
persisted anywhere (first `ask` failed until it was supplied per command), and
same-second record id collisions (fixed with the suffix scheme). Recurring
operator glue measured this phase: five manual bind invocations for the ask
results and roughly eight commands of baseline ceremony.

Classified from those same six entries:

- REMOVABLE_GLUE — reasoner endpoint rediscovered and re-supplied per command
  (F1); five separate `bind` invocations with repeated absolute paths (F2);
  shell choreography to locate query ids and artifact directories (F2, F6);
  separate commands for selection, session creation, and validation (F3);
  and the friction this task itself removes — execution evidence previously
  had no formal record path.
- REQUIRED_SUPERVISION — choosing and approving the bounded development
  objective; final human review and acceptance; commit/merge/release
  decisions.
- USEFUL_VISIBILITY — Historian citations and provenance, allowed paths,
  required checks, execution evidence, diff and test results.
- BUG — same-second record id collisions before the collision-safe suffix
  fix (F4); the top-level test collection defect is pre-existing at baseline
  and out of scope for this change.

## Next steps

- Candidate B from `selection.json`: consolidate the ask-then-bind workflow
  into fewer operator steps (bind-many/bind-latest-N with one historian repo
  root).
- Candidate D from `selection.json`: a single baseline/status front door
  reporting ZTH and Historian state, as groundwork for the eventual
  `zth task` precondition check.
- Both are recorded as friction improvements in `friction.json`; neither is
  started by this change.

## Non-goals and risks

- No `zth task` front door, no ACP adapter, no generic worker abstraction, no
  transport changes, no Historian modifications (zero this phase, per the
  prefer-zero policy; nothing this session produced earns a canonical record).
- Recorded outcomes and reviewer identities are attestations, not verified
  facts; consumers must keep treating them as evidence, per the boundary
  language carried in every record.
- Evidence files bound by hash must remain byte-stable after recording;
  validation fails closed if they drift, and the operator records a new
  execution entry rather than editing bound evidence.
