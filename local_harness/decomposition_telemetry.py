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
class DecompositionObservation:
    observation_id: str
    parent_task: str
    bifurcation_signal: str
    proposed_decomposition: str
    frozen_variables: list[str] = field(default_factory=list)
    predicted_effect: str = ""
    source_refs: list[str] = field(default_factory=list)
    prediction_status: str = "recorded"
    observed_outcome: str | None = None
    capability_notes: str = ""
    useful: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def freeze_decomposition_observation(observation: DecompositionObservation) -> dict[str, Any]:
    payload = observation.as_dict()
    serialized = _canonical_json(payload)
    return {
        "observation": payload,
        "observation_sha256": _sha256_bytes(serialized.encode("utf-8")),
        "serialized": serialized,
    }


def write_decomposition_observation(path: Path, observation: DecompositionObservation) -> str:
    frozen = freeze_decomposition_observation(observation)
    path.write_text(frozen["serialized"], encoding="utf-8")
    return frozen["observation_sha256"]
