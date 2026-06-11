# Sharing Checklist

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

Use this checklist before publishing or handing off Zaphod's Third Hand.

## Private Information

- [ ] Search for private project names, user names, machine names, LAN IPs, local paths, emails, phone numbers, account names, and credentials.
- [ ] Confirm private transcripts, chat exports, source intake files, generated runs, review patches, logs, and caches are not included.
- [ ] Replace environment-specific values with placeholders such as `<REPO_ROOT>`, `<SOURCE_FILE>`, `<LLAMA_CPP_BASE_URL>`, and `<MODEL_NAME>`.

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

## Attribution

- [ ] If AI assistance is acknowledged, use wording such as "assisted by AI".
- [ ] Do not use AI co-author commit trailers.

## License And Contact

- [ ] Confirm `LICENSE.md` and `COMMERCIAL_USE.md` match the intended noncommercial sharing terms.
- [ ] Confirm commercial use requires explicit written permission.
- [ ] Confirm David Bitecofer appears only as the approved copyright holder or commercial licensing contact.
