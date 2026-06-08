# Accepted Output

- Accepted finding: excerpt SEARCH/REPLACE patch sets are now live-proven through the manager-side direct-edit short-circuit.
- Accepted implementation note: the current excerpt route supports multi-hunk patch sets when each SEARCH block is unique at the moment it is applied.
- Accepted workflow rule: use the excerpt patch route for bounded one-file changes that are too rich for literal line replacement but too small to justify whole-file Aider.
