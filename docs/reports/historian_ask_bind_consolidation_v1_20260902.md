# Historian Ask-and-Bind Consolidation V1

- date: 2026-09-02
- status: implementation complete; execution evidence recorded (derived stage `executed`); human review pending; commit for preservation follows this report
- phase_workspace: `.work/historian-ask-bind-consolidation-v1`
- task_session: `.work/agent_tasks/consolidate-historian-ask-and-context-binding-2c423ca3c8`
- zth_baseline_head: `62c1e12b405f1ca86aebbebc77f2e96e3f8412b4`
- historian_baseline_head: `0285c4de2f44e7a85f4d3d3bef5fe325538bb598`

## Observed friction that motivated the work

The previous phase (`operator_useful_development_v1_20260902.md`, friction
entries F1/F2) measured the Historian query/context workflow as the largest
removable-glue cluster. For five materially relevant questions it took:

- 5 `historian.cli ask` commands, each with the reasoner endpoint manually
  supplied because `HISTORIAN_REASONER_ENDPOINT` is not persisted anywhere;
- 1 directory listing (`ls -t .work/historian_queries`) to discover which
  query ids the asks produced;
- 5 separate `historian_context.py bind` invocations, each manually supplying
  `--query-dir` (absolute, with the discovered id), `--records-dir` (absolute
  historian repo path), and `--out-dir`.

That is 11 commands and roughly 15 repeated path/id arguments for five
questions — pure ceremony between an already-supported query and an
already-supported binder.

## Implementation

Two new ZTH modules; Project Historian was not modified.

