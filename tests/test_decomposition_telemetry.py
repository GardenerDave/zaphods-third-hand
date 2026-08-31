from __future__ import annotations

import json
from pathlib import Path

from local_harness.decomposition_telemetry import (
    DecompositionObservation,
    freeze_decomposition_observation,
    write_prediction_record,
    write_resolution_record,
)


def test_freeze_decomposition_observation_is_stable(tmp_path: Path):
    obs = DecompositionObservation(
        record_type="prediction",
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
    sha = write_prediction_record(out, obs)
    assert sha == frozen["observation_sha256"]
    assert json.loads(out.read_text(encoding="utf-8"))["observation_id"] == obs.observation_id


def test_prediction_record_is_write_once(tmp_path: Path):
    obs = DecompositionObservation(
        record_type="prediction",
        observation_id="seed-1",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    path = tmp_path / "prediction.json"
    first = write_prediction_record(path, obs)
    assert len(first) == 64
    try:
        write_prediction_record(path, obs)
        raise AssertionError("expected FileExistsError")
    except FileExistsError:
        pass


def test_resolution_links_prediction_hash_and_is_write_once(tmp_path: Path):
    obs = DecompositionObservation(
        record_type="prediction",
        observation_id="seed-2",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    pred_path = tmp_path / "prediction.json"
    pred_sha = write_prediction_record(pred_path, obs)
    resolution_path = tmp_path / "resolution.json"
    res = {
        "record_type": "resolution",
        "observation_id": "seed-2",
        "prediction_sha256": pred_sha,
        "observed_outcome": "done",
        "useful": True,
    }
    res_sha = write_resolution_record(resolution_path, res)
    assert len(res_sha) == 64
    assert json.loads(resolution_path.read_text(encoding="utf-8"))["prediction_sha256"] == pred_sha
    try:
        write_resolution_record(resolution_path, res)
        raise AssertionError("expected FileExistsError")
    except FileExistsError:
        pass
