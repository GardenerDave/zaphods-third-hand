Task:
- # Model Request
- In `local_harness/README.md`, apply excerpt patches.
- ```text
- <<<<<<< SEARCH
- Excerpt patch: ``- In `path`, apply excerpt patches.`` then a fenced ``SEARCH/REPLACE`` patch set, then ``- Edit only the listed file.``
- One-file batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
- Multi-file batch: multiple operation bullets targeting up to 4 selected files, followed by ``- Edit only the listed files.`` Each step still has to stay unique at the point where it is applied.
- =======
- Excerpt patch: ``- In `path`, apply excerpt patches.`` then a fenced ``SEARCH/REPLACE`` patch set, then ``- Edit only the listed file.``
- One-file batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
Editable files:
- local_harness/README.md
- 02_sessions/2026-06-08_abacus-handoff-gemma-aider.md
Gemma local rules:
- Edit only the listed files.
- Do not narrate plan or analysis.
- Return only valid Aider...
