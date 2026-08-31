from __future__ import annotations

import json
from pathlib import Path

from local_harness.decomposition_telemetry import (
    DecompositionPrediction,
    DecompositionResolution,
    freeze_decomposition_observation,
    write_prediction_record,
    write_resolution_record,
)


def test_prediction_freezes_without_outcome(tmp_path: Path):
    obs = DecompositionPrediction(
        record_type="prediction",
        observation_id="semantic-router-per-property-recovery-20260831",
        parent_task="multi-label proposition extraction",
        bifurcation_signal="natural-case failures despite synthetic success",
        proposed_decomposition="per-property classification",
        frozen_variables=["candidate prose", "gold", "endpoint", "temperature"],
        predicted_effect="recover A1/A2",
        source_refs=["docs/reports/semantic_property_classification_20260831_frozen_v1_report.md"],
        prediction_status="recorded",
        capability_notes="prediction only",
    )
    frozen = freeze_decomposition_observation(obs)
    assert frozen["observation"]["record_type"] == "prediction"
    assert "observed_outcome" not in frozen["observation"]
    assert "useful" not in frozen["observation"]
    assert len(frozen["observation_sha256"]) == 64

    path = tmp_path / "prediction.json"
    sha = write_prediction_record(path, obs)
    assert sha == frozen["observation_sha256"]
    assert json.loads(path.read_text(encoding="utf-8"))["observation_id"] == obs.observation_id


def test_prediction_record_is_write_once(tmp_path: Path):
    obs = DecompositionPrediction(
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
    obs = DecompositionPrediction(
        record_type="prediction",
        observation_id="seed-2",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    pred_path = tmp_path / "prediction.json"
    pred_sha = write_prediction_record(pred_path, obs)
    resolution_path = tmp_path / "resolution.json"
    res = DecompositionResolution(
        record_type="resolution",
        observation_id="seed-2",
        prediction_sha256=pred_sha,
        observed_outcome="done",
        useful=True,
    )
    res_sha = write_resolution_record(resolution_path, pred_path, res)
    assert len(res_sha) == 64
    assert json.loads(resolution_path.read_text(encoding="utf-8"))["prediction_sha256"] == pred_sha
    try:
        write_resolution_record(resolution_path, pred_path, res)
        raise AssertionError("expected FileExistsError")
    except FileExistsError:
        pass


def test_resolution_rejects_unknown_prediction(tmp_path: Path):
    res = DecompositionResolution(
        record_type="resolution",
        observation_id="seed-3",
        prediction_sha256="0" * 64,
        observed_outcome="done",
        useful=True,
    )
    try:
        write_resolution_record(tmp_path / "resolution.json", tmp_path / "missing_prediction.json", res)
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass


def test_resolution_hash_mismatch_fails(tmp_path: Path):
    obs = DecompositionPrediction(
        record_type="prediction",
        observation_id="seed-4",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    pred_path = tmp_path / "prediction.json"
    write_prediction_record(pred_path, obs)
    res = DecompositionResolution(
        record_type="resolution",
        observation_id="seed-4",
        prediction_sha256="0" * 64,
        observed_outcome="done",
        useful=True,
    )
    try:
        write_resolution_record(tmp_path / "resolution.json", pred_path, res)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "prediction_sha256 does not match" in str(exc)


def test_resolution_observation_id_mismatch_fails(tmp_path: Path):
    obs = DecompositionPrediction(
        record_type="prediction",
        observation_id="seed-5",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    pred_path = tmp_path / "prediction.json"
    pred_sha = write_prediction_record(pred_path, obs)
    res = DecompositionResolution(
        record_type="resolution",
        observation_id="seed-5b",
        prediction_sha256=pred_sha,
        observed_outcome="done",
        useful=True,
    )
    try:
        write_resolution_record(tmp_path / "resolution.json", pred_path, res)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "observation_id must match" in str(exc)


def test_resolution_bytes_do_not_modify_prediction(tmp_path: Path):
    obs = DecompositionPrediction(
        record_type="prediction",
        observation_id="seed-6",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    pred_path = tmp_path / "prediction.json"
    pred_sha = write_prediction_record(pred_path, obs)
    before = pred_path.read_bytes()
    res = DecompositionResolution(
        record_type="resolution",
        observation_id="seed-6",
        prediction_sha256=pred_sha,
        observed_outcome="done",
        useful=True,
    )
    write_resolution_record(tmp_path / "resolution.json", pred_path, res)
    assert pred_path.read_bytes() == before


def test_resolution_rejects_second_conflicting_write(tmp_path: Path):
    obs = DecompositionPrediction(
        record_type="prediction",
        observation_id="seed-7",
        parent_task="task",
        bifurcation_signal="signal",
        proposed_decomposition="atomization",
    )
    pred_path = tmp_path / "prediction.json"
    pred_sha = write_prediction_record(pred_path, obs)
    res = DecompositionResolution(
        record_type="resolution",
        observation_id="seed-7",
        prediction_sha256=pred_sha,
        observed_outcome="done",
        useful=True,
    )
    resolution_path = tmp_path / "resolution.json"
    write_resolution_record(resolution_path, pred_path, res)
    try:
        write_resolution_record(resolution_path, pred_path, res)
        raise AssertionError("expected FileExistsError")
    except FileExistsError:
        pass
