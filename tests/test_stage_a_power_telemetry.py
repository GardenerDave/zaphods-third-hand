from __future__ import annotations

import time
import json

import pytest

from local_harness.stage_a_power_telemetry import (
    PowerSample,
    PowerTelemetryError,
    PowerSampler,
    RemoteTelemetryReading,
    integrate_energy_joules,
    read_gpu_power,
    validate_samples,
)


GPU = "GPU-test-1650"
OTHER_GPU = "GPU-test-v100"
BASE_URL = "http" + "://stub.invalid"


class StubResponse:
    def __init__(self, payload=None, *, status=200, raw=None):
        self.status = status
        self._raw = raw if raw is not None else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._raw


def opener_for(payload=None, *, status=200, raw=None):
    def opener(request, timeout):
        assert request.full_url.endswith("/telemetry")
        return StubResponse(payload, status=status, raw=raw)
    return opener


def telemetry_payload(**overrides):
    payload = {
        "schema": "zth_gpu_telemetry_v1",
        "timestamp_utc": "2026-08-20T00:00:00+00:00",
        "sequence": 1,
        "gpu_uuid": GPU,
        "gpu_name": "NVIDIA GeForce GTX 1650",
        "power_watts": 42.5,
        "utilization_percent": 10.0,
        "memory_used_mib": 100.0,
        "memory_total_mib": 4096.0,
        "temperature_c": 50.0,
        "measurement_level": 2,
        "measurement_boundary": "gpu_device_only",
    }
    payload.update(overrides)
    return payload


def samples(*watts: float) -> list[PowerSample]:
    return [
        PowerSample(
            timestamp_utc=f"2026-08-20T00:00:0{index}Z",
            monotonic_seconds=float(index),
            gpu_uuid=GPU,
            power_watts=watts,
        )
        for index, watts in enumerate(watts)
    ]


def test_energy_integration_uses_watts_times_fixed_interval() -> None:
    assert integrate_energy_joules(samples(10.0, 20.0, 30.0), sample_interval_seconds=0.5, expected_gpu_uuid=GPU) == 30.0


def test_samples_must_be_monotonic_and_target_frozen_gpu() -> None:
    validate_samples(samples(10.0), expected_gpu_uuid=GPU, sample_interval_seconds=0.25)
    with pytest.raises(PowerTelemetryError, match="wrong GPU"):
        validate_samples(
            [PowerSample("now", 0.0, OTHER_GPU, 10.0)],
            expected_gpu_uuid=GPU,
            sample_interval_seconds=0.25,
        )
    with pytest.raises(PowerTelemetryError, match="strictly monotonic"):
        validate_samples(
            [
                PowerSample("one", 1.0, GPU, 10.0),
                PowerSample("zero", 0.0, GPU, 10.0),
            ],
            expected_gpu_uuid=GPU,
            sample_interval_seconds=0.25,
        )


def test_missing_samples_fail_visibly() -> None:
    with pytest.raises(PowerTelemetryError, match="no power samples"):
        integrate_energy_joules([], sample_interval_seconds=0.25, expected_gpu_uuid=GPU)


def test_sampler_records_interval_and_propagates_gpu_mismatch() -> None:
    readings = iter([(GPU, 12.0), (GPU, 14.0), (OTHER_GPU, 16.0)])
    sampler = PowerSampler(lambda: next(readings), expected_gpu_uuid=GPU, sample_interval_seconds=0.001)
    sampler.start()
    time.sleep(0.05)
    with pytest.raises(PowerTelemetryError, match="GPU mismatch"):
        sampler.stop()
    assert sampler.sample_interval_seconds == 0.001
    assert sampler.samples


def test_physical_telemetry_has_no_capability_disposition_input() -> None:
    energy = integrate_energy_joules(samples(20.0, 20.0), sample_interval_seconds=0.25, expected_gpu_uuid=GPU)
    capability_disposition = "failed"
    assert energy == 10.0
    assert capability_disposition == "failed"


def test_remote_telemetry_reader_accepts_frozen_schema() -> None:
    reading = read_gpu_power(GPU, base_url=BASE_URL, opener=opener_for(telemetry_payload()))
    assert reading.gpu_uuid == GPU
    assert reading.power_watts == 42.5
    assert reading.sequence == 1


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"gpu_uuid": OTHER_GPU}, "GPU mismatch"),
        ({"power_watts": None}, "power is not numeric"),
        ({"measurement_level": 1}, "level is not 2"),
        ({"measurement_boundary": "whole_system"}, "boundary mismatch"),
        ({"sequence": -1}, "sequence is invalid"),
    ],
)
def test_remote_telemetry_rejects_invalid_identity_and_measurement(overrides, match) -> None:
    with pytest.raises(PowerTelemetryError, match=match):
        read_gpu_power(GPU, base_url=BASE_URL, opener=opener_for(telemetry_payload(**overrides)))


def test_remote_telemetry_rejects_malformed_missing_and_http_failure() -> None:
    with pytest.raises(PowerTelemetryError, match="malformed JSON"):
        read_gpu_power(GPU, base_url=BASE_URL, opener=opener_for(raw=b"not-json"))
    missing = telemetry_payload()
    del missing["power_watts"]
    with pytest.raises(PowerTelemetryError, match="missing fields"):
        read_gpu_power(GPU, base_url=BASE_URL, opener=opener_for(missing))
    with pytest.raises(PowerTelemetryError, match="HTTP status 503"):
        read_gpu_power(GPU, base_url=BASE_URL, opener=opener_for({}, status=503))


def test_remote_sequence_must_be_monotonic() -> None:
    readings = iter([
        RemoteTelemetryReading("2026-08-20T00:00:00+00:00", 2, GPU, 20.0),
        RemoteTelemetryReading("2026-08-20T00:00:01+00:00", 2, GPU, 21.0),
    ])
    sampler = PowerSampler(lambda: next(readings), expected_gpu_uuid=GPU, sample_interval_seconds=0.001)
    sampler.start()
    time.sleep(0.01)
    with pytest.raises(PowerTelemetryError, match="sequence is not strictly monotonic"):
        sampler.stop()
