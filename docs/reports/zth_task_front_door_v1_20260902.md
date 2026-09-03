# Supervised ZTH Task Front Door V1

- Date: 2026-09-02
- Status: implemented and tested; the first dogfood preparation attempts
  blocked at the Historian stage and are preserved (see the Dogfood section);
  the insufficiency-outcome repair landed, and the dogfood rerun completed
  end to end — executed with recorded evidence, human review pending
- Scope: add `local_harness/zth_task.py`, a single supervised front door that
  composes existing proven mechanisms into one bounded workflow from an
  ordinary-language objective to a validated, context-backed, execution-ready
  Agent Task Session, plus the smallest generic extension to
  `local_harness/agent_task_session.py` needed to carry context references
  and non-goals
- Non-goals: no new lifecycle implementation, no second task-packet format,
  no new coding-agent client, no model-worker routing, no execution
  authority, no automatic commit, merge, release, promotion, cleanup, or
  review

## Motivation

Before this phase, the supervised task workflow was correct but scattered.
An operator who wanted to do one bounded task with evidence had to run, in
order and by hand:

1. `zth_preflight.py` to observe the two-repository baseline;
2. `historian_context_query.py ask-bind` for each relevant question;
3. `agent_task_session.py new` with hand-assembled scope and checks;
4. `agent_task_session.py validate`;
5. an external coding agent with a hand-copied prompt;
6. `agent_task_session_record.py record-execution` and, later,
   `record-review`.

Each step was fail-closed and auditable, but nothing tied the steps
together, nothing preserved the ordinary-language objective or the semantic
proposal that motivated the scope, and nothing answered "where is this task
now?" without re-reading private folders. This phase composes those
mechanisms behind one front door without changing any of them.

## Design

`zth_task.py` (stdlib-only, model-free except one strictly contracted
interpretation call) provides three subcommands and a bare-objective
default:

- `prepare "<objective>"` — baseline preflight (composed from
  `zth_preflight.run_preflight`), verbatim objective preservation,
  advisory semantic interpretation, Historian ask-and-bind (composed from
  `historian_context_query.ask_and_bind_many`), deterministic scope binding
  into a validated Agent Task Session (composed from
  `agent_task_session.create_task_session` / `validate_task_session`), and
  an operator-facing summary;
- `status <task-id>` — task state derived from durable artifacts, never
  from a mutable status flag;
- `handoff <task-id>` — the exact validated agent prompt path plus the
  exact `agent_task_session_record.py record-execution` command the
  returned evidence belongs with.

Key decisions:

- **Composition, not re-implementation.** The front door imports and calls
  the existing preflight, ask-and-bind, packet, and record modules. No
  mechanism was forked; `agent_task_session.py` received only a backward-
  compatible optional-fields extension (below).
- **Interpretation is advisory and fail-closed.** One OpenAI-compatible
  chat-completion call (JSON-schema response format, temperature 0, seed 42)
  proposes a bounded interpretation under an exact contract (`goal`,
  `candidate_allowed_paths`, `non_goals`, `required_checks`,
  `historian_questions` 0–5, `reasoning_summary`, `uncertainties`). Any
  unknown field — including any authority-bearing field such as
  `execution_authority`, `approved`, or `auto_commit` — fails closed and is
  recorded, not ignored.
- **Deterministic scope binding.** ZTH, not the model, decides the final
  packet. Candidate paths must be repository-relative, existing files (or
  new files under existing directories), and must not be wildcards, `.git`,
  private/ignored evidence roots (`.work`, `outputs`, `sources`), private
  configuration, or secret material. Any held candidate blocks preparation
  and is preserved in the failure record. Required checks are recorded
  instructions, never executed by the front door.
- **State is derived, never stored.** `status` reconstructs
  `created` → `context_bound` → `ready_for_execution` → `executed` →
  `reviewed` (showing the actual recorded decision) from the workspace
  artifacts and the existing session/record validators. A preserved failure
  yields `blocked` with the failing stage. Missing or corrupt artifacts fail
  clearly instead of guessing. If a recorded session or its bound evidence
  no longer validates, status reports `blocked` with the reason rather than
  claiming execution.
- **Failures are preserved.** Every preparation failure writes
  `failure.json` (stage, error, and for interpretation failures the raw
  model output) inside the task workspace; workspaces are never overwritten,
  auto-repaired, or deleted.
- **Historian context is evidence, not decoration.** The interpreter's
  proposed questions (0–5, only questions whose answers would change the
  task) are asked once through the consolidated ask-and-bind; the packet's
  context references point at the bound context artifacts and their index,
  which record cited canonical record ids and the retrieval corpus
  fingerprint.

