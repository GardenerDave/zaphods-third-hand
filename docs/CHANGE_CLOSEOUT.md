# Change Closeout

Start here: [`README.md`](../README.md) -> [`docs/README.md`](README.md).

## What It Is

Change Closeout is the final review ritual for a completed or apparently
completed change. It produces a draft Markdown report so a human can check
behavior, validation, documentation, authority boundaries, reusable knowledge,
and follow-up work before deciding what happens next.

The first version includes:

- [`prompts/CHANGE_CLOSEOUT_PROMPT.md`](../prompts/CHANGE_CLOSEOUT_PROMPT.md),
  the compact supervised review contract;
- [`docs/templates/CHANGE_CLOSEOUT_TEMPLATE.md`](templates/CHANGE_CLOSEOUT_TEMPLATE.md),
  the blank human-copyable report;
- [`local_harness/change_closeout.py`](../local_harness/change_closeout.py), an
  offline scaffold builder for bounded source evidence.

## What It Is Not

Change Closeout is not an autonomous merge gate, auto-promoter, cleanup tool,
test runner, or authority source. It does not execute commands, modify the
reviewed change, delete evidence, merge files, promote lifecycle drafts, or
move lifecycle state.

Every generated report starts as `status: draft` with
`requires_human_review: true`. Promotion fields are recommendations only.

## Why Every Change Needs a Docs Pass

Implementation can change more than code. Commands, paths, flags, output
contracts, prompts, templates, examples, limitations, safety language, and
validation instructions can all become stale even when tests pass.

A Docs Pass explicitly checks:

- user-facing and operator documentation;
- root README and documentation-index links;
- prompt and template contracts;
- commands, flags, paths, and examples;
- known limitations and troubleshooting;
- validation instructions and safety boundaries.

`checked_no_change_needed` means those surfaces were reviewed and no edit was
needed. It must not mean “tests passed, so docs were assumed correct.”

## Relationship to Tool Maker

[`TOOL_MAKER.md`](TOOL_MAKER.md) extracts a reusable lifecycle draft from
messy workflow evidence. Change Closeout reviews a particular completed change
before wrap-up.

A closeout report can become source material for Tool Maker when it captures
reusable commands, checks, failure modes, decisions, or operating constraints.
Tool Maker drafts do not replace Change Closeout, and Change Closeout never
promotes a Tool Maker draft automatically.

## Lifecycle Promotion and Authority

Closeout prevents accidental authority creep by requiring an explicit review
of whether a change altered or blurred permission to execute, edit, merge,
promote, accept, delete, assign, or move lifecycle state.

`ready_to_promote` means only that the evidence appears ready for an authorized
human decision. The closeout report itself grants no authority and performs no
promotion.

## When to Use It

Use Change Closeout before treating a code, documentation, prompt, template,
workflow, report, or configuration change as wrapped. It is especially useful
when:

- behavior or an output contract changed;
- commands, flags, paths, examples, or validation steps changed;
- safety or role-authority language changed;
- the work produced reusable workflow knowledge;
- tests passed but manual or documentation review remains important;
- the implementation relied on a shortcut, operator memory, or incomplete
  evidence.

## Source Material to Review

Useful inputs include:

- the task or active job packet;
- implementation files and diffs;
- test output and manual smoke results;
- updated or potentially affected documentation;
- prompts, templates, examples, and configuration;
- review comments, failure logs, and operator notes;
- related Tool Maker lifecycle drafts.

Keep secrets and private evidence out of committed reports. Use `.work/`,
`/tmp`, or another operator-controlled location for private source bundles.

## Prepare a Closeout Scaffold

From the repository root:

```bash
python3 local_harness/change_closeout.py \
  --name "Tool Maker v1" \
  --out .work/change_closeouts/tool-maker-v1.md \
  docs/TOOL_MAKER.md \
  prompts/TOOL_MAKER_PROMPT.md \
  local_harness/tool_maker.py \
  local_harness/tests/test_tool_maker.py
```

The scaffold builder reads UTF-8 text files, records distinguishing source
labels and sanitized paths, full-byte SHA-256 hashes, and source/inclusion
statistics, embeds bounded source evidence, and refuses to overwrite an
existing report. It does not call a model or execute source commands.

Use `--max-source-chars` to control the total embedded character limit.
Truncation remains visible in each source record.

Files inside the repository use repository-relative source paths. Relative
external inputs retain a normalized relative label; absolute external inputs
use an `external/<path-marker>/<filename>` label so home paths are not copied
into the report. SHA-256 identifies the complete source bytes at scaffold
time, including bytes omitted from a truncated packet.

Paths and hashes improve provenance and distinguish duplicate basenames. They
do not remove secrets, classify sensitivity, or make private evidence safe to
publish. Sanitization and publication decisions remain human responsibilities.

## Review Honestly

- **Proud:** preserve decisions, abstractions, validation, safety boundaries,
  and patterns worth repeating.
- **Not proud:** surface discomfort without blame. Do not normalize lucky
  passes, brittle shortcuts, hidden manual work, or missing validation.
- **Simplify:** identify accidental complexity that can be made boring.
- **Retain:** preserve design-critical complexity that protects safety,
  provenance, reversibility, auditability, or human supervision.
- **Decide:** leave unresolved complexity for explicit human judgment.

The finished report remains evidence. A human decides whether the change is
accepted, promoted, followed up, or left as draft.
