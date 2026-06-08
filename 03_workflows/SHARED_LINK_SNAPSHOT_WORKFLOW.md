# Shared Link Snapshot Workflow

Author: [REDACTED]

Shared links are useful source pointers, but they are not local archives.

## Active Queue Semantics

`ICM/00_sources/shared_links/SharedLinks.txt` is an active intake queue. If it is empty or contains only whitespace, no active hosted links are queued. VP-0001 through VP-0018 remain historical failed audit records, and LOCAL-0001 is the usable local transcript source for the ICM-wrapper conversation.

## Steps

1. Add the shared link to `ICM/00_sources/shared_links/SharedLinks.txt` or the manifest.
2. Assign an ID such as `VP-0001`.
3. Open the link in a browser or available web tooling.
4. Save the visible conversation locally:
   - Preferred: markdown or plain text.
   - Acceptable: HTML.
   - Acceptable: PDF.
5. Save the local file to `ICM/00_sources/shared_links/snapshots/`.
6. Update `local_snapshot` and set status to `snapshot_saved`.
7. Process the local snapshot with the extraction prompt.
8. Mark status `extracted`, then `reviewed`, then `merged` as appropriate.
9. If the link cannot expose conversation content, save the blocked page or failure notes and mark status `failed`.
10. If a local transcript or official export is later provided for the same conversation, keep the failed link record as audit history and extract from the local source.

## Why This Matters

A shared link may capture a conversation at one point in time, but it is still hosted externally. The local snapshot is the durable source file.

Hosted links can fail in agent environments because of JavaScript/cookie challenges. Do not change a failed shared-link record to `extracted` unless its actual snapshot contains conversation content.