### Minimal `agent_task_session.py` extension

Task packets can now carry optional `non_goals` and `context_references`
(repo-relative advisory evidence pointers). Both fields are omitted entirely
when empty, so every previously creatable packet remains byte-identical and
all pre-existing validations, prompts, and ids are unchanged. Validation
fails closed on present-but-empty lists, unsafe reference syntax, or
duplicate entries. This is the generic carrying capacity the front door
needed; it does not change the packet contract version.

## Implementation

- `local_harness/zth_task.py` (new): front door module (~700 lines),
  including the interpretation contract, deterministic scope policy,
  artifact-derived status, and CLI.
- `local_harness/agent_task_session.py`: optional `non_goals` /
  `context_references` support in `create_task_session`, `derive_task_id`,
  `render_task_metadata`, `render_prompt`, and `validate_task_session`;
  `--non-goal` and `--context-ref` CLI flags; shared repo-relative path
  normalization helper.
- `tests/test_zth_task.py` (new): 34 focused tests covering preparation
  success and every fail-closed path, the interpretation contract (including
  authority-field rejection), Historian integration (forwarded questions,
  bound provenance, failure blocking), scope binding (escape, wildcard,
  secret, private-root, and nonexistent-parent rejection), status/resume
  (state derivation, corrupt/missing artifacts, real-recorder execution and
  review discovery, evidence-drift detection), authority boundaries, and
  the interpreter HTTP contract (mocked transport).
- `local_harness/tests/test_agent_task_session.py`: 5 new tests for the
  optional-fields extension (omitted-by-default byte compatibility,
  recorded-and-rendered fields, unsafe reference rejection, empty-list
  validation rejection, CLI flags).
- `local_harness/README.md`: front-door documentation.

## Verification evidence

Development used its own bounded Agent Task Session packet
(`add-supervised-zth-task-front-door-89200c0e66`, created and validated before
implementation, 7 allowed paths, 3 required checks). All required checks
passed. Two execution records were made against that packet with the four
changed code/test files bound by path, size, and sha256:
`execution_20260902t231858z` (initial verification) and
`execution_20260902t232942z` (final pre-commit re-run on the exact committed
tree, after the scope correction described below). The final outcomes:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
  tests/test_zth_task.py local_harness/tests/test_agent_task_session.py
  local_harness/tests/test_agent_task_session_record.py -q` —
  **117 passed, 12 subtests passed in 0.79s**;
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
  tests/test_zth_preflight.py tests/test_historian_context_query.py
  tests/test_historian_context.py -q` — **103 passed in 1.97s** (composed
  modules unchanged in behavior);
- `git diff --check` — no findings.

