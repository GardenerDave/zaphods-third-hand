"""Model-free remote GPU power sampling and sampled-energy integration."""

from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


class PowerTelemetryError(ValueError):
    """Raised when device telemetry cannot be trusted for a measurement."""


@dataclass(frozen=True)
class RemoteTelemetryReading:
    timestamp_utc: str
    sequence: int
    gpu_uuid: str
    power_watts: float


@dataclass(frozen=True)
class PowerSample:
    timestamp_utc: str
    monotonic_seconds: float
    gpu_uuid: str
    power_watts: float
    sequence: int | None = None


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise PowerTelemetryError("telemetry timestamp is missing or invalid")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PowerTelemetryError("telemetry timestamp is not ISO-8601") from exc
    return value


def _fetch_json(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        open_fn = opener or urllib.request.urlopen
        response = open_fn(request, timeout=10)
        with response as body:
            status = getattr(body, "status", 200)
            raw = body.read()
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise PowerTelemetryError("remote GPU telemetry HTTP failure") from exc
    if status != 200:
        raise PowerTelemetryError(f"remote GPU telemetry HTTP status {status}")
    try:
        payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except (TypeError, ValueError) as exc:
        raise PowerTelemetryError("remote GPU telemetry returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise PowerTelemetryError("remote GPU telemetry JSON must be an object")
    return payload


def remote_health(*, base_url: str, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Read the non-generative telemetry health endpoint."""
    return _fetch_json(f"{base_url.rstrip('/')}/health", opener=opener)


def read_gpu_power(
    gpu_uuid: str,
    *,
    base_url: str | None = None,
    opener: Callable[..., Any] | None = None,
) -> RemoteTelemetryReading:
    """Read one validated Level-2 power sample from the remote endpoint."""
    if not base_url:
        raise PowerTelemetryError("remote GPU telemetry base URL is unset")
    payload = _fetch_json(f"{base_url.rstrip('/')}/telemetry", opener=opener)
    required = {
        "schema",
        "timestamp_utc",
        "sequence",
        "gpu_uuid",
        "power_watts",
        "measurement_level",
        "measurement_boundary",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise PowerTelemetryError(f"remote GPU telemetry missing fields: {','.join(missing)}")
    if payload["schema"] != "zth_gpu_telemetry_v1":
        raise PowerTelemetryError("remote GPU telemetry schema mismatch")
    if payload["gpu_uuid"] != gpu_uuid:
        raise PowerTelemetryError(
            f"telemetry GPU mismatch: expected {gpu_uuid}, observed {payload['gpu_uuid']}"
        )
    if payload["measurement_level"] != 2:
        raise PowerTelemetryError("remote GPU telemetry measurement level is not 2")
    if payload["measurement_boundary"] != "gpu_device_only":
        raise PowerTelemetryError("remote GPU telemetry measurement boundary mismatch")
    timestamp_utc = _parse_timestamp(payload["timestamp_utc"])
    sequence = payload["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise PowerTelemetryError("remote GPU telemetry sequence is invalid")
    power_watts = payload["power_watts"]
    if isinstance(power_watts, bool) or not isinstance(power_watts, (int, float)):
        raise PowerTelemetryError("remote GPU telemetry power is not numeric")
    power_watts = float(power_watts)
    if not math.isfinite(power_watts) or power_watts < 0:
        raise PowerTelemetryError("remote GPU telemetry power is unavailable or invalid")
    return RemoteTelemetryReading(timestamp_utc, sequence, gpu_uuid, power_watts)


def validate_samples(
    samples: list[PowerSample], *, expected_gpu_uuid: str, sample_interval_seconds: float
) -> None:
    if sample_interval_seconds <= 0:
        raise PowerTelemetryError("sample interval must be positive")
    if not samples:
        raise PowerTelemetryError("no power samples were captured")
    previous_monotonic = None
    previous_sequence = None
    previous_remote_timestamp = None
    for sample in samples:
        if sample.gpu_uuid != expected_gpu_uuid:
            raise PowerTelemetryError("sample series contains the wrong GPU")
        if not math.isfinite(sample.power_watts) or sample.power_watts < 0:
            raise PowerTelemetryError("sample series contains invalid power")
        if previous_monotonic is not None and sample.monotonic_seconds <= previous_monotonic:
            raise PowerTelemetryError("sample timestamps are not strictly monotonic")
        if sample.sequence is not None:
            if previous_sequence is not None and sample.sequence <= previous_sequence:
                raise PowerTelemetryError("remote telemetry sequence is not strictly monotonic")
            previous_sequence = sample.sequence
            if previous_remote_timestamp is not None:
                try:
                    current = datetime.fromisoformat(sample.timestamp_utc.replace("Z", "+00:00"))
                    prior = datetime.fromisoformat(previous_remote_timestamp.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise PowerTelemetryError("remote telemetry timestamp is invalid") from exc
                if current <= prior:
                    raise PowerTelemetryError("remote telemetry timestamps are not strictly monotonic")
            previous_remote_timestamp = sample.timestamp_utc
        previous_monotonic = sample.monotonic_seconds


def integrate_energy_joules(
    samples: list[PowerSample], *, sample_interval_seconds: float, expected_gpu_uuid: str
) -> float:
    """Integrate gross sampled device energy using the frozen interval."""
    validate_samples(
        samples,
        expected_gpu_uuid=expected_gpu_uuid,
        sample_interval_seconds=sample_interval_seconds,
    )
    return round(sum(sample.power_watts * sample_interval_seconds for sample in samples), 6)


class PowerSampler:
    """Fixed-interval remote sampler with explicit error propagation."""

    def __init__(
        self,
        sample_reader: Callable[[], tuple[str, float] | RemoteTelemetryReading],
        *,
        expected_gpu_uuid: str,
        sample_interval_seconds: float = 0.25,
    ) -> None:
        if sample_interval_seconds <= 0:
            raise PowerTelemetryError("sample interval must be positive")
        self._sample_reader = sample_reader
        self.expected_gpu_uuid = expected_gpu_uuid
        self.sample_interval_seconds = sample_interval_seconds
        self.samples: list[PowerSample] = []
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _run(self) -> None:
        next_sample = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            if now < next_sample:
                self._stop.wait(next_sample - now)
                continue
            try:
                reading = self._sample_reader()
                if isinstance(reading, RemoteTelemetryReading):
                    observed_uuid = reading.gpu_uuid
                    power_watts = reading.power_watts
                    timestamp_utc = reading.timestamp_utc
                    sequence = reading.sequence
                else:
                    observed_uuid, power_watts = reading
                    timestamp_utc = _timestamp()
                    sequence = None
                if observed_uuid != self.expected_gpu_uuid:
                    raise PowerTelemetryError(
                        f"telemetry GPU mismatch: expected {self.expected_gpu_uuid}, "
                        f"observed {observed_uuid}"
                    )
                self.samples.append(
                    PowerSample(
                        timestamp_utc=timestamp_utc,
                        monotonic_seconds=now,
                        gpu_uuid=observed_uuid,
                        power_watts=float(power_watts),
                        sequence=sequence,
                    )
                )
            except Exception as exc:  # preserve the failure for the caller
                self.error = str(exc)
                self._stop.set()
                return
            next_sample += self.sample_interval_seconds

    def start(self) -> None:
        if self._thread is not None:
            raise PowerTelemetryError("sampler already started")
        self._thread = threading.Thread(target=self._run, name="stage-a-power-sampler")
        self._thread.start()

    def stop(self) -> list[PowerSample]:
        if self._thread is None:
            raise PowerTelemetryError("sampler was not started")
        self._stop.set()
        self._thread.join(timeout=max(1.0, self.sample_interval_seconds * 4))
        if self._thread.is_alive():
            raise PowerTelemetryError("power sampler did not stop cleanly")
        if self.error:
            raise PowerTelemetryError(self.error)
        validate_samples(
            self.samples,
            expected_gpu_uuid=self.expected_gpu_uuid,
            sample_interval_seconds=self.sample_interval_seconds,
        )
        return list(self.samples)
