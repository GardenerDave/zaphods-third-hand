# Run 4 Resource Calibration

This is a model-free calibration of a candidate resource basis. It does not
use Run 3C validation, pass/fail, unresolved, routing, task-family, or
intervention-success fields. It does not approve weights or create a Run 4
policy or fixture pack.

## Evidence binding

- Source experiment: Run 3C control and treatment pooled
- Evidence root: `.work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20/`
- Run 3C preregistration SHA256: `fd45488ffd1e4b0ce4e67c40355b1cfa9404b98ebd53a022bd79cec9e6dae49b`
- Telemetry schema: `zth_resource_telemetry_v1` / calibration extractor `zth_resource_calibration_v1`
- Worker identity: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Local-teacher identity: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- External identity: `codex-cli-0.146.0`
- External timeout configuration: 120 seconds
- Hardware identity: not recorded in Run 3C

The Run 3C artifacts predate the new monotonic telemetry field. Therefore the
elapsed values below are derived from durable trajectory start/capture
timestamps, using the same physical millisecond unit. They are operational
elapsed intervals, not isolated server compute time.

## Established operational telemetry

| Role | Calls | Elapsed coverage | p25 ms | Median ms | Mean ms | p75 ms | Min ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| worker | 156 | 156/156 | 3,746.434 | 5,276.567 | 6,243.940 | 7,772.178 | 784.921 | 20,820.883 |
| local_teacher | 41 | 41/41 | 14,348.893 | 16,220.624 | 15,737.355 | 17,217.090 | 11,739.339 | 19,983.622 |
| external_teacher | 27 | 27/27 | 24,842.750 | 28,704.012 | 28,851.873 | 32,130.696 | 18,009.400 | 41,223.029 |

External token data is unavailable and was not fabricated. Worker and local
teacher token metadata exists, but tokens are not used for this candidate
basis.

## Derived candidate basis

The fixed candidate basis is the median observed elapsed milliseconds per call:

- worker: `5276.567 milliseconds_per_call`
- local teacher: `16220.624 milliseconds_per_call`
- external teacher: `28704.012 milliseconds_per_call`

For explanatory normalization only, local teacher = 1.0:

- worker: `0.325300`
- local teacher: `1.000000`
- external teacher: `1.769600`

The candidate is recorded in
`docs/research/RUN_4_RESOURCE_WEIGHTS_CANDIDATE_2026-08-19.json`. It remains
`frozen=false`, `review_status=draft`, and has no reviewer or approval basis.

## Sensitivity

The relative ordering is stable across the selected descriptive summaries:

| Statistic | Worker | Local teacher | External teacher | Ordering |
|---|---:|---:|---:|---|
| p25 | 3,746.434 | 14,348.893 | 24,842.750 | worker < local < external |
| median | 5,276.567 | 16,220.624 | 28,704.012 | worker < local < external |
| mean | 6,243.940 | 15,737.355 | 28,851.873 | worker < local < external |
| p75 | 7,772.178 | 17,217.090 | 32,130.696 | worker < local < external |

Thus external teacher remains more costly than local teacher, and worker
remains cheaper, under all four descriptive summaries. This robustness does not
select a routing policy or use capability outcomes.

## Proposed future objective

A future weighted-cost Run 4 could ask whether evidence-guided routing minimizes
expected heterogeneous inference resource cost while preserving deterministic
solve rate. The eventual primary metric would be computed only from a frozen,
approved resource-weight manifest. Raw counts remain secondary metrics:
worker calls, deterministic retries, local-teacher calls, and external-teacher
calls.

This candidate is a first time-based resource basis, not a monetary or energy
model. It is tied to the observed model/service configuration and should be
reviewed or invalidated if model, adapter, hardware, or service configuration
materially changes. Monetary prices, energy cost, hardware-independent cost,
and external token cost remain not established.

No model calls were made during calibration.
