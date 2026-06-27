# Example Failure: CUDA on RX580-Class Host

Status: example_only

An operator asked for a GPU setup path on `navigator_desktop_example`. The
draft advice started with CUDA-specific package and runtime commands even
though the host profile says CUDA is unavailable and the GPU is an AMD
Polaris / RX 580 class placeholder.

Expected safer behavior:

- inspect the host profile first;
- do not assume NVIDIA/CUDA;
- suggest CPU fallback or OpenCL/ROCm investigation before CUDA-specific work.
