# Sanitization Notes

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

## What Was Intentionally Excluded

The public package should not include:

- Private transcripts.
- Raw conversation exports.
- Generated run records from a private project.
- Generated review patches from a private project.
- Session summaries from a private project.
- Local machine logs.
- Cache folders.
- Personal source exports.
- Product-specific generated outputs.
- Private hostnames, account names, emails, or operator-specific local paths.
- Real internal endpoint addresses or machine identifiers.

## Audit Performed

The extracted package was checked for private or project-specific leakage categories, including:

- Private project names.
- Private product names.
- Personal names and email fragments.
- Local user and workspace paths.
- Private LAN addresses.
- Private machine nicknames.
- Legacy source ID prefixes.
- Old project-specific workflow path prefixes.

The package should not contain those values. If future edits introduce any
private or project-specific term, replace it with a placeholder or document a
narrow, reviewed exception.

## Removed Or Generalized

- Private endpoint defaults were replaced with `ZTH_BASE_URL` and `<LLAMA_CPP_BASE_URL>`.
- Private model defaults were replaced with `ZTH_MODEL` and `<MODEL_NAME>`.
- Local machine paths were replaced with `<REPO_ROOT>`, `<MODEL_ROOT>`, `~`, or
  package-relative paths.
- Product-specific language was replaced with Zaphod's Third Hand or generic workflow language.
- Generated output locations were changed to package-local `outputs/` paths.
- Old lifecycle path examples were generalized to `job_queue/`, `active_jobs/`, `completed_jobs/`, `failed_jobs/`, and `blocked_jobs/`.

## Intentionally Retained As Examples

- `<SOURCE_ID>` is retained as a placeholder for a source identifier.
- `<SOURCE_FILE>` is retained as a placeholder for a local source file path.
- `<SHORT_TITLE>` is retained as a placeholder for a filesystem-safe title.
- `<LLAMA_CPP_BASE_URL>` is retained as a placeholder for a user-configured OpenAI-compatible endpoint.
- `<LAN_HOST>` is retained as a placeholder for a user-configured LAN hostname
  or address.
- `<MODEL_ROOT>` is retained as a placeholder for an operator's local model
  storage directory.
- `<MODEL_NAME>` is retained as a placeholder for a user-configured model.

Note: David Bitecofer is intentionally retained only as the copyright holder and commercial licensing contact. Other personal names, emails, account identifiers, and private contact details should not appear.

## LAN Address Policy

Public documentation, examples, reports, and tracked operator configuration
should use `<LAN_HOST>` instead of a literal RFC1918 address.

A literal RFC1918 address is allowed only as inert unit-test data or in a
deliberately synthetic fixture when the address is required to test parsing or
LAN behavior. It must not identify real reachable infrastructure, and the test
must not contact that address.

Reports may preserve the fact that a run used a LAN endpoint, but should
normalize the host before publication. This keeps the operational evidence
without publishing the operator's network layout.

## Known Limitations

- The distiller requires an OpenAI-compatible chat-completions endpoint configured by the user.
- The scripts do not load `config.env` automatically; source it in your shell or export variables directly.
- The package is intended for public sharing under the PolyForm Noncommercial License 1.0.0 and excludes private project material. It is not OSI open source.
- Generated `outputs/` are ignored by default and should be reviewed separately before any publication.

## Placeholder Meanings

- `<REPO_ROOT>`: root of the repository where this package is installed.
- `<LLAMA_CPP_BASE_URL>`: host and port for an OpenAI-compatible model endpoint.
- `<LAN_HOST>`: operator-supplied LAN hostname or address.
- `<MODEL_ROOT>`: operator-supplied root directory for local model files.
- `<MODEL_NAME>`: model name served by the endpoint.
- `<SOURCE_ID>`: stable identifier for a source transcript or log.
- `<SOURCE_FILE>`: path to a local source file.
- `<SHORT_TITLE>`: filesystem-safe short title for generated outputs.

## How To Check Before Sharing

Use tracked-file checks from the repository root. `git grep` does not traverse
ignored `.work/`, `outputs/`, `sources/`, caches, or other untracked evidence:

```bash
git status --short
git grep -nI -E '(/h[o]me/[[:alnum:]_.-]+|/Users/[[:alnum:]_.-]+|[A-Za-z]:\\Users\\[[:alnum:]_.-]+)' -- . || true
git grep -nI -E '(10[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}|172[.](1[6-9]|2[0-9]|3[01])[.][0-9]{1,3}[.][0-9]{1,3}|192[.]168[.][0-9]{1,3}[.][0-9]{1,3})' -- . ':!local_harness/tests/**' || true
git grep -nI -E '(JAR[V]ICE|Vision[[:space:]]+Planner|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN ([A-Z]+ )?PRIVATE KEY)' -- . || true
git ls-files | sort
git ls-files | grep -E '(^|/)(__pycache__|[.]pytest_cache)(/|$)|[.]py[co]$' || true
```

Review every match. A clean command result is useful evidence, but it is not a
substitute for human review.

Ignored or generated evidence must be reviewed separately before publication.
Do not add a recursive repository-wide grep to the routine release command:
doing so can print private `.work/`, `outputs/`, or `sources/` content into
terminal logs.

Also inspect tracked:

- Scripts.
- Examples.
- Workflow docs.
- Prompt files.
- Reports selected for publication.

Inspect generated files only when they are themselves being considered for
publication.

Use [`docs/SHARING_CHECKLIST.md`](SHARING_CHECKLIST.md) for a short publication checklist before copying the toolkit into a public repository.

## Review Checklist

- No private source text.
- No operator-specific local user paths.
- No real private endpoint IPs outside the narrow test/fixture exception.
- No personal email addresses.
- No private account names.
- No private product identity.
- No generated run records.
- No generated review patches.
- No cache files.

## Publication Guidance

Commit only the sanitized package files. Keep private source material and
generated project outputs outside public commits unless they have separate
human approval. Reports remain evidence after paths and hosts are normalized;
normalization must not be represented as changing the observed model behavior.
Confirm `LICENSE.md` and `COMMERCIAL_USE.md` match the intended noncommercial
sharing terms before publication.
