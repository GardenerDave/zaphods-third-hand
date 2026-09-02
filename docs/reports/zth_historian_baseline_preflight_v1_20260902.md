# ZTH + Historian Baseline Preflight V1

- date: 2026-09-02
- status: implementation complete; focused tests pass; real-repo dogfood
  observed (pre-commit run fails closed by design on this session's own
  uncommitted files; post-commit clean-baseline re-run protocol recorded
  below); execution evidence recorded (derived stage `executed`); human
  review pending; commit for preservation follows this report
- phase_workspace: `.work/zth-historian-baseline-preflight-v1`
- task_session: `.work/agent_tasks/add-zth-historian-baseline-preflight-829a2e8bfc`
- zth_baseline_head: `1eba43f38c574fcac95d1da8a5e2799360613a0f`
- historian_baseline_head: `0285c4de2f44e7a85f4d3d3bef5fe325538bb598`

## Observed ceremony that motivated the work

Before this phase, confirming the operational baseline for the two
repositories before any phase or handoff took eight distinct commands, each
repeated by hand and each able to be skimmed past when output looked
"familiar":

- 2x `git status --short` (one per repository);
- 2x `git rev-parse HEAD` (one per repository);
- 1x `python3 -m historian.cli validate` (canonical record validation,
  through the Historian runtime);
- 1x `python3 -m historian.cli validate-projection` (projected retrieval
  record validation);
- 1x an explicit retrieval-state check through the bundled runtime
  (`historian.retrieval.validate_state` over the state manifest and the
  loaded corpus); and
- 1x an ad-hoc staleness determination comparing observed counts/HEADs
  against phase expectations kept in the operator's head.

That is eight commands with no shared exit code, no single report, and no
fail-closed behavior: a skimmed `git status` or a mis-counted validation
could pass unnoticed.

## Implementation

Two new ZTH modules; Project Historian was not modified.

