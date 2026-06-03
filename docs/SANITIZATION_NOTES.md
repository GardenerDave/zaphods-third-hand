# Sanitization Notes

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
- Private hostnames, account names, emails, or local paths.

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

The package should not contain those values. If future edits introduce any private or project-specific term, either replace it with placeholders or document why the example is intentionally retained.

## Removed Or Generalized

- Private endpoint defaults were replaced with `ZTH_BASE_URL` and `<LLAMA_CPP_BASE_URL>`.
- Private model defaults were replaced with `ZTH_MODEL` and `<MODEL_NAME>`.
- Local machine paths were replaced with `<REPO_ROOT>` or package-relative paths.
- Product-specific language was replaced with Zaphod's Third Hand or generic workflow language.
- Generated output locations were changed to package-local `outputs/` paths.
- Old lifecycle path examples were generalized to `job_queue/`, `active_jobs/`, `completed_jobs/`, `failed_jobs/`, and `blocked_jobs/`.

## Intentionally Retained As Examples

- `<SOURCE_ID>` is retained as a placeholder for a source identifier.
- `<SOURCE_FILE>` is retained as a placeholder for a local source file path.
- `<SHORT_TITLE>` is retained as a placeholder for a filesystem-safe title.
- `<LLAMA_CPP_BASE_URL>` is retained as a placeholder for a user-configured OpenAI-compatible endpoint.
- `<MODEL_NAME>` is retained as a placeholder for a user-configured model.

Note: David Bitecofer is intentionally retained only as the copyright holder and commercial licensing contact. Other personal names, emails, account identifiers, and private contact details should not appear.

## Known Limitations

- The distiller requires an OpenAI-compatible chat-completions endpoint configured by the user.
- The scripts do not load `config.env` automatically; source it in your shell or export variables directly.
- The package is intended for public sharing under the PolyForm Noncommercial License 1.0.0 and excludes private project material. It is not OSI open source.
- Generated `outputs/` are ignored by default and should be reviewed separately before any publication.

## Placeholder Meanings

- `<REPO_ROOT>`: root of the repository where this package is installed.
- `<LLAMA_CPP_BASE_URL>`: host and port for an OpenAI-compatible model endpoint.
- `<MODEL_NAME>`: model name served by the endpoint.
- `<SOURCE_ID>`: stable identifier for a source transcript or log.
- `<SOURCE_FILE>`: path to a local source file.
- `<SHORT_TITLE>`: filesystem-safe short title for generated outputs.

## How To Check Before Sharing

Run checks like:

```bash
grep -RInE 'private-name|private-domain|private-host|private-path|private-product' zaphods-third-hand || true
find zaphods-third-hand -type d -name '*cache*' -print
find zaphods-third-hand -type f | sort
```

Also inspect:

- Scripts.
- Examples.
- Workflow docs.
- Prompt files.
- Any generated files.

Use `docs/SHARING_CHECKLIST.md` for a short publication checklist before copying the toolkit into a public repository.

## Review Checklist

- No private source text.
- No local user paths.
- No private endpoint IPs.
- No personal email addresses.
- No private account names.
- No private product identity.
- No generated run records.
- No generated review patches.
- No cache files.

## Publication Guidance

Commit only the sanitized package files. Keep private source material and generated project outputs outside public commits unless they have separate human approval. Confirm `LICENSE.md` and `COMMERCIAL_USE.md` match the intended noncommercial sharing terms before publication.