Additional bounded verification beyond the packet:
`local_harness/tests/test_repo_health_check.py` — **15 passed**;
`python3 local_harness/repo_health_check.py --docs` — links **PASS** over
554 tracked Markdown files; boundary-language **FAIL** remains exactly the
one pre-existing `docs/DOGFOOD_RUNNER.md:51` finding documented in the
prior baseline report (a docs wording defect, unrelated to this change,
addressed separately below through the front door's first real task). The
known pre-existing privacy findings under `docs/research/` and the known
pre-existing `tests/test_supervised_capability_loop.py` collection defect
are unchanged and unrelated to this change. No live model or Historian
call was made by any test: the interpreter call, preflight, and ask-and-bind
were injected fakes.

Session records validate (`stage=executed`, 2 executions, review pending —
execution evidence is not acceptance). A commit for preservation follows
this report.

Scope correction disclosure: during documentation, two brief
`docs/ARCHITECTURE.md` review notes were drafted before it was noticed that
`docs/ARCHITECTURE.md` is outside this packet's allowed paths. The edits
were reverted immediately, all packet checks were re-run on the corrected
tree, and the second execution record discloses this. The architecture
review notes are applied afterwards under their own bounded packet with
their own checks and commit. No other out-of-scope file was touched.

## Before/after friction

- Before: six hand-run commands across four tools, hand-assembled scope,
  no preserved objective or semantic proposal, no resumable state, prompt
  copied by hand.
- After: one `prepare` command preserves the objective verbatim, gathers
  evidence, proposes and deterministically binds scope, validates the
  packet, and prints the operator summary; `status` answers "where is this
  task?" from artifacts; `handoff` emits the exact agent prompt and the
  exact evidence-recording command. The same boundaries apply as before —
  nothing is executed, accepted, or committed by the tooling.

## Boundaries

- Task preparation grants no execution authority; a validated packet is
  review material, not permission to act.
- The semantic interpretation is advisory model output; ZTH binds
  authority-bearing facts deterministically and rejects authority-bearing
  model fields rather than ignoring them.
- The Historian answer is advisory interpretation over evidence; the cited
  canonical records remain the evidence.
- A passing preflight is an observation, not authorization; execution
  evidence is not acceptance; a commit is not acceptance.
- `zth_task.py` executes no required checks, performs no Git operations,
  commits nothing, and grants no merge, release, promotion, cleanup, or
  lifecycle authority. Human review remains a separate, required step for
  every prepared task.

## Limitations

- The interpreter contract is strict: unknown fields fail closed, which
  also rejects benign model additions; the contract is explicit and
  versioned so the model prompt can be tuned without weakening validation.
- Candidate paths must be existing files or new files under existing
  directories; wholesale new directories are refused rather than guessed.
- `status` re-validates the session packet and records on every call, so
  deliberately tampered or drifted evidence surfaces as `blocked` rather
  than as a stale state.
- V1 emits the packet for an external coding agent (`handoff`); it does
  not itself invoke Aider, an ACP adapter, or any other coding-agent
  runtime. Reusing an existing supported execution path remains future
  work, as does scope for multi-path, multi-step, or dependency-aware
  tasks.
- Context references are advisory pointers recorded in the packet; the
  durable, hash-bound provenance lives in the task workspace's historian
  index and the bound context artifacts, and `.work/` remains disposable
  private state.

## Dogfood

The front door's first real use is one genuine maintenance task — the
pre-existing repo-health boundary-language defect in
`docs/DOGFOOD_RUNNER.md` (a "must not" list bullet that reads as a positive
auto-promotion claim outside the checker's negation window). The first
preparation attempts ran with a live reasoner endpoint and the real Project
Historian, and blocked at the Historian stage: the Historian returned
contract-valid advisory answers (`schema_valid`, `grounding_valid`, and
`contract_valid` all true) that honestly cited zero canonical records, and
the strict binder correctly refused to bind them as evidence. Those blocked
attempts are preserved under `.work/zth_tasks/zth-task-fix-the-pre-existing-*`
as failure workspaces; the wording of this report section originally
described the dogfood as already executed, which was wrong, and this section
now records the blocked attempts instead.

The follow-up repair (`zth.historian_insufficient_context.v0.1`) classifies
each question as bound, insufficient, or failed — preserving zero-citation
contract-valid answers as separate non-bound artifacts while true failures
still block. The dogfood was then rerun through the front door exactly once:

- preparation reached `READY_FOR_EXECUTION` in one pass
  (`zth-task-fix-the-pre-existing-rep-3542b8f2`): preflight PASS, 3 Historian
  questions asked, 3 bound, 0 insufficient, 0 failed, 15 canonical records
  cited, session validated;
- execution changed exactly one line in exactly the one allowed file
  (`docs/DOGFOOD_RUNNER.md:51`: `- auto-promote a model or result` became
  `- never auto-promote a model or result`, so the prohibition carries its
  own negation inside the checker's negation window);
- verification: the three packet-required checks pass, `repo_health_check.py
  --docs` reports docs links PASS (555 tracked files) and boundary language
  PASS with zero findings (the pre-existing finding is gone), and
  `git diff --check` is clean;
- execution evidence is recorded
  (`modify-the-boundary-language-in-docs-dogfood-run-f67ac277e7`, stage
  `executed`, 1 execution); execution evidence is not acceptance, and human
  review remains pending.

## Exact capability claim

`local_harness/zth_task.py` can, as a supervised operator command: run the
read-only two-repository baseline preflight; preserve an ordinary-language
objective verbatim in a private task workspace; obtain one advisory,
strictly contracted semantic interpretation from an operator-configured
OpenAI-compatible endpoint; ask that interpretation's proposed questions
through the consolidated Project Historian ask-and-bind and bind the cited
evidence; deterministically validate the proposed scope against a fail-closed
path policy; create and validate a draft Agent Task Session carrying goal,
allowed paths, required checks, non-goals, and context evidence references;
derive resumable task state from durable artifacts including recorded
execution and review evidence; and emit the exact agent handoff packet and
evidence-recording command. It cannot execute tasks or checks, invoke a
coding agent, commit, merge, release, promote, clean up, accept evidence,
grant authority, or replace human review.
