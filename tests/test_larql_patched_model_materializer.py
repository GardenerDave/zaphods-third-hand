from __future__ import annotations

import json
import pickle
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_patched_model_materializer.py"


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_model_fixture(tmp_path: Path, *, include_target: bool = True, target_shape: tuple[int, int] = (2, 3)) -> Path:
    model_dir = tmp_path / "base_model"
    model_dir.mkdir()
    shard_path = model_dir / "model_state.pt"
    state = {}
    if include_target:
        rows, cols = target_shape
        state["model.layers.0.mlp.down_proj.weight"] = [[0.0 for _ in range(cols)] for _ in range(rows)]
    shard_path.write_bytes(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
    return model_dir


def delta_artifact_fixture(tmp_path: Path, *, shape: tuple[int, int] = (2, 3)) -> tuple[Path, dict]:
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    artifact_path = artifact_dir / "rank1_delta.pt"
    rows, cols = shape
    delta = [[0.001 for _ in range(cols)] for _ in range(rows)]
    artifact_path.write_bytes(
        pickle.dumps(
            {
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "delta": delta,
            },
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    )
    record = {
        "report_type": "larql_rank1_delta_artifact.v0",
        "artifact_path": str(artifact_path),
        "artifact_sha256": sha256(artifact_path),
        "artifact_format": "pt",
        "delta_artifact_written": True,
        "patched_model_materialized": False,
        "base_model_overwrite_authorized": False,
        "promotion_authorized": False,
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "delta_scale": 0.001,
        "delta_shape": [rows, cols],
    }
    return artifact_path, record


def prepare_inputs(
    tmp_path: Path,
    *,
    include_target: bool = True,
    target_shape: tuple[int, int] = (2, 3),
    artifact_shape: tuple[int, int] = (2, 3),
    mutate_record: dict | None = None,
    tamper_artifact: bool = False,
) -> tuple[Path, Path]:
    model_dir = base_model_fixture(tmp_path, include_target=include_target, target_shape=target_shape)
    artifact_path, record = delta_artifact_fixture(tmp_path, shape=artifact_shape)
    if tamper_artifact:
        artifact_path.write_bytes(artifact_path.read_bytes() + b"tamper")
    if mutate_record:
        record.update(mutate_record)
    record_path = tmp_path / "larql_rank1_delta_artifact_record.json"
    write_json(record_path, record)
    return model_dir, record_path


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_writes_no_patched_model(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_001",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "materialize_001/patched_model").exists()


def test_artifact_hash_mismatch_fails_closed(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path, tamper_artifact=True)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_002",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
        "--authorize-larql-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "sha256 mismatch" in result.stdout
    assert not (out_root / "materialize_002/patched_model").exists()


def test_artifact_record_not_marked_written_fails_closed(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path, mutate_record={"delta_artifact_written": False})
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_003",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
        "--authorize-larql-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "delta_artifact_written true" in result.stdout


def test_artifact_record_with_base_model_overwrite_authorized_true_fails_closed(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path, mutate_record={"base_model_overwrite_authorized": True})
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_004",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
        "--authorize-larql-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "base_model_overwrite_authorized must be false" in result.stdout


def test_target_tensor_missing_fails_closed(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path, include_target=False)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_005",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
        "--authorize-larql-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "target tensor missing" in result.stdout
    assert not (out_root / "materialize_005/patched_model").exists()


def test_shape_mismatch_fails_closed(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path, target_shape=(2, 2), artifact_shape=(2, 3))
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_006",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
        "--authorize-larql-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "target tensor shape does not match delta shape" in result.stdout
    assert not (out_root / "materialize_006/patched_model").exists()


def test_successful_fixture_writes_record_review_packet_and_patched_model_dir(tmp_path):
    model_dir, record_path = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "materialize_007",
        "--out-root", out_root,
        "--base-model-path", model_dir,
        "--rank1-delta-artifact-record", record_path,
        "--authorize-larql-patched-model-materialization",
    )
    assert result.returncode == 0
    out_dir = out_root / "materialize_007"
    record = json.loads((out_dir / "larql_patched_model_materialization_record.json").read_text(encoding="utf-8"))
    assert (out_dir / "patched_model_review_packet.md").exists()
    assert (out_dir / "patched_model").exists()
    assert record["report_type"] == "larql_patched_model_materialization.v0"
    assert record["weight_edit_performed"] is True
    assert record["patched_model_materialized"] is True
    assert record["base_model_overwrite_authorized"] is False
    assert record["base_model_overwritten"] is False
    assert record["model_inference_performed"] is False
    assert record["training_performed"] is False
    assert record["adapter_baseline_path"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["rank1_delta_artifact_hash_verified"] is True


def test_no_real_inference_is_run():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "transformers" not in script_text
    assert 'framework="np"' not in script_text
