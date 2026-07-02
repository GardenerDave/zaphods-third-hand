from __future__ import annotations

import hashlib
import importlib.util
import json
import pickle
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_continuation_patched_model_materializer.py"
SPEC = importlib.util.spec_from_file_location("larql_continuation_patched_model_materializer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_delta_tensor(values: list[list[float]]) -> bytes:
    return MODULE.encode_safetensors_single_tensor("model.layers.0.mlp.down_proj.weight", values)


def parse_safetensors_header(path: Path) -> tuple[dict, bytes]:
    import struct

    blob = path.read_bytes()
    header_len = struct.unpack("<Q", blob[:8])[0]
    header = json.loads(blob[8 : 8 + header_len].decode("utf-8"))
    return header, blob[8 + header_len :]


def base_model_fixture(
    tmp_path: Path,
    *,
    include_target: bool = True,
    target_shape: tuple[int, int] = (2, 3),
    use_safetensors_shard: bool = False,
) -> Path:
    base = tmp_path / "base_model"
    base.mkdir()
    if use_safetensors_shard:
        try:
            import importlib.util

            if importlib.util.find_spec("torch") is None or importlib.util.find_spec("safetensors") is None:
                pytest.skip("safetensors/torch unavailable for end-to-end safetensors materialization test")
        except pytest.SkipTest:
            raise
        try:
            from safetensors.numpy import save_file  # type: ignore
            import numpy as np  # type: ignore
        except Exception:
            pytest.skip("safetensors/torch unavailable for end-to-end safetensors materialization test")

        rows, cols = target_shape
        shard = base / "model.safetensors"
        tensor_map = {}
        if include_target:
            tensor_map["model.layers.0.mlp.down_proj.weight"] = np.array(
                [[0.0 for _ in range(cols)] for _ in range(rows)],
                dtype=np.float32,
            )
        tensor_map["other.weight"] = np.array([[1.0]], dtype=np.float32)
        save_file(tensor_map, str(shard))
        index_path = base / "model.safetensors.index.json"
        write_json(
            index_path,
            {
                "metadata": {"total_size": shard.stat().st_size},
                "weight_map": {
                    "model.layers.0.mlp.down_proj.weight": "model.safetensors",
                    "other.weight": "model.safetensors",
                },
            },
        )
        return base

    shard_path = base / "model_state.pt"
    rows, cols = target_shape
    state = {"other.weight": [[1.0]]}
    if include_target:
        state["model.layers.0.mlp.down_proj.weight"] = [[0.0 for _ in range(cols)] for _ in range(rows)]
    shard_path.write_bytes(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
    write_json(
        base / "model.safetensors.index.json",
        {
            "metadata": {"total_size": shard_path.stat().st_size},
            "weight_map": {
                "model.layers.0.mlp.down_proj.weight": "model_state.pt",
                "other.weight": "model_state.pt",
            },
        },
    )
    (base / "config.json").write_text("{}", encoding="utf-8")
    return base


def delta_manifest_fixture(
    tmp_path: Path,
    *,
    target_module: str = "model.layers.0.mlp.down_proj",
    target_parameter: str | None = None,
    target_shape: tuple[int, int] = (2, 3),
    delta_scale: float = 0.01,
    mutate: dict | None = None,
) -> tuple[Path, Path]:
    target_parameter = target_parameter or f"{target_module}.weight"
    rows, cols = target_shape
    delta_values = [[0.001 for _ in range(cols)] for _ in range(rows)]
    artifact_path = tmp_path / "artifact" / "rank1_delta.safetensors"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(encode_delta_tensor(delta_values))
    manifest = {
        "report_type": "larql_continuation_rank1_delta_artifact.v0",
        "source_continuation_rank1_delta_design_path": "design.json",
        "source_continuation_direction_vectors_path": "vectors.json",
        "artifact_format": "safetensors",
        "artifact_path": str(artifact_path),
        "artifact_sha256": sha256(artifact_path),
        "target_module": target_module,
        "target_parameter": target_parameter,
        "target_module_family": "mlp_projection",
        "vector_source": "continuation_prediction_position",
        "rank": 1,
        "delta_scale": delta_scale,
        "delta_shape": [rows, cols],
        "delta_dtype": "float32",
        "delta_frobenius_norm": delta_scale,
        "expected_delta_frobenius_norm": delta_scale,
        "nonzero_count": rows * cols,
        "expected_nonzero_count": rows * cols,
        "continuation_output_direction_sha256": "a" * 64,
        "continuation_input_direction_sha256": "b" * 64,
        "recommended_next_step": "supervised_continuation_delta_artifact_review",
        "required_next_step": "supervised_continuation_delta_artifact_review",
        "claim_boundary": {
            "writes_delta_artifact_only": True,
            "no_inference": True,
            "no_generation": True,
            "no_training": True,
            "no_lora_or_peft": True,
            "no_base_model_overwrite": True,
            "no_patched_model_materialization": True,
            "no_promotion": True,
            "evidence_not_authority": True,
        },
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed": False,
        "delta_artifact_written": True,
        "patched_model_materialized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    if mutate:
        manifest.update(mutate)
    manifest_path = write_json(tmp_path / "manifest.json", manifest)
    return manifest_path, artifact_path


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorization_required(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    result = run_script(
        "--run-id", "mat_001",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", json.loads(manifest.read_text(encoding="utf-8"))["artifact_sha256"],
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_reviewed_sha_gate_and_existing_output_dir_fail_closed(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    out_dir = tmp_path / "out" / "mat_002"
    out_dir.mkdir(parents=True)
    result = run_script(
        "--run-id", "mat_002",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", "0" * 64,
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout or "reviewed_artifact_sha256 mismatch" in result.stdout


def test_input_validation_failures(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    cases = [
        ({"report_type": "other"}, "report_type mismatch"),
        ({"artifact_format": "pt"}, "artifact_format must be safetensors"),
        ({"delta_artifact_written": False}, "delta_artifact_written true"),
        ({"patched_model_materialized": True}, "continuation delta artifact manifest must have patched_model_materialized false"),
        ({"base_model_overwritten": True}, "base_model_overwritten must be false"),
        ({"promotion_authorized": True}, "promotion_authorized must be false"),
        ({"automatic_failure_to_curriculum_capture_authorized": True}, "automatic_failure_to_curriculum_capture_authorized must be false"),
        ({"target_parameter": ""}, "target_parameter missing"),
        ({"target_module": ""}, "target_module missing"),
        ({"target_module_family": "other"}, "target_module_family must be mlp_projection"),
        ({"vector_source": "other"}, "vector_source must be continuation_prediction_position"),
        ({"delta_shape": [2]}, "delta_shape missing or invalid"),
        ({"delta_scale": 0.0}, "delta_scale must be positive and finite"),
    ]
    for index, (mutate, message) in enumerate(cases):
        bad_manifest = write_json(tmp_path / f"manifest_{index}.json", {**payload, **mutate})
        result = run_script(
            "--run-id", f"mat_bad_{index}",
            "--out-root", tmp_path / "out",
            "--base-model-path", base,
            "--delta-artifact-manifest", bad_manifest,
            "--delta-artifact", artifact,
            "--reviewed-artifact-sha256", payload["artifact_sha256"],
            "--authorize-larql-continuation-patched-model-materialization",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_artifact_validation_failures(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    bad_key = tmp_path / "artifact" / "bad_key.safetensors"
    bad_key.write_bytes(
        MODULE.encode_safetensors_single_tensor(
            "model.layers.0.mlp.down_proj.other",
            [[0.001, 0.001, 0.001], [0.001, 0.001, 0.001]],
        )
    )
    bad_shape = tmp_path / "artifact" / "bad_shape.safetensors"
    bad_shape.write_bytes(encode_delta_tensor([[0.001, 0.001], [0.001, 0.001]]))
    cases = [
        (bad_key, "delta artifact tensor key does not equal manifest target_parameter"),
        (bad_shape, "delta artifact tensor shape does not equal manifest delta_shape"),
    ]
    for index, (bad_artifact, message) in enumerate(cases):
        bad_manifest = dict(payload)
        bad_manifest["artifact_path"] = str(bad_artifact)
        bad_manifest["artifact_sha256"] = sha256(bad_artifact)
        bad_manifest_path = write_json(tmp_path / f"manifest_art_{index}.json", bad_manifest)
        result = run_script(
            "--run-id", f"mat_art_{index}",
            "--out-root", tmp_path / "out",
            "--base-model-path", base,
            "--delta-artifact-manifest", bad_manifest_path,
            "--delta-artifact", bad_artifact,
            "--reviewed-artifact-sha256", bad_manifest["artifact_sha256"],
            "--authorize-larql-continuation-patched-model-materialization",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_missing_base_and_path_inside_base_fail_closed(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = run_script(
        "--run-id", "mat_003",
        "--out-root", tmp_path / "out",
        "--base-model-path", tmp_path / "missing",
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "base model path does not exist" in result.stdout

    inside_out = base / "nested"
    result = run_script(
        "--run-id", "mat_004",
        "--out-root", inside_out,
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "output path must not be inside the base model path" in result.stdout


def test_missing_manifest_or_delta_artifact_fail_closed(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = run_script(
        "--run-id", "mat_005",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", tmp_path / "missing.json",
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "required file path does not exist" in result.stdout

    result = run_script(
        "--run-id", "mat_006",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", tmp_path / "missing.safetensors",
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "delta artifact path does not exist" in result.stdout


def test_target_parameter_missing_from_model_index_fails_closed(tmp_path):
    base = base_model_fixture(tmp_path, include_target=False)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = run_script(
        "--run-id", "mat_007",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "target parameter missing from pt shard" in result.stdout


def test_target_shape_mismatch_fails_closed(tmp_path):
    base = base_model_fixture(tmp_path, target_shape=(2, 2))
    manifest, artifact = delta_manifest_fixture(tmp_path, target_shape=(2, 3))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = run_script(
        "--run-id", "mat_008",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode != 0
    assert "target base tensor shape does not match delta shape" in result.stdout


def test_successful_materialization_writes_record_review_packet_and_copy(tmp_path):
    base = base_model_fixture(tmp_path)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    base_before = sha256(base / "model_state.pt")
    result = run_script(
        "--run-id", "mat_009",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode == 0
    out_dir = tmp_path / "out" / "mat_009"
    patched = out_dir / "patched_model"
    assert patched.exists()
    assert sha256(base / "model_state.pt") == base_before
    assert sha256(patched / "model_state.pt") != base_before
    record = json.loads((out_dir / "larql_continuation_patched_model_materialization_record.json").read_text(encoding="utf-8"))
    assert record["report_type"] == "larql_continuation_patched_model_materialization.v0"
    assert record["weight_edit_performed"] is True
    assert record["patched_model_materialized"] is True
    assert record["base_model_overwritten"] is False
    assert record["model_inference_performed"] is False
    assert record["generation_performed"] is False
    assert record["training_performed"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["patched_model_file_count"] >= 2
    assert (out_dir / "continuation_patched_model_manifest.json").exists()
    assert (out_dir / "continuation_patched_model_review_packet.md").exists()


def test_safetensors_end_to_end_or_skip(tmp_path):
    if importlib.util.find_spec("torch") is None or importlib.util.find_spec("safetensors") is None:
        pytest.skip("safetensors/torch unavailable for end-to-end safetensors materialization test")
    base = base_model_fixture(tmp_path, use_safetensors_shard=True)
    manifest, artifact = delta_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = run_script(
        "--run-id", "mat_010",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--delta-artifact-manifest", manifest,
        "--delta-artifact", artifact,
        "--reviewed-artifact-sha256", payload["artifact_sha256"],
        "--authorize-larql-continuation-patched-model-materialization",
    )
    assert result.returncode == 0


def test_no_inference_generation_training_or_promotion_in_source():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in text
    assert "from transformers import" not in text[:1200]
    assert "promotion_authorized = True" not in text
