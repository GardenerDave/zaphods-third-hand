from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_patched_model_teacher_forced_likelihood.py"
SPEC = importlib.util.spec_from_file_location("larql_patched_model_teacher_forced_likelihood", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def materialization_record_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    base_model = tmp_path / "base_model"
    patched_model = tmp_path / "patched_model"
    base_model.mkdir()
    patched_model.mkdir()
    payload = {
        "report_type": "larql_patched_model_materialization.v0",
        "base_model_path": str(base_model),
        "patched_model_path": str(patched_model),
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "delta_scale": 0.001,
        "base_tensor_sha256_before": "base-sha",
        "patched_tensor_sha256_after": "patched-sha",
        "patched_model_materialized": True,
        "weight_edit_performed": True,
        "base_model_overwritten": False,
        "model_inference_performed": False,
        "training_performed": False,
        "promotion_authorized": False,
        "base_model_overwrite_authorized": False,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "materialization_record.json", payload)


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def mock_rows(base_margin: float, patched_margin: float) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    probes = MODULE.build_probe_set()
    base_rows: list[dict[str, object]] = []
    patched_rows: list[dict[str, object]] = []
    for probe in probes:
        probe_id = probe["probe_id"]
        base_rows.append(
            {
                "probe_id": probe_id,
                "corrected_candidate_json": "{}",
                "failure_candidate_json": "{}",
                "corrected_score": {"total_logprob": base_margin - 2.0, "average_logprob": base_margin, "candidate_token_count": 4},
                "failure_score": {"total_logprob": -2.0, "average_logprob": 0.0, "candidate_token_count": 4},
            }
        )
        patched_rows.append(
            {
                "probe_id": probe_id,
                "corrected_candidate_json": "{}",
                "failure_candidate_json": "{}",
                "corrected_score": {"total_logprob": patched_margin - 2.0, "average_logprob": patched_margin, "candidate_token_count": 4},
                "failure_score": {"total_logprob": -2.0, "average_logprob": 0.0, "candidate_token_count": 4},
            }
        )
    return base_rows, patched_rows


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_runs_no_inference(tmp_path):
    record_path = materialization_record_fixture(tmp_path)
    result = run_script(
        "--run-id", "likelihood_001",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_invalid_materialization_record_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"report_type": "wrong"})
    result = run_script(
        "--run-id", "likelihood_002",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-teacher-forced-likelihood",
    )
    assert result.returncode != 0
    assert "report_type mismatch" in result.stdout


def test_record_with_patched_model_materialized_false_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"patched_model_materialized": False})
    result = run_script(
        "--run-id", "likelihood_003",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-teacher-forced-likelihood",
    )
    assert result.returncode != 0
    assert "patched_model_materialized must be true" in result.stdout


def test_record_with_base_model_overwritten_true_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"base_model_overwritten": True})
    result = run_script(
        "--run-id", "likelihood_004",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-teacher-forced-likelihood",
    )
    assert result.returncode != 0
    assert "base_model_overwritten must be false" in result.stdout


def test_record_with_promotion_authorized_true_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"promotion_authorized": True})
    result = run_script(
        "--run-id", "likelihood_005",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-teacher-forced-likelihood",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout


def test_mocked_candidate_scores_can_produce_improved(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows, patched_rows = mock_rows(0.1, 0.4)
    counter = {"calls": 0}

    def fake_run_teacher_forced_scoring(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_teacher_forced_scoring", fake_run_teacher_forced_scoring)
    record = MODULE.write_teacher_forced_likelihood(
        run_id="likelihood_006",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_teacher_forced_likelihood=True,
        device="auto",
    )
    out_dir = out_root / "likelihood_006"
    assert record["teacher_forced_likelihood_status"] == "teacher_forced_likelihood_improved"
    assert (out_dir / "larql_teacher_forced_likelihood_record.json").exists()
    assert (out_dir / "teacher_forced_likelihood_comparison.json").exists()
    assert (out_dir / "teacher_forced_likelihood_review_packet.md").exists()


def test_mocked_candidate_scores_can_produce_unchanged(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows, patched_rows = mock_rows(0.2, 0.2)
    counter = {"calls": 0}

    def fake_run_teacher_forced_scoring(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_teacher_forced_scoring", fake_run_teacher_forced_scoring)
    record = MODULE.write_teacher_forced_likelihood(
        run_id="likelihood_007",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_teacher_forced_likelihood=True,
        device="auto",
    )
    assert record["teacher_forced_likelihood_status"] == "teacher_forced_likelihood_unchanged"


def test_mocked_candidate_scores_can_produce_regressed(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows, patched_rows = mock_rows(0.4, 0.1)
    counter = {"calls": 0}

    def fake_run_teacher_forced_scoring(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_teacher_forced_scoring", fake_run_teacher_forced_scoring)
    record = MODULE.write_teacher_forced_likelihood(
        run_id="likelihood_008",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_teacher_forced_likelihood=True,
        device="auto",
    )
    assert record["teacher_forced_likelihood_status"] == "teacher_forced_likelihood_regressed"


def test_mocked_candidate_scores_can_produce_inconclusive(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows, _patched_rows = mock_rows(0.1, 0.1)
    counter = {"calls": 0}

    def fake_run_teacher_forced_scoring(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else []

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_teacher_forced_scoring", fake_run_teacher_forced_scoring)
    record = MODULE.write_teacher_forced_likelihood(
        run_id="likelihood_009",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_teacher_forced_likelihood=True,
        device="auto",
    )
    assert record["teacher_forced_likelihood_status"] == "teacher_forced_likelihood_inconclusive"


def test_authority_fields_remain_correct_on_successful_mocked_run(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows, patched_rows = mock_rows(0.1, 0.4)
    counter = {"calls": 0}

    def fake_run_teacher_forced_scoring(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_teacher_forced_scoring", fake_run_teacher_forced_scoring)
    record = MODULE.write_teacher_forced_likelihood(
        run_id="likelihood_010",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_teacher_forced_likelihood=True,
        device="auto",
    )
    assert record["model_inference_performed"] is True
    assert record["generation_performed"] is False
    assert record["teacher_forcing_performed"] is True
    assert record["training_performed"] is False
    assert record["weight_edit_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["base_model_overwritten"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False


def test_heavy_imports_are_lazy():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "import torch" not in script_text.splitlines()[:60]
    assert "from transformers import" not in script_text.splitlines()[:60]
