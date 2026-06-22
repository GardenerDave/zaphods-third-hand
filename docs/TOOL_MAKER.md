# Tool Maker

Start here: [`README.md`](../README.md) -> [`docs/README.md`](README.md).

## What It Is

Tool Maker is a supervised, workflow-to-lifecycle distiller with a
model-free scaffold builder. It helps turn a messy successful or partially
successful workflow into a reusable lifecycle draft made from plain Markdown
evidence.

Tool Maker is part of the informal [`Vogon Printer`](VOGON_PRINTER.md) family.
The family name is navigation only; Tool Maker remains a distinct lifecycle
draft workflow with its own contract.

The first version has three parts:

- [`prompts/TOOL_MAKER_PROMPT.md`](../prompts/TOOL_MAKER_PROMPT.md), the compact
  extraction contract for Codex, Aider, or a supervised local agent;
- [`docs/templates/TOOL_LIFECYCLE_TEMPLATE.md`](templates/TOOL_LIFECYCLE_TEMPLATE.md),
  the blank human-authored template;
- [`local_harness/tool_maker.py`](../local_harness/tool_maker.py), an offline
  scaffold builder that combines bounded source material with lifecycle
  sections.

## What It Is Not

Tool Maker does not run the captured workflow, execute source commands, call a
model, activate a job packet, delete evidence, or promote a lifecycle. It does
not turn a successful run into automatic authority.

Its output starts as `status: draft` and requires human review. Humans decide
whether to edit, test, reject, retain, or promote that draft.

## How It Fits ZTH

- **Context Distiller** summarizes broad transcripts and prepares review
  patches. Tool Maker focuses specifically on extracting a replayable
  operational lifecycle.
- **Model auditions** can supply useful logs, commands, validations, and
  failures. Tool Maker does not score or promote models.
- **Agent packets** authorize a particular supervised task. A tool lifecycle is
  reusable guidance, not execution authority. A later job packet must still
  define scope, allowlists, verification, and stop conditions.

## Source Material

Useful source bundles combine operator intent with observed evidence:

- terminal transcripts with command output;
- chat transcripts;
- failed-run notes;
- reviewed git diffs;
- test logs;
- screenshots summarized as notes;
- operator reflections about what mattered.

Weak source material includes:

- only a final answer;
- commands without output;
- logs without the human's intent;
- a success claim without validation.

Do not include secrets. Keep private source bundles under `.work/`, `/tmp`, or
another operator-controlled location unless they have been reviewed for
publication.

## Prepare a Lifecycle Scaffold

From the repository root:

```bash
python3 local_harness/tool_maker.py \
  --name "Local provider smoke workflow" \
  --out .work/tool_lifecycles/local-provider-smoke.md \
  path/to/chat.md \
  path/to/terminal.log \
  path/to/operator-notes.md
```

The script:

- validates and reads one or more UTF-8 text or Markdown files;
- records distinguishing source labels and sanitized paths, full-byte SHA-256
  hashes, and byte, character, line, inclusion, and truncation counts;
- embeds a bounded source packet;
- writes the required lifecycle headings and draft metadata;
- refuses to overwrite an existing output file;
- does not contact a model or execute any captured command.

Use `--max-source-chars` to lower or raise the total embedded character limit.
Truncation is recorded per source so missing evidence remains visible.

Generated scaffolds declare
`scaffold_contract_version: "tool-lifecycle-v1"`. Files inside the repository
use repository-relative source paths. Relative external inputs retain a
normalized relative label; absolute external inputs use an
`external/<path-marker>/<filename>` label so absolute home paths are not copied
into the scaffold. SHA-256 identifies the complete source bytes at scaffold
time, including bytes omitted by truncation.

Validate a generated scaffold with:

```bash
python3 local_harness/validate_scaffold.py \
  --kind tool-lifecycle \
  .work/tool_lifecycles/local-provider-smoke.md
```

Validation checks the declared contract, required headings, enum-like fields,
source metadata shape, source counts, hashes, labels, totals, and truncation
consistency. It reads only the scaffold; original source files are not
required.

Validation does not prove that source evidence or lifecycle claims are true,
safe, complete, sanitized, or promotion-ready. Source labels and hashes improve
provenance but do not remove secrets or make private evidence safe to publish.
A human must still review the draft and sanitize anything selected for sharing.

## Fill and Review the Draft

Give a supervised agent the generated scaffold together with
[`prompts/TOOL_MAKER_PROMPT.md`](../prompts/TOOL_MAKER_PROMPT.md), or complete
the sections manually with the blank template.

During review:

1. Compare each claimed step and result with the source evidence.
2. Preserve failed-but-important attempts and unknowns.
3. Preserve strengths, decisions, validation, and safety boundaries that made
   the workflow effective.
4. Surface brittle shortcuts, hidden manual steps, lucky outcomes, and other
   evidence that made the operator uneasy without assigning blame.
5. Decide whether complexity is accidental and should be simplified,
   unresolved and needs human judgment, or design-critical because it protects
   safety, provenance, reversibility, auditability, or human supervision.
6. Check commands for private paths, credentials, destructive effects, and
   environment assumptions.
7. Verify that validation checks distinguish attempted work from proven
   success.
8. Keep destructive actions, cleanup, publication, acceptance, and lifecycle
   movement behind explicit authorized approval.

This reflection is a lifecycle-hardening mechanism, not a blame ritual. Pride
identifies what should be preserved, discomfort identifies what must not be
hidden, and simplification review identifies what can be made boring without
damaging the design.

## Safe Promotion

Promotion means a human has accepted a lifecycle draft as reusable guidance.
It is not model promotion and does not authorize execution.

Before promotion, a human should:

1. resolve or explicitly retain open questions;
2. replay the workflow in a bounded environment when practical;
3. verify commands, rollback guidance, artifacts, and validation checks;
4. sanitize private evidence;
5. choose the canonical destination and approve the change through the normal
   job-packet and review process.

The scaffold builder and extraction prompt never perform this promotion.

## Relationship to Change Closeout

[`CHANGE_CLOSEOUT.md`](CHANGE_CLOSEOUT.md) reviews a completed change before it
is considered wrapped. Tool Maker extracts reusable lifecycle knowledge from
messy evidence; Change Closeout checks whether one change has adequate
validation, documentation, safety review, and follow-up.

A closeout report may become Tool Maker source material. A Tool Maker draft
does not replace closeout review, and a closeout recommendation does not
promote a lifecycle draft automatically.
