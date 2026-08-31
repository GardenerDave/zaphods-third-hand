from __future__ import annotations

import json
from pathlib import Path

from local_harness.decomposition_telemetry import (
    DecompositionObservation,
    freeze_decomposition_observation,
    write_decomposition_observation,
)


def test_freeze_decomposition_observation_is_stable(tmp_path: Path):
    obs = DecompositionObservation(
        observation_id="semantic-router-per-property-recovery-20260831",
        parent_task="multi-label proposition extraction",
        bifurcation_signal="natural-case failures despite synthetic success",
        proposed_decomposition="per-property classification",
        frozen_variables=["candidate prose", "gold", "endpoint", "temperature"],
        predicted_effect="recover A1/A2",
        source_refs=["docs/reports/semantic_property_classification_20260831_frozen_v1_report.md"],
        prediction_status="recorded",
        observed_outcome="30B recovered; 1.7B exact on natural cases",
        capability_notes="smaller-model sufficiency observed after decomposition; pre-decomposition smaller-model requirement unmeasured",
        useful=True,
    )
    frozen = freeze_decomposition_observation(obs)
    assert frozen["observation"]["observation_id"] == "semantic-router-per-property-recovery-20260831"
    assert len(frozen["observation_sha256"]) == 64

    out = tmp_path / "observation.json"
    sha = write_decomposition_observation(out, obs)
    assert sha == frozen["observation_sha256"]
    assert json.loads(out.read_text(encoding="utf-8"))["observation_id"] == obs.observation_id
