# Model Request

- In `local_harness/README.md`, apply excerpt patches.
```text
<<<<<<< SEARCH
- Excerpt patch: ``- In `path`, apply excerpt patches.`` then a fenced ``SEARCH/REPLACE`` patch set, then ``- Edit only the listed file.``
- One-file batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
- Multi-file batch: multiple operation bullets targeting up to 4 selected files, followed by ``- Edit only the listed files.`` Each step still has to stay unique at the point where it is applied.
=======
- Excerpt patch: ``- In `path`, apply excerpt patches.`` then a fenced ``SEARCH/REPLACE`` patch set, then ``- Edit only the listed file.``
- One-file batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
- Mixed batch: one excerpt patch plus literal deterministic operations across the selected files, followed by ``- Edit only the listed files.`` Each step still has to stay unique at the point where it is applied.
- Multi-file batch: multiple operation bullets targeting up to 4 selected files, followed by ``- Edit only the listed files.`` Each step still has to stay unique at the point where it is applied.
>>>>>>> REPLACE
<<<<<<< SEARCH
- Excerpt SEARCH/REPLACE patch sets are now manager-routable when each search stays unique at the step where it is applied.
- Bounded deterministic multi-file batches are now manager-routable for up to 4 selected files, and run `2026-06-08_043_*` live-proved the path on 2 real repo files.
=======
- Excerpt SEARCH/REPLACE patch sets are now manager-routable when each search stays unique at the step where it is applied.
- Mixed excerpt-plus-literal batches are now manager-routable when the excerpt SEARCH block and every literal step stay unique at the point where each step is applied.
- Bounded deterministic multi-file batches are now manager-routable for up to 4 selected files, and run `2026-06-08_043_*` live-proved the path on 2 real repo files.
>>>>>>> REPLACE
```
- In `02_sessions/2026-06-08_abacus-handoff-gemma-aider.md`, insert `- Mixed excerpt-plus-literal batches across selected files are now live-proven.\n` after `- Over-budget deterministic work no longer has to pay the whole-file Aider path first.\n`.
- Edit only the listed files.