- `local_harness/historian_ask_runner.py` — a structured single-query runner
  executed by the Historian retrieval runtime (never by ZTH's interpreter),
  with the Historian repository as working directory and import root. It calls
  the supported `historian.ask.ask` service function and prints the full
  structured result as one JSON object on stdout.
- `local_harness/historian_context_query.py` — the operator front door.
  `ask-bind` accepts one or more `--question` values plus
  `--historian-repo` and `--output-dir`, and for each question: runs the
  runner through the bundled Historian retrieval runtime, captures the exact
  structured query identity, validates it, binds the exact query directory
  through the existing `historian_context.py` binder, and reports the result.
  The existing binder is reused unchanged; the
  `zth.historian_context.v0.1` artifact and its semantics are preserved.

## Provenance behavior

- The query id and the exact query directory are taken from the structured
  Historian service result (`request_id`, `runtime.request_dir`) — the
  identity of the query the operation itself just created.
- The wrapper never lists, sorts, or "newest-first" scans Historian work
  directories, so it cannot accidentally bind another process's query.
- The on-disk `query.json` must carry the same id and the same question as
  the returned result, and the request directory must exist inside the
  Historian query work root, before binding proceeds.
- The machine-readable summary returns query id, exact query directory,
  context JSON and Markdown paths, cited canonical record ids, retrieval
  corpus fingerprint, revision, and document count.

## Endpoint configuration

`--endpoint` takes precedence, then `HISTORIAN_REASONER_ENDPOINT`; with
neither, the command fails closed with an actionable message. The endpoint is
passed to the Historian subprocess through its environment, never through
argv, and never hardcoded in tracked source. The Historian retrieval runtime
defaults to the Historian repo's bundled runtime
(`interfaces/khoj/runtime/py312-cpu/bin/python`, the path Historian's own
README documents for live `ask`) and can be overridden with
`--historian-python`; a missing runtime fails closed with an actionable
message.

## Failure behavior

Fail closed, with no ZTH context artifact written, on: missing Historian
repo; missing `historian/service.py` or `records/`; missing retrieval runtime;
unconfigured endpoint; runner timeout; runner non-zero exit; non-JSON runner
output; missing request id or request directory in the result; request
directory outside the Historian query work root or missing on disk; query
artifact id or question mismatch; Historian `status != ok` (error code, text,
and preserved query directory are reported); binder failure; existing output
artifacts without `--overwrite`. Failed Historian query artifacts are
preserved for inspection. In multi-question mode the command stops at the
first failing question, reports which one failed alongside any already-bound
artifacts, and exits non-zero.

## Test results

- `python3 -m pytest tests/test_historian_context_query.py -q` — **28
  passed**: single ask→bind success; runner invocation shape (list argv, no
  shell); endpoint via environment (not argv) and explicit override; missing
  endpoint/repo/service-module/runtime fail closed before any subprocess;
  failed Historian result, non-JSON output, non-zero exit, timeout; missing
  request id ("refusing to guess") and missing request directory ("refusing
  to scan"); request directory outside the work root; missing directory on
  disk; id and question mismatches; decoy newer query directory is not bound;
  binder failure writes no artifact; overwrite refused then allowed; canonical
  records unmodified; multi-question separate artifacts; stop at first
  failure; CLI `--help`; two real-subprocess CLI tests through a stub runtime
  (success and Historian failure paths, the stub asserting the endpoint
  arrived via its environment).
- `python3 -m pytest tests/test_historian_context.py local_harness/tests/test_agent_task_session.py local_harness/tests/test_agent_task_session_record.py -q`
  — **68 passed, 12 subtests passed** (existing binder and session surfaces
  unchanged).
- `python3 local_harness/historian_context_query.py --help` — exit 0.
- `git diff --check` — clean.

## Real operational dogfood

One real question, asked and bound through the new front door only (no
manual ask, no query-id discovery, no separate bind):

> What operator friction remains after the first reviewed Operator-Useful
> Development task, and what historical decisions constrain consolidating
> that friction?

- query id: `op-3e297451-326a-40fc-9cd3-ad99bf32b6cc`
- bound query directory:
  `<historian-repo>/.work/historian_queries/op-3e297451-326a-40fc-9cd3-ad99bf32b6cc`
- cited canonical records: `CLM-docs-index-dogfood-completed-after-harness-fixes`,
  `REV-authority-bound-semantic-handoff-separation`,
  `REV-source-bound-transport-qualification-provenance` (all resolve in the
  48-record corpus)
- context artifacts:
  `.work/historian-ask-bind-consolidation-v1/evidence/historian_context_op-3e297451-326a-40fc-9cd3-ad99bf32b6cc.{json,md}`
- provenance: schema `zth.historian_context.v0.1`, query state `COMPLETE`,
  retrieval corpus fingerprint
  `e1dfd851253843077af52593459255bd8f5763196c88c4b4698f57bb295236e5`,
  revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 48 documents
- the Historian repository remained clean (query artifacts are untracked
  `.work` state); no canonical record was modified

## Before/after manual-step count

For this specific workflow, measured:

| | Before (previous phase, 5 questions) | After (this phase) |
|---|---|---|
| commands | 11 (5 ask + 1 listing + 5 bind) | 1 (`ask-bind`) |
| query-id discovery steps | 1 listing serving 5 ids | 0 |
| path arguments | ~15 (5 absolute query dirs, 5 absolute records dirs, 5 out dirs) | 2 (`--historian-repo`, `--output-dir`) |
| endpoint supplies | 5 (once per ask command line) | 0 with env exported once per shell, or 1 `--endpoint` flag |

For a single question: 3 commands (ask, discovery, bind) → 1 command. No
exaggeration is intended: the endpoint must still be configured once per
shell (or passed per command), and the output directory is still chosen by
the operator — both remain deliberate supervision points rather than
removed ceremony.

## Authority boundary

The Historian answer remains advisory interpretation over evidence; the
cited canonical records remain the evidence. A successful query is not
approval. A successful bind is not approval. The wrapper grants no
execution, file-modification, lifecycle, promotion, training, or review
authority; it does not modify Project Historian or its canonical records;
and it never self-records review decisions. Human review remains a separate,
required step.

## Limitations

- The reasoner endpoint is still one manual configuration act per shell
  environment (export) or per command (`--endpoint`); it is deliberately not
  persisted or hardcoded anywhere.
- Multi-question mode runs questions sequentially and stops at the first
  failure; there is no `--questions-file` input and no merged index artifact
  (each question yields only its own independent context artifact).
- The wrapper targets the current Historian CLI/service shape
  (`historian/service.py`, structured `query()` result, bundled runtime path);
  a future Historian interface change would surface as a fail-closed error
  here rather than silent misbinding.
- Failed query artifacts are preserved but not summarized anywhere beyond the
  error message.

## Exact capability claim

ZTH can now, with one supervised command per set of questions, run supported
Project Historian ask queries, capture each query's exact structured identity
(request id and request directory) without directory scanning, validate that
identity against the on-disk query artifacts, and bind each exact result
through the existing ZTH Historian binder into unchanged
`zth.historian_context.v0.1` evidence artifacts — fail-closed on every
failure path, with the reasoner endpoint configurable via environment or CLI
and never hardcoded.
