# Share-Ready Checklist

Use this checklist before publishing or sharing Zaphod's Third Hand.

## Privacy

- [ ] No private transcripts, chat exports, generated runs, review patches, or local logs are included.
- [ ] No emails, phone numbers, account names, local usernames, LAN IPs, machine names, or home paths are included.
- [ ] Placeholder values such as `<REPO_ROOT>`, `<SOURCE_ID>`, `<SOURCE_FILE>`, `<LLAMA_CPP_BASE_URL>`, and `<MODEL_NAME>` are still generic.
- [ ] David Bitecofer appears only as the approved copyright holder or commercial licensing contact.

## Documentation

- [ ] `README.md` explains what the toolkit does and does not do.
- [ ] `QUICKSTART.md` shows the minimal setup path.
- [ ] The context distiller, job lifecycle, and supervised role usage are documented.
- [ ] Generated review patches are clearly described as non-canonical until accepted.

## Licensing

- [ ] `LICENSE.md` references PolyForm Noncommercial License 1.0.0.
- [ ] `COMMERCIAL_USE.md` explains that commercial or for-profit use requires explicit written permission.
- [ ] The commercial licensing contact is David Bitecofer.

## Scripts And Config

- [ ] `config.example.env` contains placeholders only.
- [ ] `scripts/run_context_distiller_head.sh` uses package-relative paths.
- [ ] Generated outputs go under `outputs/`.
- [ ] No private endpoint, model server, credential, or auth value is hardcoded.

## Git Hygiene

- [ ] `.gitignore` excludes generated outputs, local config, caches, source scratch folders, transcript scratch folders, and logs.
- [ ] `git status --short` shows only intended files.
- [ ] A leakage grep has been run before publication.
