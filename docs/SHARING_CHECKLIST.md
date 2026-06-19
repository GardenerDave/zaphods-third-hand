# Sharing Checklist

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

Use this checklist before publishing or handing off Zaphod's Third Hand.

## Private Information

- [ ] Run the tracked-file-safe checks in [`docs/SANITIZATION_NOTES.md`](SANITIZATION_NOTES.md); do not recursively scan ignored/generated directories in the routine release command.
- [ ] Search tracked files for private project names, user names, machine names, LAN IPs, local paths, emails, phone numbers, account names, and credentials.
- [ ] Confirm private transcripts, chat exports, source intake files, generated runs, review patches, logs, and caches are not included.
- [ ] Replace environment-specific values with placeholders such as `<REPO_ROOT>`, `<SOURCE_FILE>`, `<LLAMA_CPP_BASE_URL>`, `<LAN_HOST>`, `<MODEL_ROOT>`, and `<MODEL_NAME>`.
- [ ] Confirm public docs, examples, reports, and tracked operator configs do not contain a real RFC1918 endpoint address.
- [ ] Treat literal RFC1918 values in tests as inert synthetic data only; they must not identify or contact real infrastructure.
- [ ] Review ignored/generated evidence separately only when it is being considered for publication.

## Configuration

- [ ] Copy `config.example.env` to a private `config.env`.
- [ ] Configure your own OpenAI-compatible endpoint and model.
- [ ] Keep endpoint credentials out of public commits.

## Toy Test

- [ ] Run the context distiller against a small toy source, not private production material.
- [ ] Confirm generated files appear under `outputs/`.
- [ ] Review generated session summaries and review patches before accepting anything.

## Workflow Safety

- [ ] Confirm job packets remain the control surface for work.
- [ ] Confirm management-team role prompts remain supervised-only by default.
- [ ] Confirm unattended execution and batched execution are not described as approved.
- [ ] Confirm generated review patches are described as non-canonical until accepted by human review.

## Reports And Evidence

- [ ] Normalize operator-specific source paths, usernames, and endpoint hosts in reports selected for publication.
- [ ] Preserve factual observations, failure modes, scores, and human-review boundaries when normalizing report metadata.
- [ ] Confirm no report presents sanitization or publication as model promotion, role assignment, or automatic acceptance.

## Attribution

- [ ] If AI assistance is acknowledged, use wording such as "assisted by AI".
- [ ] Do not use AI co-author commit trailers.

## License And Contact

- [ ] Confirm `LICENSE.md` and `COMMERCIAL_USE.md` match the intended noncommercial sharing terms.
- [ ] Confirm commercial use requires explicit written permission.
- [ ] Confirm David Bitecofer appears only as the approved copyright holder or commercial licensing contact.
