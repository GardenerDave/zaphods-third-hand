# Example Failure: Unknown Host

Status: example_only

A failure note says "this model command does not work on my machine" but does
not identify the host profile, GPU, CPU flags, operating system, runtime, or
known-good paths.

Expected safer behavior:

- do not infer a host-specific LARQL patch;
- collect or refresh a host profile;
- keep the item in review-only status until evidence exists.
