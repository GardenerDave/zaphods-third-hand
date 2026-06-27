# Example Failure: AVX2 Binary on R420-Class Host

Status: example_only

An operator selected a binary that requires AVX2 for `r420_server_example`.
The host profile says AVX2 is unavailable in this example. The run failed with
an illegal-instruction style symptom.

Expected safer behavior:

- inspect CPU flags from the host profile;
- choose a non-AVX2 build;
- do not copy this server constraint to other hosts.
