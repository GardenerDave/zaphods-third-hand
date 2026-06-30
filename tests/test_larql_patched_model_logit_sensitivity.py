from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_patched_model_logit_sensitivity.py"
SPEC = importlib.util.spec_from_file_location("larql_patched_model_logit_sensitivity", SCRIPT)
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


def mock_probe_logits(scale: float, *, length: int = 6) -> list[dict[str, object]]:
    probes = MODULE.build_probe_set()
    rows: list[dict[str, object]] = []
    for idx, probe in enumerate(probes):
        base = [float(i) for i in range(length)]
        patched = [float(i) for i in range(length)]
        if scale and idx == 0:
            patched[0] += scale
        rows.append(
            {
                "probe_id": probe["probe_id"],
                "base_logits": base,
                "patched_logits": patched,
            }
        )
    return rows


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_runs_no_inference(tmp_path):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "logits_001",
        "--out-root", out_root,
        "--materialization-record", record_path,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "logits_001").exists()


def test_invalid_materialization_record_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"report_type": "wrong"})
    result = run_script(
        "--run-id", "logits_002",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-logit-sensitivity",
    )
    assert result.returncode != 0
    assert "report_type mismatch" in result.stdout


def test_record_with_patched_model_materialized_false_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"patched_model_materialized": False})
    result = run_script(
        "--run-id", "logits_003",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-logit-sensitivity",
    )
    assert result.returncode != 0
    assert "patched_model_materialized must be true" in result.stdout


def test_record_with_base_model_overwritten_true_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"base_model_overwritten": True})
    result = run_script(
        "--run-id", "logits_004",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-logit-sensitivity",
    )
    assert result.returncode != 0
    assert "base_model_overwritten must be false" in result.stdout


def test_record_with_promotion_authorized_true_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"promotion_authorized": True})
    result = run_script(
        "--run-id", "logits_005",
        "--out-root", tmp_path / "out",
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-logit-sensitivity",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout


def test_mocked_logits_can_produce_sensitivity_detected(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows = [{"probe_id": row["probe_id"], "final_prompt_logits": row["base_logits"], "top_k": 3} for row in mock_probe_logits(0.0)]
    patched_rows = [{"probe_id": row["probe_id"], "final_prompt_logits": row["patched_logits"], "top_k": 3} for row in mock_probe_logits(0.5)]
    counter = {"calls": 0}

    def fake_run_logit_inference(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_logit_inference", fake_run_logit_inference)
    record = MODULE.write_patched_model_logit_sensitivity(
        run_id="logits_006",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_logit_sensitivity=True,
        device="auto",
        top_k=3,
    )
    out_dir = out_root / "logits_006"
    assert record["logit_sensitivity_status"] == "logit_sensitivity_detected"
    assert (out_dir / "larql_patched_model_logit_sensitivity_record.json").exists()
    assert (out_dir / "logit_sensitivity_comparison.json").exists()
    assert (out_dir / "patched_model_logit_sensitivity_review_packet.md").exists()


def test_mocked_logits_can_produce_sensitivity_not_detected(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    rows = [{"probe_id": row["probe_id"], "final_prompt_logits": row["base_logits"], "top_k": 3} for row in mock_probe_logits(0.0)]
    counter = {"calls": 0}

    def fake_run_logit_inference(**kwargs):
        counter["calls"] += 1
        return rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_logit_inference", fake_run_logit_inference)
    record = MODULE.write_patched_model_logit_sensitivity(
        run_id="logits_007",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_logit_sensitivity=True,
        device="auto",
        top_k=3,
    )
    assert record["logit_sensitivity_status"] == "logit_sensitivity_not_detected"


def test_mocked_logits_can_produce_inconclusive(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows = [{"probe_id": "original_larql_behavior_replay", "final_prompt_logits": [0.0, 1.0], "top_k": 2}]
    patched_rows = []
    counter = {"calls": 0}

    def fake_run_logit_inference(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_logit_inference", fake_run_logit_inference)
    record = MODULE.write_patched_model_logit_sensitivity(
        run_id="logits_008",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_logit_sensitivity=True,
        device="auto",
        top_k=2,
    )
    assert record["logit_sensitivity_status"] == "logit_sensitivity_inconclusive"


def test_authority_fields_remain_correct_on_successful_mocked_run(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    rows = [{"probe_id": row["probe_id"], "final_prompt_logits": row["base_logits"], "top_k": 3} for row in mock_probe_logits(0.0)]
    counter = {"calls": 0}

    def fake_run_logit_inference(**kwargs):
        counter["calls"] += 1
        return rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_logit_inference", fake_run_logit_inference)
    record = MODULE.write_patched_model_logit_sensitivity(
        run_id="logits_009",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_logit_sensitivity=True,
        device="auto",
        top_k=3,
    )
    assert record["model_inference_performed"] is True
    assert record["generation_performed"] is False
    assert record["training_performed"] is False
    assert record["weight_edit_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["base_model_overwritten"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False


def test_heavy_imports_are_lazy():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "import torch" not in script_text.splitlines()[:50]
    assert "from transformers import" not in script_text.splitlines()[:50]