- `local_harness/zth_preflight_historian_runner.py` — a structured
  baseline-validation runner executed by the supported Historian retrieval
  runtime (never by ZTH's interpreter). It imports the existing
  `historian.cli.validate` and `historian.cli.validate_projection`, performs
  the retrieval-state currency check, and prints exactly one JSON object on
  stdout. Validation failures are reported as structured fields (never as
  prose to parse and never as silent successes); the runner exits 0 whenever
  its report was produced and exits non-zero only for usage errors.
- `local_harness/zth_preflight.py` — the operator front door. It observes
  both repositories through structured Git subprocesses
  (`rev-parse --git-dir`, `rev-parse HEAD`,
  `status --porcelain=v1 -z --no-renames`; no shell, no string assembly),
  resolves the Historian runtime (bundled
  `interfaces/khoj/runtime/py312-cpu/bin/python` by default,
  `--historian-python` to override), runs the runner once, and renders the
  result as human text (default) or `--json`
  (`zth.historian_baseline_preflight.v1`).

Commands and flags:

```bash
python3 local_harness/zth_preflight.py \
  --historian-repo /path/to/project-historian-v1
```

- `--zth-repo` (default: the repository containing the module — derived,
  not a hardcoded machine path);
- `--historian-repo` (required, explicit);
- `--historian-python` (optional runtime override);
- `--expect-zth-head`, `--expect-historian-head`, `--expect-record-count`
  (optional explicit expectations; omitted means report-only — phase
  expectations are never hardcoded in the tool);
- `--timeout` (runner timeout, default 120 s);
- `--json`.

Exit code 0 means every requested invariant was observed; anything else
exits 1.

## Retrieval-state currency semantics

The runner classifies retrieval state as exactly one of `current`, `stale`,
`missing`, or `invalid`, fail-closed:

- `missing` — `interfaces/retrieval/state/manifest.json` or
  `interfaces/retrieval/state/embeddings.npy` is absent (the state is
  incomplete, so retrieval cannot run);
- `invalid` — the manifest is unreadable/non-JSON/non-object, is missing
  required keys (`corpus_sha256`, `corpus_files`, `dimensionality`,
  `document_count`, `encoder_revision`, `record_ids`), the embeddings file
  cannot be loaded or its shape does not match the manifest's
  `document_count`/`dimensionality`, `historian.retrieval` cannot be
  imported, or state validation fails for a non-drift reason;
- `stale` — Historian's own `validate_state(manifest, docs)` raises
  `RetrievalStateMismatch` (corpus fingerprint, document count, ordered
  record mapping, or pinned encoder revision drifted from the state);
- `current` — only when the manifest matches the live corpus under
  Historian's fingerprint check and the embeddings artifact is consistent.

Nothing is inferred from file timestamps. Stale or invalid state is never
silently rebuilt: the tool is an observer, and the error text points at the
supported rebuild path rather than performing it.

## Failure behavior

Every failure mode exits 1 with an actionable error and a per-check record
(`checks` in JSON; `Failures (N):` in human output):

- missing repo path; path is not a directory; not a usable Git repository;
  no commits on HEAD; `git status` failure; unparseable status output
  (refused, never guessed);
- dirty worktree with the exact changed paths surfaced (status code and
  path per entry);
- HEAD or record-count expectation mismatch (expected vs. actual);
- canonical or projected validation failure (Historian's own assertion text
  surfaced);
- canonical/projected count disagreement, or agreement unverifiable because
  a validation failed;
- retrieval state `stale`, `missing`, or `invalid` (with the underlying
  reason);
- unsupported Historian runtime (no bundled runtime and no
  `--historian-python`, or a non-executable override);
- runner subprocess failure: non-zero exit (with stderr tail), timeout,
  launch failure, non-JSON output, non-object JSON, or a malformed report
  section (fail-closed on schema violations, never silently ignored).

A dirty Historian worktree still receives the full validation report (both
facts are reported — the operator sees the complete picture in one run).

## Checks performed

- `python3 -m pytest tests/test_zth_preflight.py -q` — 60 passed.
- `python3 -m pytest tests/test_historian_context_query.py
  tests/test_historian_context.py
  local_harness/tests/test_agent_task_session.py
  local_harness/tests/test_agent_task_session_record.py -q` — 96 passed,
  12 subtests passed (no adjacent regressions).
- `python3 local_harness/repo_health_check.py` — docs links PASS; privacy
  FAIL and boundary-language FAIL are pre-existing at the baseline HEAD
  (22 RFC1918 findings under `docs/research/`, one `auto-promote` claim in
  `docs/DOGFOOD_RUNNER.md`); this session introduced none (session files
  live outside the public-surface scan; `docs/reports/` is excluded by the
  health check itself).
- `git diff --check` — clean.

## Real dogfood

Run against the actual repositories, before the phase commit (evidence:
`.work/zth-historian-baseline-preflight-v1/evidence/preflight_pre_commit_human.txt`
and `preflight_pre_commit.json`):

- ZTH: HEAD `1eba43f…`, worktree dirty with exactly this session's two new
  untracked module files — the preflight correctly failed closed
  (`PREFLIGHT: FAIL`, exit 1) with the exact paths surfaced, which is the
  required behavior for a dirty clean-baseline precondition.
- Historian: HEAD `0285c4d…`, worktree clean, runtime
  `interfaces/khoj/runtime/py312-cpu/bin/python`, canonical 48, projected
  48, counts agree, retrieval `current` — every Historian baseline check
  passed through the real bundled runtime in the same single command.
- Neither repository was modified by the run (the runner subprocess runs
  with `PYTHONDONTWRITEBYTECODE=1` so not even `__pycache__` entries are
  written into the observed repository).

Post-commit protocol: after the phase commit makes the ZTH worktree clean
again, the same command is re-run once; that observation (expected: full
`PREFLIGHT: PASS` at the new commit) is recorded as a second execution
evidence entry in the task session rather than predicted here.

## Before/after ceremony count

- Before: 8 distinct commands/operations per baseline check (2x git status,
  2x git rev-parse HEAD, canonical validation, projection validation,
  explicit retrieval-state check, ad-hoc staleness determination).
- After: 1 command (`python3 local_harness/zth_preflight.py
  --historian-repo <path>`), one report, one exit code, fail-closed.

## Boundaries and capability classes

Boundary language shipped in the tool (docstring, human output footer, and
JSON `boundaries` array): observer only; grants no execution,
file-modification, commit, merge, lifecycle, review, promotion, or training
authority; a PASS is not permission to act; neither repository is modified;
a dirty worktree is a failed precondition, not a defect this tool fixes.

Capability classes by verb:

- Read: Git state, record validation counts, retrieval-state manifest,
  embeddings metadata, runner report.
- Validate: structural validation of inputs it consumes and outputs it
  renders.
- Report: human and `--json` reports with per-check results.
- Grant: nothing. Modify: nothing. Repair: nothing. Schedule: nothing.

## Tests and coverage

`tests/test_zth_preflight.py` — 60 tests, including parametrized cases:

- clean happy path (human + JSON + exit codes), exact check sequence;
- every fail-closed case listed above, each with its actionable error
  asserted (missing/non-git repos, dirty trees with exact paths, unborn
  HEAD, git status failure/unparseable output, git launch failure,
  canonical/projection failures, count mismatch, `stale`/`missing`/
  `invalid` retrieval, unsupported runtime, runner non-zero exit/timeout/
  launch failure/non-JSON/non-object/malformed sections, expectation
  mismatches);
- runner module behavior through real subprocesses against stub Historian
  packages (current, stale, validation failures, missing artifacts,
  malformed manifests, embeddings shape mismatch, corrupt embeddings,
  foreign-package guard, usage errors);
- read-only behavior: tree digests before/after a full real-subprocess run
  prove neither repo is mutated;
- CLI end-to-end with a real runner subprocess and stub runtime;
- a deliberate negative control (`test_negative_control_real_git_fixture_fails_closed`)
  against real temporary Git fixture repositories through the real command
  path — dirty ZTH fixture fails closed with exact paths while the
  Historian fixture reports its full baseline and remains clean afterwards;
- a scope guard asserting no phase HEADs or the 48-record count are
  hardcoded in either module.

## Limitations

- The preflight observes state; it does not and must not fix it (stale
  retrieval state still requires the supported explicit rebuild).
- Git observation requires the `git` binary; its absence is reported as a
  fail-closed launch error.
- The embeddings consistency check requires numpy inside the resolved
  Historian runtime; an interpreter without it is reported as `invalid`
  retrieval state (fail-closed), not guessed around.
- Expectation flags compare full 40-hex HEADs and integer counts only; they
  are policy inputs, not stored baseline state.
- The tool checks the two repositories it is pointed at; it does not watch
  for concurrent mutations between observation and any later action.

## Claim

One read-only command now reports and fail-closes the full ZTH + Historian
baseline; it grants no authority and modifies nothing.
