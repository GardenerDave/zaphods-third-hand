Task:
- # Model Request
- In `local_harness/README.md`, replace `and a deterministic direct-edit path that can short-circuit Aider before launch or recover after timeout when one selected file has exactly one unique literal replacement, one unique anchor insertion point, one unique block span between start/end anchors, or a small sequential batch whose steps remain unique as applied.` with `and a deterministic direct-edit path that can short-circuit Aider before launch or recover after timeout when the selected files fit a bounded literal replacement, unique-anchor insertion, block replacement, excerpt SEARCH/REPLACE patch, or deterministic batch plan.`.
- In `local_harness/README.md`, replace the block from `Guardrails remain strict:` through `- exact target or anchor text appears exactly once` with `Guardrails remain strict:
- exactly one selected file for replacement, insertion, block replacement, excerpt patch, and one-file batch routes
- up to 4 selected files for deterministic multi-file batches
- prompt length at or below 1200 characters for one-file replacement, insertion, block replacement, and one-file batch routes
Editable files:
- local_harness/README.md
- 02_sessio...
