# Model Request

- In `local_harness/README.md`, apply excerpt patches.
```text
<<<<<<< SEARCH
- Replace block: ``- In `path`, replace the block from `start` through `end` with `new`.`` then ``- Edit only the listed file.``
- Batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
=======
- Replace block: ``- In `path`, replace the block from `start` through `end` with `new`.`` then ``- Edit only the listed file.``
- Excerpt patch: ``- In `path`, apply excerpt patches.`` then a fenced ``SEARCH/REPLACE`` patch set, then ``- Edit only the listed file.``
- Batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
>>>>>>> REPLACE
<<<<<<< SEARCH
- Batched one-file deterministic edits are now manager-routable when each step stays unique.
- `validated_shape_match` is only a routing hint for Aider-sized work. Run `2026-06-08_033_*` showed a thin real-code file can still stall while matching that heuristic.
=======
- Batched one-file deterministic edits are now manager-routable when each step stays unique.
- Excerpt SEARCH/REPLACE patch sets are now manager-routable when each search stays unique at the step where it is applied.
- `validated_shape_match` is only a routing hint for Aider-sized work. Run `2026-06-08_033_*` showed a thin real-code file can still stall while matching that heuristic.
>>>>>>> REPLACE
```
- Edit only the listed file.
