from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class DecompositionPrediction:
    record_type: str
    observation_id: str
    parent_task: str
    bifurcation_signal: str
    proposed_decomposition: str
    frozen_variables: list[str] = field(default_factory=list)
    predicted_effect: str = ""
    source_refs: list[str] = field(default_factory=list)
    prediction_status: str = "recorded"
    capability_notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecompositionResolution:
    record_type: str
    observation_id: str
    prediction_sha256: str
    observed_outcome: str
    capability_notes: str = ""
    useful: bool | None = None
    resolution_source_refs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def freeze_decomposition_observation(observation: DecompositionPrediction) -> dict[str, Any]:
    payload = observation.as_dict()
    serialized = _canonical_json(payload)
    return {
        "observation": payload,
        "observation_sha256": _sha256_bytes(serialized.encode("utf-8")),
        "serialized": serialized,
    }


def write_prediction_record(path: Path, observation: DecompositionPrediction) -> str:
    if observation.record_type != "prediction":
        raise ValueError("prediction record_type required")
    if path.exists():
        raise FileExistsError(path)
    frozen = freeze_decomposition_observation(observation)
    path.write_text(frozen["serialized"], encoding="utf-8")
    return frozen["observation_sha256"]


def write_resolution_record(path: Path, prediction_path: Path, resolution: DecompositionResolution) -> str:
    if resolution.record_type != "resolution":
        raise ValueError("resolution record_type required")
    if not prediction_path.exists():
        raise FileNotFoundError(prediction_path)
    prediction_payload = json.loads(prediction_path.read_text(encoding="utf-8"))
    if not isinstance(prediction_payload, dict):
        raise ValueError("prediction record must be a JSON object")
    if prediction_payload.get("record_type") != "prediction":
        raise ValueError("prediction record_type required")
    if prediction_payload.get("observation_id") != resolution.observation_id:
        raise ValueError("resolution observation_id must match prediction observation_id")
    if prediction_payload.get("bifurcation_signal") is None or prediction_payload.get("proposed_decomposition") is None:
        raise ValueError("prediction record missing required fields")
    if "observed_outcome" in prediction_payload or "useful" in prediction_payload:
        raise ValueError("prediction record must not contain outcome fields")
    if _sha256_bytes(prediction_path.read_bytes()) != resolution.prediction_sha256:
        raise ValueError("prediction_sha256 does not match prediction_path")
    forbidden = {
        "bifurcation_signal",
        "proposed_decomposition",
        "predicted_effect",
        "frozen_variables",
        "source_refs",
        "prediction_status",
    }
    if forbidden & set(resolution.as_dict().keys()):
        raise ValueError("resolution must not redefine prediction fields")
    if path.exists():
        raise FileExistsError(path)
    payload = resolution.as_dict()
    serialized = _canonical_json(payload)
    path.write_text(serialized, encoding="utf-8")
    return _sha256_bytes(serialized.encode("utf-8"))
